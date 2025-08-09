from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.database.db import get_db
from app.models.kpi_model import DateRequest
from datetime import datetime
from app.config import config

router = APIRouter()

@router.post("/summary")
def get_summary(payload: DateRequest, db: Database = Depends(get_db)):
    try:
        if payload.date not in db.list_collection_names():
            raise HTTPException(status_code=404, detail=f"No collection found for date {payload.date}")

        collection = db[payload.date]
        parcels = list(collection.find({}))
        if not parcels:
            return {"message": "No data found for this date"}

        # Parse start and end times
        try:
            start_time = datetime.strptime(payload.start_time, "%H:%M")
            end_time = datetime.strptime(payload.end_time, "%H:%M")
        except ValueError:
            raise HTTPException(status_code=400, detail="Time format must be HH:MM")
        if end_time <= start_time:
            raise HTTPException(status_code=400, detail="End time must be after start time")

        # --- Helper to parse DB times like throughput ---
        def safe_parse_time(ts_str, start_time):
                formats = ["%H:%M:%S,%f", "%H:%M:%S"]  # support both with and without milliseconds
                for fmt in formats:
                    try:
                        ts = datetime.strptime(ts_str.strip(), fmt).replace(
                            year=start_time.year, month=start_time.month, day=start_time.day
                        )
                        return ts
                    except ValueError:
                        continue
                return None

        # --- Filter parcels by time range ---
        filtered_parcels = []
        for p in parcels:
            ts_str = p.get("registerTS")
            if not ts_str:
                continue
            ts = safe_parse_time(ts_str, start_time)
            if ts and start_time <= ts <= end_time:
                filtered_parcels.append(p)
        
        # 1. Total parcels
        unique_hosts = {p.get("hostId") for p in filtered_parcels if p.get("hostId")}
        total_parcels = len(unique_hosts)

        if total_parcels == 0:
            return {
                "message": "No parcels found in the given time range",
                "start_time": payload.start_time,
                "end_time": payload.end_time
            }

        # 2. Sorted Parcels
        sorted_parcels = sum(
            1 for p in filtered_parcels
            if p.get("status") == "sorted" and p.get("sort_strategy") == "1"
        )

        # 3. Total parcels in the system
        parcels_in_system = []
        for p in filtered_parcels:
            msg_ids = {event.get("msg_id") for event in p.get("events", [])}
            if "2" in msg_ids and not msg_ids.intersection({"6", "7"}):
                parcels_in_system.append(p)
        total_in_system = len(parcels_in_system)

        # 4. Overflow
        overflow_locations = config.get("overflow_locations", [])
        def calculate_overflow(parcels, overflow_locations):
            overflow_count = 0
            for parcel in parcels:
                events = parcel.get("events", [])

                has_verified_sort_999 = any(
                    e.get("msg_id") == "6" and
                    len(e.get("raw", "").split("|")) > 10 and
                    e.get("raw", "").split("|")[10] == "999"
                    for e in events
                )
                if has_verified_sort_999:
                    if any(ev.get("msg_id") == "2" for ev in events):
                        overflow_count += 1
                        continue

                has_msg_id_7_in_overflow_location = any(
                    e.get("msg_id") == "7" and
                    len(e.get("raw", "").split("|")) > 11 and
                    e.get("raw", "").split("|")[11] in overflow_locations
                    for e in events
                )
                if has_msg_id_7_in_overflow_location:
                    overflow_count += 1
            return overflow_count

        overflow = calculate_overflow(filtered_parcels, overflow_locations)

        # 5. Barcode Read Ratio
        barcode_read = sum(1 for p in filtered_parcels if p.get("barcode_error") is False)
        barcode_read_ratio = round((barcode_read / total_parcels) * 100, 2) if total_parcels else 0.0

        # 6. Volume Rate
        volume_valid = sum(
            1 for p in filtered_parcels
            if isinstance(p.get("volume_data", {}).get("real_volume"), (int, float))
            and p["volume_data"]["real_volume"] > 0
        )
        volume_rate = round((volume_valid / total_parcels) * 100, 2) if total_parcels else 0.0

        # 7. Throughput
        in_timestamps = []
        for p in filtered_parcels:
            for event in p.get("events", []):
                if event.get("msg_id") == "2":
                    ts = safe_parse_time(event.get("ts", ""), start_time)
                    if ts:
                        in_timestamps.append(ts)
                        break
        throughput_per_hour = 0.0
        if in_timestamps:
            duration_hours = (max(in_timestamps) - min(in_timestamps)).total_seconds() / 3600
            throughput_per_hour = round(len(in_timestamps) / duration_hours, 2) if duration_hours > 0 else 0.0

        # 8. Tracking Performance
        def has_required_msg_ids(events):
            msg_ids = {e.get("msg_id") for e in events}
            return {"2", "3", "6"}.issubset(msg_ids)

        tracking_ok = sum(1 for p in filtered_parcels if has_required_msg_ids(p.get("events", [])))
        tracking_performance = round((tracking_ok / total_parcels) * 100, 2) if total_parcels else 0.0

        return {
            "date": payload.date,
            "total_parcels": total_parcels,
            "total_in_system": total_in_system,
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
        raise HTTPException(status_code=500, detail=str(e))


# from fastapi import APIRouter, Depends, HTTPException
# from pymongo.database import Database
# from app.database.db import get_db
# from app.models.kpi_model import DateRequest
# from datetime import datetime
# from app.config import config

# router = APIRouter()

# @router.post("/summary")
# def get_summary(payload: DateRequest, db: Database = Depends(get_db)):
#     try:
#         print(f"Fetching data from collection: {payload.date}")

#         if payload.date not in db.list_collection_names():
#             raise HTTPException(status_code=404, detail=f"No collection found for date {payload.date}")

#         # Convert API start/end into time objects (HH:MM)
#         try:
#             start_time_obj = datetime.strptime(payload.start_time, "%H:%M").time()
#             end_time_obj = datetime.strptime(payload.end_time, "%H:%M").time()
#         except ValueError:
#             raise HTTPException(status_code=400, detail="Time format must be HH:MM")

#         if end_time_obj <= start_time_obj:
#             raise HTTPException(status_code=400, detail="End time must be after start time")
        
#         collection = db[payload.date]
#         parcels = list(collection.find({}))

#         if not parcels:
#             return {"message": "No data found for this date"}

#         # --- Filter parcels by HH:MM ---
#         filtered_parcels = []
#         for p in parcels:
#             ts_str = p.get("registeredTS")  # e.g. "07:45:12,123"
#             if not ts_str:
#                 continue
#             try:
#                 # Convert DB format to time object (HH:MM:SS,ms → time)
#                 parcel_time_obj = datetime.strptime(ts_str.strip(), "%H:%M:%S,%f").time()
#             except ValueError:
#                 # If DB has no milliseconds
#                 try:
#                     parcel_time_obj = datetime.strptime(ts_str.strip(), "%H:%M:%S").time()
#                 except ValueError:
#                     continue

#             if start_time_obj <= parcel_time_obj <= end_time_obj:
#                 filtered_parcels.append(p)
        
#         # 1. Total parcels
#         # Get unique host IDs from filtered parcels
#         unique_hosts = {p.get("hostId") for p in filtered_parcels if p.get("hostId")}
#         total_parcels = len(unique_hosts)

#         if total_parcels == 0:
#             return {
#                 "message": "No parcels found in the given time range",
#                 "start_time": payload.start_time,
#                 "end_time": payload.end_time
#             }

#         # 2. Sorted Parcels
#         sorted_parcels = sum(
#             1 for p in parcels
#             if p.get("status") == "sorted" and p.get("sort_strategy") == "1"
#         )

#         # 3. Total parcels in the system
#         # Calculate parcels in the system
#         parcels_in_system = []
#         for p in filtered_parcels:
#             msg_ids = {event.get("msg_id") for event in p.get("events", [])}
#             if (
#                 "2" in msg_ids
#                 and not msg_ids.intersection({"6", "7"})
#                 and ( "5" not in msg_ids or "5" in msg_ids )
#             ):
#                 parcels_in_system.append(p)

#         total_in_system = len(parcels_in_system)

#         # 4. Overflow

#         # Configurable locations for overflow detection
#         overflow_locations = config.get("overflow_locations", [])

#         # Helper function to calculate overflow
#         def calculate_overflow(parcels, overflow_locations):
#             overflow_count = 0

#             for parcel in parcels:
#                 events = parcel.get("events", [])

#                 # --- Overflow Case 1 ---
#                 has_verified_sort_999 = any(
#                     e.get("msg_id") == "6" and
#                     len(e.get("raw", "").split("|")) > 10 and
#                     e.get("raw", "").split("|")[10] == "999"
#                     for e in events
#                 )

#                 if has_verified_sort_999:
#                     has_msg_id_2 = any(ev.get("msg_id") == "2" for ev in events)
#                     if has_msg_id_2:
#                         overflow_count += 1
#                         continue  # avoid double-counting if it also matches Case 2

#                 # --- Overflow Case 2 ---
#                 has_msg_id_7_in_overflow_location = any(
#                     e.get("msg_id") == "7" and
#                     len(e.get("raw", "").split("|")) > 11 and
#                     e.get("raw", "").split("|")[11] in overflow_locations
#                     for e in events
#                 )

#                 if has_msg_id_7_in_overflow_location:
#                     overflow_count += 1

#             return overflow_count

#         overflow = calculate_overflow(parcels, overflow_locations)

#         # 5. Barcode Read Ratio
#         barcode_read = sum(1 for p in parcels if p.get("barcode_error") is False)
#         barcode_read_ratio = round((barcode_read / total_parcels) * 100, 2) if total_parcels else 0.0

#         # 6. Volume Rate (only if real_volume is a valid positive number)
#         volume_valid = sum(
#             1 for p in parcels
#             if isinstance(p.get("volume_data", {}).get("real_volume"), (int, float))
#             and p["volume_data"]["real_volume"] > 0
#         )
#         volume_rate = round((volume_valid / total_parcels) * 100, 2) if total_parcels else 0.0

#         # 7. Throughput (average parcels/hour with msg_id == "2")
#         in_timestamps = []
#         for p in filtered_parcels:
#             for event in p.get("events", []):
#                 if event.get("msg_id") == "2":
#                     ts_str = event.get("ts")
#                     try:
#                         ts = datetime.strptime(ts_str.strip(), "%H:%M:%S,%f")
#                         in_timestamps.append(ts)
#                         break
#                     except:
#                         continue
#         throughput_per_hour = 0.0
#         if in_timestamps:
#             start_time = min(in_timestamps)
#             end_time = max(in_timestamps)
#             duration_hours = (end_time - start_time).total_seconds() / 3600
#             throughput_per_hour = round(len(in_timestamps) / duration_hours, 2) if duration_hours > 0 else 0.0

#         # 8. Tracking Performance: parcels with all 3 required msg_ids
#         def has_required_msg_ids(events):
#             msg_ids = {e.get("msg_id") for e in events}
#             return {"2", "3", "6"}.issubset(msg_ids)  # Corresponding to ItemInstruction, ItemPropertiesUpdate, VerifiedSortReport

#         tracking_ok = sum(1 for p in parcels if has_required_msg_ids(p.get("events", [])))
#         tracking_performance = round((tracking_ok / total_parcels) * 100, 2) if total_parcels else 0.0

#         return {
#             "date": payload.date,
#             "total_parcels": total_parcels,
#             "total_in_system": total_in_system,
#             "sorted_parcels": sorted_parcels,
#             "overflow": overflow,
#             "barcode_read_ratio_percent": barcode_read_ratio,
#             "volume_rate_percent": volume_rate,
#             "throughput_avg_per_hour": throughput_per_hour,
#             "tracking_performance_percent": tracking_performance,
#         }

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         print(f"Unexpected error: {e}")
#         raise HTTPException(status_code=500, detail=str(e))
