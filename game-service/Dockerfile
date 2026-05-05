FROM python:3.12-slim

WORKDIR /app

# install deps via pipenv from Pipfile.lock; --system installs into the
# image's interpreter, --deploy aborts if the lockfile is stale.
RUN pip install --no-cache-dir pipenv==2026.0.3
COPY game-service/Pipfile game-service/Pipfile.lock ./
RUN pipenv install --system --deploy --ignore-pipfile

COPY game-service/app ./app
COPY data ./data

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
