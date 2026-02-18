import json
from openai import OpenAI
import os

QUESTION_GEN_SYSTEM = """You are an expert interviewer.

Based on the JOB TITLE, JOB DESCRIPTION, and RESUME, identify ALL relevant role dimensions/competencies
and generate behavioral interview questions for each.

CRITICAL: Analyze BOTH the job title AND job description together to understand the full scope of the role.

Return STRICT JSON ONLY in the following format (with ACTUAL dimension names, not placeholders):
{
  "Machine Learning Engineering": [
    {"id":"ml_q1","text":"Tell me about a time you deployed a model to production..."},
    {"id":"ml_q2","text":"Describe a situation where you optimized model performance..."}
  ],
  "Software Engineering": [
    {"id":"swe_q1","text":"Walk me through how you designed a scalable system..."}
  ]
}

Instructions:
1. START by analyzing the job title to understand the core role
2. THEN analyze the job description to identify specific competencies
3. COMBINE insights from both to identify 5-7 key role dimensions
4. Use SPECIFIC, DESCRIPTIVE dimension names
5. Generate 1-3 questions per dimension based on resume relevance
6. Questions must be behavioral or applied decision-making
7. Use STAR-style phrasing (e.g., "Tell me about a time...")
8. No markdown, no explanations, no extra keys
9. ID format: short abbreviation + _q# (e.g., "ml_q1", "swe_q2")
"""

ANSWER_GEN_SYSTEM = """You are the candidate.
Answer the question in 90-140 words.
Use only information consistent with the resume and job description.
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

FOLLOWUP_SYSTEM = """You are an expert interviewer conducting a conversational interview.

Based on the candidate's answer to the previous question, generate ONE smart follow-up question
that digs deeper into what they said.

Rules:
- The follow-up MUST be directly based on something specific the candidate mentioned in their answer
- Ask for more detail, clarification, or an example about something they said
- Keep it conversational and natural, like a real interviewer would ask
- Focus on the most interesting or unclear part of their answer
- Do NOT repeat the original question
- Do NOT ask about something they didn't mention
- Keep it to ONE question only

Return STRICT JSON ONLY:
{
  "id": "followup_q<number>",
  "text": "Follow-up question here..."
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
            "instruction": "Analyze BOTH the job title and job description together to identify relevant role dimensions/competencies, then generate 1-3 behavioral questions for each dimension."
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

        all_questions = []
        if isinstance(data, dict):
            for dimension, questions in data.items():
                if isinstance(questions, list):
                    all_questions.extend(questions)

        return all_questions

    async def generate_followup_question(
        self,
        original_question: str,
        candidate_answer: str,
        followup_number: int,
        conversation_history: list
    ):
        """
        Generate a follow-up question based on what the candidate just answered.
        conversation_history: list of {"question": ..., "answer": ...} dicts
        """
        history_text = ""
        for i, turn in enumerate(conversation_history):
            history_text += f"Q{i+1}: {turn['question']}\nA{i+1}: {turn['answer']}\n\n"

        payload = {
            "conversation_so_far": history_text,
            "last_question": original_question,
            "candidate_answer": candidate_answer,
            "followup_number": followup_number,
            "instruction": "Generate ONE follow-up question based specifically on what the candidate just said."
        }

        resp = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": FOLLOWUP_SYSTEM},
                {"role": "user", "content": json.dumps(payload)}
            ],
            response_format={"type": "json_object"}
        )

        return json.loads(resp.choices[0].message.content)

    async def answer_question(self, question: str, job_title: str, job_description: str, resume: str):
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