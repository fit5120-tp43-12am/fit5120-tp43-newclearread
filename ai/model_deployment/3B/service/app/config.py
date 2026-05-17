from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "clearread-ai-summary"
    service_version: str = "v1"
    public_model_name: str = "clearread-llama32-3b-qlora-phase2-r32-a64-lr1p5e4-epoch4"

    service_api_keys: str = Field(default="", alias="CLEARREAD_AI_SERVICE_API_KEYS")
    request_body_limit_bytes: int = 2 * 1024 * 1024
    max_blocks: int = 32
    max_chars_per_block: int = 11000
    include_error_details: bool = False

    vllm_base_url: str = "http://vllm:8000"
    vllm_api_key: str = ""
    vllm_model: str = "clearread-llama32-3b-qlora"
    vllm_timeout_seconds: float = 90.0
    vllm_max_concurrency: int = 32
    vllm_max_tokens: int = 260
    vllm_temperature: float = 0.0

    log_level: str = "INFO"

    @property
    def api_key_list(self) -> list[str]:
        return [key.strip() for key in self.service_api_keys.split(",") if key.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
