from flask import Flask, redirect, render_template, request, session, url_for

import auth
import json
import os
import player
import playlist_helper
import redis_cache
import spotipy
import util

app = Flask(__name__)
app.secret_key = os.environ['WSGI_SECRET_KEY']

log = util.setLogger(__name__)


@app.route('/')
def spotify_analytics():
    if not redis_cache.ping():  # TODO: remove after done with testing
        print("CANT CONNECT TO REDIS")

    validate = auth.validateAccessToken()
    if validate:
        return redirect(validate)

    access_token = session['access_token']
    log.info(f"Access token: {access_token}")
    spotify = spotipy.Spotify(auth=access_token)
    # user_id = spotify.current_user()['id']

    if not redis_cache.user_map_exists(access_token):
        log.info('Genre map not found in redis cache, querying Spotify API')

        genre_track_map = playlist_helper.liked_songs_genre_map(spotify)

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

    return render_template('playlist_generator_bubbles.html',
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
