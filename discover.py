import os
import re
import time
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import requests
from bs4 import BeautifulSoup
PROJECT_NAME = os.getenv("PROJECT_NAME", "lead_project").strip()
LOCATIONS_FILE = os.getenv("LOCATIONS_FILE", "lead_locations.txt")
KEYWORDS_FILE = os.getenv("KEYWORDS_FILE", "lead_keywords.txt")
OUTPUT_FILE = os.getenv("DISCOVERY_OUTPUT_FILE", f"{PROJECT_NAME}_discovered.csv")
EXCLUDE_DOMAINS_FILE = os.getenv("EXCLUDE_DOMAINS_FILE", "").strip()
SCRAPEDO_TOKEN = os.getenv("SCRAPEDO_TOKEN", "").strip().strip("'\"")
MAX_RESULTS_PER_QUERY = int(os.getenv("MAX_RESULTS_PER_QUERY", "30") or "30")
SEARCH_START_RESULT = int(os.getenv("SEARCH_START_RESULT", "0") or "0")
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", "2") or "2")
SKIP_COMPLETED_QUERIES = os.getenv("SKIP_COMPLETED_QUERIES", "1").strip() == "1"
SKIP_DOMAINS = [
    "google.",
    "youtube.com",
    "youtu.be",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "pinterest.com",
    "wikipedia.org",
]
class DiscoveryQuotaError(RuntimeError):
    pass
def read_lines(path: str) -> List[str]:
    if not os.path.exists(path):
        raise SystemExit(f"Missing file: {path}")
    values = []
    with open(path, "r", encoding="utf-8-sig") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#"):
                values.append(line)
    return values
def normalize_url(url: str) -> Optional[str]:
    if not url:
        return None
    url = urllib.parse.unquote(str(url).strip())
    if not url:
        return None
    if url.startswith("//"):
        url = "https:" + url
    if not re.match(r"^https?://", url, flags=re.I):
        url = "https://" + url
    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc:
        return None
    return parsed._replace(fragment="", query="").geturl().rstrip("/")
def domain_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()
    return domain[4:] if domain.startswith("www.") else domain
def should_skip_url(url: str) -> bool:
    domain = domain_from_url(url)
    return any(skip in domain for skip in SKIP_DOMAINS)
def load_excluded_domains(path: str) -> set:
    if not path:
        return set()
    if not os.path.exists(path):
        raise SystemExit(f"Missing exclude domains file: {path}")
    return {line.lower().strip() for line in read_lines(path)}
