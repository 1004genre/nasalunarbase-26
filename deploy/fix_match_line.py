# This file was written with AI assistance (Claude, Anthropic) for the LuniMartian Atlas project.
"""Repair the line under the globe when the experiment board has set options.

    python3 deploy/fix_match_line.py <folder of the page>

The board gives the line "16,184 areas pass. Best match: 95.3%." The globe then added
": 16,184 areas match the criteria." to it, which gave a double stop and the same count twice.
With this change the globe shows the board's line as it is. To run it again changes nothing.
"""
import sys
from pathlib import Path

OLD = ("? `${activeMatches.label || title}: ${num(matched.length)} ${s.dest === 'moon' ? 'areas' : 'squares'} match the criteria.`")
NEW = ("? (activeMatches.label || `${title}: ${num(matched.length)} ${s.dest === 'moon' ? 'areas' : 'squares'} match the criteria.`)")
path = Path(sys.argv[1]) / "globes.js"
text = path.read_text(encoding="utf-8")
if NEW in text:
    print("fix_match_line: the change is there already")
elif text.count(OLD) == 1:
    path.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print("fix_match_line: the line under the globe now shows the board's sentence once")
else:
    raise SystemExit("fix_match_line: STOP. globes.js does not have the line that this script knows.")
