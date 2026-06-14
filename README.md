# SrbLearn

Telegram-бот для изучения сербского языка с интервальным повторением (SM-2) и уведомлениями.

## Возможности

- Викторина в двух режимах: сербский → русский и русский → сербский
- Уровни A1–C2 с отдельными словарями (3000+ слов)
- Алгоритм spaced repetition для эффективного запоминания
- Настраиваемые уведомления о повторении (1–3 раза в сутки)

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие, регистрация, выбор уровня |
| `/quiz` | Начать викторину |
| `/settings` | Уровень, уведомления, время напоминаний |
| `/stats` | Статистика: изучено слов, точность, на повторении |
| `/help` | Справка |

## Установка

```bash
git clone <repo-url> srblearn
cd srblearn

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
# или установка в editable-режиме:
pip install -e ".[dev]"

cp .env.example .env
```

## Настройка `.env`

Отредактируйте `.env`:

```env
BOT_TOKEN=your_telegram_bot_token_here
DB_PATH=progress.db
```

| Переменная | Описание |
|------------|----------|
| `BOT_TOKEN` | Токен бота от [@BotFather](https://t.me/BotFather) |
| `DB_PATH` | Путь к файлу SQLite с прогрессом пользователей |

Файл `progress.db` не коммитится в git — данные хранятся локально на сервере.

## Локальный запуск

```bash
source venv/bin/activate
python -m srblearn.bot
```

## Деплой через systemd

1. Скопируйте проект на сервер:

```bash
sudo mkdir -p /opt/srblearn
sudo cp -r . /opt/srblearn/
sudo chown -R YOUR_USER:YOUR_USER /opt/srblearn
```

2. Настройте окружение на сервере:

```bash
cd /opt/srblearn
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # укажите BOT_TOKEN
```

3. Отредактируйте unit-файл — замените `YOUR_USER` на имя пользователя Linux:

```bash
nano srblearn.service
```

4. Установите и запустите сервис:

```bash
sudo cp srblearn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable srblearn
sudo systemctl start srblearn
```

5. Проверка статуса и логов:

```bash
sudo systemctl status srblearn
sudo journalctl -u srblearn -f
```

Перезапуск после обновления кода:

```bash
sudo systemctl restart srblearn
```

## Словари

Словари находятся в `srblearn/vocabulary/*.json` (A1–C2). Редактируются только через файлы, не через бота.

Формат записи:

```json
{"sr": "здраво", "ru": "привет", "tags": ["greetings"]}
```

## Тесты

```bash
source venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Стек

- Python 3.11+
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) ≥ 21
- APScheduler — уведомления
- aiosqlite — SQLite
- python-dotenv — конфигурация
