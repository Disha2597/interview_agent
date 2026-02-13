import json
from openai import OpenAI
import os

QUESTION_GEN_SYSTEM = """You are an expert interviewer.

Based on the JOB TITLE, JOB DESCRIPTION, and RESUME, identify ALL relevant role dimensions/competencies
and generate behavioral interview questions for each.

CRITICAL: Analyze BOTH the job title AND job description together to understand the full scope of the role.

Return STRICT JSON ONLY in the following format:
{
  "Role Dimension 1": [
    {"id":"dimension1_q1","text":"..."},
    {"id":"dimension1_q2","text":"..."}
  ],
  "Role Dimension 2": [
    {"id":"dimension2_q1","text":"..."}
  ]
}

Instructions:
1. START by analyzing the job title to understand the core role (e.g., "Senior ML Engineer" = ML + Seniority/Leadership)
2. THEN analyze the job description to identify specific competencies and responsibilities
3. COMBINE insights from both to identify 5-7 key role dimensions/competencies
4. Common dimensions include (but are not limited to):
   - Software Engineering, ML Engineering, Cloud/Infrastructure, Product Management
   - Data Science, Data Analysis, Business Analysis, Leadership, Communication
   - System Design, DevOps, Security, Research, Front-end, Back-end, etc.
5. Generate 1-3 questions per dimension based on resume relevance
6. Questions must be behavioral or applied decision-making
7. Every question must reference past experience or projects
8. Use STAR-style phrasing (e.g., "Tell me about a time...")
9. Avoid trivia, theory dumps, or leetcode-style questions
10. No markdown, no explanations, no extra keys
11. ID format: use short abbreviation + _q# (e.g., "swe_q1", "ml_q2", "lead_q1")
"""

ANSWER_GEN_SYSTEM = """You are the candidate.
Answer the question in 90-140 words.
Use only information that is consistent with the resume and job description.
Be honest: if unknown, say what you'd do and what you'd verify.
No markdown.
"""

EVAL_SYSTEM = """You are an interview evaluator.
Evaluate the candidate's answer to the interview question.

Return STRICT JSON ONLY:
{
  "relevancy_score": <int 0-100>,
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "improvement_tips": ["...", "..."],
  "justification": "..."
}
No markdown. No extra keys.
"""


class OpenAIToolCallingLLM:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    async def generate_role_specific_questions(self, job_title: str, job_description: str, resume: str):
        payload = {
            "job_title": job_title,
            "job_description": job_description,
            "resume": resume,
            "instruction": "Analyze BOTH the job title and job description together to identify relevant role dimensions/competencies, then generate 1-3 behavioral questions for each dimension. The job title often reveals seniority level and core function that may not be explicit in the description."
        }

        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": QUESTION_GEN_SYSTEM},
                {"role": "user", "content": json.dumps(payload)}
            ],
            response_format={"type": "json_object"}
        )

        data = json.loads(resp.choices[0].message.content)

        # Return ALL questions from ALL identified dimensions
        all_questions = []
        if isinstance(data, dict):
            for dimension, questions in data.items():
                if isinstance(questions, list):
                    all_questions.extend(questions)
        
        return all_questions
    
    async def answer_question(self, question: str, job_title: str, job_description: str, resume: str):
        """Generate candidate answer to a question"""
        payload = {
            "question": question,
            "job_title": job_title,
            "job_description": job_description,
            "resume": resume
        }
        
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": ANSWER_GEN_SYSTEM},
                {"role": "user", "content": json.dumps(payload)}
            ]
        )
        
        return resp.choices[0].message.content.strip()
    
    async def evaluate_with_tools(self, question: str, answer: str, job_title: str, job_description: str, resume: str):
        """Evaluate answer and return scores"""
        payload = {
            "question": question,
            "answer": answer,
            "job_title": job_title,
            "job_description": job_description,
            "resume": resume
        }
        
        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": EVAL_SYSTEM},
                {"role": "user", "content": json.dumps(payload)}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(resp.choices[0].message.content)