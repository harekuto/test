$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$bt = Get-ChildItem "$env:ANDROID_HOME/build-tools" -Directory |
    Sort-Object {[version]$_.Name} -Descending |
    Select-Object -First 1
if (!$bt) { throw 'Android build-tools missing' }

$zipalign = Join-Path $bt.FullName 'zipalign.exe'
$apksigner = Join-Path $bt.FullName 'apksigner.bat'
$aapt = Join-Path $bt.FullName 'aapt.exe'
if (!(Test-Path $zipalign) -or !(Test-Path $apksigner) -or !(Test-Path $aapt)) {
    throw 'Required Android tools missing'
}

New-Item -ItemType Directory -Force dist | Out-Null
$pass = [guid]::NewGuid().ToString('N')
$keyStore = 'work/port.keystore'
keytool -genkeypair -keystore $keyStore -storepass $pass -keypass $pass -alias port -keyalg RSA -keysize 2048 -validity 10000 -dname 'CN=Android Port,O=Harekuto,C=KZ'

& $zipalign -f -p 4 work/unsigned.apk work/aligned.apk
if ($LASTEXITCODE -ne 0) { throw 'zipalign failed' }

$final = Join-Path $PWD 'dist/Super-Monsters-n-Girls-v2.0.2-Android-v1.apk'
& $apksigner sign --ks $keyStore --ks-key-alias port --ks-pass "pass:$pass" --key-pass "pass:$pass" --out $final work/aligned.apk
if ($LASTEXITCODE -ne 0) { throw 'APK signing failed' }

& $apksigner verify --verbose --print-certs $final | Tee-Object work/signature.txt
& $aapt dump badging $final | Tee-Object work/aapt-badging.txt
& $zipalign -c -v 4 $final | Tee-Object work/zipalign-check.txt
if ($LASTEXITCODE -ne 0) { throw 'APK verification failed' }

"FINAL_APK=$final" | Out-File -Append $env:GITHUB_ENV
