# FIXME: Streaming output is not working!
# Create customized Ollama models with modelfile (e.g.):

# # In llama3.2:1b-128k.modelfile
# FROM llama3.2:1b
# PARAMETER num_ctx 128000
# PARAMETER repeat_penalty 1.1

# Then run: ollama create llama3.2:1b-128k -f llama3.2:1b-128k.modelfile

# https://www.youtube.com/watch?v=uWDocIoiaXE

import numpy as np
from langchain_core.embeddings import Embeddings
from numpy import ndarray
from numpy.linalg import norm


def batch_generator(iterable, batch_size: int):
    """
    Splits an iterable into batches of a specified size.

    Args:
        iterable: The input iterable (e.g., generator, list).
        batch_size: The number of items per batch.

    Yields:
        Lists containing up to batch_size elements from the iterable.
    """
    batch = []
    for item in iterable:
        batch.append(item)
        if len(batch) == batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def cosine_similarities(
    embedder: Embeddings, query: str, vecs: list[np.ndarray]
) -> list[float]:
    """Computes normalized scores
    Particularly when using ChromaDB with HuggingFaceEmbeddings.
    """
    query_vec = np.array(embedder.embed_query(query))
    vecs_mat = np.stack(vecs)
    numer = vecs_mat @ query_vec
    denom: ndarray = norm(query_vec) * norm(vecs_mat, axis=1)
    return (numer / denom).tolist()
