from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.database.db import get_db
from app.models.kpi_model import DateRequest
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
        height_count = defaultdict(int)
        width_count = defaultdict(int)
        length_count = defaultdict(int)

        for parcel in parcels:
            volume = parcel.get("volume_data", {})
            height = volume.get("height")
            width = volume.get("width")
            length = volume.get("length")

            if height is not None:
                height_count[height] += 1
            if width is not None:
                width_count[width] += 1
            if length is not None:
                length_count[length] += 1

        # Convert defaultdicts to dicts for JSON response
        return {
            "height_distribution": dict(height_count),
            "width_distribution": dict(width_count),
            "length_distribution": dict(length_count)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