def fetch_google_html(search_url: str) -> str:
    if not SCRAPEDO_TOKEN:
        raise RuntimeError("Missing SCRAPEDO_TOKEN environment variable.")
    if SCRAPEDO_TOKEN == "your_scrapedo_token":
        raise RuntimeError("SCRAPEDO_TOKEN is still set to the placeholder value.")
    encoded_url = urllib.parse.quote(search_url, safe="")
    scrape_url = f"https://api.scrape.do/?token={SCRAPEDO_TOKEN}&url={encoded_url}&super=true"
    response = requests.get(scrape_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    if response.status_code == 401:
        raise DiscoveryQuotaError("Scrape.do returned 401 Unauthorized. Token or quota is exhausted.")
    if response.status_code in {402, 403, 429}:
        raise DiscoveryQuotaError(
            f"Scrape.do returned {response.status_code}. Token, quota, or rate limit stopped discovery."
        )
    response.raise_for_status()
    return response.text
def search_google(query: str, max_results: int, start_result: int = 0) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    seen_domains = set()
    for start in range(start_result, max_results, 10):
        params = urllib.parse.urlencode({"q": query, "start": start})
        google_url = f"https://www.google.com/search?{params}"
        try:
            html = fetch_google_html(google_url)
        except DiscoveryQuotaError:
            raise
        except Exception as exc:
            print(f"  Google fetch failed: {exc}")
            continue
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            link = None
            if href.startswith("/url?"):
                parsed_href = urllib.parse.urlparse(href)
                query_params = urllib.parse.parse_qs(parsed_href.query)
                link = query_params.get("q", [None])[0]
            elif href.startswith("http"):
                link = href
            link = normalize_url(link) if link else None
            if not link or should_skip_url(link):
                continue
            domain = domain_from_url(link)
            if domain in seen_domains:
                continue
            seen_domains.add(domain)
            results.append({"name": domain, "website": link, "source_url": google_url})
            if len(results) >= max_results:
                break
        if len(results) >= max_results:
            break
        time.sleep(REQUEST_DELAY_SECONDS)
    return results
def load_existing_leads(output_file: str) -> List[Dict[str, str]]:
    if not os.path.exists(output_file):
        return []
    df = pd.read_csv(output_file).fillna("")
    print(f"Resuming existing file with {len(df)} rows: {output_file}")
    return df.to_dict("records")
def save_leads(leads: List[Dict[str, str]], output_file: str) -> None:
    columns = [
        "Location",
        "Name",
        "Website",
        "Domain",
        "Source",
        "Source_Query",
        "Source_URL",
        "Discovered_At",
    ]
    pd.DataFrame(leads, columns=columns).to_csv(output_file, index=False)
def completed_queries_from_leads(leads: List[Dict[str, str]]) -> set:
    completed = set()
    for row in leads:
        location = str(row.get("Location", "")).strip()
        source_query = str(row.get("Source_Query", "")).strip()
        if location and source_query:
            completed.add((location, source_query))
    return completed
def add_lead(
    leads: List[Dict[str, str]],
    seen_domains: set,
    excluded_domains: set,
    location: str,
    name: str,
    website: str,
    source: str,
    source_query: str,
    source_url: str,
) -> bool:
    website = normalize_url(website)
    if not website or should_skip_url(website):
        return False
    domain = domain_from_url(website)
    if domain in excluded_domains:
        return False
    domain_key = (location.lower(), domain)
    if domain_key in seen_domains:
        return False
    seen_domains.add(domain_key)
    leads.append(
        {
            "Location": location,
            "Name": name or domain,
            "Website": website,
            "Domain": domain,
            "Source": "Google Search",
            "Source_Query": source_query,
            "Source_URL": source_url,
            "Discovered_At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    return True
def main() -> None:
    locations = read_lines(LOCATIONS_FILE)
    keywords = read_lines(KEYWORDS_FILE)
    excluded_domains = load_excluded_domains(EXCLUDE_DOMAINS_FILE)
    leads = load_existing_leads(OUTPUT_FILE)
    completed_queries = completed_queries_from_leads(leads)
    seen_domains = {
        (
            str(row.get("Location", "")).strip().lower(),
            str(row.get("Domain") or domain_from_url(str(row.get("Website", "")))).strip().lower(),
        )
        for row in leads
        if row.get("Website")
    }
    print("\n--- GENERIC LEAD DISCOVERY ---")
    print(f"Project: {PROJECT_NAME}")
    print(f"Output file: {OUTPUT_FILE}")
    print(f"Locations: {len(locations)}")
    print(f"Keywords: {len(keywords)}")
    print(f"Search result range: {SEARCH_START_RESULT} to {MAX_RESULTS_PER_QUERY}")
    print(f"Excluded domains: {len(excluded_domains)}")
    try:
        for location in locations:
            print(f"\n=== {location} ===")
            for keyword in keywords:
                full_query = f"{keyword} in {location}"
                if SKIP_COMPLETED_QUERIES and (location, full_query) in completed_queries:
                    print(f"[SKIP] {full_query} already has saved results")
                    continue
                print(f"[GOOGLE] {full_query}")
                found = search_google(
                    full_query,
                    max_results=MAX_RESULTS_PER_QUERY,
                    start_result=SEARCH_START_RESULT,
                )
                added = 0
                for item in found:
                    if add_lead(
                        leads=leads,
                        seen_domains=seen_domains,
                        excluded_domains=excluded_domains,
                        location=location,
                        name=item["name"],
                        website=item["website"],
                        source="Google Search",
                        source_query=full_query,
                        source_url=item["source_url"],
                    ):
                        added += 1
                print(f"  Added {added} new websites")
                save_leads(leads, OUTPUT_FILE)
                if found:
                    completed_queries.add((location, full_query))
                time.sleep(REQUEST_DELAY_SECONDS)
    except DiscoveryQuotaError as exc:
        save_leads(leads, OUTPUT_FILE)
        print(f"\nSTOPPED: {exc}")
        print(f"Progress saved: {OUTPUT_FILE}")
        print("Fix the token/quota, then rerun this script to resume.")
        return
    save_leads(leads, OUTPUT_FILE)
    print(f"\nDone. Total discovered websites: {len(leads)}")
    print(f"Saved: {OUTPUT_FILE}")
if __name__ == "__main__":
    main()
