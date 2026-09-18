from pathlib import Path
import os
import re
import sys
from PIL import Image

if len(sys.argv) != 2:
    raise SystemExit("usage: smg_patch_apk.py <decoded-apk-root>")

root = Path(sys.argv[1])
manifest = root / "AndroidManifest.xml"
if not manifest.exists():
    raise SystemExit("AndroidManifest.xml missing")

package_name = os.environ.get("PACKAGE_NAME", "com.harekuto.supermonstersgirls")
app_name = os.environ.get("APP_NAME", "Super Monsters'n Girls")
version_name = os.environ.get("VERSION_NAME", "2.0.2-android-v1")

s = manifest.read_text(encoding="utf-8")
m = re.search(r'\bpackage\s*=\s*["\']([^"\']+)["\']', s)
if not m:
    raise SystemExit("manifest package missing")
old = m.group(1)
new = package_name
print("old package", old, "new", new)

oldslash = old.replace(".", "/")
newslash = new.replace(".", "/")
for p in root.rglob("*"):
    if not p.is_file() or p.suffix.lower() not in {".xml", ".smali", ".yml", ".txt", ".properties"}:
        continue
    try:
        t = p.read_text(encoding="utf-8")
    except Exception:
        continue
    u = t.replace(old, new).replace(oldslash, newslash)
    if u != t:
        p.write_text(u, encoding="utf-8")

s = manifest.read_text(encoding="utf-8")
s = re.sub(
    r'(android:versionName\s*=\s*["\'])[^"\']*(["\'])',
    lambda m: m.group(1) + version_name + m.group(2),
    s,
)
if re.search(r'android:versionCode\s*=', s):
    s = re.sub(
        r'(android:versionCode\s*=\s*["\'])[^"\']*(["\'])',
        lambda m: m.group(1) + "1" + m.group(2),
        s,
    )
s = re.sub(
    r'android:screenOrientation\s*=\s*["\'][^"\']*["\']',
    'android:screenOrientation="sensorLandscape"',
    s,
)
if "android:largeHeap=" not in s:
    s = s.replace("<application ", '<application android:largeHeap="true" ', 1)
manifest.write_text(s, encoding="utf-8")

escaped_app_name = app_name.replace("'", "\\'")
for p in root.rglob("strings.xml"):
    try:
        t = p.read_text(encoding="utf-8")
    except Exception:
        continue
    if 'name="app_name"' not in t:
        continue
    t = re.sub(
        r'(<string[^>]+name="app_name"[^>]*>).*?(</string>)',
        lambda m: m.group(1) + escaped_app_name + m.group(2),
        t,
        flags=re.S,
    )
    p.write_text(t, encoding="utf-8")

icon_path = Path("work/game-icon.png")
if icon_path.exists():
    src = Image.open(icon_path).convert("RGBA")
    replaced = 0
    for p in root.rglob("*.png"):
        low = str(p).replace("\\", "/").lower()
        if "/mipmap" not in low or ("icon" not in p.stem.lower() and "launcher" not in p.stem.lower()):
            continue
        try:
            with Image.open(p) as oldimg:
                size = oldimg.size
            src.resize(size, Image.Resampling.LANCZOS).save(p)
            replaced += 1
        except Exception:
            pass
    print("launcher icons replaced", replaced)

print("APK metadata patch complete")
