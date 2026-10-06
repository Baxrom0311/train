import os
from typing import List

# .env faylini o'qish (agar mavjud bo'lsa)
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "TryJob — Virtual Job Simulation Platform")
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development") # development, production, testing
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")
    API_V1_STR: str = "/api/v1"
    
    # Xavfsizlik sozlamalari
    SECRET_KEY: str = os.getenv("SECRET_KEY", "tryjob-super-secret-production-key-2026-uzbekistan-secure-hash-jwt")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120")) # 2 soat
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30")) # 30 kun
    HMAC_CERT_SECRET: str = os.getenv("HMAC_CERT_SECRET", "tryjob-cert-hmac-sha256-signature-key-2026-uzb")
    
    # PostgreSQL & Ma'lumotlar bazasi
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "tryjob_db")

    @property
    def DATABASE_URL(self) -> str:
        explicit_url = os.getenv("DATABASE_URL")
        if explicit_url:
            # Render/Heroku compatibility: postgres:// -> postgresql+psycopg2://
            if explicit_url.startswith("postgres://"):
                return explicit_url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif explicit_url.startswith("postgresql://") and not explicit_url.startswith("postgresql+psycopg2://"):
                return explicit_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            return explicit_url
        
        # Standart SQLite local yoki PostgreSQL
        # Agar env da POSTGRES_SERVER berilgan va default emas bo'lsa yoki ENVIRONMENT == 'production' bo'lsa
        if os.getenv("USE_POSTGRES", "false").lower() in ("true", "1") or self.ENVIRONMENT == "production":
            return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        
        return os.getenv("SQLITE_URL", "sqlite:///./tryjob.db")

    # DB Connection Pool sozlamalari (PostgreSQL Production)
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "10"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "300"))
    DB_POOL_PRE_PING: bool = True

    # CORS sozlamalari
    CORS_ORIGINS_RAW: str = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:8000,https://tryjob.uz"
    )

    @property
    def CORS_ORIGINS(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS_RAW.split(",") if origin.strip()]

    # Cloud AI API Kalitlari (DeepSeek / Gemini / OpenAI)
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Fayllar xavfsizligi va saqlash
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads"))
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "15"))
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx", "xlsx", "txt", "json", "py", "sql", "png", "jpg"]


settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
