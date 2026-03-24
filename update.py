#!/usr/bin/env python3
"""
update.py – add publications or talks to the website and CV.

Usage:
    python update.py
"""

import os
import re
import subprocess
import sys
from datetime import date, datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PUBS_HTML  = os.path.join(SCRIPT_DIR, "publications.html")
TALKS_HTML = os.path.join(SCRIPT_DIR, "talks.html")
CV_TEX     = os.path.join(SCRIPT_DIR, "CV", "CVnew.tex")
BIB = {
    "journal":    os.path.join(SCRIPT_DIR, "CV", "pubs.bib"),
    "chapter":    os.path.join(SCRIPT_DIR, "CV", "chapters.bib"),
    "commentary": os.path.join(SCRIPT_DIR, "CV", "comments.bib"),
    "edited":     os.path.join(SCRIPT_DIR, "CV", "edited.bib"),
}

PUB_TYPES = [
    ("journal",    "Journal Articles"),
    ("chapter",    "Book Chapters"),
    ("commentary", "Commentaries and Replies"),
    ("edited",     "Edited Volumes"),
]

# ── I/O helpers ───────────────────────────────────────────────────────────────

def ask(prompt, default=None):
    hint = f" [{default}]" if default else ""
    val = input(f"  {prompt}{hint}: ").strip()
    return val if val else (default or "")

