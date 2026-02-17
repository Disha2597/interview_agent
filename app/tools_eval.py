import re
import os
from typing import Dict, List
import json
from openai import OpenAI

def get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Set it in your environment before running."
        )
    return OpenAI(api_key=api_key)

client = get_client

def extract_requirements(job_title: str, job_description: str) -> Dict[str, List[str]]:
    text = (job_title + "\n" + job_description).lower()

    skills = set(re.findall(
        r"\b(python|sql|aws|gcp|azure|docker|kubernetes|fastapi|ml|nlp|pytorch|tensorflow|spark|airflow|dbt)\b",
        text
    ))


    responsibilities = []

    for line in job_description.splitlines():
        l = line.strip()
        if len(l) > 10 and any(k in l.lower() for k in ["responsib", "you will", "build", "design", "deploy", "develop", "own"]):
            responsibilities.append(l[:220])

    return {"skills": sorted(skills), "responsibilities": responsibilities[:12]}

def build_interview_qa_match_context(
    question: str,
    requirements: Dict[str, List[str]]
) -> str:
    skills = ", ".join(requirements.get("skills", []))
    resps = " | ".join(requirements.get("responsibilities", []))

    return f"""Interview Question:
{question}

Job Requirements:
Skills: {skills}
Responsibilities: {resps}
"""

def embed(text: str) -> List[float]:
    resp = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return resp.data[0].embedding

def cosine_sim(a: List[float], b: List[float]) -> float:
    a = np.array(a, dtype=np.float32)
    b = np.array(b, dtype=np.float32)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-12
    return float(np.dot(a, b) / denom)

def score_relevancy_embeddings(question, candidate_answer, requirements) -> Dict:
    target_context = build_interview_qa_match_context(question, requirements)

    emb_answer = embed(candidate_answer)
    emb_target = embed(target_context)

    sim = cosine_sim(emb_answer, emb_target)
    score = int(max(0, min(100, round(sim * 100))))

    strengths, weaknesses, tips = [], [], []

    if score >= 75:
        strengths.append("Answer is strongly aligned with the question and job requirements (semantic match).")
    elif score >= 55:
        strengths.append("Answer is moderately aligned with the question and job requirements.")
        weaknesses.append("Answer could be more directly tied to the job’s key responsibilities/skills.")
    else:
        weaknesses.append("Answer is weakly aligned with the question/job requirements (semantic mismatch).")

    if score < 75:
        tips.extend([
            "Explicitly connect your answer to 2–3 job requirements (skills/responsibilities).",
            "Use STAR (Situation, Task, Action, Result) to make the answer more focused.",
            "Add one measurable impact (latency, accuracy, cost, time saved, etc.)."
        ])

    return {
        "relevancy_score": score,
        "strengths": strengths[:4],
        "weaknesses": weaknesses[:4],
        "improvement_tips": tips[:4],
    }

if __name__ == "__main__":
    job_title = "Machine Learning Engineer"
    job_description = """
Responsibilities:
- Build and deploy ML models
- Develop data pipelines in Python and SQL
- Work with AWS and Docker
"""
    question = "Tell me about a time you deployed a model to production."
    candidate_answer = "I containerized a model with Docker and deployed it to AWS, adding monitoring and retraining triggers."

    reqs = extract_requirements(job_title, job_description)
    result = score_relevancy_embeddings(question, candidate_answer, reqs)
    print(json.dumps(result, indent=2))