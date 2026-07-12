param(
    [string]$ProjectName = "lead_project",
    [string]$PhoneCountryCode = "+1"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Output = Join-Path $Root "outputs"
$Scripts = Join-Path $Root "scripts"

Set-Location $Root

if (-not $env:SCRAPEDO_TOKEN) {
    throw "SCRAPEDO_TOKEN is not set. Set it in this PowerShell session first."
}

$env:PROJECT_NAME = $ProjectName
$env:USE_SCRAPEDO = "1"
$env:SCRAPEDO_FIRST = "1"
$env:PHONE_COUNTRY_CODE = $PhoneCountryCode
$env:RETRY_FAILED = "1"
$env:RETRY_MISSING = "1"
$env:RETRY_DNS_FAILED = "0"
$env:RESUME_AFTER_ROW = "0"
$env:RETRY_ROW_FROM = "0"
$env:RETRY_ROW_TO = "0"
$env:MAX_PAGES_PER_WEBSITE = "2"
$env:REQUEST_DELAY_SECONDS = "0.10"
$env:MAX_HTML_BYTES = "600000"
$env:DIRECT_CONNECT_TIMEOUT = "4"
$env:DIRECT_READ_TIMEOUT = "6"
$env:SCRAPEDO_TIMEOUT = "12"
$env:STOP_AFTER_CONTACT_FOUND = "1"
$env:ENRICH_INPUT_FILE = Join-Path $Output "${ProjectName}_for_enrichment.csv"
$env:ENRICH_OUTPUT_FILE = Join-Path $Output "${ProjectName}_enriched.csv"

python (Join-Path $Scripts "enrich.py")

$env:CLEAN_INPUT_FILE = Join-Path $Output "${ProjectName}_enriched.csv"
$env:CLEAN_OUTPUT_FILE = Join-Path $Output "${ProjectName}_cleaned.csv"
$env:REJECTED_OUTPUT_FILE = Join-Path $Output "${ProjectName}_rejected.csv"

python (Join-Path $Scripts "clean.py")

Write-Host ""
Write-Host "Retry complete:"
Write-Host (Join-Path $Output "${ProjectName}_cleaned.csv")

