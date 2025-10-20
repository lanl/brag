"""Basic RAG (brag)."""

# NOTE: Putting the import statements near usage decreases time taken to
# generate help menus.

import logging
import sys
from importlib.metadata import version
from pathlib import Path
from textwrap import dedent
from typing import Annotated, Literal, Optional

from typer import Option, Typer

__version__ = version("pybrag")


def set_logging(log_level: str):
    numeric_level = getattr(logging, log_level.upper(), None)
    logging.basicConfig(
        level=numeric_level, format="[BRAG-%(levelname)s] %(message)s"
    )


app = Typer()


@app.command()
def index(
    docs_dir: Annotated[
        Path,
        Option(
            "-d",
            "--dir",
            help="Directory containing documents. Must be a flat directory. Hidden files will not be indexed.",
        ),
    ] = Path("."),
    emb: Annotated[
        str,
        Option(
            help=dedent(
                """\
                Embedding model in litellm format (provider/model_id). e.g.,
                * openai/text-embedding-3-small
                * ollama/nomic-embed-text
                * hosted_vllm/BAAI/bge-m3
                """
            )
        ),
    ] = "openai/text-embedding-3-small",
    emb_base_url: Annotated[
        Optional[str],
        Option(
            help=dedent(
                """\
                Base url for embedder. For example, 
                * https://api.openai.com/v1 (openai)
                * http://localhost:11434/v1 (ollama)
                """
            )
        ),
    ] = None,
    emb_api_key: Annotated[
        Optional[str],
        Option(
            envvar=["BRAG_EMB_API_KEY", "OPENAI_API_KEY"],
            help="API key for embedder",
        ),
    ] = None,
    chunk_size: Annotated[
        int, Option(help="Document chunksize for embedding documents")
    ] = 1000,
    chunk_overlap: Annotated[
        int, Option(help="Document chunk overlap for embedding documents")
    ] = 100,
    batchsize: Annotated[int, Option(help="Batchsize for embedding")] = 10,
    ssl_verify: Annotated[
        bool, Option(help="Whether or not to enable ssl checks")
    ] = True,
    db_dir: Annotated[
        Path, Option("--db", help="Directory to store vector database")
    ] = Path(".brag") / "db",
    db_name: Annotated[
        str, Option(help="Database collection name")
    ] = "brag-db",
    db_host: Annotated[
        Optional[str],
        Option(
            help=dedent("""\
                Hostname for chromadb server. If not provided and
                --db-port is provided, this will default to 'localhost'.
                If --db-port is not provided, this flag is ignored. 
                """)
        ),
    ] = None,
    db_port: Annotated[
        Optional[int],
        Option(
            help=dedent("""\
                Port for chromadb server. If not supplied, chromadb will
                run locally.
                """)
        ),
    ] = None,
    log_level: str = "WARNING",
    min_space_to_bang: Annotated[
        int,
        Option(
            help=dedent(
                """\
                Some documents are '!' delimited instead of ' ' delimited. This
                messes with some vector embedders.  This option attempts to
                infer whether such a case has occured by computing the ratio of
                ' ' to '!'. By default, if '!' absolutely shows up more
                frequently than ' ', then all ' ' will be replaced by '!'.
                min_space_to_bang can be user specified.  If not specified, will
                default to 1, which implies a 1:1 ratio is acceptable (but 1:2,
                1:3, etc is not).
                """
            )
        ),
    ] = 1,
):
    import litellm

    from brag.db import Database
    from brag.emb import LiteLLMEmbeddings

    if not ssl_verify:
        litellm.ssl_verify = False

    set_logging(log_level)

    db_dir.mkdir(parents=True, exist_ok=True)

    embedder = LiteLLMEmbeddings(
        model=emb,
        api_base=emb_base_url,
        api_key=emb_api_key,
    )
    Database(
        corpus_dir=Path(docs_dir),
        embedder=embedder,
        index_doc_batch_size=batchsize,
        chunk_overlap=chunk_overlap,
        chunk_size=chunk_size,
        cache_db=True,
        db_dir=str(db_dir),
        db_name=db_name,
        db_host=db_host,
        db_port=db_port,
        min_space_to_bang=min_space_to_bang,
    )


