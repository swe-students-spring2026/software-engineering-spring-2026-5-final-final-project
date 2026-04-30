import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors

load_dotenv()

MODELS = [
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

PROMPT = """You are an academic workload estimator for college students. Given an assignment, return a JSON object with exactly these three fields:
- difficulty: integer 1-5 (1=trivial, 5=very hard)
- priority: string, one of "low", "medium", "high"
- estimated_hours: number (realistic hours to complete)

Respond with ONLY valid JSON, no explanation."""

def build_prompt(title, course, description, due_date):
    return f"{PROMPT}\n\nTitle: {title}\nCourse: {course}\nDescription: {description}\nDue date: {due_date}"

def analyze_assignment(title, course, description, due_date):
    client = genai.Client()
    last_error = None
    for model in MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=build_prompt(title, course, description, due_date),
            )
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            print(f"Used model: {model}", flush=True)
            return json.loads(match.group())
        except genai_errors.ServerError as error:
            last_error = error
            continue
    raise RuntimeError("All Gemini models are unavailable.") from last_error
