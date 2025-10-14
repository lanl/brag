brag-cache := ".brag"
docs := brag-cache / "docs"
name := "brag"
version := `uv run brag version --short`
tag := version + "-" + `arch`
sqfs := name + "-" + tag + ".sqfs"

help:
    just -l -u

# Lint and format code.
lint:
    uv run pre-commit run -a

# Update git tag and push tag. GitHub Actions will then publish to PyPI.
bump kind:
    uv run bump {{ kind }} -p

# Install git hooks
install-precommit:
    uv run pre-commit install

# Create binary for brag for current platform.
build:
    time uv run pyinstaller \
        --onefile $(uv run which brag) \
        -n brag-$(uv run brag version --short)-$(arch)

demo-corpus:
    mkdir -p {{ docs }}
    curl -L https://arxiv.org/pdf/1706.03762 -o {{ docs }}/attention.pdf
    curl -L https://arxiv.org/pdf/2106.05403 -o {{ docs }}/aibd.pdf
    curl -L https://www.gutenberg.org/cache/epub/1342/pg1342.txt -o {{ docs }}/pride-and-prejudice.txt

index:
    uv run brag index -d {{ docs }} --batchsize=32

index-ollama:
    uv run brag index -d {{ docs }} --emb=ollama/nomic-embed-text --batchsize=32

ask:
    uv run brag ask -d {{ docs }}

ask-ollama:
    uv run brag ask -d {{ docs }} --emb=ollama/nomic-embed-text

search:
    uv run brag search -d {{ docs }}

chat:
    uv run brag chat

[confirm("Remove index?")]
clean:
    rm -rf .brag/db

ascii:
    uvx pyfiglet -f slant brag

# Build wheel and sqfs
wcc: wheel cc

# Build wheel
[private]
wheel:
    [ ! -d "dist" ] || rm -rf dist/*.whl
    uv build .

# Build sqfs, assumes wheel exists
[private]
cc:
    #!/bin/bash
    module load charliecloud
    unset CH_IMAGE_AUTH
    ch-image build -t {{ name }}:{{ tag }} .
    ch-convert {{ name }}:{{ tag }} {{ sqfs }}

shell:
    #!/bin/bash
    module load charliecloud
    unset CH_IMAGE_AUTH
    ch-run -W {{ name }}:{{ tag }} \
            --unset-env='*' \
            --set-env \
            -- bash

shell-test:
    #!/bin/bash
    module load charliecloud
    unset CH_IMAGE_AUTH
    ch-run -W {{ name }}:{{ tag }} \
            --unset-env='*' \
            --bind tmp:/docs \
            --set-env \
            -- bash
