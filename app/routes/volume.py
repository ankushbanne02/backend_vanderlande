from fastapi import APIRouter, Depends
from pymongo.database import Database
from app.database.db import get_db

router = APIRouter()

@router.get("/volume")
def get_volume_records(db: Database = Depends(get_db)):
    parcels = db["parcels"]

    cursor = parcels.find({
        "volume_data.length": {"$exists": True},
        "volume_data.width": {"$exists": True},
        "volume_data.height": {"$exists": True}
    }, 
    {
        "_id": 0,
        "volume_data.length": 1,
        "volume_data.width": 1,
        "volume_data.height": 1
    }
    )

    result = []
    for doc in cursor:
        result.append({
            "length": doc["volume_data"]["length"],
            "width": doc["volume_data"]["width"],
            "height": doc["volume_data"]["height"]
        })

    return result
