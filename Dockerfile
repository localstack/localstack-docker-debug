FROM python:3.11-slim

# Install helful tools for debugging even without using the
# python package
RUN apt-get update && \
        apt-get install -y \
            curl \
            iproute2 \
            dnsutils \
            netcat-traditional \
            nmap \
            jq \
            openssl \
            graphviz \
            tini \
        && apt-get clean && rm -rf /var/lib/apt/lists/*

# So we can identify ourselves later with probe mode
LABEL cloud.localstack.dockerdebug.name=dockerdebug

WORKDIR /app
RUN python -m venv .venv
COPY setup.cfg setup.py ./
# create stub project
# TODO: consistent version
RUN mkdir dockerdebug && echo '__version__ = "0.1.0"' > dockerdebug/__init__.py
RUN /app/.venv/bin/python -m pip install -e .
COPY dockerdebug/ /app/dockerdebug/
ENTRYPOINT ["/usr/bin/tini", "--", "/app/.venv/bin/python", "-m", "dockerdebug"]
