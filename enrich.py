import os
import re
import time
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup


INPUT_FILE = os.getenv("ENRICH_INPUT_FILE", "us_goat_leads_discovered_all_states.csv")
OUTPUT_FILE = os.getenv("ENRICH_OUTPUT_FILE", "us_goat_leads_enriched_all_states.csv")

# PowerShell:
#   $env:SCRAPEDO_TOKEN="your_scrapedo_token"
SCRAPEDO_TOKEN = os.getenv("SCRAPEDO_TOKEN", "").strip()

MAX_PAGES_PER_WEBSITE = int(os.getenv("MAX_PAGES_PER_WEBSITE", "8") or "8")
REQUEST_DELAY_SECONDS = float(os.getenv("REQUEST_DELAY_SECONDS", "1.5") or "1.5")
MAX_HTML_BYTES = int(os.getenv("MAX_HTML_BYTES", "1500000") or "1500000")
PHONE_COUNTRY_CODE = os.getenv("PHONE_COUNTRY_CODE", "Auto").strip() or "Auto"
DIRECT_CONNECT_TIMEOUT = float(os.getenv("DIRECT_CONNECT_TIMEOUT", "10") or "10")
DIRECT_READ_TIMEOUT = float(os.getenv("DIRECT_READ_TIMEOUT", "15") or "15")
SCRAPEDO_TIMEOUT = float(os.getenv("SCRAPEDO_TIMEOUT", "30") or "30")
STOP_AFTER_CONTACT_FOUND = os.getenv("STOP_AFTER_CONTACT_FOUND", "0").strip() == "1"
SCRAPEDO_FIRST = os.getenv("SCRAPEDO_FIRST", "0").strip() == "1"
USE_SCRAPEDO = os.getenv("USE_SCRAPEDO", "1").strip() != "0"
RETRY_FAILED = os.getenv("RETRY_FAILED", "0").strip() == "1"
RETRY_DNS_FAILED = os.getenv("RETRY_DNS_FAILED", "0").strip() == "1"
RETRY_MISSING = os.getenv("RETRY_MISSING", "0").strip() == "1"
RESUME_AFTER_ROW = int(os.getenv("RESUME_AFTER_ROW", "0") or "0")
RETRY_ROW_FROM = int(os.getenv("RETRY_ROW_FROM", "0") or "0")
RETRY_ROW_TO = int(os.getenv("RETRY_ROW_TO", "0") or "0")

if RETRY_MISSING and RETRY_ROW_FROM:
    raise SystemExit(
        "RETRY_MISSING=1 and RETRY_ROW_FROM is also set. "
        "Remove RETRY_ROW_FROM/RETRY_ROW_TO before running missing-only mode."
    )

CONTACT_KEYWORDS = [
    "contact",
    "about",
    "wholesale",
    "supplier",
    "suppliers",
    "distributor",
    "distributors",
    "sales",
    "retail",
    "stockist",
    "stockists",
    "where to buy",
]

