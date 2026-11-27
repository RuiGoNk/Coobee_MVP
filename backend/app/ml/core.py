"""ml_core v0.6 — подбор подарков. Только stdlib.

Зафиксированные правила:
  * бюджет: ослабление +20%, затем x2, выше — никогда
  * доставка: отсекаем по days_min > 7 (2-14 дней проходит)
  * рейтинг: < 4.6 отсекаем; отсутствие рейтинга пропускаем (quality понижен)
  * возраст детей: фильтр не ослабляется никогда
"""
from __future__ import annotations

import json
import math
import re

WB_ROOT_MAP = {
    "красота": "beauty",
    "аксессуары": "accessories", "бижутерия": "accessories",
    "ювелирные украшения": "accessories", "аксессуары для обуви": "accessories",
    "головные уборы": "accessories",
    "аксессуары для электроники": "small_appliances",
    "смартфоны и гаджеты": "small_appliances",
    "телевизоры и аудиотехника": "small_appliances",
    "периферия и аксессуары": "small_appliances",
    "текстиль для дома": "home_comfort", "освещение": "home_comfort",
    "мебель офисная и торговое оборудование": "home_comfort", "мебель": "home_comfort",
    "посуда и инвентарь": "tableware",
    "игрушки": "toys",
    "товары для отдыха и кемпинга": "tourism",
    "книги": "books_boardgames", "настольные игры": "books_boardgames",
    "кофе": "coffee_tea", "чай": "coffee_tea",
    "автотовары": "auto", "хобби": "hobby",
}

INTEREST_MAP = {
    "tech": {"small_appliances": 0.9, "accessories": 0.5},
    "gadgets": {"small_appliances": 0.9, "accessories": 0.5},
    "programming": {"small_appliances": 0.7, "books_boardgames": 0.4},
    "gaming_pc": {"small_appliances": 0.8, "books_boardgames": 0.6},
    "gaming_console": {"small_appliances": 0.8, "books_boardgames": 0.6},
    "board_games": {"books_boardgames": 1.0},
    "books_fiction": {"books_boardgames": 1.0, "coffee_tea": 0.3},
    "books_nonfiction": {"books_boardgames": 1.0, "coffee_tea": 0.3},
    "comics": {"books_boardgames": 0.8},
    "cooking": {"tableware": 0.9, "coffee_tea": 0.5},
    "coffee": {"coffee_tea": 1.0, "tableware": 0.4},
    "tea": {"coffee_tea": 1.0, "tableware": 0.4},
    "gardening": {"home_comfort": 0.6, "hobby": 0.5},
    "home_interior": {"home_comfort": 0.9},
    "art": {"hobby": 0.9, "books_boardgames": 0.4, "accessories": 0.3},
    "handmade": {"hobby": 0.9, "accessories": 0.3},
    "photography": {"small_appliances": 0.8, "hobby": 0.5},
    "travel": {"tourism": 0.9, "accessories": 0.4},
    "hiking": {"tourism": 0.9},
    "fishing": {"tourism": 0.9, "hobby": 0.4},
    "auto": {"auto": 0.9, "small_appliances": 0.3},
    "moto": {"auto": 0.7, "hobby": 0.4},
    "sport_run": {"tourism": 0.5, "accessories": 0.4},
    "sport_gym": {"tourism": 0.4, "accessories": 0.4},
    "sport_yoga": {"home_comfort": 0.4, "accessories": 0.4},
    "sport_ski": {"tourism": 0.7, "accessories": 0.5},
    "fashion": {"accessories": 0.8, "beauty": 0.5},
    "beauty": {"beauty": 0.9},
    "perfume": {"beauty": 0.9},
    "jewelry": {"accessories": 1.0},
    "watches": {"accessories": 0.9},
    "science": {"books_boardgames": 0.8, "hobby": 0.4},
    "diy_tools": {"hobby": 0.7, "small_appliances": 0.4},
    "modeling": {"hobby": 0.8},
    "pets": {},   # зоотоваров в MVP нет — мост честно пустой
}

