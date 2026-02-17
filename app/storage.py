import uuid
import json
from pathlib import Path

BASE = Path("sessions")


def new_session_id() -> str:
    return uuid.uuid4().hex[:12]


def session_dir(session_id: str) -> Path:
    d = BASE / session_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def report_path(session_id: str) -> Path:
    return session_dir(session_id) / "report.txt"


def session_data_path(session_id: str) -> Path:
    return session_dir(session_id) / "session_data.json"


def save_session_data(session_id: str, data: dict) -> None:
    path = session_data_path(session_id)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_session_data(session_id: str) -> dict:
    path = session_data_path(session_id)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ─────────────────────────────────────────
# NEW: Conversation state helpers
# ─────────────────────────────────────────

def save_conversation_state(session_id: str, state: dict) -> None:
    """
    state = {
        "job_title": str,
        "job_description": str,
        "resume_text": str,
        "main_questions": [{"id":..., "text":...}, ...],   # all 10 original questions
        "current_main_index": int,                           # which main question we're on (0-9)
        "followup_count": int,                               # how many follow-ups asked so far for current q
        "conversation_history": [                            # full Q&A so far
            {"question_id": ..., "question": ..., "answer": ..., "is_followup": bool}
        ],
        "evaluations": []                                    # filled in at end
    }
    """
    path = session_dir(session_id) / "conversation_state.json"
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_conversation_state(session_id: str) -> dict:
    path = session_dir(session_id) / "conversation_state.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))