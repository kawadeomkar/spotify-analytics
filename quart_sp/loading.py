import time

from quart import Blueprint, redirect, session, url_for, websocket
from typing import List, Tuple

import aiohttp
import asyncio
import auth
import collections
import playlist_helper
import redis_cache
import spotify
import ujson
import util

log = util.setLogger(__name__)
loading_route = Blueprint('loading_route', __name__)


@loading_route.websocket("/load")
async def load_songs_counts():
    access_token = await websocket.receive()
    log.debug("access_token: ", access_token)
    # TODO: Authentication quart-auth ?

    try:
        sp = spotify.Spotify(access_token)
        async with aiohttp.ClientSession(json_serialize=ujson) as sess:
            tracks = await sp.current_user_saved_tracks(50, 0, sess)
            # total = result['total']  # TODO: Testing, currently capping at 100
            total = 100
            log.info(f"User has a total of {total} tracks")
            count = 0

            # track_artist = { track_id : [artist_id] }
            # track_album = [ [track_id], [album_id] ]
            await extract_tracks(sp, sess, tracks)
            artist_ct, album_ct = 0, 0

            loop = asyncio.get_event_loop()
            asyncio_tasks = []
            # TODO: splice on more than 50
            for offset in range(50, total, 50):
                tracks = await sp.current_user_saved_tracks(50, offset, sess)
                #print("TRACKZZZ", tracks)
                asyncio_tasks.append(loop.create_task(extract_tracks(sp, sess, tracks)))

            res = await asyncio.gather(*asyncio_tasks)
            print(res)
            time.sleep(10)
            #await asyncio.gather(*(
            #    extract_tracks(sp, sess, await sp.current_user_saved_tracks(50, offset, sess))
            #    for offset in range(50, total, 50)))

        # map user's saved tracks to redis
        redis_cache.set_user_genre_track_count(access_token)

        # return await redirect(url_for('spotify_analytics'))


    except asyncio.CancelledError:
        # TODO: Handle disconnect
        log.debug("CLIENT CLOSED")
        print("CLIENT CLOSED")
        raise


async def batch_update_album_genres(sp: spotify.Spotify, sess: aiohttp.ClientSession,
                                    album_track_ids: List[str], album_ids: List[str]):
    """Saves uncached album genres to api redis cache
    and updates user's genre set on redis session cache"""
    genre_map = collections.defaultdict(set)
    user_genres = set()
    albums = await sp.albums(album_ids, sess)

    # if not isinstance(albums, list):
    #    log.debug("Single album response")
    #    albums = [albums]

    # TODO: consider izip
    for track_id, album in zip(album_track_ids, albums):
        try:
            album_genres = album['genres']
        except:
            raise Exception("FAILURE IN ALBUM GET", album)
        if album_genres:
            for genre in album_genres:
                genre_map[genre].add(track_id)
                user_genres.add(genre)
            # save album genres to redis
            redis_cache.set_spotify_album_genres(track_id, album_genres)

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
                                     track_ids: List[str], artist_ids: List[str]) -> bool:
    """Saves uncached artist genres to api redis cache
    and updates user's genre set on redis session cache"""

    genre_map = collections.defaultdict(set)
    artists = await sp.artists(artist_ids, sess)
    user_genres = set()
    print("ARTIST IDS:", artist_ids)
    print("ARTISTS: ", artists)
    print("ARTIST IDS LEN: ", len(artist_ids))

    # if not isinstance(artists, list):
    #    log.debug("single artist response")
    #    artists = [artists]

    for track_id, artist in zip(track_ids, artists):
        print(artist)
        try:
            artist_genres = artist['genres']
        except:
            raise Exception("FAILURE IN ARTIST GET", artists)
        print("ARTIST_GENRES:", artist_genres)
        if artist_genres:
            for genre in artist_genres:
                genre_map[genre].add(track_id[0])
                user_genres.add(genre)
            # save track genres to redis
            redis_cache.set_spotify_track_genres(track_id, artist_genres)
        else:
            print("NO ARTIST GENRES")

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

    for track in tracks:
        track_obj = track['track']

        # emit to front end loading page
        print("SONG NAME: ", track_obj['name'])
        await websocket.send(track_obj['name'])
        # TODO: fix count with asyncio atomic values
        # await websocket.send(str(count))

        # save track to redis and form genre map
        if not redis_cache.exists(track_obj['id']):
            await playlist_helper.liked_songs_genre_map(track)

        artist_genres = redis_cache.get_spotify_track_genres(track_obj['id'])
        if not artist_genres:
            # artist genres update to redis
            for artist in track_obj['artists']:
                if artist['id']:
                    artist_track_ids.append(track_obj['id'])
                    artist_ids.append(artist['id'])

                # batch update genre map (API rate limit)
                if len(artist_track_ids) == 49 and len(artist_ids) == 49:
                    # save track genres to redis and update user GTC
                    batch_copy_tid = artist_track_ids[:]
                    batch_copy_aid = artist_ids[:]
                    print("BATCH SENDING ARTISTS", batch_copy_aid)
                    print("LEN OF BATCH ARTISTS", len(batch_copy_aid))
                    await batch_update_artist_genres(sp, sess, batch_copy_tid,
                                                     batch_copy_aid)
                    artist_track_ids.clear()
                    artist_ids.clear()
                elif len(artist_track_ids) != len(artist_ids):
                    # TODO: exception handling
                    raise Exception("Something bad happened")
        else:
            for genre in artist_genres:
                genres_cached[genre].add(track_obj['id'])
                genre_set.add(genre)

        album_genres = redis_cache.get_spotify_album_genres(track_obj['id'])
        if not album_genres:
            # album genres update to redis
            album_track_ids.append(track_obj['id'])
            album_ids.append(track_obj['album']['id'])
        else:
            for genre in album_genres:
                genres_cached[genre].add(track_obj['id'])
                genre_set.add(genre)

    token = await sp.get_access_token()

    # TODO: currently batch calling remaining amount (less than 50), possibly return to caller or
    #  queue on redis
    if len(artist_track_ids) != 0 and len(artist_ids) != 0:
        await batch_update_artist_genres(sp, sess, artist_track_ids, artist_ids)

    # TODO: currently batch calling remaining amount (less than 50 with cache), possibly return
    #  to caller or queue on redis
    #await batch_update_album_genres(sp, sess, album_track_ids, album_ids)

    # update user genre track list
    if genres_cached:
        # save { "token+genre" : [track_id] } to redis
        redis_cache.set_user_genre_tracks(token, genres_cached)
        # save user genres to redis
        genre_set.update(genres_cached.keys())
    # update users genres
    if genre_set:
        redis_cache.set_user_genres(token, genre_set)

    return "ASYNCIO EXTRACT RETURNED THIS"


# DEPRECATED
@loading_route.route('/loading', methods=['POST', 'GET'])
async def load_songs_from_spotify():
    """

    :return: redirect to home page
    """
    print("DEPRECATED")
    return await redirect(url_for('spotify_analytics'))
