FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN python -m pip install --no-cache-dir --upgrade pip

CMD ["python", "-m", "meme.main"]
