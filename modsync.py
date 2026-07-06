#!/usr/bin/env python3
"""
ModSync — автоматическое обновление модов The Sims 4.
Работает на Windows и Linux.
Использование:
  python modsync.py scan              # сканировать папку Mods
  python modsync.py list              # показать все моды
  python modsync.py check             # проверить обновления (требуется API ключ)
  python modsync.py --dir PATH        # указать папку вручную
"""
import os
import sys
import platform
import re
import json
import time
from pathlib import Path
from datetime import datetime

CURSEFORGE_API = "https://api.curseforge.com/v1"
RATE_LIMIT = 1.0  # секунд между запросами

# Стандартные пути к Sims 4
MODS_PATHS = {
    "Windows": [
        Path.home() / "Documents" / "Electronic Arts" / "The Sims 4" / "Mods",
        Path("C:/") / "Users" / os.environ.get("USERNAME", "") / "Documents" / "Electronic Arts" / "The Sims 4" / "Mods",
    ],
    "Linux": [
        Path.home() / "Documents" / "Electronic Arts" / "The Sims 4" / "Mods",
        Path.home() / ".local/share/Steam/steamapps/compatdata/1222670/pfx/drive_c/users/steamuser/Documents/Electronic Arts/The Sims 4/Mods",
    ],
}


def find_mods_dir() -> Path | None:
    """Автоматически ищет папку Mods Sims 4."""
    os_name = platform.system()
    paths = MODS_PATHS.get(os_name, [])
    for p in paths:
        if p.exists():
            return p
    return None


def scan_mods(mods_dir: Path) -> list[dict]:
    """Сканирует папку Mods и собирает метаданные."""
    mods = []
    extensions = {".package", ".ts4script"}

    for root, dirs, files in os.walk(mods_dir):
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext not in extensions:
                continue

            fpath = Path(root) / fname
            stat = fpath.stat()

            mod = {
                "file": str(fpath),
                "name": fname,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "folder": str(Path(root).relative_to(mods_dir)) if str(root) != str(mods_dir) else ".",
                "ext": ext,
            }

            # Парсим имя: "Author_ModName_v1.2.3.package"
            parsed = parse_filename(fname)
            mod.update(parsed)

            mods.append(mod)

    return mods


def parse_filename(filename: str) -> dict:
    """Извлекает автора, название и версию из имени файла."""
    name = Path(filename).stem  # без расширения
    result = {"author": None, "title": name, "version_raw": None}

    # Паттерны: Author_ModName_v1.2.3, ModName_v2, Author-ModName-1.4
    patterns = [
        r"^(.+?)_(.+?)_v?(\d[\d.]*\d)",      # Author_Name_v1.2.3
        r"^(.+?)_v?(\d[\d.]*(?:\.\d+)*)$",    # Name_v1.2.3
        r"^(.+?)[_-](\d[\d.]*(?:\.\d+)*)$",   # Name-1.2.3
    ]

    for pat in patterns:
        m = re.match(pat, name)
        if m:
            groups = m.groups()
            if len(groups) == 3:
                result["author"] = groups[0].replace("_", " ")
                result["title"] = groups[1].replace("_", " ")
                result["version_raw"] = groups[2]
            elif len(groups) == 2:
                result["title"] = groups[0].replace("_", " ")
                result["version_raw"] = groups[1]
            break

    return result


def check_curseforge(api_key: str, mods: list[dict]) -> list[dict]:
    """Проверяет обновления через CurseForge API."""
    import urllib.request
    import urllib.parse
    import urllib.error

    updates = []
    last_req = 0.0

    headers = {
        "Accept": "application/json",
        "x-api-key": api_key,
    }

    for mod in mods:
        title = mod.get("title", "")
        if len(title) < 3:
            continue

        # Rate limit
        since = time.time() - last_req
        if since < RATE_LIMIT:
            time.sleep(RATE_LIMIT - since)

        # Ищем мод по названию
        params = f"gameId=4&searchFilter={urllib.parse.quote(title)}&pageSize=3"
        url = f"{CURSEFORGE_API}/mods/search?{params}"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
            last_req = time.time()

            results = data.get("data", [])
            if results:
                latest = results[0]
                mod_name = latest.get("name", "?")
                mod_date = latest.get("dateModified", "?")
                mod_url = latest.get("links", {}).get("websiteUrl", "")

                updates.append({
                    "file": mod["file"],
                    "local_name": mod["name"],
                    "curseforge_name": mod_name,
                    "updated": mod_date,
                    "url": mod_url,
                    "status": "проверить (сравни версию)",
                })
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print(f"  ⚠️ CurseForge API ключ неверный или истёк", file=sys.stderr)
                break
        except Exception as e:
            pass  # сетевая ошибка — пропускаем

    return updates


def format_size(size_bytes: int) -> str:
    """Форматирует размер файла."""
    for unit in ("B", "KB", "MB"):
        if size_bytes < 1024:
            return f"{size_bytes:.0f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"


