# Liked songs library grouped by genre 
from functools import lru_cache
from itertools import zip_longest
from quart import Blueprint, redirect, render_template, request, session
from typing import Any, Dict, List, Set

import aiohttp
import auth
import player
import redis_cache
import spotify
import ujson
import util

import time

log = util.setLogger(__name__)
playlist_route = Blueprint('playlist_route', __name__)

# TESTING TODO: remove
res_pos = 0
res_neg = 0


@playlist_route.route('/playlist/<string:genre>')
async def playlist(genre):
    validate = auth.validateAccessToken()
    if validate:
        return await redirect(validate)

    access_token = session['access_token']
    songs = redis_cache.get_user_genre_tracks(access_token, genre)
    song_info_map = [redis_cache.get_spotify_track_name(t_id) for t_id in songs]
    try:
        sorted_song_info_map = sorted(song_info_map,
                                  key=lambda song: int(song['popularity']),
                                  reverse=True)
    except:
        raise Exception(str(song_info_map) + " XXX " + str(songs))

    sp = spotify.Spotify(access_token)
    d_id, devices = await player.get_device_info(sp)

    # extract artists back to strings
    for song in sorted_song_info_map:
        song['artists'] = ', '.join(ujson.loads(song['artists']))

    return await render_template('playlist_list.html', song_info_map=sorted_song_info_map,
                                 genre=genre,
                                 access_token=access_token, d_id=d_id, devices=devices)


@playlist_route.route('/export', methods=['POST'])
async def export():
    # TODO: Implement JS logic to issue error
    validate = auth.validateAccessToken()
    if validate:
        return await redirect(validate)

    genre = await request.get_json()['genre']
    access_token = await session['access_token']
    sp = spotify.Spotify(access_token)

    with aiohttp.ClientSession(json_serialize=ujson) as sess:
        # TODO: User sets the genre name
        playlist_id = await create_playlist(sp, sess, genre)

        genres_to_export = redis_cache.get_user_genre_tracks(access_token, genre)

        # TODO: retry logic in this function? display error if false
        await add_tracks_to_playlist(sp, playlist_id, genres_to_export)

    return await genre


async def get_track_genres(sp: spotify.Spotify,
                           sess: aiohttp.ClientSession,
                           artist_ids: List[str] = None,
                           album_id: str = None) -> List[str]:
    """
    Returns a set of genres obtained from the album and artist, multiple genres will map to the same
    track ID in this scenario
    """
    # TODO: TESTING
    global res_pos, res_neg

    genres = set()

    if artist_ids:
        for a_id in artist_ids:
            resp = await sp.artists(a_id, sess)
            artist_genres = []
            if isinstance(resp, list):
                for artist in resp:
                    artist_genres.extend(artist.get('genres', None))
            else:
                artist_genres = resp.get('genres', None)
            if artist_genres:
                genres.update(artist_genres)

    if album_id:
        resp = await sp.albums(album_id, sess)

        album_genres = []
        if isinstance(resp, list):
            for artist in resp:
                album_genres.extend(artist.get('genres', None))
        else:
            album_genres = resp.get('genres', None)
        if album_genres:
            genres.update(artist_genres)

    # TODO: remove analysis
    if genres:
        res_pos += 1
    else:
        res_neg += 1
    log.debug(f"HIT: {res_pos} MISS: {res_neg}")

    return genres


async def liked_songs_genre_map(track: Dict[str, Any]) -> bool:
    """
    Extracts artist and album id from each saved track and attempts to grab all related genres. Each
    track is then associated with 0 or more genres.
    Sets each spotify track id to its name in redis, default (none) TTL expiry
    """
    track_obj = track['track']

    log.info(track_obj['name'])

    # save song track info to redis
    track_info = {
        # @Future: Possibly dump all information? (external url, uri)
        'artists': ujson.dumps([artist['name'] for artist in track_obj['artists']]),
        'name': track_obj['name'],
        'duration': track_obj['duration_ms'],  # in milliseconds
        'spotify_url': track_obj['external_urls']['spotify'],
        'popularity': track_obj['popularity']
    }

    # save spotify track in redis
    success = redis_cache.set_spotify_track(track_obj['id'], track_info)

    # extract genres
    # artist_ids = [artist['id'] for artist in track_obj['artists']]
    # album_id = track_obj['album']['id']

    # genres = await get_track_genres(sp, sess, artist_ids=artist_ids, album_id=album_id)

    # TODO: figure out what to do if there is no genre associated with a track
    # for genre in genres:
    #     if genre not in genre_map:
    #         genre_map[genre] = []
    #     genre_map[genre].append(track_obj['id'])

    return success # artist_ids, album_id


async def create_playlist(sp: spotify.Spotify,
                          sess: aiohttp.ClientSession,
                          name: str,
                          public: bool = True,
                          description: str = 'This playlist was curated by SpotifyAnalytics '
                                             'https://github.com/kawadeomkar/spotify-analytics') -> str:
    """ Creates a playlist and returns playlist id """
    user_id = await sp.get_user_id(sess)
    pl = await sp.create_playlist(user_id, name, sess, public=public,
                                  description=description)
    return pl['id']


async def add_tracks_to_playlist(sp: spotify.Spotify,
                                 sess: aiohttp.ClientSession,
                                 playlist_id: str,
                                 track_ids: Set[str],
                                 position: int = 0) -> bool:
    """ Adds tracks to a playlist, if track_ids length is longer than 100,
    zip_longest is used for performance boost over slicing (matrix transpose on 100 identity refs)
    TODO: position is not used for now (use later to append based on popularity
    TODO: retry logic if HTTPError is thrown?"""
    track_len = len(track_ids)
    if track_len <= 100:
        await sp.add_items_to_playlist(playlist_id, track_ids, sess)
    else:
        for items in zip_longest(*(iter(track_ids),) * 100):
            items_filtered = list(filter(None, items))
            await sp.add_items_to_playlist(playlist_id, items_filtered, sess)

    return True
