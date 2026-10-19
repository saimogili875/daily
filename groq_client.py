import os
import json
import logging
import requests
from datetime import datetime
from flask import current_app

logger = logging.getLogger('daily_code_exam.groq')

SYSTEM_PROMPT = """You are a strict coding-exam question setter. You will receive the text of a study file uploaded yesterday. Create exactly ONE original coding question that tests the concepts in that file.

Rules:
1. Base the question only on topics found in the file. Do not copy code from it.
2. Difficulty: rotate by weekday (Mon-Tue easy, Wed-Thu medium, Fri-Sat hard, Sun mixed).
3. The question must be solvable in 15-40 lines of Python in under 50 minutes.
4. Include a clear problem statement, input format, output format, and constraints.
5. Give 2 visible sample cases with an explanation, and 5 hidden test cases (normal, edge, empty/minimum, large, tricky).
6. Hidden test outputs must be exactly correct. Self-verify them by reasoning before answering.
7. No ambiguity, no external libraries, input via input() and output via print().
8. Return ONLY valid JSON, no markdown or extra text:

{
  "title": "",
  "difficulty": "easy|medium|hard",
  "topic": "",
  "description": "",
  "input_format": "",
  "output_format": "",
  "constraints": "",
  "samples": [{"input": "", "output": "", "explanation": ""}],
  "hidden_tests": [{"input": "", "output": ""}],
  "hint": "",
  "time_limit_sec": 5,
  "numpy_allowed": false
}"""


def extract_text_from_file(file_path: str, filename: str) -> str:
    """Extracts raw text from .py, .txt, .pdf, or .docx files."""
    ext = os.path.splitext(filename)[1].lower()
    
    try:
        if ext in ('.txt', '.py'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        elif ext == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages[:20]:  # Cap at 20 pages
                extracted = page.extract_text()
                if extracted:
                    text_parts.append(extracted)
            return "\n".join(text_parts)
        elif ext == '.docx':
            import docx
            doc = docx.Document(file_path)
            return "\n".join([p.text for p in doc.paragraphs if p.text])
        else:
            return ""
    except Exception as e:
        logger.error(f"Error extracting text from file {filename}: {e}")
        return ""


def clean_json_response(raw_text: str) -> str:
    """Strips markdown code fences like ```json ... ``` from LLM outputs."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def generate_groq_question(file_text: str, today_ist: str, weekday: str) -> dict:
    """
    Calls the Groq chat completions API with the strict system prompt and user template.
    Returns a validated question dict, or None if failed.
    """
    api_key = current_app.config.get('GROQ_API_KEY')
    model = current_app.config.get('GROQ_MODEL', 'llama-3.3-70b-versatile')

    if not api_key:
        logger.warning("GROQ_API_KEY is not configured; cannot call Groq.")
        return None

    user_prompt = f"Date: {today_ist}. Weekday: {weekday}. Study file content:\n{file_text[:12000]}\nGenerate today's question."

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=40)
        if response.status_code != 200:
            logger.error(f"Groq API error HTTP {response.status_code}: {response.text}")
            return None

        result_json = response.json()
        content = result_json['choices'][0]['message']['content']
        cleaned = clean_json_response(content)
        data = json.loads(cleaned)

        # Validate required fields
        required_fields = ['title', 'description', 'samples', 'hidden_tests']
        for field in required_fields:
            if field not in data or not data[field]:
                logger.error(f"Groq generated JSON missing required field: {field}")
                return None

        # Ensure difficulty and formats are set
        data['difficulty'] = data.get('difficulty', 'medium').lower()
        if data['difficulty'] not in ('easy', 'medium', 'hard'):
            data['difficulty'] = 'medium'

        data['topic'] = data.get('topic') or 'Python Programming'
        data['time_limit_sec'] = int(data.get('time_limit_sec') or 5)

        # Detect numpy/arrays in study file content or from Groq JSON
        file_lower = file_text.lower()
        has_numpy = bool(
            data.get('numpy_allowed') is True
            or 'numpy' in file_lower
            or 'np.' in file_lower
            or 'import numpy' in file_lower
            or ('array' in file_lower and ('dimension' in file_lower or 'matrix' in file_lower))
        )
        data['numpy_allowed'] = has_numpy

        return data

    except Exception as e:
        logger.error(f"Failed to generate question with Groq: {e}", exc_info=True)
        return None


def get_ai_feedback(question_title: str, description: str, code: str, passed_count: int, total_count: int, test_results: list) -> str:
    """
    Generates a concise 2-3 sentence AI evaluation/feedback for user's code submission.
    """
    api_key = current_app.config.get('GROQ_API_KEY')
    model = current_app.config.get('GROQ_MODEL', 'llama-3.3-70b-versatile')

    if not api_key:
        if passed_count == total_count:
            return f"Excellent work! All {total_count} test cases passed successfully with clean execution."
        else:
            return f"Passed {passed_count}/{total_count} test cases. Review failed test cases for edge cases or output formatting differences."

    prompt = f"""You are an expert Python evaluator. Give a concise, constructive 2-3 sentence feedback for this exam submission.
Problem: {question_title}
Result: Passed {passed_count}/{total_count} test cases.
Submitted Code:
{code[:2000]}

Keep the review encouraging, specific to their code structure, and under 60 words. No markdown greetings."""

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 150
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=12)
        if res.status_code == 200:
            return res.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        logger.warning(f"Error fetching AI feedback: {e}")

    if passed_count == total_count:
        return f"Outstanding! All {total_count} test cases passed with full score."
    return f"Code executed. Passed {passed_count} out of {total_count} test cases."
