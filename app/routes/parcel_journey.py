from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from typing import List, Dict
import json

from app.database.db import get_db
from app.models.parcel_journey_model import ParcelJourneyRequest

router = APIRouter()

@router.post("/parcel-journey")
def get_parcel_journey(payload: ParcelJourneyRequest, db: Database = Depends(get_db)) -> List[Dict]:
    collection_name = payload.date

    if collection_name not in db.list_collection_names():
        raise HTTPException(status_code=404, detail="Collection not found")

    # Build MongoDB query
    if payload.search_by == "host_id":
        query = {"hostId": payload.search_value}
    elif payload.search_by == "barcode":
        query = {"barcode_data.barcodes": {"$in": [payload.search_value]}}  # Nested field
    elif payload.search_by == "alibi_id":
        query = {"alibi_id": payload.search_value}
    else:
        raise HTTPException(status_code=400, detail="Invalid search_by value")

    try:
        results = []
        for doc in db[collection_name].find(query):
            # Safely convert event["raw"] to stringified JSON for frontend compatibility
            raw_data = {
                str(i): event.get("raw")
                for i, event in enumerate(doc.get("events", []))
                if event.get("raw") is not None
            }

            volume_data = doc.get("volume_data", {})
            volume_str = (
            f"L:{volume_data.get('length', '')}, "
            f"H:{volume_data.get('height', '')}, "
            f"W:{volume_data.get('width', '')}, "
            f"BoxVol:{volume_data.get('box_volume', '')}, "
            f"RealVol:{volume_data.get('real_volume', '')}"
        )

            results.append({
                "host_id": doc.get("hostId"),
                "status": doc.get("status"),
                "barcode": doc.get("barcode_data", {}).get("barcodes", []),  # Return full list of barcodes
                "alibi_id": doc.get("alibi_id"),
                "register_on_and_at": f'{doc.get("registerTS", "")} {doc.get("Registered_location", "")}',
                "identification_on_and_at": f'{doc.get("identificationTS", "")} {doc.get("identification_location", "")}',
                "exit_on_and_at": f'{doc.get("exitTS", "")} {doc.get("exit_location", "")}',
                "destination": doc.get("actual_destination"),
                "volume":volume_str,
                "RAW": json.dumps(raw_data, indent=2)  # Convert to formatted string
            })

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")
