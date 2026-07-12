# Standard Lead Generator

A resumable lead-generation pipeline for discovering business websites through
Google via Scrape.do, enriching public contact details, cleaning results, and
maintaining reusable exclusion lists.

## Pipeline

1. **Discovery**
   - Combines every keyword with every location.
   - Searches Google through Scrape.do.
   - Excludes known, noisy, or previously discovered domains.
   - Saves after every query and resumes safely after interruption.

2. **Preparation**
   - Normalizes discovery output for enrichment.

3. **Contact enrichment**
   - Visits company websites directly.
   - Checks selected contact/about/supplier pages.
   - Extracts public emails, phones, WhatsApp, Facebook, Instagram, and
     LinkedIn.
   - Saves after every website.

4. **Cleaning**
   - Keeps records with email, phone, or WhatsApp.
   - Separates failed, contactless, directory, and article/resource rows.

5. **Failed-row retry**
   - Uses Scrape.do only for failed or currently missing domains.
   - Processes each missing domain once, even if it appeared in many locations.

6. **Optional review-file recovery**
   - Adds unique rejected rows that contain email addresses.
   - Labels them `Review Required`.
   - Preserves the original rejection reason.

## Repository Structure

```text
standard-lead-generator/
|-- config/
|   |-- keywords.txt
|   |-- locations.txt
|   `-- exclude_domains.txt
|-- outputs/
|   `-- .gitkeep
|-- scripts/
|   |-- discover.py
|   |-- prepare.py
|   |-- enrich.py
|   |-- clean.py
|   |-- combine_rejected_emails.py
|   `-- update_exclusions.py
|-- .env.example
|-- .gitignore
|-- requirements.txt
|-- run_pipeline.ps1
|-- retry_failed.ps1
|-- combine_rejected_emails.ps1
`-- update_exclusions.ps1
```

## Requirements

- Windows PowerShell
- Python 3.10+
- A Scrape.do API token
- Git, only when publishing to GitHub

Install Python dependencies:

```powershell
cd "C:\path\to\standard-lead-generator"
python -m pip install -r requirements.txt
```

## Configure a Lead Project

Edit these three files:

### `config/keywords.txt`

Use one buyer-intent phrase per line:

```text
dog chew importer
pet supplement distributor
private label pet products
```

### `config/locations.txt`

Use one country, state, region, or city per line:

```text
United States
California
United Kingdom
London, United Kingdom
```

### `config/exclude_domains.txt`

Use one root domain per line:

```text
amazon.com
facebook.com
yelp.com
```

Comments beginning with `#` and blank lines are ignored.

## Run the Pipeline

Set the token only in the current PowerShell session:

```powershell
$env:SCRAPEDO_TOKEN="your_real_token"
```

Run:

```powershell
.\run_pipeline.ps1 `
  -ProjectName "dog_chew_buyers" `
  -MaxResultsPerQuery 20 `
  -PhoneCountryCode "+1"
```

## Run the Browser App

The browser app lets users enter locations, keywords, result depth, and excluded
domains from a web page. It runs the same discovery, enrichment, and cleaning
pipeline, shows cleaned results page by page, and can download the cleaned file
as CSV or Excel.

Start it:

```powershell
cd "C:\path\to\standard-lead-generator"
$env:SCRAPEDO_TOKEN="your_real_token"
python web_app.py
```

Open:

```text
http://127.0.0.1:8765
```

The token can be set in PowerShell, or typed into the web form for a single
run. Job data is saved under:

```text
runs/
```

The web app is intentionally built with Python's standard library so a frontend
developer can replace the UI without changing the pipeline behavior.

Use `10` results per query for a low-credit pilot. Increase to `20`, `30`, or
`50` only after checking quality and remaining credits.

Generated files:

```text
outputs/dog_chew_buyers_discovered.csv
outputs/dog_chew_buyers_for_enrichment.csv
outputs/dog_chew_buyers_enriched.csv
outputs/dog_chew_buyers_cleaned.csv
outputs/dog_chew_buyers_rejected.csv
```

## Resume an Interrupted Run

Run the same command again. Discovery skips completed keyword/location pairs,
and enrichment skips domains already saved.

## Retry Failed Enrichment

Run after the main pipeline finishes:

```powershell
.\retry_failed.ps1 `
  -ProjectName "dog_chew_buyers" `
  -PhoneCountryCode "+1"
```

Retry progress is displayed separately from original input position:

```text
[RETRY 12/240 | input 518/4300] Enriching example.com
```

## Include Rejected Rows That Have Email Addresses

This does not overwrite the strict cleaned file:

```powershell
.\combine_rejected_emails.ps1 -ProjectName "dog_chew_buyers"
```

Output:

```text
outputs/dog_chew_buyers_cleaned_with_rejected_emails.csv
```

Added records are labelled:

```text
Rejected Lead With Email - Review Required
```

## Add Previously Found Domains to Exclusions

To prevent rediscovery in a new campaign:

```powershell
.\update_exclusions.ps1 -CsvFiles @(
  "C:\path\to\old_project_cleaned.csv",
  "C:\path\to\another_discovered.csv"
)
```

This updates `config/exclude_domains.txt`.

## Lead Definitions

- **Cleaned lead:** has at least one public email, phone, or WhatsApp contact.
- **Email-ready lead:** has a non-empty `Emails` field.
- **Phone-only lead:** has a phone but no email.
- **Review-required lead:** rejected by quality rules but retained because an
  email was found.

Do not treat every cleaned row as email-ready.

## Credit Management

- Start with national or top-market locations.
- Start with 10 results per query.
- Avoid running several discovery jobs simultaneously.
- Website enrichment is direct by default and does not use Scrape.do.
- Failed-row retry uses Scrape.do and should be run only after reviewing
  failure counts.

## Security

- Never store a real API token in a file committed to Git.
- `.env` and generated output files are ignored.
- Set `SCRAPEDO_TOKEN` in PowerShell for each session.
- If a token was ever committed, rotate it before publishing the repository.

## Publish to GitHub

First install [Git for Windows](https://git-scm.com/download/win), then restart
PowerShell.

Create an empty repository on GitHub without a README or `.gitignore`. Then:

```powershell
cd "C:\path\to\standard-lead-generator"

git init
git add .
git status
git commit -m "Create standard lead generation pipeline"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/standard-lead-generator.git
git push -u origin main
```

Before `git commit`, inspect `git status` and confirm that no CSV outputs,
tokens, or secret files are staged.

## Disclaimer

Use public business contact information responsibly. Follow applicable privacy,
anti-spam, website terms, import/export, and marketing regulations in each
target jurisdiction.
