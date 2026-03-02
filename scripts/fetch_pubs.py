#!/usr/bin/env python
"""
Fetch all publications by Garavito-Camargo from the ADS API and generate
a LaTeX publication list following the CV.tex style.

Usage:
    python fetch_pubs.py

Output:
    pubs_auto.tex  – a standalone LaTeX document with the full publication list.
"""

import os
import requests
from urllib.parse import urlencode
from datetime import datetime

# ── ADS API configuration ────────────────────────────────────────────────
ADS_TOKEN = "vD4KKH0ZCkqFfKFkMJ9G5RlEzrw6lbg7EkU5bGOX"
ADS_SEARCH_URL = "https://api.adsabs.harvard.edu/v1/search/query"
HEADERS = {"Authorization": f"Bearer {ADS_TOKEN}"}

# Fields to retrieve
FIELDS = "title,author,pubdate,pub,citation_count,bibcode,doctype,year"

# ── Query ─────────────────────────────────────────────────────────────────
QUERY = 'author:"garavito-camargo" collection:astronomy'

# Maximum number of results per page (ADS max is 2000)
ROWS = 200


def fetch_all_papers():
    """Return a list of paper dicts from the ADS API."""
    params = {
        "q": QUERY,
        "fl": FIELDS,
        "rows": ROWS,
        "sort": "date desc",
    }
    encoded = urlencode(params)
    url = f"{ADS_SEARCH_URL}?{encoded}"

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    docs = data["response"]["docs"]
    num_found = data["response"]["numFound"]

    # Paginate if more results exist
    while len(docs) < num_found:
        params["start"] = len(docs)
        encoded = urlencode(params)
        url = f"{ADS_SEARCH_URL}?{encoded}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        docs.extend(response.json()["response"]["docs"])

    return docs


def escape_latex(text):
    """Escape special LaTeX characters and problematic Unicode in a string."""
    replacements = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "~": r"\textasciitilde{}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    # Replace Unicode characters that pdflatex cannot handle
    unicode_map = {
        "\u03b1": r"$\alpha$",       # α
        "\u2500": "--",               # ─ (box drawing)
        "\u2013": "--",               # – (en dash)
        "\u2014": "---",              # — (em dash)
        "\u2018": "`",               # '
        "\u2019": "'",               # '
        "\u201c": "``",              # \u201c
        "\u201d": "''",              # \u201d
    }
    for old, new in unicode_map.items():
        text = text.replace(old, new)
    return text


def format_authors(authors, max_authors=10):
    """
    Format the author list.  Bold 'Garavito-Camargo' variants.
    Truncate to *max_authors* and append 'et al.' if needed.
    """
    formatted = []
    for a in authors[:max_authors]:
        safe = escape_latex(a)
        # Bold any variant of the target author name
        if "garavito" in a.lower():
            safe = r"\textbf{" + safe + "}"
        formatted.append(safe)
    author_str = "; ".join(formatted)
    if len(authors) > max_authors:
        author_str += "; et al."
    return author_str


def format_date(pubdate):
    """Convert ADS pubdate (e.g. '2024-11-00') to a readable string."""
    try:
        parts = pubdate.split("-")
        year = parts[0]
        month = int(parts[1]) if len(parts) > 1 else 0
        if month > 0:
            month_name = datetime(2000, month, 1).strftime("%B")
            return f"{month_name} {year}"
        return year
    except Exception:
        return pubdate


def is_garavito_first(paper):
    """True if Garavito-Camargo is the first author."""
    authors = paper.get("author", [])
    return len(authors) > 0 and "garavito" in authors[0].lower()


def is_student_led(paper):
    """
    True if a supervised student (Darragh-Ford, Brooks, Arora) is
    first author AND Garavito-Camargo is second author.
    """
    authors = paper.get("author", [])
    if len(authors) < 2:
        return False
    first = authors[0].lower()
    second = authors[1].lower()
    student_names = ["darragh-ford", "brooks", "arora"]
    return (
        any(s in first for s in student_names)
        and "garavito" in second
    )


