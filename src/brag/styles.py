from rich.console import Console
from rich.theme import Theme


def make_console():
    return Console(theme=Theme({"info": "dim green"}))


chat_css = r"""
:root {
    --font: "Helvetica Neue", Helvetica, Arial, sans-serif;
    --font-weight: 200;
    --bold-weight: 600;
}
:not(.component-wrap).flex-wrap, textarea {
    border-style: none;
}
.chatbot-outer { border-style: none !important; }
.bubble-wrap, .gradio-container {
    background-color: var(--background-fill-primary);
}
div.form, .user-input {
    background-color: var(--background-fill-primary);
    border-style: none !important;
}
strong { font-weight: var(--bold-weight); }
h1, h2, h3, h4, h5, h6 { font-weight: var(--header-weight); }
textarea { resize: none; }
body { padding-bottom: 0em !important; }
.brag-sources li {padding-top: 1em;}
.brag-tab-header {text-align: center;}
.user-input {
    position: fixed;
    bottom: 3em;
    margin-top: 10em;
    left: 50%;
    transform: translateX(-50%);
    max-width: min(85vw, 1000px);
}
"""