OCCASION_MAP = {
    "birthday": {"toys": 0.6, "books_boardgames": 0.6, "beauty": 0.5,
                 "accessories": 0.5, "home_comfort": 0.5, "small_appliances": 0.5},
    "new_year": {"home_comfort": 0.8, "coffee_tea": 0.7, "tableware": 0.6, "toys": 0.6},
    "mar8": {"beauty": 0.9, "accessories": 0.6, "home_comfort": 0.5},
    "feb23": {"small_appliances": 0.7, "tourism": 0.6, "hobby": 0.5, "auto": 0.6},
    "wedding": {"tableware": 0.8, "home_comfort": 0.8},
    "anniversary": {"beauty": 0.7, "accessories": 0.7, "home_comfort": 0.6},
    "newborn": {"toys": 0.9, "books_boardgames": 0.4},
    "sep1": {"books_boardgames": 0.9, "toys": 0.5},
    "teacher_day": {"coffee_tea": 0.8, "books_boardgames": 0.7},
    "housewarming": {"home_comfort": 0.9, "tableware": 0.7},
    "just_because": {},
    "other": {},
}

RELATIONSHIP_MAP = {
    "mother": {"beauty": 0.6, "home_comfort": 0.6, "coffee_tea": 0.5},
    "father": {"hobby": 0.6, "small_appliances": 0.5, "tourism": 0.5, "auto": 0.5},
    "wife": {"beauty": 0.8, "accessories": 0.7},
    "girlfriend": {"beauty": 0.8, "accessories": 0.7},
    "husband": {"small_appliances": 0.7, "hobby": 0.6, "auto": 0.5},
    "boyfriend": {"small_appliances": 0.7, "hobby": 0.6},
    "sister": {"beauty": 0.6, "accessories": 0.6, "home_comfort": 0.4},
    "brother": {"small_appliances": 0.5, "hobby": 0.5},
    "friend_f": {"beauty": 0.5, "home_comfort": 0.5, "hobby": 0.5},
    "friend_m": {"hobby": 0.6, "small_appliances": 0.5, "books_boardgames": 0.5},
    "colleague": {"coffee_tea": 0.6, "books_boardgames": 0.4, "accessories": 0.4},
    "boss": {"coffee_tea": 0.5, "accessories": 0.5, "home_comfort": 0.4},
    "subordinate": {"coffee_tea": 0.5, "books_boardgames": 0.4},
    "child": {"toys": 1.0, "books_boardgames": 0.6},
    "self": {},
    "other": {},
}
RELATION_GENDER = {
    "mother": "female", "wife": "female", "girlfriend": "female",
    "sister": "female", "friend_f": "female",
    "father": "male", "husband": "male", "boyfriend": "male",
    "brother": "male", "friend_m": "male",
}
FORMAL_RELATIONS = {"boss", "subordinate", "colleague"}
WORK_MARKERS = ("офис", "работ", "настольн", "кружк", "термокружк", "органайзер",
                "ежедневник", "ручк", "мыш", "клавиатур", "подогрев")
WORK_RELATIONS = {"colleague", "boss", "subordinate"}
_NON_GIFT_RE = re.compile(
    r"\b(стельк\w*|кабел\w*|провод\w*|клипс\w*|стяжк\w*|чистящ\w*|салфетк\w*|"
    r"губк\w*|батарейк\w*|переходник\w*|адаптер\w*|креплени\w*|насадк\w*|фильтр\w*)\b"
)
OCCASION_TITLE_MARKERS = {
    "новогодн": {"new_year"},
    "новый год": {"new_year"},
    "рождеств": {"new_year"},
    "8 марта": {"mar8"},
    "23 февраля": {"feb23"},
    "свадебн": {"wedding"},
    "годовщин": {"anniversary"},
    "выпускн": {"sep1"},
    "школьн": {"sep1", "teacher_day"},
}

