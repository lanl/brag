from typing import Optional
from uuid import UUID, uuid4

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from rich.markdown import Markdown

from brag.styles import make_console


class Chatbot:
    def __init__(self, model: BaseChatModel, thread_id: Optional[UUID] = None):
        self.model = model
        self.thread_id = thread_id or uuid4()
        self.console = make_console()

        memory = MemorySaver()

        # Define a new graph
        self.bot = (
            StateGraph(state_schema=MessagesState)
            # Define the (single) node in the graph
            .add_node("model", self.call_model)
            .add_edge(START, "model")
            # Add memory
            .compile(checkpointer=memory)
        )
        self.config = {"configurable": {"thread_id": self.thread_id}}

    def clear_memory(self):
        self.config["configurable"]["thread_id"] = uuid4()

    # Define the function that calls the model
    def call_model(self, state: MessagesState):
        response = self.model.invoke(state["messages"])
        return {"messages": response}

    def stream(self, query: str):
        if query == "!refresh":
            self.clear_memory()
            yield "Starting a new conversation!"
        else:
            input_messages = [HumanMessage(query)]

            s = self.bot.stream(
                {"messages": input_messages},
                self.config,
                stream_mode="messages",
            )
            for chunk, metadata in s:
                match chunk:
                    case AIMessage():
                        yield chunk.content

    def invoke(self, query: str, **kwargs):
        input_messages = [HumanMessage(query)]
        return self.bot.invoke(
            {"messages": input_messages}, self.config, **kwargs
        )

    def print_stream(self, query: str):
        stream = self.stream(query)

        # TODO: deprecate
        # for chunk in stream:
        #     print(chunk, end="")

        with self.console.status("[info]Generating response ..."):
            response = "".join(stream)
            self.console.print(Markdown(response))

        print()
