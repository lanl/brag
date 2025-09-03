import logging
import sqlite3
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from chromadb import EphemeralClient, HttpClient, PersistentClient

# from langchain.chains.query_constructor.schema import AttributeInfo
from langchain.text_splitter import (
    MarkdownTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    Docx2txtLoader,
    PyMuPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from tqdm import tqdm

from brag.defaults import Defaults
from brag.util import batch_generator


@dataclass
class MtimeDB:
    """An Sqlite3 db interface for last corpus doc modification times."""

    dbpath: Path
    table_name: str

    def open(self):
        self.dbpath.parent.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.dbpath, autocommit=True)
        self.cur = self.con.cursor()
        self.cur.execute(
            f"CREATE TABLE IF NOT EXISTS {self.table_name}(filename, stem, mtime)"
        )

    def close(self):
        self.con.close()

    def drop(self):
        self.cur.execute(f"DROP TABLE IF EXISTS {self.table_name}")

    def create(self):
        self.open()
        self.close()

    def insert(self, file: Path):
        self.open()
        self.cur.execute(
            f"INSERT INTO {self.table_name} VALUES(?, ?, ?)",
            (file.name, file.stem, file.stat().st_mtime),
        )
        self.close()

    def update(self, file: Path):
        self.open()
        self.cur.execute(
            f"Update {self.table_name} SET mtime = ? WHERE filename = ?",
            (file.name, file.stat().st_mtime),
        )
        self.close()

    def insertmany(self, files: Iterable[Path]):
        data = ((file.name, file.stem, file.stat().st_mtime) for file in files)
        self.open()
        self.cur.executemany(
            f"INSERT INTO {self.table_name} VALUES(?, ?, ?)", data
        )
        self.close()

    def get_mtime(self, file: Path):
        """Return the modification time of the file when indexed.

        If not indexed, will return -1.
        """
        self.open()
        record = self.cur.execute(
            f"SELECT * FROM {self.table_name} WHERE filename='{file.name}'"
        ).fetchone()
        self.close()

        return -1 if record is None else record[2]

    def get_filenames_in_index(self) -> list[str]:
        self.open()
        records = self.cur.execute(
            f"SELECT filename FROM {self.table_name}"
        ).fetchall()
        self.close()
        return [record[0] for record in records]


def get_page_or_chunk(doc: Document):
    m = doc.metadata
    return f"p. {m['page']}" if "page" in m else f"chunk {m['chunk']}"


