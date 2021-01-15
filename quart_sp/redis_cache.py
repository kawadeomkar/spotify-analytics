import asyncio
from hashlib import md5
from typing import Any, List, Dict, Union, Set

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


# generic get
def get_spotify_track_name(track_id: str) -> str:
    return client.hgetall(track_id)


# generic set
def set_spotify_track(track_id: str, track_info: Dict[str, str]) -> bool:
    if 'popularity' not in track_info or 'name' not in track_info:
        raise Exception("Empty track mapping")
    return client.hset(track_id, mapping=track_info)



def set_spotify_track_genres(artist_id: str, artist_genres: List[str]) -> bool:
    return client.sadd(artist_id, *artist_genres)


def get_spotify_track_genres(artist_id: str) -> Union[Set[str], Set[None]]:
    return client.smembers(artist_id)


def set_spotify_album_genres(album_id: str, album_genres: List[str]) -> bool:
    return client.sadd(album_id, *album_genres)


def get_spotify_album_genres(album_id: str) -> Union[Set[str], Set[None]]:
    return client.smembers(album_id)



def set_user_genres(access_token: str, genres: List[str]) -> bool:
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    success = client.sadd(hash_key + "genre", *genres)
    set_expire_to_access_token(hash_key, hash_key + "genre")
    return success


def _get_user_genres(hash_key: str) -> Set[str]:
    return client.smembers(hash_key + "genre")


def get_user_genre_id_map(access_token: str):
    hash_key = md5(access_token.encode('utf-8')).hexdigest() 
    user_genres = _get_user_genres(hash_key)
    # TODO: scale TTL on popularity to be min 2 hrs, hash_key in `get_user_genre_tracks`?
    genres_user_track_id_map = {'genre':get_user_genre_tracks(access_token, genre) for genre in user_genres}
    ret = {}
    for genre, tids in genres_user_track_id_map.items():
        ret[genre] = []
        for tid in tids:
            ret[genre].append(get_spotify_track_name(tid))
    return ret
            
    

def get_user_genre_track_count(access_token: str) -> Dict[str, str]:
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    return client.hgetall(hash_key + 'gtc')


def set_user_genre_tracks(access_token: str, genre_track_map: Dict[str, List[str]]) -> bool:
    # Don't need to use "set_expire_to_access_token" func here, saving one call per sadd here
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    print(f"User genre track map: {genre_track_map}")
    asyncio.sleep(0.5) # TODO: for testing
    ttl = client.ttl(hash_key)
    success = True

    for genre, track_list in genre_track_map.items():
        success = success & client.sadd(hash_key + genre, *track_list)
        client.expire(hash_key + genre, ttl)
    return success


def set_user_genre_track_count(access_token: str):
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    user_genres = _get_user_genres(hash_key)
    user_gtc = {genre: client.scard(hash_key + genre) for genre in user_genres}
    success = client.hset(hash_key + 'gtc', mapping=user_gtc)
    set_expire_to_access_token(hash_key, hash_key + 'gtc')
    return success


# DEPRECATED
def set_user_genre_track_count_v0(access_token: str, genre_track_map: Dict[str, List[str]]) -> None:
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    genre_track_count: Dict[str, int] = {k: len(v) for k, v in genre_track_map.items()}
    client.hset(hash_key + 'gtc', mapping=genre_track_count)
    set_expire_to_access_token(hash_key, hash_key + 'gtc')


def get_user_genre_tracks(access_token: str, genre: str) -> Union[Set[str], Set[None]]:
    hash_key = md5(access_token.encode('utf-8')).hexdigest()
    return client.smembers(hash_key + genre)
