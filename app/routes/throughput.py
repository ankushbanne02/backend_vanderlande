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
        valid_bins = [1, 10, 20, 30, 60]
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

        # Parse start and end times
        try:
            start_time = datetime.strptime(payload.start_time, "%H:%M")
            end_time = datetime.strptime(payload.end_time, "%H:%M")
        except ValueError:
            raise HTTPException(status_code=400, detail="Time format must be HH:MM")
        if end_time <= start_time:
            raise HTTPException(status_code=400, detail="End time must be after start time")
        
        
        # time_bins = OrderedDict()
        # start_time = datetime.strptime("00:00", "%H:%M")
        # num_bins = int(24 * 60 / bin_size)
        
        # for i in range(num_bins):
        #     label = (start_time + timedelta(minutes=i * bin_size)).strftime("%H:%M")
        #     time_bins[label] = 0

        # Configurable locations for overflow detection
        overflow_locations = ["1001.0045.0040.B31", "1001.0043.0000.B71"]

        time_bins = OrderedDict()
        current_time = start_time
        while current_time < end_time:
            label = current_time.strftime("%H:%M")
            time_bins[label] = 0
            current_time += timedelta(minutes=bin_size)

        parcels_in_time = time_bins.copy()
        parcels_out_time = time_bins.copy()

        total_in = 0
        total_out = 0
        overflow_count = 0

        for parcel in parcels:
            events = parcel.get("events", [])
            ts_in = None
            ts_out = None

            # IN event
            for event in events:
                if event.get("msg_id") == "2":
                    ts_str = event.get("ts")
                    try:
                        ts = datetime.strptime(ts_str, "%H:%M:%S,%f").replace(
                            year=start_time.year, month=start_time.month, day=start_time.day
                        )
                    except:
                        continue

                    if start_time <= ts <= end_time:
                        total_in += 1
                        bin_label = ts.strftime("%H:%M")
                        if bin_label in parcels_in_time:
                            parcels_in_time[bin_label] += 1
                        break

            # OUT event
            for event in events:
                if event.get("msg_id") == "6":
                    ts_str = event.get("ts")
                    try:
                        ts = datetime.strptime(ts_str, "%H:%M:%S,%f").replace(
                            year=start_time.year, month=start_time.month, day=start_time.day
                        )
                    except:
                        continue

                    if start_time <= ts <= end_time:
                        raw = event.get("raw", "")
                        raw_parts = raw.split("|")
                        if len(raw_parts) > 10:
                            sort_status = raw_parts[10]
                            if sort_status == "1":
                                total_out += 1
                                bin_label = ts.strftime("%H:%M")
                                if bin_label in parcels_out_time:
                                    parcels_out_time[bin_label] += 1
                                break
                            elif sort_status == "999":
                                for ev in events:
                                    if ev.get("msg_id") == "7":
                                        raw_dereg = ev.get("raw", "")
                                        parts = raw_dereg.split("|")
                                        if len(parts) > 9 and parts[9] == "2":
                                            total_out += 1
                                            bin_label = ts.strftime("%H:%M")
                                            if bin_label in parcels_out_time:
                                                parcels_out_time[bin_label] += 1
                                            break
                                break

            # Overflow Case 1
            for event in events:
                if event.get("msg_id") == "6":
                    ts_str = event.get("ts")
                    try:
                        ts = datetime.strptime(ts_str, "%H:%M:%S,%f").replace(
                            year=start_time.year, month=start_time.month, day=start_time.day
                        )
                    except:
                        continue

                    if start_time <= ts <= end_time:
                        raw = event.get("raw", "")
                        parts = raw.split("|")
                        if len(parts) > 10 and parts[10] == "999":
                            for ev in events:
                                if ev.get("msg_id") == "2":
                                    overflow_count += 1
                                    break

            # Overflow Case 2
            for event in events:
                if event.get("msg_id") == "7":
                    ts_str = event.get("ts")
                    try:
                        ts = datetime.strptime(ts_str, "%H:%M:%S,%f").replace(
                            year=start_time.year, month=start_time.month, day=start_time.day
                        )
                    except:
                        continue

                    if start_time <= ts <= end_time:
                        raw = event.get("raw", "")
                        parts = raw.split("|")
                        if len(parts) > 11 and parts[11] in overflow_locations:
                            overflow_count += 1
          
        # for parcel in parcels:
        #     events = parcel.get("events", [])

        #     # === IN Logic ===
        #     in_found = False
        #     for event in events:
        #         if event.get("type") == "itempropertiesupdate":
        #             ts = event.get("ts")
        #             if ts:
        #                 try:
        #                     dt = datetime.fromisoformat(ts)
        #                 except:
        #                     try:
        #                         dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
        #                     except:
        #                         continue

        #                 dt_time = dt.replace(year=1900, month=1, day=1)
        #                 if start_time <= dt_time < end_time:
        #                     floored_minutes = (dt.minute // payload.bin_size) * payload.bin_size
        #                     bin_time = dt.replace(minute=floored_minutes, second=0, microsecond=0)
        #                     bin_label = bin_time.strftime("%H:%M")

        #                     if bin_label in parcels_in_time:
        #                         parcels_in_time[bin_label] += 1
        #                         total_in += 1
        #                         in_found = True
        #                     break  # Use first matching event only

        #     # === OUT Logic ===
        #     out_found = False
        #     for event in events:
        #         if event.get("type") == "verifiedsortreport":
        #             sort_status = event.get("sort_status")
        #             ts = event.get("ts")

        #             if ts:
        #                 try:
        #                     dt = datetime.fromisoformat(ts)
        #                 except:
        #                     try:
        #                         dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")
        #                     except:
        #                         continue

        #                 dt_time = dt.replace(year=1900, month=1, day=1)
        #                 if start_time <= dt_time < end_time:
        #                     floored_minutes = (dt.minute // payload.bin_size) * payload.bin_size
        #                     bin_time = dt.replace(minute=floored_minutes, second=0, microsecond=0)
        #                     bin_label = bin_time.strftime("%H:%M")

        #                     if sort_status == 1:
        #                         if bin_label in parcels_out_time:
        #                             parcels_out_time[bin_label] += 1
        #                             total_out += 1
        #                             out_found = True
        #                         break

        #                     elif sort_status == 999:
        #                         # Look for itemderegister event with raw=2
        #                         for ev in events:
        #                             if ev.get("type") == "itemderegister" and ev.get("raw") == 2:
        #                                 if bin_label in parcels_out_time:
        #                                     parcels_out_time[bin_label] += 1
        #                                     total_out += 1
        #                                     out_found = True
        #                                 break
        #             if out_found:
        #                 break

        #     if not in_found and not out_found:
        #         overflow += 1

            # ts = parcel.get("events", [{}])[0].get("ts")
            # exit_state = parcel.get("exit_state")

            # if ts:
            #     try:
            #         dt = datetime.fromisoformat(ts)
            #     except:
            #         dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%fZ")  # fallback

            #     # Floor to nearest bin
            #     floored_minutes = (dt.minute // bin_size) * bin_size
            #     bin_time = dt.replace(minute=floored_minutes, second=0, microsecond=0)
            #     bin_label = bin_time.strftime("%H:%M")

            #     if bin_label in parcels_in_time:
            #         if exit_state is None:
            #             total_in += 1
            #             parcels_in_time[bin_label] += 1
            #         else:
            #             total_out += 1
            #             parcels_out_time[bin_label] += 1



        avg_in = round(total_in / len(parcels_in_time), 2) if parcels_in_time else 0
        avg_out = round(total_out / len(parcels_out_time), 2) if parcels_out_time else 0

        return {
            "bin_size_minutes": bin_size,
            "start_time": payload.start_time,
            "end_time": payload.end_time,
            "total_in": total_in,
            "total_out": total_out,
            "avg_in": avg_in,
            "avg_out": avg_out,
            "overflow": overflow_count,
            "parcels_in_time": parcels_in_time,
            "parcels_out_time": parcels_out_time
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))