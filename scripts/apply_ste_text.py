# This file was written with AI assistance (Claude, Anthropic) for the LuniMartian Atlas project.
"""Put the Simplified Technical English wording into the page's data files.

The page's data files (site/data/*.json) hold sentences that the build scripts wrote. This script
replaces each sentence that a wording map names with its rewritten form. It changes text only:
no number, no key and no structure.

    uv run python scripts/apply_ste_text.py            # apply every map in data/reference/ste/
    uv run python scripts/apply_ste_text.py --check    # say what would change; write nothing

A wording map is a JSON file in data/reference/ste/ of this shape:

    { "about": "one line on what the map covers",
      "files": { "<file name in site/data, or * for every file>": { "<old sentence, exact>": "<new sentence>" } } }

A sentence is replaced only where a whole string value equals the old sentence exactly. Run this
script again after any script that writes site/data: a rebuilt file holds the old wording again.
A sentence whose numbers changed in a rebuild no longer matches and keeps its old wording; the
script counts such entries so that the map can be brought up to date.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "data" / "reference" / "ste"
SITE_DATA = ROOT / "site" / "data"


def load_maps(folder: Path) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    by_file: dict[str, dict[str, str]] = {}
    everywhere: dict[str, str] = {}
    for path in sorted(folder.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for name, pairs in (doc.get("files") or {}).items():
            target = everywhere if name == "*" else by_file.setdefault(name, {})
            for old, new in pairs.items():
                if isinstance(old, str) and isinstance(new, str) and old != new:
                    target[old] = new
    return by_file, everywhere


def rewrite(value, pairs: dict[str, str], used: set[str]):
    if isinstance(value, str):
        if value in pairs:
            used.add(value)
            return pairs[value]
        return value
    if isinstance(value, list):
        return [rewrite(item, pairs, used) for item in value]
    if isinstance(value, dict):
        return {key: rewrite(item, pairs, used) for key, item in value.items()}
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="say what would change; write nothing")
    parser.add_argument("--site-data", type=Path, default=SITE_DATA)
    parser.add_argument("--maps", type=Path, default=MAPS)
    args = parser.parse_args()

    if not args.maps.is_dir():
        print(f"no wording maps in {args.maps.relative_to(ROOT)}: nothing to do")
        return
    by_file, everywhere = load_maps(args.maps)
    total, unused_total = 0, 0
    for path in sorted(args.site_data.glob("*.json")):
        pairs = {**everywhere, **by_file.get(path.name, {})}
        if not pairs:
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as error:
            print(f"  {path.name}: not read ({error})")
            continue
        used: set[str] = set()
        new_doc = rewrite(doc, pairs, used)
        own = by_file.get(path.name, {})
        unused = [old for old in own if old not in used and own[old] not in json.dumps(new_doc, ensure_ascii=False)]
        unused_total += len(unused)
        if used:
            total += len(used)
            if not args.check:
                data = json.dumps(new_doc, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
                side = path.with_name(path.name + ".part")
                side.write_bytes(data)
                os.replace(side, path)
        if used or unused:
            print(f"  {path.name}: {len(used)} sentence(s) {'would change' if args.check else 'changed'}"
                  + (f"; {len(unused)} map entr{'y' if len(unused) == 1 else 'ies'} matched nothing" if unused else ""))
    print(f"apply_ste_text: {total} sentence(s) {'would change' if args.check else 'changed'}; "
          f"{unused_total} map entr{'y' if unused_total == 1 else 'ies'} matched nothing")
    if unused_total and args.check:
        sys.exit(0)


if __name__ == "__main__":
    main()