def ask_yn(prompt, default=True):
    val = input(f"  {prompt} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    if not val:
        return default
    return val[0] == "y"

def rfile(p):
    with open(p, encoding="utf-8") as f:
        return f.read()

def wfile(p, s):
    with open(p, "w", encoding="utf-8") as f:
        f.write(s)

# ── LaTeX → Unicode ───────────────────────────────────────────────────────────

def latex_to_unicode(s):
    """Convert common LaTeX diacritic commands to Unicode characters."""
    # Map: (command_char, letter) → unicode
    # Handles {\cmd{L}}, {\cmdL}, and \cmdL variants
    DIACRITICS = {
        ("'", "a"): "á", ("'", "A"): "Á",
        ("'", "e"): "é", ("'", "E"): "É",
        ("'", "i"): "í", ("'", "I"): "Í",
        ("'", "o"): "ó", ("'", "O"): "Ó",
        ("'", "u"): "ú", ("'", "U"): "Ú",
        ("'", "n"): "ń", ("'", "N"): "Ń",
        ("'", "s"): "ś", ("'", "S"): "Ś",
        ("'", "z"): "ź", ("'", "Z"): "Ź",
        ("'", "c"): "ć", ("'", "C"): "Ć",
        (".", "z"): "ż", (".", "Z"): "Ż",
        (".", "a"): "ȧ", (".", "A"): "Ȧ",
        ('"', "o"): "ö", ('"', "O"): "Ö",
        ('"', "a"): "ä", ('"', "A"): "Ä",
        ('"', "u"): "ü", ('"', "U"): "Ü",
        ("v", "s"): "š", ("v", "S"): "Š",
        ("v", "z"): "ž", ("v", "Z"): "Ž",
        ("v", "c"): "č", ("v", "C"): "Č",
        ("k", "a"): "ą", ("k", "A"): "Ą",
        ("k", "e"): "ę", ("k", "E"): "Ę",
        ("c", "c"): "ç", ("c", "C"): "Ç",
        ("~", "n"): "ñ", ("~", "N"): "Ñ",
    }

    def replace_cmd(m):
        cmd, letter = m.group(1), m.group(2)
        return DIACRITICS.get((cmd, letter), m.group(0))

    # {\cmd{L}} or {\cmdL} — e.g. {\.{Z}}, {\.Z}, {\'a}, {\'{ a}}
    s = re.sub(r"\{\\(.)\{([A-Za-z])\}\}", replace_cmd, s)
    s = re.sub(r"\{\\(.)([A-Za-z])\}", replace_cmd, s)
    # \cmdL without braces — e.g. \.Z, \'a
    s = re.sub(r"\\(.)([A-Za-z])", replace_cmd, s)

    # Stroke letters: {\l} {\L}
    s = s.replace(r"{\l}", "ł").replace(r"{\L}", "Ł")
    s = s.replace(r"\l", "ł").replace(r"\L", "Ł")

    # Strip remaining bare braces and unknown \commands
    s = re.sub(r"\{([^{}]*)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)
    return s

# ── Author formatting ─────────────────────────────────────────────────────────

def fmt_authors(raw):
    """'Last, First and Last2, First2' → HTML, bolding Bystranowski."""
    raw = latex_to_unicode(raw)
    parts = [p.strip() for p in raw.split(" and ")]
    out = []
    for p in parts:
        if not p:
            continue
        if p.lower() in ("others", "et al.", "et al"):
            out.append("<em>et&nbsp;al.</em>")
            continue
        if "Bystranowski" in p:
            out.append("<strong>P.&nbsp;Bystranowski</strong>")
            continue
        if "," in p:
            last, first = p.split(",", 1)
            inits = " ".join(w[0] + "." for w in first.split() if w)
            out.append(f"{inits}&nbsp;{last.strip()}")
        else:
            words = p.split()
            out.append(f"{words[0][0]}.&nbsp;{' '.join(words[1:])}" if len(words) > 1 else p)
    if not out:
        return raw
    if len(out) == 1:
        return out[0]
    if len(out) == 2:
        return f"{out[0]} &amp; {out[1]}"
    return ", ".join(out[:-1]) + ", &amp; " + out[-1]

# ── BibTeX building ───────────────────────────────────────────────────────────

def build_bib(pub_type, key, title, authors, year, info):
    def kv(k, v):
        return f"  {k} = {{{v}}},"

    lines = []
    if pub_type == "journal":
        lines = [f"@article{{{key},",
                 kv("author",  authors),
                 kv("title",   title),
                 kv("journal", info.get("venue", ""))]
        for k in ("volume", "number", "pages"):
            if info.get(k):
                lines.append(kv(k, info[k]))
        lines.append(kv("year", year))
        for k in ("doi", "url"):
            if info.get(k):
                lines.append(kv(k, info[k]))
        lines.append("}")

    elif pub_type == "chapter":
        lines = [f"@incollection{{{key},",
                 kv("author",    authors),
                 kv("title",     title),
                 kv("booktitle", info.get("venue", ""))]
        for k in ("editor", "publisher"):
            if info.get(k):
                lines.append(kv(k, info[k]))
        lines.append(kv("year", year))
        for k in ("doi", "url"):
            if info.get(k):
                lines.append(kv(k, info[k]))
        lines.append("}")

    elif pub_type == "commentary":
        lines = [f"@article{{{key},",
                 kv("author",  authors),
                 kv("title",   title),
                 kv("journal", info.get("venue", ""))]
        if info.get("volume"):
            lines.append(kv("number", info["volume"]))
        lines.append(kv("year", year))
        for k in ("doi", "url"):
            if info.get(k):
                lines.append(kv(k, info[k]))
        lines.append("}")

    else:  # edited volume
        lines = [f"@book{{{key},",
                 kv("editor",    authors),
                 kv("title",     title)]
        if info.get("publisher"):
            lines.append(kv("publisher", info["publisher"]))
        lines.append(kv("year", year))
        for k in ("doi", "url"):
            if info.get(k):
                lines.append(kv(k, info[k]))
        lines.append("}")

    return "\n".join(lines)

# ── HTML <li> building for publications ───────────────────────────────────────

def build_pub_li(pub_type, title, authors, year, info):
    auth = fmt_authors(authors)
    doi      = info.get("doi", "")
    url      = info.get("url", "")
    preprint = info.get("preprint", "")
    venue    = info.get("venue", "")

    link = f"https://doi.org/{doi}" if doi else url
    if link:
        title_html = (f'<a class="text-link" href="{link}"'
                      f' target="_blank" rel="noopener">{title}</a>')
    else:
        title_html = title

    preprint_html = ""
    if preprint:
        preprint_html = (f' [<a class="text-link" href="{preprint}"'
                         f' target="_blank" rel="noopener">preprint</a>]')

    if pub_type == "journal":
        venue_str = f"<em>{venue}</em>"
        if info.get("volume"):
            venue_str += f" {info['volume']}"
        if info.get("number"):
            venue_str += f"({info['number']})"
        if info.get("pages"):
            venue_str += f", {info['pages']}"
        body = f'{auth}. \u201c{title_html}\u201d. {venue_str}.{preprint_html}'

    elif pub_type == "chapter":
        pub = f", {info['publisher']}" if info.get("publisher") else ""
        body = f'{auth}. \u201c{title_html}\u201d. In <em>{venue}</em>{pub}.{preprint_html}'

    elif pub_type == "commentary":
        vol = f" {info['volume']}" if info.get("volume") else ""
        body = f'{auth}. \u201c{title_html}\u201d. <em>{venue}</em>{vol}.{preprint_html}'

    else:  # edited
        pub = f". {info['publisher']}, {year}" if info.get("publisher") else f", {year}"
        body = f'{auth} (eds.). <em>{title_html}</em>{pub}.'

    return f'        <li>\n          {body}\n        </li>'

# ── Insert into publications.html ─────────────────────────────────────────────

def insert_pub_html(year_str, pub_label, li_html):
    content = rfile(PUBS_HTML)

    year_h2  = f'<h2 class="pub-year">{year_str}</h2>'
    type_h3  = f'<h3 class="pub-type">{pub_label}</h3>'

    if year_h2 not in content:
        # Build a whole new year block
        year_comment = f"<!-- {year_str} -->"
        new_block = (
            f'      {year_comment}\n'
            f'      {year_h2}\n'
            f'      {type_h3}\n'
            f'      <ul class="pub-list">\n'
            f'{li_html}\n'
            f'      </ul>\n\n'
        )
        years_in_doc = sorted(
            [int(y) for y in re.findall(r'<h2 class="pub-year">(\d{4})</h2>', content)],
            reverse=True
        )
        inserted = False
        for ey in years_in_doc:
            if ey < int(year_str):
                marker = f"<!-- {ey} -->"
                if marker in content:
                    content = content.replace(marker, new_block + "      " + marker)
                    inserted = True
                    break
                h2 = f'<h2 class="pub-year">{ey}</h2>'
                content = content.replace(h2, new_block + "      " + h2)
                inserted = True
                break
        if not inserted:
            # Older than everything existing: put before </main>
            content = content.replace("    </main>", new_block + "    </main>")
        wfile(PUBS_HTML, content)
        return

    # Year exists — check whether the type section also exists within this year
    year_pos = content.find(year_h2)
    # Find the end of this year's block: next year h2 or </main>
    next_year = re.search(r'<h2 class="pub-year">', content[year_pos + 10:])
    year_block_end = year_pos + 10 + next_year.start() if next_year else len(content)
    year_block = content[year_pos:year_block_end]

    if type_h3 not in year_block:
        # Add a new type subsection inside this year block, before next year/</main>
        new_type = (f'      {type_h3}\n'
                    f'      <ul class="pub-list">\n'
                    f'{li_html}\n'
                    f'      </ul>\n\n')
        content = content[:year_block_end] + new_type + content[year_block_end:]
        # Move the new type inside the year block (just before its end)
        # Simpler: insert at year_block_end which already IS inside the year block
        wfile(PUBS_HTML, content)
        return

    # Both year and type exist: append the new <li> before the </ul> of that type
    type_pos = content.find(type_h3, year_pos)
    ul_start = content.find('<ul class="pub-list">', type_pos)
    ul_end   = content.find("</ul>", ul_start)

    content = content[:ul_end] + li_html + "\n      " + content[ul_end:]
    wfile(PUBS_HTML, content)

# ── Add publication ───────────────────────────────────────────────────────────

def add_publication():
    print("\n  Publication type:")
    for i, (_, label) in enumerate(PUB_TYPES, 1):
        print(f"    {i}. {label}")

    choice = ask("Choice (1–4)")
    if not choice.isdigit() or int(choice) not in range(1, 5):
        print("  Invalid choice."); return
    pub_type, pub_label = PUB_TYPES[int(choice) - 1]

    print()
    authors = ask("Authors  (BibTeX: 'Last, First and Last2, First2'; 'others' for et al.)")
    title   = ask("Title")
    year    = ask("Year")

    info = {}
    if pub_type in ("journal", "commentary"):
        info["venue"]  = ask("Journal name")
        info["volume"] = ask("Volume", default="")
        info["number"] = ask("Issue / number", default="")
        if pub_type == "journal":
            info["pages"] = ask("Pages", default="")
    elif pub_type == "chapter":
        info["venue"]     = ask("Book title")
        info["editor"]    = ask("Editor(s)", default="")
        info["publisher"] = ask("Publisher", default="")
    else:  # edited
        info["venue"]     = ask("Book title", default="")
        info["publisher"] = ask("Publisher", default="")

    info["doi"]      = ask("DOI (without https://doi.org/)", default="")
    info["url"]      = ask("URL (if no DOI)", default="")
    info["preprint"] = ask("Preprint URL", default="")

    default_key = authors.split(",")[0].strip().replace(" ", "") + year
    bib_key = ask("BibTeX key", default=default_key)

    # Write bib
    bib_text = build_bib(pub_type, bib_key, title, authors, year, info)
    with open(BIB[pub_type], "a", encoding="utf-8") as f:
        f.write("\n\n" + bib_text + "\n")
    print(f"\n  ✓ Bib entry added  →  CV/{os.path.basename(BIB[pub_type])}")

    # Write HTML
    li_html = build_pub_li(pub_type, title, authors, year, info)
    insert_pub_html(year, pub_label, li_html)
    print(f"  ✓ Entry added      →  publications.html")
    compile_cv()

# ── Insert into talks.html ────────────────────────────────────────────────────

def insert_talk_html(talk_date, display_date, title, venue, is_invited, is_poster):
    content  = rfile(TALKS_HTML)
    year     = str(talk_date.year)
    cls      = "talk-item " + ("invited" if is_invited else "poster")
    note     = " (poster)" if is_poster else ""
    date_str = talk_date.strftime("%Y-%m-%d")

    li = (f'        <li class="{cls}" data-date="{date_str}">\n'
          f'          <span class="talk-date">{display_date}</span>\n'
          f'          <span><strong>{title}</strong>{note} <br />{venue}</span>\n'
          f'        </li>')

    year_marker = f'<!-- year-{year} -->'

    if year_marker not in content:
        new_section = (
            f'      {year_marker}\n'
            f'      <h2>{year}</h2>\n'
            f'      <ul class="talk-list">\n'
            f'{li}\n'
            f'      </ul>\n'
            f'      <!-- /year-{year} -->\n\n'
        )
        existing_years = sorted(
            [int(m) for m in re.findall(r'<!-- year-(\d{4}) -->', content)],
            reverse=True
        )
        inserted = False
        for ey in existing_years:
            if ey < int(year):
                marker = f'<!-- year-{ey} -->'
                content = content.replace(marker, new_section + "      " + marker)
                inserted = True
                break
        if not inserted:
            content = content.replace("    </main>", new_section + "    </main>")
        wfile(TALKS_HTML, content)
        return

    # Year section exists: insert at correct date-descending position
    ym_pos        = content.find(year_marker)
    ul_open       = content.find('<ul class="talk-list">', ym_pos)
    ul_body_start = ul_open + len('<ul class="talk-list">')
    ul_end        = content.find("</ul>", ul_body_start)
    ul_body       = content[ul_body_start:ul_end]

    insert_before = None
    for m in re.finditer(r'data-date="(\d{4}-\d{2}-\d{2})"', ul_body):
        d = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        if d < talk_date:
            li_start = ul_body.rfind("<li", 0, m.start())
            insert_before = ul_body_start + li_start
            break

    if insert_before is not None:
        content = content[:insert_before] + li + "\n        " + content[insert_before:]
    else:
        content = content[:ul_end] + li + "\n        " + content[ul_end:]

    wfile(TALKS_HTML, content)

# ── Compile CV ───────────────────────────────────────────────────────────────

def compile_cv():
    cv_dir = os.path.join(SCRIPT_DIR, "CV")
    print("\n  Compiling CV …")
    try:
        for cmd in [
            ["pdflatex", "-interaction=nonstopmode", "CVnew.tex"],
            ["biber", "CVnew"],
            ["pdflatex", "-interaction=nonstopmode", "CVnew.tex"],
            ["pdflatex", "-interaction=nonstopmode", "CVnew.tex"],
        ]:
            result = subprocess.run(cmd, cwd=cv_dir, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  ⚠  '{' '.join(cmd)}' exited with code {result.returncode}")
                print(result.stdout[-2000:] if result.stdout else "")
                return False
        import shutil
        shutil.copy(
            os.path.join(cv_dir, "CVnew.pdf"),
            os.path.join(SCRIPT_DIR, "assets", "Piotr_Bystranowski_CV.pdf")
        )
        print("  ✓ CV compiled  →  assets/Piotr_Bystranowski_CV.pdf")
        return True
    except FileNotFoundError as e:
        print(f"  ⚠  Compile failed ({e}). Run manually: cd CV && bash compile_ref.sh")
        return False

# ── Insert into CVnew.tex ─────────────────────────────────────────────────────

def insert_talk_cv(year, title, venue):
    content = rfile(CV_TEX)

    def ltx(s):
        return s.replace("&", "\\&").replace("%", "\\%").replace("$", "\\$").replace("#", "\\#")

    new_talk = f"\n  \\talk{{{year}}}{{{ltx(title)}}}{{{ltx(venue)}}}\n"

    m = re.search(r'\\section\{Invited Talks\}.*?\\begin\{content\}', content, re.DOTALL)
    if not m:
        print("  ⚠  Could not find 'Invited Talks' section in CVnew.tex — add manually.")
        return

    content = content[:m.end()] + new_talk + content[m.end():]
    wfile(CV_TEX, content)

# ── Add talk ──────────────────────────────────────────────────────────────────

def add_talk():
    print()
    date_str     = ask("Date (YYYY-MM-DD; use last day for multi-day events)")
    display_date = ask("Display date (e.g. '7 May' or '5\u20137 Nov')")
    title        = ask("Title (use 'TBD' if not yet known)")
    venue        = ask("Venue / event (e.g. 'Knobe Lab Meeting, Yale University, New Haven, USA')")
    is_invited   = ask_yn("Invited talk?", default=True)
    is_poster    = False
    if not is_invited:
        is_poster = ask_yn("Poster?", default=False)

    try:
        talk_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print("  Invalid date format — use YYYY-MM-DD."); return

    insert_talk_html(talk_date, display_date, title, venue, is_invited, is_poster)
    print(f"\n  ✓ Talk added  →  talks.html")

    if is_invited:
        insert_talk_cv(talk_date.year, title, venue)
        print(f"  ✓ Talk added  →  CV/CVnew.tex")
        compile_cv()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n  ┌─────────────────────────────────┐")
    print("  │  Website + CV updater           │")
    print("  └─────────────────────────────────┘")
    print("    1. Add publication")
    print("    2. Add talk")
    choice = ask("\n  Choice").strip()
    if choice == "1":
        add_publication()
    elif choice == "2":
        add_talk()
    else:
        print("  Bye!")

if __name__ == "__main__":
    main()
