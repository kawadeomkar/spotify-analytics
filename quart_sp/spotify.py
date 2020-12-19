from typing import List, Union
import aiohttp

class Spotify:

    endpoint = "https://api.spotify.com/"
    
    def __init__(self, auth_token: str):
        self.auth_token = auth_token


    def current_user_saved_tracks(self, limit: int, offset: int):
        """
        docstring
        """
        endp = "v1/me/tracks"
        pass

    
    def create_playlist(self, user_id: str, 
                              name: str, 
                              public: bool = True, 
                              description: str = 'This playlist was curated by SpotifyAnalytics https://github.com/kawadeomkar/spotify-analytics'):
        """
        docstring
        """
        endp = f"v1/users/{user_id}/playlists"
        pass

    def add_items_to_playlist(self, playlist_id: str, tracks: List[str],  position: int = None):
        """
        docstring
        """
        endp = f"v1/playlists/{playlist_id}/tracks"
        pass


    def artists(self, ids: Union[List, str]):
        """
        docstring
        """
        endp = "v1/artists"
        if isinstance(ids, list):
            pass
        elif isinstance(ids, str):
            pass


    def albums(self, ids: Union[List, str]):
        """
        docstring
        """
        endp = "v1/albums"
        if isinstance(ids, list):
            pass
        elif isinstance(ids, str):
            pass
    

    def get_devices(self):
        """
        docstring
        """
        endp = "v1/me/player/devices"
        pass


    def play_song(self, context_uri: str,
                        uris: List[str],
                        offset: Dict[str, Union[str, int]] = None,
                        position_ms=None):
    """
    Plays a song if uris is provided, otherwise plays context_uri if provided and then returns
    true. Otherwise returns false
    """
    if uris is None and context_uri is None:
        return False

    endp = "v1/me/player/play"
    try:
        # uris take priority
        if uris:
            pass
        elif context_uri:
            pass
        return True
    # TODO: aiohttp err fix
    except HTTPError as e:
        log.error(e)
        return False