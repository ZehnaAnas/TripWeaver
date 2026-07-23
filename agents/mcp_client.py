from langchain_mcp_adapters.client import MultiServerMCPClient

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