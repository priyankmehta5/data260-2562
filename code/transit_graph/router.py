import os

from transit_graph.state import AgentState


def router_logic(state: AgentState) -> str:
    turn_ceiling = int(os.getenv("TURN_CEILING", "10"))

    if state["turn_count"] > turn_ceiling:
        return "end"

    if state["task"] == "planner":
        return "planner"

    if state["task"] == "reviewer":
        return "reviewer"

    return "end"