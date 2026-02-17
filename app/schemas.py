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


#NEW: Conversational Interview Schemas


class StartConversationResponse(BaseModel):
    """Response when starting conversational interview - returns first question"""
    session_id: str
    question_number: int        # e.g. 1 (out of 10)
    total_questions: int        # always 10
    question: QuestionOut 
    message: str

class SubmitAnswerRequest(BaseModel):
    """Candidate submits answer to current question"""
    session_id: str
    question_id: str
    answer: str


class NextQuestionResponse(BaseModel):
    """Response after candidate answers - either follow-up or next main question"""
    session_id: str
    question_number: int
    total_questions: int
    question: QuestionOut
    is_followup: bool           # True = follow-up to previous answer, False = new main question
    interview_complete: bool    # True when all questions done
    message: str

class ConversationCompleteResponse(BaseModel):
    """Returned when interview is fully complete"""
    session_id: str
    evaluations: List[EvalOut]
    report_text: str
    report_url: str
    message: str