COUNTRY_PHONE_CODES = {
    "afghanistan": "+93", "albania": "+355", "algeria": "+213", "andorra": "+376",
    "angola": "+244", "anguilla": "+1", "antigua and barbuda": "+1", "argentina": "+54",
    "armenia": "+374", "aruba": "+297", "australia": "+61", "austria": "+43",
    "azerbaijan": "+994", "bahamas": "+1", "bahrain": "+973", "bangladesh": "+880",
    "barbados": "+1", "belarus": "+375", "belgium": "+32", "belize": "+501",
    "benin": "+229", "bermuda": "+1", "bhutan": "+975", "bolivia": "+591",
    "bosnia and herzegovina": "+387", "bosnia": "+387", "botswana": "+267", "brazil": "+55",
    "brunei": "+673", "bulgaria": "+359", "burkina faso": "+226", "burundi": "+257",
    "cambodia": "+855", "cameroon": "+237", "canada": "+1", "cape verde": "+238",
    "cayman islands": "+1", "central african republic": "+236", "chad": "+235", "chile": "+56",
    "china": "+86", "colombia": "+57", "comoros": "+269", "congo": "+242",
    "costa rica": "+506", "croatia": "+385", "cuba": "+53", "curacao": "+599",
    "cyprus": "+357", "czech republic": "+420", "czechia": "+420",
    "democratic republic of the congo": "+243", "denmark": "+45", "djibouti": "+253",
    "dominica": "+1", "dominican republic": "+1", "ecuador": "+593", "egypt": "+20",
    "el salvador": "+503", "equatorial guinea": "+240", "eritrea": "+291", "estonia": "+372",
    "eswatini": "+268", "swaziland": "+268", "ethiopia": "+251", "fiji": "+679",
    "finland": "+358", "france": "+33", "gabon": "+241", "gambia": "+220",
    "georgia": "+995", "germany": "+49", "ghana": "+233", "gibraltar": "+350",
    "greece": "+30", "grenada": "+1", "guatemala": "+502", "guinea": "+224",
    "guinea bissau": "+245", "guyana": "+592", "haiti": "+509", "honduras": "+504",
    "hong kong": "+852", "hungary": "+36", "iceland": "+354", "india": "+91",
    "indonesia": "+62", "iran": "+98", "iraq": "+964", "ireland": "+353",
    "israel": "+972", "italy": "+39", "ivory coast": "+225", "cote d ivoire": "+225",
    "jamaica": "+1", "japan": "+81", "jordan": "+962", "kazakhstan": "+7",
    "kenya": "+254", "kuwait": "+965", "kyrgyzstan": "+996", "laos": "+856",
    "latvia": "+371", "lebanon": "+961", "lesotho": "+266", "liberia": "+231",
    "libya": "+218", "liechtenstein": "+423", "lithuania": "+370", "luxembourg": "+352",
    "macau": "+853", "madagascar": "+261", "malawi": "+265", "malaysia": "+60",
    "maldives": "+960", "mali": "+223", "malta": "+356", "mauritania": "+222",
    "mauritius": "+230", "mexico": "+52", "moldova": "+373", "monaco": "+377",
    "mongolia": "+976", "montenegro": "+382", "morocco": "+212", "mozambique": "+258",
    "myanmar": "+95", "burma": "+95", "namibia": "+264", "nepal": "+977",
    "netherlands": "+31", "new zealand": "+64", "nicaragua": "+505", "niger": "+227",
    "nigeria": "+234", "north macedonia": "+389", "norway": "+47", "oman": "+968",
    "pakistan": "+92", "panama": "+507", "papua new guinea": "+675", "paraguay": "+595",
    "peru": "+51", "philippines": "+63", "poland": "+48", "portugal": "+351",
    "puerto rico": "+1", "qatar": "+974", "romania": "+40", "russia": "+7",
    "rwanda": "+250", "saint kitts and nevis": "+1", "saint lucia": "+1",
    "saint vincent and the grenadines": "+1", "samoa": "+685", "san marino": "+378",
    "saudi arabia": "+966", "senegal": "+221", "serbia": "+381", "seychelles": "+248",
    "sierra leone": "+232", "singapore": "+65", "slovakia": "+421", "slovenia": "+386",
    "somalia": "+252", "south africa": "+27", "south korea": "+82", "korea": "+82",
    "south sudan": "+211", "spain": "+34", "sri lanka": "+94", "sudan": "+249",
    "suriname": "+597", "sweden": "+46", "switzerland": "+41", "syria": "+963",
    "taiwan": "+886", "tajikistan": "+992", "tanzania": "+255", "thailand": "+66",
    "togo": "+228", "trinidad and tobago": "+1", "tunisia": "+216", "turkey": "+90",
    "turkmenistan": "+993", "uganda": "+256", "ukraine": "+380",
    "united arab emirates": "+971", "uae": "+971", "united kingdom": "+44",
    "uk": "+44", "u.k.": "+44", "great britain": "+44", "england": "+44",
    "scotland": "+44", "wales": "+44", "northern ireland": "+44",
    "united states": "+1", "usa": "+1", "u.s.a": "+1", "u.s.": "+1",
    "us": "+1", "america": "+1", "uruguay": "+598", "uzbekistan": "+998",
    "venezuela": "+58", "vietnam": "+84", "viet nam": "+84", "yemen": "+967",
    "zambia": "+260", "zimbabwe": "+263",
}


