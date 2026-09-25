from __future__ import annotations
import sys, json, re
from pathlib import Path
import UnityPy

root=Path(sys.argv[1])
out=Path(sys.argv[2])
out.mkdir(parents=True,exist_ok=True)
report=[]

def emit(s=""):
    report.append(str(s))
    print(s)

ggm=next(root.rglob("globalgamemanagers"),None)
if not ggm:
    raise SystemExit("globalgamemanagers not found")
emit(f"GLOBALGAMEMANAGERS={ggm}")
emit(f"SIZE={ggm.stat().st_size}")

env=UnityPy.load(str(ggm))
emit(f"UNITY_VERSION={getattr(env,'unity_version',None)}")

types={}
for obj in env.objects:
    t=obj.type.name
    types[t]=types.get(t,0)+1
emit("OBJECT_TYPES="+json.dumps(types,sort_keys=True))

wanted={"InputManager","PlayerSettings","BuildSettings","QualitySettings","Physics2DSettings","TimeManager","AudioManager","GraphicsSettings"}
dumps={}
for obj in env.objects:
    if obj.type.name not in wanted:
        continue
    emit(f"OBJECT {obj.type.name} path_id={obj.path_id}")
    data=None
    try:
        data=obj.read_typetree()
    except Exception as e:
        emit(f"  typetree failed: {type(e).__name__}: {e}")
        try:
            data=obj.read()
        except Exception as e2:
            emit(f"  read failed: {type(e2).__name__}: {e2}")
    if isinstance(data,dict):
        dumps.setdefault(obj.type.name,[]).append(data)
        if obj.type.name=="InputManager":
            axes=data.get("m_Axes",[])
            emit(f"  AXES={len(axes)}")
            for i,a in enumerate(axes):
                if not isinstance(a,dict): continue
                fields={k:a.get(k) for k in [
                    "m_Name","descriptiveName","descriptiveNegativeName","negativeButton","positiveButton",
                    "altNegativeButton","altPositiveButton","gravity","dead","sensitivity","snap","invert","type","axis","joyNum"
                ] if k in a}
                emit("  AXIS "+str(i)+" "+json.dumps(fields,ensure_ascii=False,sort_keys=True))
        elif obj.type.name=="PlayerSettings":
            keys=[
                "productName","companyName","bundleVersion","defaultScreenWidth","defaultScreenHeight",
                "defaultScreenWidthWeb","defaultScreenHeightWeb","fullscreenMode","resizableWindow",
                "runInBackground","usePlayerLog","scriptingBackend","applicationIdentifier",
                "activeInputHandler","m_ActiveInputHandler"
            ]
            emit("  PLAYER "+json.dumps({k:data.get(k) for k in keys if k in data},ensure_ascii=False,sort_keys=True))
        elif obj.type.name=="BuildSettings":
            keys=["scenes","m_Scenes","buildGUID","hasPROVersion","isNoWatermarkBuild","isEducationalBuild","isDebugBuild","usesOnMouseEvents"]
            emit("  BUILD "+json.dumps({k:data.get(k) for k in keys if k in data},ensure_ascii=False,default=str))
    else:
        emit(f"  DATA_TYPE={type(data).__name__}")

(out/"unitypy-settings.json").write_text(json.dumps(dumps,ensure_ascii=False,indent=2,default=str),encoding="utf-8")
(out/"unitypy-report.txt").write_text("\n".join(report)+"\n",encoding="utf-8")
