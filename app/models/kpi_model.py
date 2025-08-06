from pydantic import BaseModel
from typing import Optional

class DateRequest(BaseModel):
    date: str  # format: "YYYY-MM-DD"
    bin_size: Optional[int] = None  # in minutes: 10, 15, 30, 45, or 60
    start_time: Optional[str] = None    # "HH:MM" format
    end_time: Optional[str] = None # "HH:MM" format
