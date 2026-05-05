FROM python:3.12-slim

# Run as a non-root user so even student-spawned subprocesses can't chmod the
# interpreter, write to system paths, etc.
RUN useradd --create-home --shell /bin/bash grader

WORKDIR /app

RUN pip install --no-cache-dir pipenv==2026.0.3
COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile

COPY --chown=grader:grader app ./app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER grader

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
