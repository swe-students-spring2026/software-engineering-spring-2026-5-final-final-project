FROM python:3.11-slim

WORKDIR /app

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy Pipfile first (layer caching — only reinstalls if Pipfile changes)
COPY Pipfile .

# Install dependencies system-wide inside the container (no virtualenv needed)
RUN pipenv install --system --skip-lock
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]