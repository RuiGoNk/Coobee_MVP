"""
Сервисный слой модуля «Тайный Санта».

Структура:
- visibility.py   — применение visibility к анкете, превью для Санты
- prefill.py      — prefill анкеты из user_profiles
- draw.py         — жеребьёвка (случайная / цепочка) с учётом Exclusion
- suggestions.py  — генерация подборки идей из catalog (6 + 4)
- access.py       — проверки доступа (get_current_santa, get_current_organizer)
- notifications.py — создание in-app + Telegram уведомлений
"""