FROM ghcr.io/astral-sh/uv:0.9.0-bookworm

ENV PATH=/root/.local/bin:$PATH
COPY dist/*.whl /wheelhouse/
RUN uv tool install `ls /wheelhouse/*.whl`
RUN brag version

# Set default directory to /workspace  
WORKDIR /mnt/workspace
