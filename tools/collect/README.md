# Збирач «Чинності» · Chynnist collector

Завантажує тексти документів з [Порталу відкритих даних Верховної Ради України](https://data.rada.gov.ua) і готує з них колекцію у форматі [«Сувій»](https://github.com/marybezuhla/suvii). Працює на комп'ютері видавця, не на серверах GitHub.

*Downloads document texts from the Open Data Portal of the Verkhovna Rada of Ukraine and prepares a [Suvii](https://github.com/marybezuhla/suvii) collection from them. [English below](#english).*

## Як збирач поводиться з порталом

Збирач дотримується [правил порталу](https://data.rada.gov.ua/open/main/api/page3):

- називає себе так, як просить портал (`OpenData`), і звертається лише до `data.rada.gov.ua` та `zakon.rada.gov.ua`;
- між будь-якими двома запитами чекає 5–7 секунд;
- за день використовує не більше 90 % дозволеного (180 МБ і 90 000 запитів, доба за київським часом);
- після першої відмови (403 або 429) не робить жодного запиту добу;
- після трьох помилок мережі поспіль робить перерву на три години;
- не працює у два вікна одночасно;
- список усіх документів бере не частіше ніж раз на тиждень.

Усі ці числа зібрано в одному файлі: `src/chynnist_collect/rules.py`.

## Команди

```
chynnist-collect catalog                   # оновити список усіх документів порталу й чергу
chynnist-collect add 254к/96-вр 2341-14    # або додати окремі документи до черги
chynnist-collect run --minutes 55          # завантажувати, доки є час і ліміт
chynnist-collect status                    # що зроблено і що чекає
chynnist-collect keygen                    # один раз: ключ підпису даних у Keychain
chynnist-collect build chynnist-1.suvii    # зібрати підписаний сувій із завантаженого
chynnist-collect build proba.suvii --test-key   # пробна збірка з тимчасовим ключем
chynnist-collect release chynnist-1.suvii  # підготувати до випуску: основа або латки й index.json
```

`release` кладе в теку `work/outbox` усе, що треба завантажити: кожна підтека — це випуск GitHub з такою самою назвою (`data` — індекс, `data-РРРР-ММ` — основа місяця й латки). Раз на місяць новий стан стає основою; між тим виходять латки від кожного попереднього стану місяця, тож телефону завжди досить одного завантаження. Доки `outbox` не очищено після завантаження, новий випуск не готується. Як застосунок читає індекс — у [INDEX.md](INDEX.md).

Ключ підпису даних живе лише в Keychain на Mac видавця: застосунок довіряє тільки сувоям, підписаним ним. `keygen` ніколи не замінює наявний ключ, бо тоді всі встановлені застосунки відкидали б нові дані. Пробна збірка (`--test-key`) підписується тимчасовим ключем, який ніде не зберігається, і не витрачає номер стану.

Після збирання поруч лежить `build-report.json`: лише числа (скільки документів, що пропущено, які класи й види порталу ще невідомі), без тексту документів.

Список усіх документів — один великий файл порталу (близько 52 МБ, чверть денного ліміту). Тому збирач бере його не частіше ніж раз на тиждень і лише тоді, коли весь файл вміщається в залишок дня. `catalog --file doc.txt` бере список з уже завантаженого файлу.

Порядок черги: Конституція, кодекси, закони, постанови й укази, решта чинних документів, нечинні, і наостанок щоденні повідомлення про курси валют. Документ, у якого змінилася редакція, стає в чергу знову.

Стан зберігається в теці `work` (база `collect.db`, журнал `log.txt`, список `doc.txt`). Запуск можна перервати будь-коли: наступний продовжить з того самого місця. У журналі лише адреси документів і розміри відповідей.

## Тести

```
python -m pip install ".[test]"
python -m pytest
```

Тести не звертаються до порталу: вони працюють зі збереженою сторінкою і з малим сервером на цьому ж комп'ютері.

---

## English

The collector runs on the publisher's computer, not on GitHub servers. It follows the [portal's rules](https://data.rada.gov.ua/open/main/api/page3):

- it names itself as the portal asks (`OpenData`) and talks only to `data.rada.gov.ua` and `zakon.rada.gov.ua`;
- it waits 5–7 seconds between any two requests;
- it uses at most 90 % of the daily allowance (180 MB and 90,000 requests, the day by Kyiv time);
- after the first refusal (403 or 429) it makes no requests for a day;
- after three network failures in a row it rests for three hours;
- it never runs twice at the same time;
- the list of all documents (one file of about 52 MB) is taken at most once a week, and only when the whole file fits into what is left of the day.

All these numbers live in one file: `src/chynnist_collect/rules.py`.

Commands: `chynnist-collect keygen` (once: the data signing key, kept only in the macOS Keychain), `chynnist-collect build <file> [--test-key]` (a signed scroll from what has been downloaded; a trial build uses a throwaway key), `chynnist-collect release <file>` (prepare a signed index and the month's base or patches in `work/outbox`, see [INDEX.md](INDEX.md)), `chynnist-collect catalog` (refresh the list of all documents and the queue), `chynnist-collect add <number>…`, `chynnist-collect run --minutes 55`, `chynnist-collect status`. The queue goes: the Constitution, codes, laws, resolutions and decrees, other documents in force, documents not in force, and daily exchange rate notices last. A document whose edition has changed is queued again. The state is kept in the `work` folder; a run can be interrupted at any moment and the next one continues from the same place. The journal holds only document addresses and answer sizes.

The tests never contact the portal: they use a saved page and a small server on the same computer.
