from pathlib import Path
import os,re,sys
from PIL import Image

root=Path(sys.argv[1])
manifest=root/"AndroidManifest.xml"
if not manifest.exists(): raise SystemExit("manifest missing")

package=os.environ.get("HHP_PACKAGE","com.harekuto.happyheartpanic")
version=os.environ.get("HHP_VERSION","2025-android-v1")
vcode=os.environ.get("HHP_VCODE","100")
app="Happy Heart Panic"

s=manifest.read_text(encoding="utf-8")
m=re.search(r'\bpackage\s*=\s*["\']([^"\']+)["\']',s)
if not m: raise SystemExit("package missing")
old=m.group(1)
oldslash=old.replace(".","/")
newslash=package.replace(".","/")
for p in root.rglob("*"):
    if not p.is_file() or p.suffix.lower() not in {".xml",".smali",".yml",".txt",".properties"}: continue
    try:t=p.read_text(encoding="utf-8")
    except:continue
    u=t.replace(old,package).replace(oldslash,newslash)
    if u!=t:p.write_text(u,encoding="utf-8")

s=manifest.read_text(encoding="utf-8")
if re.search(r'android:versionCode\s*=',s):
    s=re.sub(r'(android:versionCode\s*=\s*["\'])[^"\']*(["\'])',lambda m:m.group(1)+vcode+m.group(2),s)
else:
    s=s.replace("<manifest ",f'<manifest android:versionCode="{vcode}" ',1)
if re.search(r'android:versionName\s*=',s):
    s=re.sub(r'(android:versionName\s*=\s*["\'])[^"\']*(["\'])',lambda m:m.group(1)+version+m.group(2),s)
else:
    s=s.replace("<manifest ",f'<manifest android:versionName="{version}" ',1)
if re.search(r'android:screenOrientation\s*=',s):
    s=re.sub(r'android:screenOrientation\s*=\s*["\'][^"\']*["\']','android:screenOrientation="sensorLandscape"',s)
if "android:largeHeap=" not in s:
    s=s.replace("<application ",'<application android:largeHeap="true" ',1)
if "android:hardwareAccelerated=" not in s:
    s=s.replace("<application ",'<application android:hardwareAccelerated="true" ',1)
manifest.write_text(s,encoding="utf-8")

yml=root/"apktool.yml"
if yml.exists():
    y=yml.read_text(encoding="utf-8")
    y=re.sub(r"(?m)^(\s*versionCode:\s*).*$",lambda m:m.group(1)+vcode,y)
    y=re.sub(r"(?m)^(\s*versionName:\s*).*$",lambda m:m.group(1)+"'"+version+"'",y)
    lines=y.splitlines()
    try: idx=next(i for i,l in enumerate(lines) if l.strip()=="doNotCompress:")
    except StopIteration:
        if lines and lines[-1].strip(): lines.append("")
        lines.extend(["doNotCompress:","- droid","- gif"])
    else:
        end=idx+1
        while end<len(lines) and (not lines[end].strip() or lines[end].strip().startswith("-")): end+=1
        current={l.strip()[1:].strip().strip("'\"") for l in lines[idx+1:end] if l.strip().startswith("-")}
        add=[f"- {x}" for x in ("droid","gif") if x not in current]
        lines[end:end]=add
    y="\n".join(lines)+("\n" if y.endswith("\n") else "")
    yml.write_text(y,encoding="utf-8")

escaped=app.replace("'","\\'")
for p in root.rglob("strings.xml"):
    try:t=p.read_text(encoding="utf-8")
    except:continue
    if 'name="app_name"' in t:
        t=re.sub(r'(<string[^>]+name="app_name"[^>]*>).*?(</string>)',lambda m:m.group(1)+escaped+m.group(2),t,flags=re.S)
        p.write_text(t,encoding="utf-8")

icon=Path("work/game-icon.png")
if icon.exists():
    src=Image.open(icon).convert("RGBA")
    for p in root.rglob("*.png"):
        low=str(p).replace("\\","/").lower()
        if "/mipmap" not in low or ("icon" not in p.stem.lower() and "launcher" not in p.stem.lower()): continue
        try:
            with Image.open(p) as oldim: size=oldim.size
            src.resize(size,Image.Resampling.LANCZOS).save(p)
        except: pass

print("APK metadata patched",old,"->",package)
