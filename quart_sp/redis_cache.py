import asyncio
from collections import defaultdict
from hashlib import md5
from typing import Any, Optional, List, Dict, Union, Set

import os
import redis
import util

log = util.setLogger(__name__)

# TODO: ENV host
client = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'),
                     port=6379,
                     decode_responses=True)


# testing
def ping():
    return client.ping()


### USER SESSION

# generic exists
def exists(key):
    return client.exists(key)


def add_user(access_token: str, expires_in: str) -> None:
    TTL = float(expires_in)
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    client.set(hash_key, TTL)
    client.expire(hash_key, expires_in)


def user_exists(access_token: str) -> bool:
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    return bool(client.exists(hash_key))


def user_map_exists(access_token) -> bool:
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    return user_exists(access_token) and bool(client.exists(hash_key + "gtc"))


def set_expire_to_access_token(hash_key: str, key_to_expire: str) -> bool:
    ttl = client.ttl(hash_key)
    return client.expire(key_to_expire, ttl)


### LOADING

## USER SPECIFIC CACHING

def _get_user_genres(hash_key: str) -> Set[str]:
    return client.smembers(hash_key + "genre")


def set_user_genres(access_token: str, genres: List[str]) -> bool:
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    success = client.sadd(hash_key + "genre", *genres)
    set_expire_to_access_token(hash_key, hash_key + "genre")
    return success


def get_user_genre_tracks(access_token: str, genre: str) -> Optional[Set[str]]:
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    return client.smembers(hash_key + genre)


def set_user_genre_tracks(access_token: str, genre_track_map: Dict[str, List[str]]) -> bool:
    # Don't need to use "set_expire_to_access_token" func here, saving one call per sadd here
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    log.info(f"User genre track map: {genre_track_map}")
    asyncio.sleep(0.5)  # TODO: for testing
    ttl = client.ttl(hash_key)
    success = True

    for genre, track_list in genre_track_map.items():
        success = success & client.sadd(hash_key + genre, *track_list)
        client.expire(hash_key + genre, ttl)
    return success


def get_user_genre_track_count(access_token: str) -> Dict[str, str]:
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    return client.hgetall(hash_key + 'gtc')


def set_user_genre_track_count(access_token: str):
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    user_genres = _get_user_genres(hash_key)
    if "NA" in user_genres:
        user_genres.remove("NA")

    user_gtc = {genre: client.scard(hash_key + genre) for genre in user_genres}
    success = client.hset(hash_key + 'gtc', mapping=user_gtc)
    set_expire_to_access_token(hash_key, hash_key + 'gtc')
    return success


def get_user_tracks_added_at(access_token, track_ids: List[str] = None):
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    if not track_ids:
        return client.hgetall(hash_key + 'taa')
    else:
        return client.hmget(hash_key + 'taa', track_ids)


def set_user_tracks_added_at(access_token: str, tid_added_at_map: Dict[str, str]) -> bool:
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    success = client.hset(hash_key + 'taa', mapping=tid_added_at_map)
    set_expire_to_access_token(hash_key, hash_key + 'taa')
    return success


## SPOTIFY GENERAL CACHING

# generic get
def get_spotify_track_name(track_id: str) -> str:
    return client.hgetall(track_id)


# generic set
def set_spotify_track(track_id: str, track_info: Dict[str, str]) -> bool:
    if 'popularity' not in track_info or 'name' not in track_info:
        raise Exception("Empty track mapping")
    return client.hset(track_id, mapping=track_info)


def get_spotify_artist_genres(artist_id: str) -> Union[Set[str], Set[None]]:
    return client.smembers(artist_id)


def set_spotify_artist_genres(artist_id: str, artist_genres: List[str]) -> bool:
    return client.sadd(artist_id, *artist_genres)


def get_spotify_album_genres(album_id: str) -> Union[Set[str], Set[None]]:
    return client.smembers(album_id)


def set_spotify_album_genres(album_id: str, album_genres: List[str]) -> bool:
    #print(type(album_genres))
    #raise Exception(str(album_genres))
    return client.sadd(album_id, *album_genres)


### GRAPHS

def get_user_genre_track_obj_map(access_token: str):
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    user_genres = _get_user_genres(hash_key)
    # TODO: scale TTL on popularity to be min 2 hrs, hash_key in `get_user_genre_tracks`?
    genres_user_track_id_map = defaultdict(set)

    #log.info(f"USER GENRES: {user_genres}")
    na_tids = set()
    if "NA" in user_genres:
        na_tids = get_user_genre_tracks(access_token, "NA")

    log.info(f"LEN OF USER GENRES: {len(user_genres)}")
    # TODO: async for on generator
    for genre in user_genres:
        if genre == "NA":
            log.info(f"SKIPPING GENRE: {genre}")
            continue
        ugts = get_user_genre_tracks(access_token, genre)

        # log.info(f"USER GTS FOR GENRE {genre} : USER GTS: {ugts}")
        for track_id in ugts:
            if track_id in na_tids:
                # TODO: update redis -> remove n/a from non n/a genres
                # log.info(f"Adding TRACK ID {track_id} TO GENRE {genre}")
                na_tids.remove(track_id)
            genres_user_track_id_map[genre].add(track_id)

    log.info(f"LEN OF NAs {len(na_tids)}")
    genres_user_track_id_map['NA'] = na_tids
    # log.info("GTS")
    log.info(f"LEN OF GUTIM: {len(genres_user_track_id_map)}")

    ret = []
    for genre, tids in genres_user_track_id_map.items():

        added_ats = get_user_tracks_added_at(access_token, tids)

        for tid, added_at in zip(tids, added_ats):
            t_obj = get_spotify_track_name(tid)
            t_obj['added_at'] = added_at
            t_obj['track_id'] = tid
            t_obj['genre'] = genre
            del t_obj['preview_url']
            del t_obj['spotify_url']
            log.info(t_obj)
            ret.append(t_obj)

    return ret


### DEPRECATED

def set_user_genre_track_count_v0(access_token: str, genre_track_map: Dict[str, List[str]]) -> None:
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    genre_track_count: Dict[str, int] = {k: len(v) for k, v in genre_track_map.items()}
    client.hset(hash_key + 'gtc', mapping=genre_track_count)
    set_expire_to_access_token(hash_key, hash_key + 'gtc')
