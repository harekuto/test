#!/usr/bin/env bash
set -euo pipefail

VER="${RUNNER_VERSION:?RUNNER_VERSION missing}"
GAME_DROID="artifact/game.droid"
test -s "$GAME_DROID"
mkdir -p test/assets

BUILD_TOOLS="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BUILD_TOOLS/zipalign"
APKSIGNER="$BUILD_TOOLS/apksigner"
AAPT="$BUILD_TOOLS/aapt"

curl -L --fail --retry 3   "https://raw.githubusercontent.com/znm2500/GameMaker-Mobiler/main/GMS2%20APK/$VER.apk"   -o test/runner.apk

unzip -l test/runner.apk > runner-list.txt
grep -E 'lib/(x86_64|x86|arm64-v8a)/libyoyo\.so' runner-list.txt | tee runner-abis.txt || true

cp test/runner.apk test/u.apk
zip -q -d test/u.apk 'META-INF/*' >/dev/null 2>&1 || true
cp "$GAME_DROID" test/assets/game.droid
(cd test && zip -q -0 -u u.apk assets/game.droid)

"$ZIPALIGN" -f -p 4 test/u.apk test/a.apk

keytool -genkeypair -v   -keystore test/debug.keystore   -storepass android -alias androiddebugkey -keypass android   -dname 'CN=Android Debug,O=Android,C=US'   -keyalg RSA -keysize 2048 -validity 10000 >/dev/null 2>&1

"$APKSIGNER" sign   --ks test/debug.keystore --ks-key-alias androiddebugkey   --ks-pass pass:android --key-pass pass:android   --out test/test.apk test/a.apk

"$AAPT" dump badging test/test.apk > badging.txt
PKG="$(sed -n "s/package: name='\([^']*\)'.*/\1/p" badging.txt | head -1)"
echo "$PKG" > package.txt

INSTALL="$(adb install --bypass-low-target-sdk-block test/test.apk 2>&1 || adb install test/test.apk 2>&1 || true)"
echo "$INSTALL" | tee install.txt
grep -q 'Success' install.txt

adb logcat -c
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 | tee monkey.txt || true
sleep 12

adb shell pidof "$PKG" > pid.txt 2>/dev/null || true
adb logcat -d -v threadtime > runtime.log || true
adb exec-out screencap -p > screen.png || true

echo "RUNNER=$VER" | tee result.txt
if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|Fatal signal|CObjectGM::LoadFromChunk' runtime.log >/dev/null; then
  echo "STATUS=CRASH" | tee -a result.txt
  grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|Fatal signal|CObjectGM::LoadFromChunk|LoadGameData' runtime.log | tail -40 | tee crash-summary.txt || true
  exit 1
fi

if [ ! -s pid.txt ]; then
  echo "STATUS=DEAD" | tee -a result.txt
  grep -E -i 'yoyo|runner|game\.droid|error|fatal|exception' runtime.log | tail -100 | tee runtime-summary.txt || true
  exit 1
fi

echo "STATUS=ALIVE" | tee -a result.txt
echo "PID=$(cat pid.txt)" | tee -a result.txt
echo "NATIVE_BOOTSTRAP_RUNNER_OK=$VER"
