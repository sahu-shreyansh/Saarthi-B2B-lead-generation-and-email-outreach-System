from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Database ──────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./saarthi.db"

    # ── Auth ──────────────────────────────────────
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ── Gmail OAuth ───────────────────────────────
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/auth/gmail/callback"

    # ── Stripe ────────────────────────────────────
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_STARTER: str = ""
    STRIPE_PRICE_PRO: str = ""

    # ── LLM ───────────────────────────────────────
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    # ── App ───────────────────────────────────────
    APP_NAME: str = "Saarthi"
    FRONTEND_URL: str = "http://localhost:3000"

    # ── Pipeline ──────────────────────────────────
    MAX_FOLLOWUP_STEPS: int = 3
    FOLLOWUP_INTERVAL_DAYS: int = 3

    # ── External APIs ─────────────────────────────
    SERPAPI_KEY: str = ""
    APIFY_TOKEN: str = ""
    EMAILVERIFY_KEY: str = ""


settings = Settings()
