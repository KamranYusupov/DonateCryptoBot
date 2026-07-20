FROM python:3.11

WORKDIR /

ENV INSTALL_DEV=true
COPY ./pyproject.toml ./poetry.lock* /

RUN apt update && \
    apt install -y python3-pip && \
    pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry lock && \
    bash -c "if [ $INSTALL_DEV == 'true' ] ; then poetry install --no-root ; else poetry install --no-root --no-dev ; fi" && \
    apt update && apt install -y postgresql-client

COPY . .
ENV PYTHONPATH=/

