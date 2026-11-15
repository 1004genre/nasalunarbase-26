# This file was written with AI assistance (Claude, Anthropic) for the LuniMartian Atlas project.
"""Write the name of the project, LuniMartian Atlas, in each text file of a folder.

    python3 deploy/rename_project.py <folder> [<folder> ...]

The first name of the project was two words longer. This script changes that name in the text files
(code, pages, data notes, documents). It does not change names that only code reads: the Python
package `twinfinder`, storage keys and event names. To run it again changes nothing.
"""
import sys
from pathlib import Path

OLD = "Earth " + "Twin Finder"          # in two parts, so that this script does not change itself
NEW = "LuniMartian Atlas"
OLD_FILE, NEW_FILE = "earth-" + "twin-finder", "lunimartian-atlas"
TEXT = {".js", ".mjs", ".html", ".css", ".json", ".md", ".txt", ".py", ".toml", ".conf", ".inc", ".yml", ".yaml", ""}
SKIP = {".git", ".venv", "raw", "vendor", "__pycache__", "node_modules", "analog-atlas-src", "research_notes", "handoff", "superpowers"}


def main() -> None:
    files = hits = 0
    for top in sys.argv[1:]:
        for path in Path(top).rglob("*"):
            if not path.is_file() or path.is_symlink() or path.suffix not in TEXT or SKIP & set(path.parts):
                continue
            if path.stat().st_size > 30_000_000:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            count = text.count(OLD) + text.count(OLD_FILE)
            if count:
                path.write_text(text.replace(OLD, NEW).replace(OLD_FILE, NEW_FILE), encoding="utf-8")
                files += 1
                hits += count
    print(f"rename_project: {hits} place(s) in {files} file(s)")


if __name__ == "__main__":
    main()
