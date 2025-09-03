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
