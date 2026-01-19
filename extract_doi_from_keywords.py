import requests, time
from datetime import date

def fetch_all_dois(query, output_file, start, end, mailto="email@gmail.com"):
    base_url = "https://api.crossref.org/works"
    cursor = "*"
    rows = 1000
    total_fetched, seen = 0, set()
    headers = {"User-Agent": f"doi-harvester/1.0 (mailto:{mailto})"}

    filt = f"type:journal-article,from-pub-date:{start},until-pub-date:{end}"

    with open(output_file, "w", encoding="utf-8") as f:
        while True:
            params = {
                "query": query,
                "rows": rows,
                "cursor": cursor,
                "filter": filt,
                "mailto": mailto,
            }
            for attempt in range(3):
                r = requests.get(base_url, params=params, headers=headers, timeout=30)
                if r.status_code == 200: break
                time.sleep(2*(attempt+1))
            if r.status_code != 200:
                print(f"Error {r.status_code}\nURL: {r.url}")
                break

            msg = r.json()["message"]
            items = msg.get("items", [])
            if not items:
                print("No more results."); break

            for it in items:
                doi = it.get("DOI")
                if doi and doi not in seen:
                    f.write(doi + "\n")
                    seen.add(doi); total_fetched += 1

            print(f"Fetched {total_fetched} DOIs so far...")
            cursor = msg.get("next-cursor")
            if not cursor:
                print("All pages retrieved."); break
            time.sleep(1)

    print(f"Done! Total journal DOIs saved: {total_fetched}")

if __name__ == "__main__":
    fetch_all_dois(
        "polymer molecular dynamics",
        output_file="dois_journal_1995_1999.txt",
        start="1995-01-01",
        end="1999-12-31", # Adjust this as per needed!
    )

