FROM python:3.12-alpine

ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Устанавливаем необходимые зависимости, включая Firefox
RUN apk add --no-cache firefox

COPY pyproject.toml poetry.lock ./

# Устанавливаем pip и Poetry
RUN pip install --no-cache-dir setuptools blinker==1.7.0 poetry && \
    poetry config virtualenvs.in-project true && \
    poetry install --no-dev

COPY . ./

CMD ["poetry", "run", "python", "-m", "app", "web", "--debug"]
