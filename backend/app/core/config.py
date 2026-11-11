from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "test"
    APP_DOMAIN: str = "localhost"
    SECRET_KEY: str
    JWT_ALG: str = "HS256"
    JWT_EXPIRE_DAYS: int = 30
    ADMIN_TOKEN: str

    DATABASE_URL: str

    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_BOT_USERNAME: str = "Coobee_Ai_bot"

    REDIS_URL: str = "redis://redis:6379/0"

    STATIC_DIR: str = "static"
    MAX_IMAGE_MB: int = 5


settings = Settings()