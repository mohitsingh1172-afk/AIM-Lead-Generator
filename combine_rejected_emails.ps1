param(
    [string]$ProjectName = "lead_project"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

python (Join-Path $Root "scripts\combine_rejected_emails.py") `
    --cleaned (Join-Path $Root "outputs\${ProjectName}_cleaned.csv") `
    --rejected (Join-Path $Root "outputs\${ProjectName}_rejected.csv") `
    --output (Join-Path $Root "outputs\${ProjectName}_cleaned_with_rejected_emails.csv")

