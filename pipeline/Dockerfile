FROM python:3.12-slim

WORKDIR /app

# Install deps first so Docker can cache this layer between builds
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run_pipeline.py"]
