FROM python:3.14

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: list available schools (safe smoke-test; override CMD to run a real scrape)
CMD ["python", "scraper.py", "--list-schools"]
