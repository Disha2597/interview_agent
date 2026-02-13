from pydantic import BaseModel, Field
from typing import List, Dict

class QuestionOut(BaseModel):
    """AI-generated interview question"""
    id: str
    text: str

class EvalOut(BaseModel):
    """AI evaluation of candidate's answer"""
    question_id: str
    response_text: str  # Candidate's actual answer
    relevancy_score: int
    strengths: List[str]
    weaknesses: List[str]
    improvement_tips: List[str]
    justification: str

# STEP 1 Response
class GenerateQuestionsResponse(BaseModel):
    """Response from generate-questions endpoint"""
    session_id: str
    questions: List[QuestionOut]
    message: str

# STEP 2 Request
class SubmitAnswersRequest(BaseModel):
    """Request to submit-answers endpoint"""
    session_id: str
    answers: Dict[str, str]  # {question_id: answer_text}

# STEP 2 Response
class RunInterviewResponse(BaseModel):
    """Complete interview response with evaluations"""
    session_id: str
    questions: List[QuestionOut]
    evaluations: List[EvalOut]
    report_text: str
    report_url: str