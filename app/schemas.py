from pydantic import BaseModel, Field
from typing import List, Optional, Literal

Mode = Literal["agent", "candidate"]

class QuestionOut(BaseModel):
    """Question output without audio"""
    id: str
    text: str

class EvalOut(BaseModel):
    """Evaluation output with answer text"""
    question_id: str
    response_text: str  # The answer text
    relevancy_score: int
    strengths: List[str]
    weaknesses: List[str]
    improvement_tips: List[str]
    justification: str

class RunInterviewResponse(BaseModel):
    """Interview response without audio or separate responses"""
    session_id: str
    questions: List[QuestionOut]
    evaluations: List[EvalOut]
    report_text: str
    report_url: str