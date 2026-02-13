import os
import uuid
import json
from pathlib import Path

BASE = Path("sessions")

def new_session_id() -> str:
    """Generate a new session ID"""
    return uuid.uuid4().hex[:12]

def session_dir(session_id: str) -> Path:
    """Get or create session directory"""
    d = BASE / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def report_path(session_id: str) -> Path:
    """Get path to report file"""
    return session_dir(session_id) / "report.txt"

def session_data_path(session_id: str) -> Path:
    """Get path to session data file"""
    return session_dir(session_id) / "session_data.json"

def save_session_data(session_id: str, data: dict) -> None:
    """Save session data (job info, questions, etc.)"""
    path = session_data_path(session_id)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def load_session_data(session_id: str) -> dict:
    """Load session data"""
    path = session_data_path(session_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))