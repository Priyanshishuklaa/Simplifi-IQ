# Simplifi-IQ Assessment Submission (Parts A & B)

## Contents
- `analyze_logs.py` or `analyze_logs_with_overall_summary.py` — Part A script to analyze task logs and produce summary CSVs (time per user, time per task, top-3 tasks, invalid rows).  
- `task_logs_sample.csv` — sample input CSV (8 rows with a few invalid rows).  
- `summary_report.csv` — combined overall summary produced by Part A script.  
- `scrape_summarize.py` — Part B script that reads URLs, scrapes pages, and summarizes content (uses Gemini API if configured, otherwise a local extractive summarizer).  
- `urls.txt` — sample URL list for Part B.  
- `summaries.csv` — example output (generate locally by running the script).  
- `requirements.txt` — Python dependencies.
- `README.md` — this file.
- `reflection.txt` — short reflection (<=300 words).
- `ai_assist_log.txt` — log of AI assistance prompts and use (if any).

---

## How to run (setup)
1. Create a Python 3 virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate    # Windows (PowerShell)
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Dependencies:
- requests
- beautifulsoup4
- pandas
- openpyxl

---

## Part A — Analyze task logs
**Files:** `analyze_logs_with_overall_summary.py`, `task_logs_sample.csv`

Run (default names):
```bash
python analyze_logs_with_overall_summary.py task_logs_sample.csv summary_report.csv
```
- The script reads the CSV, cleans data (invalid timestamps -> NaT, non-numeric durations -> NaN, negative durations excluded), aggregates totals, and writes a combined `summary_report.csv` with sections.  
- It also prints short summaries to the console.

Outputs produced (examples):
- `summary_time_per_user.csv` (optional separate outputs)
- `summary_time_per_task.csv`
- `summary_top3_tasks.csv`
- `summary_invalid_rows.csv`
- `summary_report.csv` (single combined file)

Assumptions & choices:
- Negative durations are treated as data errors and excluded.
- Missing durations are excluded (not imputed).
- Timestamp parsing uses `pd.to_datetime(..., errors='coerce')`.

---

## Part B — Scrape and summarize
**Files:** `scrape_summarize.py`, `urls.txt`

Basic run (no Gemini):
```bash
python scrape_summarize.py urls.txt summaries.csv --no-gemini
```
This will:
- Read URLs from `urls.txt` (one per line).
- Fetch each page, extract `title`, meta description, and a short text preview.
- Use a local extractive summarizer to create a 2–3 sentence summary for each page.
- Write results to `summaries.csv` with columns: `url,title,meta_description,summary,notes`.

Use Gemini (optional):
1. Set environment variables:
```bash
export GEMINI_API_KEY="your_key_here"
export GEMINI_API_URL="https://YOUR_GEMINI_ENDPOINT"
```
2. Run (without `--no-gemini`):
```bash
python scrape_summarize.py urls.txt summaries.csv
```
Notes:
- The `call_gemini_api` function in the script is a generic HTTP POST. Adapt its request/response handling to match the real Gemini API schema if needed.
- Be polite to websites: the script waits 1 second between requests.

---

