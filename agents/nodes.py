from typing import Literal,Optional
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
    ACTIVITY_NODE_PROMPT,
    FINALIZER_PROMPT,
)
from .entity import GraphState
from .mcp_utils import _extract_mcp_error


class TravelIntent(BaseModel):
    intent: Literal["hotel", "flight", "activities", "unknown"] = Field(default="unknown")
    sub_action: Optional[Literal["search","list_all","book"]] = None


travel_extractor = llm.with_structured_output(TravelIntent)

def router(state: GraphState) -> dict:
    try:
        messages = list(state.get("messages",[]))
        current_intent = state.get("intent")
        pending_action = state.get("pending_action")
        selected_hotel = state.get("selected_hotel")
        selected_flight = state.get("selected_flight")
        awaiting_confirmation = state.get("awaiting_confirmation",False)

        context = f"""
        CURRENT WORKFLOW STATE:
        Previous intent:
        {current_intent}
        Pending action:
        {pending_action}
        Selected hotel:
        {json.dumps(selected_hotel,default=str) if selected_hotel else "None"}
        Selected flight:
        {json.dumps(selected_flight, default=str) if selected_flight else "None"}
        Awaiting confirmation:
        {awaiting_confirmation}
        """
        router_messages = [SystemMessage(content=SYSTEM_PROMPT+"\n\n"+context)]+messages
        extracted = travel_extractor.invoke(router_messages)
        if isinstance(extracted, dict):
            intent = extracted.get("intent", "unknown")
            sub_action = extracted.get("sub_action")
        else:
            intent = getattr(extracted, "intent", "unknown")
            sub_action = getattr(extracted,"sub_action",None)
        intent = intent or "unknown"
        if pending_action == "book_hotel" and selected_hotel:
            intent = "hotel"
            sub_action = "book"
        elif pending_action == "book_flight" and selected_flight:
            intent = "flight"
            sub_action = "book"
        return {
            "intent":intent,
            "sub_action":sub_action,
            "activity_status":"ROUTING"
        }
    except Exception:
        traceback.print_exc()

        if state.get("pending_action") == "book_hotel":
            return{
                "intent":"hotel",
                "sub_action":"book",
                "activity_status":"ROUTING",
            }
        if state.get("pending_action") == "book_flight":
            return{
                "intent":"flight",
                "sub_action":"book",
                "activity_status":"ROUTING",
            }

        return {"intent":"unknown","sub_action":None ,"activity_status": "ROUTING"}


def route_after_extraction(state: GraphState) -> str:
    intent = state.get("intent", "unknown")
    if intent in ("hotel", "flight","activities", "itinerary"):
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
            previous_hotels = state.get("hotel_results") or []
            selected_hotel = state.get("selected_hotel")
            agent_context = f"""
            CURRENT TRIPWEAVER STATE

            Latest hotel results:
            {json.dumps(previous_hotels, indent=2,default=str)}
            Selected hotel:
            {json.dumps(selected_hotel,indent=2,default=str)}
            Pending action:
            {state.get("pending_action")}
            Awaiting confirmation:
            {state.get("awaiting_confirmation")}
            Booking details:
            {json.dumps(state.get("booking_details"),indent=2,default=str)}
            """
            agent_messages = [
                SystemMessage(content=agent_context),
                *list(state["messages"])[-10:],
            ]
            agent_result = await booking_agent.ainvoke({"messages":agent_messages})
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
                    "hotel_results": [],
                    "response_text": llm_text or f"I couldn't complete that request — {error_message}",
                }

            confirmation = result[0] if isinstance(result, list) and len(result) == 1 else result
            if isinstance(confirmation, dict) and confirmation.get("confirmationId"):
                return {
                    "hotel_results": [],
                    "last_confirmation": confirmation,
                    "pending_action":None,
                    "awaiting_confirmation":False,
                    "response_text": llm_text,
                }

            if isinstance(result, list):
                return {"hotel_results": result, "response_text": llm_text}

            return { "response_text": llm_text}

    except Exception:
        traceback.print_exc()
        return {"hotel_results": [], "response_text": "The hotel booking service is currently unavailable. Please try again shortly."}

async def flight_node(state: GraphState) -> dict:
    try:
        async with mcp_client.session("flight") as session:
            flight_tools = await load_mcp_tools(session)

            booking_agent = create_agent(
                model=llm,
                tools=flight_tools,
                system_prompt=FLIGHT_NODE_PROMPT,
            )
            agent_context = f"""
            CURRENT TRIPWEAVER STATE

            Latest flight results:
            {json.dumps(state.get("flight_results") or [], indent=2,default=str)}
            Selected flight:
            {json.dumps(state.get("selected_flight"),indent=2,default=str)}
            Pending action:
            {state.get("pending_action")}
            Awaiting confirmation:
            {state.get("awaiting_confirmation")}
            Booking details:
            {json.dumps(state.get("booking_details"),indent=2,default=str)}
            """
            agent_result = await booking_agent.ainvoke({"messages":[
                SystemMessage(content=agent_context),
                *list(state["messages"])[-10:],
                ]})
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
                    "flight_results": [],
                    "response_text": llm_text or f"I couldn't complete that request — {error_message}",
                }

            confirmation = (result[0] if isinstance(result, list) and len(result) == 1 else result)
            if isinstance(confirmation, dict) and confirmation.get("confirmationId"):
                            return {
                                "flight_results": [],
                                "last_confirmation": confirmation,
                                "response_text": llm_text,
                            }

            if isinstance(result, list):
                return {"flight_results": result, "response_text": llm_text}

            return {"flight_results": [], "response_text": llm_text}

    except Exception:
        traceback.print_exc()
        return {"flight_results": [], "response_text": "Flight search is temporarily unavailable — please try again shortly."}


async def activity_node(state: GraphState) -> dict:
    try:
        async with mcp_client.session("activities") as session:
            activity_tools = await load_mcp_tools(session)
            activity_agent = create_agent(model=llm, tools=activity_tools, system_prompt=ACTIVITY_NODE_PROMPT)

            agent_result = await activity_agent.ainvoke({"messages": list(state["messages"])})
            result_messages = agent_result.get("messages", [])
            tool_messages = [m for m in result_messages if type(m).__name__ == "ToolMessage"]
            llm_text = _last_ai_text(result_messages)

            if not tool_messages:
                return {"response_text": llm_text}

            result = _parse_agent_tool_content(tool_messages[-1].content)
            error_message = _extract_mcp_error(result)
            if error_message:
                return {"activity_results": [], "response_text": llm_text or f"I couldn't find activities - {error_message}"}

            activities = result if isinstance(result, list) else []
            return {"activity_results": activities, "response_text": llm_text}
    except Exception:
        traceback.print_exc()
        return {"activity_results": [], "response_text": "The activities service is currently unavailable. Please try again shortly."}

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
        return {"response_text": "I'm not sure how to help with that. Could you rephrase?"}

    try:
        messages = [
            SystemMessage(content=FINALIZER_PROMPT),
            HumanMessage(content=draft),
        ]
        response = llm.invoke(messages)
        return {
            "response_text":response.content
        }
    except Exception as e:
        print(f"[finalize_answer] Failed:{e}")
        traceback.print_exc()
        return{
            "response_text":draft
        }