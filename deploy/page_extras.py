# This file was written with AI assistance (Claude, Anthropic) for the LuniMartian Atlas project.
"""Three small changes to a copy of the page. To run it again changes nothing.

    python3 deploy/page_extras.py <folder of the page>

1. The page opens on Malapert Massif, the example region of the documents, if the data has it.
2. Under the first sentence, two links: the demo of 30 seconds, and the method and the code.
3. A box "How do we know it works?" with the checks of the method, from deploy/proof-box.html if that file exists.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
folder = Path(sys.argv[1])

# 1. the first lunar region
app = folder / "app.js"
text = app.read_text(encoding="utf-8")
OLD = "return current[0]?.id || D.meta.targets.find((t) => t.id === 'malapert')?.id || D.meta.targets[0]?.id;"
NEW = "return D.meta.targets.find((t) => t.id === 'malapert')?.id || current[0]?.id || D.meta.targets[0]?.id;"
if NEW in text:
    print("page_extras: the first region is Malapert Massif already")
elif text.count(OLD) == 1:
    app.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print("page_extras: the page now opens on Malapert Massif")
else:
    raise SystemExit("page_extras: STOP. app.js does not have the line for the first region.")

# 2. the links, and 3. the box
page = folder / "index.html"
html = page.read_text(encoding="utf-8")
LINKS = ('    <p class="hero-links"><a href="demo/lunimartian-atlas-demo.mp4">See the demo of 30 seconds</a> · '
         '<a href="https://github.com/1004genre/nasalunarbase-26">Read the method and the code</a> · '
         '<a href="#proof-section">How do we know it works?</a></p>\n')
ANCHOR = '    <p class="subline" id="subline" hidden></p>\n'
if 'class="hero-links"' not in html:
    if html.count(ANCHOR) != 1:
        raise SystemExit("page_extras: STOP. index.html does not have the line under the first sentence.")
    html = html.replace(ANCHOR, LINKS + ANCHOR)
    print("page_extras: added the links under the first sentence")
box = HERE / "proof-box.html"
START, END = "<!-- proof box: start -->", "<!-- proof box: end -->"
if box.exists():
    block = START + "\n" + box.read_text(encoding="utf-8").strip() + "\n" + END + "\n"
    if START in html:
        html = html[: html.index(START)] + block + html[html.index(END) + len(END) + 1:]
    else:
        place = '<section id="deeper-section">'
        if html.count(place) != 1:
            raise SystemExit("page_extras: STOP. index.html does not have the place for the box.")
        html = html.replace(place, block + place)
    print("page_extras: the box 'How do we know it works?' is in the page")
page.write_text(html, encoding="utf-8")

css = folder / "style.css"
style = css.read_text(encoding="utf-8")
RULES = """
/* Added by deploy/page_extras.py: the links under the first sentence, and the box of checks. */
.hero-links { margin-top: 10px; font-size: 13px; color: var(--muted); }
.hero-links a { color: var(--ui); }
.proof { max-width: 1200px; margin: 24px auto; padding: 20px 24px; border: 1px solid var(--hair); border-radius: 14px; background: var(--surface); }
.proof h2 { margin: 0 0 4px; }
.proof ul { margin: 12px 0 0; padding-left: 20px; display: grid; gap: 8px; }
.proof .caption { margin-top: 12px; }
@media (max-width: 720px) { .proof { margin: 16px; padding: 16px; } }
"""
if ".hero-links" not in style:
    css.write_text(style + RULES, encoding="utf-8")
