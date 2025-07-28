from fastapi import APIRouter, Depends
from pymongo.database import Database
from app.database.db import get_db
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/summary")
def get_summary_metrics(db: Database = Depends(get_db)):
    parcels = db["parcels"]

    total_parcels = parcels.count_documents({})
    sorted_parcels = parcels.count_documents({"lifeCycle.status": "sorted"})
    barcode_read = parcels.count_documents({"barcodeErr": False})
    volume_read = parcels.count_documents({
        "volume_data.length": {"$exists": True},
        "volume_data.width": {"$exists": True},
        "volume_data.height": {"$exists": True}
    })

    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    recent_parcels = parcels.count_documents({
        "lifeCycle.registeredAt": {"$gte": one_hour_ago}
    })

    performance_sorted = (sorted_parcels / total_parcels * 100) if total_parcels else 0
    barcode_read_rate = (barcode_read / total_parcels * 100) if total_parcels else 0
    volume_read_rate = (volume_read / total_parcels * 100) if total_parcels else 0

    return {
        "total_parcels": total_parcels,
        "sorted_parcels": sorted_parcels,
        "performance_sorted": round(performance_sorted, 2),
        "barcode_read_rate": round(barcode_read_rate, 2),
        "volume_read_rate": round(volume_read_rate, 2),
        "throughput_per_hour": recent_parcels
    }