@app.command()
def ask(
    docs_dir: Annotated[
        Path,
        Option(
            "-d",
            "--dir",
            help=(
                "Directory containing documents. Must be a flat directory. "
                "Hidden files will not be indexed."
            ),
        ),
    ] = Path("."),
    llm: Annotated[
        str,
        Option(
            help=dedent(
                """\
                LLM in litellm format (provider/model_id). e.g.,
                * openai/o3
                * ollama/gpt-oss:120b
                * hosted_vllm/meta-llama/Llama-3.1-8B-Instruct
                """
            )
        ),
    ] = "openai/o3",
    llm_base_url: Annotated[
        Optional[str],
        Option(
            help=dedent(
                """\
                Base url for embedder. For example, 
                * https://api.openai.com/v1 (openai)
                * http://localhost:11434/v1 (ollama)
                """
            )
        ),
    ] = None,
    llm_api_key: Annotated[
        Optional[str],
        Option(
            envvar=["BRAG_LLM_API_KEY", "OPENAI_API_KEY"],
            help="API key for embedder",
        ),
    ] = None,
    temperature: Annotated[
        Optional[float], Option(help="Temperature for LLM.", max=1.0, min=0.0)
    ] = None,
    max_completion_tokens: Optional[int] = None,
    max_tokens: Optional[int] = None,
    emb: Annotated[
        str,
        Option(
            help=dedent(
                """\
                Embedding model in litellm format (provider/model_id). e.g.,
                * openai/text-embedding-3-small
                * ollama/nomic-embed-text
                * hosted_vllm/BAAI/bge-m3
                """
            )
        ),
    ] = "openai/text-embedding-3-small",
    emb_base_url: Annotated[
        Optional[str],
        Option(
            help=dedent(
                """\
                Base url for embedder. For example, 
                * https://api.openai.com/v1 (openai)
                * http://localhost:11434/v1 (ollama)
                """
            )
        ),
    ] = None,
    emb_api_key: Annotated[
        Optional[str],
        Option(
            envvar=["BRAG_EMB_API_KEY", "OPENAI_API_KEY"],
            help="API key for embedder",
        ),
    ] = None,
    chunk_size: Annotated[
        int, Option(help="Document chunksize for embedding documents")
    ] = 1000,
    chunk_overlap: Annotated[
        int, Option(help="Document chunk overlap for embedding documents")
    ] = 100,
    batchsize: Annotated[int, Option(help="Batchsize for embedding")] = 10,
    ssl_verify: Annotated[
        bool, Option(help="Whether or not to enable ssl checks")
    ] = True,
    db_dir: Annotated[
        Path, Option("--db", help="Directory to store vector database")
    ] = Path(".brag") / "db",
    db_name: Annotated[
        str, Option(help="Database collection name")
    ] = "brag-db",
    db_host: Annotated[
        Optional[str],
        Option(
            help=dedent("""\
                Hostname for chromadb server. If not provided and
                --db-port is provided, this will default to 'localhost'.
                If --db-port is not provided, this flag is ignored. 
                """)
        ),
    ] = None,
    db_port: Annotated[
        Optional[int],
        Option(
            help=dedent("""\
                Port for chromadb server. If not supplied, chromadb will
                run locally.
                """)
        ),
    ] = None,
    cache_db: Annotated[
        bool,
        Option(
            help="Whether or not to store vector database to disk",
        ),
    ] = True,
    num_retrieved_docs: Annotated[
        Optional[int],
        Option(
            help=dedent(
                """\
                number of document chunks to retrieve. Recommendation: Use an
                LLM with a context window of at least 65K (e.g. the llama3.1,
                llama3.2, llama3.3.).  Number of retrieved documents should
                result in approx 5000-6000 chunks.  e.g. if using a chunksize of
                340, using about 15 retrieved docs would result in ~5100 chunks.
                batchsize * chunksize should be about 50000 chunks.  So if using
                a chunksize of 340, use a batch size of about 147.
                """
            ),
        ),
    ] = 10,
    rag_type: Annotated[
        Literal["brag", "trag"],
        Option(
            help="Port to serve web app. If not supplied, runs only in terminal."
        ),
    ] = "brag",
    port: Annotated[
        Optional[int],
        Option(
            help="Port to serve web app. If not supplied, runs only in terminal."
        ),
    ] = None,
    system_prompt_path: Annotated[
        Optional[Path],
        Option(
            help=dedent("""\
            Optional path to system prompt. The system prompt should be in a
            text file. If supplied, the --system-prompt flag will have no
            effect. If not supplied, then --system-prompt is applied.

            Example usage:
                brag ask --system-prompt-path=prompt.txt
            """),
        ),
    ] = None,
    system_prompt: Annotated[
        Literal["basic", "mindful"],
        Option(
            help=dedent("""\
            System prompt to use. Overriden if --system-prompt-path is supplied.
              * basic: answers based only on context.
              * mindful: answers based on context and llm's knowledge
            """)
        ),
    ] = "basic",
    verbose: Annotated[
        bool,
        Option(
            help=dedent(
                """\
            Whether or not to show rag sources. If present, sources will be
            shown in command line. Sources can still be recovered via !cite.
            However, sources are always presented in the web app.
            """
            ),
        ),
    ] = False,
    log_level: str = "WARNING",
    min_space_to_bang: Annotated[
        int,
        Option(
            help=dedent(
                """\
                Some documents are '!' delimited instead of ' ' delimited. This
                messes with some vector embedders.  This option attempts to
                infer whether such a case has occured by computing the ratio of
                ' ' to '!'. By default, if '!' absolutely shows up more
                frequently than ' ', then all ' ' will be replaced by '!'.
                min_space_to_bang can be user specified.  If not specified, will
                default to 1, which implies a 1:1 ratio is acceptable (but 1:2,
                1:3, etc is not).
                """
            )
        ),
    ] = 1,
    skip_index: Annotated[
        bool, Option(help="If False, skips indexing -- even if out of sync.")
    ] = False,
):
    import litellm
    from langchain_litellm import ChatLiteLLM

    from brag.db import Database
    from brag.emb import LiteLLMEmbeddings

    if not ssl_verify:
        litellm.ssl_verify = False

    set_logging(log_level)

    chat_model = ChatLiteLLM(
        model=llm,
        api_key=llm_api_key,
        api_base=llm_base_url,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,
        max_tokens=max_tokens,
    )
    logging.info(f"Embedder: {emb}, base url: {emb_base_url}")

    embedder = LiteLLMEmbeddings(
        model=emb,
        api_base=emb_base_url,
        api_key=emb_api_key,
    )

    db = Database(
        corpus_dir=Path(docs_dir),
        embedder=embedder,
        index_doc_batch_size=batchsize,
        num_retrieved_docs=num_retrieved_docs,
        chunk_overlap=chunk_overlap,
        chunk_size=chunk_size,
        cache_db=cache_db,
        db_dir=str(db_dir),
        db_name=db_name,
        db_host=db_host,
        db_port=db_port,
        # Always show sources for web app.
        terminal=port is None,
        min_space_to_bang=min_space_to_bang,
        skip_index=skip_index,
    )
    match rag_type:
        case "brag":
            from brag.rags import Brag

            ChosenRag = Brag
        case "trag":
            from brag.rags import Trag

            ChosenRag = Trag

    match system_prompt_path, system_prompt:
        case None, "basic":
            from brag.rags.abstract import RAG_SYSTEM_PROMPT

            _system_prompt = RAG_SYSTEM_PROMPT
        case None, "mindful":
            from brag.rags.abstract import MINDFUL_RAG_SYSTEM_PROMPT

            _system_prompt = MINDFUL_RAG_SYSTEM_PROMPT
        case Path(), _:  # system_prompt_path is supplied.
            logging.debug(
                f"system_prompt_path is supplied and is:{system_prompt_path}"
            )
            _system_prompt = system_prompt_path.read_text()
            logging.debug(_system_prompt)

    rag = ChosenRag(
        chat_model,
        db,
        thread_id=None,
        system_prompt=_system_prompt,
        # Always show sources for web app.
        verbose=verbose or port is not None,
    )
    if port:
        from brag.ui import serve

        serve(rag, llm_name=llm, corpus_dir=docs_dir, port=port)
    else:
        from brag.repl import AskREPL

        AskREPL().run(
            "Ask questions about your corpus!",
            rag.print_ask,
        )


