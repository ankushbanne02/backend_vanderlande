# app/database/db.py
from pymongo import MongoClient
from pymongo.database import Database
from dotenv import load_dotenv

load_dotenv()
def get_db() -> Database:
    client = MongoClient("MONGODB_URI")
    return client["ASD"]
