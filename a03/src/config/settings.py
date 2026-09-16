from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    # --- Google ---
    GOOGLE_API_KEY: str = ""

    # --- Neo4j ---
    NEO4J_URI: str = ""
    NEO4J_USERNAME: str = ""
    NEO4J_PASSWORD: str = ""
    NEO4J_DATABASE: str = "neo4j"

    # --- Long Châu ---
    LONG_CHAU_API_URL: str = (
        "https://api.nhathuoclongchau.com.vn/lccus/"
        "search-product-service/api/products/ecom/product/search"
    )
    LONG_CHAU_WEB_BASE_URL: str = "https://nhathuoclongchau.com.vn"
    LONG_CHAU_TIMEOUT_SECONDS: float = 10.0
    LONG_CHAU_SEARCH_LIMIT: int = 8
    LONG_CHAU_SUMMARY_LIMIT: int = 4

    SESSION_DB_URL: str = "sqlite+aiosqlite:///./data/adk_sessions.db"
    ALLOW_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def validate_runtime(self) -> None:
        required = {
            "GOOGLE_API_KEY": self.GOOGLE_API_KEY,
            "NEO4J_URI": self.NEO4J_URI,
            "NEO4J_USERNAME": self.NEO4J_USERNAME,
            "NEO4J_PASSWORD": self.NEO4J_PASSWORD,
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            raise RuntimeError(f"Missing required settings: {', '.join(missing)}")


settings = Settings()
