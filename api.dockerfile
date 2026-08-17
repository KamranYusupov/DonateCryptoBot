FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11

WORKDIR /

COPY ./pyproject.toml ./poetry.lock* /
RUN pip install --upgrade pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry lock && \
    poetry install --no-root

EXPOSE 8000

COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

COPY . .

WORKDIR /app

ENV PYTHONPATH=/app

ENTRYPOINT ["/entrypoint.sh"]