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
    if 'access_token' not in session or session.get('expires_in', 0) < int(time.time()):
        scope = "user-library-read playlist-modify-public user-top-read"
        spotify_auth_redir = (
            f"""{os.environ["AUTH_URL"]}"""
            f"""client_id={os.environ["SPOTIPY_CLIENT_ID"]}"""
            f"""&response_type=code"""
            f"""&redirect_uri={os.environ["SPOTIPY_REDIRECT_URI"]}"""
            f"""&scope={scope}"""
        )
        log.info("302 REDIRECT / : ", spotify_auth_redir)
        return redirect(spotify_auth_redir)

    spotify = spotipy.Spotify(auth=session['access_token'])
    # user_id = spotify.current_user()['id']

    if not redis_cache.user_map_exists():
        log.info('Genre map not found in redis cache, querying Spotify API')

        tracks = playlist_genre_map.likedSongsGenreMap(spotify)
        genre_objs = [{'Name': k, 'Count': len(v)} for k, v in tracks.items()]
        session['genre_map'] = genre_objs
        session['genre_index'] = tracks

    genre_counts = {
        "children": session['genre_map']
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
