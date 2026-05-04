from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from pathlib import Path

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def summarize_article(text: str):
    if not text or not text.strip():
        raise ValueError("Article text is required")

    text = text[:20000]  # limit input to 20k chars

    system_prompt = """ You are a news summarization system.
        Return JSON only with these keys:
        - title: extract or infer the article title
        - summary: a neutral, objective summary in 2-3 sentences
        - article_type: one of technology, sports, education, product reviews, news, other

        Rules:
        - Do not add information that is not in the article text.
        - Preserve key facts, names, and numbers.
        - Use "other" if the article does not clearly fit another category. """

    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Article:\n{text}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    content = response.choices[0].message.content
    if content is None:
        raise RuntimeError("OpenAI returned an empty response")

    return json.loads(content)
