from typing import Any, TypedDict


class AgentState(TypedDict):
    title: str
    content: str
    email: str
    strict: bool
    task: str
    llm: Any
    planner_proposal: dict[str, Any] | None
    reviewer_feedback: dict[str, Any] | None
    turn_count: int