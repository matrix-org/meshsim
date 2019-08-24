import aiohttp
import async_timeout

async def put(url, data):
    async with aiohttp.ClientSession() as session, async_timeout.timeout(30):
        async with session.put(
            url, data=data, headers={"Content-type": "application/json"}
        ) as response:
            return await response.text()


