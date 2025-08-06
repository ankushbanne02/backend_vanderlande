from pydantic import BaseModel

class DateRequest(BaseModel):
    date: str  # format: "YYYY-MM-DD"
    bin_size: int     # in minutes: 10, 15, 30, 45, or 60
    start_time: str  # "HH:MM" format
    end_time: str  # "HH:MM" format
