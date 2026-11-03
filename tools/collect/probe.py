# SPDX-License-Identifier: GPL-3.0-or-later
"""Проба API порталу відкритих даних Верховної Ради.

Робить кілька запитів (з паузами 5–7 с, як просить Рада) і зберігає відповіді в теку probe/,
щоб побачити формат даних. Потрібен лише Python 3.9+ без додаткових бібліотек.

Запуск:  python3 probe.py
"""

from __future__ import annotations

import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://data.rada.gov.ua"
UA = "OpenData"
OUT = Path(__file__).resolve().parent / "probe"

# (назва файлу, шлях, скільки байтів максимум)
PROBES = [
    ("r.txt", "/laws/main/r.txt", 200_000),
    ("r-page1.json", "/laws/main/r/page1.json", 300_000),
    ("card-constitution.json", "/laws/card/254к/96-вр.json", 300_000),
    ("show-constitution.txt", "/laws/show/254к/96-вр.txt", 3_000_000),
    ("show-constitution.html", "/laws/show/254к/96-вр", 3_000_000),
    ("card-civil-code.json", "/laws/card/435-15.json", 300_000),
    ("show-civil-code.html", "/laws/show/435-15", 6_000_000),
    ("show-small.txt", "/laws/show/n0438500-26.txt", 300_000),
    ("ogd-stan.txt", "/ogd/zak/laws/data/csv/stan.txt", 50_000),
]


def fetch(name: str, path: str, limit: int) -> dict:
    url = BASE + urllib.parse.quote(path, safe="/.-_")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    t0 = time.monotonic()
    info: dict = {"name": name, "url": url}
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            body = r.read(limit)
            info.update(status=r.status, final_url=r.geturl(), headers=dict(r.headers))
    except urllib.error.HTTPError as e:
        body = e.read(50_000)
        info.update(status=e.code, final_url=url, headers=dict(e.headers))
    except Exception as e:  # мережа, DNS, TLS
        info.update(error=f"{type(e).__name__}: {e}")
        body = b""
    info["seconds"] = round(time.monotonic() - t0, 2)
    info["bytes"] = len(body)
    (OUT / name).write_bytes(body)
    return info


def main() -> int:
    OUT.mkdir(exist_ok=True)
    results = []
    for i, (name, path, limit) in enumerate(PROBES):
        if i:
            time.sleep(random.uniform(5, 7))
        info = fetch(name, path, limit)
        results.append(info)
        status = info.get("status", info.get("error"))
        print(f"{name:28} {status}  {info['bytes']:>9} байтів  {info['seconds']} с")
        sys.stdout.flush()
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nГотово. Відповіді збережено в {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
