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
        sorted_parcels = sum(
            1 for p in parcels
            if p.get("status") == "sorted" and p.get("sort_strategy") == "1"
        )

        # Configurable locations for overflow detection
        overflow_locations = ["1001.0045.0040.B31", "1001.0043.0000.B71"]

        # Helper function to calculate overflow
        def calculate_overflow(parcels, overflow_locations):
            overflow_count = 0

            for parcel in parcels:
                events = parcel.get("events", [])

                # --- Overflow Case 1 ---
                has_verified_sort_999 = any(
                    e.get("msg_id") == "6" and
                    len(e.get("raw", "").split("|")) > 10 and
                    e.get("raw", "").split("|")[10] == "999"
                    for e in events
                )

                if has_verified_sort_999:
                    has_msg_id_2 = any(ev.get("msg_id") == "2" for ev in events)
                    if has_msg_id_2:
                        overflow_count += 1
                        continue  # avoid double-counting if it also matches Case 2

                # --- Overflow Case 2 ---
                has_msg_id_7_in_overflow_location = any(
                    e.get("msg_id") == "7" and
                    len(e.get("raw", "").split("|")) > 11 and
                    e.get("raw", "").split("|")[11] in overflow_locations
                    for e in events
                )

                if has_msg_id_7_in_overflow_location:
                    overflow_count += 1

            return overflow_count

        # 2. Overflow
        overflow = calculate_overflow(parcels, overflow_locations)

        # 3. Barcode Read Ratio
        barcode_read = sum(1 for p in parcels if p.get("barcode_error") is False)
        barcode_read_ratio = round((barcode_read / total) * 100, 2) if total else 0.0

        # 4. Volume Rate (only if real_volume is a valid positive number)
        volume_valid = sum(
            1 for p in parcels
            if isinstance(p.get("volume_data", {}).get("real_volume"), (int, float))
            and p["volume_data"]["real_volume"] > 0
        )
        volume_rate = round((volume_valid / total) * 100, 2) if total else 0.0

        # 5. Throughput (average parcels per hour using msg_id == "2")
        in_timestamps = []

        for p in parcels:
            for event in p.get("events", []):
                if event.get("msg_id") == "2":
                    ts_str = event.get("ts")
                    try:
                        ts = datetime.strptime(ts_str, "%H:%M:%S,%f")
                        in_timestamps.append(ts)
                        break  # only first msg_id == 2 per parcel
                    except:
                        continue

        throughput_per_hour = 0.0
        if in_timestamps:
            start_time = min(in_timestamps)
            end_time = max(in_timestamps)
            duration_hours = (end_time - start_time).total_seconds() / 3600
            throughput_per_hour = round(len(in_timestamps) / duration_hours, 2) if duration_hours > 0 else 0.0


        # 6. Tracking Performance: parcels with all 3 required msg_ids
        def has_required_msg_ids(events):
            msg_ids = {e.get("msg_id") for e in events}
            return {"2", "3", "6"}.issubset(msg_ids)  # Corresponding to ItemInstruction, ItemPropertiesUpdate, VerifiedSortReport

        tracking_ok = sum(1 for p in parcels if has_required_msg_ids(p.get("events", [])))
        tracking_performance = round((tracking_ok / total) * 100, 2) if total else 0.0

        return {
            "date": payload.date,
            "total_parcels": total,
            "sorted_parcels": sorted_parcels,
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
