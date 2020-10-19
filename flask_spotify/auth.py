import base64
import json
import os
import requests


def getSpotifyAuthToken(code):
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
        scope = "user-library-read playlist-modify-public user-top-read"
    return (
            f"""{os.environ["AUTH_URL"]}"""
            f"""client_id={os.environ["SPOTIPY_CLIENT_ID"]}"""
            f"""&response_type=code"""
            f"""&redirect_uri={os.environ["SPOTIPY_REDIRECT_URI"]}"""
            f"""&scope={scope}"""
        )