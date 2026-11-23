$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$CaseDir = Join-Path $ProjectRoot "inputs\case_02_real_stock_test"
$RawDir = Join-Path $CaseDir "raw_downloads"
$ClipDir = Join-Path $CaseDir "normalized_clips"
New-Item -ItemType Directory -Force -Path $RawDir | Out-Null
New-Item -ItemType Directory -Force -Path $ClipDir | Out-Null

Write-Host "========================================"
Write-Host "Download real stock videos and build test case"
Write-Host "========================================"

$downloads = @(
    @{ Name = "road_city_5s.mp4"; Url = "https://samplelib.com/mp4/sample-5s-360p.mp4" },
    @{ Name = "buses_10s.mp4"; Url = "https://samplelib.com/mp4/sample-10s-360p.mp4" },
    @{ Name = "traffic_15s.mp4"; Url = "https://samplelib.com/mp4/sample-15s-360p.mp4" },
    @{ Name = "road_traffic_20s.mp4"; Url = "https://samplelib.com/mp4/sample-20s-360p.mp4" },
    @{ Name = "park_people_30s.mp4"; Url = "https://samplelib.com/mp4/sample-30s-360p.mp4" }
)

foreach ($item in $downloads) {
    $out = Join-Path $RawDir $item.Name
    if (!(Test-Path $out)) {
        Write-Host "[DOWNLOAD] $($item.Name)"
        Invoke-WebRequest -Uri $item.Url -OutFile $out
    } else {
        Write-Host "[SKIP] Already exists: $($item.Name)"
    }
}

Write-Host "[INFO] Generating Chinese voiceover..."
$voiceText = Get-Content -Raw -Encoding UTF8 (Join-Path $CaseDir "script.txt")
$voicePath = Join-Path $CaseDir "voiceover.wav"
try {
    Add-Type -AssemblyName System.Speech
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $voice = $synth.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -like "zh-*" } | Select-Object -First 1
    if ($voice) {
        $synth.SelectVoice($voice.VoiceInfo.Name)
        Write-Host "[INFO] Using voice: $($voice.VoiceInfo.Name)"
    } else {
        Write-Host "[WARN] No Chinese SAPI voice found. Using default Windows voice."
    }
    $synth.Rate = 0
    $synth.Volume = 100
    $synth.SetOutputToWaveFile($voicePath)
    $synth.Speak($voiceText)
    $synth.Dispose()
} catch {
    Write-Host "[WARN] Windows SAPI voice generation failed. Creating fallback tone audio."
    ffmpeg -y -f lavfi -i "sine=frequency=440:duration=32" -ar 48000 -ac 2 $voicePath
}

Write-Host "[INFO] Generating background music..."
$musicPath = Join-Path $CaseDir "background_music.wav"
ffmpeg -y -f lavfi -i "sine=frequency=220:duration=32" -f lavfi -i "sine=frequency=330:duration=32" -filter_complex "[0:a]volume=0.06[a0];[1:a]volume=0.04[a1];[a0][a1]amix=inputs=2,afade=t=in:st=0:d=1,afade=t=out:st=30:d=2" -ar 48000 -ac 2 $musicPath

Write-Host "[INFO] Normalizing real stock clips to vertical video..."
$index = 1
foreach ($item in $downloads) {
    $src = Join-Path $RawDir $item.Name
    $dst = Join-Path $ClipDir ("clip_{0:D2}.mp4" -f $index)
    ffmpeg -y -i $src -t 7 -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1" -r 30 -an -c:v libx264 -preset ultrafast -pix_fmt yuv420p $dst
    $index++
}

$concatList = Join-Path $CaseDir "concat_real_stock.txt"
$clipLines = Get-ChildItem $ClipDir -Filter "clip_*.mp4" | Sort-Object Name | ForEach-Object { "file '$($_.FullName.Replace('\\','/'))'" }
$clipLines | Set-Content -Encoding UTF8 $concatList

$videoOnly = Join-Path $CaseDir "main_video_only.mp4"
ffmpeg -y -f concat -safe 0 -i $concatList -c:v libx264 -preset ultrafast -pix_fmt yuv420p $videoOnly

Write-Host "[INFO] Mixing voiceover and background music into main_talk.mp4..."
$mainTalk = Join-Path $CaseDir "main_talk.mp4"
ffmpeg -y -i $videoOnly -i $voicePath -i $musicPath -filter_complex "[1:a]volume=1.35,apad[a1];[2:a]volume=0.18,apad[a2];[a1][a2]amix=inputs=2:duration=longest,atrim=0:32[a]" -map 0:v -map "[a]" -t 32 -c:v copy -c:a aac -ar 48000 -ac 2 $mainTalk

Copy-Item (Join-Path $ClipDir "clip_02.mp4") (Join-Path $CaseDir "broll_bus.mp4") -Force
Copy-Item (Join-Path $ClipDir "clip_03.mp4") (Join-Path $CaseDir "broll_traffic.mp4") -Force
Copy-Item (Join-Path $ClipDir "clip_05.mp4") (Join-Path $CaseDir "broll_park_people.mp4") -Force

$info = @{
    case_name = "case_02_real_stock_test"
    source = "samplelib.com MP4 sample files"
    main_video = "main_talk.mp4"
    voiceover = "voiceover.wav"
    background_music = "background_music.wav"
    transcript = "transcript.json"
    note = "Real stock footage downloaded locally, then combined with generated voiceover and background music."
} | ConvertTo-Json -Depth 4
$info | Set-Content -Encoding UTF8 (Join-Path $CaseDir "case_info.json")

Write-Host "========================================"
Write-Host "Real stock test case generated:"
Write-Host $CaseDir
Write-Host "Main video: $mainTalk"
Write-Host "========================================"
