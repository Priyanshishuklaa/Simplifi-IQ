#!/usr/bin/env python3
"""
scrape_summarize.py
Reads a list of URLs from a file, fetches each page, extracts title + meta description + visible text,
and produces a CSV with an AI-based summary for each page. If a Gemini API key/endpoint is not provided,
the script will create a simple extractive summary as a fallback.

Usage:
    python scrape_summarize.py urls.txt output.csv
    - urls.txt may be a .txt (one URL per line), .csv (column "url"), or .xlsx (column "url").
    - output.csv is the path to write the structured CSV results.

Environment variables (optional):
    GEMINI_API_KEY  - set this to your Gemini API key (if you want AI summaries)
    GEMINI_API_URL  - set this to the Gemini API endpoint for text generation (if available)

Notes for the assessment:
- The script uses requests + BeautifulSoup to fetch and parse webpages.
- The AI call is a generic HTTP POST to the provided GEMINI_API_URL using Bearer authentication.
  Replace GEMINI_API_URL with the correct endpoint and request format for your Gemini API/key.
- If no API key is available the script uses a local extractive summary method (frequency-based)
  so the script always produces useful output.
"""

import os
import sys
import time
import csv
import math
import argparse
from pathlib import Path
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
from collections import Counter, defaultdict

# --------------------------- Utilities ---------------------------------

def read_urls(input_path: str) -> List[str]:
    """Read URLs from .txt (one-per-line), .csv (column 'url'), or .xlsx (column 'url')."""
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if p.suffix.lower() in ('.txt',):
        with p.open('r', encoding='utf8') as f:
            urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        return urls
    elif p.suffix.lower() in ('.csv',):
        df = pd.read_csv(p)
        if 'url' not in df.columns:
            raise ValueError("CSV must have a column named 'url'")
        return df['url'].dropna().astype(str).tolist()
    elif p.suffix.lower() in ('.xlsx', '.xls'):
        df = pd.read_excel(p)
        if 'url' not in df.columns:
            raise ValueError("Excel file must have a column named 'url'")
        return df['url'].dropna().astype(str).tolist()
    else:
        raise ValueError("Unsupported file type. Use .txt, .csv, or .xlsx")