def is_proceeding(paper):
    """True for conference abstracts, proceedings, proposals, etc."""
    skip_types = {"abstract", "inproceedings", "proposal", "erratum",
                  "phdthesis", "dataset", "catalog"}
    return paper.get("doctype", "") in skip_types


def is_white_paper(paper):
    """True for BAAS white papers and known white-paper eprints."""
    pub = paper.get("pub", "").lower()
    title = paper.get("title", [""])[0].lower()
    # BAAS Decadal survey white papers
    if "bulletin of the american astronomical" in pub:
        return True
    # Known white paper eprints by title keywords
    if paper.get("doctype") == "eprint":
        wp_keywords = ["nancy", "rubin observatory", "from data to software"]
        if any(kw in title for kw in wp_keywords):
            return True
    return False


def is_in_press(paper):
    """
    True for arXiv e-prints that are submitted to a journal but not
    yet published (i.e. eprint doctype, excluding white papers).
    """
    return paper.get("doctype") == "eprint" and not is_white_paper(paper)


def build_latex(papers):
    """Return a complete LaTeX document string."""

    today_str = datetime.now().strftime("%B %d, %Y")

    # ── Categorise ────────────────────────────────────────────────────────
    # Refereed journal articles (doctype == "article"), excluding BAAS white papers
    refereed = [p for p in papers
                if p.get("doctype") == "article" and not is_white_paper(p)]

    # First-author & student-led (refereed)
    first_and_student = [p for p in refereed
                         if is_garavito_first(p) or is_student_led(p)]

    # Contributing-author refereed papers (everything else refereed)
    first_and_student_bibcodes = {p["bibcode"] for p in first_and_student}
    contributing = [p for p in refereed
                    if p["bibcode"] not in first_and_student_bibcodes]

    # In press (submitted eprints, not white papers)
    in_press = [p for p in papers if is_in_press(p)]

    # White papers (BAAS + known eprint white papers)
    white_papers = [p for p in papers if is_white_paper(p)]

    # ── Summary counts ────────────────────────────────────────────────────
    n_refereed = len(refereed)
    n_first = sum(1 for p in refereed if is_garavito_first(p))
    n_student = sum(1 for p in refereed if is_student_led(p))
    total_citations = sum(p.get("citation_count", 0) for p in refereed)

    # ── LaTeX preamble ────────────────────────────────────────────────────
    tex = r"""\documentclass[14pt]{article}
\usepackage{enumerate}
\usepackage[hmargin=2cm,vmargin=2cm]{geometry}
\usepackage[colorlinks=true]{hyperref}
\usepackage{url}
\usepackage{etaremune}
\usepackage{fancyhdr}
\usepackage{lastpage}
\usepackage[dvipsnames]{xcolor}
\usepackage{sectsty}
\usepackage[T1]{fontenc}

\hypersetup{
  colorlinks=True,
  linkcolor={red!50!black},
  citecolor={blue!50!black},
  urlcolor={Purple}}

\pagestyle{fancy}
\fancyhf{}
\lhead{Nicol\'as Garavito-Camargo}
\chead{Publications}
\rhead{\thepage}
\thispagestyle{empty}

\fancyfoot[C]{\textit{Last updated: \today}}

\begin{document}
\begin{center}
\indent \textbf{\LARGE Nicol\'as Garavito-Camargo -- Publications} \\
\indent \rule{17cm}{0.4pt}\\
\end{center}

\fontsize{11}{11}\selectfont

"""

    tex += f"\\section*{{Publications list}}\n\n"
    tex += (
        f"Refereed: {n_refereed} -- First author: {n_first} -- "
        f"Supervised students: {n_student} (denoted by \\dag) -- "
        f"Total citations: {total_citations} "
        f"(as of {today_str})\n\n"
    )
    tex += (
        r"\noindent \href{https://orcid.org/0000-0001-7107-1744}{ORCID}, "
        r"\href{https://ui.adsabs.harvard.edu/search/q=docs(library%2F0X5_bcuLT4iE-6-Nko0kmg)&sort=date%20desc%2C%20bibcode%20desc&p_=0}{ADS}, "
        r"\href{https://arxiv.org/search/?query=garavito-camargo&searchtype=all}{arXiv}, "
        r"\href{https://scholar.google.com/citations?user=QDLiOFYAAAAJ&hl=en&oi=ao}{Google Scholar}\\" + "\n\n"
    )

    # ── 1. In press / submitted ───────────────────────────────────────────
    if in_press:
        tex += r"\subsection*{In press}" + "\n\n"
        tex += r"\begin{etaremune}" + "\n"
        for paper in in_press:
            tex += format_paper_entry(paper, mark_student=True)
        tex += r"\end{etaremune}" + "\n\n"

    # ── 2. First author & student-led (refereed) ─────────────────────────
    if first_and_student:
        tex += r"\subsection*{First author and student-led publications}" + "\n\n"
        tex += r"\begin{etaremune}" + "\n"
        for paper in first_and_student:
            tex += format_paper_entry(paper, mark_student=True)
        tex += r"\end{etaremune}" + "\n\n"

    # ── 3. Publications as collaborator ───────────────────────────────────
    if contributing:
        tex += r"\subsection*{Publications as collaborator}" + "\n\n"
        tex += r"\begin{etaremune}" + "\n"
        for paper in contributing:
            tex += format_paper_entry(paper)
        tex += r"\end{etaremune}" + "\n\n"

    # ── 4. White papers ───────────────────────────────────────────────────
    if white_papers:
        tex += r"\subsection*{White papers}" + "\n\n"
        tex += r"\begin{etaremune}" + "\n"
        for paper in white_papers:
            tex += format_paper_entry(paper)
        tex += r"\end{etaremune}" + "\n\n"

    tex += r"\end{document}" + "\n"
    return tex


