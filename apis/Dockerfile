ARG PYTHON_IMAGE_TAG=3.14
FROM python:${PYTHON_IMAGE_TAG}
ARG API_INTERNAL_PORT=8000

WORKDIR /app

COPY apis/requirements.txt ./apis/requirements.txt
RUN pip install --no-cache-dir -r ./apis/requirements.txt

COPY apis ./apis
COPY scrapers ./scrapers

EXPOSE ${API_INTERNAL_PORT}

CMD ["python", "-m", "apis.app.main"]
