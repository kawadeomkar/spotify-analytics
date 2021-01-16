# Liked songs library grouped by genre 
from itertools import zip_longest
from quart import Blueprint, redirect, render_template, request, session
from typing import Any, Dict, List, Set

import aiohttp
import auth
import player
import re
import redis_cache
import spotify
import ujson
import util

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
    sorted_song_info_map = sorted(song_info_map,
                                  key=lambda s: int(s['popularity']),
                                  reverse=True)

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

    genre = (await request.get_json())['genre']
    access_token = session['access_token']
    sp = spotify.Spotify(access_token)

    async with aiohttp.ClientSession(json_serialize=ujson) as sess:
        # TODO: User sets the genre name
        playlist_id = await create_playlist(sp, sess, genre)

        tracks_to_export = redis_cache.get_user_genre_tracks(access_token, genre)
        # TODO: Sort on popularity
        # TODO: Remove hotfix
        tracks_to_export = ["spotify:track:" + track for track in tracks_to_export]
        # TODO: retry logic in this function? display error if false
        await add_tracks_to_playlist(sp, sess, playlist_id, tracks_to_export)

    return genre





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

    print(f"Track IDS: {track_ids}")
    if track_len <= 100:
        await sp.add_items_to_playlist(playlist_id, list(track_ids), sess)
    else:
        for items in zip_longest(*(iter(track_ids),) * 100):
            items_filtered = list(filter(None, items))
            await sp.add_items_to_playlist(playlist_id, items_filtered, sess)

    return True
