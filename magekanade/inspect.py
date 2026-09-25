from __future__ import annotations
import sys, re, json, hashlib, subprocess
from pathlib import Path
from collections import Counter

src=Path(sys.argv[1]); out=Path(sys.argv[2]); ext=out/"extracted"
out.mkdir(parents=True,exist_ok=True); ext.mkdir(parents=True,exist_ok=True)
subprocess.run(["7z","x","-y",f"-o{ext}",str(src)],check=True,stdout=subprocess.DEVNULL)

files=[p for p in ext.rglob("*") if p.is_file()]
rels=[p.relative_to(ext).as_posix() for p in files]
rep=[]
w=rep.append
h=hashlib.sha256()
with src.open("rb") as f:
    for c in iter(lambda:f.read(8*1024*1024),b""): h.update(c)
w(f"SIZE={src.stat().st_size}")
w(f"SHA256={h.hexdigest()}")
w(f"FILES={len(files)}")
w("TOP_EXTENSIONS="+json.dumps(Counter(p.suffix.lower() for p in files).most_common(100),ensure_ascii=False))

engines={
"gamemaker":[r"(^|/)data\.win$",r"(^|/)audiogroup\d+\.dat$",r"(^|/)options\.ini$"],
"unity":[r"UnityPlayer\.dll$",r"_Data/Managed/Assembly-CSharp\.dll$",r"globalgamemanagers$",r"GameAssembly\.dll$"],
"godot":[r"project\.godot$",r"\.pck$"],
"rpgmaker_mv":[r"www/js/rpg_core\.js$",r"www/data/System\.json$",r"nw\.dll$"],
"rpgmaker_mz":[r"www/js/rmmz_core\.js$",r"www/data/System\.json$"],
"renpy":[r"(^|/)renpy/",r"\.rpa$",r"game/.*\.rpyc$"],
"unreal":[r"\.uproject$",r"Engine/Binaries/",r"\.pak$"],
"electron":[r"resources/app\.asar$",r"electron\.exe$"],
}
for name,pats in engines.items():
    hits=[r for r in rels if any(re.search(p,r,re.I) for p in pats)]
    if hits:
        w(f"ENGINE_{name}={len(hits)}")
        for x in hits[:120]: w("  "+x)

for p in files:
    if p.suffix.lower()==".exe": w(f"EXE {p.relative_to(ext).as_posix()} SIZE={p.stat().st_size}")
    if p.name.lower()=="data.win": w(f"DATA_WIN {p.relative_to(ext).as_posix()} SIZE={p.stat().st_size}")
    if re.fullmatch(r"audiogroup\d+\.dat",p.name,re.I): w(f"AUDIOGROUP {p.relative_to(ext).as_posix()} SIZE={p.stat().st_size}")

for p in files:
    if p.name.lower() in {"package.json","system.json","game.ini","options.ini","config.ini","project.godot","readme.txt","controls.txt"} and p.stat().st_size<4_000_000:
        w("CONTENT "+p.relative_to(ext).as_posix())
        try:
            for line in p.read_text(errors="ignore").splitlines()[:800]: w("  "+line[:1800])
        except: pass

terms=re.compile(r"\b(keyboard_check(?:_pressed|_released)?|gamepad_|vk_[a-z0-9_]+|ord\(|KeyCode|GetKey|GetButton|Input\.|keydown|keyup|keyCode|controls?|keybind|hotkey|resolution|display_set_gui_size|window_set_size|room_width|room_height)\b",re.I)
for p in files:
    if p.suffix.lower() in {".js",".json",".ini",".cfg",".txt",".xml",".cs",".gd",".lua",".py",".html",".css",".gml"} and p.stat().st_size<4_000_000:
        try: txt=p.read_text(errors="ignore")
        except: continue
        if terms.search(txt):
            ms=[]
            for i,line in enumerate(txt.splitlines(),1):
                if terms.search(line):
                    ms.append((i,line[:1200]))
                    if len(ms)>=120: break
            w("INPUTFILE "+p.relative_to(ext).as_posix())
            for i,line in ms: w(f"  {i}: {line}")

w("TREE_BEGIN")
for r in sorted(rels)[:2000]: w(r)
w("TREE_END")
(out/"inspection.txt").write_text("\n".join(rep),encoding="utf-8")
(out/"all_files.txt").write_text("\n".join(sorted(rels)),encoding="utf-8")
print("\n".join(rep[:3500]))
