$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$env:PYTHONUTF8='1'

python -m pip install --upgrade pip gdown pillow | Out-Null
New-Item -ItemType Directory -Force work, dist | Out-Null

gdown 'https://drive.google.com/uc?id=1Iy5ZMgEM_JP7wxeSNySKD4fdxz3dWo3e' -O work/original.rar
if(!(Test-Path work/original.rar)){ throw 'Game download failed' }
$hash=(Get-FileHash work/original.rar -Algorithm SHA256).Hash.ToLower()
if($hash -ne '63e12e9776d3421a6e9716da5564f608a38f9dd3c41a80c2a5d5c29923eb4131'){ throw "Original archive SHA mismatch: $hash" }
"ORIGINAL_SHA256=$hash" | Tee-Object work/original-sha256.txt

7z x -y work/original.rar -owork/game | Out-Null
$data=Get-ChildItem work/game -Recurse -Filter data.win | Select-Object -First 1
if(!$data){ throw 'data.win missing' }
"DATA_WIN=$($data.FullName)" | Out-File -Append $env:GITHUB_ENV
"GAME_DIR=$($data.DirectoryName)" | Out-File -Append $env:GITHUB_ENV

git clone https://github.com/znm2500/GameMaker-Mobiler.git work/mobiler
Push-Location work/mobiler
git checkout 6a23adc1d4e71c238456568df18f85cc7b44caa9
Pop-Location

Invoke-WebRequest -Uri 'https://github.com/UnderminersTeam/UndertaleModTool/releases/download/0.9.2.0/UTMT_CLI_v0.9.2.0-Windows.zip' -OutFile work/utmt.zip
Expand-Archive work/utmt.zip -DestinationPath work/utmt -Force
$cli=Get-ChildItem work/utmt -Recurse -Filter UndertaleModCli.exe | Select-Object -First 1
if(!$cli){ throw 'UTMT CLI missing' }
"UTMT_CLI=$($cli.FullName)" | Out-File -Append $env:GITHUB_ENV

$template=Join-Path $PWD 'work/mobiler/GMS2 APK/2023.11.apk'
if(!(Test-Path $template)){ throw '2023.11 Android runner template missing' }
"TEMPLATE_APK=$template" | Out-File -Append $env:GITHUB_ENV

@'
ScriptMessage($"GM_EXACT={Data.GeneralInfo.Major}.{Data.GeneralInfo.Minor}.{Data.GeneralInfo.Release}.{Data.GeneralInfo.Build};BC={Data.GeneralInfo.BytecodeVersion};YYC={Data.IsYYC()}");
'@ | Set-Content work/version.csx -Encoding UTF8
& $cli.FullName load $data.FullName -s work/version.csx -v 2>&1 | Tee-Object work/version-run.txt
if($LASTEXITCODE -ne 0){ throw 'Version inspection failed' }
$v=Get-Content work/version-run.txt -Raw
if($v -notmatch 'GM_EXACT=2023\.8\.0\.0;BC=17;YYC=False'){ throw 'Unexpected GameMaker build' }
