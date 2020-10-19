# Liked songs library grouped by genre 
from functools import lru_cache
from itertools import chain
from typing import Dict, List

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

    if genres:res_pos += 1
    else:res_neg += 1
    print(res_pos, res_neg)

    return genres


def likedSongsGenreMap(spotify: spotipy.client) -> Dict[str, List[str]]:
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
    log.info("TRACKS: ", tracks)
    for track in tracks:
        track_obj = track['track']

        artist_ids = [artist['id'] for artist in track_obj['artists']]
        album_id = track_obj['album']['id']
        genres = get_track_genres(spotify, artist_ids=artist_ids, album_id=album_id)

        for genre in genres:
            if genre not in genre_map:
                genre_map[genre] = []
            genre_map[genre].append(track_obj['id'])

    return genre_map