def fetch_page(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch a webpage and return its HTML text or None on failure."""
    headers = {
        "User-Agent": "SimplifiIQ-Agent/1.0 (+https://example.com)"
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"[WARN] Failed to fetch {url}: {e}", file=sys.stderr)
        return None

def extract_text_and_meta(html: str) -> Dict[str, str]:
    """Extract <title>, meta description, and visible text from HTML."""
    soup = BeautifulSoup(html, 'html.parser')

    title = soup.title.string.strip() if soup.title and soup.title.string else ''

    # meta description
    meta_desc_tag = soup.find('meta', attrs={'name':'description'}) or soup.find('meta', attrs={'property':'og:description'})
    meta_description = meta_desc_tag.get('content','').strip() if meta_desc_tag else ''

    # visible text: remove scripts/styles and collapse whitespace
    for s in soup(['script','style','noscript']):
        s.extract()
    text = soup.get_text(separator=' ')
    text = re.sub(r'\s+', ' ', text).strip()
    # keep a preview (first 800 characters)
    text_preview = text[:800]

    return {'title': title, 'meta_description': meta_description, 'text_preview': text_preview, 'full_text': text}

# -------------------- Simple local extractive summarizer -----------------

def simple_extractive_summary(text: str, max_sentences: int = 3) -> str:
    """Create a tiny extractive summary by scoring sentences on word frequency.
    This is a fallback when no AI API key is provided.
    """
    if not text:
        return ''
    # split into sentences naively
    sentences = re.split(r'(?<=[.!?])\s+', text)
    if len(sentences) <= max_sentences:
        return ' '.join(sentences).strip()

    # tokenize and compute word frequencies
    words = re.findall(r'\w+', text.lower())
    stopwords = set([
        'the','is','in','and','to','of','a','for','on','that','with','as','are','was','it','at','by','an','be','this','or','from'
    ])
    freqs = Counter([w for w in words if w not in stopwords and len(w) > 2])
    if not freqs:
        return ' '.join(sentences[:max_sentences]).strip()

    # score sentences
    sent_scores = []
    for s in sentences:
        s_words = re.findall(r'\w+', s.lower())
        score = sum(freqs.get(w,0) for w in s_words)
        sent_scores.append((score, s))
    # pick top sentences by score keeping original order
    top = sorted(sent_scores, key=lambda x: x[0], reverse=True)[:max_sentences]
    # sort by original position to keep coherent order
    top_set = set(t[1] for t in top)
    ordered = [s for s in sentences if s in top_set]
    summary = ' '.join(ordered).strip()
    return summary

# -------------------- Gemini API call (generic) ---------------------------

def call_gemini_api(prompt: str, api_key: str, api_url: str, timeout: int = 30) -> Optional[str]:
    """
    Generic HTTP POST to a Gemini-like API endpoint. The exact request/response
    shape depends on the API; adapt as needed for the real Gemini API.
    This function returns the raw text response (summary) or None on error.
    """
    if not api_key or not api_url:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "max_tokens": 300
    }
    try:
        resp = requests.post(api_url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        # The exact location of the generated text may differ. Here we try common keys.
        if isinstance(data, dict):
            if 'summary' in data:
                return data['summary']
            if 'choices' in data and isinstance(data['choices'], list) and len(data['choices'])>0:
                # openai-like response
                return data['choices'][0].get('text') or data['choices'][0].get('message',{}).get('content')
            if 'output' in data and isinstance(data['output'], str):
                return data['output']
        # fallback to raw text
        return resp.text
    except Exception as e:
        print(f"[WARN] Gemini API call failed: {e}", file=sys.stderr)
        return None

# -------------------- Main workflow -------------------------------------

def summarize_urls(urls: List[str], use_gemini: bool = True, gemini_api_key: Optional[str] = None, gemini_api_url: Optional[str] = None):
    results = []
    for i, url in enumerate(urls, start=1):
        print(f"[{i}/{len(urls)}] Processing: {url}")
        html = fetch_page(url)
        if not html:
            results.append({'url': url, 'title':'', 'meta_description':'', 'summary':'', 'notes':'fetch_failed'})
            continue
        info = extract_text_and_meta(html)
        title = info['title']
        meta_description = info['meta_description']
        preview = info['text_preview']

        # Build a prompt for the LLM
        prompt = f"Summarize the following webpage content in 2-3 short sentences. Keep it factual and concise.\n\nTitle: {title}\n\nMeta: {meta_description}\n\nContent preview: {preview}\n\nSummary:"

        summary = None
        notes = ''

        if use_gemini and gemini_api_key and gemini_api_url:
            summary = call_gemini_api(prompt, gemini_api_key, gemini_api_url)
            if summary:
                notes = 'generated_by_gemini'
            else:
                notes = 'gemini_failed_fallback_extractive'
                summary = simple_extractive_summary(preview)
        else:
            notes = 'no_gemini_local_extractive'
            summary = simple_extractive_summary(preview)

        results.append({
            'url': url,
            'title': title,
            'meta_description': meta_description,
            'summary': summary,
            'notes': notes
        })

        # polite pause to avoid hammering sites
        time.sleep(1.0)

    return results

def write_results_csv(results: List[Dict], out_path: str):
    df = pd.DataFrame(results)
    df.to_csv(out_path, index=False)
    print(f"[INFO] Results written to {out_path}")

# -------------------- CLI -----------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scrape webpages and summarize them (uses Gemini API if configured).")
    parser.add_argument('input', help="Input file (urls.txt, urls.csv, or urls.xlsx)")
    parser.add_argument('output', help="Output CSV file (e.g. summaries.csv)")
    parser.add_argument('--no-gemini', action='store_true', help="Do not call Gemini even if API key exists; use local summarizer")
    args = parser.parse_args()

    urls = read_urls(args.input)
    if not urls:
        print("[ERROR] No URLs found.", file=sys.stderr)
        sys.exit(1)

    gemini_key = os.getenv('GEMINI_API_KEY')
    gemini_url = os.getenv('GEMINI_API_URL')

    use_gemini = (not args.no_gemini) and bool(gemini_key) and bool(gemini_url)

    results = summarize_urls(urls, use_gemini=use_gemini, gemini_api_key=gemini_key, gemini_api_url=gemini_url)
    write_results_csv(results, args.output)

if __name__ == '__main__':
    main()
