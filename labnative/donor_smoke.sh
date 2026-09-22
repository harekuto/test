#!/usr/bin/env bash
set -euo pipefail
APK="$(find artifact -name '*.apk' -print -quit)"
PKG="$(cat artifact/package.txt)"
test -n "$APK"
test -n "$PKG"

adb install -r "$APK"
adb logcat -c
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null
sleep 12

adb shell pidof "$PKG" > donor-smoke-pid.txt 2>/dev/null || true
adb exec-out screencap -p > donor-bootstrap.png || true
adb logcat -d -v threadtime > donor-smoke-log.txt || true

if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|Fatal signal|FATAL ERROR in|Memory allocation failed|CObjectGM::LoadFromChunk' donor-smoke-log.txt; then
  grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|Fatal signal|FATAL ERROR in|Memory allocation failed|CObjectGM::LoadFromChunk|yoyo|game\.droid' donor-smoke-log.txt | tail -300
  exit 1
fi

if [ ! -s donor-smoke-pid.txt ]; then
  echo "LAB_DONOR_BOOTSTRAP_PROCESS_DEAD"
  grep -E -i 'yoyo|gamemaker|runner|fatal|exception|sigsegv|sigabrt|game\.droid|error' donor-smoke-log.txt | tail -300 || true
  exit 1
fi

adb shell input tap 1200 700
sleep 2
adb exec-out screencap -p > donor-touch.png || true
echo LAB_DONOR_BOOTSTRAP_RUNTIME_OK
