from datetime import date

# Границы диапазонов из анкеты (верхняя граница включительно).
AGE_GROUPS: list[tuple[int, int | None, str]] = [
    (0, 3, "0-3"),
    (4, 6, "4-6"),
    (7, 12, "7-12"),
    (13, 17, "13-17"),
    (18, 25, "18-25"),
    (26, 35, "26-35"),
    (36, 45, "36-45"),
    (46, 55, "46-55"),
    (56, None, "56+"),
]


def age_to_group(age: int) -> str:
    for lo, hi, label in AGE_GROUPS:
        if age >= lo and (hi is None or age <= hi):
            return label
    raise ValueError(f"age out of range: {age}")


def calc_age(birth_date: date, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )


def age_from_year(birth_year: int, today: date | None = None) -> int:
    today = today or date.today()
    return today.year - birth_year