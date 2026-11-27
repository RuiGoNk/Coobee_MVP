"""Регрессионные тесты пайплайна. Фикстуры синтетические, данные не нужны."""
import pytest

from app.ml.core import (build_query, diversify, from_wb_row, passes,
                         recommend, score, why_code)


def row(**kw):
    base = {
        "sku": "1",
        "title": "Подарочный набор",
        "price": {"discounted": 2000},
        "category_path": ["Красота"],
        "attributes": {},
        "rating": 4.8,
        "reviews_count": 100,
        "delivery": {"days_min": 2, "days_max": 5},
        "availability": "in_stock",
    }
    base.update(kw)
    return from_wb_row(base)


def profile(**kw):
    base = {"budget_min": 1000, "budget_max": 5000, "occasion": "birthday",
            "relationship": "mother", "gender": "female", "interests": []}
    base.update(kw)
    return base


# ---------------------------------------------------------------- бюджет
def test_budget_steps_1_0_fails_1_2_fails_2_0_passes():
    rec = row(price={"discounted": 1500})
    p = profile(budget_min=1000, budget_max=1200)
    assert not passes(rec, p, 1.0)
    assert not passes(rec, p, 1.2)      # 1200 * 1.2 = 1440 < 1500
    assert passes(rec, p, 2.0)          # 2400 >= 1500


def test_budget_within_20_percent_passes():
    rec = row(price={"discounted": 1300})
    assert passes(rec, profile(budget_min=1000, budget_max=1200), 1.2)


# --------------------------------------------------------------- доставка
def test_delivery_uses_days_min_not_max():
    rec = row(delivery={"days_min": 2, "days_max": 14})
    assert passes(rec, profile())


def test_delivery_days_min_over_7_filtered():
    rec = row(delivery={"days_min": 8, "days_max": 10})
    assert not passes(rec, profile())


def test_delivery_unknown_passes():
    rec = row(delivery={})
    assert passes(rec, profile())


# ---------------------------------------------------------------- рейтинг
@pytest.mark.parametrize("rating,expected", [(4.5, False), (4.6, True),
                                             (4.9, True), (None, True)])
def test_rating_threshold_4_6(rating, expected):
    assert passes(row(rating=rating), profile()) is expected


# ------------------------------------------------------------------- дети
def test_child_age_blocks_older_toy():
    rec = row(title="Конструктор", category_path=["Игрушки"],
              attributes={"Возрастные ограничения": "6+"})
    assert not passes(rec, profile(child_age=3))


def test_child_age_allows_matching_toy():
    rec = row(title="Погремушка Совенок, 0+", category_path=["Игрушки"])
    assert passes(rec, profile(child_age=3))


def test_child_age_blocks_non_toy_without_age():
    rec = row(title="Торшер", category_path=["Освещение"], attributes={})
    assert not passes(rec, profile(child_age=3))


def test_adult_does_not_get_kids_items():
    rec = row(title="Меховые наушники Единорог с ушками",
              category_path=["Аксессуары"])
    assert not passes(rec, profile(child_age=None))


# ------------------------------------------------------------ не-подарки
@pytest.mark.parametrize("title,expected", [
    ("Стельки с подогревом многоразовые", False),
    ("Кабель USB Type-C 1 м", False),
    ("Магнитный держатель для телефона", True),
    ("беспроводной Наушники TWS FreeBuds SE 2", True),
    ("Беспроводные наушники с кошачьими ушками", True),
    ("Кружка с подогревом и беспроводной зарядкой", True),
])
def test_non_gift_filter(title, expected):
    assert passes(row(title=title), profile()) is expected


# ------------------------------------------------------------------- пол
def test_gender_filters_male_marked_item_for_female():
    rec = row(title="Набор для шашлыка подарочный для мужчин")
    assert not passes(rec, profile(gender="female"))


def test_gender_filters_female_marked_item_for_male():
    rec = row(title="Бомбочки для ванны подарок для девушки")
    assert not passes(rec, profile(gender="male"))


