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
| --- | --- | --- |
| Agent Architect | AI Orchestration | LangGraph 0.2 |
| Agent Architect | LLM | Google Gemini / OpenAI / Groq / Ollama |
| Agent Architect | Prompts | LangChain Prompts |
| Tool Builder | Web Agent | TinyFish API + Live Streaming |
| Tool Builder | Health Check | Python requests |
| Tool Builder | Database | SQLite / PostgreSQL + SQLAlchemy |
| Tool Builder | Scheduler | APScheduler (BackgroundScheduler) |
| Tool Builder | Alerts | Slack Webhooks |
| Experience Designer | UI | Streamlit 1.32 |
| Experience Designer | Config | Pydantic Settings |

## LLM Providers (All Have Free Tiers!)

Choose your preferred LLM provider via `LLM_PROVIDER` env variable:

| Provider | Setup | Free Tier | Speed |
|----------|-------|-----------|-------|
| **Google Gemini** (default) | `GOOGLE_API_KEY` | 15 req/min, 1M tokens/day | Fast |
| **OpenAI** | `OPENAI_API_KEY` | Free tier available | Medium |
| **Groq** | `GROQ_API_KEY` | Very fast, generous free tier | Very Fast |
| **Ollama** | Local install | Completely free, runs locally | Depends on hardware |

Set `LLM_PROVIDER=google|openai|groq|ollama` in your `.env` file.

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
 - **Live Browser Preview**: Watch TinyFish automation in real-time via streaming URL (🔴 Live Preview)
 - **Scheduled Monitoring**: Set up recurring QA checks (every 1/5/15/30 min, hourly, daily)
 - **Active Job Management**: View, monitor, and stop scheduled jobs from the dashboard
 - **Multi-Provider LLM**: Support for Google Gemini (default), OpenAI, Groq, and Ollama
 - **Persistent History**: All QA runs stored in SQLite/PostgreSQL with full step-by-step logs
 - **Instant Alerts**: Slack notifications for FAILED checks with HIGH/MEDIUM severity
 - **Clean Dashboard**: Streamlit UI with tabs — Run QA, History, Active Schedules, About
 - **Pre-built Workflows**: Login Flow, Checkout Flow, Form Validation templates
 - **Configurable**: Any URL, any goal, any severity threshold, any LLM provider


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
# ==============================================
# 1. TinyFish API Key (REQUIRED)
#    Get from: https://www.tinyfish.ai -> Dashboard -> API Keys
# ==============================================
TINYFISH_API_KEY=your_tinyfish_api_key_here

# ==============================================
# 2. LLM Provider Selection (REQUIRED)
#    Options: google, openai, groq, ollama
# ==============================================
LLM_PROVIDER=google

# ----------------------------------------------
# Google Gemini (FREE - Recommended)
# Get from: https://aistudio.google.com/app/apikey
# Free tier: 15 req/min, 1M tokens/day
# ----------------------------------------------
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-2.0-flash

# ----------------------------------------------
# OR OpenAI
# Get from: https://platform.openai.com
# ----------------------------------------------
# OPENAI_API_KEY=your_openai_key_here
# OPENAI_MODEL=gpt-3.5-turbo

# ----------------------------------------------
# OR Groq (Very Fast!)
# Get from: https://console.groq.com
# ----------------------------------------------
# GROQ_API_KEY=your_groq_key_here
# GROQ_MODEL=llama-3.1-70b-versatile

# ----------------------------------------------
# OR Ollama (Local - Completely Free)
# Install from: https://ollama.com
# ----------------------------------------------
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3.1

# ==============================================
# 3. Database (Auto-created, no setup needed)
#    SQLite (default) or PostgreSQL
# ==============================================
DATABASE_URL=sqlite:///./qa_results.db

# ==============================================
# 4. Slack Webhook (OPTIONAL)
#    Get from: https://api.slack.com/messaging/webhooks
#    Leave blank to disable Slack alerts
# ==============================================
SLACK_WEBHOOK_URL=

## How It Works

1. **User opens Streamlit** → enters URL, workflow name, and QA goal
2. **LangGraph `validate_input` node** → validates URL format, sets RUNNING state
3. **LangGraph `run_agent` node** → LangChain AgentExecutor takes over: 
   - Calls `check_url_health` → verifies URL is reachable (HTTP 200)
   - Calls `run_tinyfish_qa` → TinyFish agent browses with LIVE streaming URL for real-time preview
   - Calls `save_qa_result` → stores result in SQLite/PostgreSQL DB
   - Calls `send_slack_alert` → fires Slack alert if FAILED + HIGH/MEDIUM severity
  **Schedule Setup** (optional) → APScheduler creates background job for recurring checks
5. **LangGraph `finalize` node** → records timestamps, prepares summary
6. **Streamlit displays** → status, steps taken, agent output, duration

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
