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
- не працює у два вікна одночасно.

Усі ці числа зібрано в одному файлі: `src/chynnist_collect/rules.py`.

## Команди

```
chynnist-collect add 254к/96-вр 2341-14    # додати документи до черги
chynnist-collect run --minutes 55          # завантажувати, доки є час і ліміт
chynnist-collect status                    # що зроблено і що чекає
```

Стан зберігається в теці `work` (база `collect.db`, журнал `log.txt`). Запуск можна перервати будь-коли: наступний продовжить з того самого місця. У журналі лише адреси документів і розміри відповідей.

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
- it never runs twice at the same time.

All these numbers live in one file: `src/chynnist_collect/rules.py`.

Commands: `chynnist-collect add <number>…`, `chynnist-collect run --minutes 55`, `chynnist-collect status`. The state is kept in the `work` folder; a run can be interrupted at any moment and the next one continues from the same place. The journal holds only document addresses and answer sizes.

The tests never contact the portal: they use a saved page and a small server on the same computer.
