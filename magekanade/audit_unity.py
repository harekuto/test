from __future__ import annotations
import subprocess, sys, re, json
from pathlib import Path

src=Path(sys.argv[1]); out=Path(sys.argv[2])
out.mkdir(parents=True,exist_ok=True)

# List archive and locate exact Unity metadata paths.
cp=subprocess.run(["7z","l","-ba",str(src)],check=True,capture_output=True,text=True,errors="ignore")
paths=[]
for line in cp.stdout.splitlines():
    # 7z -ba: date time attr size compressed path
    parts=line.split(None,5)
    if len(parts)==6:
        paths.append(parts[5])
wanted_names={"global-metadata.dat","globalgamemanagers","boot.config","GameAssembly.dll","ScriptingAssemblies.json"}
found={}
for p in paths:
    name=Path(p).name
    if name in wanted_names:
        found[name]=p
rep=[]
w=rep.append
for k,v in sorted(found.items()): w(f"FOUND {k}={v}")

def extract_one(name):
    path=found.get(name)
    if not path: return None
    dst=out/name
    with dst.open("wb") as fh:
        proc=subprocess.run(["7z","e","-so",str(src),path],stdout=fh,stderr=subprocess.PIPE)
    if proc.returncode!=0:
        w(f"EXTRACT_FAIL {name}: {proc.stderr.decode(errors='ignore')[:500]}")
        return None
    w(f"EXTRACTED {name} SIZE={dst.stat().st_size}")
    return dst

files={n:extract_one(n) for n in wanted_names}

def strings(path,minlen=4):
    if not path or not path.exists(): return []
    cp=subprocess.run(["strings","-a","-n",str(minlen),str(path)],capture_output=True,text=True,errors="ignore")
    return cp.stdout.splitlines()

# Unity version.
for name in ["globalgamemanagers","GameAssembly.dll"]:
    ss=strings(files.get(name),5)
    vers=[]
    for s in ss:
        if re.search(r"20\d\d\.\d+\.\d+[a-z]\d+",s):
            if s not in vers: vers.append(s)
    w(f"VERSION {name}: "+json.dumps(vers[:50]))

# Input/action strings from IL2CPP metadata.
terms=["InputAction","InputActionAsset","PlayerInput","InputSystem","Keyboard","Gamepad",
"Move","Movement","Jump","Attack","Interact","Submit","Cancel","Inventory","Menu","Pause",
"Sprint","Run","Dash","Dodge","Skill","Ability","Spell","Map","Camera","Look","Aim","Fire",
"Block","Guard","Heal","Item","Quest","Save","Load","Mouse","LeftClick","RightClick"]
rx=re.compile("|".join(re.escape(t) for t in terms),re.I)
for name in ["global-metadata.dat","GameAssembly.dll"]:
    hits=[]; seen=set()
    for s in strings(files.get(name),4):
        if rx.search(s) and s not in seen:
            seen.add(s); hits.append(s)
            if len(hits)>=2500: break
    w(f"INPUT_BEGIN {name}")
    for s in hits: w(s[:1600])
    w(f"INPUT_END {name}")

# boot.config + assemblies.
for name in ["boot.config","ScriptingAssemblies.json"]:
    p=files.get(name)
    if p and p.exists():
        try:
            txt=p.read_text(errors="ignore")
            w(f"TEXT_BEGIN {name}")
            for line in txt.splitlines()[:1000]: w(line[:2000])
            w(f"TEXT_END {name}")
        except: pass

(out/"unity-audit.txt").write_text("\n".join(rep),encoding="utf-8")
# Remove bulky extracted binaries; artifact must stay tiny.
for p in files.values():
    if p and p.exists(): p.unlink()
print("\n".join(rep))
