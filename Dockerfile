FROM python:latest

ENV PYTHONUNBUFFERED 1

WORKDIR /app


RUN apt-get update
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.in-project true && \
    poetry install --no-dev

COPY . ./

CMD poetry run python -m app web --debug
