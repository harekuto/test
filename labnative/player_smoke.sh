#!/usr/bin/env bash
set -euo pipefail
APK="$(find artifact -name '*.apk' -print -quit)"
PKG="$(cat artifact/package.txt)"
test -n "$APK"
test -n "$PKG"

adb install -r "$APK"
adb shell settings put secure immersive_mode_confirmations confirmed || true
adb shell settings put global hide_error_dialogs 1 || true
adb shell am force-stop com.google.android.apps.nexuslauncher || true
adb shell am force-stop com.android.launcher3 || true
adb shell input keyevent 4 || true
adb logcat -c

ACTIVITY="$(adb shell cmd package resolve-activity --brief "$PKG" | tail -1 | tr -d '\r')"
test -n "$ACTIVITY"
echo "$ACTIVITY" > resolved-activity.txt
adb shell am start -W -n "$ACTIVITY" > activity-start.txt
sleep 12

adb shell dumpsys window | grep -E 'mCurrentFocus|mFocusedApp' > focus-after-start.txt || true
if grep -Eqi 'AppNotResponding|Quickstep|launcher3|nexuslauncher|Application Error' focus-after-start.txt; then
  adb shell input keyevent 4 || true
  sleep 2
fi

adb shell pidof "$PKG" > player-pid.txt 2>/dev/null || true
adb exec-out screencap -p > player-start.png || true
adb logcat -d -v threadtime > player-log.txt || true

if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|Fatal signal|FATAL ERROR in|Memory allocation failed|CObjectGM::LoadFromChunk|ERROR in[[:space:]]+action number' player-log.txt; then
  grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|Fatal signal|FATAL ERROR in|Memory allocation failed|CObjectGM::LoadFromChunk|ERROR in[[:space:]]+action number|yoyo|game\.droid' player-log.txt | tail -350
  exit 1
fi
test -s player-pid.txt

python3 - <<'PY' > touch-map.txt
import struct
with open("player-start.png","rb") as f:
    f.seek(16)
    w,h=struct.unpack(">II",f.read(8))
scale=min(w/640.0,h/480.0)
ox=(w-640.0*scale)/2.0
oy=(h-480.0*scale)/2.0
points={
    "LEFT":(67,393),
    "RIGHT":(163,393),
    "JUMP":(573,383),
    "MELEE":(470,380),
    "GUN":(570,285),
    "RELOAD":(470,285),
    "GUARD":(372,380),
    "BACK":(67,295),
    "MENU":(274,41),
    "TAB":(362,41),
}
print(f"SCREEN={w}x{h}")
print(f"SCALE={scale:.6f}")
print(f"OFFSET={ox:.3f},{oy:.3f}")
for name,(gx,gy) in points.items():
    print(f"{name}={round(ox+gx*scale)},{round(oy+gy*scale)}")
PY
cat touch-map.txt

coord() {
  awk -F= -v k="$1" '$1==k{print $2}' touch-map.txt
}

RIGHT="$(coord RIGHT)"
JUMP="$(coord JUMP)"
MELEE="$(coord MELEE)"
GUN="$(coord GUN)"
RELOAD="$(coord RELOAD)"
GUARD="$(coord GUARD)"
BACK="$(coord BACK)"
MENU="$(coord MENU)"
TAB="$(coord TAB)"
RX="${RIGHT%,*}"; RY="${RIGHT#*,}"
JX="${JUMP%,*}"; JY="${JUMP#*,}"
MX="${MELEE%,*}"; MY="${MELEE#*,}"
GX="${GUN%,*}"; GY="${GUN#*,}"
WX="${RELOAD%,*}"; WY="${RELOAD#*,}"
QX="${GUARD%,*}"; QY="${GUARD#*,}"
BX="${BACK%,*}"; BY="${BACK#*,}"
UX="${MENU%,*}"; UY="${MENU#*,}"
TX="${TAB%,*}"; TY="${TAB#*,}"

START_SHA="$(sha256sum player-start.png | awk '{print $1}')"

adb shell input swipe "$RX" "$RY" "$RX" "$RY" 1400
sleep 1
adb exec-out screencap -p > player-after-right.png
RIGHT_SHA="$(sha256sum player-after-right.png | awk '{print $1}')"
if [ "$RIGHT_SHA" = "$START_SHA" ]; then
  echo "Right virtual key produced no visual change"
  exit 1
fi

adb shell input swipe "$JX" "$JY" "$JX" "$JY" 350
sleep 0.20
adb exec-out screencap -p > player-after-jump.png
sleep 1

for xy in "$MX,$MY" "$GX,$GY" "$WX,$WY" "$QX,$QY" "$BX,$BY" "$UX,$UY" "$TX,$TY"; do
  x="${xy%,*}"
  y="${xy#*,}"
  adb shell input swipe "$x" "$y" "$x" "$y" 260
  sleep 0.18
done

sleep 1
adb exec-out screencap -p > player-after-input.png

adb shell pidof "$PKG" > player-pid-after.txt 2>/dev/null || true
test -s player-pid-after.txt

adb logcat -d -v threadtime > player-final-log.txt || true
if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|Fatal signal|FATAL ERROR in|Memory allocation failed|CObjectGM::LoadFromChunk|ERROR in[[:space:]]+action number' player-final-log.txt; then
  cat player-final-log.txt
  exit 1
fi

grep -F 'LAB_INPUT_MV=1' player-final-log.txt > /dev/null || {
  echo "Native RIGHT movement marker missing"
  grep -E 'LAB_INPUT|LAB_JUMP|yoyo' player-final-log.txt | tail -200 || true
  exit 1
}
grep -F 'LAB_JUMP_TRIGGERED=' player-final-log.txt > /dev/null || {
  echo "Native JUMP marker missing"
  grep -E 'LAB_INPUT|LAB_JUMP|yoyo' player-final-log.txt | tail -200 || true
  exit 1
}

for marker in LAB_ACTION_MELEE=1 LAB_ACTION_GUN=1 LAB_ACTION_RELOAD=1 LAB_ACTION_GUARD=1 LAB_ACTION_BACK=1 LAB_ACTION_MENU=1 LAB_ACTION_TAB=1; do
  grep -F "$marker" player-final-log.txt > /dev/null || {
    echo "Native action marker missing: $marker"
    grep -a -E 'LAB_|yoyo|FATAL|SIG' player-final-log.txt | tail -260 || true
    exit 1
  }
done

echo "START_SHA=$START_SHA" > player-screen-hashes.txt
echo "RIGHT_SHA=$RIGHT_SHA" >> player-screen-hashes.txt
echo "JUMP_SHA=$(sha256sum player-after-jump.png | awk '{print $1}')" >> player-screen-hashes.txt
echo LAB_NATIVE_PLAYER_RUNTIME_OK
