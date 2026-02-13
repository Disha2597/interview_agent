from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal


Mode = Literal["agent","candidate"]

class RunInterviewRequest(BaseModel):
    job_title: str = Field(..., min_length = 2)
    job_description: str = Field(..., min_length = 10)
    resume : str = Field(..., min_length=10)
    mode : Mode = "agent"
    candidate_answers: Optional[Dict[str, str]] = None  # keys: q1..q10

class QuestionOut(BaseModel):
    id : str
    text: str


class Response(BaseModel):
    question_id : str
    text: str

class EvalOut(BaseModel):
    question_id: str
    response_text : str
    relevancy_score: int
    strengths: List[str]
    weaknesses: List[str]
    improvement_tips: List[str]
    justification: str

class RunInterviewResponse(BaseModel):
    session_id : str
    questions : List[QuestionOut]
    responses : List[Response]
    evaluations: List[EvalOut]
    report_text: str
    report_url: str