@app.command()
def search(
    docs_dir: Annotated[
        Path,
        Option(
            "-d",
            "--dir",
            help="Directory containing documents. Must be a flat directory. Hidden files will not be indexed.",
        ),
    ] = Path("."),
    emb: Annotated[
        str,
        Option(
            help=dedent(
                """\
                Embedding model in litellm format (provider/model_id). e.g.,
                * openai/text-embedding-3-small
                * ollama/nomic-embed-text
                * hosted_vllm/BAAI/bge-m3
                """
            )
        ),
    ] = "openai/text-embedding-3-small",
    emb_base_url: Annotated[
        Optional[str],
        Option(
            help=dedent(
                """\
                Base url for embedder. For example, 
                * https://api.openai.com/v1 (openai)
                * http://localhost:11434/v1 (ollama)
                """
            )
        ),
    ] = None,
    emb_api_key: Annotated[
        Optional[str],
        Option(
            envvar=["BRAG_EMB_API_KEY", "OPENAI_API_KEY"],
            help="API key for embedder",
        ),
    ] = None,
    chunk_size: Annotated[
        int, Option(help="Document chunksize for embedding documents")
    ] = 1000,
    chunk_overlap: Annotated[
        int, Option(help="Document chunk overlap for embedding documents")
    ] = 100,
    batchsize: Annotated[int, Option(help="Batchsize for embedding")] = 10,
    ssl_verify: Annotated[
        bool, Option(help="Whether or not to enable ssl checks")
    ] = True,
    db_dir: Annotated[
        Path, Option("--db", help="Directory to store vector database")
    ] = Path(".brag") / "db",
    db_name: Annotated[
        str, Option(help="Database collection name")
    ] = "brag-db",
    db_host: Annotated[
        Optional[str],
        Option(
            help=dedent("""\
                Hostname for chromadb server. If not provided and
                --db-port is provided, this will default to 'localhost'.
                If --db-port is not provided, this flag is ignored. 
                """)
        ),
    ] = None,
    db_port: Annotated[
        Optional[int],
        Option(
            help=dedent("""\
                Port for chromadb server. If not supplied, chromadb will
                run locally.
                """)
        ),
    ] = None,
    cache_db: Annotated[
        bool,
        Option(
            help="Whether or not to store vector database to disk",
        ),
    ] = True,
    num_retrieved_docs: Annotated[
        Optional[int],
        Option(
            help=dedent(
                """\
                number of document chunks to retrieve. Recommendation: Use an
                LLM with a context window of at least 65K (e.g. the llama3.1,
                llama3.2, llama3.3.).  Number of retrieved documents should
                result in approx 5000-6000 chunks.  e.g. if using a chunksize of
                340, using about 15 retrieved docs would result in ~5100 chunks.
                batchsize * chunksize should be about 50000 chunks.  So if using
                a chunksize of 340, use a batch size of about 147.
                """
            ),
        ),
    ] = 10,
    log_level: str = "WARNING",
    min_space_to_bang: Annotated[
        int,
        Option(
            help=dedent(
                """\
                Some documents are '!' delimited instead of ' ' delimited. This
                messes with some vector embedders.  This option attempts to
                infer whether such a case has occured by computing the ratio of
                ' ' to '!'. By default, if '!' absolutely shows up more
                frequently than ' ', then all ' ' will be replaced by '!'.
                min_space_to_bang can be user specified.  If not specified, will
                default to 1, which implies a 1:1 ratio is acceptable (but 1:2,
                1:3, etc is not).
                """
            )
        ),
    ] = 1,
    skip_index: Annotated[
        bool, Option(help="If False, skips indexing -- even if out of sync.")
    ] = False,
    query: Annotated[
        Optional[str],
        Option(
            "-q",
            "--query",
            help=(
                "Optional query. If provided, then search results are "
                "immediately printed in non-interactive mode (i.e., "
                "not in brag REPL) as json."
            ),
        ),
    ] = None,
):
    import litellm

    from brag.db import Database
    from brag.emb import LiteLLMEmbeddings
    from brag.repl import BragREPL

    set_logging(log_level)
    if not ssl_verify:
        litellm.ssl_verify = False

    embedder = LiteLLMEmbeddings(
        model=emb,
        api_base=emb_base_url,
        api_key=emb_api_key,
    )

    db = Database(
        corpus_dir=docs_dir,
        embedder=embedder,
        index_doc_batch_size=batchsize,
        num_retrieved_docs=num_retrieved_docs,
        chunk_overlap=chunk_overlap,
        chunk_size=chunk_size,
        cache_db=cache_db,
        db_dir=str(db_dir),
        db_name=db_name,
        db_host=db_host,
        db_port=db_port,
        terminal=True,
        min_space_to_bang=min_space_to_bang,
        skip_index=skip_index,
    )

    if query is None:
        # Interactive mode.
        def print_results(_query: str):
            print(db.retrieve(_query, None))

        BragREPL().run("Begin searching your corpus!", print_results)
    else:
        # Non-interactive mode.
        import json

        from rich import print_json

        result = db.retrieve_as_dict(query, None)
        result_json = json.dumps(dict(result=result), indent=4)
        print_json(result_json)
        sys.exit()


