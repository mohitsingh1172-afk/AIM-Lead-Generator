import csv
import os


PROJECT_NAME = os.getenv("PROJECT_NAME", "lead_project").strip()
INPUT_FILE = os.getenv("GENERIC_DISCOVERY_FILE", f"{PROJECT_NAME}_discovered.csv")
OUTPUT_FILE = os.getenv("ENRICH_INPUT_FILE", f"{PROJECT_NAME}_discovered_for_enrichment.csv")


def main() -> None:
    with open(INPUT_FILE, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])

    if "Location" in fieldnames and "State" not in fieldnames:
        fieldnames.append("State")
        for row in rows:
            row["State"] = row.get("Location", "")

    if "Name" not in fieldnames:
        fieldnames.append("Name")
        for row in rows:
            row["Name"] = row.get("Domain", "")

    with open(OUTPUT_FILE, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Read: {INPUT_FILE}")
    print(f"Saved: {OUTPUT_FILE}")
    print(f"Rows: {len(rows)}")


if __name__ == "__main__":
    main()
