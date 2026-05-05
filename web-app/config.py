import os
 
class Config:
    MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME = os.environ.get("DB_NAME", "katydid_brigade")
    GAME_ENGINE_URL = os.environ.get("GAME_ENGINE_URL", "http://game-engine:5001")
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev")
    TESTING = False
 
class TestConfig(Config):
    TESTING = True
    MONGO_URI = "mongodb://localhost:27017/puzzlegame_test"
    DB_NAME = "puzzlegame_test"
    GAME_ENGINE_URL = "http://localhost:5001"
 