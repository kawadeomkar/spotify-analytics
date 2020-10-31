from typing import List, Dict, Union, Set

import os
import redis
import time
import util

log = util.setLogger(__name__)

# TODO: ENV host
client = redis.Redis(host=os.environ.get('REDIS_HOST', 'localhost'),
                     port=6379,
                     decode_responses=True)


# testing
def ping():
    return client.ping()


def add_user(access_token: str, expires_in: str) -> None:
    TTL = float(expires_in) + time.time()
    client.set(access_token, TTL)
    client.expire(access_token, expires_in)


def user_exists(access_token: str) -> bool:
    return bool(client.exists(str(access_token)))


def user_map_exists(access_token) -> bool:
    return user_exists(access_token) and bool(client.exists(access_token + "genre"))


def set_expire_to_access_token(access_token: str, key: str) -> bool:
    ttl = client.ttl(access_token)
    return client.expire(key, ttl)


# generic set
def set_spotify_track(track_id: str, track_info: Dict[str, str]) -> bool:
    return client.hset(track_id, mapping=track_info)


# generic get
def get_spotify_track_name(track_id: str) -> str:
    return client.hgetall(track_id)


def set_user_genres(access_token: str, genres: List[str]) -> None:
    client.sadd(access_token + "genre", *genres)
    set_expire_to_access_token(access_token, access_token + "genre")


def set_user_genre_tracks(access_token: str, genre_track_map: Dict[str, List[str]]) -> None:
    # Don't need to use "set_expire_to_access_token" func here, saving one call per sadd here
    ttl = client.ttl(access_token)
    for genre, track_list in genre_track_map.items():
        client.sadd(access_token + genre, *track_list)
        client.expire(access_token + genre, ttl)


def set_user_genre_track_count(access_token: str, genre_track_map: Dict[str, List[str]]) -> None:
    genre_track_count: Dict[str, int] = {k: len(v) for k, v in genre_track_map.items()}
    client.hset(access_token + 'gtc', mapping=genre_track_count)
    set_expire_to_access_token(access_token, access_token + 'gtc')


def get_user_genre_track_count(access_token: str) -> Dict[str, str]:
    return client.hgetall(access_token + 'gtc')


def get_user_genre_tracks(access_token: str, genre: str) -> Union[Set[str], Set[None]]:
    return client.smembers(access_token + genre)
