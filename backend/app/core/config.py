from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
import json

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    env: str = "development"
    database_url: str = "postgresql+psycopg://nexis:change_me@localhost:5432/nexis"
    redis_url: str = "redis://localhost:6379/0"

    # Cryptographic keys
    secret_key: str = "nexis_super_secure_random_secret_key_at_least_32_bytes_long"
    hmac_key: str = "nexis_hmac_secret_key_for_recovery_codes_at_least_32_bytes"
    totp_enc_key: str = "eXxBzHmNDOjXGYpGCrNJTe9Du38J-v2pE34_yULBgko="

    # Cookie settings (NFR4, A27)
    cookie_name: str = "nexis_session"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    cookie_httponly: bool = True
    cookie_path: str = "/"

    # Session lifetimes (A40)
    session_idle_minutes: int = 30
    session_absolute_hours: int = 8
    pending_mfa_minutes: int = 5
    recovery_token_minutes: int = 15

    # Rate limiting & Lockout (FR9, A24, A25)
    lockout_threshold: int = 5
    lockout_duration_minutes: int = 15
    rate_limit_login_per_minute: int = 10
    rate_limit_mfa_per_minute: int = 5
    rate_limit_recovery_per_minute: int = 5

    # CORS
    cors_origins: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ]

    def get_cors_origins(self) -> List[str]:
        if isinstance(self.cors_origins, str):
            try:
                parsed = json.loads(self.cors_origins)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return self.cors_origins


settings = Settings()
