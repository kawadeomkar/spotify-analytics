import aiohttp
import asyncio

async def main():

    async with aiohttp.ClientSession() as session:
        async with session.get('https://api.spotify.com/v1/artists', headers={'Authorization': f"Bearer BQD_rYDXD0GZBz-YWm_M9ff2Ci5gOKRXUcW1BUbx7qoMBRTsxLe4VUGUOw_mbW6bsVFCZu9sTVQ17SbF6aNdGjPaXlm1DMe2fxrXBLFQlaGGqym-ioYf1Qb90GH_xJ_Dz46OIaPdyozb2wGc85-2H0z7_TWfLfOmZ3dYcbJVrXXzhNaziVKWimmLA8la1SyccmbkIUMGP13aw2b62TIT4CzD-d2UGwNPiy7BVutTAV0lyVYfnaA"},
                                   # 'Content-Type': 'application/json'},
                                   params={'ids':','.join(['73YFrf7gXIkvp3pxaqtOpZ', '3r1XkJ7vCs8kHBSzGvPLdP', '5Q81rlcTFh3k6DQJXPdsot', '1PAn2z7cLcCoRWdGpUU7Qb', '5fAix5NwfNgHQqYRrHIPxo', '1Q2WlUWRQZVxpBBO4UHRV5', '5cj0lLjcoR7YOSnhnX0Po5', '5HFSWl4JPwju06kHxukvTe', '5fAix5NwfNgHQqYRrHIPxo', '5fAix5NwfNgHQqYRrHIPxo', '7FqhC9JMS6bbcfMVKKPHBc', '7GuUYiGZOzQwq4L6gAfy1T', '37hAfseJWi0G3Scife12Il', '5cj0lLjcoR7YOSnhnX0Po5', '6OqhFYFJDnBBHas02HopPT', '4QUvpcWdhkN0qFJ1e77cTr', '76qNU3B5etz1hVVRU7k8eT', '1nVq0hKIVReeaiB3xJgKf0', '3xFXCUS8RN65oCwsO4PJRI', '6PfSUFtkMVoDkx4MQkzOi3', '25uiPmTg16RbhZWAqwLBy5', '2OaHYHb2XcFPvqL3VsyPzU', '6OqhFYFJDnBBHas02HopPT', '6yby1ACnfwVigbSSaH3kEQ', '0u2qphtOdF2T2YWmi74O0P', '4bQCZKbtYa0W0hzA7JrpC4', '5XE0fiZWGbq9TcSuWwJ1fA', '6PfSUFtkMVoDkx4MQkzOi3', '4UXqAaa6dQYAk18Lv7PEgX', '5aYf0AInMznHfXGaemKEBv', '0MfC3pip8rY8OFLJVVNvBO', '6PfSUFtkMVoDkx4MQkzOi3', '3sklFG9fuDAq3vbIZlkNH6', '2Cm6C9PNHioyjRKBfO7n9N', '3RIgMUtdfRx98Lm5bXM3GD', '6CTStccOisUTgXVrtCIANm', '7rGbODPTIVjzn3CTR6RCzE', '6gK1Uct5FEdaUWRWpU4Cl2', '6gK1Uct5FEdaUWRWpU4Cl2', '3I4kM4D2rNnlG8JwEH5bHx', '5kZ3bLambJ4rBTQ7c2pmi5', '5XE0fiZWGbq9TcSuWwJ1fA', '6PfSUFtkMVoDkx4MQkzOi3', '3sklFG9fuDAq3vbIZlkNH6', '2Cm6C9PNHioyjRKBfO7n9N', '6PfSUFtkMVoDkx4MQkzOi3', '3sklFG9fuDAq3vbIZlkNH6', '2Cm6C9PNHioyjRKBfO7n9N', '6PfSUFtkMVoDkx4MQkzOi3', '3sklFG9fuDAq3vbIZlkNH6'])}) as response:

            print("Status:", response.status)
            print("Content-type:", response.headers['content-type'])

            html = await response.json()
            print("Body:", html)
            print(response.url)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())