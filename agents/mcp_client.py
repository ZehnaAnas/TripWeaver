from langchain_mcp_adapters.client import MultiServerMCPClient

_TOOL_CACHE: dict[str, list] = {}
async def get_tools(server_name: str) -> list:
    """Load MCP tools once per process instead of once per request."""
    if server_name not in _TOOL_CACHE:
        _TOOL_CACHE[server_name] = await mcp_client.get_tools(server_name=server_name)
    return _TOOL_CACHE[server_name]

mcp_client = MultiServerMCPClient({
    "hotel":{
        "url":"http://localhost:8001/mcp",
        "transport":"streamable_http"
    },
    "flight":{
        "url":"http://localhost:8002/mcp",
        "transport":"streamable_http"
    },
    "activities":{
        "url":"http://localhost:8003/mcp",
        "transport":"streamable_http"
    }
})