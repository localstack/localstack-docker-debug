FROM python:3.11-slim

WORKDIR /app
RUN python -m venv .venv
COPY setup.cfg setup.py ./
# create stub project
# TODO: consistent version
RUN mkdir dockerdebug && echo '__version__ = "0.1.0"' > dockerdebug/__init__.py
RUN /app/.venv/bin/python -m pip install -e .
COPY dockerdebug/ /app/dockerdebug/
ENTRYPOINT ["/app/.venv/bin/python"]
CMD ["-m", "dockerdebug"]
