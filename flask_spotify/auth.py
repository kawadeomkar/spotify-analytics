from flask import session
from typing import Union

import base64
import json
import os
import redis_cache
import requests
import util

log = util.setLogger(__name__)


def getSpotifyAuthToken(code) -> json:
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


def authenticationRedirectURL(scope: str = None) -> str:
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


def refresh_token():
    pass

