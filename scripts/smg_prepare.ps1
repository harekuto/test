$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$env:PYTHONUTF8 = '1'

python -m pip install --upgrade pip
python -m pip install gdown pillow

New-Item -ItemType Directory -Force work, dist | Out-Null
gdown 1P5tBahadA9hu2EH21632YGrFC25ewFaN -O work/original_game.zip
if (!(Test-Path work/original_game.zip)) { throw 'Game download failed' }

$hash = (Get-FileHash work/original_game.zip -Algorithm SHA256).Hash.ToLower()
"ORIGINAL_SHA256=$hash" | Tee-Object work/original-sha256.txt
7z x -y work/original_game.zip -owork/game | Out-Null

$data = Get-ChildItem work/game -Recurse -Filter *.win | Select-Object -First 1
if (!$data) { throw 'GameMaker data file not found' }
"DATA_WIN=$($data.FullName)" | Out-File -Append $env:GITHUB_ENV
"GAME_DIR=$($data.DirectoryName)" | Out-File -Append $env:GITHUB_ENV

git clone https://github.com/znm2500/GameMaker-Mobiler.git work/mobiler
Push-Location work/mobiler
git checkout 6a23adc1d4e71c238456568df18f85cc7b44caa9
Pop-Location

Invoke-WebRequest -Uri 'https://github.com/UnderminersTeam/UndertaleModTool/releases/download/0.9.2.0/UTMT_CLI_v0.9.2.0-Windows.zip' -OutFile work/utmt.zip
Expand-Archive work/utmt.zip -DestinationPath work/utmt -Force
$cli = Get-ChildItem work/utmt -Recurse -Filter UndertaleModCli.exe | Select-Object -First 1
if (!$cli) { throw 'UndertaleModCli.exe not found' }
"UTMT_CLI=$($cli.FullName)" | Out-File -Append $env:GITHUB_ENV

$template = Join-Path $PWD 'work/mobiler/GMS2 APK/2.2.2.apk'
if (!(Test-Path $template)) { throw 'GameMaker 2.2.2 Android runner missing' }
"TEMPLATE_APK=$template" | Out-File -Append $env:GITHUB_ENV

@'
ScriptMessage($"GM_EXACT={Data.GeneralInfo.Major}.{Data.GeneralInfo.Minor}.{Data.GeneralInfo.Release}.{Data.GeneralInfo.Build};BC={Data.GeneralInfo.BytecodeVersion};YYC={Data.IsYYC()}");
'@ | Set-Content work/version.csx -Encoding UTF8

& $cli.FullName load $data.FullName -s work/version.csx -v 2>&1 | Tee-Object work/version-run.txt
$line = Select-String -Path work/version-run.txt -Pattern 'GM_EXACT=' | Select-Object -First 1
if (!$line) { throw 'Could not determine GameMaker version' }
if ($line.Line -notmatch 'GM_EXACT=2\.2\.2\.302;BC=17;YYC=False') {
    throw "Unexpected GameMaker build: $($line.Line)"
}
Write-Host $line.Line