class Database:
    def __init__(
        self,
        corpus_dir: Path,
        embedder: Embeddings,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        index_doc_batch_size: Optional[int] = None,
        num_retrieved_docs: Optional[int] = None,
        cache_db: bool = True,
        db_dir: Optional[str] = None,
        db_name: Optional[str] = None,
        db_host: Optional[str] = None,
        db_port: Optional[int] = None,
        mtime_db_path: Optional[str] = None,
        terminal: bool = False,
        mtime_table_name: str = "corpus_mtimes",
        min_space_to_bang: int = 1,
    ):
        self.corpus_dir = corpus_dir
        self.embedder = embedder
        self.cache_db = cache_db

        defaults = Defaults()
        self.chunk_size = chunk_size or defaults.chunk_size
        self.chunk_overlap = chunk_overlap or defaults.chunk_overlap_from(
            self.chunk_size
        )
        self.index_doc_batch_size = (
            index_doc_batch_size or defaults.batch_size_from(self.chunk_size)
        )
        self.num_retrieved_docs = (
            num_retrieved_docs
            or defaults.num_retrieved_docs_from(self.chunk_size)
        )

        self.db_name = db_name or "brag-db"
        self.db_dir = Path(db_dir or ".brag/db")
        self.db_host = db_host
        self.db_port = db_port

        self.mtime_db_path = mtime_db_path
        self.terminal = terminal
        self.mtime_table_name = mtime_table_name
        self.mtime_db = MtimeDB(
            dbpath=self.mtime_db_path_, table_name=self.mtime_table_name
        )

        # Minimum allowed ratio of space to exclaimation points.  If
        # min_space_to_bang is 10, that means I expect/require 10 ' ' for every
        # '!'. This can be violated if the document is corrupt.
        self.min_space_to_bang = min_space_to_bang

        logging.info(f"chunksize: {self.chunk_size}")
        logging.info(f"chunkoverlap: {self.chunk_overlap}")
        self.index()  # Index corpus.

    @property
    def in_sync(self) -> bool:
        return self.corpus_dir_mtime_when_last_indexed == self.corpus_dir_mtime

    @property
    def index_info_path(self):
        return self.db_dir / "index-info.txt"

    @property
    def corpus_dir_mtime_when_last_indexed(self) -> float:
        # Returns: when the corpus was last indexed, what was the mtime of the
        # corpus directory?
        self.index_info_path.parent.mkdir(parents=True, exist_ok=True)
        if self.index_info_path.exists():
            return float(self.index_info_path.read_text())
        else:
            # Record.
            self.index_info_path.write_text(str("-1"))
            return -1

    @property
    def corpus_dir_mtime(self) -> float:
        return self.corpus_dir.stat().st_mtime

    @property
    def mtime_db_path_(self) -> Path:
        """Sqlite3 db containing last modification times of corpus docs."""
        return Path(
            self.mtime_db_path
            or f"{self.db_dir}/{self.mtime_table_name}.sqlite3"
        )

    @property
    def bar_format(self):
        return "{desc} [{percentage:3.0f}% | {n_fmt}/{total_fmt} | {elapsed}<{remaining} | {rate_fmt}]"

    def delete_collection(self):
        match self.vectorstore:
            case Chroma():
                self.vectorstore.delete_collection()
                self.mtime_db.drop()

    def index(self):
        """Sync vectorstore and docs in corpus.

        - If a file is in corpus but not in vectorstore, the file is indexed.
        - If a file was in indexed but no longer in corpus, the file is removed
          from index.
        - If file is in corpus and has been indexed, but the file has been
          modified since indexing, the file is reindexed (i.e, removed from
          index, then indexed).
        """
        if not self.in_sync:  # no need to index if in sync.
            # Record the current mtime of the corpus directory.
            self.index_info_path.write_text(str(self.corpus_dir_mtime))

            # Index everything, if needed. docs will contain only documents that
            # are out of sync. So, documents that are in sync will not be
            # reindexed. New files in corpus will also be indexed.
            docs = self.parse_docs()
            batches = list(batch_generator(docs, self.index_doc_batch_size))
            for batch in tqdm(
                batches,
                bar_format=self.bar_format,
                desc="Indexing:",
            ):
                self.vectorstore.add_documents(batch)

            # Remove documents that are in index but no longer in corpus dir.
            fnames_index = set(self.mtime_db.get_filenames_in_index())
            fnames_corpus = {file.name for file in self.corpus_dir.iterdir()}
            files_to_remove = fnames_index.difference(fnames_corpus)
            for fname in files_to_remove:
                logging.info(f"Removing {fname} from index.")
                self.vectorstore.delete(where=dict(filename=fname))

    @cached_property
    def vectorstore(self):
        if self.cache_db:
            self.db_dir.mkdir(parents=True, exist_ok=True)

            if self.db_port is None:
                client = PersistentClient(path=str(self.db_dir))
            else:
                client = HttpClient(
                    host=self.db_host or "localhost", port=self.db_port
                )

        else:
            client = EphemeralClient()

        return Chroma(
            collection_name=self.db_name,
            embedding_function=self.embedder,
            client=client,
            collection_metadata={"hnsw:space": "cosine"},
        )

    @cached_property
    def vectorstore_isempty(self) -> bool:
        match self.vectorstore:
            case Chroma():
                return self.vectorstore._collection.count() == 0
            case _:
                raise NotImplementedError()

    def parse_file(self, file: Path) -> Iterator[Document]:
        mtime_when_indexed = self.mtime_db.get_mtime(file)
        logging.debug(f"{file.stem}, {mtime_when_indexed}")
        if file.stat().st_mtime > mtime_when_indexed:
            # need to index / reindex.
            if mtime_when_indexed < 0:
                self.mtime_db.insert(file)
            else:
                self.mtime_db.update(file)

            try:
                match file.suffix.lower():  # file extension.
                    case ".pdf":
                        loader = PyMuPDFLoader(file)
                        text_splitter = RecursiveCharacterTextSplitter(
                            chunk_size=self.chunk_size,
                            chunk_overlap=self.chunk_overlap,
                        )

                    case ".md" | ".markdown":
                        loader = TextLoader(file)
                        text_splitter = MarkdownTextSplitter(
                            chunk_size=self.chunk_size,
                            chunk_overlap=self.chunk_overlap,
                        )

                    case ".docx":
                        loader = Docx2txtLoader(file)
                        text_splitter = RecursiveCharacterTextSplitter(
                            chunk_size=self.chunk_size,
                            chunk_overlap=self.chunk_overlap,
                        )

                    case _:
                        # Assume text file.
                        loader = TextLoader(file)
                        text_splitter = RecursiveCharacterTextSplitter(
                            chunk_size=self.chunk_size,
                            chunk_overlap=self.chunk_overlap,
                        )

                docs = loader.load_and_split(text_splitter=text_splitter)

                # Add additional metadata.
                for i, d in enumerate(docs):
                    bang_count = d.page_content.count("!")
                    space_count = d.page_content.count(" ")
                    space_to_bang = space_count / (bang_count + 1e-6)

                    # Some documents are '!' delimited instead of ' '
                    # delimited. This messes with some vector embedders.  The
                    # following attempts to infer whether such a case has
                    # occured by computing the ratio of ' ' to '!'. By default,
                    # if '!' absolutely shows up more frequently than ' ', then
                    # all ' ' will be replaced by '!'. min_space_to_bang can be
                    # user specified.  If not specified, will default to 1,
                    # which implies a 1:1 ratio is acceptable (but 1:2, 1:3, etc
                    # is not).
                    if space_to_bang < self.min_space_to_bang:
                        print(
                            "brag detected too many '!'. "
                            f"{file.name} Could be a problematic document."
                            "Converting '!' to ' '."
                            "If this is expected, try decreasing `min_space_to_bang` "
                            "in brag.db.Database."
                        )
                        print("space_to_bang:", space_to_bang)
                        print(d.page_content)
                        d.page_content = d.page_content.replace("!", " ")

                    d.metadata["chunk"] = i + 1
                    d.metadata["file_name"] = file.name
                    d.metadata["file_stem"] = file.stem
                    d.metadata["abs_path"] = str(file.absolute())
                    d.metadata["corpus_dir"] = str(self.corpus_dir)
                    d.metadata["rel_path"] = str(
                        file.relative_to(self.corpus_dir)
                    )
                    d.metadata["db_name"] = self.db_name

                yield from docs

            except Exception:
                logging.warning(f"Skipping {file.name} due to parsing errors.")

    def delete_file(self, file_name: str):
        logging.info(f"deleting file: {file_name}")
        self.vectorstore.delete(where={"file_name": file_name})
        logging.info("done.")

    def add_file(self, file_name: str):
        logging.info("adding file: ", file_name)
        file = self.corpus_dir / file_name
        docs = self.parse_file(file)
        batches = list(batch_generator(docs, self.index_doc_batch_size))
        for batch in tqdm(
            batches,
            bar_format=self.bar_format,
            desc="Indexing:",
        ):
            self.vectorstore.add_documents(batch)

        logging.info("done.")

    def parse_docs(self) -> Iterator[Document]:
        # TODO: Provide an option to parallelize this.
        num_files = self.count_files_in_dir(self.corpus_dir)
        for file in tqdm(
            self.corpus_dir.iterdir(),
            total=num_files,
            bar_format=self.bar_format,
            desc="Parsing: ",
        ):
            if file.is_file():
                yield from self.parse_file(file)

    def count_files_in_dir(self, dir: Path):
        return sum(1 for f in dir.iterdir() if f.is_file())

    def retrieve(self, query: str, filter_dict: Optional[dict[str, Any]]):
        # Scores are in [0, 1]. 0 for most dissimilar. 1 for most similar.
        retrieved_docs, scores = zip(
            *(
                self.vectorstore.similarity_search_with_relevance_scores(
                    query, k=self.num_retrieved_docs, filter=filter_dict
                )
            )
        )
        serialized_context = serialize(retrieved_docs, scores, self.terminal)  # type: ignore
        return serialized_context

    # def sync(self): ...


