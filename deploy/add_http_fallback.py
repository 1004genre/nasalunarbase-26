# This file was written with AI assistance (Claude, Anthropic) for the Earth Twin Finder project.
"""Make a copy of the page work on a plain http address.

    python3 deploy/add_http_fallback.py <folder of the page>

It copies secure-fallback.js into the folder and adds one script line to index.html, before every
other script. To run it again changes nothing.
"""
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LINE = '<script src="secure-fallback.js"></script>'


def main() -> None:
    folder = Path(sys.argv[1])
    shutil.copyfile(HERE / "secure-fallback.js", folder / "secure-fallback.js")
    page = folder / "index.html"
    text = page.read_text(encoding="utf-8")
    if LINE in text:
        print("add_http_fallback: the line is there already")
        return
    first = re.search(r"<script\b", text)
    if not first:
        raise SystemExit("add_http_fallback: index.html has no script line")
    page.write_text(text[: first.start()] + LINE + "\n" + text[first.start():], encoding="utf-8")
    print("add_http_fallback: added the line before the first script")


if __name__ == "__main__":
    main()
