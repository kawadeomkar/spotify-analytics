from quart import Blueprint
from typing import Dict, List, Tuple, Union

import aiohttp
import spotify
import ujson
import util

log = util.setLogger(__name__)
player_route = Blueprint('player_route', __name__)


@player_route.route('/play/<string:uri>')
async def play(uri):
    pass


async def play_song(sp: spotify.Spotify,
                    context_uri: str = None,
                    uris: List[str] = None,
                    offset: Dict[str, Union[str, int]] = None,
                    position_ms=None,
                    session: aiohttp.ClientSession = None):
    """ Plays a song if uris is provided, otherwise plays context_uri if provided and then returns
     true. Otherwise returns false"""
    if uris is None and context_uri is None:
        return False
    if not session:
        session = aiohttp.ClientSession(json_serialize=ujson)

    if uris:
        sp.start_playback(session, uris=uris, offset=offset, position_ms=position_ms)
    elif context_uri:
        sp.start_playback(session, context_uri=context_uri, offset=offset, position_ms=position_ms)
    return True


async def get_device_info(sp: spotify.Spotify, session: aiohttp.ClientSession = None) \
        -> Tuple[Union[None, str], Dict]:
    """ Returns tuple of current device in use and dict of devices"""
    if not session:
        session = aiohttp.ClientSession(json_serialize=ujson)

    async with session as sess:
        devices = await sp.get_devices(sess)

    d_id = None

    log.info(devices)

    for device in devices:
        if device['is_active']:
            d_id = device['id']
        del device['is_active']
        del device['is_private_session']
        del device['volume_percent']

    print(f"Current device: {d_id}")
    log.info(devices)

    return d_id, devices
