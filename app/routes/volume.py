### Backend (FastAPI Route) - backend/app/routes/volume.py

from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.database.db import get_db
from app.models.kpi_model import DateRequest

router = APIRouter()

@router.post("/volume")
def get_volume(payload: DateRequest, db: Database = Depends(get_db)):
    try:
        if payload.date not in db.list_collection_names():
            raise HTTPException(status_code=404, detail=f"No collection found for date {payload.date}")

        collection = db[payload.date]
        parcels = list(collection.find({}))

        if not parcels:
            return {"message": "No data found for this date"}

        heights, widths, lengths = [], [], []

        for parcel in parcels:
            volume = parcel.get("volume_data", {})
            if volume.get("height") is not None:
                heights.append(volume["height"])
            if volume.get("width") is not None:
                widths.append(volume["width"])
            if volume.get("length") is not None:
                lengths.append(volume["length"])

        def count_distribution(values):
            dist = {}
            for val in values:
                dist[str(round(val))] = dist.get(str(round(val)), 0) + 1
            return dist

        return {
            "height_distribution": count_distribution(heights),
            "width_distribution": count_distribution(widths),
            "length_distribution": count_distribution(lengths)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
