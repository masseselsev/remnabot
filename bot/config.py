import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr, Field, field_validator
from typing import List, Optional, Any

class Settings(BaseSettings):
    bot_token: SecretStr
    
    # Remnawave
    remnawave_url: str
    remnawave_api_key: SecretStr
    
    # Database
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    
    # Payments
    payment_provider_token_stars: Optional[SecretStr] = None
    payment_provider_token_yookassa: Optional[SecretStr] = None
    payment_provider_token_platega: Optional[SecretStr] = None
    payment_provider_token_tribute: Optional[SecretStr] = None
    
    # Webhook
    webhook_url: Optional[str] = None
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8000

    # Admin
    admin_group_id: int
    admin_ids: List[int] = Field(default_factory=list)

    @field_validator("admin_ids", mode="before")
    @classmethod
    def parse_admin_ids(cls, v: Any) -> List[int]:
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(",") if x.strip()]
        if isinstance(v, int):
            return [v]
        return v

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password.get_secret_value()}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

config = Settings()
