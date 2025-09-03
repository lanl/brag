from argparse import (
    ArgumentDefaultsHelpFormatter,
    ArgumentParser,
    RawTextHelpFormatter,
)
from importlib.metadata import version
from textwrap import dedent

from brag.defaults import Defaults

__version__ = version("pybrag")


class BragCliFormatter(RawTextHelpFormatter, ArgumentDefaultsHelpFormatter):
    pass


def parse_args():
    defaults = Defaults()

    parser = ArgumentParser("brag")
    parser.add_argument("-v", "--version", action="store_true")

    def add_ssl_verify(subparser):
        subparser.add_argument(
            "--no-ssl-verify",
            action="store_true",
            help="if present, litellm.ssl_verify will be set to False.",
        )

    def add_llm(subparser):
        subparser.add_argument(
            "--llm",
            help=dedent(
                """\
                LLM model in litellm format (provider/model_id). e.g.,
                * openai/gpt-40-mini
                * ollama/llama3.1:8b
                * hosted_vllm/meta-llama/Llama-3.1-8B-Instruct
                """
            ),
            default="openai/gpt-4o-mini",
        )

    def add_temperature(subparser):
        # Not setting default as some openai reasoning (o1, o3, etc.) models do
        # not accept temperature.
        subparser.add_argument(
            "--temperature",
            type=float,
            help="LLM temperature.",
        )

    def add_api_key(subparser):
        subparser.add_argument(
            "--api-key",
            help=dedent(
                """\
                LLM API Key (e.g. OPENAI_API_KEY). These environment variables
                are recognized so can be omitted here:

                * OPENAI_API_KEY

                If using ollama/vllm, an api key may be required.
                """
            ),
        )

    def add_base_url(subparser):
        subparser.add_argument(
            "--base-url",
            help=dedent(
                """\
                Base url (e.g. openai base url).

                For ollama, brag automatically sets to: http://localhost:11434
                """
            ),
        )

    def add_llm_arg_parsers(subparser):
        add_llm(subparser)
        add_temperature(subparser)
        add_base_url(subparser)
        add_api_key(subparser)

    def add_emb(subparser):
        subparser.add_argument(
            "--emb",
            type=str,
            help=dedent(
                """\
                Embedding model in litellm format (provider/model_id). e.g.,
                * openai/text-embedding-3-small
                * ollama/nomic-embed-text
                * hosted_vllm/BAAI/bge-m3
                """
            ),
            default="openai/text-embedding-3-small",
        )

    def add_emb_base_url(subparser):
        subparser.add_argument(
            "--emb-base-url",
            help=dedent(
                """\
                Base url for embedder. For example, 
                * http://localhost:8001
                * http://some-random-site/

                You will have to repeat the url even if it is the same as
                --base-url.
                """
            ),
        )

    def add_emb_api_key(subparser):
        subparser.add_argument(
            "--emb-api-key",
            help=dedent(
                """\
                API key for embedder. You will have to repeat the api key even if
                it is the same as --api-key.

                These environment variables are recognized so can be omitted
                here:

                * OPENAI_API_KEY
                """
            ),
        )

    def add_emb_arg_parsers(subparser):
        add_emb(subparser)
        add_emb_api_key(subparser)
        add_emb_base_url(subparser)

    def add_log(subparser):
        subparser.add_argument("--log", help="logging level", default="WARNING")

    def add_chunksize(subparser):
        subparser.add_argument(
            "--chunk-size",
            help="chunk size for document indexing.",
            type=int,
            default=defaults.chunk_size,
        )

    def add_chunk_overlap(subparser):
        subparser.add_argument(
            "--chunk-overlap",
            help="chunk-overlap for indexing.",
            type=int,
            default=defaults.chunk_overlap,
        )

    def add_batchsize(subparser):
        subparser.add_argument(
            "--batchsize",
            help="how many document chunks to index at a time.",
            default=defaults.batch_size,
            type=int,
        )

    def add_corpus_dir(subparser):
        subparser.add_argument(
            "--corpus-dir", help="directory to corpus.", default="."
        )

    def add_db_dir(subparser):
        subparser.add_argument(
            "--db-dir",
            help="directory to save vector database.",
            default=".brag/db",
        )

    def add_db_name(subparser):
        subparser.add_argument(
            "--db-name",
            help="vector database collection name.",
            type=str,
        )

    def add_db_host(subparser):
        subparser.add_argument(
            "--db-host",
            help=dedent("""\
                        Hostname for chromadb server. If not provided and
                        --db-port is provided, this will default to 'localhost'.
                        If --db-port is not provided, this flag is ignored. 
                        """),
            type=str,
        )

    def add_db_port(subparser):
        subparser.add_argument(
            "--db-port",
            help=dedent("""\
                        Port for chromadb server. If not supplied, chromadb will
                        run locally.
                        """),
            type=int,
        )

    def add_num_retrieved_docs(subparser):
        subparser.add_argument(
            "-n",
            "--num-retrieved-docs",
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
            type=int,
            default=defaults.num_retrieved_docs,
        )

    def add_no_cache_db(subparser):
        subparser.add_argument(
            "--no-cache-db",
            action="store_true",
            help="if present, vector database is stored in memory and is NOT saved.",
        )

    # Sub commands.
    parsers = parser.add_subparsers(dest="command", required=False)

    # Delete index.
    rm_index_parser = parsers.add_parser(
        "rm-index",
        help="Delete a ChromaDB collection.",
        formatter_class=BragCliFormatter,
    )
    add_db_dir(rm_index_parser)
    add_db_name(rm_index_parser)
    add_db_host(rm_index_parser)
    add_db_port(rm_index_parser)
    add_log(rm_index_parser)
    rm_index_parser.add_argument(
        "--reset",
        action="store_true",
        help="If present, all collections in vector database are removed.",
    )

    # Index a directory of documents.
    index_parser = parsers.add_parser(
        "index",
        help="index a directory of docs.",
        formatter_class=BragCliFormatter,
    )
    add_api_key(index_parser)
    add_base_url(index_parser)
    add_emb_arg_parsers(index_parser)
    add_corpus_dir(index_parser)
    add_db_dir(index_parser)
    add_db_name(index_parser)
    add_db_host(index_parser)
    add_db_port(index_parser)
    add_batchsize(index_parser)
    add_chunksize(index_parser)
    add_chunk_overlap(index_parser)
    add_log(index_parser)
    add_ssl_verify(index_parser)
    index_parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="whether or not to overwrite existing vector database.",
    )

    # Ask about a corpus.
    # llm, temperature, base_url, api_key, log
    ask_parser = parsers.add_parser(
        "ask",
        help=dedent(
            """\
            Ask questions about a corpus. Vectorstore will update when `ask` is
            invoked. Files that are in corpus, but not indexed will be indexed.
            Files that are indexed but not in corpus will be removed. Files
            that were modified after indexed will be re-indexed. 
            """
        ),
        formatter_class=BragCliFormatter,
    )

    add_llm_arg_parsers(ask_parser)
    add_corpus_dir(ask_parser)
    add_emb_arg_parsers(ask_parser)
    add_chunksize(ask_parser)
    add_chunk_overlap(ask_parser)
    add_batchsize(ask_parser)
    add_db_dir(ask_parser)
    add_db_name(ask_parser)
    add_db_host(ask_parser)
    add_db_port(ask_parser)
    add_num_retrieved_docs(ask_parser)
    add_no_cache_db(ask_parser)
    add_ssl_verify(ask_parser)
    add_log(ask_parser)

    ask_parser.add_argument(
        "--rag-type",
        choices=["brag", "trag"],
        help=dedent(
            """\
            * brag (basic rag, which does not use tool calling)
            * trag (tool-calling rag)
            """
        ),
        default="brag",
    )
    ask_parser.add_argument(
        "-p",
        "--port",
        help="port to serve web app. If not supplied, runs only in terminal.",
        type=int,
    )

    ask_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help=dedent(
            """\
            Whether or not to show rag sources. If present, sources will be
            shown in command line. Sources can still be recovered via !cite.
            However, sources are always presented in the web app.
            """
        ),
        default=False,
    )

    ask_parser.add_argument(
        "--system-prompt",
        type=str,
        help=dedent(
            """\
            System prompt to use. Overriden if --system-prompt-path is supplied.
              * basic: answers based only on context.
              * mindful: answers based on context and llm's knowledge
            """
        ),
        choices=["basic", "mindful"],
        default="basic",
    )

    ask_parser.add_argument(
        "--system-prompt-path",
        type=str,
        help=dedent(
            """\
            Optional path to system prompt. The system prompt should be in a
            text file. If supplied, the --system-prompt flag will have no
            effect. If not supplied, then --system-prompt is applied.

            Example usage:
                brag ask --system-prompt-path=prompt.txt
            """
        ),
    )

    # Search within a corpus.
    search_parser = parsers.add_parser(
        "search",
        help="search within a corpus.",
        formatter_class=BragCliFormatter,
    )
    add_corpus_dir(search_parser)
    add_emb_arg_parsers(search_parser)
    add_chunksize(search_parser)
    add_chunk_overlap(search_parser)
    add_batchsize(search_parser)
    add_db_name(search_parser)
    add_db_dir(search_parser)
    add_db_host(search_parser)
    add_db_port(search_parser)
    add_num_retrieved_docs(search_parser)
    add_no_cache_db(search_parser)
    add_ssl_verify(search_parser)
    add_log(search_parser)

    # Chat.
    chat_parser = parsers.add_parser(
        "chat",
        help="chat with a bot.",
        formatter_class=BragCliFormatter,
    )
    add_llm_arg_parsers(chat_parser)
    add_ssl_verify(chat_parser)
    add_log(chat_parser)

    return parser.parse_args(), parser
