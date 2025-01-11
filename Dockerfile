FROM python:3.12-bookworm
LABEL authors="hsn"
USER root

# Install Poetry
RUN pip3 install poetry

WORKDIR /app


COPY ./pyproject.toml /app/pyproject.toml

RUN poetry install --no-dev --no-root 
RUN poetry run playwright install
RUN poetry run playwright install-deps

COPY ./src /app/src
COPY ./start.py /app/start.py
COPY ./main.py /app/main.py
ENTRYPOINT ["poetry", "run", "python", "-u","start.py"]
