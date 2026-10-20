from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    frontend_origin: str = "http://localhost:3000"
    tavily_api_key: str  # no default, so startup fails if it's missing
    llm_api_key: str  # required, so startup fails fast if missing
    llm_base_url: str = "https://integrate.api.nvidia.com/v1"
    llm_model: str = "nvidia/nemotron-3-super-120b-a12b"
    llm_max_rpm: int = 30
    llm_extra_body: dict = {}  # extra JSON fields sent with every LLM request
    supabase_url: str
    supabase_publishable_key: str
    embedding_cache_dir: str = ".fastembed_cache"


@lru_cache
def get_settings() -> Settings:
    return Settings()