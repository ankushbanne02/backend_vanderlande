# app/database/db.py
from pymongo import MongoClient
from pymongo.database import Database

def get_db() -> Database:
    client = MongoClient("mongodb+srv://ankushbanne23:Ankush1316@asd.qj6if.mongodb.net/?retryWrites=true&w=majority")
    return client["ASD"]
