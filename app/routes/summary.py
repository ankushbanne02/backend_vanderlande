from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.database.db import get_db
from app.models.kpi_model import DateRequest
from datetime import datetime

router = APIRouter()

@router.post("/summary")
def get_summary(payload: DateRequest, db: Database = Depends(get_db)):
    try:
        print(f"Fetching data from collection: {payload.date}")

        if payload.date not in db.list_collection_names():
            raise HTTPException(status_code=404, detail=f"No collection found for date {payload.date}")

        collection = db[payload.date]
        parcels = list(collection.find({}))

        if not parcels:
            return {"message": "No data found for this date"}

        total = len(parcels)

        # 1. Sorted Good
        sorted_good = sum(
            1 for p in parcels
            if p.get("lifeCycle", {}).get("status") == "sorted"
            and str(p.get("destination_status", "")).endswith(";1")
        )

        # 2. Overflow (status == "open")
        overflow = sum(1 for p in parcels if p.get("lifeCycle", {}).get("status") == "open")

        # 3. Barcode Read Ratio
        barcode_read = sum(1 for p in parcels if p.get("barcodeErr") is False)
        barcode_read_ratio = round((barcode_read / total) * 100, 2) if total else 0.0

        # 4. Volume Rate (only if real_volume is a valid positive number)
        volume_valid = sum(
            1 for p in parcels
            if isinstance(p.get("volume_data", {}).get("real_volume"), (int, float))
            and p["volume_data"]["real_volume"] > 0
        )
        volume_rate = round((volume_valid / total) * 100, 2) if total else 0.0

        # 5. Throughput (average parcels per hour)
        timestamps = [
            datetime.fromisoformat(p["lifeCycle"]["registeredAt"])
            for p in parcels
            if "lifeCycle" in p and "registeredAt" in p["lifeCycle"]
        ]
        throughput_per_hour = 0.0
        if timestamps:
            duration = (max(timestamps) - min(timestamps)).total_seconds() / 3600
            throughput_per_hour = round(total / duration, 2) if duration > 0 else 0.0

        # 6. Tracking Performance: parcels with all 3 required events
        def has_required_events(events):
            types = {e.get("type") for e in events}
            return {"ItemInstruction", "ItemPropertiesUpdate", "VerifiedSortReport"}.issubset(types)

        tracking_ok = sum(1 for p in parcels if has_required_events(p.get("events", [])))
        tracking_performance = round((tracking_ok / total) * 100, 2) if total else 0.0

        return {
            "date": payload.date,
            "total_parcels": total,
            "sorted_good": sorted_good,
            "overflow": overflow,
            "barcode_read_ratio_percent": barcode_read_ratio,
            "volume_rate_percent": volume_rate,
            "throughput_avg_per_hour": throughput_per_hour,
            "tracking_performance_percent": tracking_performance,
        }

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
