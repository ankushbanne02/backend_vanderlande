from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.database.db import get_db
from app.models.kpi_model import DateRequest
from datetime import datetime
from collections import defaultdict

router = APIRouter()

@router.post("/volume")
def get_volume(payload: DateRequest, db: Database = Depends(get_db)):
    try:
        print(f"Fetching data from collection: {payload.date}")

        if payload.date not in db.list_collection_names():
            raise HTTPException(status_code=404, detail=f"No collection found for date {payload.date}")

        collection = db[payload.date]
        parcels = list(collection.find({}))

        if not parcels:
            return {"message": "No data found for this date"}

        # Count occurrences
        weight_count = defaultdict(int)
        height_count = defaultdict(int)
        width_count = defaultdict(int)

        for parcel in parcels:
            volume = parcel.get("volume_data", {})

            weight = volume.get("real_volume")
            height = volume.get("height")
            width = volume.get("width")

            if weight is not None:
                weight_count[weight] += 1
            if height is not None:
                height_count[height] += 1
            if width is not None:
                width_count[width] += 1

        # Convert defaultdicts to dicts for JSON response
        return {
            "weight_distribution": dict(weight_count),
            "height_distribution": dict(height_count),
            "width_distribution": dict(width_count)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
