# Liked songs library grouped by genre 
from functools import lru_cache
from itertools import chain, zip_longest
from requests.exceptions import HTTPError
from typing import Dict, List, Set

import json
import redis_cache
import spotipy
import util

log = util.setLogger(__name__)

# TESTING TODO: remove
res_pos = 0
res_neg = 0


@lru_cache(maxsize=128)
def get_artist_genres(spotify: spotipy.client, artist_id: str) -> List[str]:
    return spotify.artist(artist_id)['genres']


@lru_cache(maxsize=128)
def get_album_genres(spotify: spotipy.client, album_id: str):
    return spotify.album(album_id)['genres']


def get_track_genres(spotify: spotipy.client,
                     artist_ids: List[str] = None,
                     album_id: str = None) -> List[str]:
    """
    Returns a set of genres obtained from the album and artist, multiple genres will map to the same
    track ID in this scenario
    """
    global res_pos, res_neg

    genres = set()

    if artist_ids:
        for a_id in artist_ids:
            genres.update(get_artist_genres(spotify, a_id))

    if album_id:
        genres.update(get_album_genres(spotify, album_id))

    # TODO: remove analysis
    if genres:
        res_pos += 1
    else:
        res_neg += 1
    print(res_pos, res_neg)

    return genres


def liked_songs_genre_map(spotify: spotipy.client) -> Dict[str, List[str]]:
    """
    Extracts artist and album id from each saved track and attempts to grab all related genres. Each
    track is then associated with 0 or more genres.
    Sets each spotify track id to its name in redis, default (none) TTL expiry
    """
    result = spotify.current_user_saved_tracks(limit=50, offset=0)
    tracks = result['items']
    # total = result['total'] TODO: Testing, currently capping at 100
    total = 100
    log.info(f"User has a total of {total} tracks")

    if total > 50:
        rest = list(map(
            lambda x: (spotify.current_user_saved_tracks(limit=50, offset=x)['items']),
            list(range(50, total, 50))
        ))
        rest = list(chain.from_iterable(rest))
        tracks.extend(rest)

    genre_map = {}
    for track in tracks:
        track_obj = track['track']

        # save song track info to redis
        track_info = {
            # @Future: Possibly dump all information? (external url, uri)
            'artists': json.dumps([artist['name'] for artist in track_obj['artists']]),
            'name': track_obj['name'],
            'duration': track_obj['duration_ms'],  # in milliseconds
            'spotify_url': track_obj['external_urls']['spotify']
        }
        redis_cache.set_spotify_track(track_obj['id'], track_info)

        # extract genres
        artist_ids = [artist['id'] for artist in track_obj['artists']]
        album_id = track_obj['album']['id']
        genres = get_track_genres(spotify, artist_ids=artist_ids, album_id=album_id)

        for genre in genres:
            if genre not in genre_map:
                genre_map[genre] = []
            genre_map[genre].append(track_obj['id'])

    return genre_map


def create_playlist(spotify: spotipy.client,
                    name: str,
                    public: bool = True,
                    description: str = 'This playlist was curated by SpotifyAnalytics '
                                       'https://github.com/kawadeomkar/spotify-analytics') -> str:
    """ Creates a playlist and returns playlist id """
    user_id = spotify.me()['id']
    playlist = spotify.user_playlist_create(user_id, name, public=public, description=description)
    return playlist['id']


def add_tracks_to_playlist(spotify: spotipy.client,
                           playlist_id: str,
                           track_ids: Set[str],
                           position: int = 0) -> bool:
    """ Adds tracks to a playlist, if track_ids length is longer than 100,
    zip_longest is used for performance boost over slicing (matrix transpose on 100 identity refs)
    TODO: position is not used for now (use later to append based on popularity
    TODO: retry logic if HTTPError is thrown?"""
    try:
        track_len = len(track_ids)
        if track_len <= 100:
            spotify.playlist_add_items(playlist_id, track_ids)
        else:
            for items in zip_longest(*(iter(track_ids),) * 100):
                items_filtered = list(filter(None, items))
                spotify.playlist_add_items(playlist_id, items_filtered)

        return True
    except HTTPError as e:
        log.error(e)
        return False



