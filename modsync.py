#!/usr/bin/env python3
"""
ModSync — автоматическое обновление модов The Sims 4.
Работает на Windows и Linux.
Источники: CurseForge, ModTheSims, thesims.cc, Patreon, ВКонтакте.
Использование:
  python modsync.py scan              # сканировать папку Mods
  python modsync.py list              # показать все моды
  python modsync.py check             # проверить обновления (нужны API ключи в .env)
  python modsync.py check --source    # выбрать источник
"""
import os
import sys
import platform
import re
import json
import time
import ssl
import hashlib
from pathlib import Path
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode

# ---------------------------------------------------------------------------
# КОНФИГУРАЦИЯ
# ---------------------------------------------------------------------------
RATE_LIMIT = 1.0  # секунд между запросами
USER_AGENT = "ModSync/0.2 (Sims4 mod updater)"
REQUEST_TIMEOUT = 10

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

# Реестр источников: (env_key, функция-обработчик)
SOURCES = {}

# ---------------------------------------------------------------------------
# УТИЛИТЫ
# ---------------------------------------------------------------------------

def format_size(size_bytes: float) -> str:
    for unit in ("B", "KB", "MB"):
        if size_bytes < 1024:
            return f"{size_bytes:.0f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"


def load_api_key(env_key: str) -> str:
    """Загружает API ключ из .env или переменных окружения."""
    key = os.environ.get(env_key, "")
    if key:
        return key
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return ""
    with open(env_file) as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split(chr(0x3d), 1)
            if len(parts) == 2 and parts[0].strip() == env_key:
                return parts[1].strip()
    return ""


def get_json(url: str, headers: dict = None) -> dict | None:
    """GET запрос с парсингом JSON."""
    req = Request(url, headers=headers or {})
    req.add_header("User-Agent", USER_AGENT)
    try:
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def check_reliability(url: str) -> dict:
    """
    Проверяет надёжность источника.
    Возвращает: {ssl_valid, response_ms, score (0-100), warnings}
    """
    result = {"ssl_valid": False, "response_ms": 0, "score": 0, "warnings": []}

    # SSL
    domain = url.split("/")[2]
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(ssl.socket.socket(), server_hostname=domain) as s:
            s.settimeout(5)
            s.connect((domain, 443))
            cert = s.getpeercert()
        result["ssl_valid"] = True
    except Exception:
        result["ssl_valid"] = False
        result["warnings"].append("⚠️ SSL: нет или истёк")

    # Время ответа
    start = time.time()
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            resp.read(1)
        result["response_ms"] = int((time.time() - start) * 1000)
    except Exception:
        result["response_ms"] = 9999
        result["warnings"].append("⚠️ Источник не отвечает")

    # Оценка
    if result["ssl_valid"]:
        result["score"] += 40
    ms = result["response_ms"]
    if ms < 500:
        result["score"] += 40
    elif ms < 2000:
        result["score"] += 20
    elif ms < 5000:
        result["score"] += 10
    result["score"] += 20  # базовая
    if not result["warnings"]:
        result["score"] = min(100, result["score"])

    return result


# ---------------------------------------------------------------------------
# ИСТОЧНИКИ
# ---------------------------------------------------------------------------

def check_curseforge(mods: list[dict]) -> list[dict]:
    """CurseForge API (gameId=4 для Sims 4)."""
    api_key = load_api_key("CURSEFORGE_API_KEY")
    if not api_key:
        return []

    updates = []
    last_req = 0.0
    headers = {"Accept": "application/json", "x-api-key": api_key}

    for mod in mods:
        title = mod.get("title", "")
        if len(title) < 3:
            continue

        since = time.time() - last_req
        if since < RATE_LIMIT:
            time.sleep(RATE_LIMIT - since)

        params = f"gameId=4&searchFilter={quote(title)}&pageSize=2"
        url = f"https://api.curseforge.com/v1/mods/search?{params}"

        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                data = json.loads(resp.read())
            last_req = time.time()

            for item in data.get("data", [])[:1]:
                updates.append({
                    "file": mod["file"],
                    "local_name": mod["name"],
                    "source": "CurseForge",
                    "online_name": item.get("name", "?"),
                    "updated": item.get("dateModified", "?"),
                    "url": item.get("links", {}).get("websiteUrl", ""),
                    "status": "найдено",
                })
        except HTTPError as e:
            if e.code == 403:
                break
        except Exception:
            pass

    return updates


