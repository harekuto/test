$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$final = $env:FINAL_APK
if (!(Test-Path $final)) { throw 'Final APK missing' }

7z t $final | Tee-Object work/apk-zip-test.txt
if ($LASTEXITCODE -ne 0) { throw 'APK ZIP integrity test failed' }

7z l $final | Tee-Object work/apk-list.txt
$list = Get-Content work/apk-list.txt -Raw
if ($list -notmatch 'game\.droid') { throw 'APK lacks game.droid' }
foreach ($n in 1..3) {
    if ($list -notmatch "audiogroup$n\.dat") { throw "APK lacks audiogroup$n.dat" }
}

New-Item -ItemType Directory -Force work/apkextract | Out-Null
Push-Location work/apkextract
7z e -y $final 'assets/game.droid' | Out-Null
Pop-Location

& $env:UTMT_CLI info work/apkextract/game.droid -v 2>&1 | Tee-Object work/final-game-info.txt
if ($LASTEXITCODE -ne 0) { throw 'Final game.droid parsing failed' }

$hash = (Get-FileHash $final -Algorithm SHA256).Hash.ToLower()
$size = (Get-Item $final).Length
"APK_SIZE=$size" | Tee-Object work/final-hash.txt
"APK_SHA256=$hash" | Tee-Object -Append work/final-hash.txt
"RUNNER_TEMPLATE=2.2.2.apk" | Tee-Object -Append work/final-hash.txt
"GM_VERSION=2.2.2.302 BYTECODE=17 VM" | Tee-Object -Append work/final-hash.txt

Write-Host "APK_SIZE=$size"
Write-Host "APK_SHA256=$hash"
