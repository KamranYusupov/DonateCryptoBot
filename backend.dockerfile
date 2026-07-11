FROM python:3.12

WORKDIR /app/

ENV INSTALL_DEV=true
COPY ./app/pyproject.toml ./app/poetry.lock* /app/

RUN apt update && \
    apt install -y python3-pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry lock && \
    bash -c "if [ $INSTALL_DEV == 'true' ] ; then poetry install --no-root ; else poetry install --no-root --no-dev ; fi" && \
    apt update && apt install -y postgresql-client

COPY ./app /app
ENV PYTHONPATH=/app