def phone_code_for_location(location: str) -> str:
    configured = PHONE_COUNTRY_CODE.strip()
    if configured and configured.lower() not in {"auto", "automatic"}:
        return configured if configured.startswith("+") else f"+{configured}"

    text = re.sub(r"[^a-z0-9\s.]+", " ", str(location).lower())
    text = re.sub(r"\s+", " ", text).strip()
    for name, code in sorted(COUNTRY_PHONE_CODES.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"(^|\s){re.escape(name)}($|\s)", text):
            return code

    return "+1"

BAD_EMAIL_TERMS = [
    "example",
    "noreply",
    "no-reply",
    "donotreply",
    "sentry",
    "wixpress",
    "domain.com",
    "email.com",
    "yourname",
    "name@",
]

SOCIAL_DOMAINS = {
    "Instagram": "instagram.com",
    "Facebook": "facebook.com",
    "LinkedIn": "linkedin.com",
}


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

    return parsed._replace(fragment="").geturl().rstrip("/")


def domain_from_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()
    return domain[4:] if domain.startswith("www.") else domain


def same_domain(url: str, base_url: str) -> bool:
    return domain_from_url(url) == domain_from_url(base_url)


def fetch_direct(url: str) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    response = requests.get(
        url,
        headers=headers,
        timeout=(DIRECT_CONNECT_TIMEOUT, DIRECT_READ_TIMEOUT),
        stream=True,
    )
    response.raise_for_status()

    chunks = []
    total = 0
    for chunk in response.iter_content(chunk_size=32768, decode_unicode=False):
        if not chunk:
            continue
        chunks.append(chunk)
        total += len(chunk)
        if total >= MAX_HTML_BYTES:
            break

    content = b"".join(chunks)
    encoding = response.encoding or response.apparent_encoding or "utf-8"
    return content.decode(encoding, errors="replace")


def fetch_with_scrapedo(url: str) -> str:
    if not SCRAPEDO_TOKEN:
        raise RuntimeError("Missing SCRAPEDO_TOKEN environment variable.")

    encoded_url = urllib.parse.quote(url, safe="")
    scrape_url = f"https://api.scrape.do/?token={SCRAPEDO_TOKEN}&url={encoded_url}"

    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(scrape_url, headers=headers, timeout=SCRAPEDO_TIMEOUT)
    if response.status_code == 401:
        raise RuntimeError("Scrape.do returned 401 Unauthorized. Check or rotate SCRAPEDO_TOKEN.")
    response.raise_for_status()
    return response.text


def fetch_url(url: str) -> str:
    direct_error = None
    scrapedo_error = None

    if USE_SCRAPEDO and SCRAPEDO_FIRST:
        try:
            return fetch_with_scrapedo(url)
        except RuntimeError:
            raise
        except Exception as exc:
            scrapedo_error = exc

    try:
        return fetch_direct(url)
    except Exception as exc:
        direct_error = exc

    if USE_SCRAPEDO and not SCRAPEDO_FIRST:
        try:
            return fetch_with_scrapedo(url)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"direct fetch failed ({direct_error}); Scrape.do failed ({exc})")

    if scrapedo_error is not None:
        raise RuntimeError(
            f"Scrape.do failed ({scrapedo_error}); direct fetch failed ({direct_error})"
        )

    raise RuntimeError(f"direct fetch failed ({direct_error})")


def clean_email(email: str) -> Optional[str]:
    email = email.lower().strip()
    email = email.strip(".,;:()[]{}<>\"'")

    if not email or any(term in email for term in BAD_EMAIL_TERMS):
        return None

    if email.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")):
        return None

    return email


def extract_emails(html: str) -> List[str]:
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return []

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    chunks = [soup.get_text(" ")]

    for a in soup.find_all("a", href=True):
        href = urllib.parse.unquote(a["href"])
        if href.lower().startswith("mailto:"):
            href = href.split(":", 1)[1].split("?", 1)[0]
        chunks.append(href)

    raw_emails = re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        " ".join(chunks),
    )

    emails = []
    for email in raw_emails:
        email = clean_email(email)
        if email and email not in emails:
            emails.append(email)

    return emails


