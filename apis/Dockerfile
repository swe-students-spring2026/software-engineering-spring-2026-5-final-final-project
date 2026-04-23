ARG PYTHON_IMAGE_TAG=3.14
FROM python:${PYTHON_IMAGE_TAG}
ARG API_INTERNAL_PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE ${API_INTERNAL_PORT}

CMD ["python", "-m", "app.main"]
