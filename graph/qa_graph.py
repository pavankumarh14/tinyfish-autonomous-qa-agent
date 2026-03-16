# graph/qa_graph.py - LangGraph QA Agent Graph (Agent Architect Role)
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from agents.tools import run_tinyfish_qa, check_url_health, save_qa_result, send_slack_alert
from graph.state import QAState
from config import settings
from datetime import datetime
import json

# ----- LLM Setup (Google Gemini - FREE) -----
llm = ChatGoogleGenerativeAI(
    model=settings.GEMINI_MODEL,
    google_api_key=settings.GOOGLE_API_KEY,
    temperature=0,
    streaming=True
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
For severity assessment: HIGH = critical feature broken, MEDIUM = degraded functionality, LOW = minor issues.

You have access to the following tools:
{tools}

Use the following format:
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

prompt = PromptTemplate.from_template(SYSTEM_PROMPT)

# ----- Create Agent -----
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=10
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
        output = result.get("output", "No output")
        
        # Parse status from output
        output_upper = output.upper()
        if "PASSED" in output_upper:
            status = "PASSED"
            severity = "LOW"
        elif "FAILED" in output_upper:
            status = "FAILED"
            if "CRITICAL" in output_upper or "HIGH" in output_upper:
                severity = "HIGH"
            elif "MEDIUM" in output_upper:
                severity = "MEDIUM"
            else:
                severity = "HIGH"
        else:
            status = "UNKNOWN"
            severity = "MEDIUM"
        
        state["status"] = status
        state["severity"] = severity
        state["result"] = output
        state["error"] = None
        
    except Exception as e:
        state["status"] = "ERROR"
        state["severity"] = "HIGH"
        state["result"] = ""
        state["error"] = str(e)
    
    return state

def should_alert(state: QAState) -> str:
    """Decide whether to send alert based on status"""
    if state.get("status") == "FAILED" and state.get("severity") in ["HIGH", "MEDIUM"]:
        return "alert"
    return "done"

def send_alert_node(state: QAState) -> QAState:
    """Send Slack alert for failed tests"""
    try:
        send_slack_alert.invoke({
            "url": state["url"],
            "status": state["status"],
            "severity": state["severity"],
            "message": state.get("result", "")[:500]
        })
    except Exception as e:
        state["error"] = f"Alert failed: {str(e)}"
    return state

# ----- Build LangGraph -----
def build_qa_graph():
    workflow = StateGraph(QAState)
    
    # Add nodes
    workflow.add_node("qa_agent", run_qa_agent)
    workflow.add_node("send_alert", send_alert_node)
    
    # Set entry point
    workflow.set_entry_point("qa_agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "qa_agent",
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
