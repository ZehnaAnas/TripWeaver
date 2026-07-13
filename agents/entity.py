from typing import List, Optional, TypedDict

class GraphState(TypedDict):
    messages: List[str]

    intent: str
    sub_action: str

    activity_status:str
    tool_status:str

    city: Optional[str]
    city_code: Optional[str]
    check_in: Optional[str]
    check_out: Optional[str]

    origin: Optional[str]
    destination: Optional[str]
    flight_date: Optional[str]

    passenger_email:Optional[str]
    passenger_name:Optional[str]
    booking_confirmed:bool

    flying_type:Optional[str]
    date_of_birth:Optional[str]
    passport_number:Optional[str]

    nationality:Optional[str]
    guest_name:Optional[str]
    guest_email:Optional[str]
    airline:Optional[str]

    room_type:Optional[str]
    hotel_id:Optional[str]
    flight_id:Optional[str]
    star_rating:Optional[int]

    hotel_budget:Optional[int] 
    flight_budget:Optional[int] 
    origin_country:Optional[str] 

    destination_country:Optional[str] 
    hotel_name: Optional[str]

    hotel_search_cache: List[dict]
    flight_search_cache : List[dict]

    hotel_results : List[dict]
    flight_results : List[dict]
    response_text : str

   

    