FROM python:3.12-slim

WORKDIR /app

ENV PIPENV_VENV_IN_PROJECT=1

RUN pip install --no-cache-dir pipenv

COPY Pipfile Pipfile.lock* ./
RUN pipenv install --skip-lock

COPY . .

EXPOSE 5000

CMD ["pipenv", "run", "python", "app.py"]
