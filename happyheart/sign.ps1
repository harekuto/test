$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$bt=Get-ChildItem "$env:ANDROID_HOME/build-tools" -Directory | Sort-Object {[version]$_.Name} -Descending | Select-Object -First 1
if(!$bt){ throw 'Android build-tools missing' }
$zipalign=Join-Path $bt.FullName 'zipalign.exe'
$apksigner=Join-Path $bt.FullName 'apksigner.bat'
$aapt=Join-Path $bt.FullName 'aapt.exe'
New-Item -ItemType Directory -Force dist | Out-Null
$pass=[guid]::NewGuid().ToString('N')
$key='work/hhp.keystore'
keytool -genkeypair -keystore $key -storepass $pass -keypass $pass -alias hhp -keyalg RSA -keysize 2048 -validity 10000 -dname 'CN=Happy Heart Panic Android,O=Harekuto,C=KZ'
& $zipalign -f -p 4 work/unsigned.apk work/aligned.apk
if($LASTEXITCODE -ne 0){ throw 'zipalign failed' }
$final=Join-Path $PWD 'dist/Happy-Heart-Panic-2025-Android-v1.apk'
& $apksigner sign --ks $key --ks-key-alias hhp --ks-pass "pass:$pass" --key-pass "pass:$pass" --out $final work/aligned.apk
if($LASTEXITCODE -ne 0){ throw 'sign failed' }
& $apksigner verify --verbose --print-certs $final | Tee-Object work/signature.txt
if($LASTEXITCODE -ne 0){ throw 'signature verify failed' }
& $aapt dump badging $final | Tee-Object work/aapt-badging.txt
& $zipalign -c -v 4 $final | Tee-Object work/zipalign-check.txt
if($LASTEXITCODE -ne 0){ throw 'zipalign verify failed' }
"FINAL_APK=$final" | Out-File -Append $env:GITHUB_ENV
