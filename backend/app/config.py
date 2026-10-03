from functools import lru_cache
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    database_url: str = "sqlite:///./data/disprot.db"
    storage_dir: str = "./data/files"
    app_env: str = "local"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    if desktop_dir := os.environ.get("DISPROT_DATA_DIR"):
        root = Path(desktop_dir).resolve()
        return Settings(
            _env_file=None,
            database_url=URL.create("sqlite", database=str(root / "disprot.db")).render_as_string(),
            storage_dir=str(root / "files"),
            app_env="desktop",
        )
    return Settings()
