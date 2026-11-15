# Written with an AI assistant (Claude); see README.md, section 'How AI was used'.
"""Copy the credit lines of data/SOURCES.md, section 3, into README.md.

The lines go between the two marks <!-- CREDITS-START --> and <!-- CREDITS-END --> of README.md.
Each credit line is copied as it stands in data/SOURCES.md: word for word, with its line breaks,
in the order of the file. The parser is the one of scripts/build_submission.py, which writes the
same lines into section 8c of SUBMISSION.md. Nothing outside the two marks changes.

    uv run python scripts/write_readme_credits.py            writes README.md
    uv run python scripts/write_readme_credits.py --check    says if README.md is up to date, writes nothing
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_submission import SOURCES, credit_lines  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
START, END = "<!-- CREDITS-START -->", "<!-- CREDITS-END -->"


def credits_block(sources_text: str) -> str:
    lines = credit_lines(sources_text)
    if not lines:
        raise SystemExit("write_readme_credits: STOPPED. data/SOURCES.md, section 3, has no credit line")
    return "\n".join(line for item in lines for line in item["lines"])


def with_credits(readme: str, block: str) -> str:
    if readme.count(START) != 1 or readme.count(END) != 1 or readme.index(START) > readme.index(END):
        raise SystemExit(f"write_readme_credits: STOPPED. README.md must hold {START} once, then {END} once")
    before, rest = readme.split(START, 1)
    _, after = rest.split(END, 1)
    return f"{before}{START}\n{block}\n{END}{after}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Copy the credit lines of data/SOURCES.md into README.md.")
    parser.add_argument("--check", action="store_true", help="say if README.md is up to date; write nothing")
    args = parser.parse_args(argv)
    sources_text = SOURCES.read_text(encoding="utf-8")
    block = credits_block(sources_text)
    readme = README.read_text(encoding="utf-8")
    new = with_credits(readme, block)
    count = len(credit_lines(sources_text))
    if args.check:
        print(f"write_readme_credits: README.md is {'up to date' if new == readme else 'NOT up to date'} "
              f"({count} credit lines in data/SOURCES.md)")
        return 0 if new == readme else 1
    if new != readme:
        part = README.with_name(README.name + ".part")
        part.write_text(new, encoding="utf-8")
        os.replace(part, README)
    print(f"write_readme_credits: {count} credit lines between the marks of README.md "
          f"({'written' if new != readme else 'no change'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
