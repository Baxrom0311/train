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

    # Frontend domenlari (vergul bilan ajratilgan). Bo'sh qoldirilsa CORS
    # umuman ochilmaydi (xavfsiz default) — "*" + credentials birikmasi
    # ataylab qo'llanilmaydi.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

settings = Settings()