def format_paper_entry(paper, mark_student=False):
    """Format a single paper as an \\item in etaremune.

    If *mark_student* is True, student-led papers get a \dag prefix.
    """
    title = paper.get("title", ["Untitled"])[0]
    authors = paper.get("author", ["Unknown"])
    pubdate = paper.get("pubdate", "")
    journal = paper.get("pub", "")
    citations = paper.get("citation_count", 0)
    bibcode = paper.get("bibcode", "")

    ads_url = f"https://ui.adsabs.harvard.edu/abs/{bibcode}/abstract"

    title_escaped = escape_latex(title)
    journal_escaped = escape_latex(journal)
    author_str = format_authors(authors)
    date_str = format_date(pubdate)

    # Prefix with \dag for student-led papers
    prefix = ""
    if mark_student and is_student_led(paper):
        prefix = r"\dag\ "

    entry = f"\\item {prefix}\\textit{{\\href{{{ads_url}}}{{{title_escaped}}}}}\\\\\n"
    entry += (
        f"  {{\\small \\color{{darkgray}} {author_str}.\\\\\n"
        f"  {journal_escaped}, {date_str}. [{citations} citations]}}\n\n"
    )
    return entry


def main():
    print("Fetching papers from ADS …")
    papers = fetch_all_papers()
    print(f"  Found {len(papers)} papers.")

    # Sort by date descending (most recent first)
    papers.sort(key=lambda p: p.get("pubdate", "0000"), reverse=True)

    print("Generating LaTeX …")
    tex = build_latex(papers)

    root_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
    outfile = os.path.join(root_dir, "pubs_auto.tex")
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(tex)
    print(f"  Written to {outfile}")

    # Also print a quick summary
    refereed = [p for p in papers
                if p.get("doctype") == "article" and not is_white_paper(p)]
    first_student = [p for p in refereed
                     if is_garavito_first(p) or is_student_led(p)]
    in_press = [p for p in papers if is_in_press(p)]
    white_papers = [p for p in papers if is_white_paper(p)]
    contributing = [p for p in refereed
                    if p["bibcode"] not in {x["bibcode"] for x in first_student}]
    total_cit = sum(p.get("citation_count", 0) for p in refereed)

    print(f"\n  Refereed papers              : {len(refereed)}")
    print(f"  First author + student-led   : {len(first_student)}")
    print(f"  Contributing author          : {len(contributing)}")
    print(f"  In press (submitted eprints) : {len(in_press)}")
    print(f"  White papers                 : {len(white_papers)}")
    print(f"  Total citations (refereed)   : {total_cit}")


if __name__ == "__main__":
    main()
