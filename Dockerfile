FROM ghcr.io/astral-sh/uv:0.9.0-bookworm

# Set working dir
WORKDIR /app

ENV PATH=/root/.local/bin:$PATH
COPY dist/*.whl /wheelhouse/
RUN uv init -p 3.12
RUN uv add `ls /wheelhouse/*.whl`
# ENV NLTK_DATA=/root/nltk_data
# RUN uv run python -c "import nltk; nltk.download('punkt_tab'); nltk.download('popular'); nltk.download('averaged_perceptron_tagger_eng')"
COPY misc /app/misc
RUN ls /app
RUN uv run /app/misc/get-nltk-pack.py
ENV PATH=/app/.venv/bin:$PATH
RUN brag version

# Set environment in /app as default uv environment
ENV UV_PROJECT=/app

# Set default directory to /workspace  
WORKDIR /mnt/workspace
