# This file was written with AI assistance (Claude, Anthropic) for the LuniMartian Atlas project.
"""Make the tour turn to Malapert Massif, the example region of the documents.

    python3 deploy/tour_region.py <folder of the page>

The tour (tools.js) turns the globe to a lunar region that is not the selected one. It took the first
region of the list, which has the lowest Sun and thus the fewest hours. With this change it takes
Malapert Massif if that region is in the data and is not the selected one. To run it again changes nothing.
"""
import sys
from pathlib import Path

OLD = "const other = api.targets.find((t) => t.id !== saved.state.target) || api.targets[0];"
EARLIER = ("const other = api.targets.find((t) => t.id === 'malapert' && t.id !== saved.state.target)"
           " || api.targets.find((t) => t.id !== saved.state.target) || api.targets[0];")
NEW = ("const other = api.targets.find((t) => t.id === 'malapert')"
       " || api.targets.find((t) => t.id !== saved.state.target) || api.targets[0];")
path = Path(sys.argv[1]) / "tools.js"
text = path.read_text(encoding="utf-8")
if NEW in text:
    print("tour_region: the change is there already")
elif text.count(OLD) == 1 or text.count(EARLIER) == 1:
    path.write_text(text.replace(OLD, NEW).replace(EARLIER, NEW), encoding="utf-8")
    print("tour_region: the tour now turns to Malapert Massif")
else:
    raise SystemExit("tour_region: STOP. tools.js does not have the line that this script knows.")
