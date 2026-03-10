# agents/tools.py - Tool Builder Role
# All @tool decorated functions used by the LangChain agent
import os
import requests
from datetime import datetime
from langchain_core.tools import tool
from tinyfish import TinyfishClient
from tinyfish.models import EventType, RunStatus
from config import settings
from db.database import get_db, create_qa_result

# ---- TinyFish Client ----
tinyfish_client = TinyfishClient(api_key=settings.TINYFISH_API_KEY)


@tool
def check_url_health(url: str) -> dict:
    """
    Checks if a URL is accessible and returns HTTP status.
    Use this FIRST before running QA to verify the target is reachable.
    """
    try:
        response = requests.get(url, timeout=10, allow_redirects=True)
        return {
            "url": url,
            "status_code": response.status_code,
            "reachable": response.status_code < 400,
            "response_time_ms": round(response.elapsed.total_seconds() * 1000, 2)
        }
    except requests.exceptions.Timeout:
        return {"url": url, "reachable": False, "error": "Request timed out"}
    except requests.exceptions.ConnectionError:
        return {"url": url, "reachable": False, "error": "Connection failed"}
    except Exception as e:
        return {"url": url, "reachable": False, "error": str(e)}


@tool
def run_tinyfish_qa(url: str, goal: str) -> dict:
    """
    Runs an autonomous QA check using TinyFish web agent.
    The agent will browse the URL and attempt to complete the specified goal.
    Returns the run status, steps taken, and result JSON.
    """
    result = {
        "url": url,
        "goal": goal,
        "status": "PENDING",
        "steps": [],
        "result_json": {},
        "error": None
    }

    start_time = datetime.now()
    try:
        with tinyfish_client.agent.stream(url=url, goal=goal) as stream:
            for event in stream:
                if event.type == EventType.PROGRESS:
                    result["steps"].append(event.purpose)
                if event.type == EventType.COMPLETE:
                    if event.status == RunStatus.COMPLETED:
                        result["status"] = "COMPLETED"
                        result["result_json"] = event.result_json or {}
                    else:
                        result["status"] = "FAILED"
                        result["error"] = "Agent run did not complete"
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    result["duration_seconds"] = (datetime.now() - start_time).seconds
    return result


@tool
def save_qa_result(
    workflow_name: str,
    url: str,
    goal: str,
    status: str,
    agent_output: str,
    steps: list,
    duration_seconds: float = 0.0
) -> dict:
    """
    Saves a QA run result to the SQLite database.
    Always call this after running QA to persist results for history tracking.
    """
    try:
        import json
        db = next(get_db())
        record = create_qa_result(
            db=db,
            workflow_name=workflow_name,
            url=url,
            goal=goal,
            status=status,
            agent_output=agent_output,
            steps=json.dumps(steps),
            duration_seconds=duration_seconds
        )
        return {"saved": True, "record_id": record.id, "message": "Result saved to database"}
    except Exception as e:
        return {"saved": False, "error": str(e)}


@tool
def send_slack_alert(workflow_name: str, status: str, message: str, severity: str) -> dict:
    """
    Sends a Slack alert when a QA workflow fails.
    Only call this when status is FAIL and severity is MEDIUM or HIGH.
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        return {"sent": False, "reason": "No Slack webhook configured"}

    emoji = "🔴" if severity == "HIGH" else "🟡"
    payload = {
        "text": f"{emoji} *AutoQA Alert*\n"
                f"*Workflow:* {workflow_name}\n"
                f"*Status:* {status}\n"
                f"*Severity:* {severity}\n"
                f"*Details:* {message}"
    }

    response = requests.post(webhook_url, json=payload)
    return {
        "sent": response.status_code == 200,
        "status_code": response.status_code
    }
