# Autonomous Web QA Agent for Production Monitoring

> **TinyFish Hackathon 2026** | Build an Autonomous Web Agent

![Python](https://img.shields.io/badge/Python-3.11-blue) ![TinyFish](https://img.shields.io/badge/TinyFish-API-green) ![LangGraph](https://img.shields.io/badge/LangGraph-0.2-orange) ![Streamlit](https://img.shields.io/badge/Streamlit-1.32-red) ![License](https://img.shields.io/badge/License-MIT-yellow)

## Problem Statement

Production web applications break silently. A login form stops working, a checkout button becomes unresponsive, or a key page throws an error — and no one notices until customers complain. Manual QA is too slow and cannot run 24/7.

## Solution

An **Autonomous Web QA Agent** that:
- Uses **TinyFish** to intelligently browse and interact with your production web app like a real user
- Uses **LangGraph** to orchestrate a multi-node QA decision workflow
- Uses **LangChain** tools to check health, run tests, save results, and fire Slack alerts
- Displays everything in a clean **Streamlit** dashboard with real-time results and history

## Architecture Flow

```
+---------------------------+
|   Streamlit UI (app.py)   |
|  [URL] [Goal] [Schedule]  |
+-----------+---------------+
            |
            v
+---------------------------+
|   LangGraph QA Graph      |
|                           |
|  [validate_input] ------> [run_agent] ---------> [finalize]
|       Node 1                 Node 2                Node 3  |
|   Checks URL format      LangChain Agent          Records  |
|   Sets RUNNING status    with 4 @tools          timestamps |
+---------------------------+---------------------------+-----+
                                    |
               +--------------------+--------------------+
               |                    |                    |
               v                    v                    v
    +-------------------+  +------------------+  +-------------------+
    | check_url_health  |  | run_tinyfish_qa  |  |  save_qa_result   |
    | (requests + HTTP) |  | (TinyFish API)   |  | (SQLite via ORM)  |
    +-------------------+  +------------------+  +-------------------+
                                                         |
                                                         v
                                               +-------------------+
                                               | send_slack_alert  |
                                               | (Slack Webhook)   |
                                               +-------------------+
```

## Tech Stack

| Role | Component | Technology |
|------|-----------|------------|
| Agent Architect | AI Orchestration | LangGraph 0.2 |
| Agent Architect | LLM | OpenAI GPT-4o |
| Agent Architect | Prompts | LangChain Prompts |
| Tool Builder | Web Agent | TinyFish API |
| Tool Builder | Health Check | Python requests |
| Tool Builder | Database | SQLite + SQLAlchemy |
| Tool Builder | Alerts | Slack Webhooks |
| Experience Designer | UI | Streamlit 1.32 |
| Experience Designer | Config | Pydantic Settings |

## Project Structure

```
tinyfish-autonomous-qa-agent/
├── app.py                  # Streamlit UI - Experience Designer
├── config.py               # Pydantic settings & env vars
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
├── agents/
│   ├── __init__.py
│   └── tools.py            # @tool functions - Tool Builder Role
├── graph/
│   ├── __init__.py
│   ├── state.py            # QAState TypedDict
│   └── qa_graph.py         # LangGraph nodes & edges - Agent Architect
└── db/
    ├── __init__.py
    └── database.py         # SQLAlchemy ORM models & CRUD
```

## Key Features

- **Autonomous Testing**: TinyFish browses your app and verifies goals without human intervention
- **Smart Orchestration**: LangGraph conditional edges route flow based on validation results
- **Persistent History**: All QA runs stored in SQLite with full step-by-step logs
- **Instant Alerts**: Slack notifications for FAILED checks with HIGH/MEDIUM severity
- **Clean Dashboard**: Streamlit UI with 3 tabs — Run QA, History, About
- **Configurable**: Any URL, any goal, any severity threshold

## Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/pavankumarh14/tinyfish-autonomous-qa-agent.git
cd tinyfish-autonomous-qa-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

### 4. Run the app
```bash
streamlit run app.py
```

## Environment Variables

```env
TINYFISH_API_KEY=your_tinyfish_api_key
OPENAI_API_KEY=your_openai_api_key
SLACK_WEBHOOK_URL=your_slack_webhook_url  # optional
OPENAI_MODEL=gpt-4o
DATABASE_URL=sqlite:///./qa_results.db
```

## How It Works

1. **User opens Streamlit** → enters URL, workflow name, and QA goal
2. **LangGraph `validate_input` node** → validates URL format, sets RUNNING state
3. **LangGraph `run_agent` node** → LangChain AgentExecutor takes over:
   - Calls `check_url_health` → verifies URL is reachable (HTTP 200)
   - Calls `run_tinyfish_qa` → TinyFish agent browses the app, executes the goal
   - Calls `save_qa_result` → stores result in SQLite DB
   - Calls `send_slack_alert` → fires Slack alert if FAILED + HIGH/MEDIUM severity
4. **LangGraph `finalize` node** → records timestamps, prepares summary
5. **Streamlit displays** → status, steps taken, agent output, duration

## Team Roles

### Agent Architect (ML/AI Focus)
- Designed the LangGraph flow (nodes & edges)
- Wrote system prompts for GPT-4o
- Configured LangChain AgentExecutor with tool binding
- Files: `graph/qa_graph.py`, `graph/state.py`

### Tool Builder (Backend/DevOps Focus)
- Built `@tool` decorated functions the agent calls
- Integrated TinyFish API (`run_tinyfish_qa`)
- Implemented SQLite persistence (`save_qa_result`)
- Added Slack alerting (`send_slack_alert`)
- Files: `agents/tools.py`, `db/database.py`, `config.py`

### Experience Designer (Frontend/UI Focus)
- Built Streamlit dashboard with 3 tabs
- Implemented streaming results display
- Built QA run history viewer
- Files: `app.py`

## Demo

Example QA check:
- **URL**: `https://your-production-app.com`
- **Goal**: `Navigate to the login page. Verify the login form loads correctly with email and password fields. Try submitting empty form and verify validation errors appear.`
- **Result**: PASSED/FAILED with step-by-step agent reasoning

## License

MIT License - see [LICENSE](LICENSE)

---

*Built for TinyFish Hackathon 2026 by pavankumarh14*
