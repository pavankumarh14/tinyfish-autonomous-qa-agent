# agents/tools.py - Tool Builder Role
# All @tool decorated functions used by the LangChain agent
import os
import requests
from datetime import datetime
from langchain_core.tools import tool
from tinyfish import TinyFish, RunStatus, ProgressEvent, CompleteEvent
from config import settings
from db.database import get_db, create_qa_result

# ---- TinyFish Client ----
tinyfish_client = TinyFish(api_key=settings.TINYFISH_API_KEY)


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
                if isinstance(event, ProgressEvent):
                    result["steps"].append(getattr(event, 'purpose', str(event)))
                if isinstance(event, CompleteEvent):
                    if event.status == RunStatus.COMPLETED:
                        result["status"] = "COMPLETED"
                        result["result_json"] = event.result_json or {}
                    else:
                        result["status"] = "FAILED"
                        error_msg = getattr(event, 'error', None)
                        result["error"] = str(error_msg) if error_msg else "Run failed"
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)

    result["duration_ms"] = round((datetime.now() - start_time).total_seconds() * 1000, 2)
    return result


@tool
def save_qa_result(url: str, goal: str, status: str, agent_output: str, steps: str, duration_seconds: float, workflow_name: str = "") -> dict:
    """
    Saves QA result to the PostgreSQL database.
    Call this after run_tinyfish_qa to persist results.
    """
    try:
        db = next(get_db())
        import json
        qa_result = create_qa_result(
            db=db,
            workflow_name=workflow_name,
            url=url,
            goal=goal,
            status=status,
            agent_output=agent_output,
            steps=steps,
            duration_seconds=duration_seconds
        )
        return {
            "saved": True,
            "id": qa_result.id,
            "url": url,
            "status": status
        }
    except Exception as e:
        return {"saved": False, "error": str(e)}


@tool
def send_slack_alert(message: str, severity: str = "info") -> dict:
    """
    Sends a Slack alert when QA issues are detected.
    Use severity: 'info', 'warning', or 'critical'
    """
    webhook_url = settings.SLACK_WEBHOOK_URL
    if not webhook_url:
        return {"sent": False, "reason": "No Slack webhook configured"}

    emoji = {"info": "\u2139\ufe0f", "warning": "\u26a0\ufe0f", "critical": "\U0001f6a8"}.get(severity, "\u2139\ufe0f")
    payload = {
        "text": f"{emoji} *QA Agent Alert* [{severity.upper()}]\n{message}"
    }
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        return {"sent": response.status_code == 200, "status_code": response.status_code}
    except Exception as e:
        return {"sent": False, "error": str(e)}
