# SPDX-License-Identifier: GPL-3.0-or-later
"""Проба API порталу відкритих даних Верховної Ради: кілька запитів з паузами, вивід у журнал.

Правила API (data.rada.gov.ua/open/main/api/page3): User-Agent "OpenData" для не-JSON форматів,
пауза 5–7 с між запитами, не запитувати токен і не перевіряти ліміти перед кожним запитом.
"""

from __future__ import annotations

import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://data.rada.gov.ua"
UA = "OpenData"

PROBES = [
    # (опис, шлях без кодування)
    ("Список поновлених (nreg, TXT)", "/laws/main/r.txt"),
    ("Список поновлених з реквізитами (JSON, стор. 1)", "/laws/main/r/page1.json"),
    ("Картка Конституції (JSON)", "/laws/card/254к/96-вр.json"),
    ("Текст Конституції (TXT)", "/laws/show/254к/96-вр.txt"),
    ("Текст Конституції (HTML)", "/laws/show/254к/96-вр"),
    ("Картка КК (JSON)", "/laws/card/2341-14.json"),
    ("Метадані карток (OGD)", "/ogd/zak/laws/docs/meta.json"),
]


def fetch(path: str) -> None:
    url = BASE + urllib.parse.quote(path, safe="/.-_")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read(3_000_000)
            status, headers, final = r.status, r.headers, r.geturl()
    except urllib.error.HTTPError as e:
        body, status, headers, final = e.read(20_000), e.code, e.headers, url
    except Exception as e:  # мережа, DNS, TLS
        print(f"  ПОМИЛКА: {type(e).__name__}: {e}")
        return
    dt = time.monotonic() - t0
    print(f"  статус {status}, {len(body)} байтів, {dt:.1f} с, кінцева адреса: {final}")
    for h in ("Content-Type", "Last-Modified", "Content-Length", "ETag", "Server"):
        if headers.get(h):
            print(f"  {h}: {headers.get(h)}")
    ctype = (headers.get("Content-Type") or "").lower()
    enc = "cp1251" if "1251" in ctype else "utf-8"
    text = body.decode(enc, errors="replace")
    head = text[:2500]
    print("  --- початок ---")
    for line in head.splitlines():
        print("  | " + line[:300])
    if "<a name=" in text or ' id="' in text:
        import re

        ids = re.findall(r'(?:name|id)="([^"]{1,40})"', text)
        print(f"  --- якорі: {len(ids)}, приклади: {ids[:15]}")


def main() -> int:
    for i, (title, path) in enumerate(PROBES):
        if i:
            time.sleep(random.uniform(5, 7))
        print(f"\n=== {title}: {path}")
        sys.stdout.flush()
        fetch(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
