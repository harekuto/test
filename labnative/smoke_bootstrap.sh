#!/usr/bin/env bash
set -euo pipefail
APK="$(find artifact -name '*.apk' -print -quit)"
PKG="$(cat artifact/package.txt)"
test -n "$APK"
test -n "$PKG"

adb install -r "$APK"
adb logcat -c
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1
sleep 12
adb shell pidof "$PKG" | tee smoke-pid.txt
test -s smoke-pid.txt
adb exec-out screencap -p > bootstrap.png
adb logcat -d -v threadtime > smoke-log.txt

if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|FATAL ERROR in|Memory allocation failed' smoke-log.txt; then
  cat smoke-log.txt
  exit 1
fi

echo LAB_NATIVE_BOOTSTRAP_SMOKE_OK
