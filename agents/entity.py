from typing import Annotated, List, Optional, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


class GraphState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    
    session_id: Optional[str]
    intent: str
    response_text: str
    activity_status: str
    hotel_results: List[dict]
    flight_results: List[dict]
    weather_results: List[dict]
    activity_results: List[dict]