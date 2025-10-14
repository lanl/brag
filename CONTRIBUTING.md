# Contributing

## Development tools

The following development tools are used in this project:
- `uv`
- `justfile`

You can install `uv` by following instructions from:
https://docs.astral.sh/uv/getting-started/installation/

I recommend using the Standalone Installer.

After you install `uv`, you can install `just` by `uv tool install
rust-just`.

## Linting and Formatting

You will need to lint and format your code using [`ruff`][2]. The easiest way
to automate linting/formatting of code prior to each commit is via the
[`pre-commit`][1] package, which simplifies management of git hooks.

Using `uv`, `pre-commit` will be installed in your default (dev)
environment.

To install the ruff git hook to your local `.git/hooks` folder, run
the following in the current directory:

```bash
uv run pre-commit install
```

Prior to subsequent `git commit` calls, `ruff` will first lint/format code.

Instead of running git hooks, you can lint/format code manually via running the
following in the current directory:

```bash
# Lint
ruff check --fix

# Format
ruff format
```

To continually lint while developing, you can
run the following in your terminal

```bash
ruff check --watch
```

For editor (e.g., vim, VSCode) integration, see [here][4].

You can install ruff following instructions [here][3].

If code is not linted/formatted, PRs will be blocked.

[1]: https://pre-commit.com
[2]: https://github.com/astral-sh/ruff
[3]: https://docs.astral.sh/ruff/installation
[4]: https://docs.astral.sh/ruff/editors/setup
