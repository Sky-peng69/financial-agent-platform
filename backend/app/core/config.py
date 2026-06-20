from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://finagent:finagent_dev@localhost:5432/finagent"
    redis_url: str = "redis://localhost:6379/0"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    secret_key: str = "dev-secret-change-in-production"
    tushare_token: str = ""
    debug: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
