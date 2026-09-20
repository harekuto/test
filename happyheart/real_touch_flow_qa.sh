#!/usr/bin/env bash
set -euo pipefail

TEST_PACKAGE="com.harekuto.happyheartpanic"
APK="$(find apk -type f -name '*.apk' -print -quit)"
if [[ -z "$APK" ]]; then
  echo "APK not found" >&2
  exit 1
fi

adb install -r "$APK"
adb shell settings put secure immersive_mode_confirmations confirmed || true
adb shell settings put policy_control immersive.full=* || true
adb logcat -c
adb shell monkey -p "$TEST_PACKAGE" -c android.intent.category.LAUNCHER 1
sleep 10
adb shell pidof "$TEST_PACKAGE" | tee pid-agreement.txt
test -s pid-agreement.txt
adb exec-out screencap -p > agreement.png

read TAP_X TAP_Y < <(python3 - <<'PY'
import struct
with open("agreement.png","rb") as f:
    f.seek(16)
    w,h=struct.unpack(">II",f.read(8))
scale=min(w/1280.0,h/800.0)
ox=(w-1280.0*scale)/2.0
oy=(h-800.0*scale)/2.0
x=round(ox+(870+115/2)*scale)
y=round(oy+(615+72/2)*scale)
print(x,y)
PY
)
echo "SCREEN_TAP_EOK=$TAP_X,$TAP_Y" | tee touch-coordinates.txt

BASE_SHA="$(sha256sum agreement.png | awk '{print $1}')"
MENU_SHA="$BASE_SHA"
for delta in "0 0" "70 0" "-70 0" "0 45" "0 -45"; do
  dx="${delta% *}"
  dy="${delta#* }"
  x=$((TAP_X + dx))
  y=$((TAP_Y + dy))
  echo "tap agreement candidate $x,$y"
  adb shell input tap "$x" "$y"
  sleep 4
  adb exec-out screencap -p > menu-probe.png
  MENU_SHA="$(sha256sum menu-probe.png | awk '{print $1}')"
  if [[ "$MENU_SHA" != "$BASE_SHA" ]]; then
    cp menu-probe.png menu.png
    break
  fi
done
if [[ "$MENU_SHA" == "$BASE_SHA" ]]; then
  echo "Agreement screen did not advance after virtual E/OK taps" >&2
  exit 1
fi

sleep 8
adb shell pidof "$TEST_PACKAGE" | tee pid-menu.txt
test -s pid-menu.txt
adb exec-out screencap -p > menu.png
MENU_SHA="$(sha256sum menu.png | awk '{print $1}')"
echo "AGREEMENT_SHA=$BASE_SHA" | tee screen-hashes.txt
echo "MENU_SHA=$MENU_SHA" | tee -a screen-hashes.txt
test "$BASE_SHA" != "$MENU_SHA"

adb shell input tap "$TAP_X" "$TAP_Y"
sleep 20
adb shell pidof "$TEST_PACKAGE" | tee pid-gameplay.txt
test -s pid-gameplay.txt
adb exec-out screencap -p > gameplay.png
GAME_SHA="$(sha256sum gameplay.png | awk '{print $1}')"
echo "GAMEPLAY_SHA=$GAME_SHA" | tee -a screen-hashes.txt
if [[ "$GAME_SHA" == "$MENU_SHA" ]]; then
  echo "New Game screen did not advance" >&2
  exit 1
fi

adb logcat -d -v threadtime > runtime.log
if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|FATAL ERROR in|Memory allocation failed|File is not opened for reading|ERROR in[[:space:]]+action number|ANR in com\.harekuto\.happyheartpanic' runtime.log; then
  cat runtime.log
  exit 1
fi

adb shell am force-stop "$TEST_PACKAGE"
adb shell monkey -p "$TEST_PACKAGE" -c android.intent.category.LAUNCHER 1
sleep 10
adb shell pidof "$TEST_PACKAGE" | tee pid-relaunch.txt
test -s pid-relaunch.txt
adb exec-out screencap -p > relaunch.png
RELAUNCH_SHA="$(sha256sum relaunch.png | awk '{print $1}')"
echo "RELAUNCH_SHA=$RELAUNCH_SHA" | tee -a screen-hashes.txt
if [[ "$RELAUNCH_SHA" == "$BASE_SHA" ]]; then
  echo "Agreement acceptance did not persist across relaunch" >&2
  exit 1
fi
adb logcat -d -v threadtime > relaunch.log
if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|FATAL ERROR in|Memory allocation failed|File is not opened for reading|ERROR in[[:space:]]+action number' relaunch.log; then
  cat relaunch.log
  exit 1
fi

echo HHP_REAL_TOUCH_FLOW_OK