# узкие календарные праздники: по ним фильтруем жёстко,
# остальные (НГ, ДР, свадьба) — только буст
HARD_EXCLUSIVE_OCCASIONS = {"mar8", "feb23", "sep1", "teacher_day"}

_OCCASION_TEXT_RE = {
    "new_year": re.compile(
        r"\b(новогодн\w*|ёлочн\w*|елочн\w*|рождеств\w*|новый\s+год\w*|для\s+ёлк\w*|на\s+ёлк\w*)\b"),
    "mar8": re.compile(r"\b(8\s*марта|международный\s+женский\s+день)\b"),
    "feb23": re.compile(r"\b(23\s*февраля|день\s+защитника\w*)\b"),
    "wedding": re.compile(r"\b(свадебн\w*)\b"),
    "anniversary": re.compile(r"\b(годовщин\w*)\b"),
    "sep1": re.compile(r"\b(1\s*сентября|школьн\w*|выпускн\w*)\b"),
    "teacher_day": re.compile(r"\b(день\s+учителя)\b"),
    "housewarming": re.compile(r"\b(новосель\w*)\b"),
}


def record_occasions(record: dict) -> set[str]:
    """Поводы, к которым товар явно привязан. Пусто = универсальный."""
    path = [str(p).lower() for p in (record.get("category_path") or [])]
    attrs = " ".join(str(v).lower() for v in (record.get("attributes") or {}).values())
    text = " ".join([
        str(record.get("title") or "").lower(),
        path[-1] if path else "",
        attrs,
        str(record.get("description") or "").lower()[:400],
    ])
    return {occ for occ, rx in _OCCASION_TEXT_RE.items() if rx.search(text)}

def occasion_mismatch(record: dict, profile: dict) -> bool:
    """True, если в названии зашит чужой повод."""
    title = str(record.get("title") or "").lower()
    occasion = profile.get("occasion") or ""
    for marker, allowed in OCCASION_TITLE_MARKERS.items():
        if marker in title and occasion and occasion not in allowed:
            return True
    return False


def is_non_gift(record: dict) -> bool:
    title = str(record.get("title") or "").lower().replace("беспровод", "беспров_")
    return bool(_NON_GIFT_RE.search(title))

BUDGET_NUM = {"symbolic": (0, 1000), "standard": (1000, 5000),
              "solid": (5000, 15000), "premium": (15000, None)}

WEIGHTS = {"interest": 0.30, "occasion": 0.20, "relation": 0.15, "quality": 0.07}
MIN_RATING = 4.6
MAX_DELIVERY_DAYS = 7
BUDGET_STEPS = (1.0, 1.2, 2.0)
TAG_RU = {
    "cooking": "кулинария посуда рецепты готовка",
    "coffee": "кофе кофемашина турка",
    "tea": "чай чайник заварка",
    "gardening": "сад растения горшки",
    "home_interior": "дом интерьер уют декор",
    "books_fiction": "книга роман чтение",
    "books_nonfiction": "книга чтение",
    "board_games": "настольная игра",
    "tech": "гаджет техника устройство",
    "gaming_console": "игровая приставка геймпад",
    "gaming_pc": "игровая мышь клавиатура",
    "art": "рисование краски кисти",
    "handmade": "рукоделие набор творчество",
    "photography": "фотоаппарат фотография",
    "travel": "путешествие чемодан термос",
    "hiking": "поход туризм рюкзак",
    "fishing": "рыбалка снасти",
    "auto": "автомобиль авто",
    "moto": "мотоцикл мото",
    "sport_ski": "лыжи сноуборд",
    "sport_gym": "фитнес тренировка",
    "sport_yoga": "йога коврик",
    "beauty": "косметика красота уход",
    "perfume": "парфюм аромат духи",
    "jewelry": "украшение серебро золото",
    "watches": "часы наручные",
    "fashion": "аксессуар стиль сумка",
    "science": "наука набор опытов",
    "music_instruments": "музыка инструмент",
}
OCCASION_RU = {
    "new_year": "новый год праздник подарок",
    "birthday": "день рождения подарок",
    "mar8": "8 марта цветы женский",
    "feb23": "23 февраля мужской",
    "wedding": "свадьба подарок",
    "housewarming": "новоселье дом",
    "sep1": "школа учеба",
    "teacher_day": "учитель школа",
}
RELATION_RU = {
    "mother": "мама маме", "father": "папа папе",
    "wife": "жена жене", "girlfriend": "девушка",
    "husband": "муж мужу", "boyfriend": "парень",
    "sister": "сестра сестре", "brother": "брат брату",
    "friend_f": "подруга подруге", "friend_m": "друг другу",
    "colleague": "коллега работе", "boss": "начальник офис",
    "child": "ребенок детский игрушка",
}


