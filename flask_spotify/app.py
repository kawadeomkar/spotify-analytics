from flask import Flask, redirect, render_template, request, session, url_for

import auth
import json
import logging
import os
import playlist_genre_map
import spotipy
import time


app = Flask(__name__)
app.secret_key = os.environ["WSGI_SECRET_KEY"]
Spotify = None

@app.route('/')
def SpotifyAnalytics():
	if 'access_token' not in session or session.get('expires_in', 0) < int(time.time()):
		scope = "user-library-read playlist-modify-public user-top-read"
		spotify_auth_redir = (
				f"""{os.environ["AUTH_URL"]}"""
				f"""client_id={os.environ["SPOTIPY_CLIENT_ID"]}"""
				f"""&response_type=code"""
				f"""&redirect_uri={os.environ["SPOTIPY_REDIRECT_URI"]}"""
				f"""&scope={scope}"""
			)
		logging.info("302 REDIRECT / : ", spotify_auth_redir)
		return redirect(spotify_auth_redir)

	Spotify = spotipy.Spotify(auth=session['access_token'])
	if session.get('genre_map', None) == None:
		print('genre_map not in session')
		tracks = playlist_genre_map.likedSongsGenreMap(Spotify)
		genre_objs = [{'Name':k, 'Count':len(v)} for k, v in tracks.items()]
		session['genre_map'] = genre_objs
		session['genre_index'] = tracks
	genre_counts = {
		"children":session['genre_map']
	}  
	print(genre_counts)
	
	return render_template('playlist_generator_grid.html', 
		page_title='Spotify Analytics - Playlist Generator',
		genre_counts=genre_counts)

@app.route('/callback/')
def callback():
	auth_details = auth.getSpotifyAuthToken(request.args.get('code'))

	session['access_token'] = auth_details['access_token']
	session['expires_in'] = auth_details['expires_in'] + int(time.time())
	return redirect(url_for('SpotifyAnalytics'))

@app.route('/playlist', methods=['POST'])
def playlist():
	Spotify = spotipy.Spotify(auth=session["access_token"])
	genre = request.get_json()['Name']
	print(session.items())
	print('SONGS BABY')
	songs = session['genre_map'][session['genre_index'][genre]] #[genre]]['Songs']
	print(songs)
	
	return render_template('playlist.html', songs=songs, genre=genre) 


@app.route('/export', methods=['POST'])
def export():
	genre = request.form['export']
	pass
	