def normalize_phone(phone: str, phone_country_code: str) -> Optional[str]:
    digits = re.sub(r"\D", "", phone)
    country_digits = re.sub(r"\D", "", phone_country_code)

    if country_digits and digits.startswith(country_digits) and len(digits) > 10:
        digits = digits[len(country_digits):]

    if phone_country_code != "+1" and len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    if phone_country_code == "+91" and len(digits) > 10:
        digits = digits[-10:]

    if len(digits) != 10:
        return None

    if len(set(digits)) <= 2:
        return None

    return f"{phone_country_code}{digits}"


def extract_phones_and_whatsapp(html: str, phone_country_code: str) -> Tuple[List[str], List[str]]:
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return [], []

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(" ")
    raw_phones = re.findall(
        r"(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}",
        text,
    )

    phones = []
    for phone in raw_phones:
        phone = normalize_phone(phone, phone_country_code)
        if phone and phone not in phones:
            phones.append(phone)

    whatsapp = []
    for a in soup.find_all("a", href=True):
        href = urllib.parse.unquote(a["href"]).strip()
        href_lower = href.lower()

        if "wa.me/" in href_lower or "api.whatsapp.com" in href_lower:
            if href not in whatsapp:
                whatsapp.append(href)
            continue

        if href_lower.startswith("tel:") and "whatsapp" in a.get_text(" ").lower():
            phone = normalize_phone(href, phone_country_code)
            if phone and phone not in whatsapp:
                whatsapp.append(phone)

    return phones, whatsapp


def extract_social_links(html: str) -> Dict[str, str]:
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception:
        return {name: "" for name in SOCIAL_DOMAINS}
    socials = {name: "" for name in SOCIAL_DOMAINS}

    for a in soup.find_all("a", href=True):
        href = urllib.parse.unquote(a["href"]).strip()
        href_lower = href.lower()

        for name, domain in SOCIAL_DOMAINS.items():
            if domain in href_lower and not socials[name]:
                socials[name] = href

    return socials


def discover_contact_pages(base_url: str, html: str) -> List[str]:
    try:
        soup = BeautifulSoup(html, "html.parser")
    except Exception as exc:
        print(f"    Could not parse homepage links: {exc}")
        return [base_url]
    pages = [base_url]

    for a in soup.find_all("a", href=True):
        text = f"{a.get_text(' ')} {a['href']}".lower()
        if not any(keyword in text for keyword in CONTACT_KEYWORDS):
            continue

        url = normalize_url(urllib.parse.urljoin(base_url, a["href"]))
        if not url or not same_domain(url, base_url):
            continue

        if url not in pages:
            pages.append(url)

        if len(pages) >= MAX_PAGES_PER_WEBSITE:
            break

    return pages


