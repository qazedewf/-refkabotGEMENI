import aiohttp
from config import BOTOHUB_API_KEY, BOTOHUB_API_URL

async def get_botohub_sponsors(user_id: int):
    headers = {"Authorization": f"Bearer {BOTOHUB_API_KEY}"}
    params = {"user_id": user_id, "min_payout_rub": 5.0}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BOTOHUB_API_URL}/get_tasks", headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("tasks", [])
    except Exception as e:
        print(f"Botohub API Error: {e}")
    return []