from typing import List
from .schemas import QuestionOut, EvalOut

def build_report(
    job_title: str,
    questions: List[QuestionOut],
    evaluations: List[EvalOut]
) -> str:
    """
    Build interview report.
    AI asks questions → Candidate answers → AI evaluates
    """
    
    # Create lookup for evaluations by question ID
    eval_by_qid = {e.question_id: e for e in evaluations}

    def bullets(items: List[str]) -> List[str]:
        return [f"  - {x}" for x in items] if items else ["  - (none)"]
    
    lines = [
        "=" * 70,
        "INTERVIEW REPORT",
        "=" * 70,
        f"Role: {job_title}",
        "=" * 70,
        "",
    ]
    
    scores = []
    
    # Loop through each question
    for idx, q in enumerate(questions, 1):
        lines.append(f"\n{'='*70}")
        lines.append(f"QUESTION {idx}: {q.id.upper()}")
        lines.append(f"{'='*70}")
        lines.append(f"\n{q.text}")

        # Get evaluation for this question
        evaluation = eval_by_qid.get(q.id)

        if not evaluation:
            lines.append("\nEvaluation: (not available)")
            lines.append("-" * 70)
            continue

        # FIXED: This was outside the loop - now it's inside
        # Add candidate's answer
        lines.append(f"\nCandidate Answer:\n{evaluation.response_text}")
        
        # Add score
        scores.append(evaluation.relevancy_score)
        lines.append(f"\nRelevancy Score: {evaluation.relevancy_score}/100")
        
        # Add evaluation details
        lines.append("\nStrengths:")
        lines.extend(bullets(evaluation.strengths))

        lines.append("\nWeaknesses:")
        lines.extend(bullets(evaluation.weaknesses))

        lines.append("\nImprovement Tips:")
        lines.extend(bullets(evaluation.improvement_tips))
        
        if evaluation.justification:
            lines.append(f"\nJustification:\n{evaluation.justification}")

    # Overall summary
    lines.append("\n" + "=" * 70)
    lines.append("OVERALL SUMMARY")
    lines.append("=" * 70)
    
    avg = round(sum(scores) / len(scores)) if scores else 0
    lines.append(f"\nTotal Questions: {len(questions)}")
    lines.append(f"Average Relevancy Score: {avg}/100")
    
    if scores:
        lines.append(f"Highest Score: {max(scores)}/100")
        lines.append(f"Lowest Score: {min(scores)}/100")
    
    lines.append("\n" + "=" * 70)

    return "\n".join(lines)