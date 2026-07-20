import json

def _extract_mcp_error(result):
    """
    Returns a human-readable error message if the (already _parse_mcp_result'd) 
    tool result represents an error, otherwise None.

    Why this is needed: MCP wraps a tool's return value in exactly one content
    block whether the underlying Python function returned a single dict 
    (e.g. an error) or - after _parse_mcp_result unwraps it - a list containing
    exactly one real item. Both shapes look identical by the time they reach 
    this code (a one-item list, or a bare dict). Checking for "error" content at both possible shapes lets every node reliably distinguish a real
    single-result list from a wrapped error, instead of silently treating an error dict as if it were a valid hotel/flight/weather/etc. result.
    """
    candidate = result
    if isinstance(candidate, list) and len(candidate) == 1:
        candidate = candidate[0]
    if isinstance(candidate,dict) and candidate.get("error"):
        message = candidate.get("message")
        if not message:
            error_value = candidate.get("error")
            message = error_value if isinstance(error_value,str) else "The service returned an error"
        return message
    return
