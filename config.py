import os
import random
import aiohttp
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_TOKEN = os.getenv("USER_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан")
if not USER_TOKEN:
    raise ValueError("USER_TOKEN не задан")

PROXY_USER = "zokylxzq"
PROXY_PASS = "kmiwh1bvbpl5"

PROXY_LIST = [
    "31.59.20.176:6754",
    "45.38.107.97:6014",
    "198.105.121.200:6462",
    "64.137.96.74:6641",
    "198.23.243.226:6361",
    "38.154.185.97:6370",
    "84.247.60.125:6095",
    "142.111.67.146:5611",
    "191.96.254.138:6185",
    "31.58.9.4:6077",
]


async def get_working_proxy() -> tuple[str, aiohttp.BasicAuth] | tuple[None, None]:
    """
    Перебирает прокси в случайном порядке, возвращает первую рабочую.
    """
    auth = aiohttp.BasicAuth(PROXY_USER, PROXY_PASS)
    shuffled = PROXY_LIST.copy()
    random.shuffle(shuffled)

    for host_port in shuffled:
        proxy_url = f"http://{host_port}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://discord.com/api/v10/gateway",
                    proxy=proxy_url,
                    proxy_auth=auth,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    if resp.status == 200:
                        print(f"[Proxy] Рабочая: {host_port}", flush=True)
                        return proxy_url, auth
                    else:
                        print(f"[Proxy] {host_port} → {resp.status}, пропуск", flush=True)
        except Exception as e:
            print(f"[Proxy] {host_port} → ошибка: {e}, пропуск", flush=True)

    print("[Proxy] Все прокси недоступны!", flush=True)
    return None, None
