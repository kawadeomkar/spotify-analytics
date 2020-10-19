import redis
from flask import Flask, redirect, render_template, request, session, url_for

import auth
import json
import logging
import os
import playlist_genre_map
import redis_cache
import spotipy
import util
import time

app = Flask(__name__)
app.secret_key = os.environ['WSGI_SECRET_KEY']

log = util.setLogger(__name__)


@app.route('/')
def spotify_analytics():
    if not redis_cache.ping():
        print("CANT CONNECT TO REDIS")

    if 'access_token' not in session or not redis_cache.user_exists(session['access_token']):
        spotify_auth_redir = auth.authenticationRedirectURL()
        log.info(f"302 REDIRECT, User needs to authenticate, redirect: {spotify_auth_redir}")
        return redirect(spotify_auth_redir)

    access_token = session['access_token']
    spotify = spotipy.Spotify(auth=access_token)
    # user_id = spotify.current_user()['id']

    # mapping needed for d3.js
    genre_map_d3 = {}

    if not redis_cache.user_map_exists(access_token):
        log.info('Genre map not found in redis cache, querying Spotify API')

        genre_track_map = playlist_genre_map.likedSongsGenreMap(spotify)

        log.info("USER MAP", genre_track_map)
        # map user's saved tracks to redis
        redis_cache.set_user_genres(access_token, genre_track_map.keys())
        redis_cache.set_user_genre_tracks(access_token, genre_track_map)
        redis_cache.set_user_genre_track_count(access_token, genre_track_map)

        genre_map_d3 = [{'Name': genre, 'Count': len(tracks)}
                        for genre, tracks in genre_track_map.items()]
    else:
        # load from redis
        genre_map_raw = redis_cache.get_user_genre_track_count(access_token)
        genre_map_d3 = [{'Name': genre, 'Count': int(tracks)}
                        for genre, tracks in genre_map_raw.items()]

    genre_counts = {
        "children": genre_map_d3
    }

    return render_template('playlist_generator_grid.html',
                           page_title='Spotify Analytics - Playlist Generator',
                           genre_counts=genre_counts)


@app.route('/callback/')
def callback():
    auth_details = auth.getSpotifyAuthToken(request.args.get('code'))
    access_token, expires_in = auth_details['access_token'], auth_details['expires_in']

    # add user to redis cache
    redis_cache.add_user(access_token, expires_in)
    session['access_token'] = access_token
    session['expires_in'] = expires_in

    return redirect(url_for('spotify_analytics'))


@app.route('/playlist', methods=['POST'])
def playlist():
    spotify = spotipy.Spotify(auth=session["access_token"])
    genre = request.get_json()['Name']

    songs = session['genre_map'][session['genre_index'][genre]]  # [genre]]['Songs']

    return render_template('playlist.html', songs=songs, genre=genre)


@app.route('/export', methods=['POST'])
def export():
    genre = request.form['export']
    pass
