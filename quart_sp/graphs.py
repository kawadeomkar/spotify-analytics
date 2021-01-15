from quart import Blueprint
from typing import Dict, List, Tuple, Union

import aiohttp
import redis_cache
import spotify
import ujson
import uti

log = util.setLogger(__name__)
player_route = Blueprint('graphs_route', __name__)


@graphs_route.route('/graphs')
async def graphs():

