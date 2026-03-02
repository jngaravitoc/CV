#!/usr/bin/env bash
# update_pubs.sh — Fetch publications from ADS and compile the PDF.
# Intended to be run monthly via cron.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CV_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$CV_DIR"

LOG="$CV_DIR/update_pubs.log"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$LOG"

# 1. Fetch papers and generate standalone pubs_auto.tex
echo "Fetching publications …" >> "$LOG"
python3 "$SCRIPT_DIR/fetch_pubs.py" >> "$LOG" 2>&1

# 2. Generate full CV.tex with updated publications
echo "Generating CV.tex …" >> "$LOG"
python3 "$SCRIPT_DIR/generate_cv.py" >> "$LOG" 2>&1

# 3. Compile LaTeX (run twice for correct references/numbering)
echo "Compiling pubs_auto.tex …" >> "$LOG"
pdflatex -interaction=nonstopmode pubs_auto.tex >> "$LOG" 2>&1
pdflatex -interaction=nonstopmode pubs_auto.tex >> "$LOG" 2>&1

echo "Compiling CV.tex …" >> "$LOG"
pdflatex -interaction=nonstopmode CV.tex >> "$LOG" 2>&1
pdflatex -interaction=nonstopmode CV.tex >> "$LOG" 2>&1

echo "Done. PDFs: $CV_DIR/{pubs_auto,CV}.pdf" >> "$LOG"
echo "" >> "$LOG"
