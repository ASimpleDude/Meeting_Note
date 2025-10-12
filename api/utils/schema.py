from pydantic import BaseModel
from typing import List, Optional

class MeetingSummarySchema(BaseModel):
    meeting_title: Optional[str]
    participants: List[str]
    summary: str
    key_points: List[str]
    blockers: Optional[List[str]]
    next_action: Optional[List[str]]
    