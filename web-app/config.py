from dotenv import load_dotenv
import os
import pymongo


class Config:
    # Load variables from .env file
    load_dotenv()
    MONGO_DBNAME = os.getenv("MONGO_DBNAME")
    MONGO_URI = os.getenv("MONGO_URI")

    # Connect to Mongo
    @staticmethod
    def connect_to_db():
        connection = pymongo.MongoClient(self.MONGO_URI)
        db = connection[self.MONGO_DBNAME]
        return db
