#!/usr/bin/env bash
set -u

GAME_DROID="artifact/game.droid"
test -s "$GAME_DROID"
mkdir -p matrix
BUILD_TOOLS="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BUILD_TOOLS/zipalign"
APKSIGNER="$BUILD_TOOLS/apksigner"
AAPT="$BUILD_TOOLS/aapt"

keytool -genkeypair -v   -keystore matrix/debug.keystore   -storepass android -alias androiddebugkey -keypass android   -dname 'CN=Android Debug,O=Android,C=US'   -keyalg RSA -keysize 2048 -validity 10000 >/dev/null 2>&1

VERSIONS=("2.0.6" "2.2.2" "2.3.0" "2.3.2" "2.3.7" "2022.3" "2022.12" "2023.6" "2024.14")
FOUND=""

for VER in "${VERSIONS[@]}"; do
  echo "===== TEST RUNNER $VER ====="
  SAFE="${VER//./_}"
  DIR="matrix/$SAFE"
  mkdir -p "$DIR/assets"

  URL="https://raw.githubusercontent.com/znm2500/GameMaker-Mobiler/main/GMS2%20APK/$VER.apk"
  if ! curl -L --fail --retry 2 "$URL" -o "$DIR/runner.apk"; then
    echo "$VER DOWNLOAD_FAIL" | tee -a matrix/results.txt
    continue
  fi

  cp "$DIR/runner.apk" "$DIR/u.apk"
  zip -q -d "$DIR/u.apk" 'META-INF/*' >/dev/null 2>&1 || true
  cp "$GAME_DROID" "$DIR/assets/game.droid"
  (
    cd "$DIR"
    zip -q -0 -u u.apk assets/game.droid
  )

  if ! "$ZIPALIGN" -f -p 4 "$DIR/u.apk" "$DIR/a.apk"; then
    echo "$VER ZIPALIGN_FAIL" | tee -a matrix/results.txt
    continue
  fi
  if ! "$APKSIGNER" sign       --ks matrix/debug.keystore       --ks-key-alias androiddebugkey       --ks-pass pass:android --key-pass pass:android       --out "$DIR/test.apk" "$DIR/a.apk"; then
    echo "$VER SIGN_FAIL" | tee -a matrix/results.txt
    continue
  fi

  "$AAPT" dump badging "$DIR/test.apk" > "$DIR/badging.txt" || true
  PKG="$(sed -n "s/package: name='\([^']*\)'.*/\1/p" "$DIR/badging.txt" | head -1)"
  if [ -z "$PKG" ]; then
    echo "$VER PACKAGE_FAIL" | tee -a matrix/results.txt
    continue
  fi

  adb uninstall "$PKG" >/dev/null 2>&1 || true
  INSTALL_OUT="$(adb install --bypass-low-target-sdk-block "$DIR/test.apk" 2>&1 || adb install "$DIR/test.apk" 2>&1 || true)"
  echo "$INSTALL_OUT" > "$DIR/install.txt"
  if ! grep -q "Success" "$DIR/install.txt"; then
    echo "$VER INSTALL_FAIL" | tee -a matrix/results.txt
    continue
  fi

  adb logcat -c
  adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 > "$DIR/monkey.txt" 2>&1 || true
  sleep 9
  adb shell pidof "$PKG" > "$DIR/pid.txt" 2>/dev/null || true
  adb logcat -d -v threadtime > "$DIR/log.txt" || true
  adb exec-out screencap -p > "$DIR/screen.png" 2>/dev/null || true

  if grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|AndroidRuntime.*FATAL|Fatal signal|CObjectGM::LoadFromChunk' "$DIR/log.txt" >/dev/null; then
    echo "$VER CRASH" | tee -a matrix/results.txt
    grep -E -i 'FATAL EXCEPTION|SIGSEGV|SIGABRT|Fatal signal|CObjectGM::LoadFromChunk|LoadGameData' "$DIR/log.txt" | tail -30 > "$DIR/crash-summary.txt" || true
    adb shell am force-stop "$PKG" || true
    continue
  fi

  if [ -s "$DIR/pid.txt" ]; then
    echo "$VER ALIVE package=$PKG pid=$(cat "$DIR/pid.txt")" | tee -a matrix/results.txt
    FOUND="$VER"
    cp "$DIR/test.apk" matrix/LAB-Native-Working-Runner.apk
    cp "$DIR/screen.png" matrix/working-screen.png || true
    cp "$DIR/log.txt" matrix/working-log.txt
    echo "$VER" > matrix/working-runner.txt
    break
  else
    echo "$VER DEAD_NO_FATAL_MATCH" | tee -a matrix/results.txt
  fi
done

echo "===== MATRIX RESULTS ====="
cat matrix/results.txt
if [ -z "$FOUND" ]; then
  echo "NO_WORKING_RUNNER"
  exit 1
fi
echo "WORKING_RUNNER=$FOUND"
