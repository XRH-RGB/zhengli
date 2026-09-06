from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    execution_enabled: bool = False
    app_api_key: str = ""
    github_token: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = ""
    llm_api_key: str = ""
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_model: str = ""
    embedding_api_key: str = ""
    data_dir: str = "data"
    chunk_size: int = Field(1800, ge=300, le=6000)
    chunk_overlap: int = Field(240, ge=0, le=299)
    max_files: int = Field(300, ge=1, le=2000)
    max_file_bytes: int = Field(200000, ge=1024, le=1000000)
    max_chunks: int = Field(5000, ge=1, le=20000)
    max_context_chars: int = Field(16000, ge=2000, le=60000)
    request_timeout: int = Field(60, ge=5, le=180)

    @property
    def database_path(self) -> Path:
        return (ROOT / self.data_dir).resolve() / "knowledge.sqlite3"
