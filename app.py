# app.py - Streamlit UI (Experience Designer Role)
import streamlit as st
import asyncio
from datetime import datetime
from graph.qa_graph import qa_graph
from db.database import get_all_results, get_db
from graph.state import QAState

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
    "This agent uses TinyFish to browse your web app, "
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
            with st.spinner("Running QA Agent... This may take 30-60 seconds."):
                # Prepare initial state
                initial_state: QAState = {
                    "url": url,
                    "workflow_name": workflow_name,
                    "goal": goal,
                    "schedule": schedule,
                    "status": "PENDING",
                    "steps": [],
                    "agent_output": "",
                    "error": None,
                    "started_at": None,
                    "completed_at": None
                }

                try:
                    result = qa_graph.invoke(initial_state)

                    # Display result
                    st.markdown("### Results")

                    status = result.get("status", "UNKNOWN")
                    if status == "COMPLETED":
                        st.success(f"✅ Status: {status}")
                    elif status == "FAILED":
                        st.error(f"❌ Status: {status}")
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
                    st.info(result.get("agent_output", "No output"))

                    st.markdown("#### Steps Taken")
                    for i, step in enumerate(result.get("steps", []), 1):
                        st.markdown(f"{i}. {step}")

                except Exception as e:
                    st.error(f"Agent error: {str(e)}")

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
                with st.expander(
                    f"{'✅' if r.status == 'COMPLETED' else '❌'} "
                    f"{r.workflow_name} | {r.url} | {r.created_at}"
                ):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Status", r.status)
                    col2.metric("URL", r.url[:30] + "..." if len(r.url) > 30 else r.url)
                    col3.metric("Duration", f"{r.duration_seconds:.1f}s" if r.duration_seconds else "N/A")

                    if r.agent_output:
                        st.markdown("**Agent Output:**")
                        st.info(r.agent_output)

                    if r.steps:
                        st.markdown("**Steps:**")
                        import json
                        steps = json.loads(r.steps) if isinstance(r.steps, str) else r.steps
                        for i, step in enumerate(steps, 1):
                            st.markdown(f"{i}. {step}")

    except Exception as e:
        st.warning(f"Could not load history: {str(e)}")

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
