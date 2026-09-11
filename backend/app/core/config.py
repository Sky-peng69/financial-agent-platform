from pydantic_settings import BaseSettings


def _fix_database_url(url: str) -> str:
    """Render 注入的 DATABASE_URL 是 postgres://，需要转为 asyncpg 驱动格式"""
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


class Settings(BaseSettings):
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://finagent:finagent_dev@localhost:5432/finagent"
    redis_url: str = "redis://localhost:6379/0"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    secret_key: str = "dev-secret-change-in-production"
    tushare_token: str = ""
    debug: bool = True
    storage_path: str = "./storage"
    max_upload_size_mb: int = 20
    llm_request_timeout_seconds: int = 60

    model_config = {"env_file": ".env", "extra": "ignore"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.database_url = _fix_database_url(self.database_url)

    def validate_runtime_config(self) -> None:
        """拒绝使用不安全的生产环境默认配置。"""
        if self.environment.lower() in {"production", "staging"}:
            if not self.deepseek_api_key:
                raise ValueError("生产环境必须配置 DEEPSEEK_API_KEY")
            if not self.secret_key or self.secret_key == "dev-secret-change-in-production":
                raise ValueError("生产环境必须配置安全的 SECRET_KEY")


settings = Settings()
