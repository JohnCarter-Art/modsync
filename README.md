# ModSync — Обновление модов The Sims 4

[![Platform](https://img.shields.io/badge/platform-Windows%20|%20Linux-blue)]()
[![Python](https://img.shields.io/badge/python-3.8%2B-green)]()
[![License](https://img.shields.io/badge/license-MIT-orange)]()

Сканирует папку `Mods`, находит устаревшие моды и проверяет обновления по 5 источникам.

## Возможности

- 📁 **Автопоиск папки Mods** — работает на Windows и Linux
- 📦 **Сканирование** — читает `.package` и `.ts4script`, извлекает версию из имени файла
- 🔍 **5 источников** — проверка обновлений везде где можно
- 🎨 **GUI** — веб-интерфейс с таблицей модов и кнопками
- 🛡️ **Проверка надёжности** — SSL + время ответа для каждого источника

## Источники

| Источник | API ключ | Сравнение версий |
|---|---|---|
| **CurseForge** | `CURSEFORGE_API_KEY` | ✅ Автоматическое |
| **ModTheSims** | `MODTHESIMS_API_KEY` | ✅ Автоматическое |
| **thesims.cc** | не нужен | ❌ ручная проверка |
| **Patreon** | `PATREON_API_KEY` | ❌ ручная проверка |
| **ВКонтакте** | `VK_API_KEY` | ❌ ручная проверка |

## Установка

```bash
git clone https://github.com/JohnCarter-Art/modsync
cd modsync
pip install -r requirements.txt  # можно пропустить — зависимости не требуются
```

## Использование

```bash
# CLI
python modsync.py scan              # просканировать папку Mods
python modsync.py list              # показать кэш
python modsync.py check             # проверить все источники
python modsync.py check --source curseforge  # только CurseForge

# GUI (веб-интерфейс)
python modsync_gui.py               # открыть http://localhost:9876
```

## Настройка API ключей

Создай файл `.env` рядом с `modsync.py`:

```env
CURSEFORGE_API_KEY=***MODTHESIMS_API_KEY=*** Или через переменные окружения:
```bash
export CURSEFORGE_API_KEY=***```

## Как определяются версии

- **Локально**: из имени файла формата `Author_ModName_v1.2.3.package`
- **CurseForge/ModTheSims**: из названия на сайте
- **Статус**: `🔄 устарел`, `✅ актуален`, `❓ проверить вручную`
- Если версию не удалось извлечь — мод помечается `❓`

## Системные требования

- Python 3.8+
- Windows или Linux
- The Sims 4 (стандартная папка `Documents/Electronic Arts/The Sims 4/Mods`)
