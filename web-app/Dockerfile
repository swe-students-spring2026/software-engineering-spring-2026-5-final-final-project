FROM python:3.10-slim

WORKDIR /app

COPY Pipfile* ./
RUN python -m pip install --no-cache-dir --upgrade pip pipenv \
    && if [ -f Pipfile.lock ]; then pipenv sync --system; else pipenv install --system --skip-lock; fi

COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

COPY . .

EXPOSE 8080

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8080} main:app"]
