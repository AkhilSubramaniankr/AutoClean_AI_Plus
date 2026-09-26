# syntax=docker/dockerfile:1
#
# Multi-stage build for AutoClean AI+.
# See docs/phase_deliverables/Phase3_Environment_Setup.md, Section 7, for the
# base-image and multi-stage-build decisions.

# ---------------------------------------------------------------------------
# Stage 1: builder -- installs dependencies into a virtual environment
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build

# System build dependencies for packages with native extensions
# (e.g. numpy/scipy/pandas wheels are usually prebuilt, but this keeps the
# build resilient across architectures where prebuilt wheels are unavailable).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: runtime -- copies only the venv + source into a slim final image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    AUTOCLEAN_ENVIRONMENT=production

# Run as a non-root user (defense in depth; no reason this process needs root)
RUN useradd --create-home --uid 1000 autoclean
WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --chown=autoclean:autoclean . .

RUN mkdir -p data/uploads data/cleaned data/reports data/scripts logs \
    && chown -R autoclean:autoclean data logs

USER autoclean

EXPOSE 8501

# Basic container-level healthcheck against Streamlit's own health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

ENTRYPOINT ["streamlit", "run", "src/autoclean/presentation/streamlit_app.py"]
CMD ["--server.port=8501", "--server.address=0.0.0.0"]
