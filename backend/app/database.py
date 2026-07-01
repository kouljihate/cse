from pymongo import MongoClient
from config import settings

client = MongoClient(settings.mongo_uri)
db = client.get_database()


def get_db():
    return db
