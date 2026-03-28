# agents/tools.py - Tool Builder Role
# All @tool decorated functions used by the LangChain agent
import os
import requests
from datetime import datetime
from langchain_core.tools import tool
from tinyfish import TinyFish, RunStatus, ProgressEvent, CompleteEvent
from config import settings
from db.database import get_db, create_qa_result
import queue
# Global queue for streaming URL communication between tool and UI
streaming_url_queue: queue.Queue = queue.Queue()

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
    Runs an autonomous QA check using TinyFish web agent with LIVE streaming.
    The agent will browse the URL and attempt to complete the specified goal.
    Captures live browser preview URL and real-time progress updates.
    Returns the run status, steps taken, result JSON, and streaming URL.
    """
    result = {
        "url": url,
        "goal": goal,
        "status": "PENDING",
        "steps": [],
        "result_json": {},
        "error": None,
        "streaming_url": None,  # Live browser preview URL
        "run_id": None
    }
    start_time = datetime.now()
    
    try:
        with tinyfish_client.agent.stream(url=url, goal=goal) as stream:
            for event in stream:
                # Capture run ID when started
                if hasattr(event, 'run_id') and not result["run_id"]:
                    result["run_id"] = event.run_id
                
                # Capture streaming URL for live browser preview
                if hasattr(event, 'streaming_url') and event.streaming_url:
                    result["streaming_url"] = event.streaming_url
                    result["steps"].append(f"🔴 LIVE PREVIEW: {event.streaming_url}")
                    
                    # 🆕 SEND TO QUEUE for immediate UI display
                    streaming_url_queue.put({
                        "streaming_url": event.streaming_url,
                        "run_id": result["run_id"],
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Capture progress updates
                if isinstance(event, ProgressEvent):
                    purpose = getattr(event, 'purpose', str(event))
                    result["steps"].append(f"▶️ {purpose}")
                
                # Capture completion
                if isinstance(event, CompleteEvent):
                    if event.status == RunStatus.COMPLETED:
                        result["status"] = "COMPLETED"
                        result["result_json"] = event.result_json or {}
                        result["steps"].append("✅ Task completed successfully")
                    else:
                        result["status"] = "FAILED"
                        error_msg = getattr(event, 'error', None)
                        result["error"] = str(error_msg) if error_msg else "Run failed"
                        result["steps"].append(f"❌ Failed: {result['error']}")
                        
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)
        result["steps"].append(f"🚨 Exception: {str(e)}")

    result["duration_ms"] = round((datetime.now() - start_time).total_seconds() * 1000, 2)
    return result



@tool
def get_live_preview_url(run_id: str) -> dict:
    """
    Get the live browser preview URL for an active TinyFish run.
    Users can watch the automation execute in real-time.
    """
    # Note: This is a helper - the streaming_url is already captured in run_tinyfish_qa
    return {
        "message": "Live preview URL is captured during run_tinyfish_qa execution",
        "note": "Check the 'streaming_url' field in the QA results for the live browser link"
    }



@tool
def save_qa_result(url: str, goal: str, status: str, agent_output: str, steps: str, duration_seconds: float, workflow_name: str = "") -> dict:
    """
    Saves QA result to the PostgreSQL database.
    Call this after run_tinyfish_qa to persist results.
    """
    try:
        import json
        # Ensure agent_output is a string (handle dict/list inputs)
        if isinstance(agent_output, (dict, list)):
            agent_output = json.dumps(agent_output)
        elif not isinstance(agent_output, str):
            agent_output = str(agent_output)
        
        # Ensure steps is a string
        if isinstance(steps, list):
            steps = json.dumps(steps)
        elif not isinstance(steps, str):
            steps = str(steps)

        db = next(get_db())
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
