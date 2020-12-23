from functools import lru_cache
from typing import Any, Dict, List, Union

import aiohttp
import asyncio
import util

log = util.setLogger(__name__)


class Spotify:
    endpoint_prefix = "https://api.spotify.com/"

    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.user_id = None

    async def http_call(self,
                        endpoint_route: str,
                        session: aiohttp.ClientSession,
                        params: Dict[str, Union[str, int]] = None,
                        http_method='GET'):
        async with session.request(http_method,
                                   self.endpoint_prefix + endpoint_route,
                                   headers={'Authorization': f"Bearer {self.auth_token}",
                                            'Content-Type': 'application/json'},
                                   params=params) as resp:
            if resp.status == 200 or resp.status == 201:
                data = await resp.json()
                return data

    async def get_user_id(self, session: aiohttp.ClientSession) -> str:
        """
        Returns user's spotify ID
        """
        if self.user_id is not None:
            return self.user_id

        endpoint_route = "v1/me"
        resp = await self.http_call(endpoint_route, session)
        self.user_id = resp['id']
        return self.user_id

    async def current_user_saved_tracks(self, limit: int, offset: int,
                                        session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """
        Returns saved tracks from the user's library

        limit: number of desired tracks (max=50)
        offset: offset of saved library to start from
        """
        endpoint_route = "v1/me/tracks"
        resp = await self.http_call(endpoint_route, session,
                                    params={'limit': limit, 'offset': offset})
        return resp['items']

    async def create_playlist(self, user_id: str,
                              name: str,
                              session: aiohttp.ClientSession,
                              public: bool = True,
                              description: str = 'This playlist was curated by SpotifyAnalytics '
                                                 'https://github.com/kawadeomkar/spotify-analytics') -> str:
        """
        Creates a playlist, returns id of playlist upon creation
        """
        endpoint_route = f"v1/users/{user_id}/playlists"
        resp = await self.http_call(endpoint_route,
                                    session,
                                    params={'name': name, 'public': public,
                                            'description': description},
                                    http_method='POST')
        return resp['id']

    async def add_items_to_playlist(self, playlist_id: str,
                                    tracks: List[str],
                                    session: aiohttp.ClientSession):
        """
        Add items to a playlist, returns snapshot id (used to identify playlist version)
        """
        endpoint_route = f"v1/playlists/{playlist_id}/tracks"
        resp = await self.http_call(endpoint_route, session, params={'uris': tracks},
                                    http_method='POST')
        return resp['snapshot_id']

    @lru_cache(maxsize=None)
    async def artists(self, ids: Union[List, str], session: aiohttp.ClientSession):
        """
        Returns artist(s) information

        ids: List of artist IDs or single artist ID
        """
        endpoint_route = "v1/artists"
        if isinstance(ids, str):
            ids = [ids]
        resp = await self.http_call(endpoint_route, session, params={'ids': ids})
        return resp['artists']

    @lru_cache(maxsize=None)
    async def albums(self, ids: Union[List, str], session: aiohttp.ClientSession):
        """
        Returns album(s) information

        ids: List of album IDs or single album ID
        """
        endpoint_route = "v1/albums"
        if isinstance(ids, str):
            ids = [ids]
        resp = await self.http_call(endpoint_route, session, params={'ids': ids})
        return resp['albums']

    async def get_devices(self, session: aiohttp.ClientSession):
        """
        Returns active devices
        """
        endpoint_route = "v1/me/player/devices"
        resp = await self.http_call(endpoint_route, session)
        return resp['devices']

    async def play_song(self, session: aiohttp.ClientSession,
                        context_uri: str = None,
                        uris: List[str] = None,
                        offset: Dict[str, Union[str, int]] = None,
                        position_ms=None):

        """
        Plays a song if uris is provided, otherwise plays context_uri if provided and then returns
        true. Otherwise returns false

        offset: plays uri with offset - applies only to albums and playlist
        """
        endpoint_route = "v1/me/player/play"
        params = {}

        if offset:
            params['offset'] = offset
        if position_ms:
            params['position_ms'] = position_ms
        if uris:
            params['uris'] = uris
        elif context_uri:
            params['context_uri'] = context_uri

        resp = await self.http_call(endpoint_route, session, params=params, http_method='PUT')

        if resp is None:
            return True
        else:
            log.error(resp)
            return False
