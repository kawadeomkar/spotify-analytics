from quart import redirect, request, session, url_for
from quart_sp import app
from typing import Dict, Union

import aiohttp
import asyncio
import base64
import os
import redis_cache
import ujson
import util

log = util.setLogger(__name__)


@app.route('/callback/')
async def callback():
    auth_details = getSpotifyAuthToken(request.args.get('code'))
    access_token, expires_in = auth_details['access_token'], auth_details['expires_in']

    # add user to redis cache
    redis_cache.add_user(access_token, expires_in)
    session['access_token'] = access_token
    session['expires_in'] = expires_in

    return await redirect(url_for('spotify_analytics'))


async def getSpotifyAuthToken(code) -> Dict:
    body = {
        "grant_type": 'authorization_code',
        "code": code,
        "redirect_uri": os.environ["SPOTIPY_REDIRECT_URI"],
        "client_id": os.environ["SPOTIPY_CLIENT_ID"],
        "client_secret": os.environ["SPOTIPY_CLIENT_ID"]
    }

    encoded = base64.b64encode(
        (
            f"""{os.environ["SPOTIPY_CLIENT_ID"]}:"""
            f"""{os.environ["SPOTIPY_CLIENT_SECRET"]}"""
        ).encode('utf-8')).decode('utf-8')

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded}"
    }

    post = requests.post(os.environ["AUTH_TOKEN"], params=body, headers=headers)
    if post.status_code != 200:
        print(post.status_code, post.text)
        if post.status_code == 400:
            # TODO: handle invalid auth code error
            print("400: AUTH TOKEN EXPIRED")
            raise Exception
        raise Exception
    return json.loads(post.text)


async def authenticationRedirectURL(scope: str = None) -> str:
    if not scope:
        scope = "user-library-read playlist-modify-public playlist-modify-private user-top-read " \
                "streaming user-read-email user-read-private user-read-playback-state"
    return (
        f"""{os.environ["AUTH_URL"]}"""
        f"""client_id={os.environ["SPOTIPY_CLIENT_ID"]}"""
        f"""&response_type=code"""
        f"""&redirect_uri={os.environ["SPOTIPY_REDIRECT_URI"]}"""
        f"""&scope={scope}"""
    )


def validateAccessToken() -> Union[str, None]:
    if 'access_token' not in session or not redis_cache.user_exists(session['access_token']):
        spotify_auth_redir = authenticationRedirectURL()
        log.info(f"302 REDIRECT, User needs to authenticate, redirect: {spotify_auth_redir}")
        return spotify_auth_redir


# TODO: implement
def refresh_token():
    pass