from requests.exceptions import HTTPError
from typing import Dict, List, Tuple, Union

import spotipy
import util

log = util.setLogger(__name__)


def play_song(spotify: spotipy.client,
              context_uri: str,
              uris: List[str],
              offset: Dict[str, Union[str, int]] = None,
              position_ms=None):
    """ Plays a song if uris is provided, otherwise plays context_uri if provided and then returns
     true. Otherwise returns false"""
    if uris is None and context_uri is None:
        return False
    try:
        # uris take priority
        if uris:
            spotify.start_playback(uris=uris, offset=offset, position_ms=position_ms)
        elif context_uri:
            spotify.start_playback(context_uri=context_uri, offset=offset, position_ms=position_ms)
        return True
    except HTTPError as e:
        log.error(e)
        return False


def get_device_info(spotify: spotipy.client) -> Tuple[Union[None, str], Dict]:
    """ Returns tuple of current device in use and dict of devices"""
    devices = spotify.devices()['devices']
    d_id = None

    log.info(devices)

    for device in devices:
        if device['is_active']:
            d_id = device['id']
        del device['is_active']
        del device['is_private_session']
        del device['volume_percent']

    log.info(d_id)
    log.info(devices)

    return d_id, devices


