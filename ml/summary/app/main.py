from fastapi import FastAPI
from pydantic import BaseModel
from .summarizer import process_input

# Using FastAPI to test summarization functionality.
app = FastAPI()


# Request format goes here
class ArticleRequest(BaseModel):
    text: str | None = None
    url: str | None = None


# This is the API endpoint for summarization
@app.post("/summarize")
def summarize(req: ArticleRequest):
    input_value = req.url or req.text
    if not input_value:
        raise ValueError("Article text or URL is required")
    return process_input(input_value)
