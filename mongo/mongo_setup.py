from dotenv import load_dotenv
import os
import pymongo

#Load variables from .env file
MONGO_DBNAME = os.getenv('MONGO_DBNAME')
MONGO_URI = os.getenv('MONGO_URI')

#Connect to Mongo
connection = pymongo.MongoClient(MONGO_URI)