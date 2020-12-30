import aiohttp
import asyncio

import ujson

async def main():
    user_id = "1223102973"

    async with aiohttp.ClientSession() as session:
        async with session.post(f'https://api.spotify.com/v1/users/{user_id}/playlists', headers={
            'Authorization': f"Bearer BQBIZimrm6JlKhsxpGoVdIqEHv2GXxl8-pZVTDU6rgY_oN4GEoci8VUP43k_tNldk_6ZjvkW4UPn36MkqX9rTxkzxEdsAgqYIQ8TsHfv1KCDUNERysRb07MVTNTZXM1YI94zsuqcmr_cDq69oUAduucumU53weHub6wCShEKCNF4q9YrQgv9MGqJQ0lqKSsYA_2NP7ueJ2bJSq9j-_G1BuFqjVRB-76AkLJpAIGbUckJn9fv8Xwdy4phEVI"},
                                # 'Content-Type': 'application/json'},
                                data=ujson.dumps({'name': "lol", 'public': True,
                                        'description': 'test'})) as response:
            print("Status:", response.status)
            print("Content-type:", response.headers['content-type'])

            html = await response.json()
            print("Body:", html)
            print(response.url)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
