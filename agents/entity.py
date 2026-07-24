from typing import Annotated, List, Optional, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage


class GraphState(TypedDict, total=False):
    messages: Annotated[List[AnyMessage], add_messages]

    # Conversation/session
    session_id: Optional[str]

    # Routing
    intent: str
    sub_action :Optional[str]

    # Final response
    response_text: str

    # UI status
    activity_status: str

    # Search results
    hotel_results: List[dict]
    flight_results: List[dict]
    activity_results: List[dict]

    # Currently selected item for booking
    selected_hotel:Optional[dict]
    selected_flight:Optional[dict]

    # Type of pending action
    pending_action: Optional[str]
    
    # Indicates that the system is waiting for user confirmation
    awaiting_confirmation: bool

    # Booking details
    booking_details:Optional[dict]

    # Last booking result
    last_confirmation:Optional[dict]

