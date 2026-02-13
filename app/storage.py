import os
import uuid
from pathlib import Path

BASE = Path("sessions")

def new_session_id() -> str:
    return uuid.uuid4().hex[:12]

def session_dir(session_id: str) -> Path:
    d = BASE / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d

def audio_path(session_id: str, qid: str) -> Path:
    return session_dir(session_id) / f"{qid}.mp3"

def report_path(session_id: str) -> Path:
    return session_dir(session_id) / "report.txt"