def build_query(profile: dict) -> str:
    """Профиль -> текстовый запрос. Позже сюда встанет LLM (query expansion)."""
    parts: list[str] = []
    for tag in profile.get("interests") or []:
        if TAG_RU.get(tag):
            parts.append(TAG_RU[tag])
    parts.append(OCCASION_RU.get(profile.get("occasion") or "", ""))
    parts.append(RELATION_RU.get(profile.get("relationship") or "", ""))
    if profile.get("child_age") is not None:
        parts.append("детский ребенок")
    return " ".join(p for p in parts if p).strip()
KID_MARKERS = ("детск", "для детей", "для девочек", "для мальчиков",
               "единорог", "погремушк", "0+", "1+", "2+", "3+")
MALE_MARKERS = ("для мужчин", "мужск")
FEMALE_MARKERS = ("для женщин", "женск", "для девочек", "для девушки", "девушк")


def load_jsonl(path: str) -> list[dict]:
    path = str(path).strip().strip('"').rstrip("\\/")   # защита от лишнего слэша
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


CATEGORIES = ("accessories", "beauty", "home_comfort", "tableware",
              "small_appliances", "toys", "tourism", "books_boardgames",
              "coffee_tea", "auto", "hobby")


def category_of(record: dict) -> str | None:
    for raw in record.get("category_path") or []:
        key = str(raw).strip().lower()
        if key in CATEGORIES:
            return key
        if key in WB_ROOT_MAP:
            return WB_ROOT_MAP[key]
        for prefix, cat in WB_ROOT_MAP.items():
            if key.startswith(prefix):
                return cat
    return None


def age_min_of(record: dict) -> float | None:
    for k, v in (record.get("attributes") or {}).items():
        if "озраст" in str(k).lower():
            m = re.search(r"(\d+[.,]?\d*)", str(v))
            if m:
                return float(m.group(1).replace(",", "."))
    for field in ("title", "slug"):
        text = str(record.get(field) or "")
        m = re.search(r"\b(\d{1,2})\s*\+", text) or re.search(r"от\s*(\d+[.,]?\d*)", text)
        if m:
            return float(m.group(1).replace(",", "."))
    return None


def _recover_rating(row: dict) -> float | None:
    r = row.get("rating")
    if r:
        return float(r)
    dist = row.get("reviews_distribution")
    if isinstance(dist, dict) and dist:
        total = sum(v for v in dist.values() if isinstance(v, (int, float)))
        if total:
            return round(sum(float(k) * float(v) for k, v in dist.items()
                             if isinstance(v, (int, float))) / total, 2)
    return None


def from_wb_row(row: dict) -> dict:
    price = (row.get("price") or {}).get("discounted")
    return {
        "external_id": row.get("sku"),
        "title": row.get("title"),
        "description": row.get("description") or "",
        "price_min": price,
        "price_max": price,
        "category_path": row.get("category_path") or [],
        "attributes": row.get("attributes") or {},
        "slug": (row.get("identifiers") or {}).get("slug"),
        "rating": _recover_rating(row),
        "reviews_count": row.get("reviews_count") or 0,
        "delivery_days_min": (row.get("delivery") or {}).get("days_min"),
        "in_stock": row.get("availability") != "out_of_stock",
    }

