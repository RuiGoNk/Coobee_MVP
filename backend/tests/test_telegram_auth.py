import hashlib
import hmac
import time

from app.core.security import validate_telegram_hash

BOT_TOKEN = "123456:TEST_TOKEN_FOR_HASH"


def make_hash(data: dict, bot_token: str = BOT_TOKEN) -> str:
    pairs = [f"{k}={v}" for k, v in data.items() if k != "hash" and v is not None]
    pairs.sort()
    dcs = "\n".join(pairs)
    secret = hashlib.sha256(bot_token.encode()).digest()
    return hmac.new(secret, dcs.encode(), hashlib.sha256).hexdigest()


def test_valid_hash():
    data = {
        "id": 123456789,
        "first_name": "Test",
        "username": "testuser",
        "auth_date": int(time.time()),
    }
    data["hash"] = make_hash(data)
    assert validate_telegram_hash(data, BOT_TOKEN) is True


def test_invalid_hash():
    data = {
        "id": 123456789,
        "first_name": "Test",
        "auth_date": int(time.time()),
        "hash": "deadbeef" * 8,
    }
    assert validate_telegram_hash(data, BOT_TOKEN) is False


def test_tampered_field():
    data = {
        "id": 123456789,
        "first_name": "Test",
        "auth_date": int(time.time()),
    }
    data["hash"] = make_hash(data)
    data["first_name"] = "Hacker"  # подмена после подписи
    assert validate_telegram_hash(data, BOT_TOKEN) is False


def test_expired_auth_date():
    data = {
        "id": 123456789,
        "first_name": "Test",
        "auth_date": int(time.time()) - 90000,  # > 24ч
    }
    data["hash"] = make_hash(data)
    assert validate_telegram_hash(data, BOT_TOKEN) is False