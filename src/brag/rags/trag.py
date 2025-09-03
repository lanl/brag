# Resources:
#
# https://python.langchain.com/docs/tutorials/rag/
# https://python.langchain.com/api_reference/core/vectorstores/langchain_core.vectorstores.in_memory.InMemoryVectorStore.html
# https://python.langchain.com/docs/integrations/text_embedding/
#
# https://python.langchain.com/docs/how_to/self_query/

import logging
from dataclasses import dataclass
from typing import Any, Iterator, Optional
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from brag.db import Database
from brag.rags.abstract import RAG_SYSTEM_PROMPT, Rag


@dataclass
class Trag(Rag):  # Tool calling RAG.
    llm: BaseChatModel
    db: Database
    thread_id: Optional[str] = None
    system_prompt: str = RAG_SYSTEM_PROMPT
    verbose: bool = True

    def apply_filter(self, filter_dict: Optional[dict[str, Any]] = None):
        self.make_retrieve_tool(filter_dict)  # Make document retriever tool.
        self.make_executor()  # Make langchain agent executor.

    def __post_init__(self):
        self.config = {"configurable": {"thread_id": self.thread_id or uuid4()}}
        self.apply_filter(None)

    def make_retrieve_tool(self, filter_dict: Optional[dict[str, Any]]):
        # NOTE: A docstring is required here for tool calling!
        def retrieve(query: str):
            """Retrieve information related to a query."""
            return self.db.retrieve(query, filter_dict=filter_dict)

        self.retrieve_tool = tool(response_format="content")(retrieve)

    def make_executor(self):
        memory = MemorySaver()
        tools = [self.retrieve_tool]
        logging.debug(f"System prompt: {self.system_prompt}")
        self.agent_executor = create_react_agent(
            self.llm,
            tools=tools,
            checkpointer=memory,
            prompt=self.system_prompt,
        )

    def ask(self, query: str) -> Iterator[str]:
        # References:
        # https://python.langchain.com/docs/how_to/qa_streaming/
        # This still only works for OpenAI but not Ollama.
        match query:
            case "!refresh":
                self.clear_memory()
                yield "Starting a new conversation... "

            case "!cite":
                yield self._context

            case _:
                self._context = ""
                self._response = ""
                for msg, _ in self.agent_executor.stream(
                    {"messages": ("user", query)},
                    stream_mode="messages",
                    config=self.config,
                ):
                    if msg.content and not isinstance(msg, HumanMessage):
                        if msg.type == "tool":
                            self._context = msg.content
                        else:
                            self._response += msg.content
                            # print(msg.content, flush=True, end="|")
                            yield msg.content
