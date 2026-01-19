#!/usr/bin/env python3
import argparse, csv, re, time, sys
from pathlib import Path
import fitz  # pip install pymupdf
import requests

DOI_RE = re.compile(r'10\.\d{4,9}/\S+\b', re.I)

def find_doi(pdf_path, max_pages=3):
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None
    text = []
    for i in range(min(max_pages, len(doc))):
        try:
            text.append(doc[i].get_text() or "")
        except Exception:
            pass
    m = DOI_RE.search("\n".join(text))
    if not m:
        return None
    return m.group(0).rstrip(').,;]')

def guess_title_local(pdf_path):
    try:
        doc = fitz.open(pdf_path)
    except Exception:
        return None
    meta = (doc.metadata or {}).get("title", "")
    if meta and meta.strip() and not meta.strip().lower().startswith("microsoft word"):
        return meta.strip()

    try:
        page = doc[0]
        blocks = page.get_text("dict")["blocks"]
    except Exception:
        return None

    candidates = []
    for b in blocks:
        for l in b.get("lines", []):
            for s in l.get("spans", []):
                txt = (s.get("text") or "").strip()
                if len(txt) < 6:
                    continue
                lower = txt.lower()
                if any(k in lower for k in ["doi:", "http", "arxiv", "issn", "license", "copyright"]):
                    continue
                candidates.append((s.get("size", 0), s.get("bbox", [0, 9999])[1], txt))
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][2] if candidates else None

def title_via_crossref(doi, mailto=None, throttle=0.15):
    headers, params = {}, {}
    if mailto:
        params["mailto"] = mailto
        headers["User-Agent"] = f"doi-title-extractor/1.0 (mailto:{mailto})"
    url = f"https://api.crossref.org/works/{doi}"
    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
        if throttle:
            time.sleep(throttle)
        r.raise_for_status()
        msg = r.json().get("message", {})
        titles = msg.get("title", [])
        return " ".join(titles).strip() if titles else None
    except Exception:
        return None

def process_folder(folder, out_csv, log_file, mailto=None):
    folder = Path(folder)
    pdfs = sorted(folder.rglob("*.pdf"))

    out_csv = Path(out_csv)
    log_file = Path(log_file)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    with out_csv.open("w", newline="", encoding="utf-8") as f_csv, \
         log_file.open("w", encoding="utf-8") as f_log:

        w = csv.writer(f_csv)
        w.writerow(["title", "doi", "filename"])

        for idx, pdf in enumerate(pdfs, 1):
            doi = find_doi(pdf)
            title = None
            if doi and mailto:
                title = title_via_crossref(doi, mailto=mailto)
            if not title:
                title = guess_title_local(pdf)
            if not title:
                title = pdf.stem

            filename = str(pdf.relative_to(folder))
            w.writerow([title, doi or "", filename])
            f_csv.flush()  # flush after each write

            # log what we wrote
            log_line = f"[{idx}/{len(pdfs)}] TITLE: {title} | DOI: {doi or 'None'} | FILE: {filename}"
            print(log_line)
            f_log.write(log_line + "\n")
            f_log.flush()

def main():
    ap = argparse.ArgumentParser(description="Extract (title, DOI) from PDFs in a folder.")
    ap.add_argument("--folder", required=True, help="Path to folder containing PDFs")
    ap.add_argument("--out-csv", help="Output CSV path (default: <folder>/titles_to_dois.csv)")
    ap.add_argument("--mailto", help="Email for Crossref polite requests (optional)")
    args = ap.parse_args()
    folder_path = Path(args.folder)
    out_csv = args.out_csv or folder_path / "titles_to_dois.csv"
    log_file = folder_path / f"{folder_path.name}.log"

    process_folder(folder_path, out_csv, log_file, mailto=args.mailto)

if __name__ == "__main__":
    sys.exit(main())

