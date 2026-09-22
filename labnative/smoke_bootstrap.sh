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

adb shell pidof "$PKG" | tee smoke-pid.txt || true
adb exec-out screencap -p > bootstrap.png || true
adb logcat -d -v threadtime > smoke-log.txt || true
adb shell dumpsys activity activities > smoke-activity.txt || true

echo '--- GameMaker / Android runtime diagnostics ---'
grep -E -i 'yoyo|gamemaker|runner|fatal|exception|sigsegv|sigabrt|game\.droid|memory|error' smoke-log.txt | tail -300 || true

if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|FATAL ERROR in|Memory allocation failed' smoke-log.txt; then
  echo 'FATAL_RUNTIME_ERROR=1'
  exit 1
fi

if [ ! -s smoke-pid.txt ]; then
  echo 'GAME_PROCESS_NOT_ALIVE=1'
  exit 1
fi

echo LAB_NATIVE_BOOTSTRAP_SMOKE_OK
