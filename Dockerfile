FROM ghcr.io/astral-sh/uv:0.9.0-bookworm

# Set working dir
WORKDIR /app

ENV PATH=/root/.local/bin:$PATH
COPY dist/*.whl /wheelhouse/
RUN uv init -p 3.12
RUN uv add `ls /wheelhouse/*.whl`
COPY misc /app/misc
RUN ls /app
ENV NLTK_DATA=/root/nltk_data
RUN uv run /app/misc/get-nltk-pack.py
ENV PATH=/app/.venv/bin:$PATH
RUN brag version

# Set environment in /app as default uv environment
ENV UV_PROJECT=/app

# Set default directory to /workspace  
WORKDIR /mnt/workspace
