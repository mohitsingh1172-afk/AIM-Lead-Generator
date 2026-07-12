import csv
import os
import re
import urllib.parse
from collections import Counter


PROJECT_NAME = os.getenv("PROJECT_NAME", "lead_project").strip()
INPUT_FILE = os.getenv("CLEAN_INPUT_FILE", f"{PROJECT_NAME}_enriched.csv")
CLEAN_OUTPUT_FILE = os.getenv("CLEAN_OUTPUT_FILE", f"{PROJECT_NAME}_cleaned.csv")
REJECTED_OUTPUT_FILE = os.getenv("REJECTED_OUTPUT_FILE", f"{PROJECT_NAME}_rejected.csv")

CONTACT_COLUMNS = ["Emails", "Phones", "WhatsApp"]

EXCLUDE_DOMAIN_CONTAINS = [
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "youtu.be",
    "pinterest.com",
    "reddit.com",
    "wikipedia.org",
    "google.",
    "mapquest.com",
    "tripadvisor.com",
]

EXCLUDE_TEXT_TERMS = [
    "article",
    "blog",
    "news",
    "magazine",
    "recipe",
    "tourism",
    "travel",
    "government",
    "university",
    "extension",
]

EXCLUDE_PATH_PARTS = [
    "/article",
    "/articles",
    "/blog",
    "/news",
    "/story",
    "/stories",
    "/recipe",
    "/recipes",
]


def norm(value):
    return (value or "").strip()


def has_contact(row):
    return any(norm(row.get(column)) for column in CONTACT_COLUMNS)


def domain_from_url(url):
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()
    return domain[4:] if domain.startswith("www.") else domain


def row_text(row):
    parts = [
        row.get("Name", ""),
        row.get("Domain", ""),
        row.get("Website", ""),
        row.get("Source_Query", ""),
        row.get("State", ""),
        row.get("Location", ""),
    ]
    return " ".join(parts).lower()


def website_path(row):
    parsed = urllib.parse.urlparse(row.get("Website", ""))
    return parsed.path.lower()


def clean_contact_fields(row):
    cleaned = dict(row)

    emails = []
    for email in re.split(r"\s*;\s*", norm(row.get("Emails"))):
        email = email.lower().strip()
        if not email:
            continue
        if "filler@" in email or "example" in email:
            continue
        emails.append(email)
    cleaned["Emails"] = "; ".join(dict.fromkeys(emails))

    for column in ["Phones", "WhatsApp"]:
        values = [
            value.strip()
            for value in re.split(r"\s*;\s*", norm(row.get(column)))
            if value.strip()
        ]
        cleaned[column] = "; ".join(dict.fromkeys(values))

    return cleaned


def reject_reason(row):
    row = clean_contact_fields(row)
    domain = norm(row.get("Domain")).lower() or domain_from_url(row.get("Website", ""))
    status = norm(row.get("Enrichment_Status")).lower()
    text = row_text(row)
    path = website_path(row)

    if status.startswith("homepage fetch failed"):
        return "fetch failed"

    if not has_contact(row):
        return "no email/phone/whatsapp"

    if any(part in domain for part in EXCLUDE_DOMAIN_CONTAINS):
        return "excluded social/directory domain"

    if any(part in path for part in EXCLUDE_PATH_PARTS):
        return "article/resource URL path"

    if any(term in text for term in EXCLUDE_TEXT_TERMS):
        return "likely article/resource result"

    return ""


def lead_segment(row):
    text = row_text(row)
    if "distributor" in text or "wholesale" in text or "importer" in text:
        return "Distributor/Wholesaler"
    if "manufacturer" in text or "processor" in text or "factory" in text:
        return "Manufacturer/Processor"
    if "retail" in text or "store" in text or "shop" in text or "market" in text:
        return "Retailer/Seller"
    return "Business Lead"


def main():
    with open(INPUT_FILE, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    cleaned = []
    rejected = []

    for row in rows:
        reason = reject_reason(row)
        if reason:
            out = dict(row)
            out["Reject_Reason"] = reason
            rejected.append(out)
            continue

        out = clean_contact_fields(row)
        out["Segment"] = lead_segment(row)
        cleaned.append(out)

    clean_fields = [
        "State",
        "Location",
        "Name",
        "Segment",
        "Website",
        "Domain",
        "Emails",
        "Phones",
        "WhatsApp",
        "Instagram",
        "Facebook",
        "LinkedIn",
        "Source",
        "Source_Query",
        "Email_Source_URL",
        "Phone_Source_URL",
        "Enrichment_Status",
        "Enriched_At",
    ]
    available = set(fieldnames) | {"Segment"}
    clean_fields = [field for field in clean_fields if field in available]

    rejected_fields = list(fieldnames)
    if "Reject_Reason" not in rejected_fields:
        rejected_fields.append("Reject_Reason")

    with open(CLEAN_OUTPUT_FILE, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=clean_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(cleaned)

    with open(REJECTED_OUTPUT_FILE, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rejected_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rejected)

    segment_counts = Counter(row.get("Segment", "") for row in cleaned)
    reject_counts = Counter(row.get("Reject_Reason", "") for row in rejected)

    print(f"Input rows: {len(rows)}")
    print(f"Cleaned rows: {len(cleaned)}")
    print(f"Rejected rows: {len(rejected)}")
    print("\nCleaned by segment:")
    for segment, count in segment_counts.most_common():
        print(f"  {segment}: {count}")
    print("\nTop rejection reasons:")
    for reason, count in reject_counts.most_common():
        print(f"  {reason}: {count}")
    print(f"\nSaved: {CLEAN_OUTPUT_FILE}")
    print(f"Saved: {REJECTED_OUTPUT_FILE}")


if __name__ == "__main__":
    main()
