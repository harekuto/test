from __future__ import annotations
import subprocess, sys, re, json, hashlib
from pathlib import Path

src=Path(sys.argv[1]); out=Path(sys.argv[2]); tmp=out/"tmp"
out.mkdir(parents=True,exist_ok=True); tmp.mkdir(parents=True,exist_ok=True)

# Extract only engine/input metadata, not 5,500 bundles.
patterns=[
    "*global-metadata.dat","*globalgamemanagers","*boot.config","*GameAssembly.dll",
    "*UnityPlayer.dll","*catalog*.json","*settings*.json","*link.xml",
    "*UnityServicesProjectConfiguration.json","*app.info","*ScriptingAssemblies.json"
]
cmd=["7z","x","-y",f"-o{tmp}",str(src)]+patterns
subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)

files=[p for p in tmp.rglob("*") if p.is_file()]
rep=[]
w=rep.append
for p in files:
    w(f"FILE {p.relative_to(tmp).as_posix()} SIZE={p.stat().st_size}")

# Strings helper.
def strings(path: Path, minlen=4):
    try:
        cp=subprocess.run(["strings","-a","-n",str(minlen),str(path)],check=True,capture_output=True,text=True,errors="ignore")
        return cp.stdout.splitlines()
    except Exception:
        return []

# Unity version candidates from globalgamemanagers / player DLL.
for p in files:
    if p.name in {"globalgamemanagers","UnityPlayer.dll","GameAssembly.dll"}:
        ss=strings(p,5)
        vers=[s for s in ss if re.search(r"20\d\d\.\d+\.\d+[a-z]\d+",s)]
        if vers:
            w(f"VERSION_STRINGS {p.name}: "+json.dumps(vers[:20]))

# boot.config
for p in files:
    if p.name=="boot.config":
        try:
            w("BOOT_CONFIG_BEGIN")
            for line in p.read_text(errors="ignore").splitlines(): w(line)
            w("BOOT_CONFIG_END")
        except: pass

# Input/action vocabulary from IL2CPP metadata and GameAssembly.
terms=[
 "InputAction","InputActionAsset","PlayerInput","InputSystem","Keyboard","Gamepad",
 "Move","Movement","Jump","Attack","LightAttack","HeavyAttack","Interact","Use","Submit","Cancel",
 "Inventory","Menu","Pause","Sprint","Run","Dash","Dodge","Skill","Ability","Spell","Map",
 "Camera","Look","Aim","Fire","Block","Guard","Heal","Item","Quest","Save","Load"
]
rx=re.compile("|".join(re.escape(x) for x in terms),re.I)
for p in files:
    if p.name in {"global-metadata.dat","GameAssembly.dll"}:
        ss=strings(p,4)
        hits=[]
        seen=set()
        for s in ss:
            if rx.search(s) and s not in seen:
                seen.add(s); hits.append(s)
                if len(hits)>=2000: break
        w(f"INPUT_STRINGS_BEGIN {p.name}")
        for s in hits: w(s[:1200])
        w(f"INPUT_STRINGS_END {p.name}")

# JSON metadata/catalogn search for actions, addresses, provider ids.
for p in files:
    if p.suffix.lower()==".json" and p.stat().st_size<50_000_000:
        try: txt=p.read_text(errors="ignore")
        except: continue
        w(f"JSON {p.relative_to(tmp).as_posix()} SIZE={len(txt)}")
        for term in ["Input","Control","Keyboard","Gamepad","Move","Attack","Interact","Submit","Cancel","UI","Player"]:
            if term.lower() in txt.lower():
                w(f"  CONTAINS {term}")
        # Keep small JSONs in report.
        if len(txt)<300_000:
            (out/(p.name+".txt")).write_text(txt,encoding="utf-8")

# PE architecture.
for p in files:
    if p.name.lower().endswith(".dll"):
        try:
            desc=subprocess.run(["file","-b",str(p)],capture_output=True,text=True).stdout.strip()
            w(f"PE {p.name}: {desc}")
        except: pass

(out/"unity-audit.txt").write_text("\n".join(rep),encoding="utf-8")
print("\n".join(rep))
# Don't upload tmp.
