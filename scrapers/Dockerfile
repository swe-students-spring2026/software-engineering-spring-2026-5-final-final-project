ARG PYTHON_IMAGE_TAG=3.14
FROM python:${PYTHON_IMAGE_TAG}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "scrape_bulletins.py", "--to-mongo"]
