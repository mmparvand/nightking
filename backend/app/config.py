import os
from functools import lru_cache
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = Field("Nightking VPN Panel", env="APP_NAME")
    environment: str = Field("development", env="ENVIRONMENT")
    secret_key: str = Field("dev-insecure-secret-change-me", env="SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    access_token_expires_minutes: int = Field(60, env="ACCESS_TOKEN_EXPIRES_MINUTES")
    allow_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    admin_username: str = Field("admin", env="ADMIN_USERNAME")
    admin_password: str = Field("changeme", env="ADMIN_PASSWORD")
    admin_role: str = Field("ADMIN", env="ADMIN_ROLE")
    reseller_username: str = Field("", env="RESELLER_USERNAME")
    reseller_password: str = Field("", env="RESELLER_PASSWORD")

    postgres_user: str = Field("postgres", env="POSTGRES_USER")
    postgres_password: str = Field("postgres", env="POSTGRES_PASSWORD")
    postgres_db: str = Field("nightking", env="POSTGRES_DB")
    postgres_host: str = Field("db", env="POSTGRES_HOST")
    postgres_port: int = Field(5432, env="POSTGRES_PORT")
    redis_url: str = Field("redis://redis:6379/0", env="REDIS_URL")
    database_url: str = Field("postgresql+psycopg2://postgres:postgres@db:5432/nightking", env="DATABASE_URL")

    class Config:
        env_file = os.getenv("ENV_FILE", ".env")
        case_sensitive = False

    @model_validator(mode="before")
    @classmethod
    def parse_allow_origins(cls, values: dict) -> dict:
        origins = values.get("allow_origins")
        if isinstance(origins, str):
            values["allow_origins"] = [o.strip() for o in origins.split(",") if o.strip()]
        return values


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
