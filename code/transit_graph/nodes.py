import json
import os
from typing import Any

from transit_graph.state import AgentState


def extract_json(value: str) -> dict[str, Any]:
    text = value.strip()
    decoder = json.JSONDecoder()

    for index, character in enumerate(text):
        if character != "{":
            continue

        try:
            result, _ = decoder.raw_decode(text[index:])

            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            continue

    return {}


def planner_node(state: AgentState) -> dict[str, Any]:
    feedback = state.get("reviewer_feedback")
    feedback_text = ""

    if feedback and not feedback.get("approved", False):
        feedback_text = (
            "\nReviewer feedback from the previous attempt:\n"
            f"{feedback.get('feedback', '')}"
        )

    system_prompt = (
        "You are a planner for municipal transit incidents. "
        "Return valid JSON only. The JSON must contain a tags array "
        "with exactly three short tags and a summary with no more than "
        "25 words."
    )

    user_prompt = (
        f"Title: {state['title']}\n"
        f"Content: {state['content']}\n"
        f"Strict mode: {state['strict']}"
        f"{feedback_text}"
    )

    response = state["llm"].complete(
        [
            ("system", system_prompt),
            ("human", user_prompt)
        ]
    )

    proposal = extract_json(str(response.content))

    return {
        "planner_proposal": proposal,
        "reviewer_feedback": None
    }


def reviewer_node(state: AgentState) -> dict[str, Any]:
    proposal = state.get("planner_proposal") or {}

    force_issue = (
        os.getenv("FORCE_REVIEW_ISSUE") == "1"
        and state["turn_count"] <= 2
    )

    if force_issue:
        return {
            "reviewer_feedback": {
                "approved": False,
                "feedback": (
                    "Replace one generic tag with a more specific "
                    "transit-related tag."
                )
            }
        }

    system_prompt = (
        "You are a reviewer for municipal transit incident output. "
        "Check that the result contains exactly three relevant and "
        "distinct tags and a summary of no more than 25 words. "
        "Return valid JSON only with approved as true or false and "
        "feedback as a short string."
    )

    user_prompt = (
        f"Title: {state['title']}\n"
        f"Content: {state['content']}\n"
        f"Planner proposal: {json.dumps(proposal)}"
    )

    response = state["llm"].complete(
        [
            ("system", system_prompt),
            ("human", user_prompt)
        ]
    )

    review = extract_json(str(response.content))
    approved_value = review.get("approved", False)

    approved = (
        approved_value is True
        or str(approved_value).lower() == "true"
    )

    return {
        "reviewer_feedback": {
            "approved": approved,
            "feedback": str(
                review.get(
                    "feedback",
                    "Review did not return usable feedback."
                )
            )
        }
    }

def supervisor_node(state: AgentState) -> dict[str, Any]:
    turn_count = state["turn_count"] + 1
    proposal = state.get("planner_proposal")
    review = state.get("reviewer_feedback")

    if proposal is None:
        task = "planner"
    elif review is None:
        task = "reviewer"
    elif review.get("approved", False):
        task = "end"
    else:
        task = "planner"

    return {
        "task": task,
        "turn_count": turn_count
    }