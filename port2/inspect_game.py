from __future__ import annotations
import os, sys, json, zipfile, tarfile, subprocess, shutil, re, hashlib
from pathlib import Path
src=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
report=[]
def w(s=""): report.append(str(s))
w(f"input={src}")
w(f"size={src.stat().st_size}")
w(f"sha256={hashlib.sha256(src.read_bytes()).hexdigest() if src.stat().st_size < 50_000_000 else 'skipped-large'}")
# identify
try:
    ft=subprocess.check_output(["file","-b",str(src)],text=True).strip()
except Exception as e: ft=repr(e)
w(f"file_type={ft}")
extract=out/"extracted"; extract.mkdir(exist_ok=True)
ok=False
if zipfile.is_zipfile(src):
    with zipfile.ZipFile(src) as z: z.extractall(extract)
    ok=True; w("archive=zip")
else:
    # try 7z
    try:
        subprocess.check_call(["7z","x","-y",f"-o{extract}",str(src)],stdout=subprocess.DEVNULL)
        ok=True; w("archive=7z-compatible")
    except Exception as e: w(f"extract_error={e!r}")
if not ok: raise SystemExit("Could not extract archive")
files=[p for p in extract.rglob("*") if p.is_file()]
w(f"files={len(files)}")
w(f"dirs={sum(1 for p in extract.rglob('*') if p.is_dir())}")
from collections import Counter
ext=Counter(p.suffix.lower() for p in files)
w("top_extensions="+json.dumps(ext.most_common(60),ensure_ascii=False))
# engine signatures
checks={
"unity":[r"UnityPlayer\.dll$", r"_Data/Managed/Assembly-CSharp\.dll$", r"globalgamemanagers$"],
"unreal":[r"\.uproject$", r"Engine/Binaries/", r"\.pak$"],
"godot":[r"project\.godot$", r"\.pck$"],
"rpgmaker_mv":[r"www/js/rpg_core\.js$", r"www/data/System\.json$", r"nw\.dll$"],
"rpgmaker_mz":[r"www/js/rmmz_core\.js$", r"www/data/System\.json$"],
"renpy":[r"renpy/", r"\.rpa$", r"game/script.*\.rpyc$"],
"gamemaker":[r"data\.win$", r"options\.ini$"],
"electron":[r"resources/app\.asar$", r"electron\.exe$"],
"nwjs":[r"nw\.dll$", r"package\.json$"],
"java":[r"\.jar$"],
}
rels=[p.relative_to(extract).as_posix() for p in files]
for eng,pats in checks.items():
    hits=[r for r in rels if any(re.search(pat,r,re.I) for pat in pats)]
    if hits:
        w(f"ENGINE_{eng}={len(hits)}")
        for h in hits[:25]: w("  "+h)
# project/build markers
markers=["package.json","project.godot","*.uproject","*.sln","*.csproj","*.vcxproj","build.gradle","gradlew","CMakeLists.txt","GameAssembly.dll","UnityPlayer.dll","Assembly-CSharp.dll","data.win"]
for m in markers:
    hit=list(extract.rglob(m))
    for p in hit[:20]: w("MARKER "+p.relative_to(extract).as_posix())
# likely executable roots
for p in files:
    if p.suffix.lower()==".exe":
        w("EXE "+p.relative_to(extract).as_posix()+f" size={p.stat().st_size}")
# text/input audit on likely text files, cap
key_terms=re.compile(r"\b(KeyCode|Input\.|Input\.is|Keyboard|Mouse|Gamepad|GetKey|GetButton|keyCode|keydown|keyup|Input\.keyMapper|Input\.gamepadMapper|controls?|keybind|hotkey)\b",re.I)
interesting=[]
for p in files:
    if p.suffix.lower() in {".js",".json",".ini",".cfg",".txt",".xml",".cs",".gd",".lua",".py",".html",".css",".yaml",".yml"} and p.stat().st_size < 3_000_000:
        try: s=p.read_text(errors="ignore")
        except: continue
        if key_terms.search(s):
            matches=[]
            for i,line in enumerate(s.splitlines(),1):
                if key_terms.search(line):
                    matches.append((i,line[:500]))
                    if len(matches)>=80: break
            interesting.append((p.relative_to(extract).as_posix(),matches))
for fn,matches in interesting[:80]:
    w("INPUTFILE "+fn)
    for i,line in matches: w(f"  {i}: {line}")
# dimensions/UI-ish metadata
for p in files:
    if p.name.lower() in {"package.json","system.json","game.ini","options.ini","config.ini"} and p.stat().st_size<2_000_000:
        try:
            w("CONTENT "+p.relative_to(extract).as_posix())
            for line in p.read_text(errors="ignore").splitlines()[:250]: w("  "+line[:1000])
        except: pass
# top 400 tree entries
w("TREE_BEGIN")
for r in sorted(rels)[:400]: w(r)
w("TREE_END")
(out/"inspection.txt").write_text("\n".join(report),encoding="utf-8")
# also save concise file list
(out/"all_files.txt").write_text("\n".join(sorted(rels)),encoding="utf-8")
print("\n".join(report[:2000]))
