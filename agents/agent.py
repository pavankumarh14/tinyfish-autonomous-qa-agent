# agents/agent.py - Agent Runner (Agent Architect Role)
# High-level interface to run QA workflows via LangGraph

from graph.qa_graph import qa_graph
from graph.state import QAState
from config import WORKFLOWS
from datetime import datetime
from typing import Optional


def run_qa_workflow(
    workflow_name: str,
    url: str,
    goal: str,
    workflow_id: Optional[str] = None
) -> dict:
    """
    Main entry point to run a QA workflow.
    Accepts a workflow name, target URL, and goal description.
    Returns the final QAState as a dict.
    """
    initial_state: QAState = {
        "workflow_name": workflow_name,
        "workflow_id": workflow_id or "",
        "url": url,
        "goal": goal,
        "status": "PENDING",
        "agent_output": "",
        "steps": [],
        "intermediate_steps": [],
        "error": None,
        "started_at": "",
        "completed_at": "",
        "duration_seconds": 0.0
    }

    final_state = qa_graph.invoke(initial_state)
    return final_state


def run_workflow_by_id(workflow_id: str) -> dict:
    """
    Look up a workflow from config.py WORKFLOWS list by ID and run it.
    """
    workflow = next(
        (w for w in WORKFLOWS if w["id"] == workflow_id), None
    )

    if not workflow:
        return {
            "status": "ERROR",
            "error": f"Workflow '{workflow_id}' not found in config",
            "steps": []
        }

    return run_qa_workflow(
        workflow_name=workflow["name"],
        url=workflow["url"],
        goal=workflow["goal"].strip(),
        workflow_id=workflow["id"]
    )


def run_all_workflows() -> list:
    """
    Run all defined workflows from config and return results.
    Used for scheduled/batch monitoring runs.
    """
    results = []
    for workflow in WORKFLOWS:
        print(f"Running workflow: {workflow['name']}")
        result = run_qa_workflow(
            workflow_name=workflow["name"],
            url=workflow["url"],
            goal=workflow["goal"].strip(),
            workflow_id=workflow["id"]
        )
        results.append({
            "id": workflow["id"],
            "name": workflow["name"],
            "category": workflow.get("category", ""),
            "status": result.get("status"),
            "agent_output": result.get("agent_output", ""),
            "duration_seconds": result.get("duration_seconds", 0),
            "error": result.get("error")
        })
    return results
