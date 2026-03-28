# app.py - Streamlit UI (Experience Designer Role)
import streamlit as st
import asyncio
from datetime import datetime
from graph.qa_graph import qa_graph
from db.database import get_all_results, get_db
from graph.state import QAState
from config import settings
import threading
import queue
import time
from agents.tools import streaming_url_queue



# ---- Page Config ----
st.set_page_config(
    page_title="Autonomous Web QA Agent",
    page_icon="🤖",
    layout="wide"
)

# ---- Header ----
st.title("🤖 Autonomous Web QA Agent")
st.caption("Powered by TinyFish + LangGraph + LangChain | Production Monitoring")
st.divider()

# ---- Sidebar: Configuration ----
st.sidebar.header("⚙️ Configuration")
st.sidebar.info(
    "This agent uses TinyFish to browse your web app with LIVE streaming, "
    "LangGraph to orchestrate the QA workflow, and "
    "LangChain tools to check, test, and alert."
)

with st.sidebar:
    st.subheader("Architecture Flow")
    st.markdown("""
    ```
    [Input URL + Goal]
          |
    [validate_input]
          |
    [run_agent] <-- LangGraph Node
     |    |    |
     |    |    |
  check  run  save
  health  QA  result
  (tool) (TinyFish) (DB)
          |
       [finalize]
          |
    [Slack Alert?]
    ```
    """)

    st.divider()
    st.subheader("🤖 LLM Provider")
    
    # Display current LLM provider with icon
    provider = settings.LLM_PROVIDER
    provider_icons = {
        "google": "🔮 Google Gemini",
        "openai": "🤖 OpenAI GPT",
        "groq": "⚡ Groq",
        "ollama": "🏠 Ollama (Local)"
    }
    provider_display = provider_icons.get(provider, f"🤖 {provider.title()}")
    
    st.success(f"**Active:** {provider_display}")
    
    # Show model name
    if provider == "google":
        st.caption(f"Model: `{settings.GEMINI_MODEL}`")
    elif provider == "openai":
        st.caption(f"Model: `{settings.OPENAI_MODEL}`")
    elif provider == "groq":
        st.caption(f"Model: `{settings.GROQ_MODEL}`")
    elif provider == "ollama":
        st.caption(f"Model: `{settings.OLLAMA_MODEL}`")
    
    st.info("💡 Configure in `.env` file with `LLM_PROVIDER`")


# ---- Tabs ----
tab1, tab2, tab3 = st.tabs(["▶️ Run QA Check", "📊 QA History", "📖 About"])

# ---- Tab 1: Run QA ----
with tab1:
    st.subheader("Configure QA Workflow")

    col1, col2 = st.columns(2)

    with col1:
        workflow_name = st.text_input(
            "Workflow Name",
            value="Login Flow Check",
            help="A descriptive name for this QA check"
        )
        url = st.text_input(
            "Target URL",
            value="https://example.com",
            help="The production URL to test"
        )

    with col2:
        schedule = st.selectbox(
            "Schedule",
            ["manual", "every_15_min", "every_30_min", "hourly", "daily"],
            help="How often to run this check (for demo, runs manually)"
        )
        severity_threshold = st.selectbox(
            "Alert Severity Threshold",
            ["HIGH", "MEDIUM", "LOW"],
            index=1
        )

    goal = st.text_area(
        "QA Goal / Test Scenario",
        value="Navigate to the homepage. Verify the page loads correctly, check if the main navigation is visible, and confirm there are no broken elements or error messages.",
        height=120,
        help="Describe what TinyFish agent should verify on the page"
    )

    st.markdown("---")

    if st.button("🚀 Run QA Agent", type="primary", use_container_width=True):
        if not url or not goal:
            st.error("Please provide both URL and QA Goal.")
        else:
            # Clear any previous streaming URL from queue
            while not streaming_url_queue.empty():
                try:
                    streaming_url_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Create placeholder for live preview (will show as soon as URL available)
            live_preview_placeholder = st.empty()
            streaming_url_displayed = False
            
            # Container for final results
            result_container = {}
            
            def run_qa_thread():
                """Run QA in background thread"""
                initial_state: QAState = {
                    "url": url,
                    "workflow_name": workflow_name,
                    "goal": goal,
                    "schedule": schedule,
                    "status": "PENDING",
                    "steps": [],
                    "agent_output": "",
                    "error": None,
                    "started_at": datetime.now().isoformat(),
                    "completed_at": None
                }
                
                try:
                    result = qa_graph.invoke(initial_state)
                    result_container["result"] = result
                    result_container["success"] = True
                except Exception as e:
                    result_container["error"] = str(e)
                    result_container["success"] = False
            
            # Start QA in background thread
            qa_thread = threading.Thread(target=run_qa_thread)
            qa_thread.start()
            
            # Poll for streaming URL while thread runs
            with st.spinner("Running QA Agent... This may take 30-60 seconds."):
                status_text = st.empty()
                
                while qa_thread.is_alive():
                    # Check for streaming URL in queue (non-blocking)
                    try:
                        url_data = streaming_url_queue.get(timeout=0.1)
                        if url_data.get("streaming_url") and not streaming_url_displayed:
                            # 🎉 SHOW LIVE PREVIEW BUTTON IMMEDIATELY!
                            with live_preview_placeholder.container():
                                st.markdown("---")
                                st.markdown("### 🔴 Live Browser Preview")
                                st.caption("Watch the automation execute in real-time:")
                                st.link_button(
                                    "🔗 Open Live Preview", 
                                    url_data["streaming_url"], 
                                    type="primary"
                                )
                                st.caption(f"Run ID: `{url_data.get('run_id', 'N/A')}`")
                                streaming_url_displayed = True
                    except queue.Empty:
                        pass
                    
                    time.sleep(0.05)  # Small delay to prevent CPU spinning
            
            # Wait for thread to complete
            qa_thread.join()
            
            # Clear the spinner and live preview placeholder
            status_text.empty()
            
            # Handle errors
            if not result_container.get("success"):
                st.error(f"Agent error: {result_container.get('error', 'Unknown error')}")
            else:
                result = result_container["result"]
                
                # Display final results
                st.markdown("### Results")

                status = result.get("status", "UNKNOWN")
                if status in ["COMPLETED", "PASSED"]:
                    st.success(f"✅ Status: {status}")
                elif status == "FAILED":
                    st.error(f"❌ Status: {status}")
                elif status == "ERROR":
                    st.error(f"🚨 Status: {status}")
                else:
                    st.warning(f"⚠️ Status: {status}")

                col_a, col_b = st.columns(2)
                with col_a:
                    st.metric("Started At", result.get("started_at", "N/A"))
                with col_b:
                    st.metric("Completed At", result.get("completed_at", "N/A"))

                if result.get("error"):
                    st.error(f"Error: {result['error']}")

                st.markdown("#### Agent Output")
                output_text = result.get("agent_output") or result.get("result", "No output")
                st.info(output_text)
                
                st.markdown("#### Steps Taken")
                steps_list = result.get("steps_taken") or result.get("steps", [])
                if steps_list:
                    for i, step in enumerate(steps_list, 1):
                        st.markdown(f"{i}. {step}")
                else:
                    st.markdown("*No steps recorded*")
                
                # Keep showing the streaming URL if available
                streaming_url = result.get("streaming_url")
                if streaming_url and not streaming_url_displayed:
                    st.markdown("---")
                    st.markdown("### 🔴 Live Browser Preview")
                    st.caption("Watch the automation execute in real-time:")
                    st.link_button("🔗 Open Live Preview", streaming_url, type="primary")
                    st.caption(f"Run ID: `{result.get('run_id', 'N/A')}`")


