import asyncio
import json
import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SELF_BOT_SITE = os.path.join(
    BASE_DIR,
    "selfbot_venv",
    "lib",
    "python3.12",
    "site-packages"
)

if os.path.isdir(SELF_BOT_SITE):
    sys.path.insert(0, SELF_BOT_SITE)
    print(f"[Selfbot] selfbot_venv найден: {SELF_BOT_SITE}", flush=True)
else:
    print(f"[Selfbot] ВНИМАНИЕ: selfbot_venv не найден по пути {SELF_BOT_SITE}", flush=True)

import aiohttp
import discord

print(f"[Selfbot] discord из: {discord.__file__}", flush=True)
print(f"[Selfbot] discord версия: {discord.__version__}", flush=True)

REQUEST_FILE = os.path.join(BASE_DIR, "requests.json")
RESPONSE_FILE = os.path.join(BASE_DIR, "responses.json")

POLL_INTERVAL = 0.5
FETCH_CONCURRENCY = 8
SEARCH_LIMIT = 25

PROXY_URL = os.getenv("PROXY_URL", "http://31.59.20.176:6754")
PROXY_USER = "zokylxzq"
PROXY_PASS = "kmiwh1bvbpl5"
PROXY_AUTH = aiohttp.BasicAuth(PROXY_USER, PROXY_PASS)


# ---------- Транслитерация ----------

_MULTI_RU_TO_EN = [
    ('щ', 'shch'), ('ё', 'yo'), ('ю', 'yu'), ('я', 'ya'),
    ('ж', 'zh'), ('ч', 'ch'), ('ш', 'sh'), ('ц', 'ts'), ('х', 'kh'),
]
_SINGLE_RU_TO_EN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'з': 'z',
    'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'ы': 'y',
    'э': 'e', 'ъ': '', 'ь': '',
}

_MULTI_EN_TO_RU = [
    ('shch', 'щ'), ('sch', 'щ'), ('yo', 'ё'), ('yu', 'ю'), ('ya', 'я'),
    ('zh', 'ж'), ('ch', 'ч'), ('sh', 'ш'), ('ts', 'ц'), ('kh', 'х'), ('ye', 'е'),
]
_SINGLE_EN_TO_RU = {
    'a': 'а', 'b': 'б', 'v': 'в', 'g': 'г', 'd': 'д', 'e': 'е', 'z': 'з',
    'i': 'и', 'y': 'й', 'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о',
    'p': 'п', 'r': 'р', 's': 'с', 't': 'т', 'u': 'у', 'f': 'ф', 'h': 'х',
    'c': 'ц', 'w': 'в', 'x': 'кс', 'j': 'дж',
}


def cyr_to_lat(text: str) -> str:
    result = text.lower()
    for cyr, lat in _MULTI_RU_TO_EN:
        result = result.replace(cyr, lat)
    return ''.join(_SINGLE_RU_TO_EN.get(ch, ch) for ch in result)


def lat_to_cyr(text: str) -> str:
    result = text.lower()
    for lat, cyr in _MULTI_EN_TO_RU:
        result = result.replace(lat, cyr)
    return ''.join(_SINGLE_EN_TO_RU.get(ch, ch) for ch in result)


def has_cyrillic(s: str) -> bool:
    return any('а' <= ch <= 'я' or ch == 'ё' for ch in s.lower())


def has_latin(s: str) -> bool:
    return any('a' <= ch <= 'z' for ch in s.lower())


def generate_query_variants(query: str) -> set:
    q = query.lower().strip()
    variants = {q}
    if has_cyrillic(q):
        variants.add(cyr_to_lat(q))
    if has_latin(q):
        variants.add(lat_to_cyr(q))
    return {v for v in variants if v}


# Разделители: слэши, дефисы, подчёркивания, точки, запятые, пробелы
_SEPARATORS_RE = re.compile(r'[|/_\-.,\s]+')

# Граница буква<->цифра (например user54321 -> user | 54321)
_LETTER_DIGIT_BOUNDARY_RE = re.compile(r'(?<=[^\d\W])(?=\d)|(?<=\d)(?=[^\d\W])')


def tokens_of(s: str) -> list:
    """Разбивает строку на токены по разделителям и по границе буква/цифра."""
    if not s:
        return []

    raw_tokens = [t for t in _SEPARATORS_RE.split(s) if t]

    tokens = set()
    for t in raw_tokens:
        tokens.add(t)
        # дробим ещё и на границе буква-цифра
        for sub in _LETTER_DIGIT_BOUNDARY_RE.split(t):
            if sub:
                tokens.add(sub)

    return list(tokens)


def matches_query(candidate: str, variants: set) -> bool:
    candidate = candidate.lower()
    if not candidate:
        return False
    for v in variants:
        if not v:
            continue
        if v in candidate or candidate in v:
            return True
    return False


