FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
# FROM ghcr.io/astral-sh/uv:debian
# FROM continuumio/miniconda3

WORKDIR /app

# Set PATH for uv.
ENV HOME="/root"
ENV PATH="/root/.local/bin:$PATH"
ENV GRADIO_SERVER_NAME="0.0.0.0"

# Set env vars for brag.
RUN echo "CH_PORT=$CH_PORT"
ENV TOKENIZERS_PARALLELISM=true
ENV ALLOW_RESET=True
ENV ANONYMIZED_TELEMETRY=False

# Add brag source.
COPY pyproject.toml /app
COPY src /app
COPY uv.lock /app

# Instal brag.
# NOTE: To keep the environment consistent with the dev environment:
# RUN uv sync --no-dev
RUN uv tool install --from . brag

# Create the brag cache directory.
RUN mkdir -p /app/.brag
RUN mkdir -p /app/.gradio
