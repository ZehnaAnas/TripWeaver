import json

def _parse_mcp_result(result):
    """MCP tools returning list[dict] come back as content blocks
    ({'type':'text','text':'<json string>'}) rather than parsed
    dicts - unwrap them here before the rest of the pipeline touches them.
    """
    if isinstance(result,list):
        parsed = []
        for item in result:
            if isinstance(item,dict) and item.get("type") == "text" and "text" in item:
                try:
                    parsed.append(json.loads(item["text"]))
                except (json.JSONDecodeError, TypeError):
                    parsed.append(item)
            else:
                parsed.append(item)
        return parsed
    return result

