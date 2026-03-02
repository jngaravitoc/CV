#!/usr/bin/env python
"""
Generate the full CV.tex by combining the static CV content with
automatically-fetched publications from the ADS API.

Everything in CV.tex above the marker line
    %%%%%%%%%%%%%%% Publications %%%%%%%%%%%%%%%%%%%%%
is preserved. The publications section (and white papers + \\end{document})
is regenerated from ADS data.

Usage:
    python generate_cv.py          # writes CV.tex in place
    python generate_cv.py --dry    # writes to CV_preview.tex instead

Requires:  fetch_pubs.py  (in the same directory)
"""

import re
import sys
import os
from datetime import datetime

# Import helpers from fetch_pubs.py (same directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_pubs import (
    fetch_all_papers,
    escape_latex,
    format_authors,
    format_date,
    format_paper_entry,
    is_garavito_first,
    is_student_led,
    is_proceeding,
    is_white_paper,
    is_in_press,
)

# ── Configuration ─────────────────────────────────────────────────────────
ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir)
CV_FILE = os.path.join(ROOT_DIR, "CV.tex")
MARKER = "%%%%%%%%%%%%%%% Publications %%%%%%%%%%%%%%%%%%%%%"


def count_talks(text):
    """Count total and invited talks in the Scientific Talks section.

    Returns (total, invited, conf_total, conf_invited, sem_total, sem_invited).
    Invited talks are \\item lines whose text ends with \\dag (possibly
    followed by whitespace).
    """
    # Extract the Scientific Talks section (up to the next \section*)
    m = re.search(
        r"\\section\*\{Scientific Talks\}(.*?)(?=\\section\*)",
        text,
        re.DOTALL,
    )
    if not m:
        return 0, 0, 0, 0, 0, 0

    talks_block = m.group(1)

    # Split into Conferences and Seminars sub-blocks
    conf_m = re.search(
        r"\\subsection\*\{Conferences.*?\}(.*?)(?=\\subsection\*|$)",
        talks_block,
        re.DOTALL,
    )
    sem_m = re.search(
        r"\\subsection\*\{Seminars.*?\}(.*?)(?=\\subsection\*|$)",
        talks_block,
        re.DOTALL,
    )

    def _count(block):
        items = re.findall(r"\\item\b(.*?)(?=\\item|\\end\{itemize\})", block, re.DOTALL)
        total = len(items)
        invited = sum(
            1 for it in items if re.search(r"\\dag\s*$", it.strip())
        )
        return total, invited

    conf_total, conf_invited = _count(conf_m.group(1)) if conf_m else (0, 0)
    sem_total, sem_invited = _count(sem_m.group(1)) if sem_m else (0, 0)

    total = conf_total + sem_total
    invited = conf_invited + sem_invited
    return total, invited, conf_total, conf_invited, sem_total, sem_invited


def update_talk_counts(text):
    """Replace hardcoded talk statistics with auto-counted values."""
    total, invited, conf_total, _, sem_total, _ = count_talks(text)
    if total == 0:
        return text  # nothing to update

    # Update the summary line: "57 Total: 27 Invited (denoted by \dag)\\"
    text = re.sub(
        r"\d+ Total: \d+ Invited \(denoted by \\dag\)",
        f"{total} Total: {invited} Invited (denoted by \\\\dag)",
        text,
    )
    # Update subsection headers: "Conferences (18)" and "Seminars and Colloquia (39)"
    text = re.sub(
        r"(\\subsection\*\{Conferences)\s*\(\d+\)",
        rf"\1 ({conf_total})",
        text,
    )
    text = re.sub(
        r"(\\subsection\*\{Seminars and Colloquia)\s*\(\d+\)",
        rf"\1 ({sem_total})",
        text,
    )
    return text


def remove_posters_section(text):
    """Remove the \\section*{Posters} block (up to the next \\section*)."""
    text = re.sub(
        r"\\section\*\{Posters\}.*?(?=\\section\*)",
        "",
        text,
        flags=re.DOTALL,
    )
    return text


