# BRAG

[![PyPI Version][pypi-version]](https://pypi.org/project/pybrag/)
[![PyPI Downloads][pypi-downloads]](https://pypistats.org/packages/pybrag)

**B**asic **RAG** that can be used in a browser or command line.

## Installation
With pip:
```console
pip install pybrag
```

```console
# Test that brag was properly installed
brag --help
```

With uv:
```console
uv add pybrag
```

```
# Test that brag was properly installed
uv run brag --help
```

With uv, you can install brag as a command line tool by:
```console
uv tool install pybrag
```

```console
# Test that brag was properly installed
brag --help
```

## Usage

Ask questions, interactively, about a corpus of documents in a terminal.
(Currently, the supported file types are `pdf`, `txt`, and `md`.)
```console
brag ask --corpus-dir path/to/my/corpus/of/documents
```

For more options
```console
brag ask --help
```

and
```
brag --help
```

If you want to run in a browser, set `port`.
```console
brag ask --corpus-dir path/to/my/corpus/of/documents --port=8000
```

Then view the web app at `http://localhost:8000`.

## Advanced Usage
[LiteLLM](https://docs.litellm.ai/docs/) is used to support the use of
different LLM providers in brag.  Models are specified as `provider/model-id`.
For example, to use OpenAI's `gpt-4o-mini`, you can supply
`--llm=openai/gpt-4o-mini` to `brag ask`. You can supply your openai api key
via `--api-key` or set `OPENAI_API_KEY` in your shell.

With `brag ask`, you can use different providers for the language and embedding
models.  For example, say with `brag ask` you want to use as the LLM
`Llama-3.1-8b` served via vllm, and `nomic-embed-text` as the embedding model
served via ollama, you can run:

```console
brag ask --corpus-dir <path-to-corpus> \
    --llm "hosted_vllm/meta-llama/Llama-3.1-8B-Instruct" \
    --emb "ollama/nomic-embed-text" \
    --base-url="http://localhost:8200"
```

This assumes that vllm is served on port 8200 on localhost and ollama is served
at port 11434. You can also explicitly specify the port for ollama if served
elsewhere. E.g.,

```console
brag ask --corpus-dir <path-to-corpus> \
    --llm "hosted_vllm/meta-llama/Llama-3.1-8B-Instruct" \
    --emb "ollama/nomic-embed-text" \
    --base-url="http://localhost:8200"
    --emb-base-url="http://localhost:8201"
```


For all available options, run `brag ask --help`

***

© 2025. Triad National Security, LLC. All rights reserved.

This program was produced under U.S. Government contract 89233218CNA000001 for
Los Alamos National Laboratory (LANL), which is operated by Triad National
Security, LLC for the U.S. Department of Energy/National Nuclear Security
Administration. All rights in the program are reserved by Triad National
Security, LLC, and the U.S. Department of Energy/National Nuclear Security
Administration. The Government is granted for itself and others acting on its
behalf a nonexclusive, paid-up, irrevocable worldwide license in this material
to reproduce, prepare derivative works, distribute copies to the public,
perform publicly and display publicly, and to permit others to do so.

LANL Software Release **O4983**

[pypi-version]: https://img.shields.io/pypi/v/pybrag?style=flat-square&label=PyPI
[pypi-downloads]: https://img.shields.io/pypi/dm/pybrag?style=flat-square&label=Downloads&color=blue
