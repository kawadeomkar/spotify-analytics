# Liked songs library grouped by genre 
from functools import lru_cache
from itertools import chain

import json
import spotipy


@lru_cache(maxsize=100)
def getArtistGenres(spotify, artist_id):
	res = spotify.artist(artist_id)
	print(artist_id, res)
	print(res['genres'])
	return res['genres']

def likedSongsGenreMap(spotify):
	result = spotify.current_user_saved_tracks(limit=50, offset=0)
	tracks = result['items']
	total = result['total']
	
	if total > 50:
		rest = list(map(
			lambda x: (spotify.current_user_saved_tracks(limit=50, offset=x)['items']),
			list(range(50, total, 50))
		))
		rest = list(chain.from_iterable(rest))
		tracks.extend(rest)	
	
	genre_map = {}
	for track in tracks:
		track = track['track']
		for genre in getArtistGenres(spotify, track['artists'][0]['id']):	
			if not genre in genre_map:
				genre_map[genre] = []
			genre_map[genre].append(track['id'])
	return genre_map
	
	
	
	
	
