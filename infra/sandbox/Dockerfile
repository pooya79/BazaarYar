FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    XDG_CONFIG_HOME=/tmp \
    MPLCONFIGDIR=/tmp/matplotlib

RUN apt-get update \
    && apt-get install -y --no-install-recommends tini ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install \
    pandas==3.0.0 \
    numpy==2.4.2 \
    matplotlib==3.10.8 \
    seaborn==0.13.2 \
    openpyxl==3.1.5

WORKDIR /workspace

COPY runner.py /opt/sandbox/runner.py
COPY session_runner.py /opt/sandbox/session_runner.py

RUN useradd --create-home --shell /usr/sbin/nologin sandbox \
    && chown -R sandbox:sandbox /opt/sandbox /workspace

USER sandbox

ENTRYPOINT ["/usr/bin/tini", "--", "python", "/opt/sandbox/runner.py"]
