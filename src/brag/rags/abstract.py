from abc import ABC, abstractmethod
from typing import Any, Iterator, Optional
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from rich.console import Console
from rich.markdown import Markdown

from brag.db import Database
from brag.styles import make_console

"""Prompt for RAG."""
RAG_SYSTEM_PROMPT = """
Please answer the user's questions based on the provided context. If the context 
doesn't contain information relevant to the question, say you don't have enough 
information to answer the question.
""".strip().replace("\n", "")

"""Mindful prompt for RAG.

Enables the use of the LLM's existing knowledge to answer the question.
"""

MINDFUL_RAG_SYSTEM_PROMPT = """
Please answer the user's questions. A context will be provided for you 
to help you answer questions, but you need not answer based only on 
the context. If you do answer based on information that is not 
included in the context, just say so.
""".strip().replace("\n", "")

# MINDFUL_RAG_SYSTEM_PROMPT_FAILED_ATTEMP_2 = """
# Please answer the user's questions. A context will be provided for you
# to help you answer questions, but you need not answer based only on
# the context. If you still don't have enough information to answer the
# user's questions, say that you don't have enough information and if possible
# state what information you would need to answer the questions.
# """.strip().replace("\n", "")

# MINDFUL_RAG_SYSTEM_PROMPT_FAILED_ATTEMPT_1 = """
# Please answer the user's questions based on the provided context. If the
# context doesn't contain information relevant to the question, use your
# existing knowledge to answer the question. If you still don't have enough
# information to answer the question, say that you don't have enough information
# to answer the question.
# """.strip().replace("\n", "")


class Rag(ABC):  # Tool calling RAG.
    config: dict[str, Any]
    _context: str
    db: Database
    llm: BaseChatModel
    system_prompt: str
    verbose: bool = True
    console: Console = make_console()

    @abstractmethod
    def ask(self, query: str) -> Iterator[str]: ...

    @abstractmethod
    def apply_filter(self, filter_dict: Optional[dict[str, Any]] = None): ...

    def clear_memory(self) -> None:
        self.config["configurable"]["thread_id"] = uuid4()

    def print_ask(self, query: str) -> None:
        """Print query response, with context if verbose."""
        with self.console.status("[info]Generating response ..."):
            response = "".join(self.yield_ask(query))

        self.console.print(Markdown(response))

    def yield_ask(self, query: str) -> Iterator[str]:
        """Yield query response, with context if verbose."""
        yield from self.ask(query)
        if self.verbose:
            yield "\n"
            yield self._context
