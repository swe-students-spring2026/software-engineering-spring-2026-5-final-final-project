FROM python:3.12-slim

WORKDIR /app

# Install dependencies so Docker can reuse this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# Start the Flask app when the container runs
CMD ["python", "app.py"]
