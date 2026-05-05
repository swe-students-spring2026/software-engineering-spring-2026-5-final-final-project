from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    grader_service_url: str = "http://localhost:8001"
    game_service_port: int = 8000

    # "mock" | "mongo"
    db_backend: str = "mock"

    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "fish_likes_cat"

    # CORS allow-list, comma-separated
    allowed_origins: str = (
        "http://localhost:5173,http://localhost:5174,"
        "http://localhost:5175,http://localhost:3000"
    )

    log_level: str = "INFO"

    # Optional override for the combined CatCh judgeable problem dataset.
    problem_dataset_path: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