class SelfBot(discord.Client):

    def __init__(self):
        super().__init__(
            proxy=PROXY_URL,
            proxy_auth=PROXY_AUTH,
        )
        self._ready_event = asyncio.Event()

    async def on_ready(self):
        print(f"[Selfbot] Залогинен как {self.user}", flush=True)
        print(f"[Selfbot] Серверов: {len(self.guilds)}", flush=True)
        print(f"[Selfbot] Proxy: {PROXY_URL}", flush=True)
        self._ready_event.set()

    async def _resolve_member(self, guild, user_id, semaphore):
        member = guild.get_member(user_id)
        if member is not None:
            return guild, member

        async with semaphore:
            try:
                member = await guild.fetch_member(user_id)
                return guild, member
            except Exception:
                return guild, None

    async def get_user_guild_data(self, user_id: int) -> dict:
        await self._ready_event.wait()

        semaphore = asyncio.Semaphore(FETCH_CONCURRENCY)
        tasks = [
            self._resolve_member(guild, user_id, semaphore)
            for guild in self.guilds
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_guilds = []
        role_guilds = []

        for res in results:
            if isinstance(res, Exception):
                continue

            guild, member = res
            if member is None:
                continue

            all_guilds.append({
                "guild_id": guild.id,
                "guild_name": guild.name,
            })

            roles = [
                role
                for role in member.roles
                if role.name != "@everyone"
            ]

            if not roles:
                continue

            role_guilds.append({
                "guild_id": guild.id,
                "guild_name": guild.name,
                "nick": member.nick or member.display_name,
                "joined_at": (
                    member.joined_at.isoformat()
                    if member.joined_at
                    else None
                ),
                "roles": [
                    {
                        "name": role.name,
                        "color": role.color.value,
                        "id": role.id
                    }
                    for role in sorted(
                        roles,
                        key=lambda r: r.position,
                        reverse=True
                    )
                ]
            })

        return {
            "all_guilds": all_guilds,
            "role_guilds": role_guilds,
        }

    def search_members(self, query: str, limit: int = SEARCH_LIMIT) -> list:
        """Фаззи-поиск по нику/юзернейму/статику с транслитерацией и разбивкой на токены."""
        variants = generate_query_variants(query)
        found = {}

        for guild in self.guilds:
            for member in guild.members:
                if member.id in found:
                    continue

                nick = member.nick or ""
                username = member.name

                candidates = (
                    [username, nick]
                    + tokens_of(username)
                    + tokens_of(nick)
                )

                matched_str = None
                for c in candidates:
                    if matches_query(c, variants):
                        matched_str = c
                        break

                if matched_str:
                    found[member.id] = {
                        "user_id": member.id,
                        "username": username,
                        "nick": nick,
                        "matched": matched_str,
                        "guild_name": guild.name,
                    }
                    if len(found) >= limit:
                        return list(found.values())

        return list(found.values())

    async def poll_requests(self):
        await self._ready_event.wait()

        while True:
            try:
                if os.path.exists(REQUEST_FILE):
                    with open(REQUEST_FILE, "r", encoding="utf-8") as f:
                        req = json.load(f)

                    os.remove(REQUEST_FILE)

                    req_id = req.get("req_id")
                    mode = req.get("mode")

                    if mode == "profile":
                        user_id = int(req.get("user_id"))
                        print(f"[Selfbot] Профиль для user_id={user_id}", flush=True)

                        data = await self.get_user_guild_data(user_id)

                        response = {
                            "req_id": req_id,
                            "mode": "profile",
                            "user_id": user_id,
                            "all_guilds": data["all_guilds"],
                            "role_guilds": data["role_guilds"],
                            "total_guilds": len(self.guilds),
                        }

                        print(
                            f"[Selfbot] Ответ записан. "
                            f"Общих: {len(data['all_guilds'])}, "
                            f"с ролями: {len(data['role_guilds'])}",
                            flush=True
                        )

                    elif mode == "search":
                        query = req.get("query", "")
                        print(f"[Selfbot] Поиск по запросу: {query}", flush=True)

                        candidates = self.search_members(query)

                        response = {
                            "req_id": req_id,
                            "mode": "search",
                            "candidates": candidates,
                        }

                        print(f"[Selfbot] Найдено кандидатов: {len(candidates)}", flush=True)

                    else:
                        response = {"req_id": req_id, "error": "unknown_mode"}

                    with open(RESPONSE_FILE, "w", encoding="utf-8") as f:
                        json.dump(response, f, ensure_ascii=False, indent=2)

            except json.JSONDecodeError as e:
                print(f"[Selfbot] Ошибка JSON: {e}", flush=True)

            except Exception as e:
                print(f"[Selfbot] Ошибка poll: {type(e).__name__}: {e}", flush=True)

            await asyncio.sleep(POLL_INTERVAL)

    async def setup_hook(self):
        asyncio.create_task(self.poll_requests())


async def main():
    token = os.getenv("USER_TOKEN")

    if not token:
        raise ValueError("USER_TOKEN не задан")

    bot = SelfBot()

    try:
        print("[Selfbot] Запуск...", flush=True)
        print(f"[Selfbot] Proxy = {PROXY_URL}", flush=True)
        await bot.start(token)
    finally:
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
