# app/routes/parcel_journey.py

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from typing import List, Dict

from app.database.db import get_db
from app.models.parcel_journey_model import ParcelJourneyRequest

router = APIRouter()

@router.post("/parcel-journey")
def get_parcel_journey(payload: ParcelJourneyRequest, db: Database = Depends(get_db)) -> List[Dict]:
    collection_name = payload.date

    if collection_name not in db.list_collection_names():
        raise HTTPException(status_code=404, detail="Collection not found")

    # Build MongoDB query
    if payload.search_by == "host_id":
        query = {"hostId": payload.search_value}
    elif payload.search_by == "barcode":
        query = {"barcodes": {"$in": [payload.search_value]}}
    elif payload.search_by == "alibi_id":
        query = {"alibi_number": payload.search_value}
    else:
        raise HTTPException(status_code=400, detail="Invalid search_by value")

    try:
        results = []
        for doc in db[collection_name].find(query):
            results.append({
                "host_id": doc.get("hostId"),
                "status": doc.get("lifeCycle", {}).get("status"),
                "barcode": doc.get("barcodes", [""])[0],
                "alibi_id": doc.get("alibi_number"),
                "register_at": doc.get("lifeCycle", {}).get("registeredAt"),
                "destination": doc.get("destination"),
                "volume": doc.get("volume_data", {}).get("box_volume"),
                "location": doc.get("location")
            })

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
