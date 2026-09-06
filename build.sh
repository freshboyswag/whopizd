#!/bin/bash
set -e

# Основное окружение - discord.py для бота
pip install discord.py==2.3.2 python-dotenv==1.0.1 aiohttp

# Отдельное окружение для selfbot
python -m venv selfbot_venv
selfbot_venv/bin/pip install discord.py-self==2.1.0 aiohttp
