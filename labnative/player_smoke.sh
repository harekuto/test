#!/usr/bin/env bash
set -euo pipefail
APK="$(find artifact -name '*.apk' -print -quit)"
PKG="$(cat artifact/package.txt)"
test -n "$APK"
test -n "$PKG"

adb install -r "$APK"
adb shell settings put secure immersive_mode_confirmations confirmed || true
adb logcat -c
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null
sleep 12

adb shell pidof "$PKG" > player-pid.txt 2>/dev/null || true
adb exec-out screencap -p > player-start.png || true
adb logcat -d -v threadtime > player-log.txt || true

if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|Fatal signal|FATAL ERROR in|Memory allocation failed|CObjectGM::LoadFromChunk|ERROR in[[:space:]]+action number' player-log.txt; then
  grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|Fatal signal|FATAL ERROR in|Memory allocation failed|CObjectGM::LoadFromChunk|ERROR in[[:space:]]+action number|yoyo|game\.droid' player-log.txt | tail -350
  exit 1
fi
test -s player-pid.txt

# Exercise right movement and jump through actual touch locations after 640x480 -> landscape scaling.
adb shell input tap 1450 930 || true
sleep 2
adb shell input tap 2150 900 || true
sleep 2
adb exec-out screencap -p > player-after-input.png || true
adb shell pidof "$PKG" > player-pid-after.txt 2>/dev/null || true
test -s player-pid-after.txt

echo LAB_NATIVE_PLAYER_RUNTIME_OK