def print_mods_table(mods: list[dict]):
    """Красиво выводит список модов в таблицу."""
    if not mods:
        print("Моды не найдены.")
        return

    # Заголовок
    print(f"\n{'ФАЙЛ':<50} {'РАЗМЕР':>8}  {'ДАТА':<16}")
    print("-" * 80)

    mods_sorted = sorted(mods, key=lambda m: m["name"].lower())
    for m in mods_sorted:
        size = format_size(m["size"])
        date = m["modified"][:16].replace("T", " ")
        name = m["name"][:48]

        # Версия если есть
        ver = m.get("version_raw", "")
        suffix = f" (v{ver})" if ver else ""

        print(f"{name + suffix:<50} {size:>8}  {date:<16}")

    print(f"\n Всего: {len(mods)} модов")


def cmd_scan(mods_dir: Path):
    """Сканирует папку Mods."""
    print(f"📁 Папка модов: {mods_dir}")
    mods = scan_mods(mods_dir)
    print_mods_table(mods)

    # Сохраняем кэш для последующих проверок
    cache_path = mods_dir / ".modsync_cache.json"
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(mods, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Кэш сохранён: {cache_path}")


def cmd_list(mods_dir: Path):
    """Показывает список из кэша."""
    cache_path = mods_dir / ".modsync_cache.json"
    if cache_path.exists():
        with open(cache_path, encoding="utf-8") as f:
            mods = json.load(f)
        print_mods_table(mods)
    else:
        print("Сначала запусти 'scan' — кэш пуст.")
        print(f"  python modsync.py scan")


def cmd_check(mods_dir: Path):
    """Проверяет обновления через CurseForge."""
    # Пробуем получить ключ
    api_key = os.environ.get("CURSEFORGE_API_KEY", "")
    if not api_key:
        # Проверяем .env файл рядом
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith("CURSEFORGE_API_KEY="):
                        api_key = line.strip().split("=", 1)[1].strip()
                        break

    if not api_key:
        print("❌ Нужен CURSEFORGE_API_KEY!")
        print("   1. Зайди на https://developers.curseforge.com")
        print("   2. Создай API ключ (бесплатно)")
        print("   3. Укажи в .env файле: CURSEFORGE_API_KEY=твой_ключ")
        print("   4. Повтори: python modsync.py check")
        return

    # Загружаем кэш
    cache_path = mods_dir / ".modsync_cache.json"
    if not cache_path.exists():
        print("Сначала сделай 'scan'.")
        return

    with open(cache_path, encoding="utf-8") as f:
        mods = json.load(f)

    print(f"🔍 Проверяю {len(mods)} модов через CurseForge...")
    print("   (может занять пару минут)\n")

    updates = check_curseforge(api_key, mods)

    if not updates:
        print("✅ Обновлений не найдено (или все моды актуальны)")
        return

    print(f"\n{'ЛОКАЛЬНЫЙ ФАЙЛ':<50} {'НА CURSEFORGE':<30} {'СТАТУС':<15}")
    print("-" * 95)
    for u in updates:
        print(f"{u['local_name']:<50} {u['curseforge_name'][:28]:<30} {'⚠️ ' + u['status']:<15}")


def cmd_info(mods_dir: Path):
    """Показывает информацию о папке Mods."""
    mods = []
    for root, _, files in os.walk(mods_dir):
        for f in files:
            if f.lower().endswith((".package", ".ts4script")):
                mods.append(f)

    total_size = sum(
        os.path.getsize(os.path.join(root, f))
        for root, _, files in os.walk(mods_dir)
        for f in files
        if f.lower().endswith((".package", ".ts4script"))
    )

    print(f"📁 {mods_dir}")
    print(f"📦 Модов: {len(mods)}")
    print(f"💾 Общий размер: {format_size(total_size)}")
    print(f"🖥️  Платформа: {platform.system()} {platform.release()}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="ModSync — обновление модов Sims 4")
    parser.add_argument("command", nargs="?", default="info",
                        choices=["scan", "list", "check", "info"],
                        help="Команда (по умолчанию: info)")
    parser.add_argument("--dir", "-d", help="Путь к папке Mods (если не найден автоматически)")

    args = parser.parse_args()

    mods_dir = Path(args.dir) if args.dir else find_mods_dir()

    if mods_dir is None:
        print("❌ Папка Mods не найдена автоматически!")
        print("   Укажи путь вручную: python modsync.py scan --dir 'C:\\Users\\...\\Mods'")
        sys.exit(1)

    if not mods_dir.exists():
        print(f"❌ Папка не существует: {mods_dir}")
        sys.exit(1)

    commands = {
        "scan": cmd_scan,
        "list": cmd_list,
        "check": cmd_check,
        "info": cmd_info,
    }

    commands[args.command](mods_dir)


if __name__ == "__main__":
    main()
