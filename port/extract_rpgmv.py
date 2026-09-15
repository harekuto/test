from __future__ import annotations
import sys, zipfile, shutil
from pathlib import Path

if len(sys.argv) != 4:
    raise SystemExit('Usage: extract_rpgmv.py <zip> <extract_dir> <dest_webroot>')
src=Path(sys.argv[1]); out=Path(sys.argv[2]); dest=Path(sys.argv[3])
out.mkdir(parents=True,exist_ok=True)
base=out.resolve()
with zipfile.ZipFile(src) as z:
    for info in z.infolist():
        p=(out/info.filename).resolve()
        if p!=base and base not in p.parents:
            raise SystemExit('Unsafe ZIP path: '+info.filename)
    z.extractall(out)
candidates=[]
for idx in out.rglob('index.html'):
    root=idx.parent
    score=(100 if (root/'js/rpg_core.js').is_file() else 0)+(30 if (root/'data/System.json').is_file() else 0)
    candidates.append((score,-len(root.parts),root))
if not candidates:
    raise SystemExit('No index.html in supplied archive')
candidates.sort(reverse=True)
score,_,root=candidates[0]
if score<130:
    raise SystemExit(f'Best candidate is not a complete RPG Maker MV web root: {root}')
if dest.exists(): shutil.rmtree(dest)
dest.mkdir(parents=True,exist_ok=True)
for item in root.iterdir():
    target=dest/item.name
    if item.is_dir(): shutil.copytree(item,target)
    else: shutil.copy2(item,target)
print('RPG Maker MV web root:',root)
print('Copied to:',dest)
print('Files:',sum(1 for p in dest.rglob('*') if p.is_file()))
