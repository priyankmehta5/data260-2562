import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

ROOT = Path(__file__).resolve().parents[2]
CODE_DIRECTORY = ROOT / "code"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if str(CODE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(CODE_DIRECTORY))

from src.model_client import OllamaModelClient
from transit_graph.nodes import (
    planner_node,
    reviewer_node,
    supervisor_node
)
from transit_graph.router import router_logic
from transit_graph.state import AgentState


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("supervisor", supervisor_node)
    builder.add_node("planner", planner_node)
    builder.add_node("reviewer", reviewer_node)

    builder.add_edge(START, "supervisor")
    builder.add_edge("planner", "supervisor")
    builder.add_edge("reviewer", "supervisor")

    builder.add_conditional_edges(
        "supervisor",
        router_logic,
        {
            "planner": "planner",
            "reviewer": "reviewer",
            "end": END
        }
    )

    return builder.compile()


def display_update(update: dict[str, Any]) -> None:
    print(json.dumps(update, indent=2, default=str))


def run_workflow(
    title: str,
    content: str,
    email: str,
    model: str,
    temperature: float,
    strict: bool,
    force_review_issue: bool
) -> dict[str, Any]:
    if force_review_issue:
        os.environ["FORCE_REVIEW_ISSUE"] = "1"
    else:
        os.environ.pop("FORCE_REVIEW_ISSUE", None)

    client = OllamaModelClient(
        model=model,
        temperature=temperature
    )

    initial_state: AgentState = {
        "title": title,
        "content": content,
        "email": email,
        "strict": strict,
        "task": "",
        "llm": client,
        "planner_proposal": None,
        "reviewer_feedback": None,
        "turn_count": 0
    }

    graph = build_graph()
    final_state = dict(initial_state)

    print("\n--- LangGraph Stream ---")

    for update in graph.stream(
        initial_state,
        config={"recursion_limit": 30},
        stream_mode="updates"
    ):
        display_update(update)

        for node_update in update.values():
            if isinstance(node_update, dict):
                final_state.update(node_update)

    print("\n--- Final Result ---")
    print(
        json.dumps(
            {
                "planner_proposal": final_state[
                    "planner_proposal"
                ],
                "reviewer_feedback": final_state[
                    "reviewer_feedback"
                ],
                "turn_count": final_state["turn_count"]
            },
            indent=2,
            default=str
        )
    )

    return final_state


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("--title", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument(
        "--email",
        default="priyank.mehta@sjsu.edu"
    )
    parser.add_argument(
        "--model",
        default="qwen3:1.7b"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0
    )
    parser.add_argument(
        "--strict",
        action="store_true"
    )
    parser.add_argument(
        "--force-review-issue",
        action="store_true"
    )

    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()

    run_workflow(
        title=arguments.title,
        content=arguments.content,
        email=arguments.email,
        model=arguments.model,
        temperature=arguments.temperature,
        strict=arguments.strict,
        force_review_issue=arguments.force_review_issue
    )