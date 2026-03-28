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

# ============================================================
# NEW: SCHEDULER IMPORTS AND SETUP
# ============================================================
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import atexit

# Initialize background scheduler
scheduler = BackgroundScheduler()
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# Session state for scheduled jobs
if "scheduled_jobs" not in st.session_state:
    st.session_state["scheduled_jobs"] = {}

# NEW: Helper function to run scheduled QA
def run_scheduled_qa(workflow_name, url, goal, schedule_name):
    """Function to run QA on a schedule"""
    print(f"[SCHEDULER] Running {workflow_name} ({schedule_name}) at {datetime.now()}")
    
    initial_state = {
        "url": url,
        "workflow_name": workflow_name,
        "goal": goal,
        "schedule": schedule_name,
        "status": "PENDING",
        "steps": [],
        "agent_output": "",
        "error": None,
        "started_at": datetime.now().isoformat(),
        "completed_at": None
    }
    
    try:
        result = qa_graph.invoke(initial_state)
        print(f"[SCHEDULER] Completed {workflow_name}: {result.get('status', 'UNKNOWN')}")
    except Exception as e:
        print(f"[SCHEDULER] Error running {workflow_name}: {e}")

# NEW: Convert schedule to minutes
def get_interval_minutes(schedule):
    intervals = {
        "every_1_min": 1,
        "every_5_min": 5,
        "every_15_min": 15,
        "every_30_min": 30,
        "hourly": 60,
        "daily": 1440,
    }
    return intervals.get(schedule, None)

# NEW: Generate unique job ID
def generate_job_id(workflow_name, url):
    import hashlib
    unique_string = f"{workflow_name}_{url}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return hashlib.md5(unique_string.encode()).hexdigest()[:12]
