"""Settings and configuration loader."""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


class Settings:
    """Load and manage application settings."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / "data"
        self.config_dir = self.project_root / "config"
        self.secrets_dir = self.project_root / "secrets"
        self.logs_dir = self.project_root / "logs"

        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.secrets_dir.mkdir(exist_ok=True)

        # Load .env
        env_file = self.project_root / ".env"
        load_dotenv(env_file)

        # Gmail settings
        self.gmail_credentials_path = Path(
            os.getenv("GMAIL_CREDENTIALS_PATH", str(self.secrets_dir / "credentials.json"))
        )
        self.gmail_token_path = Path(
            os.getenv("GMAIL_TOKEN_PATH", str(self.secrets_dir / "token.json"))
        )

        # Backfill and sync
        self.backfill_since = os.getenv("BACKFILL_SINCE", "2024-01-01")
        self.sync_overlap_days = int(os.getenv("SYNC_OVERLAP_DAYS", "3"))

        # LLM settings
        self.llm_provider = os.getenv("LLM_PROVIDER", "anthropic")
        self.llm_model = os.getenv("LLM_MODEL", "")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

        # Database path
        self.db_path = self.data_dir / "ccstmt.duckdb"

        # Load issuers config
        self.issuers = self._load_issuers()

    def _load_issuers(self) -> list[dict]:
        """Load issuer configuration from YAML."""
        issuers_file = self.config_dir / "issuers.yaml"
        if not issuers_file.exists():
            return []

        with open(issuers_file) as f:
            data = yaml.safe_load(f)
            return data.get("issuers", []) if data else []

    def get_issuer_password(self, issuer_id: str) -> Optional[str]:
        """Get password for an issuer from env vars."""
        env_var = f"CC_PWD_{issuer_id.upper()}"
        return os.getenv(env_var)


# Global settings instance
settings = Settings()
