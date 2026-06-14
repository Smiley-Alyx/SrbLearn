# 🇷🇸 SrbLearn

[![Python](https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white)](https://python.org)
[![Telegram Bot](https://img.shields.io/badge/telegram-bot-2CA5E0?logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![SM-2](https://img.shields.io/badge/algorithm-SM--2-7f77dd)](https://en.wikipedia.org/wiki/SuperMemo)
[![systemd](https://img.shields.io/badge/deploy-systemd-orange)](srblearn.service)

> Telegram-бот для изучения сербских слов методом интервального повторения.
> Уровни A1–C2, два режима викторины, умные уведомления, прогресс на каждого пользователя.

**🤖 Попробовать бота:** [@srb_learn_bot](https://t.me/srb_learn_bot)

## Возможности

- Викторина в двух режимах: сербский → русский и русский → сербский
- Уровни A1–C2 с отдельными словарями (3000+ слов)
- Алгоритм [SM-2](https://en.wikipedia.org/wiki/SuperMemo) для эффективного запоминания
- Настраиваемые уведомления о повторении (1–3 раза в сутки)
- Управление через кнопки меню и команды

## Как пользоваться

1. Откройте [@srb_learn_bot](https://t.me/srb_learn_bot) и нажмите **Start**
2. Выберите уровень A1–C2
3. Нажмите **📝 Викторина** — отвечайте на вопросы с 4 вариантами
4. В **⚙️ Настройки** включите уведомления, чтобы бот напоминал о повторении
5. Следите за прогрессом в **📊 Статистика**

## Команды и кнопки

| Действие | Команда | Кнопка |
|----------|---------|--------|
| Приветствие | `/start` | — |
| Викторина | `/quiz` | 📝 Викторина |
| Настройки | `/settings` | ⚙️ Настройки |
| Статистика | `/stats` | 📊 Статистика |
| Справка | `/help` | ❓ Справка |

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

## Лицензия

[MIT](LICENSE)
