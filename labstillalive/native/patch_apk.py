from pathlib import Path
import os,re,sys

root=Path(sys.argv[1])
manifest=root/"AndroidManifest.xml"
package=os.environ.get("LAB_PACKAGE","com.harekuto.labstillalive")
version=os.environ.get("LAB_VERSION","1.25-native-bootstrap1")
vcode=os.environ.get("LAB_VCODE","1001")
app="LAB Still Alive Native"

s=manifest.read_text(encoding="utf-8")
m=re.search(r'\bpackage\s*=\s*["\']([^"\']+)["\']',s)
if not m:
    raise SystemExit("package missing")
old=m.group(1)
oldslash=old.replace(".","/")
newslash=package.replace(".","/")

for p in root.rglob("*"):
    if not p.is_file() or p.suffix.lower() not in {".xml",".smali",".yml",".txt",".properties"}:
        continue
    try:
        t=p.read_text(encoding="utf-8")
    except Exception:
        continue
    u=t.replace(old,package).replace(oldslash,newslash)
    if u!=t:
        p.write_text(u,encoding="utf-8")

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
    try:
        idx=next(i for i,l in enumerate(lines) if l.strip()=="doNotCompress:")
    except StopIteration:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(["doNotCompress:","- droid"])
    else:
        end=idx+1
        while end<len(lines) and (not lines[end].strip() or lines[end].strip().startswith("-")):
            end+=1
        current={l.strip()[1:].strip().strip("'\"") for l in lines[idx+1:end] if l.strip().startswith("-")}
        if "droid" not in current:
            lines[end:end]=["- droid"]
    y="\n".join(lines)+("\n" if y.endswith("\n") else "")
    yml.write_text(y,encoding="utf-8")

for p in root.rglob("strings.xml"):
    try:
        t=p.read_text(encoding="utf-8")
    except Exception:
        continue
    if 'name="app_name"' in t:
        t=re.sub(r'(<string[^>]+name="app_name"[^>]*>).*?(</string>)',lambda m:m.group(1)+app+m.group(2),t,flags=re.S)
        p.write_text(t,encoding="utf-8")

print("PATCHED_PACKAGE",old,"->",package)
