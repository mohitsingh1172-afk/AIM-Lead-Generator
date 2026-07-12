import argparse
import csv
import re


OUTPUT_FIELDS = [
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
    "Lead_Status",
    "Original_Reject_Reason",
]


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def text(value):
    return str(value or "").strip()


def emails(value):
    return {
        item.lower()
        for item in re.split(r"\s*;\s*", text(value))
        if item.strip()
    }


def prepare(row, status, reason=""):
    output = {field: text(row.get(field)) for field in OUTPUT_FIELDS}
    output["State"] = output["State"] or text(row.get("Location"))
    output["Location"] = output["Location"] or output["State"]
    output["Segment"] = output["Segment"] or "Business Lead"
    output["Lead_Status"] = status
    output["Original_Reject_Reason"] = reason
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cleaned", required=True)
    parser.add_argument("--rejected", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    cleaned = read_csv(args.cleaned)
    rejected = read_csv(args.rejected)
    combined = []
    seen_domains = set()
    seen_emails = set()

    for row in cleaned:
        output = prepare(row, "Cleaned Lead")
        domain = text(output["Domain"]).lower()
        if domain:
            seen_domains.add(domain)
        seen_emails.update(emails(output["Emails"]))
        combined.append(output)

    added = 0
    for row in rejected:
        row_emails = emails(row.get("Emails"))
        if not row_emails:
            continue
        domain = text(row.get("Domain")).lower()
        if (domain and domain in seen_domains) or row_emails.issubset(seen_emails):
            continue
        combined.append(
            prepare(
                row,
                "Rejected Lead With Email - Review Required",
                text(row.get("Reject_Reason")),
            )
        )
        if domain:
            seen_domains.add(domain)
        seen_emails.update(row_emails)
        added += 1

    with open(args.output, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(combined)

    print(f"Cleaned rows: {len(cleaned)}")
    print(f"Rejected email rows added: {added}")
    print(f"Combined rows: {len(combined)}")
    print(f"Saved: {args.output}")


if __name__ == "__main__":
    main()

