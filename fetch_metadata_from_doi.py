#!/usr/bin/env python3
import sys
import requests
import pandas as pd
import time
import concurrent.futures

# Extraction from Semantic Scholar
def fetch_semantic(doi):
    base_url = f"https://api.semanticscholar.org/graph/v1/paper/DOI:{doi}"
    params = {"fields": "title,abstract,authors,year,url"}
    try:
        r = requests.get(base_url, params=params, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        return {
            "source": "Semantic Scholar",
            "Title": data.get("title"),
            "Abstract": data.get("abstract"),
            "Authors": ", ".join(a["name"] for a in data.get("authors", [])),
            "Year": data.get("year"),
            "URL": data.get("url")
        }
    except Exception:
        return None

# Extraction from Crossref
def fetch_crossref(doi):
    base_url = f"https://api.crossref.org/works/{doi}"
    headers = {"User-Agent": "DOI-Fetcher (mailto:your_email@example.com)"}
    try:
        r = requests.get(base_url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json().get("message", {})
        authors = data.get("author", [])
        authors = ", ".join(f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors)
        abstract = data.get("abstract")
        if abstract:
            abstract = abstract.replace("<jats:p>", "").replace("</jats:p>", "").strip()
        return {
            "source": "Crossref",
            "Title": data.get("title", [""])[0],
            "Abstract": abstract,
            "Authors": authors,
            "Year": data.get("issued", {}).get("date-parts", [[None]])[0][0],
            "URL": data.get("URL")
        }
    except Exception:
        return None


# Extraction from opneALex
def fetch_openalex(doi):
    doi = doi.lower().strip()
    base_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
    try:
        r = requests.get(base_url, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        title = data.get("title")
        abstract = data.get("abstract_inverted_index")
        if abstract:
            pos_to_word = {}
            for word, positions in abstract.items():
                for pos in positions:
                    pos_to_word[pos] = word
            abstract = " ".join([pos_to_word[i] for i in sorted(pos_to_word.keys())])
        authors = ", ".join(a["author"]["display_name"] for a in data.get("authorships", []))
        year = data.get("publication_year")
        url = data.get("id")
        return {
            "source": "OpenAlex",
            "Title": title,
            "Abstract": abstract,
            "Authors": authors,
            "Year": year,
            "URL": url
        }
    except Exception:
        return None

# Main function
def get_metadata_from_doi(doi):
    """Try Semantic Scholar - Crossref - OpenAlex."""
    for fetcher in (fetch_semantic, fetch_crossref, fetch_openalex):
        meta = fetcher(doi)
        if meta and meta.get("Title"):
            return {"DOI": doi, **meta}
    return {
        "DOI": doi,
        "Title": None,
        "Abstract": None,
        "Authors": None,
        "Year": None,
        "URL": None,
        "source": None
    }


 # Entry point
if __name__ == "__main__":
    # Read command-line arguments
    input_file = sys.argv[1] if len(sys.argv) > 1 else "dois.txt"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "doi_metadata_all_sources.csv"

    with open(input_file) as f:
        dois = [line.strip() for line in f if line.strip()]

    MAX_WORKERS = 8  # match SLURM -c cores per task
    print(f"Processing {len(dois)} DOIs from {input_file} using {MAX_WORKERS} threads")

    # Function to handle one DOI 
    def process_doi(doi):
        try:
            meta = get_metadata_from_doi(doi)
            print(f"{doi} — {meta['Title']} (source: {meta['source']})")
            return meta
        except Exception as e:
            print(f"Error processing {doi}: {e}")
            return {"DOI": doi, "Title": None, "Abstract": None, "Authors": None,
                    "Year": None, "URL": None, "source": None}

    # Parallel execution
    results = []
    start = time.time()

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for meta in executor.map(process_doi, dois):
            results.append(meta)

    # Save results
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    print(f"\nSaved {len(df)} records to {output_file}")
    print(f"Elapsed time: {time.time() - start:.2f} seconds")

