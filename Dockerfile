FROM python:3.11-slim

WORKDIR /app
RUN python -m venv ./.venv
COPY setup.py setup.cfg ./
COPY dockerdebug/__init__.py ./dockerdebug/__init__.py
RUN ./.venv/bin/python -m pip install -e .

COPY dockerdebug ./dockerdebug
ENTRYPOINT ["./.venv/bin/python", "-m", "dockerdebug"]