# ---- Tab 2: History ----
with tab2:
    st.subheader("QA Run History")

    if st.button("🔄 Refresh"):
        st.rerun()

    try:
        db = next(get_db())
        results = get_all_results(db)

        if not results:
            st.info("No QA runs yet. Run your first check in the 'Run QA Check' tab.")
        else:
            for r in reversed(results):
                # Handle status icon
                status_icon = "✅" if r.status in ['COMPLETED', 'PASSED'] else "❌" if r.status == 'FAILED' else "⚠️"
                
                with st.expander(
                    f"{status_icon} "
                    f"{getattr(r, 'workflow_name', 'Unnamed')} | {getattr(r, 'url', 'No URL')} | {r.created_at}"
                ):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Status", r.status)
                    col2.metric("URL", r.url[:30] + "..." if len(r.url) > 30 else r.url)
                    col3.metric("Duration", f"{r.duration_seconds:.1f}s" if r.duration_seconds else "N/A")

                    # Safely get agent_output
                    agent_output = getattr(r, 'agent_output', None) or getattr(r, 'result', None)
                    if agent_output:
                        st.markdown("**Agent Output:**")
                        st.info(agent_output)

                    # Safely get and parse steps
                    steps_data = getattr(r, 'steps', None) or getattr(r, 'steps_taken', None)
                    if steps_data:
                        st.markdown("**Steps:**")
                        import json
                        try:
                            if isinstance(steps_data, str):
                                steps = json.loads(steps_data)
                            else:
                                steps = steps_data
                            if isinstance(steps, list):
                                for i, step in enumerate(steps, 1):
                                    st.markdown(f"{i}. {step}")
                            else:
                                st.markdown(f"1. {steps}")
                        except (json.JSONDecodeError, TypeError):
                            # If JSON parsing fails, show as string
                            st.markdown(f"1. {str(steps_data)[:200]}")

    except Exception as e:
        st.error(f"Could not load history: {str(e)}")
        st.info("Try running a test first to initialize the database.")


# ---- Tab 3: About ----
with tab3:
    st.subheader("About This Project")
    st.markdown("""
    ## Autonomous Web QA Agent for Production Monitoring

    ### Problem
    Production web apps break silently. Manual QA is slow and doesn't run 24/7.

    ### Solution
    An autonomous agent that uses **TinyFish** to browse your production app,
    **LangGraph** to orchestrate decision-making, and **LangChain** tools to
    check, test, store results, and alert your team.

    ### Tech Stack
    | Component | Technology |
    |-----------|------------|
    | Web Agent | TinyFish API |
    | AI Orchestration | LangGraph |
    | LLM + Tools | LangChain + OpenAI GPT-4 |
    | UI | Streamlit |
    | Database | SQLite (SQLAlchemy) |
    | Alerts | Slack Webhooks |

    ### Architecture
    ```
    User (Streamlit UI)
         |
    LangGraph QA Graph
    ├── Node 1: validate_input
    ├── Node 2: run_agent (LangChain AgentExecutor)
    │   ├── Tool: check_url_health
    │   ├── Tool: run_tinyfish_qa  <-- TinyFish Web Agent
    │   ├── Tool: save_qa_result   <-- SQLite DB
    │   └── Tool: send_slack_alert <-- Slack
    └── Node 3: finalize
    ```

    ### Team Roles
    - **Agent Architect**: Designed LangGraph flow, nodes, edges, system prompts
    - **Tool Builder**: Built @tool functions - TinyFish, health check, DB, Slack
    - **Experience Designer**: Built Streamlit UI with streaming results & history

    ### Hackathon
    TinyFish Hackathon 2026 - Build an Autonomous Web Agent
    """)

# ---- Footer ----
st.divider()
st.caption("TinyFish Hackathon 2026 | Autonomous Web QA Agent | pavankumarh14")
