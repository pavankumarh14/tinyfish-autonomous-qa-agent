# graph/state.py
# LangGraph State Schema - shared state between all nodes

from typing import TypedDict, Optional, List

class QAState(TypedDict):
    # Input
    workflow_id: str
    workflow_name: str
    url: str
    goal: str

    # After TinyFish execution
    tinyfish_status: str        # COMPLETED or FAILED
    tinyfish_result: dict       # raw result JSON
    steps_taken: List[str]      # progress steps
    duration_seconds: int

    # After LLM analysis
    status: str                 # PASS or FAIL
    message: str                # short summary
    analysis: str               # detailed analysis
    severity: str               # LOW / MEDIUM / HIGH
    recommendation: str         # what to do next

    # Alert
    alert_sent: bool
    error: Optional[str]