def serialize(docs: list[Document], scores: list[float], terminal: bool):
    num_sources = len(docs)

    if terminal:
        serialized = "\n\n".join(
            (
                f"{i + 1}. {doc.metadata['file_name']} ({get_page_or_chunk(doc)})"
                f"\nExcerpt ({score * 100:3.0f}%): {doc.page_content}"
            )
            for i, (doc, score) in enumerate(zip(docs, scores))
        )
        return f"\nSources ({num_sources})\n\n***\n\n" + serialized
    else:
        tag_open = (
            f"<details><summary><b>Sources ({num_sources})</b></summary>"
            "<div class='sources'>"
            "<ol class='brag-source'>"
        )
        body = ""
        tag_close = "</ol></div></details>"

        for doc, score in zip(docs, scores):
            m = doc.metadata
            if "page" in m:
                page = m["page"] + 1
                location = f"p. {page}"
                rel_path = m["rel_path"] + f"#page={page}"
            else:
                location = f"chunk {m['chunk']}"
                rel_path = m["rel_path"]

            fname = m["file_name"]
            fstem = Path(fname).stem
            url = f"/corpus/{rel_path}"

            body += (
                "<li>"
                f"<a href='{url}' target=_blank>{fstem} ({location})</a>"
                "<details>"
                f"<summary>Preview (Score: {score * 100:.0f}%)</summary>"
                f"<div class='preview'>{doc.page_content}</div>"
                "</details>"
                "</li>"
            )

        return tag_open + body + tag_close
