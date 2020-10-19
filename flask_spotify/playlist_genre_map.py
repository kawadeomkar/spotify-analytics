# Liked songs library grouped by genre 
from functools import lru_cache
from itertools import chain

import json
import logging
import spotipy
import util

log = util.setLogger(__name__)


@lru_cache(maxsize=100)
def getArtistGenres(spotify, artist_id):
    res = spotify.artist(artist_id)
    return res['genres']


def likedSongsGenreMap(spotify: spotipy.client) -> dict:
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

    log.info(tracks)

    genre_map = {}
    for track in tracks:
        track_obj = track['track']
        for genre in getArtistGenres(spotify, track_obj['artists'][0]['id']):
            if not genre in genre_map:
                genre_map[genre] = []
            genre_map[genre].append(track_obj['id'])
    return genre_map
