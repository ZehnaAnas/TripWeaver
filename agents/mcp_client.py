from langchain_mcp_adapters.client import MultiServerMCPClient
import os
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()

HOTEL_MCP_URL = os.getenv("HOTEL_MCP_URL", "http://localhost:8001/mcp")
FLIGHT_MCP_URL = os.getenv("FLIGHT_MCP_URL", "http://localhost:8002/mcp")
ACTIVITY_MCP_URL = os.getenv("ACTIVITY_MCP_URL", "http://localhost:8003/mcp")

mcp_client = MultiServerMCPClient({
    "hotel": {"url": HOTEL_MCP_URL, "transport": "streamable_http"},
    "flight": {"url": FLIGHT_MCP_URL, "transport": "streamable_http"},
    "activities": {"url": ACTIVITY_MCP_URL, "transport": "streamable_http"},
})

_TOOL_CACHE: dict[str, list] = {}
async def get_tools(server_name: str) -> list:
    """Load MCP tools once per process instead of once per request."""
    if server_name not in _TOOL_CACHE:
        _TOOL_CACHE[server_name] = await mcp_client.get_tools(server_name=server_name)
    return _TOOL_CACHE[server_name]