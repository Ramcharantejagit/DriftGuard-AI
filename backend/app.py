import asyncio
import os
import time
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .scanner import scan_project
from .models import ExplainRequest
from .ai import explain_finding

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
WATCH_PATH = os.getenv("DRIFTGUARD_WATCH_PATH", str(BASE_DIR / "demo_project"))

app = FastAPI(title="DriftGuard AI", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

clients: Set[WebSocket] = set()
state = {
    "last_scan": None,
    "last_event": None,
    "scan_count": 0,
    "data": None,
    "events": [],
}
_loop = None
observer = None

def record_event(kind: str, message: str):
    event = {"time": time.strftime("%H:%M:%S"), "kind": kind, "message": message}
    state["events"].insert(0, event)
    state["events"] = state["events"][:40]
    state["last_event"] = event

def run_scan(trigger="manual"):
    data = scan_project(WATCH_PATH)
    state["data"] = data
    state["last_scan"] = time.strftime("%Y-%m-%d %H:%M:%S")
    state["scan_count"] += 1
    record_event("scan", f"Scan #{state['scan_count']} completed ({trigger})")
    return data

async def broadcast(payload: dict):
    stale = []
    for ws in list(clients):
        try:
            await ws.send_json(payload)
        except Exception:
            stale.append(ws)
    for ws in stale:
        clients.discard(ws)

async def scan_and_broadcast(trigger="file-change"):
    await asyncio.sleep(0.15)
    data = run_scan(trigger)
    await broadcast({
        "type": "scan",
        "data": data,
        "last_scan": state["last_scan"],
        "events": state["events"],
    })

class ChangeHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if any(part in {".git", ".venv", "node_modules", "__pycache__"} for part in p.parts):
            return
        record_event("change", f"{event.event_type}: {p.name}")
        if _loop:
            asyncio.run_coroutine_threadsafe(
                scan_and_broadcast(f"{event.event_type}:{p.name}"),
                _loop
            )

@app.on_event("startup")
async def startup_event():
    global _loop, observer
    _loop = asyncio.get_running_loop()
    Path(WATCH_PATH).mkdir(parents=True, exist_ok=True)
    run_scan("startup")
    observer = Observer()
    observer.schedule(ChangeHandler(), WATCH_PATH, recursive=True)
    observer.start()
    record_event("system", f"Watching {WATCH_PATH}")

@app.on_event("shutdown")
async def shutdown_event():
    global observer
    if observer:
        observer.stop()
        observer.join(timeout=2)

@app.get("/")
def home():
    return FileResponse(str(FRONTEND_DIR / "index.html"))

@app.get("/api/health")
def health():
    return {"ok": True, "watching": WATCH_PATH}

@app.get("/api/status")
def status():
    if state["data"] is None:
        run_scan("status")
    return {
        "watching": WATCH_PATH,
        "last_scan": state["last_scan"],
        "scan_count": state["scan_count"],
        "events": state["events"],
        "data": state["data"],
    }

@app.get("/api/findings")
def findings():
    if state["data"] is None:
        run_scan("findings")
    return state["data"]["findings"]

@app.post("/api/scan")
async def manual_scan():
    data = run_scan("manual")
    await broadcast({
        "type": "scan",
        "data": data,
        "last_scan": state["last_scan"],
        "events": state["events"],
    })
    return data

@app.post("/api/explain")
def explain(req: ExplainRequest):
    if not state["data"]:
        run_scan("explain")
    finding = next((x for x in state["data"]["findings"] if x["id"] == req.finding_id), None)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    return explain_finding(finding)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    try:
        await websocket.send_json({
            "type": "hello",
            "data": state["data"],
            "last_scan": state["last_scan"],
            "events": state["events"],
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.discard(websocket)
    except Exception:
        clients.discard(websocket)
