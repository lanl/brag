from dataclasses import dataclass
from typing import Optional

import litellm
from langchain_core.embeddings import Embeddings


@dataclass
class LiteLLMEmbeddings(Embeddings):
    model: str
    api_base: Optional[str] = None
    api_key: Optional[str] = None

    def __post_init__(self):
        self.provider, self.model_id = self.model.split("/", 1)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed search docs."""
        match self.provider:
            case "ollama":
                # NOTE: As of 9 May 2025, litellm.embedding somehow uses async
                # calls for ollama. This is a fix.
                from ollama import Client

                client = Client(host=self.api_base)
                return client.embed(
                    model=self.model_id,
                    input=texts,
                ).embeddings  # type: ignore

            case _:
                responses = litellm.embedding(
                    input=texts,
                    model=self.model,
                    api_base=self.api_base,
                    api_key=self.api_key,
                    aembedding=False,
                )
                return [data["embedding"] for data in responses.data]  # type: ignore

    def embed_query(self, text: str) -> list[float]:
        """Embed query text."""
        return self.embed_documents([text])[0]
