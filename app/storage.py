import os
import uuid
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