def check_modthesims(mods: list[dict]) -> list[dict]:
    """ModTheSims — отдельный API ключ."""
    api_key = load_api_key("MODTHESIMS_API_KEY")
    if not api_key:
        return []

    updates = []
    for mod in mods:
        title = mod.get("title", "")
        if len(title) < 3:
            continue

        url = f"https://api.modthesims.info/v2/downloads?q={quote(title)}&limit=2"
        data = get_json(url, {"x-api-key": api_key})
        if not data:
            continue
        time.sleep(RATE_LIMIT)

        for item in data.get("results", [])[:1]:
            updates.append({
                "file": mod["file"],
                "local_name": mod["name"],
                "source": "ModTheSims",
                "online_name": item.get("name", "?"),
                "updated": item.get("updated", "?"),
                "url": item.get("url", ""),
                "status": "найдено",
            })

    return updates


def check_thesimscc(mods: list[dict]) -> list[dict]:
    """thesims.cc — парсинг поиска (без API ключа)."""
    base = "https://thesims.cc"
    reliability = check_reliability(base)

    updates = []
    for mod in mods:
        title = mod.get("title", "")
        if len(title) < 3:
            continue

        search_url = f"{base}/search?q={quote(title)}"
        headers = {
            "Accept": "text/html",
            "User-Agent": USER_AGENT,
        }
        try:
            req = Request(search_url, headers=headers)
            with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            time.sleep(RATE_LIMIT)

            # Ищем ссылки на моды: /threads/...
            found = False
            for match in re.finditer(r'href="(/threads/[^"]+)"', html):
                thread_url = base + match.group(1)
                updates.append({
                    "file": mod["file"],
                    "local_name": mod["name"],
                    "source": "thesims.cc",
                    "online_name": title,
                    "url": thread_url,
                    "status": "ссылка (проверь вручную)",
                    "score": reliability["score"],
                })
                found = True
                break
        except Exception:
            pass

    return updates


def check_patreon(mods: list[dict]) -> list[dict]:
    """Patreon API — ищет посты русскоязычных авторов."""
    api_key = load_api_key("PATREON_API_KEY")
    if not api_key:
        return []

    updates = []
    headers = {"Authorization": f"Bearer {api_key}"}

    for mod in mods:
        title = mod.get("title", "")
        author = mod.get("author", "")
        if len(title) < 3 and not author:
            continue

        query = author if author else title
        url = f"https://www.patreon.com/api/oauth2/v2/campaigns?filter[search]={quote(query)}"
        data = get_json(url, headers)
        if not data:
            continue
        time.sleep(RATE_LIMIT)

        if data.get("data"):
            updates.append({
                "file": mod["file"],
                "local_name": mod["name"],
                "source": "Patreon",
                "online_name": author or title,
                "url": f"https://www.patreon.com/search?q={quote(query)}",
                "status": "найдено (проверь вручную)",
            })

    return updates


def check_vk(mods: list[dict]) -> list[dict]:
    """ВКонтакте API — поиск по сообществам Sims 4."""
    api_key = load_api_key("VK_API_KEY")
    if not api_key:
        return []

    updates = []
    for mod in mods:
        title = mod.get("title", "")
        if len(title) < 3:
            continue

        # Поиск по стене — публичные посты
        url = f"https://api.vk.com/method/wall.search?q={quote(title)}&count=3&v=5.199&access_token={api_key}"
        data = get_json(url)
        if not data:
            continue
        time.sleep(RATE_LIMIT)

        for item in data.get("response", {}).get("items", [])[:1]:
            post_id = item.get("id", "")
            owner_id = item.get("owner_id", "")
            updates.append({
                "file": mod["file"],
                "local_name": mod["name"],
                "source": "ВКонтакте",
                "online_name": title,
                "url": f"https://vk.com/wall{owner_id}_{post_id}",
                "status": "найдено (проверь вручную)",
            })

    return updates


# Регистрируем источники
SOURCES["curseforge"] = check_curseforge
SOURCES["modthesims"] = check_modthesims
SOURCES["thesimscc"] = check_thesimscc
SOURCES["patreon"] = check_patreon
SOURCES["vk"] = check_vk


# ---------------------------------------------------------------------------
# ПОИСК И СКАНИРОВАНИЕ
# ---------------------------------------------------------------------------

def find_mods_dir() -> Path | None:
    os_name = platform.system()
    for p in MODS_PATHS.get(os_name, []):
        if p.exists():
            return p
    return None


