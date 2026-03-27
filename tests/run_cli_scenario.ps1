[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Binary,

    [Parameter(Mandatory = $true, Position = 1)]
    [string]$InputFile,

    [Parameter(Position = 2, ValueFromRemainingArguments = $true)]
    [string[]]$ExpectedFragments = @()
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $Binary)) {
    throw "binary not found: $Binary"
}

if (-not (Test-Path -LiteralPath $InputFile)) {
    throw "input file not found: $InputFile"
}

$inputText = Get-Content -LiteralPath $InputFile -Raw
$output = $inputText | & $Binary | Out-String
$normalized = $output -replace "`r", ""

foreach ($expected in $ExpectedFragments) {
    if (-not $normalized.Contains($expected)) {
        Write-Error "missing expected output fragment: $expected"
        Write-Error "--- output ---"
        Write-Error $normalized
        exit 1
    }
}

exit 0
