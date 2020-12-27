from quart import Blueprint, redirect, session, url_for, websocket
from typing import List

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

            # create genre map to save to redis
            genre_map = collections.defaultdict(set)

            # track_artist = { track_id : [artist_id] }
            # track_album = [ [track_id], [album_id] ]
            track_artist, track_album, artist_count, album_count = await extract_tracks(sp, sess,
                                                                                        genre_map,
                                                                                        tracks,
                                                                                        count)
            artist_ct, album_ct = 0, 0

            # TODO: splice on more than 50
            for offset in range(50, total, 50):

                # batch update genre map (API rate limit)
                # artist update
                if artist_count + artist_ct > 50:
                    batch_genre_map = await batch_update_artist_genres(sp, sess, track_artist)
                    # TODO: batch update on users GTC on redis
                    for genre, a_ids in batch_genre_map.items():
                        genre_map[genre].update(a_ids)
                    track_artist = {}
                    artist_ct = 0

                track_artist = track_artist | t_artist

                # album update (50 per call / loop)
                track_album = t_album
                batch_genre_map = await batch_update_album_genres(sp, sess, track_album)

                artist_count += artist_ct
                album_count += album_ct

                tracks = await sp.current_user_saved_tracks(50, offset, sess)
                t_artist, t_album, artist_ct, album_ct = await extract_tracks(sp, sess, genre_map,
                                                                              tracks,
                                                                              count)

        # map user's saved tracks to redis
        redis_cache.set_user_genres(access_token, genre_map.keys())
        redis_cache.set_user_genre_tracks(access_token, genre_map)
        redis_cache.set_user_genre_track_count(access_token, genre_map)

        return await redirect(url_for('spotify_analytics'))
    except asyncio.CancelledError:
        # TODO: Handle disconnect
        log.debug("CLIENT CLOSED")
        print("CLIENT CLOSED")
        raise


async def batch_update_album_genres(sp: spotify.Spotify, sess: aiohttp.ClientSession,
                                    track_id_map: List[List, List]):
    genre_map = collections.defaultdict(set)

    resp = await sp.albums(track_id_map[1], sess)
    if isinstance(resp, list):
        # TODO: consider izip
        for track_id, album in zip(resp):
            album_genres = album['genres']
            if len(album_genres) != 0:
                for genre in album_genres:
                    genre_map[genre].add(track_id)

    return genre_map




async def batch_update_artist_genres(sp: spotify.Spotify, sess: aiohttp.ClientSession,
                                     track_id_map):
    genre_map = collections.defaultdict(set)

    batch_artist_ids = []
    artist_intervals = []
    track_ids = []

    for track_id, artist_ids in track_id_map.items():
        artist_intervals.append(len(artist_ids))
        batch_artist_ids.extend(artist_ids)
        track_ids.append(track_id)

    resp = await sp.artists(batch_artist_ids, sess)
    if isinstance(resp, list):
        int_idx, int_ct, track_idx = 0, 0, 0
        genre_set = set()

        for artist in resp:
            if int_ct == artist_intervals[int_idx]:
                int_ct = 0
                int_idx += 1
                track_idx += 1
                for genre in genre_set:
                    genre_map[genre].add(track_ids[track_idx])
                genre_set.clear()

            artist_genres = artist['genres']
            if len(artist_genres) != 0:
                genre_set.update(artist['genres'])

            int_ct += 1
    elif isinstance(resp, dict):
        raise Exception("TODO")

    return genre_map


# TODO: optimize this poorly written code
async def extract_tracks(sp: spotify.Spotify, sess: aiohttp.ClientSession, genre_map,
                         tracks: List, count: int):
    track_artist = {}  # { track_id : [artist_id] }
    track_ids, track_album = [], []  # [track_id], [album_id]
    artist_ct, album_ct = 0, 0
    for track in tracks:
        track_obj = track['track']

        # emit to front end loading page
        print("SONG NAME: ", track_obj['name'])
        await websocket.send(track_obj['name'])
        count += 1
        await websocket.send(str(count))

        # save track to redis and form genre map
        artist_ids, album_id = await playlist_helper.liked_songs_genre_map(sp, sess, genre_map,
                                                                           track)
        track_artist[track_obj['id']] = artist_ids
        track_album.append(album_id)
        track_ids.append(track_obj['id'])
        artist_ct += len(artist_ids)
        album_ct += 1

    return track_artist, [track_ids, track_album], artist_ct, album_ct


# DEPRECATED
@loading_route.route('/loading', methods=['POST', 'GET'])
async def load_songs_from_spotify():
    """

    :return: redirect to home page
    """
    print("DEPRECATED")
    return await redirect(url_for('spotify_analytics'))
