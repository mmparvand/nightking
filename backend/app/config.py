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

    subscription_domain: str = Field("localhost", env="SUBSCRIPTION_DOMAIN")
    subscription_port: int = Field(2053, env="SUBSCRIPTION_PORT")
    subscription_scheme: str = Field("https", env="SUBSCRIPTION_SCHEME")

    xray_config_path: str = Field("/var/lib/xray/config.json", env="XRAY_CONFIG_PATH")
    xray_reload_command: str = Field("", env="XRAY_RELOAD_COMMAND")
    xray_status_host: str = Field("xray", env="XRAY_STATUS_HOST")
    xray_inbound_port: int = Field(8443, env="XRAY_INBOUND_PORT")

    ip_limit_window_seconds: int = Field(24 * 3600, env="IP_LIMIT_WINDOW_SECONDS")
    concurrent_window_seconds: int = Field(300, env="CONCURRENT_WINDOW_SECONDS")
    reseller_max_ip_limit: int = Field(10, env="RESELLER_MAX_IP_LIMIT")
    reseller_max_concurrent_limit: int = Field(10, env="RESELLER_MAX_CONCURRENT_LIMIT")
    reseller_max_traffic_limit_bytes: int = Field(10 * 1024 * 1024 * 1024, env="RESELLER_MAX_TRAFFIC_LIMIT_BYTES")

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
