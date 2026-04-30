from dotenv import load_dotenv
import os
import pymongo

class Config:
    load_dotenv()
    #Load variables from .env file
    MONGO_DBNAME = os.getenv('MONGO_DBNAME')
    MONGO_URI = os.getenv('MONGO_URI')

    #Connect to Mongo
    def connect_to_db():
        connection = pymongo.MongoClient(MONGO_URI)
        db = connection[MONGO_DBNAME]
        return db