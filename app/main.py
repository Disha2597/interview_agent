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
from fastapi import Form, File, UploadFile
from pypdf import PdfReader
import io
from .schemas import Mode

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
async def run_interview_upload(
    job_title: str = Form(...),
    job_description: str = Form(...),
    mode: Mode = Form("agent"),
    resume_file: UploadFile = File(...)
):
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

    # 3. Generate questions
    qs = await llm.generate_role_specific_questions(
        job_title,
        job_description,
        resume_text
    )

    questions_out = [
        QuestionOut(id=q["id"], text=q["text"].strip())
        for q in qs[:10]
    ]

    # 4. Generate answers + evaluation
    evaluations_out = []
    for q in questions_out:
        if mode == "candidate":
            answer = "No answer provided."
        else:
            answer = await llm.answer_question(
                q.text, job_title, job_description, resume_text
            )

        score_obj = await llm.evaluate_with_tools(
            q.text, answer, job_title, job_description, resume_text
        )

        evaluations_out.append(EvalOut(
            question_id=q.id,
            answer=answer,
            relevancy_score=int(score_obj["relevancy_score"]),
            strengths=score_obj.get("strengths", []),
            weaknesses=score_obj.get("weaknesses", []),
            improvement_tips=score_obj.get("improvement_tips", []),
            justification=score_obj.get("justification", "")
        ))

    # 5. Build report
    report_text = build_report(job_title, questions_out, evaluations_out)
    rp = report_path(session_id)
    rp.write_text(report_text, encoding="utf-8")

    return RunInterviewResponse(
        session_id=session_id,
        questions=questions_out,
        evaluations=evaluations_out,
        report_text=report_text,
        report_url=f"{BASE_URL}/report/{session_id}"
    )

@app.get("/report/{session_id}")
def get_report(session_id: str):
    """Serve text report"""
    path = report_path(session_id)
    if not path.exists():
        return PlainTextResponse("Not found", status_code=404)
    return FileResponse(str(path), media_type="text/plain", filename="report.txt")