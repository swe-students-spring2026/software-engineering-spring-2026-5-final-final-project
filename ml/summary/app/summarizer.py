from openai import OpenAI
from dotenv import load_dotenv
from newspaper import Article
from urllib.parse import urlparse

import os
import json
import re

load_dotenv()

MAX_INPUT_CHARS = 20000
DEFAULT_MODEL = "gpt-5-nano"  # make sure we are using gpt-5-nano for testing

prompt = """
    You are a news summarization system.
    Return JSON only with these keys:
    - title: extract or infer the article title
    - summary: a neutral, objective summary in 2-3 sentences
    - article_type: one of technology, sports, education, product reviews, news, other
    - source_type: one of url, text

    Rules:
    - Do not add information that is not in the article text.
    - Preserve key facts, names, and numbers.
    - Use "other" if the article does not clearly fit another category.
    """


# Helper functions for processing input and summarization
# First is for checking if the input is a URL
def is_url(text):
    url = urlparse(text.strip()) if text else urlparse("")
    return url.scheme in {"http", "https"} and bool(url.netloc)


# If it is text, we cleaning it up by removing extra whitespace.
def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


# Main func for extracting article text
def extract_article(user_input):
    user_input = clean(user_input)
    if not user_input:
        raise ValueError("Article text or URL is required")

    if not is_url(user_input):
        return "", user_input[:MAX_INPUT_CHARS], "text"

    article = Article(user_input)
    try:
        article.download()
        article.parse()
    except Exception as exc:
        raise RuntimeError("Could not extract article from URL") from exc

    text = clean(article.text)
    if not text:
        raise RuntimeError("No article text found at URL")
    return clean(article.title), text[:MAX_INPUT_CHARS], "url"


def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def summarize_article(user_input):
    title, text, source_type = extract_article(user_input)
    response = get_client().chat.completions.create(
        model=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
        messages=[
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": f"Source type: {source_type}\nTitle: {title}\nArticle:\n{text}",
            },
        ],
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    try:
        result = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI returned invalid JSON") from exc
    return {
        "title": result.get("title") or title,
        "article_text": user_input if source_type == "text" else None,
        "article_summary": result["summary"],
        "article_type": result.get("article_type", "other"),
        "source_type": source_type,
    }


def process_input(user_input):
    return summarize_article(user_input)


def send_to_meme_generator(data):
    return {"status": "ready", "target": "memegen_client.py", "payload": data}
