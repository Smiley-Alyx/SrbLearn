# Changelog

Формат основан на [Keep a Changelog](https://keepachangelog.com/).
Версионирование — [SemVer](https://semver.org/).

## [0.1.0] - 2026-06-14

Первый публичный релиз SrbLearn — Telegram-бот для изучения сербского языка.

### Добавлено

- Викторина в двух режимах: сербский → русский и русский → сербский
- Словари A1–C2 (3000+ слов) в `srblearn/vocabulary/*.json`
- Алгоритм интервального повторения SM-2 (`quiz_engine.py`)
- SQLite-хранилище прогресса пользователей (`db.py`)
- Команды: `/start`, `/quiz`, `/settings`, `/stats`, `/help`
- Кнопочное меню: 📝 Викторина, ⚙️ Настройки, 📊 Статистика, ❓ Справка
- FSM-настройки: уровень, уведомления, частота и время (HH:MM)
- Планировщик уведомлений на APScheduler
- Деплой через systemd (`srblearn.service`)
- Тесты для `db` и `quiz_engine` (19 тестов)
- README с инструкцией по установке и деплою

### Бот

Попробовать: [@srb_learn_bot](https://t.me/srb_learn_bot)

[0.1.0]: https://github.com/Smiley-Alyx/SrbLearn/releases/tag/v0.1.0
