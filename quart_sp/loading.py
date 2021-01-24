from functools import reduce
from quart import Blueprint, redirect, session, url_for, websocket
from typing import Any, Dict, List, Tuple

import aiohttp
import asyncio
import auth
import collections
import playlist_helper
import re
import redis_cache
import spotify
import ujson
import util

log = util.setLogger(__name__)
loading_route = Blueprint('loading_route', __name__)


@loading_route.websocket("/load")
async def load_songs_counts():
    access_token = await websocket.receive()
    # TODO: Authentication quart-auth ?

    try:
        sp = spotify.Spotify(access_token)
        async with aiohttp.ClientSession(json_serialize=ujson) as sess:
            tracks = await sp.current_user_saved_tracks(50, 0, sess)
            # total = result['total']  # TODO: Testing, currently capping at 100
            total = 200
            log.info(f"User has a total of {total} tracks")
            await websocket.send(str(total))

            await extract_tracks(sp, sess, tracks)

            loop = asyncio.get_event_loop()
            asyncio_tasks = []
            for offset in range(50, total, 50):
                tracks = await sp.current_user_saved_tracks(50, offset, sess)
                asyncio_tasks.append(loop.create_task(extract_tracks(sp, sess, tracks)))

            # collect remaining artists and album ids to be called
            res = await asyncio.gather(*asyncio_tasks)
            res = reduce(lambda x, y: (x[0] + y[0], x[1] + y[1], x[2] + y[2], x[3] + y[3]),
                         res)

            # update remaining artist and album genres
            await asyncio.gather(*[
                loop.create_task(batch_update_artist_genres(
                    sp, sess, res[0][i:i + 49], res[1][i:i + 49]))
                for i in range(0, len(res[0]), 49)])

            await asyncio.gather(*[
                loop.create_task(batch_update_album_genres(
                    sp, sess, res[2][i:i + 19], res[3][i:i + 19]))
                for i in range(0, len(res[0]), 49)])

        # map user's saved tracks to redis
        # TODO: maybe have async gather on genre:len(tids) to eliminate SCARD overhead
        redis_cache.set_user_genre_track_count(access_token)

        await websocket.send("STOP")
        # return redirect(url_for('spotify_analytics'))

    except asyncio.CancelledError:
        # TODO: Handle disconnect
        log.debug("CLIENT CLOSED")
        raise


# TODO: Should we save tracks with no genres? Currently no visibility
# TODO: Delete unused fields
async def save_track_to_redis(track: Dict[str, Any], added_at: str, access_token: str) -> bool:
    """
    Extracts artist and album id from each saved track and attempts to grab all related genres. Each
    track is then associated with 0 or more genres.
    Sets each spotify track id to its name in redis, default (none) TTL expiry
    """
    track_obj = track['track']

    log.info(track_obj['name'])

    # clean songs titles with quotes
    cleaned_tname = re.sub("(\"|\')", "\\\"", track_obj['name'])

    # save song track info to redis
    track_info = {
        # @FUTURE: Possibly dump all information? (external url, uri)
        'album': track_obj['album']['id'],
        'artists': ujson.dumps([artist['name'] for artist in track_obj['artists']]),
        'duration': track_obj['duration_ms'],  # in milliseconds
        # 'is_playable': track_obj['is_playable'],
        'name': cleaned_tname,
        'popularity': track_obj['popularity'],
        'preview_url': track_obj['preview_url'],
        'spotify_url': track_obj['external_urls']['spotify']
    }

    # save spotify track in redis
    success_ts = redis_cache.set_spotify_track(track_obj['id'], track_info)
    success_ta = redis_cache.set_user_tracks_added_at(access_token, {track_obj['id']: added_at})

    return success_ts & success_ta # artist_ids, album_id


async def batch_update_album_genres(sp: spotify.Spotify, sess: aiohttp.ClientSession,
                                    album_ids: List[str], album_track_ids: List[str]) -> bool:
    """Saves uncached album genres to api redis cache and updates user's genre set on
    redis session cache, currently returns a boolean if genres were saved (not used ATM)"""
    albums = await sp.albums(album_ids, sess)
    genre_map = collections.defaultdict(set)
    user_genres = set()

    # TODO: consider izip
    for track_id, album in zip(album_track_ids, albums):
        if not album:
            raise Exception(albums, album_ids)
        album_genres = album['genres']
        if album_genres:
            for genre in album_genres:
                genre_map[genre].add(track_id)
                user_genres.add(genre)
        else:
            log.debug(f'Could not extract album genres from {track_id}')
            album_genres = ["NA"]
            genre_map["NA"].add(track_id)
            user_genres.add("NA")

        # save album genres to redis
        redis_cache.set_spotify_album_genres(album['id'], album_genres)

    token = await sp.get_access_token()
    user_gt_set, user_g_set = True, True
    # save "token+genre" : [track_id] to redis
    if genre_map:
        user_gt_set = redis_cache.set_user_genre_tracks(token, genre_map)
    # update users genres set
    if user_genres:
        user_g_set = redis_cache.set_user_genres(token, user_genres)
    return user_gt_set & user_g_set


