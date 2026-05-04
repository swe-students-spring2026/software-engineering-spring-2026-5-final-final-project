from fastapi import FastAPI
from pydantic import BaseModel
from ml.summary.app.summarizer import summarize_article

app = FastAPI()

# Request format goes here
class ArticleRequest(BaseModel):
    text: str

# This is the API endpoint for summarization
@app.post("/summarize")
def summarize(req: ArticleRequest):
    result = summarize_article(req.text)
    return result