def from_db_item(item) -> dict:
    """CatalogItem (SQLAlchemy) -> внутренняя запись."""
    details = item.details or {}
    rating = details.get("rating")
    if rating is None:
        rating = _recover_rating({"reviews_distribution": details.get("reviews_distribution")})
    category_path = details.get("category_path") or []
    if not category_path and item.tags:
        category_path = [str(t) for t in item.tags]
    return {
        "external_id": item.external_id or str(item.id),
        "title": item.title,
        "description": item.description or "",
        "price_min": item.price_min,
        "price_max": item.price_max,
        "category_path": category_path,
        "attributes": details.get("attributes") or {},
        "slug": details.get("slug"),
        "rating": rating,
        "reviews_count": details.get("reviews_count") or 0,
        "delivery_days_min": (details.get("delivery") or {}).get("days_min"),
        "in_stock": bool(item.is_available),
    }


WHY_TEXT = {
    "matches_interest": "совпадает с интересами получателя",
    "matches_occasion": "уместно к поводу",
    "matches_relation": "подходит для этого человека",
    "popular_in_category": "популярный выбор в категории",
}


def why_text(code: str | None) -> str | None:
    return WHY_TEXT.get(code or "")

# сильные маркеры детского товара в описании
KID_DESC_MARKERS = ("детск", "для девочек", "для девочки", "для мальчиков",
                    "для мальчика", "малышк", "принцесс", "для детей",
                    "ребенку", "ребёнку", "малыша")


def is_kids_item(record: dict) -> bool:
    """Детский товар: маркер в названии ИЛИ несколько сильных маркеров в описании."""
    title = str(record.get("title") or "").lower()
    if any(m in title for m in KID_MARKERS):
        return True
    desc = str(record.get("description") or "").lower()[:700]
    if not desc:
        return False
    hits = sum(1 for m in KID_DESC_MARKERS if m in desc)
    return hits >= 2 or "детск" in desc

def text_gender(record: dict) -> str | None:
    """Пол по названию И описанию. None = унисекс или не определить."""
    text = (str(record.get("title") or "") + " "
            + str(record.get("description") or "")[:600]).lower()
    if "унисекс" in text:
        return None
    has_f = any(m in text for m in FEMALE_MARKERS)
    has_m = any(m in text for m in MALE_MARKERS)
    if has_f and has_m:
        return None
    if has_f:
        return "female"
    if has_m:
        return "male"
    return None

def passes(record: dict, profile: dict, budget_mult: float = 1.0) -> bool:
    lo = float(profile.get("budget_min") or 0)
    hi_raw = profile.get("budget_max")
    hi = float(hi_raw) * budget_mult if hi_raw else math.inf

    pmin, pmax = record.get("price_min"), record.get("price_max")
    if pmin is None:
        return False
    pmax = pmax or pmin
    if not (lo <= pmax and pmin <= hi):
        return False

    dmin = record.get("delivery_days_min")
    if dmin is not None and dmin > MAX_DELIVERY_DAYS:
        return False

    rating = record.get("rating")
    if rating is not None and rating < MIN_RATING:
        return False

    if not record.get("in_stock", True):
        return False

    child_age = profile.get("child_age")
    if child_age is not None and child_age < 18:
        amin, cat = age_min_of(record), category_of(record)
        if amin is None and cat not in {"toys", "books_boardgames"}:
            return False
        if amin is not None and child_age < amin:
            return False

    if profile.get("relationship") in FORMAL_RELATIONS and category_of(record) == "beauty":
        return False
    title = str(record.get("title") or "").lower()
    if profile.get("child_age") is None:          # взрослому — не детское
        if is_kids_item(record):
            return False
    gender = profile.get("gender")
    if gender in {"male", "female"}:
        tg = text_gender(record)
        if tg is not None and tg != gender:
            return False
    if is_non_gift(record):
        return False
    explicit = record_occasions(record)
    wanted = profile.get("occasion") or ""
    if explicit and wanted and wanted not in explicit:
        # жёстко отсекаем только узкие календарные праздники
        if (explicit & HARD_EXCLUSIVE_OCCASIONS) and category_of(record) != "toys":
            return False
    return True


