$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$final=$env:FINAL_APK
if(!(Test-Path $final)){ throw 'Final APK missing' }
$badging=Get-Content work/aapt-badging.txt -Raw
if($badging -notmatch "name='com\.harekuto\.happyheartpanic'"){ throw 'package mismatch' }
if($badging -notmatch "versionCode='100'"){ throw 'versionCode mismatch' }
if($badging -notmatch "versionName='2025-android-v1'"){ throw 'versionName mismatch' }

7z t $final | Tee-Object work/apk-zip-test.txt
if($LASTEXITCODE -ne 0){ throw 'ZIP integrity failed' }
7z l $final | Tee-Object work/apk-list.txt
$list=Get-Content work/apk-list.txt -Raw
if($list -notmatch 'assets\\game\.droid'){ throw 'game.droid missing' }
if($list -notmatch 'assets\\dlc\\maxwell\.gif'){ throw 'DLC asset missing' }
if($list -notmatch 'lib\\arm64-v8a\\libyoyo\.so'){ throw 'arm64 runner missing' }
if($list -notmatch 'lib\\x86_64\\libyoyo\.so'){ throw 'x86_64 runner missing' }

7z l -slt $final | Tee-Object work/apk-list-slt.txt | Out-Null
$current=''
$sz=$null;$packed=$null
foreach($line in Get-Content work/apk-list-slt.txt){
  if($line -match '^Path = (.+)$'){ $current=$Matches[1]; continue }
  $isGame=($current -eq 'assets\game.droid') -or ($current -eq 'assets/game.droid')
  if($isGame -and $line -match '^Size = ([0-9]+)$'){ $sz=[int64]$Matches[1]; continue }
  if($isGame -and $line -match '^Packed Size = ([0-9]+)$'){ $packed=[int64]$Matches[1] }
}
if($null -eq $sz -or $null -eq $packed){ throw 'Cannot inspect game.droid compression' }
if($sz -ne $packed){ throw "game.droid compressed ($packed/$sz)" }
"GAME_DROID_STORED=$sz" | Tee-Object work/game-droid-compression.txt

New-Item -ItemType Directory -Force work/apkextract | Out-Null
Push-Location work/apkextract
7z e -y $final 'assets/game.droid' | Out-Null
Pop-Location
& $env:UTMT_CLI info work/apkextract/game.droid -v 2>&1 | Tee-Object work/final-game-info.txt
if($LASTEXITCODE -ne 0){ throw 'Final game.droid parsing failed' }

$hash=(Get-FileHash $final -Algorithm SHA256).Hash.ToLower()
$size=(Get-Item $final).Length
"APK_SIZE=$size" | Tee-Object work/final-hash.txt
"APK_SHA256=$hash" | Tee-Object -Append work/final-hash.txt
"RUNNER_TEMPLATE=2023.11.apk" | Tee-Object -Append work/final-hash.txt
"GAME_VERSION=2023.8.0.0 BYTECODE=17 VM" | Tee-Object -Append work/final-hash.txt
"GAME_DROID_STORED=$sz" | Tee-Object -Append work/final-hash.txt
