from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    database_url: str
    redis_url: str
    hmac_key: str
    totp_enc_key: str
    cookie_secure: bool = False        # True in production (NFR4)
    session_idle_minutes: int = 30     # A40
    session_absolute_hours: int = 8    # A40
    pending_mfa_minutes: int = 5

settings = Settings()