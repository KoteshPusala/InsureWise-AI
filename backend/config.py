import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).parent / ".env"
load_dotenv(_env_path, override=True)

class Settings:
    # LLM Configuration
    @property
    def LLM_PROVIDER(self) -> str:
        return os.getenv("LLM_PROVIDER", "groq")

    @property
    def GROQ_API_KEY(self) -> str:
        return os.getenv("GROQ_API_KEY", "")

    @property
    def GROQ_MODEL(self) -> str:
        return os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    @property
    def ANTHROPIC_API_KEY(self) -> str:
        return os.getenv("ANTHROPIC_API_KEY", "")

    @property
    def ANTHROPIC_MODEL(self) -> str:
        return os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    @property
    def OPENAI_API_KEY(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def OPENAI_MODEL(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o")

    # Embedding Configuration
    @property
    def EMBEDDING_PROVIDER(self) -> str:
        return os.getenv("EMBEDDING_PROVIDER", "local")

    @property
    def OPENAI_EMBEDDING_MODEL(self) -> str:
        return os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

    # App Configuration
    @property
    def DEMO_MODE(self) -> bool:
        return os.getenv("DEMO_MODE", "false").lower() == "true"

    @property
    def MAX_UPLOAD_MB(self) -> int:
        return int(os.getenv("MAX_UPLOAD_MB", "15"))

    @property
    def ALLOWED_ORIGINS(self) -> list:
        raw = os.getenv("ALLOWED_ORIGINS", "*")
        if not raw or raw.strip() == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]

    # Chunking
    CHUNK_TARGET_MIN: int = 600
    CHUNK_TARGET_MAX: int = 900
    CHUNK_OVERLAP: int = 100

    # Retrieval
    TOP_K: int = 6
    RELEVANCE_THRESHOLD: float = 0.35

    # Limits
    MAX_PAGES: int = 200
    MAX_HISTORY_TURNS: int = 6
    OCR_MIN_CHARS: int = 30
    BATCH_SIZE: int = 32
    PROCESSING_TIMEOUT_SECONDS: int = 300
    STAGE_TIMEOUT_SECONDS: int = 60

    # Paths (configurable for Render Persistent Disks & test fixtures)
    BACKEND_DIR: Path = Path(__file__).resolve().parent

    _storage_dir: Optional[Path] = None
    _uploads_dir: Optional[Path] = None
    _indexes_dir: Optional[Path] = None
    _reports_dir: Optional[Path] = None
    _db_path: Optional[Path] = None

    @property
    def STORAGE_DIR(self) -> Path:
        if self._storage_dir:
            return self._storage_dir
        custom = os.getenv("STORAGE_DIR")
        return Path(custom) if custom else self.BACKEND_DIR / "storage"

    @STORAGE_DIR.setter
    def STORAGE_DIR(self, val: Path):
        self._storage_dir = Path(val)

    @property
    def UPLOADS_DIR(self) -> Path:
        return self._uploads_dir if self._uploads_dir else self.STORAGE_DIR / "uploads"

    @UPLOADS_DIR.setter
    def UPLOADS_DIR(self, val: Path):
        self._uploads_dir = Path(val)

    @property
    def INDEXES_DIR(self) -> Path:
        return self._indexes_dir if self._indexes_dir else self.STORAGE_DIR / "indexes"

    @INDEXES_DIR.setter
    def INDEXES_DIR(self, val: Path):
        self._indexes_dir = Path(val)

    @property
    def REPORTS_DIR(self) -> Path:
        return self._reports_dir if self._reports_dir else self.STORAGE_DIR / "reports"

    @REPORTS_DIR.setter
    def REPORTS_DIR(self, val: Path):
        self._reports_dir = Path(val)

    @property
    def DB_PATH(self) -> Path:
        return self._db_path if self._db_path else self.STORAGE_DIR / "insurewise.db"

    @DB_PATH.setter
    def DB_PATH(self, val: Path):
        self._db_path = Path(val)

    @property
    def CHECKLIST_PATH(self) -> Path:
        return self.BACKEND_DIR / "config" / "claim_checklists.json"

    def reload_env(self):
        load_dotenv(_env_path, override=True)

    @property
    def active_api_key(self) -> str:
        provider = self.LLM_PROVIDER.lower()
        if provider == "groq":
            return self.GROQ_API_KEY
        elif provider == "openai":
            return self.OPENAI_API_KEY
        return self.ANTHROPIC_API_KEY

    @property
    def active_model(self) -> str:
        provider = self.LLM_PROVIDER.lower()
        if provider == "groq":
            return self.GROQ_MODEL
        elif provider == "openai":
            return self.OPENAI_MODEL
        return self.ANTHROPIC_MODEL

    @property
    def api_key_configured(self) -> bool:
        return bool(self.active_api_key.strip())

    @property
    def is_demo(self) -> bool:
        return self.DEMO_MODE or not self.api_key_configured


settings = Settings()
