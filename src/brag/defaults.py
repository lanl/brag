from dataclasses import dataclass
from functools import cached_property
from math import ceil

_MAX_CHUNKS_SENT = 30000
_MAX_CTX_CHUNKS = 5500


@dataclass
class Defaults:
    chunk_size: int = 512
    temperature: float = 0.2
    max_chunks_sent: int = _MAX_CHUNKS_SENT
    max_ctx_chunks: int = _MAX_CTX_CHUNKS

    @staticmethod
    def chunk_overlap_from(chunk_size: int) -> int:
        return ceil(chunk_size * 0.2)

    @staticmethod
    def batch_size_from(
        chunk_size: int, max_chunks_sent: int = _MAX_CHUNKS_SENT
    ) -> int:
        return max_chunks_sent // chunk_size

    @staticmethod
    def num_retrieved_docs_from(
        chunk_size: int, max_ctx_chunks: int = _MAX_CTX_CHUNKS
    ) -> int:
        return max_ctx_chunks // chunk_size

    @cached_property
    def chunk_overlap(self) -> int:
        return self.chunk_overlap_from(self.chunk_size)

    @cached_property
    def batch_size(self) -> int:
        return self.max_chunks_sent // self.chunk_size

    @cached_property
    def num_retrieved_docs(self) -> int:
        return self.max_ctx_chunks // self.chunk_size
