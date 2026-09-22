#!/usr/bin/env bash
set -euo pipefail
APK="$(find artifact -name '*.apk' -print -quit)"
PKG="$(cat artifact/package.txt)"
test -s "$APK"
test -n "$PKG"

adb install --bypass-low-target-sdk-block -r "$APK" 2>&1 | tee install.txt || adb install -r "$APK" 2>&1 | tee -a install.txt
grep -q 'Success' install.txt
adb logcat -c
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 | tee monkey.txt || true
sleep 12

adb shell pidof "$PKG" | tee pid.txt || true
adb exec-out screencap -p > bootstrap.png || true
adb logcat -d -v threadtime > runtime.log || true

grep -E -i 'yoyo|gamemaker|runner|game\.droid|fatal|exception|sigsegv|error' runtime.log | tail -300 > runtime-summary.txt || true

if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|Fatal signal|CObjectGM::LoadFromChunk|AndroidRuntime.*FATAL|FATAL ERROR in|ERROR in[[:space:]]+action number|ShowMessage.*FATAL' runtime.log >/dev/null; then
  cat runtime-summary.txt
  exit 1
fi
test -s pid.txt
echo LAB_GMS23_NATIVE_BOOTSTRAP_OK
