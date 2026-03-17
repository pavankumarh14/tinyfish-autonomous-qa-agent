# graph/qa_graph.py - LangGraph QA Agent Graph (Agent Architect Role)
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from agents.tools import run_tinyfish_qa, check_url_health, save_qa_result, send_slack_alert
from graph.state import QAState
from config import settings
from datetime import datetime
from db.database import get_db

# ----- LLM Setup (Google Gemini - FREE) -----
llm = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL,
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0,
    streaming=False
)

# ----- Tools list -----
tools = [run_tinyfish_qa, check_url_health, save_qa_result, send_slack_alert]

# ----- System Prompt -----
SYSTEM_PROMPT = """You are an Autonomous Web QA Agent for production monitoring.
Your job is to:
1. Check if the given URL is accessible using check_url_health
2. Run a detailed QA test using run_tinyfish_qa with the provided goal
3. Analyze the result and determine if it PASSED or FAILED
4. Save the result to the database using save_qa_result
5. If status is FAILED and severity is HIGH or MEDIUM, send a Slack alert using send_slack_alert
Always be systematic. Report step by step what you are doing.
For severity assessment: HIGH = critical feature broken, MEDIUM = degraded functionality, LOW = minor issues."""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# ----- Create Agent -----
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=False,
    handle_parsing_errors=True,
    max_iterations=10,
    return_intermediate_steps=True
)

# ----- LangGraph Node Functions -----
def run_qa_agent(state: QAState) -> QAState:
    """Main agent node that runs the QA workflow"""
    url = state["url"]
    goal = state["goal"]

    query = f"""Run QA test for URL: {url}
Goal: {goal}
Current time: {datetime.now().isoformat()}"""

    try:
        result = agent_executor.invoke({"input": query})
        output = result.get("output", "No output") if result else "No output"
        # Extract intermediate steps
        steps_taken = []
        if result and "intermediate_steps" in result:
            for action, observation in result["intermediate_steps"]:
                steps_taken.append(f"Tool: {action.tool} - {action.tool_input}")
                if observation:
                    steps_taken.append(f"Result: {str(observation)[:200]}")

        # Parse status from output
        output_lower = output.lower()
        output_upper = output.upper()
        
        # Check for explicit status markers first
        if "PASSED" in output_upper or "PASS" in output_upper:
            status = "PASSED"
            severity = "LOW"
        elif "FAILED" in output_upper or "FAIL" in output_upper:
            status = "FAILED"
            if "CRITICAL" in output_upper or "HIGH" in output_upper:
                severity = "HIGH"
            elif "MEDIUM" in output_upper:
                severity = "MEDIUM"
            else:
                severity = "HIGH"
        else:
            # No explicit status found - analyze output content
            error_keywords = ['error', 'unable to', 'could not', 'timeout', 'exception', 
                            'not found', 'unreachable', 'broken', 'failed', 'failure',
                            'does not', "doesn't", 'invalid', 'unauthorized', 'forbidden']
            
            success_keywords = ['success', 'completed', 'working', 'functional', 
                              'accessible', 'verified', 'confirmed', 'found', 'visible',
                              'loaded', 'available', 'passed']
            
            has_error = any(keyword in output_lower for keyword in error_keywords)
            has_success = any(keyword in output_lower for keyword in success_keywords)
            
            if has_error and not has_success:
                status = "FAILED"
                severity = "HIGH"
            elif has_success or (output and len(output) > 20):
                # Output seems positive and substantial
                status = "PASSED"
                severity = "LOW"
            else:
                # Ambiguous output - check for negative indicators
                negative_indicators = ['not ', 'no ', 'unable', 'cannot', "can't"]
                if any(ind in output_lower for ind in negative_indicators):
                    status = "FAILED"
                    severity = "MEDIUM"
                else:
                    status = "PASSED"  # Default to passed if output exists
                    severity = "LOW"

        state["status"] = status
        state["severity"] = severity
        state["agent_output"] = output
        state["error"] = None
        state["started_at"] = datetime.now().isoformat()
        state["completed_at"] = datetime.now().isoformat()
        state["steps_taken"] = steps_taken if steps_taken else ["Agent completed QA workflow"]
        state["steps"] = steps_taken if steps_taken else ["Agent completed QA workflow"]


    except Exception as e:
        state["status"] = "ERROR"
        state["severity"] = "HIGH"
        state["agent_output"] = ""
        state["error"] = str(e)
        state["started_at"] = datetime.now().isoformat()
        state["completed_at"] = datetime.now().isoformat()
        state["steps_taken"] = []
        state["steps"] = []

    return state


def should_alert(state: QAState) -> str:
    """Decide whether to send alert based on status"""
    status = state.get("status", "")
    severity = state.get("severity", "LOW")
    if status in ["FAILED", "ERROR"] and severity in ["HIGH", "MEDIUM"]:
        return "alert"
    return "done"


def send_alert_node(state: QAState) -> QAState:
    """Send Slack alert for failed tests"""
    try:
        send_slack_alert.invoke({
            "message": f"QA FAILED for {state['url']}: {state.get('agent_output', '')[:500]}",
            "severity": state.get("severity", "HIGH")
        })
    except Exception as e:
        state["error"] = f"Alert failed: {str(e)}"
    return state

def save_results_node(state: QAState) -> QAState:
    """Save results to database"""
    try:
        from datetime import datetime
        db = next(get_db())
        import json
        
        # Calculate duration if timestamps exist
        duration = 0
        if state.get("started_at") and state.get("completed_at"):
            try:
                start = datetime.fromisoformat(state["started_at"])
                end = datetime.fromisoformat(state["completed_at"])
                duration = (end - start).total_seconds()
            except:
                pass
        
        # Ensure steps is a string
        steps = state.get("steps_taken", [])
        if isinstance(steps, list):
            steps = json.dumps(steps)
        
        create_qa_result(
            db=db,
            workflow_name=state.get("workflow_name", ""),
            url=state["url"],
            goal=state["goal"],
            status=state.get("status", "UNKNOWN"),
            agent_output=state.get("agent_output", ""),
            steps=steps,
            duration_seconds=duration,
            workflow_id=state.get("workflow_id", "")
        )
    except Exception as e:
        state["error"] = f"DB save failed: {str(e)}"
    
    return state



# ----- Build LangGraph -----
def build_qa_graph():
    workflow = StateGraph(QAState)

    # Add nodes
    workflow.add_node("qa_agent", run_qa_agent)
    workflow.add_node("save_results", save_results_node)
    workflow.add_node("send_alert", send_alert_node)

    # Set entry point
    workflow.set_entry_point("qa_agent")
    
    # Always save results after agent runs
    workflow.add_edge("qa_agent", "save_results")

    # Add conditional edges from save to alert
    workflow.add_conditional_edges(
        "save_results",
        should_alert,
        {
            "alert": "send_alert",
            "done": END
        }
    )

    # Alert always leads to END
    workflow.add_edge("send_alert", END)

    return workflow.compile()


qa_graph = build_qa_graph()