def read_static_cv():
    """Read CV.tex up to the publications marker, update talk counts,
    and remove the Posters section."""
    with open(CV_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    static_lines = []
    for line in lines:
        static_lines.append(line)
        if MARKER in line:
            break
    else:
        raise RuntimeError(
            f"Marker line not found in {CV_FILE}:\n  {MARKER}\n"
            "Please ensure it exists before the publications section."
        )

    static_text = "".join(static_lines)
    static_text = update_talk_counts(static_text)
    static_text = remove_posters_section(static_text)
    return static_text


def build_publications_section(papers):
    """
    Build the publications + white papers LaTeX sections from ADS data.
    Returns a string to be appended after the static CV content.
    """
    today_str = datetime.now().strftime("%B %d, %Y")

    # ── Categorise ────────────────────────────────────────────────────────
    refereed = [
        p for p in papers
        if p.get("doctype") == "article" and not is_white_paper(p)
    ]
    first_and_student = [
        p for p in refereed
        if is_garavito_first(p) or is_student_led(p)
    ]
    first_and_student_bibcodes = {p["bibcode"] for p in first_and_student}
    contributing = [
        p for p in refereed
        if p["bibcode"] not in first_and_student_bibcodes
    ]
    in_press = [p for p in papers if is_in_press(p)]
    white_papers = [p for p in papers if is_white_paper(p)]

    # ── Summary counts ────────────────────────────────────────────────────
    n_refereed = len(refereed)
    n_first = sum(1 for p in refereed if is_garavito_first(p))
    n_student = sum(1 for p in refereed if is_student_led(p))
    total_citations = sum(p.get("citation_count", 0) for p in refereed)

    # ── Build LaTeX ───────────────────────────────────────────────────────
    tex = "\n"
    tex += r"\section*{Publications list}" + "\n\n"
    tex += (
        f"Refereed: {n_refereed} -- First author: {n_first} -- "
        f"Supervised students: {n_student} (denoted by \\dag) -- "
        f"Total citations: {total_citations} "
        f"(as of {today_str})\n\n"
    )
    tex += (
        r"\noindent \href{https://orcid.org/0000-0001-7107-1744}{ORCID},"
        + "\n"
        + r"\href{https://ui.adsabs.harvard.edu/search/q=docs(library%2F0X5_bcuLT4iE-6-Nko0kmg)&sort=date%20desc%2C%20bibcode%20desc&p_=0}{ADS},"
        + "\n"
        + r"\href{https://arxiv.org/search/?query=garavito-camargo&searchtype=all}{arXiv},"
        + "\n"
        + r"\href{https://scholar.google.com/citations?user=QDLiOFYAAAAJ&hl=en&oi=ao}{Google Scholar}\\"
        + "\n\n"
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
        tex += (
            r"\subsection*{First author and student-led publications}"
            + "\n\n"
        )
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
        tex += r"\section*{White papers}" + "\n\n"
        tex += r"\begin{etaremune}" + "\n"
        for paper in white_papers:
            tex += format_paper_entry(paper)
        tex += r"\end{etaremune}" + "\n\n"

    tex += "\n" + r"\end{document}" + "\n"
    return tex


def main():
    dry_run = "--dry" in sys.argv

    print("Reading static CV content …")
    # Read raw content first to count talks before any modifications
    with open(CV_FILE, "r", encoding="utf-8") as f:
        raw_cv = f.read()
    total_talks, invited_talks, conf, _, sem, _ = count_talks(raw_cv)
    print(f"  Talks: {total_talks} total, {invited_talks} invited "
          f"(Conferences: {conf}, Seminars: {sem})")

    static_content = read_static_cv()

    print("Fetching papers from ADS …")
    papers = fetch_all_papers()
    print(f"  Found {len(papers)} papers.")

    # Sort by date descending
    papers.sort(key=lambda p: p.get("pubdate", "0000"), reverse=True)

    print("Building publications section …")
    pubs_section = build_publications_section(papers)

    full_cv = static_content + pubs_section

    if dry_run:
        outfile = os.path.join(ROOT_DIR, "CV_preview.tex")
    else:
        outfile = CV_FILE
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(full_cv)

    label = "(preview)" if dry_run else ""
    print(f"  Written to {outfile} {label}")

    # Quick summary
    refereed = [
        p for p in papers
        if p.get("doctype") == "article" and not is_white_paper(p)
    ]
    first_student = [
        p for p in refereed
        if is_garavito_first(p) or is_student_led(p)
    ]
    in_press = [p for p in papers if is_in_press(p)]
    white_papers = [p for p in papers if is_white_paper(p)]
    contributing = [
        p for p in refereed
        if p["bibcode"] not in {x["bibcode"] for x in first_student}
    ]
    total_cit = sum(p.get("citation_count", 0) for p in refereed)

    print(f"\n  Refereed papers              : {len(refereed)}")
    print(f"  First author + student-led   : {len(first_student)}")
    print(f"  Contributing author          : {len(contributing)}")
    print(f"  In press (submitted eprints) : {len(in_press)}")
    print(f"  White papers                 : {len(white_papers)}")
    print(f"  Total citations (refereed)   : {total_cit}")


if __name__ == "__main__":
    main()
