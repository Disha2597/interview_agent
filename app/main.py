import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

from .schemas import QuestionOut, EvalOut, RunInterviewResponse, GenerateQuestionsResponse, SubmitAnswersRequest
from .storage import new_session_id, session_dir, report_path, save_session_data, load_session_data
from .report import build_report
from .llm_questions import OpenAIToolCallingLLM
from pypdf import PdfReader
import io

app = FastAPI(title="Interview Agent - Two Step Process")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
llm = OpenAIToolCallingLLM()

@app.get("/health")
def health():
    return {"ok": True}

# STEP 1: Generate Questions
@app.post("/generate-questions", response_model=GenerateQuestionsResponse)
async def generate_questions(
    job_title: str = Form(...),
    job_description: str = Form(...),
    resume_file: UploadFile = File(...)
):
    """
    STEP 1: Generate interview questions
    Returns: session_id and questions for candidate to answer
    """
    
    # 1. Create session
    session_id = new_session_id()
    session_dir(session_id)

    # 2. Read & extract text from PDF
    pdf_bytes = await resume_file.read()
    reader = PdfReader(io.BytesIO(pdf_bytes))
    resume_text = "\n".join(
        page.extract_text() or "" for page in reader.pages
    )

    if not resume_text.strip():
        raise ValueError("Resume PDF contains no readable text")

    # 3. Generate questions (AI asks questions)
    qs = await llm.generate_role_specific_questions(
        job_title,
        job_description,
        resume_text
    )

    questions_out = [
        QuestionOut(id=q["id"], text=q["text"].strip())
        for q in qs[:10]
    ]

    # 4. Save session data for later use
    save_session_data(session_id, {
        "job_title": job_title,
        "job_description": job_description,
        "resume_text": resume_text,
        "questions": [{"id": q.id, "text": q.text} for q in questions_out]
    })

    return GenerateQuestionsResponse(
        session_id=session_id,
        questions=questions_out,
        message="Questions generated. Please provide answers for each question."
    )


# STEP 2: Submit Answers and Get Evaluation
@app.post("/submit-answers", response_model=RunInterviewResponse)
async def submit_answers(request: SubmitAnswersRequest):
    """
    STEP 2: Candidate submits answers, AI evaluates them
    Input: session_id + answers (dict of question_id -> answer_text)
    Returns: evaluations and report
    """
    
    # 1. Load session data
    session_data = load_session_data(request.session_id)
    if not session_data:
        raise ValueError(f"Session {request.session_id} not found")
    
    job_title = session_data["job_title"]
    job_description = session_data["job_description"]
    resume_text = session_data["resume_text"]
    questions = session_data["questions"]
    
    questions_out = [QuestionOut(**q) for q in questions]

    # 2. Evaluate candidate's answers
    evaluations_out = []

    for q in questions_out:
        # Get candidate's answer for this question
        candidate_answer = request.answers.get(q.id, "").strip()
        
        if not candidate_answer:
            candidate_answer = "No answer provided."

        # AI evaluates the candidate's answer
        score_obj = await llm.evaluate_with_tools(
            q.text, 
            candidate_answer, 
            job_title, 
            job_description, 
            resume_text
        )

        evaluations_out.append(EvalOut(
            question_id=q.id,
            response_text=candidate_answer,
            relevancy_score=int(score_obj["relevancy_score"]),
            strengths=score_obj.get("strengths", []),
            weaknesses=score_obj.get("weaknesses", []),
            improvement_tips=score_obj.get("improvement_tips", []),
            justification=score_obj.get("justification", "")
        ))

    # 3. Build report
    report_text = build_report(
        job_title=job_title,
        questions=questions_out,
        evaluations=evaluations_out
    )
    
    rp = report_path(request.session_id)
    rp.write_text(report_text, encoding="utf-8")

    return RunInterviewResponse(
        session_id=request.session_id,
        questions=questions_out,
        evaluations=evaluations_out,
        report_text=report_text,
        report_url=f"{BASE_URL}/report/{request.session_id}"
    )


@app.get("/report/{session_id}")
def get_report(session_id: str):
    """Serve text report"""
    path = report_path(session_id)
    if not path.exists():
        return PlainTextResponse("Not found", status_code=404)
    return FileResponse(str(path), media_type="text/plain", filename="report.txt")