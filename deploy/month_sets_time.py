# This file was written with AI assistance (Claude, Anthropic) for the LuniMartian Atlas project.
"""Let a chosen month or half-year set "the selected time" at each importance above 0.

    python3 deploy/month_sets_time.py <folder of the page>

Before this change, the board used a month for the options "in the selected time" (hours of low Sun,
snow-free odds, air temperature, cloud) only if the month had the importance 10. With an importance
of 1 to 9, these options showed figures for the full year, which a visitor did not expect.
To run the script again changes nothing.
"""
import sys
from pathlib import Path

OLD = "(c.importance===10||c.importance==null&&c.necessity==='necessary')).flatMap(c=>c.value)"
NEW = "(c.importance==null?c.necessity==='necessary':c.importance>0)).flatMap(c=>c.value)"
path = Path(sys.argv[1]) / "ask.js"
text = path.read_text(encoding="utf-8")
if text.count(OLD) == 2:
    path.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print("month_sets_time: a month and a half-year now set the selected time at each importance above 0")
elif text.count(NEW) == 2:
    print("month_sets_time: the change is there already")
else:
    raise SystemExit(f"month_sets_time: STOP. ask.js has {text.count(OLD)} of the 2 lines that this script knows.")
