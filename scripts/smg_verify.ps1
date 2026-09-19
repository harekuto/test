$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$final = $env:FINAL_APK
if (!(Test-Path $final)) { throw 'Final APK missing' }

$badging = Get-Content work/aapt-badging.txt -Raw
if ($badging -notmatch "name='com\.harekuto\.supermonstersgirls'") { throw 'Final APK package mismatch' }
if ($badging -notmatch "versionCode='300'") { throw 'Final APK versionCode mismatch' }
if ($badging -notmatch "versionName='2\.0\.2-android-v3'") { throw 'Final APK versionName mismatch' }

7z t $final | Tee-Object work/apk-zip-test.txt
if ($LASTEXITCODE -ne 0) { throw 'APK ZIP integrity test failed' }

7z l $final | Tee-Object work/apk-list.txt
$list = Get-Content work/apk-list.txt -Raw
if ($list -notmatch 'game\.droid') { throw 'APK lacks game.droid' }
foreach ($n in 1..3) {
    if ($list -notmatch "audiogroup$n\.dat") { throw "APK lacks audiogroup$n.dat" }
}
if ($list -notmatch 'lib\\arm64-v8a\\libyoyo\.so') { throw 'APK lacks arm64 GameMaker runner' }
if ($list -notmatch 'lib\\x86\\libyoyo\.so') { throw 'APK lacks x86 GameMaker runner' }

7z l -slt $final | Tee-Object work/apk-list-slt.txt | Out-Null
$currentPath = ''
$gameSize = $null
$gamePacked = $null
foreach ($line in Get-Content work/apk-list-slt.txt) {
    if ($line -match '^Path = (.+)$') {
        $currentPath = $Matches[1]
        continue
    }
    $isGameDroid = ($currentPath -eq 'assets\game.droid') -or ($currentPath -eq 'assets/game.droid')
    if ($isGameDroid -and $line -match '^Size = ([0-9]+)$') {
        $gameSize = [int64]$Matches[1]
        continue
    }
    if ($isGameDroid -and $line -match '^Packed Size = ([0-9]+)$') {
        $gamePacked = [int64]$Matches[1]
    }
}
if ($null -eq $gameSize -or $null -eq $gamePacked) {
    throw 'Could not inspect game.droid compression mode'
}
if ($gameSize -ne $gamePacked) {
    throw "game.droid is compressed ($gamePacked/$gameSize); legacy runner would inflate it into RAM"
}
"GAME_DROID_STORED=$gameSize" | Tee-Object work/game-droid-compression.txt

New-Item -ItemType Directory -Force work/apkextract | Out-Null
Push-Location work/apkextract
7z e -y $final 'assets/game.droid' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not extract game.droid' }
Pop-Location

& $env:UTMT_CLI info work/apkextract/game.droid -v 2>&1 | Tee-Object work/final-game-info.txt
if ($LASTEXITCODE -ne 0) { throw 'Final game.droid parsing failed' }

$hash = (Get-FileHash $final -Algorithm SHA256).Hash.ToLower()
$size = (Get-Item $final).Length
"APK_SIZE=$size" | Tee-Object work/final-hash.txt
"APK_SHA256=$hash" | Tee-Object -Append work/final-hash.txt
"RUNNER_TEMPLATE=2.2.2.apk" | Tee-Object -Append work/final-hash.txt
"GM_VERSION=2.2.2.302 BYTECODE=17 VM" | Tee-Object -Append work/final-hash.txt
"GAME_DROID_STORED=$gameSize" | Tee-Object -Append work/final-hash.txt

Write-Host "APK_SIZE=$size"
Write-Host "APK_SHA256=$hash"
Write-Host "GAME_DROID_STORED=$gameSize"
