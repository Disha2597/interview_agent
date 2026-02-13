from typing import List, Dict
from .schemas import QuestionOut, EvalOut, Response

def build_report(
    report_id: str,
    job_id: str,    
    job_title: str,
    questions: List[QuestionOut],
    responses: List[Response],
    evaluations: List[EvalOut]
) -> str:
    
    response_by_qid: Dict[str, Response] = {
        r.question_id: r for r in responses
    }
    eval_by_qid: Dict[str, EvalOut] = {
        e.question_id: e for e in evaluations
    }

    def bullets(items: List[str]) -> List[str]:
        return [f"  - {x}" for x in items] if items else ["  - (none)"]
    
    lines = [
    "Interview Report",
    f"Role: {job_title}",
    "=" * 70,
    "",
]
    
    scores = []
    
    for q in questions:
        lines.append(f"{q.id.upper()}: {q.text}")
        lines.append(f"Question Audio: {q.audio_url}")

        response = response_by_qid.get(q.id)
        evaluation = eval_by_qid.get(q.id)

        if response:
            lines.append(f"Candidate Answer: {response.text}")
            lines.append(f"Answer Audio: {response.audio_url}")
        else:
            lines.append("Candidate Answer: (not provided)")

         # Evaluation
        if not evaluation:
            lines.append("Evaluation: (not available)")
            lines.append("-" * 70)
            continue

    scores.append(evaluation.relevancy_score)

    lines.append("Strengths:")
    lines.extend(bullets(evaluation.strengths))

    lines.append("Weaknesses:")
    lines.extend(bullets(evaluation.weaknesses))

    lines.append("Tips:")
    lines.extend(bullets(evaluation.improvement_tips))

    
    avg = round(sum(scores) / len(scores)) if scores else 0
    lines.append("")
    lines.append(f"Overall Average Relevancy: {avg}/100")

    return "\n".join(lines) 