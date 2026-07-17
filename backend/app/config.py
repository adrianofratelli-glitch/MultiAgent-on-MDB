from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Configuração central; segredos vêm somente do ambiente."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    mongodb_uri: str = ""
    mongodb_db: str = "multi_agent_poc"
    mongodb_brain_db: str = "ai_brain"
    anthropic_api_key: str = ""
    jwt_secret: str = "desenvolvimento-inseguro-troque-este-segredo"
    jwt_ttl_minutes: int = 60
    auth_required: bool = True
    admin_api_key: str = "admin-demo"
    global_turn_token_budget: int = 6000
    turn_deadline_seconds: int = 120
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60
    log_json: bool = False
    demo_mode: bool = False
    cors_origins: str = "http://127.0.0.1:5191"
    api_host: str = "127.0.0.1"
    api_port: int = 8031
    app_name: str = "multi-agent-poc"
    environment: str = Field(default="development", alias="ENVIRONMENT")

    # Calibrado contra o índice real (voyage-4, quantização escalar): texto idêntico só chega a ~0.84 de
    # score, não 1.0 — um threshold de 0.85+ nunca bateria nem no caso trivial. Não-relacionado mede ~0.64,
    # então a folga real é ~0.20, não os 0.15/0.07 que os números "de catálogo" 0.85/0.93 sugeriam.
    short_term_cache_threshold: float = 0.80
    global_cache_threshold: float = 0.83
    long_term_memory_limit: int = 5
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    @property
    def use_memory_store(self) -> bool:
        return self.demo_mode or not self.mongodb_uri

    @property
    def langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
