FROM python:3.10-slim

WORKDIR /app

COPY Pipfile* ./
RUN python -m pip install --no-cache-dir --upgrade pip pipenv \
    && if [ -f Pipfile.lock ]; then pipenv sync --system; else pipenv install --system --skip-lock; fi

COPY . .

CMD ["python", "-m", "meme.main"]
