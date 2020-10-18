import redis
import time

# TODO: ENV host
client = redis.Redis(host='localhost', port=6379)


# adds user, hset value to expiry
def add_user(access_token, expires_in) -> None:
    TTL = expires_in + time.time()
    client.hset(str(access_token), TTL)
    client.expire(expires_in)


def user_exists(access_token) -> bool:
    return bool(client.exists(str(access_token)))


def user_map_exists(access_token) -> bool:
    return user_exists(access_token) and bool(client.exists(str(access_token)+"genre"))