def enrich_website(website: str, phone_country_code: str) -> Dict[str, str]:
    website = normalize_url(website)
    if not website:
        return {
            "Emails": "",
            "Phones": "",
            "WhatsApp": "",
            "Instagram": "",
            "Facebook": "",
            "LinkedIn": "",
            "Contact_Pages_Checked": "",
            "Email_Source_URL": "",
            "Phone_Source_URL": "",
            "Enrichment_Status": "missing website",
        }

    all_emails = []
    all_phones = []
    all_whatsapp = []
    socials = {name: "" for name in SOCIAL_DOMAINS}
    checked_pages = []
    email_source = ""
    phone_source = ""

    try:
        homepage_html = fetch_url(website)
    except Exception as exc:
        return {
            "Emails": "",
            "Phones": "",
            "WhatsApp": "",
            "Instagram": "",
            "Facebook": "",
            "LinkedIn": "",
            "Contact_Pages_Checked": website,
            "Email_Source_URL": "",
            "Phone_Source_URL": "",
            "Enrichment_Status": f"homepage fetch failed: {exc}",
        }

    pages = discover_contact_pages(website, homepage_html)
    page_html_by_url = {website: homepage_html}

    for page in pages:
        if page in checked_pages:
            continue

        try:
            html = page_html_by_url.get(page) or fetch_url(page)
        except Exception as exc:
            print(f"    Page failed: {page} ({exc})")
            continue

        checked_pages.append(page)

        emails = extract_emails(html)
        phones, whatsapp = extract_phones_and_whatsapp(html, phone_country_code)
        page_socials = extract_social_links(html)

        for email in emails:
            if email not in all_emails:
                all_emails.append(email)
                if not email_source:
                    email_source = page

        for phone in phones:
            if phone not in all_phones:
                all_phones.append(phone)
                if not phone_source:
                    phone_source = page

        for item in whatsapp:
            if item not in all_whatsapp:
                all_whatsapp.append(item)

        for name, link in page_socials.items():
            if link and not socials[name]:
                socials[name] = link

        if STOP_AFTER_CONTACT_FOUND and (all_emails or all_phones or all_whatsapp):
            break

        time.sleep(REQUEST_DELAY_SECONDS)

    if all_emails or all_phones or all_whatsapp:
        status = "enriched"
    else:
        status = "no public email/phone found"

    return {
        "Emails": "; ".join(all_emails),
        "Phones": "; ".join(all_phones),
        "WhatsApp": "; ".join(all_whatsapp),
        "Instagram": socials["Instagram"],
        "Facebook": socials["Facebook"],
        "LinkedIn": socials["LinkedIn"],
        "Contact_Pages_Checked": "; ".join(checked_pages),
        "Email_Source_URL": email_source,
        "Phone_Source_URL": phone_source,
        "Enrichment_Status": status,
    }