def _map_weights(values, table) -> dict[str, float]:
    out: dict[str, float] = {}
    for v in values or []:
        for cat, w in (table.get(str(v).strip().lower(), {}) or {}).items():
            out[cat] = max(out.get(cat, 0.0), w)
    return out


def score(record: dict, profile: dict) -> float:
    """Итоговый скор товара. Сумма взвешенных компонент + поправки повода."""
    cat = category_of(record)
    total = 0.0

    # 1. интерес получателя: интерес -> категория -> товар
    total += WEIGHTS["interest"] * _map_weights(
        profile.get("interests"), INTEREST_MAP).get(cat, 0.0)

    # 2. повод: общая матрица "повод -> категория"
    total += WEIGHTS["occasion"] * OCCASION_MAP.get(
        profile.get("occasion") or "", {}).get(cat, 0.0)

    # 3. родство: "кто он вам" -> категория
    total += WEIGHTS["relation"] * RELATIONSHIP_MAP.get(
        profile.get("relationship") or "", {}).get(cat, 0.0)

    # 4. качество: рейтинг + популярность
    rating = record.get("rating")
    reviews = record.get("reviews_count") or 0
    q = 0.3 * (rating / 5.0 if rating else 0.4) + 0.7 * (math.log1p(reviews) / math.log1p(2000))
    total += WEIGHTS["quality"] * min(q, 1.0)

    # 5. офисный контекст (временная эвристика вместо use_context)
    title = str(record.get("title") or "").lower()
    if profile.get("relationship") in WORK_RELATIONS and any(m in title for m in WORK_MARKERS):
        total += 0.12

    # 6. явная привязка к поводу: лист категории + характеристики + описание
    explicit = record_occasions(record)
    wanted = profile.get("occasion") or ""
    if wanted and wanted in explicit:
        total += 0.15       # товар явно к этому поводу — поднимаем
    elif explicit and wanted:
        total -= 0.25       # в товаре зашит чужой повод — опускаем

    return round(total, 4)


def why_code(record: dict, profile: dict) -> str:
    cat = category_of(record)
    if _map_weights(profile.get("interests"), INTEREST_MAP).get(cat):
        return "matches_interest"
    if OCCASION_MAP.get(profile.get("occasion") or "", {}).get(cat):
        return "matches_occasion"
    if RELATIONSHIP_MAP.get(profile.get("relationship") or "", {}).get(cat):
        return "matches_relation"
    return "popular_in_category"


def diversify(ranked, limit: int):
    picked, per_cat = [], {}
    for rec, s in ranked:
        cat = category_of(rec) or "?"
        if per_cat.get(cat, 0) >= 2 and len(picked) < limit:
            continue
        picked.append((rec, s))
        per_cat[cat] = per_cat.get(cat, 0) + 1
        if len(picked) == limit:
            break
    if len(picked) < limit:
        ids = {r["external_id"] for r, _ in picked}
        for rec, s in ranked:
            if rec["external_id"] not in ids:
                picked.append((rec, s))
            if len(picked) == limit:
                break
    return picked[:limit]

def _resolve_gender(recipient: dict) -> str | None:
    """unisex/пусто при известном родстве — берём пол из родства."""
    gender = (recipient.get("gender") or "").strip().lower()
    by_relation = RELATION_GENDER.get(recipient.get("relationship") or "")
    if gender in {"", "unisex", "any"}:
        return by_relation
    return gender

def profile_from_recipient(recipient: dict) -> dict:
    lo, hi = BUDGET_NUM.get(recipient.get("budget_range") or "standard", (1000, 5000))
    details = recipient.get("details") or {}
    child_age = details.get("child_age")
    if child_age is None and recipient.get("relationship") == "child":
        child_age = recipient.get("age")
    return {
        "interests": details.get("interests") or [],
        "occasion": recipient.get("occasion") or "just_because",
        "relationship": recipient.get("relationship") or "other",
        "age": recipient.get("age"),
        "gender": _resolve_gender(recipient),
        "child_age": child_age,
        "budget_min": lo,
        "budget_max": hi,
    }


