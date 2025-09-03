# https://fastapi.tiangolo.com/tutorial/static-files/
# https://www.gradio.app/guides/creating-a-custom-chatbot-with-blocks
import logging
from argparse import Namespace
from pathlib import Path

import gradio as gr
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pypdf import PdfReader

from brag.chat import Chatbot
from brag.rags.abstract import Rag
from brag.styles import chat_css


def make_tabs(rag: Rag, args: Namespace):
    with gr.Blocks(analytics_enabled=False) as rag_tab:
        with gr.Row():
            with gr.Column(scale=1):
                checkbox = gr.Checkbox(False, label="Show documents")

                def filter_docs(docnames: list[str]):
                    logging.info(f"Selected documents: {', '.join(docnames)}")
                    filter_dict = {"file_stem": {"$in": docnames}}
                    rag.apply_filter(filter_dict)

                corpus_dir = Path(args.corpus_dir)
                docs = {
                    doc.stem: doc
                    for doc in corpus_dir.iterdir()
                    if doc.is_file()
                }

                sorted_docnames = sorted(docs.keys())
                dropdown = gr.Dropdown(
                    choices=sorted_docnames,
                    value=sorted_docnames,
                    label="Select documents to query",
                    multiselect=True,
                    visible=False,
                )

                def toggle_dropdown(show: bool):
                    return gr.update(visible=show)

                dropdown.change(fn=filter_docs, inputs=dropdown)
                checkbox.change(
                    fn=toggle_dropdown, inputs=checkbox, outputs=dropdown
                )

            with gr.Column(scale=2, elem_classes="rag"):
                gr.Markdown(
                    f"# Chat about Documents (powered by {args.llm})",
                    elem_classes="brag-tab-header",
                )
                # FIXME: After clearing screen. Ask another question. Then the
                # old history reappears?!
                # clear = gr.HTML(
                #     "<a href='#'>Start new conversation</a>",
                #     elem_classes="brag-tab-header",
                # )

                def respond(query: str, _: list[dict[str, str]]):
                    response = ""
                    for chunk in rag.yield_ask(query):
                        response += str(chunk)
                        yield response

                chatbot = gr.Chatbot(
                    type="messages",
                    height="60vh",
                    container=False,
                    show_copy_button=True,
                )

                msg = gr.Textbox(
                    container=False,
                    placeholder="Enter query here",
                    show_copy_button=True,
                )

                gr.ChatInterface(
                    fn=respond,
                    chatbot=chatbot,
                    textbox=msg,
                    type="messages",
                    fill_height=True,
                    flagging_mode="manual",
                )

                # def clear_screen():
                #     rag.clear_memory()
                #     return "", []

                # clear.click(
                #     fn=clear_screen, inputs=None, outputs=[msg, chatbot]
                # )

        def on_load():
            # On page refresh, include all docs first.
            logging.info("Filter nothing from RAG.")
            rag.apply_filter(None)

        # If not using on_load, can comment this out.
        rag_tab.load(on_load)

    with gr.Blocks(analytics_enabled=False) as search_engine_tab:

        def clear_screen():
            return []

        gr.Markdown("# Search", elem_classes="brag-tab-header")
        clear = gr.HTML(
            "<a href='#'>Clear screen</a>", elem_classes="brag-tab-header"
        )

        chatbot = gr.Chatbot(
            type="messages",
            show_label=False,
            container=False,
            placeholder="Search history will show up here",
            height="100%",
            elem_classes="chatbot-outer",
            show_copy_button=True,
        )
        msg = gr.Textbox(
            placeholder="Enter search",
            show_label=False,
            elem_classes="user-input",
            show_copy_button=True,
        )

        def search(query: str, history: list[dict[str, str]]):
            history.append(dict(role="user", content=query))
            history.append(dict(role="assistant", content=""))

            for chunk in rag.db.retrieve(query, filter_dict=None):
                history[-1]["content"] += str(chunk)
                yield "", history

        msg.submit(search, inputs=[msg, chatbot], outputs=[msg, chatbot])
        clear.click(fn=clear_screen, inputs=None, outputs=chatbot)

    with gr.Blocks(analytics_enabled=False) as chat_tab:
        bot = Chatbot(rag.llm)

        def clear_llm_history():
            bot.clear_memory()
            gr.update(value=[])

        gr.Markdown(f"# Chat with {args.llm}", elem_classes="brag-tab-header")
        clear = gr.HTML(
            "<a href='#'>Start new conversation</a>",
            elem_classes="brag-tab-header",
        )

        chatbot = gr.Chatbot(
            type="messages",
            show_label=False,
            container=False,
            placeholder="Chat history will show up here",
            height="100%",
            elem_classes="chatbot-outer",
            show_copy_button=True,
        )

        msg = gr.Textbox(
            placeholder="Chat with BRAG ",
            show_label=False,
            elem_classes="user-input",
            show_copy_button=True,
        )

        def update(query: str, history: list[dict[str, str]]):
            history.append(dict(role="user", content=query))
            history.append(dict(role="assistant", content=""))

            for chunk in bot.stream(query):
                history[-1]["content"] += str(chunk)
                yield "", history

        msg.submit(update, inputs=[msg, chatbot], outputs=[msg, chatbot])
        clear.click(fn=clear_llm_history, inputs=None, outputs=chatbot)

    with gr.Blocks(analytics_enabled=False) as summarize_tab:
        corpus_dir = Path(args.corpus_dir)
        docs = {doc.stem: doc for doc in corpus_dir.iterdir() if doc.is_file()}

        def summarize(docname: str):
            prompt = "Please summarize the following:\n{content}"
            doc = docs[docname]

            logging.info("Load text.")
            match doc.suffix[1:]:
                case "pdf":
                    # content = pymupdf4llm.to_markdown(doc)
                    reader = PdfReader(doc)
                    content = "\n".join(
                        page.extract_text() for page in reader.pages
                    )
                case "txt" | "md":
                    content = doc.read_text()
                case _:
                    raise NotImplementedError()

            logging.info(
                f"Number of words in {docname}: {len(content.split())}."
            )
            response = ""
            for chunk in rag.llm.stream(prompt.format(content=content)):
                response += str(chunk.content)
                yield response

        summary = gr.Markdown(
            label="Summary",
            max_height=500,
            show_copy_button=True,
        )

        gr.Interface(
            summarize,
            [
                gr.Dropdown(
                    sorted(docs.keys()), label="Select a document to summarize"
                )
            ],
            summary,
        )

    return rag_tab, search_engine_tab, summarize_tab, chat_tab


def serve(rag: Rag, args: Namespace):
    # Serve /corpus dir.
    app = FastAPI()
    app.mount(
        "/corpus",
        StaticFiles(directory=str(args.corpus_dir)),
    )

    tabs = make_tabs(rag, args)
    demo = gr.TabbedInterface(
        tabs,
        ["Document Chat", "Search", "Summarize", "LLM"],
        css=chat_css,
    )
    app = gr.mount_gradio_app(app, demo, path="/")
    uvicorn.run(app, port=args.port)
