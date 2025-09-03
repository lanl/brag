help:
    just -l -u

lint:
    uv run pre-commit run -a

[private]
install-precommit:
    uv run pre-commit install
