from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    session_id:Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id : str
    hotels: Optional[List[dict]] = None
    flights: Optional[List[dict]] = None

class ResetRequest(BaseModel):
    session_id:str