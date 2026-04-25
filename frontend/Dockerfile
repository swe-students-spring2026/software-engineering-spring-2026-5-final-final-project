ARG PYTHON_IMAGE_TAG=3.12-bullseye
FROM python:${PYTHON_IMAGE_TAG}
ARG FRONTEND_INTERNAL_PORT=3000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE ${FRONTEND_INTERNAL_PORT}

CMD ["python", "-m", "app.main"]
