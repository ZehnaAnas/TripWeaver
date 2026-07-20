from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from .nodes import (
    router, hotel_node, flight_node, weather_node, places_node,
    itinerary_node, unknown_node, finalize_answer, route_after_extraction,
)
from .entity import GraphState


def build_graph() -> StateGraph:
    builder = StateGraph(GraphState)

    builder.add_node("router", router)
    builder.add_node("hotel_node", hotel_node)
    builder.add_node("flight_node", flight_node)
    builder.add_node("weather_node", weather_node)
    builder.add_node("places_node", places_node)
    builder.add_node("itinerary_node", itinerary_node)
    builder.add_node("unknown_node", unknown_node)
    builder.add_node("finalize_answer", finalize_answer)

    builder.add_edge(START, "router")

    builder.add_conditional_edges(
        "router",
        route_after_extraction,
        {
            "hotel": "hotel_node",
            "flight": "flight_node",
            "weather": "weather_node",
            "activities": "places_node",
            "itinerary": "itinerary_node",
            "unknown": "unknown_node",
        },
    )

    builder.add_edge("hotel_node", "finalize_answer")
    builder.add_edge("flight_node", "finalize_answer")
    builder.add_edge("weather_node", "finalize_answer")
    builder.add_edge("places_node", "finalize_answer")
    builder.add_edge("itinerary_node", "finalize_answer")
    builder.add_edge("unknown_node", "finalize_answer")
    builder.add_edge("finalize_answer", END)

    return builder


graph = build_graph().compile(checkpointer=InMemorySaver())