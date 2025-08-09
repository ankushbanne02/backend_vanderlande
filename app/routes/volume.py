# from fastapi import APIRouter, Depends, HTTPException, status
# from pymongo.database import Database
# from app.database.db import get_db
# from app.models.kpi_model import DateRequest
# from collections import defaultdict
# import re
# import math
# from typing import Dict, Any, List

# router = APIRouter()

# @router.post("/volume")
# def get_volume(payload: dict, db: Database = Depends(get_db)):
#     try:
#         date = payload.get("date")
#         start_time = payload["start_time"]
#         end_time = payload["end_time"]

#         if date not in db.list_collection_names():
#             raise HTTPException(status_code=404, detail=f"No collection found for date {date}")

#         collection = db[date]
#         parcels = list(collection.find({}))

#         if not parcels:
#             return {"message": "No data found for this date"}

#         # Filter by start and end time (only HH:MM)
#         def is_in_time_range(ts_str):
#             try:
#                 hhmm = ts_str.split(",")[0][:5]  # "HH:MM:SS" -> "HH:MM"
#                 return start_time <= hhmm <= end_time
#             except:
#                 return False

#         parcels = [
#             p for p in parcels
#             if is_in_time_range(p.get("timestamp", "00:00"))
#         ]

#         height_count, width_count, length_count = defaultdict(int), defaultdict(int), defaultdict(int)
#         for parcel in parcels:
#             volume = parcel.get("volume_data", {})
#             h, w, l = volume.get("height"), volume.get("width"), volume.get("length")

#             if h is not None:
#                 height_count[h] += 1
#             if w is not None:
#                 width_count[w] += 1
#             if l is not None:
#                 length_count[l] += 1

#         return {
#             "height_distribution": dict(height_count),
#             "width_distribution": dict(width_count),
#             "length_distribution": dict(length_count)
#         }

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from app.database.db import get_db
from collections import defaultdict
import re
import math
from typing import Dict, Any, List

router = APIRouter()

_HHMM_RE = re.compile(r"(\d{2}:\d{2})")
timestamp_field_names = ["timestamp", "created_at", "time"]

def extract_hhmm(ts: str) -> str:
    """Extract first HH:MM from a timestamp string."""
    if not ts or not isinstance(ts, str):
        return ""
    m = _HHMM_RE.search(ts)
    return m.group(1) if m else ""

def time_in_range(start: str, end: str, target: str) -> bool:
    """Inclusive time range check, supports overnight ranges."""
    def to_min(t: str) -> int:
        hh, mm = map(int, t.split(":"))
        return hh * 60 + mm
    s, e, t = to_min(start), to_min(end), to_min(target)
    if s <= e:
        return s <= t <= e
    return t >= s or t <= e  # overnight

def compute_normal_distribution(values: List[float], bins: int = 100) -> Dict[str, float]:
    """Compute normal distribution y-values for plotting."""
    if not values:
        return {}
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std = math.sqrt(variance)
    min_val, max_val = min(values), max(values)
    step = (max_val - min_val) / bins if bins > 0 else 1
    x_points = [min_val + i * step for i in range(bins + 1)]
    y_points = [
        (1 / (std * math.sqrt(2 * math.pi))) * math.exp(-0.5 * ((x - mean) / std) ** 2)
        for x in x_points
    ]
    return {str(round(x, 2)): round(y, 6) for x, y in zip(x_points, y_points)}

@router.post("/volume")
def get_volume(payload: dict, db: Database = Depends(get_db)) -> Dict[str, Any]:
    # Validate input
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload must be JSON object")
    date = payload.get("date")
    if not date:
        raise HTTPException(status_code=400, detail="Missing 'date'")
    try:
        start_time = payload["start_time"]
        end_time = payload["end_time"]
    except KeyError as ke:
        raise HTTPException(status_code=400, detail=f"Missing required field: {ke}")

    if not re.fullmatch(r"\d{2}:\d{2}", start_time) or not re.fullmatch(r"\d{2}:\d{2}", end_time):
        raise HTTPException(status_code=422, detail="start_time and end_time must be HH:MM")

    # Get collection
    if date not in db.list_collection_names():
        raise HTTPException(status_code=404, detail=f"No collection for date {date}")
    collection = db[date]
    parcels = list(collection.find({}))
    if not parcels:
        return {"height_distribution": {}, "width_distribution": {}, "length_distribution": {},
                "normal_height": {}, "normal_width": {}, "normal_length": {},
                "kpi": {"allocated_total": 0, "under_400_count": 0, "above_600_count": 0,
                        "under_400_pct": 0.0, "above_600_pct": 0.0}}

    height_count, width_count, length_count = defaultdict(int), defaultdict(int), defaultdict(int)
    height_vals, width_vals, length_vals = [], [], []
    allocated_total, under_400, above_600 = 0, 0, 0

    for p in parcels:
        ts_raw = next((p.get(k) for k in timestamp_field_names if k in p), None)
        hhmm = extract_hhmm(ts_raw)
        if not hhmm or not time_in_range(start_time, end_time, hhmm):
            continue

        vol = p.get("volume_data", {}) or {}
        h, w, l = vol.get("height"), vol.get("width"), vol.get("length")

        if h is not None:
            height_count[str(h)] += 1
            try: height_vals.append(float(h))
            except: pass
        if w is not None:
            width_count[str(w)] += 1
            try: width_vals.append(float(w))
            except: pass
        if l is not None:
            length_count[str(l)] += 1
            try:
                l_val = float(l)
                length_vals.append(l_val)
                if l_val > 0:
                    allocated_total += 1
                    if l_val <= 400:
                        under_400 += 1
                    if l_val >= 600:
                        above_600 += 1
            except: pass

    kpi = {
        "allocated_total": allocated_total,
        "under_400_count": under_400,
        "above_600_count": above_600,
        "under_400_pct": round(100 * under_400 / allocated_total, 2) if allocated_total else 0.0,
        "above_600_pct": round(100 * above_600 / allocated_total, 2) if allocated_total else 0.0
    }

    return {
        "height_distribution": dict(height_count),
        "width_distribution": dict(width_count),
        "length_distribution": dict(length_count),
        "normal_height": compute_normal_distribution(height_vals),
        "normal_width": compute_normal_distribution(width_vals),
        "normal_length": compute_normal_distribution(length_vals),
        "kpi": kpi
    }
