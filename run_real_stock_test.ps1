$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "========================================"
Write-Host "Run real stock footage autocut test"
Write-Host "========================================"

.\download_real_stock_assets.ps1

$InputDir = ".\inputs\case_02_real_stock_test"
$OutputDir = ".\outputs\case_02_real_stock_test"
$TranscriptFile = ".\inputs\case_02_real_stock_test\transcript.json"

python .\main.py run `
  --input $InputDir `
  --output $OutputDir `
  --template product_promo `
  --platform douyin `
  --duration 30 `
  --brief "使用真实下载的视频素材，做一个产品宣传短视频，突出痛点、功能、流程和行动引导" `
  --transcript-file $TranscriptFile `
  --force

Write-Host "========================================"
Write-Host "Done. Check output:"
Write-Host $OutputDir
Write-Host "Try opening:"
Write-Host ".\outputs\case_02_real_stock_test\version_A\version_A_subtitled.mp4"
Write-Host "========================================"
