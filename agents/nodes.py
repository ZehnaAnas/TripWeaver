from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain.agents import create_agent
import json
import traceback

from .mcp_client import mcp_client
from .llm import llm
from .prompts import (
    SYSTEM_PROMPT,
    SYSTEM_PROMPT_FOR_UNKNOWN_NODE,
    HOTEL_NODE_PROMPT,
    FLIGHT_NODE_PROMPT,
    WEATHER_NODE_PROMPT,
    PLACES_NODE_PROMPT,
    ITINERARY_NODE_PROMPT,
    FINALIZER_PROMPT,
)
from .entity import GraphState
from .mcp_utils import _extract_mcp_error


class TravelIntent(BaseModel):
    intent: Literal["hotel", "flight", "weather", "activities", "itinerary", "unknown"] = Field(
        default="unknown",
        description="The single travel intent that best matches the user's message.",
    )


travel_extractor = llm.with_structured_output(TravelIntent)


def router(state: GraphState) -> dict:
    try:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(state["messages"])
        extracted = travel_extractor.invoke(messages)
        intent = extracted.intent or "unknown"
    except Exception:
        intent = "unknown"

    return {"intent": intent, "activity_status": "ROUTING"}


def route_after_extraction(state: GraphState) -> str:
    intent = state.get("intent", "unknown")
    if intent in ("hotel", "flight", "weather", "activities", "itinerary"):
        return intent
    return "unknown"


def _last_ai_text(result_messages) -> str:
    final = result_messages[-1] if result_messages else None
    return getattr(final, "content", "") or "I'm not sure how to help with that."


def _parse_agent_tool_content(raw_content):
    try:
        parsed = json.loads(raw_content)
    except (TypeError, json.JSONDecodeError):
        return raw_content
    if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict) and parsed[0].get("type") == "text":
        try:
            return json.loads(parsed[0]["text"])
        except (TypeError, json.JSONDecodeError, KeyError):
            return parsed
    return parsed

async def hotel_node(state: GraphState) -> dict:
    try:
        async with mcp_client.session("hotel") as session:
            hotel_tools = await load_mcp_tools(session)

            booking_agent = create_agent(
                model=llm,
                tools=hotel_tools,
                system_prompt=HOTEL_NODE_PROMPT,
            )

            agent_result = await booking_agent.ainvoke({"messages": list(state["messages"])})
            result_messages = agent_result.get("messages", [])

            tool_messages = [m for m in result_messages if type(m).__name__ == "ToolMessage"]
            last_tool_message = tool_messages[-1] if tool_messages else None
            llm_text = _last_ai_text(result_messages)

            if last_tool_message is None:
                return {"response_text": llm_text}

            result = _parse_agent_tool_content(last_tool_message.content)
            error_message = _extract_mcp_error(result)
            if error_message:
                return {
                    "hotel_results": [], "flight_results": [],
                    "response_text": llm_text or f"I couldn't complete that request — {error_message}",
                }

            confirmation = result[0] if isinstance(result, list) and len(result) == 1 else result
            if isinstance(confirmation, dict) and confirmation.get("confirmationId"):
                return {
                    "hotel_results": [], "flight_results": [],
                    "last_confirmation": confirmation,
                    "response_text": llm_text,
                }

            if isinstance(result, list):
                return {"hotel_results": result, "flight_results": [], "response_text": llm_text}

            return {"hotel_results": [], "flight_results": [], "response_text": llm_text}

    except Exception:
        traceback.print_exc()
        return {"hotel_results": [], "flight_results": [], "response_text": "The hotel booking service is currently unavailable. Please try again shortly."}

async def flight_node(state: GraphState) -> dict:
    try:
        async with mcp_client.session("flight") as session:
            flight_tools = await load_mcp_tools(session)

            booking_agent = create_agent(
                model=llm,
                tools=flight_tools,
                system_prompt=FLIGHT_NODE_PROMPT,
            )

            agent_result = await booking_agent.ainvoke({"messages": list(state["messages"])})
            result_messages = agent_result.get("messages", [])

            tool_messages = [m for m in result_messages if type(m).__name__ == "ToolMessage"]
            last_tool_message = tool_messages[-1] if tool_messages else None
            llm_text = _last_ai_text(result_messages)

            if last_tool_message is None:
                return {"response_text": llm_text}

            result = _parse_agent_tool_content(last_tool_message.content)
            error_message = _extract_mcp_error(result)
            if error_message:
                return {
                    "hotel_results": [], "flight_results": [],
                    "response_text": llm_text or f"I couldn't complete that request — {error_message}",
                }

            confirmation = result[0] if isinstance(result, list) and len(result) == 1 else result
            if isinstance(confirmation, dict) and confirmation.get("confirmationId"):
                return {
                    "hotel_results": [], "flight_results": [],
                    "last_confirmation": confirmation,
                    "response_text": llm_text,
                }

            if isinstance(result, list):
                return {"hotel_results": [], "flight_results": result, "response_text": llm_text}

            return {"hotel_results": [], "flight_results": [], "response_text": llm_text}

    except Exception:
        traceback.print_exc()
        return {"hotel_results": [], "flight_results": [], "response_text": "Flight search is temporarily unavailable — please try again shortly."}

