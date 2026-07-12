import argparse
import csv
from pathlib import Path
from urllib.parse import urlparse


def normalize(value):
    value = str(value or "").strip().lower()
    if not value:
        return ""
    if "://" in value:
        value = urlparse(value).netloc.lower()
    value = value.split("/", 1)[0].split(":", 1)[0]
    return value[4:] if value.startswith("www.") else value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--exclude-file", required=True)
    parser.add_argument("--csv-files", nargs="+", required=True)
    args = parser.parse_args()

    exclude_path = Path(args.exclude_file)
    domains = set()
    if exclude_path.exists():
        domains.update(
            normalize(line)
            for line in exclude_path.read_text(
                encoding="utf-8-sig", errors="ignore"
            ).splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )

    for csv_name in args.csv_files:
        path = Path(csv_name)
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                domain = normalize(row.get("Domain"))
                if not domain:
                    domain = normalize(row.get("Website"))
                if domain:
                    domains.add(domain)

    domains.discard("")
    exclude_path.write_text(
        "\n".join(sorted(domains)) + "\n", encoding="utf-8"
    )
    print(f"Saved {len(domains)} domains: {exclude_path}")


if __name__ == "__main__":
    main()

