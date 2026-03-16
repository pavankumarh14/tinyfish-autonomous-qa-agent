# graph/state.py
# LangGraph State Schema - shared state between all nodes

from typing import TypedDict, Optional, List

class QAState(TypedDict):
    # Input
    workflow_id: str
    workflow_name: str
    url: str
    goal: str
    schedule: str               # manual, hourly, daily, etc.

    # After TinyFish execution
    tinyfish_status: str        # COMPLETED or FAILED
    tinyfish_result: dict       # raw result JSON
    steps_taken: List[str]      # progress steps
    duration_seconds: float     # execution time in seconds

    # After LLM analysis
    status: str                 # PASSED / FAILED / ERROR / UNKNOWN
    message: str                # short summary
    analysis: str               # detailed analysis
    severity: str               # LOW / MEDIUM / HIGH
    recommendation: str         # what to do next
    agent_output: str           # full agent response text
    # Timing
    started_at: Optional[str]   # ISO timestamp
    completed_at: Optional[str] # ISO timestamp


    # Alert
    alert_sent: bool
    error: Optional[str]