async def batch_update_artist_genres(sp: spotify.Spotify, sess: aiohttp.ClientSession,
                                     artist_ids: List[str], track_ids: List[str]) -> bool:
    """Saves uncached artist genres to api redis cache and updates user's genre set on redis
    session cache, currently returns a boolean if genres were saved (not used ATM)"""

    genre_map = collections.defaultdict(set)
    artists = await sp.artists(artist_ids, sess)
    user_genres = set()

    for track_id, artist in zip(track_ids, artists):
        artist_genres = artist['genres']
        if artist_genres:
            for genre in artist_genres:
                genre_map[genre].add(track_id)
                user_genres.add(genre)
            # save track genres to redis
        else:
            # TODO: save as N/A genre?
            log.debug(f'Could not extract genres from {track_id}')
            genre_map["NA"].add(track_id)
            user_genres.add("NA")
            artist_genres = ["NA"]

        redis_cache.set_spotify_artist_genres(artist['id'], artist_genres)

    token = await sp.get_access_token()
    user_gt_set, user_g_set = True, True
    # save "token+genre" : [track_id] to redis
    if genre_map:
        user_gt_set = redis_cache.set_user_genre_tracks(token, genre_map)
    # update users genres set
    if user_genres:
        user_g_set = redis_cache.set_user_genres(token, user_genres)
    return user_gt_set & user_g_set


# TODO: optimize this poorly written code
async def extract_tracks(sp: spotify.Spotify, sess: aiohttp.ClientSession, tracks):
    genres_cached = collections.defaultdict(set)  # port cached artists to users GTC
    artist_track_ids = []
    artist_ids = []  #
    album_track_ids = []
    album_ids = []
    genre_set = set()
    token = await sp.get_access_token()

    for track in tracks:
        track_obj = track['track']
        added_at = track['added_at']

        # emit to front end loading page
        await websocket.send(track_obj['name'])
        print(track_obj['name'])

        # Conditions to skip # TODO: testing on local files
        if track_obj['is_local'] or not track_obj['available_markets'] \
                or 'US' not in track_obj['available_markets']:
            continue

        # save track and user added date to redis
        if not redis_cache.exists(track_obj['id']):
            await save_track_to_redis(track, added_at, token)

        # artist genres update to redis
        for artist in track_obj['artists']:
            artist_genres = redis_cache.get_spotify_artist_genres(artist['id'])
            if not artist_genres:
                artist_track_ids.append(track_obj['id'])
                artist_ids.append(artist['id'])

                # batch update genre map (API rate limit)
                if len(artist_track_ids) == 49 and len(artist_ids) == 49:
                    # save track genres to redis and update user GTC
                    batch_copy_tid = artist_track_ids[:]
                    batch_copy_aid = artist_ids[:]
                    await batch_update_artist_genres(sp, sess, batch_copy_aid,
                                                     batch_copy_tid)
                    artist_track_ids.clear()
                    artist_ids.clear()
            else:
                # TODO: create generic genre setting
                for genre in artist_genres:
                    genres_cached[genre].add(track_obj['id'])
                    genre_set.add(genre)

        album_genres = redis_cache.get_spotify_album_genres(track_obj['album']['id'])
        if not album_genres:
            # album genres update to redis
            album_track_ids.append(track_obj['id'])
            album_ids.append(track_obj['album']['id'])

            if len(album_ids) == 19 and len(album_track_ids) == 19:
                batch_copy_aid = album_ids[:]
                batch_copy_tid = album_track_ids[:]
                log.debug(album_ids, album_track_ids)
                await batch_update_album_genres(sp, sess, batch_copy_aid, batch_copy_tid)
                album_ids.clear()
                album_track_ids.clear()
        else:
            for genre in album_genres:
                genres_cached[genre].add(track_obj['id'])
                genre_set.add(genre)

    # update user genre track list
    if genres_cached:
        # save { "token+genre" : [track_id] } to redis
        redis_cache.set_user_genre_tracks(token, genres_cached)
        # save user genres to redis
        genre_set.update(genres_cached.keys())
    # update users genres
    if genre_set:
        redis_cache.set_user_genres(token, genre_set)

    return artist_ids, artist_track_ids, album_ids, album_track_ids


# DEPRECATED
@loading_route.route('/loading', methods=['POST', 'GET'])
async def load_songs_from_spotify():
    """

    :return: redirect to home page
    """
    print("DEPRECATED")
    return await redirect(url_for('spotify_analytics'))
