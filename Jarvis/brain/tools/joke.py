import random

import pyjokes


def spec():
    return {
        "name": "joke",
        "description": "Tell a joke using a local joke generator/catalog.",
        "args": {"language": "string"},
    }


def run(*, assistant=None, wolfram_fn=None, language=""):
    lang = (language or "").strip().lower()

    # pyjokes has best support in English; provide lightweight curated fallbacks.
    if lang.startswith("ru"):
        jokes = [
            "Почему программист путает Хэллоуин и Рождество? Потому что OCT 31 == DEC 25.",
            "Я не ленивый разработчик. Я просто работаю в режиме энергосбережения.",
            "Вчера исправил один баг. Сегодня появилось два новых. Баланс вселенной сохранен.",
        ]
        return random.choice(jokes)
    if lang.startswith("hy"):
        jokes = [
            "Ծրագրավորողի սուրճը վերջանում է, բայց բագերը՝ ոչ։",
            "Այսօր մեկ բագ փակեցի, երկուսը բացվեցին․ հավասարակշռությունը պահպանվեց։",
            "Կոդը չաշխատեց առաջին անգամ, բայց գոնե վստահ էր, որ ես եմ մեղավոր։",
        ]
        return random.choice(jokes)

    try:
        return pyjokes.get_joke()
    except Exception:
        return "I tried to fetch a joke, but my humor engine is rebooting."
