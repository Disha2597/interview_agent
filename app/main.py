import os
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

from .schemas import (
    QuestionOut, EvalOut,
    StartInterviewResponse, SubmitAnswerRequest,
    NextQuestionResponse, FinishInterviewResponse
)
from .storage import (
    new_session_id, session_dir, report_path,
    save_conversation_state, load_conversation_state
)
from .report import build_report
from .llm_questions import OpenAIToolCallingLLM
from pypdf import PdfReader
import io

app = FastAPI(title="Interview Agent - Auto Conversational")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
llm = OpenAIToolCallingLLM()

# Only Q1 and Q2 get follow-ups
QUESTIONS_WITH_FOLLOWUP = {0, 1}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/start-interview", response_model=StartInterviewResponse)
async def start_interview(
    job_title: str = Form(...),
    job_description: str = Form(...),
    resume_file: UploadFile = File(...)
):
    """
    ONE-SHOT START:
    Upload resume + job info → Get Q1 immediately
    Conversation starts automatically for Q1 and Q2 (with follow-ups)
    Q3-Q10 are asked normally without follow-ups
    """
    session_id = new_session_id()
    session_dir(session_id)

    # Extract resume
    pdf_bytes = await resume_file.read()
    reader = PdfReader(io.BytesIO(pdf_bytes))
    resume_text = "\n".join(page.extract_text() or "" for page in reader.pages)

    if not resume_text.strip():
        raise ValueError("Resume PDF contains no readable text")

    # Generate all 10 questions
    qs = await llm.generate_role_specific_questions(job_title, job_description, resume_text)
    main_questions = [{"id": q["id"], "text": q["text"].strip()} for q in qs[:10]]

    # Save state
    save_conversation_state(session_id, {
        "job_title": job_title,
        "job_description": job_description,
        "resume_text": resume_text,
        "main_questions": main_questions,
        "current_main_index": 0,
        "awaiting_followup": False,
        "followup_counter": 0,
        "conversation_history": []
    })

    first_q = main_questions[0]
    
    return StartInterviewResponse(
        session_id=session_id,
        question_number=1,
        total_questions=len(main_questions),
        question=QuestionOut(**first_q),
        message="Interview started! Questions 1 and 2 will have follow-ups based on your answers."
    )


@app.post("/submit-answer", response_model=NextQuestionResponse)
async def submit_answer(request: SubmitAnswerRequest):
    """
    Submit answer → Get next question
    
    Flow:
    - Answer Q1 → get follow-up on Q1
    - Answer follow-up → get Q2
    - Answer Q2 → get follow-up on Q2
    - Answer follow-up → get Q3
    - Answer Q3-Q10 → get next question (no follow-ups)
    """
    state = load_conversation_state(request.session_id)
    if not state:
        raise ValueError(f"Session {request.session_id} not found")

    job_title = state["job_title"]
    job_description = state["job_description"]
    resume_text = state["resume_text"]
    main_questions = state["main_questions"]
    current_idx = state["current_main_index"]
    awaiting_followup = state["awaiting_followup"]

    # Save answer to history
    state["conversation_history"].append({
        "question_id": request.question_id,
        "question": next(
            (q["text"] for q in main_questions if q["id"] == request.question_id),
            request.question_id
        ),
        "answer": request.answer,
        "is_followup": awaiting_followup
    })

    # ── CASE 1: Just answered a follow-up OR a question that doesn't get follow-up (Q3+) ──
    # → Move to next main question
    if awaiting_followup or current_idx not in QUESTIONS_WITH_FOLLOWUP:
        next_idx = current_idx + 1

        if next_idx >= len(main_questions):
            # All done!
            state["awaiting_followup"] = False
            save_conversation_state(request.session_id, state)

            return NextQuestionResponse(
                session_id=request.session_id,
                question_number=len(main_questions),
                total_questions=len(main_questions),
                question=QuestionOut(id="done", text="Interview complete."),
                is_followup=False,
                interview_complete=True,
                message="All questions answered! Call POST /finish-interview to get your results."
            )

        # Move to next main question
        state["current_main_index"] = next_idx
        state["awaiting_followup"] = False
        save_conversation_state(request.session_id, state)

        next_q = main_questions[next_idx]
        return NextQuestionResponse(
            session_id=request.session_id,
            question_number=next_idx + 1,
            total_questions=len(main_questions),
            question=QuestionOut(**next_q),
            is_followup=False,
            interview_complete=False,
            message=f"Question {next_idx + 1} of {len(main_questions)}."
        )

    # ── CASE 2: Just answered Q1 or Q2 (main questions that get follow-ups) ──
    # → Generate follow-up based on their answer
    state["followup_counter"] += 1
    followup_number = state["followup_counter"]

    followup_q = await llm.generate_followup_question(
        original_question=main_questions[current_idx]["text"],
        candidate_answer=request.answer,
        followup_number=followup_number,
        conversation_history=state["conversation_history"]
    )

    state["awaiting_followup"] = True
    save_conversation_state(request.session_id, state)

    return NextQuestionResponse(
        session_id=request.session_id,
        question_number=current_idx + 1,
        total_questions=len(main_questions),
        question=QuestionOut(id=followup_q["id"], text=followup_q["text"]),
        is_followup=True,
        interview_complete=False,
        message="Follow-up question based on your answer."
    )


@app.post("/finish-interview", response_model=FinishInterviewResponse)
async def finish_interview(session_id: str = Form(...)):
    """
    Get final evaluation and report.
    Just pass session_id.
    """
    state = load_conversation_state(session_id)
    if not state:
        raise ValueError(f"Session {session_id} not found")

    job_title = state["job_title"]
    job_description = state["job_description"]
    resume_text = state["resume_text"]
    conversation_history = state["conversation_history"]

    evaluations_out = []
    questions_out = []

    for turn in conversation_history:
        q = QuestionOut(id=turn["question_id"], text=turn["question"])
        questions_out.append(q)

        score_obj = await llm.evaluate_with_tools(
            turn["question"],
            turn["answer"],
            job_title,
            job_description,
            resume_text
        )

        evaluations_out.append(EvalOut(
            question_id=turn["question_id"],
            response_text=turn["answer"],
            relevancy_score=int(score_obj["relevancy_score"]),
            strengths=score_obj.get("strengths", []),
            weaknesses=score_obj.get("weaknesses", []),
            improvement_tips=score_obj.get("improvement_tips", []),
            justification=score_obj.get("justification", "")
        ))

    report_text = build_report(
        job_title=job_title,
        questions=questions_out,
        evaluations=evaluations_out
    )
    report_path(session_id).write_text(report_text, encoding="utf-8")

    return FinishInterviewResponse(
        session_id=session_id,
        evaluations=evaluations_out,
        report_text=report_text,
        report_url=f"{BASE_URL}/report/{session_id}",
        message="Interview complete! Here are your evaluations and report."
    )


@app.get("/report/{session_id}")
def get_report(session_id: str):
    path = report_path(session_id)
    if not path.exists():
        return PlainTextResponse("Not found", status_code=404)
    return FileResponse(str(path), media_type="text/plain", filename="report.txt")