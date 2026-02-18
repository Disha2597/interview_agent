from pydantic import BaseModel
from typing import List

class QuestionOut(BaseModel):
    id: str
    text: str

class EvalOut(BaseModel):
    question_id: str
    response_text: str
    relevancy_score: int
    strengths: List[str]
    weaknesses: List[str]
    improvement_tips: List[str]
    justification: str

# ── STREAMLINED ENDPOINTS ──

class StartInterviewResponse(BaseModel):
    """Upload resume → immediately get Q1"""
    session_id: str
    question_number: int
    total_questions: int
    question: QuestionOut
    message: str

class SubmitAnswerRequest(BaseModel):
    """Submit one answer"""
    session_id: str
    question_id: str
    answer: str

class NextQuestionResponse(BaseModel):
    """After submitting answer → get next question or follow-up"""
    session_id: str
    question_number: int
    total_questions: int
    question: QuestionOut
    is_followup: bool
    interview_complete: bool
    message: str

class FinishInterviewResponse(BaseModel):
    """Final results"""
    session_id: str
    evaluations: List[EvalOut]
    report_text: str
    report_url: str
    message: str