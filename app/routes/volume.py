from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from app.database.db import get_db
from app.models.kpi_model import DateRequest
from collections import defaultdict
from typing import Dict, Any, List
import numpy as np

router = APIRouter()

@router.post("/volume")
def get_volume(payload: DateRequest, db: Database = Depends(get_db)) -> Dict[str, Any]:
    """
    Retrieves height, width, and length distributions + normal distribution
    parameters for parcels within a given date and time range.
    """

    date = payload.date
    start_time = payload.start_time
    end_time = payload.end_time

    # Ensure collection exists
    if date not in db.list_collection_names():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No collection found for date {date}"
        )

    collection = db[date]
    parcels: List[Dict[str, Any]] = list(collection.find({}))

    if not parcels:
        return {"message": "No data found for this date"}

    def extract_hhmm(ts_str: str) -> str:
        """
        Extract HH:MM from HH:MM:SS,milliseconds.
        If format invalid, returns '00:00'.
        """
        try:
            # Example: "09:15:26,625" -> "09:15"
            return ts_str.split(",")[0][:5]
        except Exception:
            return "00:00"

    def is_in_time_range(ts_str: str) -> bool:
        """Check if timestamp is within the given HH:MM range."""
        hhmm = extract_hhmm(ts_str)
        return start_time <= hhmm <= end_time

    # Filter parcels by time range
    filtered_parcels = [
        p for p in parcels
        if is_in_time_range(p.get("registerTS", "00:00"))
    ]

    height_count = defaultdict(int)
    width_count = defaultdict(int)
    length_count = defaultdict(int)

    heights, widths, lengths = [], [], []

    for parcel in filtered_parcels:
        volume = parcel.get("volume_data", {})
        if (h := volume.get("height")) is not None:
            height_count[h] += 1
            heights.append(h)
        if (w := volume.get("width")) is not None:
            width_count[w] += 1
            widths.append(w)
        if (l := volume.get("length")) is not None:
            length_count[l] += 1
            lengths.append(l)

    def normal_stats(values: List[float]) -> Dict[str, float]:
        """Return mean and std deviation for normal distribution."""
        if not values:
            return {"mean": 0, "std_dev": 0}
        arr = np.array(values)
        return {
            "mean": round(float(np.mean(arr)), 2),
            "std_dev": round(float(np.std(arr)), 2)
        }

    return {
        "height_distribution": dict(height_count),
        "width_distribution": dict(width_count),
        "length_distribution": dict(length_count),
        "normal_distribution": {
            "height": normal_stats(heights),
            "width": normal_stats(widths),
            "length": normal_stats(lengths)
        }
    }