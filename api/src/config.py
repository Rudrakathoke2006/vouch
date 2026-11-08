from enum import Enum
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class PaymentProviderType(str, Enum):
    MOCK = "mock"
    PAYPAL_SANDBOX = "paypal_sandbox"


class LLMProviderType(str, Enum):
    MOCK = "mock"
    GEMINI = "gemini"


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    DATABASE_URL: str = "postgresql+asyncpg://vouch_user:vouch_password@localhost:5432/vouch_db"
    
    # Payment configuration
    PAYMENT_PROVIDER: PaymentProviderType = PaymentProviderType.MOCK
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_WEBHOOK_ID: Optional[str] = None
    PAYPAL_RECEIVER_EMAIL: Optional[str] = "facilitator@sandbox.paypal.com"
    
    # LLM configuration
    LLM_PROVIDER: LLMProviderType = LLMProviderType.MOCK
    LLM_MODEL: str = "gemini-2.0-flash"
    GEMINI_API_KEY: Optional[str] = None
    
    # App Settings
    JWT_SECRET: str = "vouch_hackathon_super_secret_jwt_key_32_bytes_min"
    UPLOAD_DIR: str = "./uploads"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