@app.command()
def chat(
    llm: Annotated[
        str,
        Option(
            help=dedent(
                """\
                LLM in litellm format (provider/model_id). e.g.,
                * openai/o3
                * ollama/gpt-oss:120b
                * hosted_vllm/meta-llama/Llama-3.1-8B-Instruct
                """
            )
        ),
    ] = "openai/o3",
    llm_base_url: Annotated[
        Optional[str],
        Option(
            help=dedent(
                """\
                Base url for embedder. For example, 
                * https://api.openai.com/v1 (openai)
                * http://localhost:11434/v1 (ollama)
                """
            )
        ),
    ] = None,
    llm_api_key: Annotated[
        Optional[str],
        Option(
            envvar=["BRAG_LLM_API_KEY", "OPENAI_API_KEY"],
            help="API key for embedder",
        ),
    ] = None,
    temperature: Annotated[
        Optional[float], Option(help="Temperature for LLM.", max=1.0, min=0.0)
    ] = None,
    max_completion_tokens: Optional[int] = None,
    max_tokens: Optional[int] = None,
    ssl_verify: Annotated[
        bool, Option(help="Whether or not to enable ssl checks")
    ] = True,
):
    import litellm
    from langchain_litellm import ChatLiteLLM

    from brag.chat import Chatbot
    from brag.repl import BragREPL

    if not ssl_verify:
        litellm.ssl_verify = False

    chat_model = ChatLiteLLM(
        model=llm,
        api_base=llm_base_url,
        api_key=llm_api_key,
        temperature=temperature,
        max_completion_tokens=max_completion_tokens,
        max_tokens=max_completion_tokens,
    )
    chatbot = Chatbot(chat_model)
    BragREPL().run(f"Begin chatting with {llm} ", chatbot.print_stream)


