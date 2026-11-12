# Як застосунок дізнається про нові дані · How the app finds new data

Збирач публікує дані «Чинності» у випусках (Releases) репозиторію `marybezuhla/chynnist`. Теги даних починаються з `data`, теги застосунку — з `v`.

| Випуск | Що в ньому |
|---|---|
| `data` | Завжди лише два файли: `index.json` і `index.sig` — що є зараз |
| `data-РРРР-ММ` | Основа місяця `chynnist-<стан>.suvii` і латки `chynnist-<з>-<до>.patch.suvii` |

## `index.json`

```json
{
 "format": "chynnist-index-1",
 "collection": "8e3b6c1a-5d2f-4b7e-9a41-2c6f0d8e7b53",
 "created": "2026-11-12T10:00:00Z",
 "seq": 7,
 "base": {"seq": 5, "file": "chynnist-5.suvii", "url": "https://github.com/…/data-2026-11/chynnist-5.suvii",
          "size": 412345678, "sha256": "…"},
 "patches": [
  {"from": 5, "to": 7, "file": "chynnist-5-7.patch.suvii", "url": "…", "size": 2345678, "sha256": "…"},
  {"from": 6, "to": 7, "file": "chynnist-6-7.patch.suvii", "url": "…", "size": 1234567, "sha256": "…"}
 ]
}
```

- `seq` — найновіший стан. Латки є від **кожного** попереднього стану місяця до нього, тож телефону на будь-якому з них потрібне одне завантаження.
- Невідомі поля застосунок пропускає; інший `format` — «потрібна новіша версія застосунку».

## Підпис

`index.sig` — один рядок base64: підпис ed25519 над байтами `"chynnist-index-sig-1\n"`, за якими йдуть **точні байти** `index.json` (без перетворень). Ключ — той самий ключ даних, яким підписано сувої; публічний ключ вбудовано в застосунок.

## Що робить застосунок

1. Завантажує `index.json` і `index.sig` (кожен не більше 1 МБ), перевіряє підпис вбудованим ключем. Не збігся — нічого не змінювати.
2. Перевіряє `collection` і що `seq` більший за власний стан; `created` не з майбутнього більш ніж на добу.
3. Якщо є латка з `from` = власний стан — пропонує її; інакше — основу. Розміри показує людині, бо латка й основа можуть різнитися в сотні разів.
4. Завантажує файл лише з `https://github.com/marybezuhla/chynnist/releases/download/` (і перенаправлень GitHub на його сховище), перевіряє `size` і `sha256` до відкриття.
5. Застосовує латку однією транзакцією за `SPEC.md` (розділ 12) і перевіряє підпис сувою. Будь-яка помилка — лишається попередній стан.

---

## English

Data is published in Releases of `marybezuhla/chynnist`: the `data` release always holds the current `index.json` and `index.sig`; `data-YYYY-MM` holds the month's base and its patches. Patches exist from **every** earlier state of the month to the newest, so a phone on any of them downloads exactly one file. `index.sig` is a base64 ed25519 signature over `"chynnist-index-sig-1\n"` followed by the exact bytes of `index.json`, made with the data key whose public half is built into the app. The app verifies the signature, picks the patch whose `from` equals its own state (or the base), downloads only from the repository's release URLs, checks `size` and `sha256` before opening, and applies the patch in one transaction as `SPEC.md`, section 12 describes.