# ------------------------------------------------------------ разнообразие
def test_mmr_caps_two_per_category():
    """Когда категорий хватает — кэп 2 на категорию соблюдается."""
    beauty = [row(sku=f"b{i}", category_path=["Красота"]) for i in range(5)]
    toys = [row(sku=f"t{i}", category_path=["Игрушки"]) for i in range(5)]
    home = [row(sku=f"h{i}", category_path=["Освещение"]) for i in range(5)]
    ranked = [(r, 1.0 - i * 0.01) for i, r in enumerate(beauty + toys + home)]
    picked = diversify(ranked, 5)
    assert len(picked) == 5
    cats = [r["category_path"][0] for r, _ in picked]
    assert max(cats.count(c) for c in set(cats)) <= 2


def test_mmr_fills_output_when_categories_are_few():
    """Если категорий мало — лучше 5 товаров с повтором, чем 4 (пустой экран хуже)."""
    beauty = [row(sku=f"b{i}", category_path=["Красота"]) for i in range(5)]
    toys = [row(sku=f"t{i}", category_path=["Игрушки"]) for i in range(5)]
    ranked = [(r, 1.0 - i * 0.01) for i, r in enumerate(beauty + toys)]
    picked = diversify(ranked, 5)
    assert len(picked) == 5
    cats = [r["category_path"][0] for r, _ in picked]
    assert cats.count("Красота") >= 2 and cats.count("Игрушки") >= 2


# ---------------------------------------------------------------- пайплайн
def test_empty_pool_gives_reason_not_exception():
    out = recommend(profile(budget_min=100, budget_max=200),
                    [row(price={"discounted": 2000})])
    assert out["items"] == []
    assert out["reason"] == "no_candidates"


def test_build_query_uses_canonical_tags():
    q = build_query(profile(interests=["cooking"], occasion="new_year",
                            relationship="mother"))
    assert "кулинария" in q and "новый год" in q and "мама" in q


def test_why_code_interest_match():
    rec = row(category_path=["Посуда и инвентарь"])
    assert why_code(rec, profile(interests=["cooking"])) == "matches_interest"


def test_score_is_deterministic():
    rec, p = row(), profile(interests=["beauty"])
    assert score(rec, p) == score(rec, p)

# ------------------------------------------------------- повод в названии
@pytest.mark.parametrize("title,occasion,expected", [
    ("Бомбочки для ванны набор Новогодние подарок для девушки", "birthday", False),
    ("Бомбочки для ванны набор Новогодние подарок для девушки", "new_year", True),
    ("Кружка с подогревом", "birthday", True),
    ("Подарочный набор косметики", "new_year", True),
    ("Набор 8 марта для женщин", "mar8", True),
    ("Набор 8 марта для женщин", "birthday", False),
])
def test_occasion_mismatch_filter(title, occasion, expected):
    from app.ml.core import occasion_mismatch
    rec = row(title=title)
    assert passes(rec, profile(occasion=occasion)) is expected
    assert occasion_mismatch(rec, profile(occasion=occasion)) is (not expected)


def test_toys_exempt_from_occasion_marker():
    """Ёлочные игрушки на день рождения — норма, не отсекаем."""
    rec = row(title="Новогодний набор елочных игрушек", category_path=["Игрушки"])
    assert passes(rec, profile(occasion="birthday"))

# ------------------------------------------------------------ пол по родству
@pytest.mark.parametrize("gender,relationship,expected", [
    ("unisex", "mother", "female"),
    ("unisex", "husband", "male"),
    ("", "wife", "female"),
    ("any", "father", "male"),
    ("female", "father", "female"),   # явный пол важнее родства
    ("unisex", "colleague", None),
])
def test_resolve_gender(gender, relationship, expected):
    from app.ml.core import _resolve_gender
    assert _resolve_gender({"gender": gender, "relationship": relationship}) == expected


def test_mother_with_unisex_gender_does_not_get_male_item():
    from app.ml.core import _resolve_gender
    p = profile(gender=_resolve_gender({"gender": "unisex", "relationship": "mother"}))
    rec = row(title="Набор для шашлыка подарочный для мужчин в кейсе")
    assert not passes(rec, p)