async def weather_node(state: GraphState) -> dict:
    try:
        async with mcp_client.session("weather") as session:
            weather_tools = await load_mcp_tools(session)
            weather_agent = create_agent(model=llm, tools=weather_tools, system_prompt=WEATHER_NODE_PROMPT)

            agent_result = await weather_agent.ainvoke({"messages": list(state["messages"])})
            result_messages = agent_result.get("messages", [])
            tool_messages = [m for m in result_messages if type(m).__name__ == "ToolMessage"]
            llm_text = _last_ai_text(result_messages)

            if not tool_messages:
                return {"response_text": llm_text}

            result = _parse_agent_tool_content(tool_messages[-1].content)
            weather_data = result[0] if isinstance(result, list) and len(result) == 1 else result
            error_message = _extract_mcp_error(weather_data)
            if error_message:
                return {"weather_results": [], "response_text": llm_text or f"I couldn't get the weather - {error_message}"}

            return {
                "weather_results": [weather_data] if isinstance(weather_data, dict) else (weather_data if isinstance(weather_data, list) else []),
                "response_text": llm_text,
            }
    except Exception:
        traceback.print_exc()
        return {"weather_results": [], "response_text": "The weather service is currently unavailable. Please try again shortly."}


async def places_node(state: GraphState) -> dict:
    try:
        async with mcp_client.session("places") as session:
            place_tools = await load_mcp_tools(session)
            places_agent = create_agent(model=llm, tools=place_tools, system_prompt=PLACES_NODE_PROMPT)

            agent_result = await places_agent.ainvoke({"messages": list(state["messages"])})
            result_messages = agent_result.get("messages", [])
            tool_messages = [m for m in result_messages if type(m).__name__ == "ToolMessage"]
            llm_text = _last_ai_text(result_messages)

            if not tool_messages:
                return {"response_text": llm_text}

            result = _parse_agent_tool_content(tool_messages[-1].content)
            error_message = _extract_mcp_error(result)
            if error_message:
                return {"activity_results": [], "response_text": llm_text or f"I couldn't find places - {error_message}"}

            places = result if isinstance(result, list) else []
            return {"activity_results": places, "response_text": llm_text}
    except Exception:
        traceback.print_exc()
        return {"activity_results": [], "response_text": "The places service is currently unavailable. Please try again shortly."}


def itinerary_node(state: GraphState) -> dict:
    try:
        messages = [SystemMessage(content=ITINERARY_NODE_PROMPT)] + list(state["messages"])
        response = llm.invoke(messages)
        return {"response_text": response.content}
    except Exception:
        traceback.print_exc()
        return {"response_text": "I couldn't put together an itinerary right now. Please try again shortly."}


def unknown_node(state: GraphState) -> dict:
    try:
        messages = [SystemMessage(content=SYSTEM_PROMPT_FOR_UNKNOWN_NODE)] + list(state["messages"])
        response = llm.invoke(messages)
        return {"response_text": response.content}
    except Exception as e:
        return {"response_text": f"I couldn't understand your request clearly. Error: {str(e)}"}


def finalize_answer(state: GraphState) -> dict:
    draft = state.get("response_text")
    if not draft:
        return {"response_text": "I'm not sure how to help with that - could you rephrase?"}

    intent = state.get("intent")
    raw_data = None
    if intent == "hotel":
        raw_data = state.get("last_confirmation") or state.get("hotel_results")
    elif intent == "flight":
        raw_data = state.get("last_confirmation") or state.get("flight_results")
    elif intent == "weather":
        raw_data = state.get("weather_results")
    elif intent == "activities":
        raw_data = state.get("activity_results")

    user_content = f"Draft answer from the specialist agent:\n{draft}"
    if raw_data:
        user_content += (
            "\n\nThe actual raw data behind this draft - use this to verify every "
            "fact and never contradict it, but don't just dump it verbatim:\n"
            f"{json.dumps(raw_data, indent=2, default=str)}"
        )

    try:
        messages = [SystemMessage(content=FINALIZER_PROMPT), HumanMessage(content=user_content)]
        response = llm.invoke(messages)
        return {"response_text": response.content}
    except Exception:
        traceback.print_exc()
        return {"response_text": draft}