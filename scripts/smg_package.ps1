$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$env:PYTHONUTF8 = '1'
$env:PACKAGE_NAME = 'com.harekuto.supermonstersgirls'
$env:APP_NAME = "Super Monsters'n Girls"
$env:VERSION_NAME = '2.0.2-android-v2'
$env:VERSION_CODE = '200'

if (!(Test-Path $env:TEMPLATE_APK)) { throw 'Android runner template missing' }
if (!(Test-Path $env:MOBILE_WIN)) { throw 'MOBILE_WIN missing' }

$apktool = Get-ChildItem work/mobiler -Recurse -Filter 'apktool_3.0.3.jar' | Select-Object -First 1
if (!$apktool) { throw 'apktool jar not found' }
"APKTOOL=$($apktool.FullName)" | Out-File -Append $env:GITHUB_ENV

java -jar $apktool.FullName d -f -o work/apkdecoded $env:TEMPLATE_APK
if ($LASTEXITCODE -ne 0) { throw 'apktool decode failed' }

python scripts/smg_patch_apk.py work/apkdecoded

New-Item -ItemType Directory -Force work/apkdecoded/assets | Out-Null
Remove-Item work/apkdecoded/assets/game.droid -Force -ErrorAction SilentlyContinue
Copy-Item $env:MOBILE_WIN work/apkdecoded/assets/game.droid -Force

Get-ChildItem $env:GAME_DIR -Filter 'audiogroup*.dat' | ForEach-Object {
    Copy-Item $_.FullName (Join-Path 'work/apkdecoded/assets' $_.Name) -Force
}

$groups = Get-ChildItem work/apkdecoded/assets -Filter 'audiogroup*.dat'
if ($groups.Count -lt 3) { throw "Expected 3 audio groups, found $($groups.Count)" }

$gameDroid = Get-Item work/apkdecoded/assets/game.droid
"GAME_DROID_SIZE=$($gameDroid.Length)" | Tee-Object work/game-droid-size.txt
$groups | Format-Table Name,Length

java -Xmx6g -jar $apktool.FullName b -f --no-crunch -o work/unsigned.apk work/apkdecoded
if ($LASTEXITCODE -ne 0) { throw 'apktool build failed' }
if (!(Test-Path work/unsigned.apk)) { throw 'unsigned APK missing' }
