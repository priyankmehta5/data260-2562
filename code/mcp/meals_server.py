"""TheMealDB MCP STDIO server with offline-testable tool functions."""
from __future__ import annotations
import logging
import sys
from typing import Any
import httpx
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
BASE = "https://www.themealdb.com/api/json/v1/1"
def _get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        response = httpx.get(BASE + path, params=params, timeout=8.0)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("TheMealDB returned a non-object JSON response")
        return payload
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"TheMealDB request failed: {exc}") from exc
def _limit(limit: int, default: int) -> int:
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 25:
        raise ValueError("limit must be an integer from 1 through 25")
    return limit or default
def _detail(meal: dict[str, Any]) -> dict[str, Any]:
    ingredients = [{"name": meal[f"strIngredient{i}"].strip(), "measure": meal[f"strMeasure{i}"].strip()}
                   for i in range(1, 21) if meal.get(f"strIngredient{i}", "").strip()]
    return {"id": meal.get("idMeal"), "name": meal.get("strMeal"), "category": meal.get("strCategory"),
            "area": meal.get("strArea"), "instructions": meal.get("strInstructions"), "image": meal.get("strMealThumb"),
            "source": meal.get("strSource"), "youtube": meal.get("strYoutube"), "ingredients": ingredients}
def search_meals_by_name(query: str, limit: int = 5) -> list[dict[str, Any]]:
    if not isinstance(query, str) or not query.strip(): raise ValueError("query must be non-empty")
    payload = _get("/search.php", {"s": query.strip()})
    meals = payload.get("meals") or []
    return [{"id": m.get("idMeal"), "name": m.get("strMeal"), "area": m.get("strArea"), "category": m.get("strCategory"), "thumb": m.get("strMealThumb")} for m in meals[:_limit(limit, 5)]]
def meals_by_ingredient(ingredient: str, limit: int = 12) -> list[dict[str, Any]]:
    if not isinstance(ingredient, str) or not ingredient.strip(): raise ValueError("ingredient must be non-empty")
    meals = _get("/filter.php", {"i": ingredient.strip()}).get("meals") or []
    return [{"id": m.get("idMeal"), "name": m.get("strMeal"), "thumb": m.get("strMealThumb")} for m in meals[:_limit(limit, 12)]]
def random_meal() -> dict[str, Any]:
    meals = _get("/random.php").get("meals") or []
    if not meals: raise RuntimeError("no random meal returned")
    return _detail(meals[0])
def meal_details(id: str | int) -> dict[str, Any]:
    if not str(id).strip(): raise ValueError("id must be non-empty")
    meals = _get("/lookup.php", {"i": str(id)}).get("meals") or []
    if not meals: raise ValueError("meal not found")
    return _detail(meals[0])
try:
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("meals")
    mcp.tool()(search_meals_by_name); mcp.tool()(meals_by_ingredient); mcp.tool()(random_meal); mcp.tool()(meal_details)
except ImportError:
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer("meals")
    mcp.add_tool(search_meals_by_name); mcp.add_tool(meals_by_ingredient); mcp.add_tool(random_meal); mcp.add_tool(meal_details)
if __name__ == "__main__":
    import asyncio
    if hasattr(mcp, "run_stdio_async"): asyncio.run(mcp.run_stdio_async())
    else: mcp.run(transport="stdio")