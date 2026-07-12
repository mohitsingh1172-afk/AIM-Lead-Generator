param(
    [Parameter(Mandatory = $true)]
    [string[]]$CsvFiles
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ExcludeFile = Join-Path $Root "config\exclude_domains.txt"

python (Join-Path $Root "scripts\update_exclusions.py") `
    --exclude-file $ExcludeFile `
    --csv-files $CsvFiles

