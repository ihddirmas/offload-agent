import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

VALID_SOURCE_TYPES = {"quick_add", "telegram", "voice", "forward", "llm_session"}
VALID_LANES = {"executor", "delegator", "scheduler"}
VALID_TASK_STATES = {"captured", "scheduled", "awaiting_response", "nudged", "done", "abandoned"}

DEFAULT_SNOOZE_MINUTES = 30


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite+aiosqlite:///offload.db")
    )
    model_provider: str = field(default_factory=lambda: os.getenv("MODEL_PROVIDER", "bedrock"))
    bedrock_model_id: str = field(
        default_factory=lambda: os.getenv(
            "BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0"
        )
    )
    anthropic_model_id: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_MODEL_ID", "claude-sonnet-4-20250514")
    )
    telegram_bot_token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    telegram_chat_id: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    ollama_host: str = field(
        default_factory=lambda: os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    )
    ollama_model_id: str = field(
        default_factory=lambda: os.getenv("OLLAMA_MODEL_ID", "hermes3")
    )


def get_settings() -> Settings:
    return Settings()
