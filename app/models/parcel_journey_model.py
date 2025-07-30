# app/models/parcel_journey_model.py

from pydantic import BaseModel

class ParcelJourneyRequest(BaseModel):
    date: str
    search_by: str  # must be one of: 'host_id', 'barcode', 'alibi_id'
    search_value: str
