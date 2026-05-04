FROM python:3.10-slim

WORKDIR /app

COPY Pipfile Pipfile.lock ./
RUN python -m pip install --no-cache-dir --upgrade pip pipenv \
    && pipenv install --system --deploy

COPY . .

CMD ["python", "-m", "app.main"]
