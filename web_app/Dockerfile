FROM python:3.9

WORKDIR /app

RUN pip install pipenv

COPY Pipfile Pipfile.lock ./
RUN pipenv install --system --deploy

COPY . .
#test for now
CMD ["python", "app/app.py"]