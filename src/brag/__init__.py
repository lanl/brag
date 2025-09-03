"""Basic RAG (brag)."""

# NOTE: Putting the import statements near usage decreases time taken to
# generate help menus.

import logging
from pathlib import Path

from brag.parse_args import __version__, parse_args


def main():
    """Cli entry point."""
    args, parser = parse_args()

    if args.version:
        print(f"brag version {__version__}")
        exit()

    if args.command is None:
        parser.print_help()
        exit()

    # Set logging.
    numeric_level = getattr(logging, args.log.upper(), None)
    logging.basicConfig(
        level=numeric_level, format="[BRAG-%(levelname)s] %(message)s"
    )
    logging.debug(args)

    # from brag.util import make_emb, make_llm
    import litellm
    from langchain_litellm import ChatLiteLLM

    from brag.emb import LiteLLMEmbeddings

    match args.command:
        case "index":
            from brag.db import Database

            if args.no_ssl_verify:
                litellm.ssl_verify = False

            embedder = LiteLLMEmbeddings(
                model=args.emb,
                api_base=args.emb_base_url,
                api_key=args.emb_base_key,
            )
            Database(
                corpus_dir=Path(args.corpus_dir),
                embedder=embedder,
                index_doc_batch_size=args.batchsize,
                chunk_overlap=args.chunk_overlap,
                chunk_size=args.chunk_size,
                cache_db=True,
                db_dir=args.db_dir,
                db_name=args.db_name,
                db_host=args.db_host,
                db_port=args.db_port,
            )

        case "update-db":
            logging.warning("update-db (WIP)")

        case "ask":
            from brag.db import Database

            if args.no_ssl_verify:
                litellm.ssl_verify = False

            logging.info(args)
            llm = ChatLiteLLM(
                model=args.llm,
                api_key=args.api_key,
                api_base=args.base_url,
                temperature=args.temperature,
            )
            logging.info(f"Embedder: {args.emb}, base url: {args.emb_base_url}")

            embedder = LiteLLMEmbeddings(
                model=args.emb,
                api_base=args.emb_base_url,
                api_key=args.emb_api_key,
            )

            db = Database(
                corpus_dir=Path(args.corpus_dir),
                embedder=embedder,
                index_doc_batch_size=args.batchsize,
                num_retrieved_docs=args.num_retrieved_docs,
                chunk_overlap=args.chunk_overlap,
                chunk_size=args.chunk_size,
                cache_db=not args.no_cache_db,
                db_dir=args.db_dir,
                db_name=args.db_name,
                db_host=args.db_host,
                db_port=args.db_port,
                # Always show sources for web app.
                terminal=args.port is None,
            )
            match args.rag_type:
                case "brag":
                    from brag.rags import Brag

                    ChosenRag = Brag
                case "trag":
                    from brag.rags import Trag

                    ChosenRag = Trag
                case _:
                    raise ValueError(f"{args.rag_type} is not a valid option!")

            match args.system_prompt_path, args.system_prompt:
                case None, "basic":
                    from brag.rags.abstract import RAG_SYSTEM_PROMPT

                    system_prompt = RAG_SYSTEM_PROMPT
                case None, "mindful":
                    from brag.rags.abstract import MINDFUL_RAG_SYSTEM_PROMPT

                    system_prompt = MINDFUL_RAG_SYSTEM_PROMPT
                case None, _:
                    raise ValueError(
                        f"{args.system_prompt} is an invalid prompt."
                    )
                case _:  # system_prompt_path is supplied.
                    logging.debug(
                        "system_prompt_path is supplied and is:"
                        f"{args.system_prompt_path}"
                    )
                    with open(args.system_prompt_path, "r") as file:
                        system_prompt = file.read()
                    logging.debug(system_prompt)

            rag = ChosenRag(
                llm,
                db,
                thread_id=None,
                system_prompt=system_prompt,
                # Always show sources for web app.
                verbose=args.verbose or args.port is not None,
            )
            if args.port:
                from brag.ui import serve

                serve(rag, args)
            else:
                from brag.repl import AskREPL

                AskREPL().run(
                    "Ask questions about your corpus!",
                    rag.print_ask,
                )

        case "chat":
            from brag.chat import Chatbot
            from brag.repl import BragREPL

            if args.no_ssl_verify:
                litellm.ssl_verify = False

            logging.info(args)
            llm = ChatLiteLLM(
                model=args.llm,
                api_base=args.base_url,
                api_key=args.api_key,
            )
            chatbot = Chatbot(llm)
            BragREPL().run(
                f"Begin chatting with {args.llm} ", chatbot.print_stream
            )

        case "search":
            from brag.db import Database
            from brag.repl import BragREPL

            if args.no_ssl_verify:
                litellm.ssl_verify = False

            embedder = LiteLLMEmbeddings(
                model=args.emb,
                api_base=args.emb_base_url,
                api_key=args.emb_api_key,
            )

            db = Database(
                corpus_dir=Path(args.corpus_dir),
                embedder=embedder,
                index_doc_batch_size=args.batchsize,
                num_retrieved_docs=args.num_retrieved_docs,
                chunk_overlap=args.chunk_overlap,
                chunk_size=args.chunk_size,
                cache_db=not args.no_cache_db,
                db_dir=args.db_dir,
                db_name=args.db_name,
                db_host=args.db_host,
                db_port=args.db_port,
                terminal=True,
            )

            def print_results(query: str):
                print(db.retrieve(query, None))

            BragREPL().run("Begin searching your corpus!", print_results)

        case "rm-index":
            from chromadb import HttpClient, PersistentClient
            from chromadb.config import Settings

            # Recursively remove db dir.
            db_dir = Path(args.db_dir)
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
            if (port := args.db_port) is None:
                client = PersistentClient(path=str(db_dir), settings=settings)
            else:
                host = args.db_host or "localhost"
                client = HttpClient(host=host, port=port, settings=settings)

            try:
                # FIXME: the actual directories aren't removed, though the
                # collections are no longer associated. This could lead to large
                # disk space consumption.
                print(
                    "Number of collections (before):",
                    client.count_collections(),
                )

                client.delete_collection(name=args.db_name)
                if args.reset:
                    print("HERE")
                    client.reset()

                print(
                    "Number of collections (after):",
                    client.count_collections(),
                )

                logging.info(
                    f"Collection '{args.db_name}' deleted successfully."
                )
            except ValueError:
                logging.info(
                    f"Collection '{args.db_name}' was not found at {host}:{port}."
                )
