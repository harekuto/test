from __future__ import annotations
import os, sys, json, re, hashlib, subprocess
from pathlib import Path
from collections import Counter

src=Path(sys.argv[1])
out=Path(sys.argv[2])
extract=out/"extracted"
out.mkdir(parents=True,exist_ok=True)
extract.mkdir(parents=True,exist_ok=True)

def run(*args):
    return subprocess.run(args,check=True,text=True,capture_output=True)

report=[]
def w(x=""): report.append(str(x))

w(f"INPUT={src.name}")
w(f"SIZE={src.stat().st_size}")
h=hashlib.sha256()
with src.open("rb") as f:
    for chunk in iter(lambda:f.read(8*1024*1024),b""): h.update(chunk)
w(f"SHA256={h.hexdigest()}")

subprocess.run(["7z","x","-y",f"-o{extract}",str(src)],check=True)
files=[p for p in extract.rglob("*") if p.is_file()]
rels=[p.relative_to(extract).as_posix() for p in files]
w(f"FILES={len(files)}")
w(f"DIRS={sum(1 for p in extract.rglob('*') if p.is_dir())}")
w("TOP_EXTENSIONS="+json.dumps(Counter(p.suffix.lower() for p in files).most_common(80),ensure_ascii=False))

patterns={
"unity":[r"UnityPlayer\.dll$",r"_Data/Managed/Assembly-CSharp\.dll$",r"globalgamemanagers$",r"GameAssembly\.dll$"],
"unreal":[r"\.uproject$",r"Engine/Binaries/",r"\.pak$"],
"godot":[r"project\.godot$",r"\.pck$"],
"rpgmaker_mv":[r"www/js/rpg_core\.js$",r"www/data/System\.json$",r"nw\.dll$"],
"rpgmaker_mz":[r"www/js/rmmz_core\.js$",r"www/data/System\.json$"],
"renpy":[r"(^|/)renpy/",r"\.rpa$",r"game/.*\.rpyc$"],
"gamemaker":[r"(^|/)data\.win$",r"(^|/)options\.ini$",r"(^|/)audiogroup\d+\.dat$"],
"electron":[r"resources/app\.asar$",r"electron\.exe$"],
"nwjs":[r"nw\.dll$",r"package\.json$"],
"java":[r"\.jar$"],
}
for eng,pats in patterns.items():
    hits=[r for r in rels if any(re.search(p,r,re.I) for p in pats)]
    if hits:
        w(f"ENGINE_{eng}={len(hits)}")
        for x in hits[:80]: w("  "+x)

for p in files:
    if p.suffix.lower()==".exe":
        w(f"EXE {p.relative_to(extract).as_posix()} SIZE={p.stat().st_size}")

# marker content
for p in files:
    low=p.name.lower()
    if low in {"package.json","system.json","game.ini","options.ini","config.ini","project.godot"} and p.stat().st_size<3_000_000:
        w("CONTENT "+p.relative_to(extract).as_posix())
        try:
            for line in p.read_text(errors="ignore").splitlines()[:500]: w("  "+line[:1500])
        except Exception as e: w("  READ_ERROR "+repr(e))

# GameMaker-specific quick fingerprints
for p in files:
    if p.name.lower()=="data.win":
        w(f"GAMEMAKER_DATA={p.relative_to(extract).as_posix()} SIZE={p.stat().st_size}")
    if re.fullmatch(r"audiogroup\d+\.dat",p.name,re.I):
        w(f"AUDIOGROUP={p.relative_to(extract).as_posix()} SIZE={p.stat().st_size}")

terms=re.compile(r"\b(keyboard_check(?:_pressed|_released)?|gamepad_|vk_[a-z0-9_]+|ord\(|KeyCode|GetKey|GetButton|Input\.|keydown|keyup|keyCode|controls?|keybind|hotkey|resolution|display_set_gui_size|window_set_size|room_width|room_height)\b",re.I)
interesting=[]
for p in files:
    if p.suffix.lower() in {".js",".json",".ini",".cfg",".txt",".xml",".cs",".gd",".lua",".py",".html",".css",".gml"} and p.stat().st_size<4_000_000:
        try: txt=p.read_text(errors="ignore")
        except: continue
        if terms.search(txt):
            mm=[]
            for i,line in enumerate(txt.splitlines(),1):
                if terms.search(line):
                    mm.append((i,line[:1000]))
                    if len(mm)>=120: break
            interesting.append((p.relative_to(extract).as_posix(),mm))
for fn,mm in interesting[:120]:
    w("INPUTFILE "+fn)
    for i,line in mm: w(f"  {i}: {line}")

# save likely engine metadata for follow-up
copy_names={"data.win","options.ini","package.json","project.godot","Game.ini","System.json","rpg_core.js","rmmz_core.js"}
meta=out/"metadata"; meta.mkdir(exist_ok=True)
for p in files:
    if p.name in copy_names and p.stat().st_size<25_000_000:
        safe=p.relative_to(extract).as_posix().replace("/","__")
        try: (meta/safe).write_bytes(p.read_bytes())
        except: pass

w("TREE_BEGIN")
for r in sorted(rels)[:1200]: w(r)
w("TREE_END")

(out/"inspection.txt").write_text("\n".join(report),encoding="utf-8")
(out/"all_files.txt").write_text("\n".join(sorted(rels)),encoding="utf-8")
print("\n".join(report[:2500]))
