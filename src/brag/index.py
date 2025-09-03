# Experimental WIP.
# https://python.langchain.com/docs/how_to/indexing/

from langchain.indexes import SQLRecordManager, index
from langchain_core.documents import Document


class Index:
    def __init__(
        self,
        vectorstore,
        db: str = "chromadb",
        source_id_key: str = "source",
    ):
        self.vectorstore = vectorstore
        self.collection_name = self.vectorstore._collection.name
        self.db = db
        self.namespace = f"{self.db}/{self.collection_name}"
        self.record_manager = SQLRecordManager(
            self.namespace, db_url="sqlite:///record_manager_cache.sql"
        )
        self.source_id_key = source_id_key
        self.record_manager.create_schema()
        self._index = index

    def count(self) -> int:
        return self.vectorstore._collection.count()

    def add(self, docs: list[Document]):
        return self._index(
            docs,
            self.record_manager,
            self.vectorstore,
            cleanup="incremental",
            source_id_key=self.source_id_key,
        )

    def sync(self, docs: list[Document]):
        return self._index(
            docs,
            self.record_manager,
            self.vectorstore,
            cleanup="full",
            source_id_key=self.source_id_key,
        )

    def clear(self):
        """Helper method to clear content. See the `full` mode section to
        to understand why it works."""
        return self.sync([])
