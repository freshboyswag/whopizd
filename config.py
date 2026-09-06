import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
USER_TOKEN = os.getenv("USER_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не задан в .env")
if not USER_TOKEN:
    raise ValueError("USER_TOKEN не задан в .env")
