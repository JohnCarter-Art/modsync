# ModSync — Автоматическое обновление модов Sims 4

Следит за модами для **The Sims 4** и проверяет обновления через CurseForge API.
Работает на **Windows** и **Linux**.

## Установка

```bash
git clone https://github.com/JohnCarter-Art/modsync
cd modsync
# Зависимостей нет — только стандартная библиотека Python
```

## Использование

```bash
# Показать инфо о папке Mods
python modsync.py

# Просканировать моды
python modsync.py scan

# Показать список из кэша
python modsync.py list

# Проверить обновления через CurseForge (нужен API ключ)
python modsync.py check

# Указать папку вручную
python modsync.py scan --dir "C:\\Users\\...\\Mods"
```

## CurseForge API ключ

1. Зайди на https://developers.curseforge.com
2. Создай приложение → получи ключ
3. Создай файл `.env` рядом с `modsync.py`:

```
CURSEFORGE_API_KEY=***```

4. Или через переменную окружения:
```bash
export CURSEFORGE_API_KEY=***```

## Как работает

- Автоматически находит папку Mods (стандартные пути)
- Сканирует `.package` и `.ts4script` файлы
- Извлекает автора, название и версию из имени файла
- Проверяет обновления через CurseForge API
- Сохраняет кэш в `.modsync_cache.json` для быстрого доступа
