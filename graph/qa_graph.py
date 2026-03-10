# graph/qa_graph.py - LangGraph QA Agent Graph (Agent Architect Role)
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from agents.tools import run_tinyfish_qa, check_url_health, save_qa_result, send_slack_alert
from graph.state import QAState
from config import settings
from datetime import datetime
import json

# ---- LLM Setup ----
llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
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
agent = create_openai_tools_agent(llm, tools, prompt)
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
    """Node 2: Run the LangChain agent with TinyFish tools"""
    if state.get("status") == "FAILED":
        return state

    try:
        user_input = f"""Run QA check for the following:
- URL: {state['url']}
- Workflow: {state['workflow_name']}
- Goal: {state['goal']}
- Schedule: {state['schedule']}

Please check health, run QA, save result, and alert if needed."""

        result = agent_executor.invoke({
            "input": user_input,
            "chat_history": []
        })

        state["agent_output"] = result.get("output", "")
        state["steps"].extend([
            step[0].log for step in result.get("intermediate_steps", [])
            if hasattr(step[0], "log")
        ])
        state["status"] = "COMPLETED"

    except Exception as e:
        state["status"] = "FAILED"
        state["error"] = str(e)

    return state


def finalize(state: QAState) -> QAState:
    """Node 3: Finalize and prepare summary"""
    state["completed_at"] = datetime.utcnow().isoformat()
    if state["status"] == "COMPLETED":
        state["steps"].append("QA workflow completed successfully.")
    else:
        state["steps"].append(f"QA workflow ended with status: {state['status']}")
    return state


def should_continue(state: QAState) -> str:
    """Edge condition: decide next node"""
    if state.get("status") == "FAILED" and state.get("error"):
        return "finalize"
    return "run_agent"


# ---- Build Graph ----
def build_qa_graph() -> StateGraph:
    graph = StateGraph(QAState)

    graph.add_node("validate_input", validate_input)
    graph.add_node("run_agent", run_agent)
    graph.add_node("finalize", finalize)

    graph.set_entry_point("validate_input")

    graph.add_conditional_edges(
        "validate_input",
        should_continue,
        {
            "run_agent": "run_agent",
            "finalize": "finalize"
        }
    )

    graph.add_edge("run_agent", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


# Compiled graph instance
qa_graph = build_qa_graph()
