FROM ghcr.io/astral-sh/uv:0.9.0-bookworm

# Get current git tag
ARG GIT_TAG

# Set working dir
WORKDIR /app

# Get essentials
RUN apt update && apt install -y build-essential curl ca-certificates

# brag directories
COPY .gitignore /app/.gitignore
COPY examples /app/examples
COPY src /app/src

# brag files
COPY LICENSE.md /app
COPY README.md /app
COPY pyproject.toml /app
COPY uv.lock /app

# Sync brag environment. Use git to inform version.
RUN uv python pin 3.12
RUN git init 
RUN git add -A
RUN git commit -m 'init'
RUN git tag ${GIT_TAG}
RUN uv sync --no-cache --no-dev --locked
RUN cp /app/.venv/bin/brag /bin
RUN brag version

# Set environment in /app as default uv environment
ENV UV_PROJECT=/app

# Set default directory to /workspace  
WORKDIR /mnt/workspace
