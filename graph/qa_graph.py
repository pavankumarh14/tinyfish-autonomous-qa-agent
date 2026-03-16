# graph/qa_graph.py - LangGraph QA Agent Graph (Agent Architect Role)
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from agents.tools import run_tinyfish_qa, check_url_health, save_qa_result, send_slack_alert
from graph.state import QAState
from config import settings
from datetime import datetime
import json

# ---- LLM Setup (Google Gemini - FREE) ----
llm = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL,
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0,
    streaming=True
)

# ---- Tools list ----
tools = [run_tinyfish_qa, check_url_health, save_qa_result, send_slack_alert]

# ---- System Prompt ----
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
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# ---- Agent ----
agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    return_intermediate_steps=True,
    max_iterations=10
)


# ---- Graph Nodes ----
def validate_input(state: QAState) -> QAState:
    """Node 1: Validate input URL and workflow config"""
    state["status"] = "RUNNING"
    state["started_at"] = datetime.utcnow().isoformat()
    state["steps"].append(f"Validating input: {state['url']}")

    if not state["url"].startswith(("http://", "https://")):
        state["status"] = "FAILED"
        state["error"] = "Invalid URL format"
    return state


def run_agent(state: QAState) -> QAState:
    """Node 2: Run the LangChain Agent with TinyFish tools"""
    if state.get("status") == "FAILED":
        return state

    state["steps"].append("Starting LangGraph agent with TinyFish tools...")

    try:
        user_message = f"""
        Run a complete QA check:
        - Workflow: {state['workflow_name']}
        - URL: {state['url']}
        - Goal: {state['goal']}

        First check if URL is reachable, then run the full QA test,
        save the result, and alert if failed.
        """

        result = agent_executor.invoke({
            "input": user_message,
            "chat_history": []
        })

        state["agent_output"] = result.get("output", "")
        state["intermediate_steps"] = [
            {"tool": step[0].tool, "output": str(step[1])}
            for step in result.get("intermediate_steps", [])
        ]

        # Parse status from output
        output_lower = state["agent_output"].lower()
        if "pass" in output_lower or "success" in output_lower:
            state["status"] = "PASSED"
        elif "fail" in output_lower or "error" in output_lower:
            state["status"] = "FAILED"
        else:
            state["status"] = "COMPLETED"

    except Exception as e:
        state["status"] = "ERROR"
        state["error"] = str(e)
        state["agent_output"] = f"Agent execution error: {str(e)}"

    return state


def finalize(state: QAState) -> QAState:
    """Node 3: Finalize the run - mark complete and record duration"""
    state["completed_at"] = datetime.utcnow().isoformat()
    if state.get("started_at"):
        try:
            start = datetime.fromisoformat(state["started_at"])
            end = datetime.fromisoformat(state["completed_at"])
            state["duration_seconds"] = (end - start).total_seconds()
        except Exception:
            state["duration_seconds"] = 0.0

    state["steps"].append(f"QA workflow completed with status: {state['status']}")
    return state


def should_continue(state: QAState) -> str:
    """Conditional edge: if input validation failed, skip to finalize"""
    if state.get("status") == "FAILED" and state.get("error"):
        return "finalize"
    return "run_agent"


# ---- Build LangGraph ----
workflow = StateGraph(QAState)

workflow.add_node("validate_input", validate_input)
workflow.add_node("run_agent", run_agent)
workflow.add_node("finalize", finalize)

workflow.set_entry_point("validate_input")
workflow.add_conditional_edges(
    "validate_input",
    should_continue,
    {
        "run_agent": "run_agent",
        "finalize": "finalize"
    }
)
workflow.add_edge("run_agent", "finalize")
workflow.add_edge("finalize", END)

qa_graph = workflow.compile()
