from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "资产评估项目流程管理系统 API"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    app_port: int = 8080

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/asset_flow"

    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 8

    initial_admin_username: str = "admin"
    initial_admin_password: str = "zhongqin123"
    initial_admin_real_name: str = "系统管理员"


settings = Settings()
