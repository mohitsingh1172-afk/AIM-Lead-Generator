from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Iterable
from urllib import robotparser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse
from urllib.request import Request, urlopen


PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
USER_AGENT = "EmailLeadGenerator/1.0 (+public-contact-discovery)"
DEFAULT_FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.nationalPhoneNumber",
        "places.internationalPhoneNumber",
        "places.websiteUri",
        "places.googleMapsUri",
        "places.rating",
        "places.userRatingCount",
        "places.businessStatus",
        "nextPageToken",
    ]
)

EMAIL_RE = re.compile(
    r"(?<![\w.+-])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![\w.-])",
    re.IGNORECASE,
)
OBFUSCATED_EMAIL_RE = re.compile(
    r"([A-Z0-9._%+-]+)\s*(?:\(|\[)?\s*at\s*(?:\)|\])?\s*"
    r"([A-Z0-9.-]+)\s*(?:\(|\[)?\s*dot\s*(?:\)|\])?\s*([A-Z]{2,})",
    re.IGNORECASE,
)
BAD_EMAIL_SUFFIXES = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".css",
    ".js",
)
BAD_EMAIL_CONTAINS = (
    "@2x.",
    "@3x.",
    "example.com",
    "email.com",
    "yourdomain",
    "domain.com",
    "sentry.io",
    "wixpress.com",
    "schema.org",
)
BAD_EMAIL_LOCAL_PARTS = {
    "email",
    "example",
    "name",
    "test",
    "user",
    "username",
    "your-email",
    "youremail",
}
CONTACT_HINTS = (
    "contact",
    "about",
    "team",
    "support",
    "customer",
    "service",
    "location",
    "locations",
)
SOCIAL_HOSTS = {
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "x.com",
    "twitter.com",
    "youtube.com",
    "tiktok.com",
}
PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}(?!\w)"
)
GENERIC_LOCAL_PARTS = {
    "admin",
    "booking",
    "careers",
    "contact",
    "hello",
    "help",
    "info",
    "inquiries",
    "office",
    "sales",
    "service",
    "support",
}


@dataclass
class Place:
    place_id: str
    name: str
    address: str = ""
    phone: str = ""
    website: str = ""
    google_maps_url: str = ""
    rating: str = ""
    review_count: str = ""
    business_status: str = ""


@dataclass
class EmailHit:
    email: str
    source_url: str
    is_generic: bool


@dataclass
class Enrichment:
    emails: list[EmailHit] = field(default_factory=list)
    website_phones: list[str] = field(default_factory=list)
    social_links: list[str] = field(default_factory=list)


@dataclass
class Lead:
    place: Place
    enrichment: Enrichment = field(default_factory=Enrichment)

    @property
    def emails(self) -> list[EmailHit]:
        return self.enrichment.emails


class LinkParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__()
        self.base_url = base_url
        self.links: list[str] = []
        self.mailtos: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = {key.lower(): value for key, value in attrs if value}
        href = attrs_dict.get("href")
        if not href:
            return
        href = html.unescape(href).strip()
        if href.lower().startswith("mailto:"):
            address = href[7:].split("?", 1)[0]
            self.mailtos.append(unquote(address))
            return
        self.links.append(urljoin(self.base_url, href))


