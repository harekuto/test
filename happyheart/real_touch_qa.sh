#!/usr/bin/env bash
set -euo pipefail

TEST_PACKAGE="com.harekuto.happyheartpanic"
APK="$(find apk -type f -name '*.apk' -print -quit)"
test -n "$APK"

adb install -r "$APK"
adb shell settings put secure immersive_mode_confirmations confirmed || true
adb shell settings put policy_control immersive.full=* || true
adb logcat -c
adb shell monkey -p "$TEST_PACKAGE" -c android.intent.category.LAUNCHER 1
sleep 10

adb shell pidof "$TEST_PACKAGE" | tee pid-agreement.txt
test -s pid-agreement.txt
adb exec-out screencap -p > agreement.png

python3 - <<'PY' > touch-coordinates.txt
import struct
with open("agreement.png","rb") as f:
    f.seek(16)
    w,h=struct.unpack(">II",f.read(8))
scale=min(w/1280.0,h/800.0)
ox=(w-1280.0*scale)/2.0
oy=(h-800.0*scale)/2.0
buttons={
    "EOK":(870+115/2,615+72/2),
    "DASH":(900+115/2,700+62/2),
    "ITEM1":(900+86/2,530+54/2),
    "ITEM2":(995+86/2,505+54/2),
    "EXTRA":(1085+82/2,420+48/2),
    "RETRY":(1175+82/2,420+48/2),
    "BACK":(18+92/2,18+46/2),
}
print(f"SCREEN={w}x{h} SCALE={scale:.6f} OFFSET={ox:.2f},{oy:.2f}")
for name,(gx,gy) in buttons.items():
    sx=round(ox+gx*scale); sy=round(oy+gy*scale)
    print(f"{name}={sx},{sy}")
PY
cat touch-coordinates.txt

tap_button() {
  local name="$1"
  local xy
  xy="$(awk -F= -v n="$name" '$1==n{print $2}' touch-coordinates.txt)"
  test -n "$xy"
  local x="${xy%,*}"
  local y="${xy#*,}"
  adb shell input tap "$x" "$y"
}

sha(){ sha256sum "$1" | awk '{print $1}'; }

# Agreement -> menu via actual on-screen E/OK touch target.
tap_button EOK
sleep 12
adb shell pidof "$TEST_PACKAGE" | tee pid-menu.txt
test -s pid-menu.txt
adb exec-out screencap -p > menu.png
BASE_SHA="$(sha agreement.png)"
MENU_SHA="$(sha menu.png)"
printf 'AGREEMENT_SHA=%s\nMENU_SHA=%s\n' "$BASE_SHA" "$MENU_SHA" | tee screen-hashes.txt
test "$BASE_SHA" != "$MENU_SHA"

adb logcat -d -v threadtime > hhp-menu-log.txt
if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|FATAL ERROR in|Memory allocation failed|File is not opened for reading|ERROR in[[:space:]]+action number|ANR in com\.harekuto\.happyheartpanic' hhp-menu-log.txt; then
  cat hhp-menu-log.txt
  exit 1
fi

# Menu defaults to New Game; the same touch target emits E and Enter.
tap_button EOK
sleep 20
adb shell pidof "$TEST_PACKAGE" | tee pid-gameplay.txt
test -s pid-gameplay.txt
adb exec-out screencap -p > gameplay.png
GAME_SHA="$(sha gameplay.png)"
echo "GAMEPLAY_SHA=$GAME_SHA" | tee -a screen-hashes.txt
test "$GAME_SHA" != "$MENU_SHA"

adb logcat -d -v threadtime > hhp-final-log.txt
if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|FATAL ERROR in|Memory allocation failed|File is not opened for reading|ERROR in[[:space:]]+action number|ANR in com\.harekuto\.happyheartpanic' hhp-final-log.txt; then
  cat hhp-final-log.txt
  exit 1
fi

# Exercise a few real mobile controls during gameplay.
tap_button DASH
tap_button ITEM1
tap_button ITEM2
tap_button EXTRA
sleep 3
adb shell pidof "$TEST_PACKAGE" | tee pid-controls.txt
test -s pid-controls.txt
adb exec-out screencap -p > gameplay-after-controls.png

# Relaunch: accepted agreement must persist.
adb shell am force-stop "$TEST_PACKAGE"
adb shell monkey -p "$TEST_PACKAGE" -c android.intent.category.LAUNCHER 1
sleep 10
adb shell pidof "$TEST_PACKAGE" | tee pid-relaunch.txt
test -s pid-relaunch.txt
adb exec-out screencap -p > relaunch.png
RELAUNCH_SHA="$(sha relaunch.png)"
echo "RELAUNCH_SHA=$RELAUNCH_SHA" | tee -a screen-hashes.txt
test "$RELAUNCH_SHA" != "$BASE_SHA"

adb logcat -d -v threadtime > hhp-relaunch-log.txt
if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|FATAL ERROR in|Memory allocation failed|File is not opened for reading|ERROR in[[:space:]]+action number|ANR in com\.harekuto\.happyheartpanic' hhp-relaunch-log.txt; then
  cat hhp-relaunch-log.txt
  exit 1
fi

echo HHP_REAL_TOUCH_FLOW_OK
