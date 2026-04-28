FROM python:3.11-slim

WORKDIR /app

# Install pipenv
RUN pip install --no-cache-dir pipenv

# Copy Pipfile first (cached layer)
COPY Pipfile Pipfile.lock ./

# Install deps into the system (not a virtualenv) — cleaner in Docker
RUN pipenv install --system --deploy

# Copy app source
COPY . .

RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]