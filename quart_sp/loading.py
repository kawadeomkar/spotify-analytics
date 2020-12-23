from quart import redirect, session, url_for, websocket
from quart_sp import app
from typing import List

import aiohttp
import playlist_helper
import redis_cache
import spotify
import ujson
import util

log = util.setLogger(__name__)


@app.websocket("/loading_song_count")
async def load_songs_counts(song_count: str):
    await websocket.send(song_count)


async def extract_tracks(sp: spotify.Spotify, session: aiohttp.ClientSession, genre_map,
                         tracks: List, count: int):
    for track in tracks:
        track_obj = track['track']

        # emit to front end loading page
        print("SONG NAME: ", track_obj['name'])
        await websocket.send("loading_song_titles", track_obj['name'])
        count += 1
        await websocket.send("loading_song_count", str(count))

        # save track to redis and form genre map
        await playlist_helper.liked_songs_genre_map(sp, session, genre_map, track)


@app.route('/loading', methods=['POST', 'GET'])
async def load_songs_from_spotify():
    """

    :return: redirect to home page
    """
    print("loading")
    access_token = session['access_token']
    sp = spotify.Spotify(access_token)

    async with aiohttp.ClientSession(json_serialize=ujson) as sess:
        tracks = await sp.current_user_saved_tracks(50, 0, sess)
        # total = result['total']  # TODO: Testing, currently capping at 100
        total = 100
        log.info(f"User has a total of {total} tracks")
        count = 0

        # create genre map to save to redis
        genre_map = {}
        extract_tracks(sp, sess, genre_map, tracks, count)

        for size in range(50, total, 50):
            tracks = await sp.current_user_saved_tracks(50, size, sess)
            await extract_tracks(sp, genre_map, tracks, count)

    # map user's saved tracks to redis
    redis_cache.set_user_genres(access_token, genre_map.keys())
    redis_cache.set_user_genre_tracks(access_token, genre_map)
    redis_cache.set_user_genre_track_count(access_token, genre_map)

    return await redirect(url_for('spotify_analytics'))
