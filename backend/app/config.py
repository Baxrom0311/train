from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REDIS_URL: str = "redis://localhost:6379"

    # Run chat fayllari (CONTRACT.md §9.5). Docker'da doimiy volume
    # (`/data/uploads`), lokalda repo ichidagi `uploads/` (.gitignore'da).
    UPLOAD_DIR: str = "uploads"

    # AI provayderlari (CONTRACT.md §9.10, `app/ai/llm.py`). Kalitlar faqat
    # .env'dan; bo'sh kalitli provayder o'tkazib yuboriladi.
    DEEPSEEK_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    LLM_PROVIDERS: str = "deepseek,gemini,openai"   # urinish tartibi
    DEEPSEEK_MODEL: str = "deepseek-chat"
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_MODEL: str = "gpt-4o-mini"
    LLM_TIMEOUT_SECONDS: float = 20.0
    # §21.1: 1M token narxi (USD), "provider=kirish/chiqish,..."; bo'sh — narx hisoblanmaydi
    LLM_PRICES: str = ""
    # §9.0 Q12 — o'lcham `models/scenario.py: EMBEDDING_DIM` bilan bir xil
    EMBEDDING_MODEL: str = "gemini-embedding-001"

    # §18.1: production'da false — /docs, /redoc, /openapi.json yopiladi
    DOCS_ENABLED: bool = True

    # §19.2: talaba kodi runner'i. Bo'sh — lokal rejim (faqat dev/test):
    # skript shu konteynerda, yashirin testlar o'chiq.
    SANDBOX_URL: str = ""
    SANDBOX_TOKEN: str = ""

    # Email bildirishnomalar (CONTRACT.md §15.3). SMTP_HOST bo'sh — email
    # o'chirilgan, faqat ilova ichidagi bildirishnoma ishlaydi.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "TryJob <no-reply@localhost>"
    SMTP_STARTTLS: bool = True
    # Emaildagi havolalar uchun frontend manzili
    PUBLIC_URL: str = "http://localhost:5173"

    # Frontend domenlari (vergul bilan ajratilgan). Bo'sh qoldirilsa CORS
    # umuman ochilmaydi (xavfsiz default) — "*" + credentials birikmasi
    # ataylab qo'llanilmaydi.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def llm_providers_list(self) -> List[str]:
        return [p.strip().lower() for p in self.LLM_PROVIDERS.split(",") if p.strip()]

    @property
    def llm_prices(self) -> dict[str, tuple[float, float]]:
        """`deepseek=0.27/1.10` → {"deepseek": (0.27, 1.10)}; buzuq qism e'tiborsiz qoldiriladi."""
        prices: dict[str, tuple[float, float]] = {}
        for part in self.LLM_PRICES.split(","):
            name, _, pair = part.partition("=")
            price_in, _, price_out = pair.partition("/")
            try:
                prices[name.strip().lower()] = (float(price_in), float(price_out))
            except ValueError:
                continue
        return prices

settings = Settings()