# ============================================================


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
    
    provider = settings.LLM_PROVIDER
    provider_icons = {
        "google": "🔮 Google Gemini",
        "openai": "🤖 OpenAI GPT",
        "groq": "⚡ Groq",
        "ollama": "🏠 Ollama (Local)"
    }
    provider_display = provider_icons.get(provider, f"🤖 {provider.title()}")
    
    st.success(f"**Active:** {provider_display}")
    
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
        # ============================================================
        # NEW: Added every_1_min and every_5_min options
        # ============================================================
        schedule = st.selectbox(
            "Schedule",
            ["manual", "every_1_min", "every_5_min", "every_15_min", "every_30_min", "hourly", "daily"],
            help="How often to run this check. Use 'every_1_min' for testing only!"
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

    # ============================================================
    # NEW: Stop Schedule Button (only shown when schedule is active)
    # ============================================================
    
    # Check if there's an active schedule for this workflow
    current_job_id = None
    is_currently_scheduled = False
    
    for job_id, job_info in st.session_state["scheduled_jobs"].items():
        if job_info["workflow_name"] == workflow_name and job_info["url"] == url:
            current_job_id = job_id
            is_currently_scheduled = True
            break
    
    # Show Stop button ONLY if there's an active schedule
    if is_currently_scheduled:
        st.warning(f"⏰ This workflow is currently scheduled: **{st.session_state['scheduled_jobs'][current_job_id]['schedule']}**")
        
        col_run, col_stop = st.columns([3, 1])
        
        with col_run:
            run_clicked = st.button("🚀 Run QA Agent Now", type="primary", use_container_width=True)
        
        with col_stop:
            if st.button("🛑 Stop Schedule", type="secondary", use_container_width=True):
                try:
                    scheduler.remove_job(current_job_id)
                    del st.session_state["scheduled_jobs"][current_job_id]
                    st.success("✅ Schedule stopped!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error stopping schedule: {e}")
        
        if run_clicked:
            execute_qa = True
        else:
            execute_qa = False
            
    else:
        # Normal Run button when no schedule is active
        if st.button("🚀 Run QA Agent", type="primary", use_container_width=True):
            execute_qa = True
        else:
            execute_qa = False
    
    # ============================================================
    # Execute QA logic
    # ============================================================
    if execute_qa:
        if not url or not goal:
            st.error("Please provide both URL and QA Goal.")
        else:
            # Clear any previous streaming URL from queue
            while not streaming_url_queue.empty():
                try:
                    streaming_url_queue.get_nowait()
                except queue.Empty:
                    break
            
            # Create placeholder for live preview
            live_preview_placeholder = st.empty()
            streaming_url_displayed = False
            
            # Container for final results
            result_container = {}
            
            def run_qa_thread():
                """Run QA in background thread"""
                initial_state = {
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
                    try:
                        url_data = streaming_url_queue.get(timeout=0.1)
                        if url_data.get("streaming_url") and not streaming_url_displayed:
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
                    
                    time.sleep(0.05)
            
            qa_thread.join()
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
                
                streaming_url = result.get("streaming_url")
                if streaming_url and not streaming_url_displayed:
                    st.markdown("---")
                    st.markdown("### 🔴 Live Browser Preview")
                    st.caption("Watch the automation execute in real-time:")
                    st.link_button("🔗 Open Live Preview", streaming_url, type="primary")
                    st.caption(f"Run ID: `{result.get('run_id', 'N/A')}`")
                
                # ============================================================
                # NEW: Setup recurring schedule if selected
                # ============================================================
                if schedule != "manual" and not is_currently_scheduled:
                    interval_minutes = get_interval_minutes(schedule)
                    if interval_minutes:
                        job_id = generate_job_id(workflow_name, url)
                        
                        scheduler.add_job(
                            func=run_scheduled_qa,
                            trigger=IntervalTrigger(minutes=interval_minutes),
                            id=job_id,
                            args=[workflow_name, url, goal, schedule],
                            replace_existing=True
                        )
                        
                        st.session_state["scheduled_jobs"][job_id] = {
                            "workflow_name": workflow_name,
                            "url": url,
                            "schedule": schedule,
                            "created_at": datetime.now().isoformat()
                        }
                        
                        st.success(f"✅ Scheduled to run **{schedule}** (every {interval_minutes} min)")
                        if schedule == "every_1_min":
                            st.warning("⚠️ 1-minute schedule is for testing only!")
                        st.info("🔄 The schedule will run in the background. You can close this page.")
                        st.rerun()


    # ============================================================
    # NEW: Active Schedules Section
    # ============================================================
    st.markdown("---")
    st.subheader("⏰ Active Scheduled Jobs")
    
    if not st.session_state["scheduled_jobs"]:
        st.info("No scheduled jobs. Select a schedule (every_1_min, hourly, etc.) and run to create one.")
    else:
        for job_id, job_info in list(st.session_state["scheduled_jobs"].items()):
            col_s1, col_s2, col_s3, col_s4 = st.columns([2, 2, 2, 1])
            
            with col_s1:
                st.markdown(f"**{job_info['workflow_name']}**")
                st.caption(f"{job_info['url'][:40]}...")
            
            with col_s2:
                st.markdown(f"⏱️ **{job_info['schedule']}**")
            
            with col_s3:
                # Get next run time from scheduler
                try:
                    job = scheduler.get_job(job_id)
                    if job and job.next_run_time:
                        st.caption(f"Next run: {job.next_run_time.strftime('%H:%M:%S')}")
                    else:
                        st.caption("Status: Running")
                except:
                    st.caption("Status: Unknown")
            
            with col_s4:
                if st.button("🗑️ Remove", key=f"remove_{job_id}"):
                    try:
                        scheduler.remove_job(job_id)
                    except:
                        pass
                    del st.session_state["scheduled_jobs"][job_id]
                    st.rerun()
        
        if st.button("🛑 Stop All Scheduled Jobs", type="primary"):
            for job_id in list(st.session_state["scheduled_jobs"].keys()):
                try:
                    scheduler.remove_job(job_id)
                except:
                    pass
            st.session_state["scheduled_jobs"].clear()
            st.success("All scheduled jobs stopped!")
            st.rerun()


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
                status_icon = "✅" if r.status in ['COMPLETED', 'PASSED'] else "❌" if r.status == 'FAILED' else "⚠️"
                
                with st.expander(
                    f"{status_icon} "
                    f"{getattr(r, 'workflow_name', 'Unnamed')} | {getattr(r, 'url', 'No URL')} | {r.created_at}"
                ):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Status", r.status)
                    col2.metric("URL", r.url[:30] + "..." if len(r.url) > 30 else r.url)
                    col3.metric("Duration", f"{r.duration_seconds:.1f}s" if r.duration_seconds else "N/A")

                    agent_output = getattr(r, 'agent_output', None) or getattr(r, 'result', None)
                    if agent_output:
                        st.markdown("**Agent Output:**")
                        st.info(agent_output)

                    steps_data = getattr(r, 'steps', None) or getattr(r, 'steps_taken', None)
                    if steps_data:
                        st.markdown("**Steps:**")
                        import json
                        try:
                            if isinstance(steps_data, str):
                                steps = json.loads(steps_data)
                            else:
                                steps = steps_data
                            if isinstance(steps, list_
