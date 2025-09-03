help:
    just -l -u

# Lint and format code.
lint:
    uv run pre-commit run -a

[private]
install-precommit:
    uv run pre-commit install

# Update git tag and push tag. GitHub Actions will then publish to PyPI.
bump kind:
    uv run bump {{ kind }} -p
