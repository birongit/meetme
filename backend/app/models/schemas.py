from pydantic import BaseModel, Field
from typing import List, Optional

class Slot(BaseModel):
    start: str = Field(description="ISO8601 start time")
    end: str = Field(description="ISO8601 end time")

class SlotList(BaseModel):
    slots: List[Slot] = Field(description="List of suggested meeting slots")
    message: Optional[str] = Field(default="", description="A friendly message to the user explaining the choices or answering their question.")

class BookingRequest(BaseModel):
    start: str
    end: str
    summary: Optional[str] = None
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
