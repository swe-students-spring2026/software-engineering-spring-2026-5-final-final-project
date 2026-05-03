FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir pipenv==2026.0.3
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile

COPY app/ ./app/

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
