$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$env:HHP_PACKAGE='com.harekuto.happyheartpanic'
$env:HHP_VERSION='2025-android-v4'
$env:HHP_VCODE='400'

$apktool=Get-ChildItem work/mobiler -Recurse -Filter 'apktool_3.0.3.jar' | Select-Object -First 1
if(!$apktool){ throw 'apktool missing' }
"APKTOOL=$($apktool.FullName)" | Out-File -Append $env:GITHUB_ENV

java -jar $apktool.FullName d -f -o work/apkdecoded $env:TEMPLATE_APK
if($LASTEXITCODE -ne 0){ throw 'apktool decode failed' }
python happyheart/patch_apk.py work/apkdecoded

New-Item -ItemType Directory -Force work/apkdecoded/assets | Out-Null
Remove-Item work/apkdecoded/assets/game.droid -Force -ErrorAction SilentlyContinue
Copy-Item $env:MOBILE_WIN work/apkdecoded/assets/game.droid -Force

# Preserve every static sidecar file the Windows game opens at runtime.
$sidecars=@('supporters.txt','credits.txt','CONTROLS.txt')
Remove-Item work/sidecar-hashes.txt -Force -ErrorAction SilentlyContinue
foreach($name in $sidecars){
  $src=Join-Path $env:GAME_DIR $name
  if(!(Test-Path $src)){ throw "Required original sidecar missing: $name" }
  Copy-Item $src (Join-Path 'work/apkdecoded/assets' $name) -Force
  $h=(Get-FileHash $src -Algorithm SHA256).Hash.ToLower()
  "$name=$h" | Add-Content work/sidecar-hashes.txt
}

$dlc=Join-Path $env:GAME_DIR 'dlc'
if(Test-Path $dlc){
  New-Item -ItemType Directory -Force work/apkdecoded/assets/dlc | Out-Null
  Copy-Item (Join-Path $dlc '*') work/apkdecoded/assets/dlc -Recurse -Force
}

java -Xmx4g -jar $apktool.FullName b -f --no-crunch -o work/unsigned.apk work/apkdecoded
if($LASTEXITCODE -ne 0){ throw 'apktool build failed' }
if(!(Test-Path work/unsigned.apk)){ throw 'unsigned APK missing' }
