# Quick local validation: use the bundled transcript and smaller output.
$env:OUTPUT_WIDTH="360"
$env:OUTPUT_HEIGHT="640"
$env:OUTPUT_FPS="8"

python .\main.py run `
  --input .\inputs\demo `
  --output .\outputs\demo_fixture `
  --template short_talk `
  --platform douyin `
  --duration 12 `
  --transcript-file .\inputs\demo\demo_transcript.json `
  --brief "demo validation" `
  --force
