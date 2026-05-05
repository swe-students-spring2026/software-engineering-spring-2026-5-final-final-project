FROM python:3.12-slim
WORKDIR /app

COPY requirements.txt ./

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["gunicorn", "-b","0.0.0.0:5001", "app:app"]