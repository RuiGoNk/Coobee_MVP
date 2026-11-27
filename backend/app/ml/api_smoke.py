"""Проверка эндпоинта /recommend на реальных данных из БД. Только stdlib.

Запуск внутри контейнера:  python -m app.ml.api_smoke
"""
from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request

from sqlalchemy import select

from app.core.security import create_jwt
from app.db.session import SessionLocal
from app.models.recipient import Recipient
from app.models.user import User

BASE = "http://127.0.0.1:8000/api/v1"


def post_json(url: str, payload: dict, token: str) -> tuple[int, dict | str]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:400]
    except Exception as e:  # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


async def main() -> None:
    async with SessionLocal() as db:
        users = list((await db.execute(select(User))).scalars().all())
        target = None
        for u in users:
            recs = list((await db.execute(
                select(Recipient).where(Recipient.user_id == u.id,
                                        Recipient.is_deleted.is_(False))
            )).scalars().all())
            if recs:
                target = (u, recs)
                break
        if target is None:
            print("нет пользователя с получателями")
            return

    user, recs = target
    token = create_jwt(str(user.id))
    print(f"пользователь {user.id} | получателей {len(recs)}\n")

    for rec in recs:
        print(f"== получатель {rec.name} ({rec.relationship}, {rec.occasion}, "
              f"{rec.budget_range})")
        status, body = await asyncio.to_thread(
            post_json, f"{BASE}/recommend", {"recipient_id": str(rec.id)}, token
        )
        print(f"   HTTP {status}")
        if status != 200 or not isinstance(body, dict):
            print(f"   {body}")
            continue
        for it in body.get("items", []):
            print(f"   {str(it['title'])[:46]:48} {it.get('price_min') or 0:>6}₽ "
                  f"| {it.get('why')}")
        print()


if __name__ == "__main__":
    asyncio.run(main())