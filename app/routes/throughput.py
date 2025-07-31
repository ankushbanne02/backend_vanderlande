from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.database.db import get_db
from app.models.kpi_model import DateRequest
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict

router = APIRouter()

@router.post("/throughput")
def get_throughput(payload: DateRequest, db: Database = Depends(get_db)):
    try:
        print(f"Fetching data from collection: {payload.date}")

        # Validate bin_size
        valid_bins = [10, 15, 30, 45, 60]
        bin_size = payload.bin_size
        if bin_size not in valid_bins:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid bin size. Choose from {valid_bins}"
            )

        if payload.date not in db.list_collection_names():
            raise HTTPException(status_code=404, detail=f"No collection found for date {payload.date}")

        collection = db[payload.date]
        parcels = list(collection.find({}))

        if not parcels:
            return {"message": "No data found for this date"}
        
        time_bins = OrderedDict()
        start_time = datetime.strptime("00:00", "%H:%M")
        num_bins = int(24 * 60 / bin_size)
        
        for i in range(num_bins):
            label = (start_time + timedelta(minutes=i * bin_size)).strftime("%H:%M")
            time_bins[label] = 0

        parcels_in_time = time_bins.copy()
        parcels_out_time = time_bins.copy()

        total_in = 0
        total_out = 0

        for parcel in parcels:
            ts = parcel.get("lifeCycle", {}).get("registeredAt") or parcel.get("events", [{}])[0].get("ts")
            exit_state = parcel.get("exit_state")

            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                except:
                    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")  # fallback

                # Floor to nearest bin
                floored_minutes = (dt.minute // bin_size) * bin_size
                bin_time = dt.replace(minute=floored_minutes, second=0, microsecond=0)
                bin_label = bin_time.strftime("%H:%M")

                if bin_label in parcels_in_time:
                    if exit_state is None:
                        total_in += 1
                        parcels_in_time[bin_label] += 1
                    else:
                        total_out += 1
                        parcels_out_time[bin_label] += 1

        avg_in = round(total_in / len(parcels_in_time), 2) if parcels_in_time else 0
        avg_out = round(total_out / len(parcels_out_time), 2) if parcels_out_time else 0

        return {
            "bin_size_minutes": bin_size,
            "total_in": total_in,
            "total_out": total_out,
            "avg_in": avg_in,
            "avg_out": avg_out,
            "parcels_in_time": parcels_in_time,
            "parcels_out_time": parcels_out_time
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))