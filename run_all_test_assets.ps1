$ErrorActionPreference = "Stop"

Write-Host "========================================"
Write-Host "AI Video Autocut Test Assets Runner"
Write-Host "========================================"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$InputDir = ".\inputs\case_01_product_promo"
$OutputDir = ".\outputs\case_01_product_promo"
$TranscriptFile = ".\inputs\case_01_product_promo\transcript.json"

if (!(Test-Path ".\main.py")) {
    Write-Host "[ERROR] main.py not found. Please run this script in project root."
    exit 1
}

if (!(Test-Path $InputDir)) {
    Write-Host "[ERROR] Input directory not found: $InputDir"
    exit 1
}

if (!(Test-Path $TranscriptFile)) {
    Write-Host "[ERROR] Transcript file not found: $TranscriptFile"
    exit 1
}

Write-Host "[INFO] Input: $InputDir"
Write-Host "[INFO] Output: $OutputDir"
Write-Host "[INFO] Transcript: $TranscriptFile"
Write-Host ""

$argsList = @(
    "run",
    "--input", $InputDir,
    "--output", $OutputDir,
    "--template", "short_talk",
    "--platform", "douyin",
    "--duration", "30",
    "--brief", "产品宣传短视频测试，节奏快一点，突出痛点、卖点和结尾行动引导",
    "--transcript-file", $TranscriptFile,
    "--force"
)

python .\main.py @argsList

Write-Host ""
Write-Host "========================================"
Write-Host "Done"
Write-Host "Check output directory:"
Write-Host $OutputDir
Write-Host "========================================"
