from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gemini_api_key: str
    spotify_client_id: str
    spotify_client_secret: str
    openweather_api_key: str
    mongo_uri: str = "mongodb://mongo:27017/moodmusic"

    class Config:
        env_file = ".env"


settings = Settings()
