# This file was written with AI assistance (Claude, Anthropic) for the Earth Twin Finder project.
"""Let one copy of the page use the AI models of the right computer.

    python3 deploy/use_server_models.py <folder of the page>

The board code (ask.js) asks for the two optional AI models on the visitor's own computer
(localhost:11434, through Ollama). A browser does not let a public page do that. On a public
server, the web server passes three requests (/ollama/api/tags, /ollama/api/embed and
/ollama/api/chat) to a model service beside it: see nginx-site.conf.

This script changes ask.js so that the page decides when it runs:
- on localhost, it asks the models of that computer, and its sentences say "on your computer";
- on each other address, it asks the server of the page, and its sentences say so.
To run the script again changes nothing.
"""
import sys
from pathlib import Path

FLAG = "ETF_LOCAL"
FLAG_LINE = ("// Added by deploy/use_server_models.py: true if this copy of the page runs on the visitor's own computer.\n"
             f"const {FLAG}=/^(?:localhost|127\\.0\\.0\\.1|\\[::1\\])$/.test(globalThis.location?.hostname||'localhost');\n")
ADDRESS_FORMS = [
    "fetch(`http://localhost:11434${path}`",
    ("fetch(`${/^(?:localhost|127\\.0\\.0\\.1|\\[::1\\])$/.test(location.hostname)"
     "?'http://localhost:11434':'/ollama'}${path}`"),
]
ADDRESS_NEW = "fetch(`${" + FLAG + "?'http://localhost:11434':'/ollama'}${path}`"
# Each pair: the sentence for a copy on the visitor's computer, the sentence for a copy on a server.
SENTENCES = [
    ("The AI models run on your computer. They only change your words into options. The places and all figures come from the data.",
     "The AI models run on the server of this page. Your words go to that server and to no other service. "
     "The models only change your words into options. The places and all figures come from the data."),
    (" Use an AI model on this computer", " Use an AI model"),
    ("No local model replied. The page rules still set options.", "No AI model replied. The page rules still set options."),
    ("The local models are off.", "The AI models are off."),
    ("The local model server refused this request.", "The model server refused this request."),
]


def main() -> None:
    path = Path(sys.argv[1]) / "ask.js"
    text = path.read_text(encoding="utf-8")
    if FLAG_LINE not in text:
        text = FLAG_LINE + text
    if ADDRESS_NEW not in text:
        found = [form for form in ADDRESS_FORMS if text.count(form) == 1]
        if not found:
            raise SystemExit("use_server_models: STOP. ask.js does not have the model address in a form that this script knows.")
        text = text.replace(found[0], ADDRESS_NEW)
        print("use_server_models: changed the address of the models")
    for local, server in SENTENCES:
        both = f"({FLAG}?'{local}':'{server}')"
        if both in text:
            continue
        count = 0
        for form in (local, server):          # the plain sentence, or the sentence of an earlier run of this script
            literal = f"'{form}'"
            if literal in text:
                count += text.count(literal)
                text = text.replace(literal, both)
                break
        if count:
            print(f"use_server_models: changed {count} x: {local[:60]}")
        else:
            print(f"use_server_models: WARNING, sentence not found: {local[:60]}")
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