def parse_filename(filename: str) -> dict:
    name = Path(filename).stem
    result = {"author": None, "title": name, "version_raw": None}
    patterns = [
        r"^(.+?)_(.+?)_v?(\d[\d.]*\d)",
        r"^(.+?)_v?(\d[\d.]*(?:\.\d+)*)$",
        r"^(.+?)[_-](\d[\d.]*(?:\.\d+)*)$",
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


def scan_mods(mods_dir: Path) -> list[dict]:
    mods = []
    extensions = {".package", ".ts4script"}
    for root, _, files in os.walk(mods_dir):
        for fname in files:
            if Path(fname).suffix.lower() not in extensions:
                continue
            fpath = Path(root) / fname
            stat = fpath.stat()
            mod = {
                "file": str(fpath),
                "name": fname,
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "folder": str(Path(root).relative_to(mods_dir)) if str(root) != str(mods_dir) else ".",
                "ext": Path(fname).suffix.lower(),
            }
            mod.update(parse_filename(fname))
            mods.append(mod)
    return mods


def check_mods(mods: list[dict], source: str = None) -> list[dict]:
    """Проверяет обновления по всем (или одному) источникам."""
    all_updates = []

    sources_to_check = [source] if source else list(SOURCES.keys())

    for src_name in sources_to_check:
        fn = SOURCES.get(src_name)
        if not fn:
            continue
        print(f"  🔗 {src_name}...")
        try:
            result = fn(mods)
            all_updates.extend(result)
            print(f"     найдено: {len(result)}")
        except Exception as e:
            print(f"     ⚠️ ошибка: {e}")

    return all_updates


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def print_mods_table(mods: list[dict]):
    if not mods:
        print("Моды не найдены.")
        return
    print(f"\n{'ФАЙЛ':<50} {'РАЗМЕР':>8}  {'ДАТА':<16}")
    print("-" * 80)
    for m in sorted(mods, key=lambda x: x["name"].lower()):
        size = format_size(m["size"])
        date = m["modified"][:16].replace("T", " ")
        name = m["name"][:48]
        ver = m.get("version_raw", "")
        suffix = f" (v{ver})" if ver else ""
        print(f"{name + suffix:<50} {size:>8}  {date:<16}")
    print(f"\n Всего: {len(mods)} модов")


def cmd_scan(mods_dir: Path):
    print(f"📁 Папка модов: {mods_dir}")
    mods = scan_mods(mods_dir)
    print_mods_table(mods)
    cache = mods_dir / ".modsync_cache.json"
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(mods, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Кэш: {cache}")


def cmd_list(mods_dir: Path):
    cache = mods_dir / ".modsync_cache.json"
    if cache.exists():
        with open(cache, encoding="utf-8") as f:
            mods = json.load(f)
        print_mods_table(mods)
    else:
        print("Сначала сделай 'scan'.")


def cmd_check(mods_dir: Path, source: str = None):
    cache = mods_dir / ".modsync_cache.json"
    if not cache.exists():
        print("Сначала сделай 'scan'.")
        return
    with open(cache, encoding="utf-8") as f:
        mods = json.load(f)

    print(f"🔍 Проверяю {len(mods)} модов...\n")
    updates = check_mods(mods, source)

    if not updates:
        print("✅ Обновлений не найдено.")
        return

    print(f"\n{'ЛОКАЛЬНО':<45} {'ИСТОЧНИК':<15} {'СТАТУС':<12}")
    print("-" * 85)
    for u in updates:
        print(f"{u['local_name']:<45} {u['source']:<15} {u.get('status','?'):<12}")
        if u.get("url"):
            print(f"  🔗 {u['url']}")


def cmd_info(mods_dir: Path):
    mods = []
    total_size = 0
    for root, _, files in os.walk(mods_dir):
        for f in files:
            if f.lower().endswith((".package", ".ts4script")):
                mods.append(f)
                total_size += os.path.getsize(os.path.join(root, f))
    print(f"📁 {mods_dir}")
    print(f"📦 Модов: {len(mods)}")
    print(f"💾 Общий размер: {format_size(total_size)}")
    print(f"🖥️  Платформа: {platform.system()} {platform.release()}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ModSync — обновление модов Sims 4 (CurseForge, ModTheSims, thesims.cc, Patreon, VK)")
    parser.add_argument("command", nargs="?", default="info",
                        choices=["scan", "list", "check", "info"])
    parser.add_argument("--dir", "-d", help="Путь к папке Mods")
    parser.add_argument("--source", "-s", choices=list(SOURCES.keys()),
                        help="Проверить только один источник")
    args = parser.parse_args()

    mods_dir = Path(args.dir) if args.dir else find_mods_dir()
    if mods_dir is None or not mods_dir.exists():
        print("❌ Папка Mods не найдена. Укажи --dir")
        sys.exit(1)

    {"scan": cmd_scan, "list": cmd_list, "check": lambda d: cmd_check(d, args.source), "info": cmd_info}[args.command](mods_dir)


if __name__ == "__main__":
    main()