def request_json(url: str, *, headers: dict[str, str], payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(url, data=data, headers=headers, method="POST" if payload else "GET")
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,text/plain;q=0.8,*/*;q=0.1",
        },
    )
    with urlopen(request, timeout=20) as response:
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            return ""
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(1_500_000).decode(charset, errors="replace")


def normalize_url(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    if not parsed.netloc:
        return ""
    return parsed._replace(fragment="").geturl()


def same_site(url: str, root: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    root_host = urlparse(root).netloc.lower().removeprefix("www.")
    return host == root_host


def can_fetch(url: str, cache: dict[str, robotparser.RobotFileParser]) -> bool:
    parsed = urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    if root not in cache:
        parser = robotparser.RobotFileParser()
        parser.set_url(urljoin(root, "/robots.txt"))
        try:
            parser.read()
        except Exception:
            return True
        cache[root] = parser
    return cache[root].can_fetch(USER_AGENT, url)


def clean_email(email_address: str) -> str:
    email_address = html.unescape(unquote(email_address)).strip().strip(".,;:()[]{}<>\"'")
    return email_address.lower()


def is_valid_email(email_address: str) -> bool:
    if not email_address or any(email_address.endswith(suffix) for suffix in BAD_EMAIL_SUFFIXES):
        return False
    if any(value in email_address for value in BAD_EMAIL_CONTAINS):
        return False
    if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9.-]+\.[a-z]{2,24}", email_address):
        return False
    local, _, domain = email_address.partition("@")
    if local in BAD_EMAIL_LOCAL_PARTS:
        return False
    if local.startswith(".") or local.endswith(".") or domain.startswith(".") or domain.endswith("."):
        return False
    if ".." in email_address:
        return False
    labels = domain.split(".")
    if any(not label or label.startswith("-") or label.endswith("-") for label in labels):
        return False
    return True


def is_generic_email(email_address: str) -> bool:
    local = email_address.split("@", 1)[0].lower()
    local = re.split(r"[.+_-]", local, maxsplit=1)[0]
    return local in GENERIC_LOCAL_PARTS


def extract_emails(page_text: str, source_url: str, mailtos: Iterable[str] = ()) -> list[EmailHit]:
    candidates = set()
    candidates.update(match.group(1) for match in EMAIL_RE.finditer(page_text))
    candidates.update(f"{m.group(1)}@{m.group(2)}.{m.group(3)}" for m in OBFUSCATED_EMAIL_RE.finditer(page_text))
    candidates.update(mailtos)

    hits = []
    for candidate in sorted(candidates):
        email_address = clean_email(candidate)
        if is_valid_email(email_address):
            hits.append(EmailHit(email=email_address, source_url=source_url, is_generic=is_generic_email(email_address)))
    return hits


def normalize_phone(phone: str) -> str:
    phone = re.sub(r"\s+", " ", phone.strip())
    return phone.strip(".,;:()[]{}<>\"'")


def is_probable_phone(phone: str) -> bool:
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 7 or len(digits) > 15:
        return False
    return len(set(digits)) > 2


def extract_phones(page_text: str) -> list[str]:
    phones = []
    for match in PHONE_RE.finditer(page_text):
        phone = normalize_phone(match.group(0))
        if is_probable_phone(phone):
            phones.append(phone)
    return sorted(dict.fromkeys(phones))


def is_social_link(url: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return any(host == social_host or host.endswith(f".{social_host}") for social_host in SOCIAL_HOSTS)


def contact_page_score(url: str) -> int:
    parsed = urlparse(url)
    text = f"{parsed.path} {parse_qs(parsed.query)}".lower()
    return sum(1 for hint in CONTACT_HINTS if hint in text)


def discover_candidate_pages(root_url: str, page_text: str, max_pages: int) -> list[str]:
    parser = LinkParser(root_url)
    parser.feed(page_text)
    candidates = [root_url]
    for link in parser.links:
        clean = normalize_url(link)
        if not clean or not same_site(clean, root_url):
            continue
        path = urlparse(clean).path.lower()
        if any(path.endswith(ext) for ext in BAD_EMAIL_SUFFIXES):
            continue
        if contact_page_score(clean) > 0:
            candidates.append(clean)

    unique = list(dict.fromkeys(candidates))
    unique.sort(key=lambda item: contact_page_score(item), reverse=True)
    return unique[:max_pages]


def discover_contact_details(website: str, *, max_pages: int, delay: float, respect_robots: bool) -> Enrichment:
    root_url = normalize_url(website)
    if not root_url:
        return Enrichment()

    robots_cache: dict[str, robotparser.RobotFileParser] = {}
    hits_by_email: dict[str, EmailHit] = {}
    website_phones: dict[str, None] = {}
    social_links: dict[str, None] = {}

    try:
        if respect_robots and not can_fetch(root_url, robots_cache):
            return Enrichment()
        home_text = fetch_text(root_url)
    except (HTTPError, URLError, TimeoutError, ValueError):
        return Enrichment()

    parser = LinkParser(root_url)
    parser.feed(home_text)
    for hit in extract_emails(home_text, root_url, parser.mailtos):
        hits_by_email.setdefault(hit.email, hit)
    for phone in extract_phones(home_text):
        website_phones.setdefault(phone, None)
    for link in parser.links:
        clean = normalize_url(link)
        if clean and is_social_link(clean):
            social_links.setdefault(clean, None)

    pages = discover_candidate_pages(root_url, home_text, max_pages)
    for page_url in pages:
        if page_url == root_url:
            continue
        try:
            if respect_robots and not can_fetch(page_url, robots_cache):
                continue
            time.sleep(delay)
            page_text = fetch_text(page_url)
            page_parser = LinkParser(page_url)
            page_parser.feed(page_text)
        except (HTTPError, URLError, TimeoutError, ValueError):
            continue
        for hit in extract_emails(page_text, page_url, page_parser.mailtos):
            hits_by_email.setdefault(hit.email, hit)
        for phone in extract_phones(page_text):
            website_phones.setdefault(phone, None)
        for link in page_parser.links:
            clean = normalize_url(link)
            if clean and is_social_link(clean):
                social_links.setdefault(clean, None)

    return Enrichment(
        emails=sorted(hits_by_email.values(), key=lambda hit: (not hit.is_generic, hit.email)),
        website_phones=sorted(website_phones),
        social_links=sorted(social_links),
    )


def search_places(api_key: str, query: str, *, limit: int, language_code: str | None = None) -> list[Place]:
    places: list[Place] = []
    page_token = None

    while len(places) < limit:
        payload: dict[str, object] = {"textQuery": query}
        if page_token:
            payload["pageToken"] = page_token
        if language_code:
            payload["languageCode"] = language_code

        data = request_json(
            PLACES_TEXT_SEARCH_URL,
            payload=payload,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": DEFAULT_FIELD_MASK,
            },
        )

        for item in data.get("places", []):
            display_name = item.get("displayName") or {}
            places.append(
                Place(
                    place_id=item.get("id", ""),
                    name=display_name.get("text", ""),
                    address=item.get("formattedAddress", ""),
                    phone=item.get("nationalPhoneNumber") or item.get("internationalPhoneNumber", ""),
                    website=item.get("websiteUri", ""),
                    google_maps_url=item.get("googleMapsUri", ""),
                    rating=str(item.get("rating", "")),
                    review_count=str(item.get("userRatingCount", "")),
                    business_status=item.get("businessStatus", ""),
                )
            )
            if len(places) >= limit:
                break

        page_token = data.get("nextPageToken")
        if not page_token:
            break
        time.sleep(2)

    return places


def lead_to_rows(lead: Lead) -> list[dict[str, str]]:
    email_ids = "; ".join(hit.email for hit in lead.emails)
    website_phones = "; ".join(lead.enrichment.website_phones)
    social_links = "; ".join(lead.enrichment.social_links)
    primary_email = lead.emails[0] if lead.emails else EmailHit(email="", source_url="", is_generic=False)
    return [
        {
            "business_name": lead.place.name,
            "email_ids": email_ids,
            "email": primary_email.email,
            "email_type": "generic" if primary_email.email and primary_email.is_generic else ("direct/unknown" if primary_email.email else ""),
            "email_source": primary_email.source_url,
            "phone": lead.place.phone,
            "website_phones": website_phones,
            "website": lead.place.website,
            "social_links": social_links,
            "address": lead.place.address,
            "google_maps_url": lead.place.google_maps_url,
            "rating": lead.place.rating,
            "review_count": lead.place.review_count,
            "business_status": lead.place.business_status,
            "place_id": lead.place.place_id,
        }
    ]


def csv_columns() -> list[str]:
    return [
        "business_name",
        "email_ids",
        "email",
        "email_type",
        "email_source",
        "phone",
        "website_phones",
        "website",
        "social_links",
        "address",
        "google_maps_url",
        "rating",
        "review_count",
        "business_status",
        "place_id",
    ]


def write_csv(leads: list[Lead], output_path: str) -> None:
    columns = csv_columns()
    with open(output_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for lead in leads:
            writer.writerows(lead_to_rows(lead))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find businesses with Google Places API and enrich them with public contact details from their websites."
    )
    parser.add_argument("query", help='Business search query, such as "dentists in Austin TX".')
    parser.add_argument("--limit", type=int, default=20, help="Maximum businesses to collect. Google may cap at 60.")
    parser.add_argument("--output", default="leads.csv", help="CSV output path.")
    parser.add_argument("--api-key", default=os.getenv("GOOGLE_MAPS_API_KEY"), help="Google Places API key.")
    parser.add_argument("--language", default=None, help="Optional Places API language code, such as en.")
    parser.add_argument("--max-pages", type=int, default=4, help="Maximum pages to check per business website.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between website page requests in seconds.")
    parser.add_argument("--no-robots-check", action="store_true", help="Skip robots.txt checks for business websites.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print("Missing API key. Set GOOGLE_MAPS_API_KEY or pass --api-key.", file=sys.stderr)
        return 2
    if args.limit < 1:
        print("--limit must be at least 1.", file=sys.stderr)
        return 2

    limit = min(args.limit, 60)
    print(f"Searching Places for: {args.query}")
    places = search_places(args.api_key, args.query, limit=limit, language_code=args.language)
    print(f"Found {len(places)} businesses. Checking public websites for emails...")

    leads: list[Lead] = []
    for index, place in enumerate(places, start=1):
        print(f"[{index}/{len(places)}] {place.name}")
        if place.website:
            enrichment = discover_contact_details(
                place.website,
                max_pages=max(1, args.max_pages),
                delay=max(0, args.delay),
                respect_robots=not args.no_robots_check,
            )
        else:
            enrichment = Enrichment()
        leads.append(Lead(place=place, enrichment=enrichment))

    write_csv(leads, args.output)
    email_count = sum(len(lead.emails) for lead in leads)
    print(f"Saved {len(leads)} businesses and {email_count} emails to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
