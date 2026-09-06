# Discord Role Checker

Бот для проверки ролей пользователя по всем серверам через юзерский аккаунт.

## Структура

```
discord-role-checker/
├── main.py              # точка входа
├── keepalive.py         # HTTP сервер для Render + UptimeRobot
├── config.py            # загрузка токенов из .env
├── bot/
│   ├── client.py        # официальный бот
│   └── commands.py      # слэш-команда /check
├── utils/
│   └── selfbot.py       # selfbot — сбор данных через юзерский акк
├── requirements.txt
├── .env.example
└── .gitignore
```

## Установка

1. Скопируй `.env.example` в `.env` и вставь токены
2. `pip install -r requirements.txt`
3. `python main.py`

## Команды

- `/check user:@упоминание` — проверить роли по упоминанию
- `/check user_id:123456789` — проверить роли по Discord ID
