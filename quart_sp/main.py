from itertools import chain
from quart import Quart, redirect, render_template, request, session, url_for, websocket
from typing import List

import aiohttp
import asyncio
import os
import redis_cache
import spotify
import traceback
import ujson
import util

# import routes
import auth
import loading
import player
import playlist_helper

app = Quart(__name__)
app.register_blueprint(auth.auth_route)
app.register_blueprint(loading.loading_route)
app.register_blueprint(player.player_route)
app.register_blueprint(playlist_helper.playlist_route)

app.secret_key = os.environ['WSGI_SECRET_KEY']

# TODO: server setup with TLS


# logging
log = util.setLogger(__name__)


# TODO: remove flask-socketio
# socketio = SocketIO(app, cors_allowed_origins='*', logger=True, engineio_logger=True)


@app.route('/', methods=['POST', 'GET'])
async def spotify_analytics():
    if not redis_cache.ping():  # TODO: remove after done with testing
        print("CANT CONNECT TO REDIS")

    validate = auth.validateAccessToken()
    if validate:
        return redirect(validate)

    access_token = session['access_token']
    log.info(f"Access token: {access_token}")

    if not redis_cache.user_map_exists(access_token):
        log.info('Genre map not found in redis cache, querying Spotify API')

        return await render_template('loading.html',
                                     page_title="Loading songs",
                                     access_token=access_token)
    else:
        # load from redis
        genre_map_raw = redis_cache.get_user_genre_track_count(access_token)
        genre_map_d3 = [{'Name': genre, 'Count': int(tracks)}
                        for genre, tracks in genre_map_raw.items()]
        return await render_template('playlist_generator_bubbles.html',
                                     page_title='Spotify Analytics - Playlist Generator',
                                     genre_counts={"children": genre_map_d3})

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
