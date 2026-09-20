# DriftGuard AI

**Real-time AI-assisted codebase consistency and risk monitoring.**

DriftGuard AI watches a software project continuously and streams problems to a live dashboard the moment they appear.

It is designed as a portfolio-ready Generative AI / Agentic AI project that can run locally without paid APIs, while optionally using **Ollama** for AI explanations.

<img width="1920" height="891" alt="Screenshot (78)" src="https://github.com/user-attachments/assets/2e598056-cd02-4303-bd4e-31e3462d4357" />









## What makes it different

Traditional linters usually inspect one language or one file at a time. DriftGuard AI looks across the repository and tries to detect **cross-file drift** such as:

- Frontend calling API endpoints that the backend does not expose
- Potential secrets committed in source code
- Environment variables used in code but missing from `.env.example`
- TODO / FIXME technical-debt hotspots
- Debug statements accidentally left in production code
- README references to files that do not exist
- Risk-score changes in real time
- Live timeline of repository events

## Real-time architecture

```text
Project Folder
     |
     v
File Watcher (Watchdog)
     |
     v
Scanner / Rule Agents
     |
     +--> API Drift Agent
     +--> Secret Agent
     +--> Env Agent
     +--> Tech Debt Agent
     +--> Debug Agent
     +--> Docs Agent
     |
     v
FastAPI Backend
     |
     +--> REST API
     +--> WebSocket /ws
     |
     v
Live Dashboard
```

## Demo features

- Live project scanning
- WebSocket updates with no page refresh
- Risk score from 0-100
- Severity filters
- Scan statistics
- Repository event timeline
- Optional Ollama-powered issue explanation
- Demo repository included so you can show problems immediately

## Tech stack

- Python 3.10+
- FastAPI
- Uvicorn
- Watchdog
- WebSockets
- HTML / CSS / JavaScript
- Optional Ollama

## Quick start

### 1. Create a virtual environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
python run.py
```

Open:

```text
http://127.0.0.1:8000
```

By default DriftGuard scans the included `demo_project/`.

## Scan your own project

```bash
python run.py --watch "C:\path\to\your\project"
```

or:

```bash
python run.py --watch /path/to/project
```

## Optional local AI with Ollama

Install Ollama and pull a model such as:

```bash
ollama pull llama3.2
```

Start Ollama, then set:

Windows CMD:

```bash
set DRIFTGUARD_OLLAMA_MODEL=llama3.2
```

PowerShell:

```powershell
$env:DRIFTGUARD_OLLAMA_MODEL="llama3.2"
```

Then run DriftGuard normally.

If Ollama is not installed, the project still works. AI explanations gracefully fall back to deterministic recommendations.

## API

- `GET /api/health`
- `GET /api/status`
- `GET /api/findings`
- `POST /api/scan`
- `POST /api/explain`
- `WS /ws`

## Good GitHub screenshots to take

1. Dashboard showing several findings.
2. Change a file in `demo_project/frontend/app.js`.
3. Save it.
4. Show that the dashboard updates instantly.
5. Click **Explain** on a finding.
6. Add your architecture diagram and screenshots to this README.

## Suggested GitHub description

> Real-time AI-assisted codebase drift detector that watches repositories, catches API mismatches, secrets, env/config drift and technical debt, and streams findings live over WebSockets.

## Suggested resume bullet

> Built DriftGuard AI, a real-time repository monitoring agent using FastAPI, Watchdog and WebSockets that detects cross-file API/configuration drift, potential secrets and code-quality risks, with optional local LLM explanations via Ollama.

## Future extensions

- GitHub App integration
- Pull request comments
- Embedding-based semantic documentation drift
- Automatic patch generation
- Multi-repository monitoring
- Slack / Discord alerts
- Dependency vulnerability feeds
- CI/CD mode

## License

MIT
