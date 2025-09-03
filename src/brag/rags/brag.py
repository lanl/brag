# Resources:
#
# https://python.langchain.com/docs/tutorials/rag/
# https://python.langchain.com/api_reference/core/vectorstores/langchain_core.vectorstores.in_memory.InMemoryVectorStore.html
# https://python.langchain.com/docs/integrations/text_embedding/
# https://python.langchain.com/docs/how_to/chatbots_memory/

import logging
from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
)
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph

from brag.db import Database
from brag.rags.abstract import RAG_SYSTEM_PROMPT, Rag


@dataclass
class Brag(Rag):
    """Basic RAG (Brag).

    This does not rely on tool calls, so might be better for VLLM-served models
    or LLMs that aren't reliable with tool calling.
    """

    llm: BaseChatModel
    db: Database
    thread_id: Optional[str] = None
    system_prompt: str = RAG_SYSTEM_PROMPT
    verbose: bool = True

    def __post_init__(self):
        self.config = {"configurable": {"thread_id": self.thread_id or uuid4()}}
        self.apply_filter(None)

    def apply_filter(self, filter_dict: Optional[dict[str, Any]] = None):
        workflow = StateGraph(state_schema=MessagesState)

        # Define the function that calls the model
        def call_model(state: MessagesState):
            logging.debug(f"System prompt: {self.system_prompt}")
            system_message = SystemMessage(content=self.system_prompt)

            # exclude the most recent user input
            message_history = state["messages"][:-1]

            last_human_message = state["messages"][-1]
            logging.debug(f"LHM: {last_human_message.content}")

            # Summarize the messages if the chat history reaches a certain size
            if len(message_history) >= 2:
                # Invoke the model to generate conversation summary
                summary_prompt = (
                    "Given the above chat history and the latest user query below, "
                    "which might reference the chat history, "
                    "formulate a standalone question which can be understood without the "
                    "chat history. Do NOT answer the user's question. Just reformulate it "
                    "if needed; otherwise, just return it as is."
                    "\n\n# Question:\n"
                    f"{last_human_message.content}"
                )

                # Generate standalone query using chat history.
                contextualized_query = self.llm.invoke(
                    message_history + [HumanMessage(content=summary_prompt)]
                )
                self._ctx_query = contextualized_query.content

                # Retrieve context.
                self._context = self.db.retrieve(
                    str(contextualized_query.content),
                    filter_dict=filter_dict,
                )

                prompt_with_context = (
                    f"\n\n# Question:\n{contextualized_query.content}"
                    f"\n\n# Context:\n{self._context}"
                )

                # Call the model with summary & response
                response = self.llm.invoke([
                    system_message,
                    HumanMessage(content=prompt_with_context),
                ])

                # Re-add user message
                human_message = HumanMessage(content=last_human_message.content)

                updated_messages = message_history + [
                    human_message,
                    response,
                ]
            else:
                # Retrieve context.
                self._context = self.db.retrieve(
                    last_human_message.content,
                    filter_dict=filter_dict,
                )

                prompt_with_context = (
                    f"\n\n# Question:\n{last_human_message.content}"
                    f"\n\n# Context:\n{self._context}"
                )

                response = self.llm.invoke(
                    [system_message]
                    + message_history
                    + [HumanMessage(prompt_with_context)]
                )

                updated_messages = message_history + [
                    HumanMessage(last_human_message.content),
                    response,
                ]

            return {"messages": updated_messages}

        # Define the node and edge
        workflow.add_node("model", call_model)
        workflow.add_edge(START, "model")

        # Add simple in-memory checkpointer
        memory = MemorySaver()
        self.app = workflow.compile(checkpointer=memory)

    def ask(self, query: str):
        # References:
        # https://python.langchain.com/docs/how_to/qa_streaming/
        # This still only works for OpenAI but not Ollama.
        # yield "WARNING: Brag is WIP. Please use Trag for production!\n\n"
        match query:
            case "!refresh":
                self.clear_memory()
                yield "Starting a new conversation... "

            case "!cite":
                yield self._context

            case _:
                self._context = ""
                self._response = ""
                self._ctx_query = ""
                # NOTE: I don't know why, but the contextualized query is
                # repeated.
                ctx_query = {}
                for msg, _ in self.app.stream(
                    {"messages": ("user", query)},
                    stream_mode="messages",
                    config=self.config,
                ):
                    if msg.content and not isinstance(msg, HumanMessage):
                        if msg.type == "AIMessageChunk":
                            ctx_query.setdefault(msg.id, "")
                            ctx_query[msg.id] += msg.content
                            if len(ctx_query) > 1:
                                # For some reason, the LLM always responds with
                                # the contextualized question. So skip the
                                # first.
                                self._response += msg.content
                                yield msg.content

                if len(ctx_query) == 1:
                    # For some reason, the contextualized query was not included
                    # in the AI response.
                    yield ctx_query[first_key(ctx_query)]

                yield "\n\n"

                logging.info(
                    f"Contextualized Query: {self._ctx_query or query}"
                )


def first_key(d: dict[str, Any]) -> str:
    return list(d)[0]
