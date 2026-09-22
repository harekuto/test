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
RX="\${RIGHT%,*}"; RY="\${RIGHT#*,}"
JX="\${JUMP%,*}"; JY="\${JUMP#*,}"

START_SHA="$(sha256sum player-start.png | awk '{print $1}')"

adb shell input swipe "$RX" "$RY" "$RX" "$RY" 1400
sleep 1
adb exec-out screencap -p > player-after-right.png
RIGHT_SHA="$(sha256sum player-after-right.png | awk '{print $1}')"
if [ "$RIGHT_SHA" = "$START_SHA" ]; then
  echo "Right virtual key produced no visual change"
  exit 1
fi

adb shell input tap "$JX" "$JY"
sleep 0.25
adb exec-out screencap -p > player-after-jump.png
sleep 2
adb exec-out screencap -p > player-after-input.png

adb shell pidof "$PKG" > player-pid-after.txt 2>/dev/null || true
test -s player-pid-after.txt

adb logcat -d -v threadtime > player-final-log.txt || true
if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|Fatal signal|FATAL ERROR in|Memory allocation failed|CObjectGM::LoadFromChunk|ERROR in[[:space:]]+action number' player-final-log.txt; then
  cat player-final-log.txt
  exit 1
fi

echo "START_SHA=$START_SHA" > player-screen-hashes.txt
echo "RIGHT_SHA=$RIGHT_SHA" >> player-screen-hashes.txt
echo "JUMP_SHA=$(sha256sum player-after-jump.png | awk '{print $1}')" >> player-screen-hashes.txt
echo LAB_NATIVE_PLAYER_RUNTIME_OK
