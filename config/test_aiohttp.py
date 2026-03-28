import aiohttp
import asyncio

async def main():
    print("Testing aiohttp with default connector...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://eha-cloud.doh.hawaii.gov/cwb/api/json/reply/GetEvents") as response:
                print(f"Status: {response.status}")
                data = await response.json()
                print(f"Data length: {len(data.get('list', []))}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