@app.command()
def rm_index(
    db_dir: Annotated[
        Path, Option("--db", help="Directory to store vector database")
    ] = Path(".brag") / "db",
    db_name: Annotated[
        str, Option(help="Database collection name")
    ] = "brag-db",
    db_host: Annotated[
        Optional[str],
        Option(
            help=dedent("""\
                Hostname for chromadb server. If not provided and
                --db-port is provided, this will default to 'localhost'.
                If --db-port is not provided, this flag is ignored. 
                """)
        ),
    ] = None,
    db_port: Annotated[
        Optional[int],
        Option(
            help=dedent("""\
                Port for chromadb server. If not supplied, chromadb will
                run locally.
                """)
        ),
    ] = None,
    reset: Annotated[
        bool,
        Option(
            help="If present, all collections in vector database are removed.",
        ),
    ] = False,
    log_level: str = "WARNING",
):
    from chromadb import HttpClient, PersistentClient
    from chromadb.config import Settings

    set_logging(log_level)

    # Recursively remove db dir.
    local_files_to_remove = [
        db_dir / "corpus_mtimes.sqlite3",
        db_dir / "index-info.txt",
    ]
    for file in local_files_to_remove:
        try:
            file.unlink()
            logging.info(f"Successfully deleted '{file}'.")
        except FileNotFoundError:
            logging.info(f"{file} was not found.")

    # Remove collection if needed.
    settings = Settings(allow_reset=True)
    if db_port is None:
        client = PersistentClient(path=str(db_dir), settings=settings)
    else:
        host = db_host or "localhost"
        client = HttpClient(host=host, port=db_port, settings=settings)

    try:
        # FIXME: the actual directories aren't removed, though the
        # collections are no longer associated. This could lead to large
        # disk space consumption.
        print(
            "Number of collections (before):",
            client.count_collections(),
        )

        client.delete_collection(name=db_name)
        if reset:
            print("HERE")
            client.reset()

        print(
            "Number of collections (after):",
            client.count_collections(),
        )

        logging.info(f"Collection '{db_name}' deleted successfully.")
    except ValueError:
        logging.info(
            f"Collection '{db_name}' was not found at {host}:{db_port}."
        )


@app.command()
def version(short: bool = False):
    if short:
        print(__version__)
    else:
        print(f"brag version {__version__}")


@app.command()
def update_db():
    print("WIP")


def main():
    app()
