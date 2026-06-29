from __future__ import annotations

import csv
import json
import os
import re
import threading
import time
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError

from lead_generator import (
    Enrichment,
    Lead,
    csv_columns,
    discover_contact_details,
    lead_to_rows,
    search_places,
)


ROOT_DIR = Path(__file__).resolve().parent
STATIC_DIR = ROOT_DIR / "web"
OUTPUT_DIR = ROOT_DIR / "exports"
SETTINGS_PATH = ROOT_DIR / "app_settings.json"
HOST = "127.0.0.1"
PORT = int(os.getenv("PORT", os.getenv("LEAD_APP_PORT", "8765")))

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def make_job_id() -> str:
    return f"job-{int(time.time() * 1000)}"


def safe_filename(text: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return name[:70] or "leads"


def set_job(job_id: str, **updates) -> None:
    with JOBS_LOCK:
        job = JOBS.setdefault(job_id, {})
        job.update(updates)


def get_job(job_id: str) -> dict | None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        return dict(job) if job else None


def load_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def saved_api_key() -> str:
    return str(load_settings().get("googleMapsApiKey", "")).strip()


def parse_queries(payload: dict) -> list[str]:
    raw_queries = str(payload.get("queries", "")).strip()
    if not raw_queries:
        raw_queries = str(payload.get("query", "")).strip()
    queries = [line.strip() for line in raw_queries.splitlines() if line.strip()]
    return list(dict.fromkeys(queries))


def place_dedupe_key(place) -> str:
    if place.place_id:
        return f"id:{place.place_id}"
    name = re.sub(r"[^a-z0-9]+", "", place.name.lower())
    address = re.sub(r"[^a-z0-9]+", "", place.address.lower())
    phone = re.sub(r"\D+", "", place.phone)
    website = re.sub(r"^https?://(www\.)?", "", place.website.lower()).rstrip("/")
    return f"business:{name}|{phone or website or address}"


def collect_places(api_key: str, queries: list[str], target: int, language: str | None) -> tuple[list, list[str]]:
    places_by_id = {}
    completed_queries = []
    for query in queries:
        if len(places_by_id) >= target:
            break
        per_query_limit = min(60, max(target - len(places_by_id), 20))
        for place in search_places(api_key, query, limit=per_query_limit, language_code=language):
            dedupe_key = place_dedupe_key(place)
            places_by_id.setdefault(dedupe_key, place)
            if len(places_by_id) >= target:
                break
        completed_queries.append(query)
    return list(places_by_id.values())[:target], completed_queries


def run_lead_job(job_id: str, payload: dict) -> None:
    queries = parse_queries(payload)
    api_key = str(payload.get("apiKey", "")).strip() or saved_api_key() or os.getenv("GOOGLE_MAPS_API_KEY", "")
    language = str(payload.get("language", "")).strip() or None
    limit = max(1, min(int(payload.get("limit", 25)), 100))
    max_pages = max(1, min(int(payload.get("maxPages", 4)), 10))
    delay = max(0.0, float(payload.get("delay", 1.0)))
    respect_robots = bool(payload.get("respectRobots", True))

    try:
        if not queries:
            raise ValueError("Enter at least one business search query.")
        if not api_key:
            raise ValueError("Add your Google Maps API key, save it in settings, or set GOOGLE_MAPS_API_KEY in PowerShell.")

        if bool(payload.get("saveApiKey", False)) and str(payload.get("apiKey", "")).strip():
            settings = load_settings()
            settings["googleMapsApiKey"] = str(payload.get("apiKey", "")).strip()
            settings["updatedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_settings(settings)

        set_job(job_id, status="running", message=f"Searching {len(queries)} Google Places query set...", progress=8)
        places, completed_queries = collect_places(api_key, queries, limit, language)
        leads: list[Lead] = []
        total = max(len(places), 1)

        for index, place in enumerate(places, start=1):
            set_job(
                job_id,
                message=f"Enriching {index} of {len(places)}: {place.name}",
                progress=10 + int((index - 1) / total * 82),
            )
            enrichment = (
                discover_contact_details(
                    place.website,
                    max_pages=max_pages,
                    delay=delay,
                    respect_robots=respect_robots,
                )
                if place.website
                else Enrichment()
            )
            leads.append(Lead(place=place, enrichment=enrichment))

        rows = [row for lead in leads for row in lead_to_rows(lead)]
        OUTPUT_DIR.mkdir(exist_ok=True)
        output_name = f"{safe_filename(queries[0])}_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        output_path = OUTPUT_DIR / output_name
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=csv_columns())
            writer.writeheader()
            writer.writerows(rows)

        set_job(
            job_id,
            status="complete",
            message="Lead list ready.",
            progress=100,
            rows=rows,
            businessCount=len(leads),
            emailCount=sum(1 for row in rows if row["email"]),
            queryCount=len(completed_queries),
            downloadUrl=f"/exports/{output_name}",
            savedPath=str(output_path),
        )
    except (HTTPError, URLError) as exc:
        set_job(job_id, status="error", message=f"Google/API request failed: {exc}", progress=100)
    except Exception as exc:
        set_job(job_id, status="error", message=str(exc), progress=100)


class LeadAppHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return

        if self.path.startswith("/api/jobs/"):
            job_id = self.path.rsplit("/", 1)[-1]
            job = get_job(job_id)
            if not job:
                self.send_json({"error": "Job not found."}, HTTPStatus.NOT_FOUND)
                return
            self.send_json(job)
            return

        if self.path == "/api/settings":
            key = saved_api_key() or os.getenv("GOOGLE_MAPS_API_KEY", "")
            self.send_json(
                {
                    "hasApiKey": bool(key),
                    "apiKeySource": "saved project settings" if saved_api_key() else ("PowerShell environment" if key else ""),
                }
            )
            return

        if self.path.startswith("/exports/"):
            self.directory = str(ROOT_DIR)
            return super().do_GET()

        self.directory = str(STATIC_DIR)
        if self.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:
        if self.path == "/api/settings":
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            api_key = str(payload.get("apiKey", "")).strip()
            if not api_key:
                self.send_json({"error": "Enter an API key before saving."}, HTTPStatus.BAD_REQUEST)
                return
            settings = load_settings()
            settings["googleMapsApiKey"] = api_key
            settings["updatedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
            save_settings(settings)
            self.send_json({"ok": True, "hasApiKey": True, "apiKeySource": "saved project settings"})
            return

        if self.path != "/api/search":
            self.send_json({"error": "Not found."}, HTTPStatus.NOT_FOUND)
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        job_id = make_job_id()
        set_job(job_id, status="queued", message="Queued.", progress=0, rows=[])
        thread = threading.Thread(target=run_lead_job, args=(job_id, payload), daemon=True)
        thread.start()
        self.send_json({"jobId": job_id}, HTTPStatus.ACCEPTED)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        if self.path.startswith("/api/jobs/"):
            return
        super().log_message(format, *args)


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), LeadAppHandler)
    print(f"Lead Generator is running at http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop it.")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