def recommend(profile: dict, records: list[dict], limit: int = 5, index=None) -> dict:
    """index — Index из app.ml.retrieval; без него поиск не используется."""
    pool, step = [], 1.0
    for step in BUDGET_STEPS:
        pool = [r for r in records if passes(r, profile, step)]
        if len(pool) >= limit:
            break
    if not pool:
        return {"items": [], "reason": "no_candidates", "budget_step": step,
                "candidates": 0, "hints": ["Расширьте бюджет или измените повод"]}

    # BM25 по всему каталогу, затем оставляем только прошедших фильтры
    query = build_query(profile)
    bm25: dict[str, float] = {}
    if index is not None and query:
        bm25 = {rec["external_id"]: s for rec, s in index.search(query, k=len(records))}

    pool_ids = {r["external_id"] for r in pool}
    bm25 = {k: v for k, v in bm25.items() if k in pool_ids}

    ranked = []
    for rec in pool:
        base = score(rec, profile)
        rel = bm25.get(rec["external_id"], 0.0)
        total = round(0.75 * base + 0.25 * rel, 4) if bm25 else base
        ranked.append((rec, total))
    ranked.sort(key=lambda x: x[1], reverse=True)

    items = []
    for pos, (rec, s) in enumerate(diversify(ranked, limit), 1):
        items.append({
            "position": pos, "external_id": rec["external_id"], "title": rec["title"],
            "price": rec.get("price_min"), "category": category_of(rec),
            "score": s, "why_code": why_code(rec, profile),
            "retrieval": round(bm25.get(rec["external_id"], 0.0), 3),
            "over_budget": bool(profile.get("budget_max")
                                and (rec.get("price_min") or 0) > profile["budget_max"]),
        })
    return {"items": items, "budget_step": step, "candidates": len(pool),
            "query": query, "retrieval_used": bool(bm25)}


def demo(path: str) -> None:
    records = [from_wb_row(r) for r in load_jsonl(path)]
    from .retrieval import Index
    index = Index.build([from_wb_row(r) for r in load_jsonl(path)])
    recipients = [
        {"name": "маме 58, ДР, standard", "relationship": "mother", "occasion": "birthday",
         "gender": "female", "age": 58, "budget_range": "standard",
         "details": {"interests": ["cooking", "gardening"]}},
        {"name": "другу 27, НГ, symbolic", "relationship": "friend_m", "occasion": "new_year",
         "gender": "male", "age": 27, "budget_range": "symbolic", "details": {}},
        {"name": "ребёнку 3 года, symbolic", "relationship": "child", "occasion": "birthday",
         "gender": "unisex", "age": 3, "budget_range": "symbolic", "details": {"interests": []}},
        {"name": "коллеге 40, 8 марта, standard", "relationship": "colleague", "occasion": "mar8",
         "gender": "female", "age": 40, "budget_range": "standard", "details": {}},
    ]
    for rec in recipients:
        out = recommend(profile_from_recipient(rec), records, index=index)
        print(f"\n== {rec['name']}: кандидатов {out['candidates']}, шаг x{out['budget_step']}")
        if not out["items"]:
            print(f"   пусто: {out.get('reason')} | {out.get('hints')}")
        for it in out["items"]:
            flag = "  [выше бюджета]" if it["over_budget"] else ""
            print(f"   {it['position']}. {str(it['title'])[:50]:52} {it['price'] or 0:>6.0f}₽ "
                  f"{str(it['category']):<17} {it['score']:.3f} {it['why_code']}{flag}")


if __name__ == "__main__":
    import sys
    demo(sys.argv[1] if len(sys.argv) > 1 else "items.jsonl")