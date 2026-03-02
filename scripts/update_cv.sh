#!/usr/bin/env bash
# update_cv.sh — Regenerate CV.tex with fresh ADS data and compile the PDF.
# Intended to be run monthly via cron.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CV_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$CV_DIR"

LOG="$CV_DIR/update_cv.log"

echo "===== $(date '+%Y-%m-%d %H:%M:%S') =====" >> "$LOG"

# 1. Generate CV.tex with updated publications and talk counts
echo "Generating CV.tex …" >> "$LOG"
python3 "$SCRIPT_DIR/generate_cv.py" >> "$LOG" 2>&1

# 2. Compile LaTeX (run twice for correct references/numbering)
echo "Compiling CV.tex …" >> "$LOG"
pdflatex -interaction=nonstopmode CV.tex >> "$LOG" 2>&1
pdflatex -interaction=nonstopmode CV.tex >> "$LOG" 2>&1

echo "Done. PDF: $CV_DIR/CV.pdf" >> "$LOG"
echo "" >> "$LOG"
