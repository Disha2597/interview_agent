import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()
from .schemas import QuestionOut, EvalOut, Response, RunInterviewResponse
from .storage import new_session_id, session_dir, report_path
from .report import build_report
from .llm_questions import OpenAIToolCallingLLM

app = FastAPI(title="Interview Agent (Text + Audio + Tool Calling)")

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

@app.post("/run-interview-upload", response_model=RunInterviewResponse)
async def run_interview(
    job_title: str = Form(...),
    job_description: str = Form(...),
    mode: str = Form("agent"),
    resume_file: UploadFile = File(...)
):
    """
    Main endpoint to run interview:
    1. Upload resume
    2. Generate questions
    3. Generate audio for questions
    4. Generate answers (agent mode) or use provided answers (candidate mode)
    5. Evaluate answers
    6. Generate report
    """
    
    session_id = new_session_id() 
    sdir = session_dir(session_id)                

    # 1) Save uploaded resume file into the session folder
    resume_path = sdir / resume_file.filename
    resume_bytes = await resume_file.read()
    resume_path.write_bytes(resume_bytes)

    # 2) Convert resume to text (works for .txt resumes)
    resume_text = resume_bytes.decode("utf-8", errors="ignore")

    # 3) Generate role-specific questions for ALL roles
    all_questions = await llm.generate_role_specific_questions(job_title, job_description, resume_text)
    
    # 4) Take up to 10 questions from the combined pool
    questions_out = []
    for q in all_questions[:10]:  # Limit to 10 questions total
        qid = q["id"]
        qtext = q["text"].strip()

        questions_out.append(QuestionOut(id=qid, text=qtext))

    # 5) Generate answers and audio for answers
    responses_out = []
    for q in questions_out:
        # In agent mode, LLM generates answer; in candidate mode, we'd need their answers
        if mode == "agent":
            answer_text = await llm.answer_question(q.text, job_title, job_description, resume_text)
        else:
            # For candidate mode, you'd need to pass candidate_answers from request body
            # For now, use placeholder
            answer_text = "Candidate answer would go here"
        
        # Generate audio for answer
        answer_id = f"{q.id}_answer"
        
        responses_out.append(Response(
            question_id=q.id,
            text=answer_text,
        ))

    # 6) Evaluate answers
    evaluations_out = []
    for q, r in zip(questions_out, responses_out):
        score_obj = await llm.evaluate_with_tools(
            q.text, 
            r.text, 
            job_title, 
            job_description, 
            resume_text
        )

        evaluations_out.append(EvalOut(
            question_id=q.id,
            response_text=r.text,
            relevancy_score=int(score_obj.get("relevancy_score", 0)),
            strengths=score_obj.get("strengths", []),
            weaknesses=score_obj.get("weaknesses", []),
            improvement_tips=score_obj.get("improvement_tips", []),
            justification=score_obj.get("justification", "")
        ))

    # 7) Generate report
    report_text = build_report(
        report_id=session_id,
        job_id=session_id,
        job_title=job_title,
        questions=questions_out,
        responses=responses_out,
        evaluations=evaluations_out
    )
    
    rp = report_path(session_id)
    rp.write_text(report_text, encoding="utf-8")
    report_url = f"{BASE_URL}/report/{session_id}"

    return RunInterviewResponse(
        session_id=session_id,
        questions=questions_out,
        responses=responses_out,
        evaluations=evaluations_out,
        report_text=report_text,
        report_url=report_url
    )

@app.get("/report/{session_id}")
def get_report(session_id: str):
    """Serve text report"""
    path = report_path(session_id)
    if not path.exists():
        return PlainTextResponse("Not found", status_code=404)
    return FileResponse(str(path), media_type="text/plain", filename="report.txt")