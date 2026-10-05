"""Municipal transit MCP STDIO server."""
from __future__ import annotations
import sys, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hw05_tools import search, detail_lookup, aggregate
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
def search_incidents(query: str):
    return search(query)
def incident_detail(incident_id: int):
    return detail_lookup(incident_id)
def incident_aggregate(inputs: dict | None = None):
    if inputs:
        return {
            "ok": False,
            "data": None,
            "error": "aggregate accepts no inputs",
        }
    return aggregate()
try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("municipal-transit")
    mcp.tool()(search_incidents)
    mcp.tool()(incident_detail)
    mcp.tool()(incident_aggregate)
except ImportError:
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer("municipal-transit")
    mcp.add_tool(search_incidents)
    mcp.add_tool(incident_detail)
    mcp.add_tool(incident_aggregate)
if __name__ == "__main__":
    import asyncio
    if hasattr(mcp, "run_stdio_async"):
        asyncio.run(mcp.run_stdio_async())
    else:
        mcp.run(transport="stdio")
