from itertools import chain

from flask import Flask, redirect, render_template, request, session, url_for
from flask_socketio import SocketIO, send, emit
from typing import List

import auth
import json
import loading
import os
import player
import playlist_helper
import redis_cache
import spotipy
import traceback
import util

# TODO: server setup with TLS
app = Flask(__name__)
app.secret_key = os.environ['WSGI_SECRET_KEY']

# logging
log = util.setLogger(__name__)

socketio = SocketIO(app, cors_allowed_origins='*', logger=True, engineio_logger=True)


@socketio.on('loading_song_count')
def load_songs_counts(song_count: str):
    emit('loading_song_count', song_count)


@socketio.on('loading_song_titles')
def load_songs(song_title: str):
    emit('loading_song_titles', song_title)


def extract_tracks(spotify: spotipy.client, genre_map, tracks: List, count: int):
    for track in tracks:
        track_obj = track['track']

        # emit to front end loading page
        print("SONG NAME: ", track_obj['name'])
        socketio.emit("loading_song_titles", track_obj['name'])
        count += 1
        socketio.emit("loading_song_count", str(count))

        # save track to redis and form genre map
        playlist_helper.liked_songs_genre_map(spotify, genre_map, track)


@app.route('/loading', methods=['POST', 'GET'])
def load_songs_from_spotify():
    """

    :return: redirect to home page
    """
    print("loading")
    access_token = session['access_token']
    spotify = spotipy.Spotify(auth=access_token)

    result = spotify.current_user_saved_tracks(limit=50, offset=0)
    tracks = result['items']
    # total = result['total']  # TODO: Testing, currently capping at 100
    total = 100
    log.info(f"User has a total of {total} tracks")
    count = 0

    # create genre map to save to redis
    genre_map = {}
    extract_tracks(spotify, genre_map, tracks, count)

    for size in range(50, total, 50):
        tracks = spotify.current_user_saved_tracks(limit=50, offset=size)['items']
        extract_tracks(spotify, genre_map, tracks, count)

    # map user's saved tracks to redis
    redis_cache.set_user_genres(access_token, genre_map.keys())
    redis_cache.set_user_genre_tracks(access_token, genre_map)
    redis_cache.set_user_genre_track_count(access_token, genre_map)

    return redirect(url_for('spotify_analytics'))


@app.route('/', methods=['POST', 'GET'])
def spotify_analytics():
    if not redis_cache.ping():  # TODO: remove after done with testing
        print("CANT CONNECT TO REDIS")

    validate = auth.validateAccessToken()
    if validate:
        return redirect(validate)

    access_token = session['access_token']
    log.info(f"Access token: {access_token}")

    if not redis_cache.user_map_exists(access_token):
        log.info('Genre map not found in redis cache, querying Spotify API')

        return render_template('loading.html',
                               page_title="Loading songs")
    else:
        # load from redis
        genre_map_raw = redis_cache.get_user_genre_track_count(access_token)
        genre_map_d3 = [{'Name': genre, 'Count': int(tracks)}
                        for genre, tracks in genre_map_raw.items()]
        return render_template('playlist_generator_bubbles.html',
                               page_title='Spotify Analytics - Playlist Generator',
                               genre_counts={"children": genre_map_d3})


@app.route('/callback/')
def callback():
    auth_details = auth.getSpotifyAuthToken(request.args.get('code'))
    access_token, expires_in = auth_details['access_token'], auth_details['expires_in']

    # add user to redis cache
    redis_cache.add_user(access_token, expires_in)
    session['access_token'] = access_token
    session['expires_in'] = expires_in

    return redirect(url_for('spotify_analytics'))


@app.route('/playlist/<string:genre>')
def playlist(genre):
    validate = auth.validateAccessToken()
    if validate:
        return redirect(validate)

    access_token = session['access_token']
    songs = redis_cache.get_user_genre_tracks(access_token, genre)
    song_info_map = [redis_cache.get_spotify_track_name(t_id) for t_id in songs]
    sorted_song_info_map = sorted(song_info_map,
                                  key=lambda song: int(song['popularity']),
                                  reverse=True)

    spotify = spotipy.Spotify(auth=access_token)
    d_id, devices = player.get_device_info(spotify)

    # extract artists back to strings
    for song in sorted_song_info_map:
        song['artists'] = ', '.join(json.loads(song['artists']))

    return render_template('playlist_list.html', song_info_map=sorted_song_info_map, genre=genre,
                           access_token=access_token, d_id=d_id, devices=devices)


@app.route('/export', methods=['POST'])
def export():
    # TODO: Implement JS logic to issue error
    validate = auth.validateAccessToken()
    if validate:
        return redirect(validate)

    genre = request.get_json()['genre']
    access_token = session['access_token']
    spotify = spotipy.Spotify(auth=access_token)

    # TODO: User sets the genre name
    playlist_id = playlist_helper.create_playlist(spotify, genre)
    genres_to_export = redis_cache.get_user_genre_tracks(access_token, genre)
    # TODO: retry logic in this function? display error if false
    ret = playlist_helper.add_tracks_to_playlist(spotify, playlist_id, genres_to_export)

    return genre


@app.route('/play/<string:uri>')
def play(uri):
    pass

# # TODO: handle 500 ISE
# @app.errorhandler(500)
# def internal_error(e):
#     """
#     handle internal errors nicely
#     """
#     tb = traceback.format_exc()
#     return render_template('error.html',
#                            error=e,
#                            traceback=tb), 500
