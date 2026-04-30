FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade pip \
    && if [ -s requirements.txt ]; then python -m pip install --no-cache-dir -r requirements.txt; fi

COPY . .

CMD ["python", "app.py"]
