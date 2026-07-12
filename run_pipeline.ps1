param(
    [string]$ProjectName = "lead_project",
    [int]$MaxResultsPerQuery = 20,
    [string]$PhoneCountryCode = "+1"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Config = Join-Path $Root "config"
$Output = Join-Path $Root "outputs"
$Scripts = Join-Path $Root "scripts"

Set-Location $Root
New-Item -ItemType Directory -Force -Path $Output | Out-Null

if (-not $env:SCRAPEDO_TOKEN) {
    throw "SCRAPEDO_TOKEN is not set. Set it in this PowerShell session first."
}

$env:PROJECT_NAME = $ProjectName
$env:LOCATIONS_FILE = Join-Path $Config "locations.txt"
$env:KEYWORDS_FILE = Join-Path $Config "keywords.txt"
$env:EXCLUDE_DOMAINS_FILE = Join-Path $Config "exclude_domains.txt"
$env:DISCOVERY_OUTPUT_FILE = Join-Path $Output "${ProjectName}_discovered.csv"
$env:MAX_RESULTS_PER_QUERY = "$MaxResultsPerQuery"
$env:SEARCH_START_RESULT = "0"
$env:SKIP_COMPLETED_QUERIES = "1"
$env:REQUEST_DELAY_SECONDS = "2"

python (Join-Path $Scripts "discover.py")

$env:GENERIC_DISCOVERY_FILE = Join-Path $Output "${ProjectName}_discovered.csv"
$env:ENRICH_INPUT_FILE = Join-Path $Output "${ProjectName}_for_enrichment.csv"
python (Join-Path $Scripts "prepare.py")

$env:USE_SCRAPEDO = "0"
$env:SCRAPEDO_FIRST = "0"
$env:PHONE_COUNTRY_CODE = $PhoneCountryCode
$env:MAX_PAGES_PER_WEBSITE = "3"
$env:REQUEST_DELAY_SECONDS = "0.20"
$env:MAX_HTML_BYTES = "700000"
$env:DIRECT_CONNECT_TIMEOUT = "5"
$env:DIRECT_READ_TIMEOUT = "8"
$env:STOP_AFTER_CONTACT_FOUND = "1"
$env:RETRY_FAILED = "0"
$env:RETRY_DNS_FAILED = "0"
$env:RETRY_MISSING = "0"
$env:RESUME_AFTER_ROW = "0"
$env:RETRY_ROW_FROM = "0"
$env:RETRY_ROW_TO = "0"
$env:ENRICH_INPUT_FILE = Join-Path $Output "${ProjectName}_for_enrichment.csv"
$env:ENRICH_OUTPUT_FILE = Join-Path $Output "${ProjectName}_enriched.csv"

python (Join-Path $Scripts "enrich.py")

$env:CLEAN_INPUT_FILE = Join-Path $Output "${ProjectName}_enriched.csv"
$env:CLEAN_OUTPUT_FILE = Join-Path $Output "${ProjectName}_cleaned.csv"
$env:REJECTED_OUTPUT_FILE = Join-Path $Output "${ProjectName}_rejected.csv"

python (Join-Path $Scripts "clean.py")

Write-Host ""
Write-Host "Pipeline complete:"
Write-Host (Join-Path $Output "${ProjectName}_cleaned.csv")

