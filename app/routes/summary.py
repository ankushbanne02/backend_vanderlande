
from fastapi import APIRouter, Depends
from pymongo.database import Database
from app.database.db import get_db

router = APIRouter()

@router.get("/summary")
def get_summary_metrics(db: Database = Depends(get_db)):
    parcels = db["parcels"]
    total_parcels = parcels.count_documents({})
    sorted_parcels = parcels.count_documents({"lifeCycle.status": "sorted"})

    return {
        "total_parcels": total_parcels,
        "sorted_parcels": sorted_parcels
    }