def main() -> None:
    if USE_SCRAPEDO and not SCRAPEDO_TOKEN:
        raise SystemExit(
            "Missing SCRAPEDO_TOKEN. Set it in PowerShell first, or set USE_SCRAPEDO=0."
        )

    if not os.path.exists(INPUT_FILE):
        raise SystemExit(f"Missing input file: {INPUT_FILE}")

    df = pd.read_csv(INPUT_FILE).fillna("")

    retry_domains = set()
    retry_keys = set()

    if os.path.exists(OUTPUT_FILE):
        enriched_df = pd.read_csv(OUTPUT_FILE).fillna("")
        if (RETRY_FAILED or RETRY_DNS_FAILED) and "Enrichment_Status" in enriched_df.columns:
            statuses = enriched_df["Enrichment_Status"].astype(str)
            if RETRY_DNS_FAILED and not RETRY_FAILED:
                failed_mask = statuses.str.contains(
                    "NameResolutionError|Failed to resolve|getaddrinfo failed",
                    regex=True,
                    case=False,
                    na=False,
                )
            else:
                failed_mask = statuses.str.startswith("homepage fetch failed")
            retry_domains = set(
                enriched_df.loc[failed_mask, "Domain"].astype(str).str.strip()
            )
            retry_keys = set(
                zip(
                    enriched_df.loc[failed_mask, "State"].astype(str).str.strip(),
                    enriched_df.loc[failed_mask, "Domain"].astype(str).str.strip(),
                )
            )
            retry_count = int(failed_mask.sum())
            if retry_count:
                print(f"Retry mode: removing {retry_count} rows for retry.")
                enriched_df = enriched_df.loc[~failed_mask].copy()
        done_domains = set(enriched_df.get("Domain", pd.Series(dtype=str)).astype(str))
        print(f"Resuming {OUTPUT_FILE}; already enriched {len(done_domains)} domains.")
    else:
        enriched_df = pd.DataFrame()
        done_domains = set()

    if RETRY_ROW_FROM:
        row_to = RETRY_ROW_TO or RETRY_ROW_FROM
        row_range_df = df.iloc[RETRY_ROW_FROM - 1 : row_to].copy()
        row_range_keys = set(
            zip(
                row_range_df.get("State", pd.Series(dtype=str)).astype(str).str.strip(),
                row_range_df.get("Domain", pd.Series(dtype=str)).astype(str).str.strip(),
            )
        )
        retry_keys.update(row_range_keys)
        retry_domains.update(domain for _state, domain in row_range_keys)

        if not enriched_df.empty:
            enriched_keys = list(
                zip(
                    enriched_df.get("State", pd.Series(dtype=str)).astype(str).str.strip(),
                    enriched_df.get("Domain", pd.Series(dtype=str)).astype(str).str.strip(),
                )
            )
            keep_mask = [key not in row_range_keys for key in enriched_keys]
            removed_count = len(enriched_df) - sum(keep_mask)
            if removed_count:
                print(f"Row retry mode: removing {removed_count} saved rows for retry.")
                enriched_df = enriched_df.loc[keep_mask].copy()
                done_domains = set(enriched_df.get("Domain", pd.Series(dtype=str)).astype(str))

    retry_mode = RETRY_FAILED or RETRY_DNS_FAILED or RETRY_MISSING or bool(RETRY_ROW_FROM)

    if retry_mode:
        discovered_domains = set(df.get("Domain", pd.Series(dtype=str)).astype(str).str.strip())
        if RETRY_MISSING:
            saved_domains = set(
                enriched_df.get("Domain", pd.Series(dtype=str)).astype(str).str.strip()
            )
            targeted_missing_domains = set()
            for _, missing_row in df.iterrows():
                missing_domain = str(missing_row.get("Domain", "")).strip()
                missing_state = str(missing_row.get("State", "")).strip()
                if (
                    not missing_domain
                    or missing_domain in saved_domains
                    or missing_domain in targeted_missing_domains
                ):
                    continue
                retry_keys.add((missing_state, missing_domain))
                retry_domains.add(missing_domain)
                targeted_missing_domains.add(missing_domain)
        retry_domains.discard("")
        retry_keys.discard(("", ""))
        print(f"Retry mode: will process only {len(retry_keys)} targeted rows.")

    enriched_rows = []
    retry_position = 0
    retry_total = len(retry_keys) if retry_mode else 0

    print("\n--- STEP 2: ENRICHMENT ONLY ---")
    print(f"Input rows: {len(df)}")
    print(f"Output file: {OUTPUT_FILE}")
    if RESUME_AFTER_ROW:
        print(f"Resume override: skipping input rows 1 through {RESUME_AFTER_ROW}.")
    if RETRY_ROW_FROM:
        print(f"Row retry mode: retrying input rows {RETRY_ROW_FROM} through {RETRY_ROW_TO or RETRY_ROW_FROM}.")

    for index, row in df.iterrows():
        row_number = index + 1
        if RESUME_AFTER_ROW and row_number <= RESUME_AFTER_ROW:
            continue

        domain = str(row.get("Domain", "")).strip()
        state = str(row.get("State", "")).strip()
        location = str(row.get("Location", "") or state).strip()
        website = str(row.get("Website", "")).strip()
        row_phone_country_code = phone_code_for_location(f"{state} {location}")

        if not domain and website:
            domain = domain_from_url(website)

        if retry_mode and (state, domain) not in retry_keys:
            continue

        if not retry_mode and domain in done_domains:
            continue

        if retry_mode:
            retry_position += 1
            print(
                f"[RETRY {retry_position}/{retry_total} | "
                f"input {row_number}/{len(df)}] Enriching {domain or website}"
            )
        else:
            print(f"[{row_number}/{len(df)}] Enriching {domain or website}")

        enriched = enrich_website(website, row_phone_country_code)
        output_row = row.to_dict()
        output_row.update(enriched)
        output_row["Phone_Country_Code"] = row_phone_country_code
        output_row["Enriched_At"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        enriched_rows.append(output_row)
        done_domains.add(domain)

        combined = pd.concat(
            [enriched_df, pd.DataFrame(enriched_rows)],
            ignore_index=True,
        )
        combined.to_csv(OUTPUT_FILE, index=False)

        print(f"    {enriched['Enrichment_Status']}")
        time.sleep(REQUEST_DELAY_SECONDS)

    final_df = pd.concat(
        [enriched_df, pd.DataFrame(enriched_rows)],
        ignore_index=True,
    )
    final_df.to_csv(OUTPUT_FILE, index=False)

    print(f"\nDone. Enriched rows saved: {len(final_df)}")
    print(f"Saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
