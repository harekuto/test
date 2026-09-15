from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path


def write_report(report: Path, name: str, text: str) -> None:
    report.mkdir(parents=True, exist_ok=True)
    (report / name).write_text(text, encoding="utf-8")
    print(f"--- {name} ---\n{text[:20000]}")


def strip_windows(root: Path, report: Path) -> None:
    removed: list[tuple[int, str]] = []

    def remove(p: Path) -> None:
        if p.is_file():
            n = p.stat().st_size
            removed.append((n, p.relative_to(root).as_posix()))
            p.unlink()
        elif p.is_dir():
            n = sum(x.stat().st_size for x in p.rglob("*") if x.is_file())
            removed.append((n, p.relative_to(root).as_posix() + "/"))
            shutil.rmtree(p)

    for p in list(root.iterdir()):
        low = p.name.lower()
        if p.is_file() and (
            p.suffix.lower() in {".dll", ".exe", ".pdb"}
            or (low.startswith("nw_") and low.endswith(".pak"))
        ):
            remove(p)

    for name in [
        "resources.pak", "icudtl.dat", "snapshot_blob.bin",
        "v8_context_snapshot.bin", "package.json", "credits.html",
        "debug.log", "supertoolsengine.html",
    ]:
        remove(root / name)
    for name in ["locales", "swiftshader", "save"]:
        remove(root / name)

    text = "".join(f"{n}\t{x}\n" for n, x in sorted(removed, reverse=True))
    text += f"TOTAL_REMOVED_BYTES={sum(n for n, _ in removed)}\n"
    write_report(report, "removed-windows.txt", text)


def decrypt_assets(root: Path, report: Path) -> None:
    sysf = root / "data" / "System.json"
    data = json.loads(sysf.read_text(encoding="utf-8-sig"))
    keyhex = str(data.get("encryptionKey", "")).strip()
    if not keyhex:
        raise SystemExit("System.json has no RPG Maker MV encryptionKey")
    try:
        key = bytes.fromhex(keyhex)[:16]
    except Exception as exc:
        raise SystemExit(f"Invalid encryptionKey: {exc}")
    if len(key) != 16:
        raise SystemExit(f"Expected 16-byte encryption key, got {len(key)}")

    mapping = {".rpgmvp": ".png", ".rpgmvo": ".ogg", ".rpgmvm": ".m4a"}
    counts: dict[str, int] = {}
    failures: list[str] = []
    out_bytes = 0

    def valid(ext: str, b: bytes | bytearray) -> bool:
        if ext == ".png":
            return bytes(b[:8]) == b"\x89PNG\r\n\x1a\n"
        if ext == ".ogg":
            return bytes(b[:4]) == b"OggS"
        if ext == ".m4a":
            return len(b) >= 12 and bytes(b[4:8]) == b"ftyp"
        return False

    for enc_ext, out_ext in mapping.items():
        files = list(root.rglob("*" + enc_ext))
        counts[enc_ext] = len(files)
        for p in files:
            raw = p.read_bytes()
            if len(raw) < 32:
                failures.append(f"{p.relative_to(root)}: encrypted file too small")
                continue
            body = bytearray(raw[16:])
            for i in range(min(16, len(body))):
                body[i] ^= key[i]
            out = p.with_suffix(out_ext)
            out.write_bytes(body)
            out_bytes += len(body)
            if not valid(out_ext, body):
                failures.append(
                    f"{p.relative_to(root)} -> {out.relative_to(root)} bad magic {bytes(body[:16]).hex()}"
                )

    if failures:
        write_report(report, "decrypt-failures.txt", "\n".join(failures))
        raise SystemExit(f"Encrypted asset validation failed for {len(failures)} files")

    data["hasEncryptedImages"] = False
    data["hasEncryptedAudio"] = False
    sysf.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    for ext in mapping:
        for p in root.rglob("*" + ext):
            p.unlink()

    icon = root / "img" / "system" / "IconSet.png"
    if not icon.is_file() or icon.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("IconSet.png was not produced correctly")

    text = "\n".join(f"{k}={v}" for k, v in counts.items())
    text += f"\ndecrypted_bytes={out_bytes}\nhasEncryptedImages=false\nhasEncryptedAudio=false\n"
    text += f"IconSet.png={icon.stat().st_size} bytes\n"
    write_report(report, "decryption.txt", text)


def audit_case_and_refs(root: Path, report: Path) -> None:
    allfiles = [p for p in root.rglob("*") if p.is_file()]
    rel = {p.relative_to(root).as_posix(): p for p in allfiles}
    lower: dict[str, str] = {}
    collisions: dict[str, list[str]] = {}
    for k in rel:
        lower.setdefault(k.lower(), k)
        collisions.setdefault(k.lower(), []).append(k)
    case_collisions = {k: v for k, v in collisions.items() if len(v) > 1}

    rx = re.compile(
        r"(?:(?:img|audio|movies|fonts)/[A-Za-z0-9_ ./@!#$%&()+,;=\-\[\]{}~]+?\."
        r"(?:png|jpg|jpeg|webp|ogg|m4a|mp3|wav|webm|mp4|ttf|woff2?))",
        re.I,
    )
    refs: set[str] = set()
    for p in root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".js", ".json", ".html", ".css"}:
            continue
        if p.stat().st_size >= 20_000_000:
            continue
        s = p.read_text(encoding="utf-8-sig", errors="ignore")
        refs.update(x.strip().replace("\\", "/") for x in rx.findall(s))

    casefix: list[tuple[str, str]] = []
    missing: list[str] = []
    for r in sorted(refs):
        if r in rel:
            continue
        actual = lower.get(r.lower())
        if actual:
            casefix.append((r, actual))
        else:
            missing.append(r)

    for wanted, actual in casefix:
        src = root / actual
        dst = root / wanted
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)

    text = (
        f"files={len(allfiles)}\n"
        f"literal_asset_refs={len(refs)}\n"
        f"case_mismatches_fixed={len(casefix)}\n"
        f"case_collisions={len(case_collisions)}\n"
        f"missing_literal_refs={len(missing)}\n"
        "\nCASE_FIXES:\n"
        + "\n".join(f"{a} <- {b}" for a, b in casefix[:500])
        + "\n\nCASE_COLLISIONS:\n"
        + "\n".join(f"{k}: {v}" for k, v in list(case_collisions.items())[:500])
        + "\n\nMISSING_LITERAL_REFS (may be optional/comment/generated):\n"
        + "\n".join(missing[:1000])
    )
    write_report(report, "asset-audit.txt", text)


CONTROL_INJECTION = r'''<style id="android-port-controls-style">
#android-port-controls{position:fixed;right:14px;bottom:14px;z-index:2147483647;display:flex;gap:10px;pointer-events:auto;user-select:none;-webkit-user-select:none;touch-action:none;font-family:sans-serif}
.android-port-key{min-width:72px;height:48px;padding:0 12px;border:1px solid rgba(255,255,255,.55);border-radius:10px;background:rgba(0,0,0,.48);color:#fff;font-size:14px;font-weight:700;box-shadow:0 2px 8px rgba(0,0,0,.35)}
.android-port-key:active,.android-port-key.pressed{background:rgba(255,255,255,.28)}
</style>
<script id="android-port-compat">
(function(){
  if(typeof window.process==='undefined') window.process={versions:{'node-webkit':'0.0.0'},platform:'android',env:{}};
  else {process.versions=process.versions||{};if(!process.versions['node-webkit'])process.versions['node-webkit']='0.0.0';}
  window.addEventListener('error',function(e){console.error('[AndroidPort][uncaught] '+String(e.message||e.error||'unknown')+' @ '+String(e.filename||'')+':'+String(e.lineno||0));});
  window.addEventListener('unhandledrejection',function(e){console.error('[AndroidPort][promise] '+String(e.reason));});
  function setKey(symbol,down,keyCode,key){
    try{if(window.Input&&Input._currentState)Input._currentState[symbol]=!!down;}catch(e){}
    try{var ev=new KeyboardEvent(down?'keydown':'keyup',{key:key,code:key==='Enter'?'Enter':'Escape',keyCode:keyCode,which:keyCode,bubbles:true,cancelable:true});document.dispatchEvent(ev);}catch(e){}
  }
  function installControls(){
    if(document.getElementById('android-port-controls'))return;
    var box=document.createElement('div');box.id='android-port-controls';
    function add(label,symbol,code,key){
      var b=document.createElement('button');b.type='button';b.className='android-port-key';b.textContent=label;b.setAttribute('aria-label',label);
      var down=function(e){e.preventDefault();e.stopPropagation();b.classList.add('pressed');setKey(symbol,true,code,key);};
      var up=function(e){e.preventDefault();e.stopPropagation();b.classList.remove('pressed');setKey(symbol,false,code,key);};
      b.addEventListener('pointerdown',down,{passive:false});b.addEventListener('pointerup',up,{passive:false});b.addEventListener('pointercancel',up,{passive:false});b.addEventListener('pointerleave',function(e){if(b.classList.contains('pressed'))up(e);},{passive:false});
      box.appendChild(b);
    }
    add('ESC','escape',27,'Escape');add('ENTER','ok',13,'Enter');document.body.appendChild(box);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',installControls);else installControls();
})();
</script>
'''


def patch_index(root: Path, report: Path) -> None:
    idx = root / "index.html"
    s = idx.read_text(encoding="utf-8-sig", errors="replace")
    if "android-port-compat" not in s:
        pos = s.lower().find("<head>")
        s = s[: pos + 6] + CONTROL_INJECTION + s[pos + 6 :] if pos >= 0 else CONTROL_INJECTION + s
    idx.write_text(s, encoding="utf-8")
    write_report(report, "controls.txt", "ENTER=enabled\nESC=enabled\nprocess_guard=enabled\n")


def patch_java(java: Path, report: Path) -> None:
    j = java.read_text(encoding="utf-8")
    if "import android.util.Log;" not in j:
        j = j.replace("import android.os.Bundle;", "import android.os.Bundle;\nimport android.util.Log;\nimport android.content.Intent;")

    j = j.replace("settings.setAllowContentAccess(false);", "settings.setAllowContentAccess(true);")
    j = j.replace("settings.setAllowUniversalAccessFromFileURLs(false);", "settings.setAllowUniversalAccessFromFileURLs(true);")
    if "settings.setLoadsImagesAutomatically(true);" not in j:
        anchor = "settings.setUseWideViewPort(true);"
        extra = (
            "\n        settings.setLoadsImagesAutomatically(true);"
            "\n        settings.setJavaScriptCanOpenWindowsAutomatically(true);"
            "\n        settings.setCacheMode(WebSettings.LOAD_DEFAULT);"
        )
        j = j.replace(anchor, anchor + extra)

    j = j.replace(
        "return super.onConsoleMessage(consoleMessage);",
        'Log.e("RPGWEB", consoleMessage.sourceId() + ":" + consoleMessage.lineNumber() + " " + consoleMessage.message());\n                return true;',
    )
    j = j.replace(
        "super.onPageFinished(view, url);\n            injectRuntimePatches(view);",
        'super.onPageFinished(view, url);\n            Log.i("RPGWEB", "PAGE_FINISHED " + url);\n            injectRuntimePatches(view);',
    )

    old_override = '''            Uri uri = request.getUrl();
            return !"file".equals(uri.getScheme());'''
    new_override = '''            Uri uri = request.getUrl();
            if ("file".equals(uri.getScheme())) return false;
            try {
                startActivity(new Intent(Intent.ACTION_VIEW, uri));
            } catch (Exception error) {
                Log.w("RPGWEB", "Cannot open external URL: " + uri, error);
            }
            return true;'''
    if old_override in j:
        j = j.replace(old_override, new_override)

    old_back = '''    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }
        super.onBackPressed();
    }'''
    new_back = '''    @Override
    public void onBackPressed() {
        if (webView != null) {
            webView.evaluateJavascript("(function(){try{if(window.Input&&Input._currentState){Input._currentState.escape=true;setTimeout(function(){Input._currentState.escape=false;},90);}}catch(e){}})();", null);
            return;
        }
        super.onBackPressed();
    }'''
    if old_back in j:
        j = j.replace(old_back, new_back)

    java.write_text(j, encoding="utf-8")
    checks = {
        "file_access": "setAllowFileAccessFromFileURLs(true)" in j,
        "universal_file_access": "setAllowUniversalAccessFromFileURLs(true)" in j,
        "console_log": 'Log.e("RPGWEB"' in j,
        "page_marker": "PAGE_FINISHED" in j,
        "back_as_escape": "Input._currentState.escape=true" in j,
        "external_intent": "Intent.ACTION_VIEW" in j,
    }
    if not all(checks.values()):
        raise SystemExit(f"MainActivity patch incomplete: {checks}")
    write_report(report, "webview-patches.txt", "\n".join(f"{k}={v}" for k, v in checks.items()) + "\n")


def validate(root: Path, report: Path) -> None:
    required = [
        "index.html", "js/rpg_core.js", "js/rpg_managers.js", "js/rpg_objects.js",
        "js/rpg_scenes.js", "js/rpg_sprites.js", "js/rpg_windows.js", "js/plugins.js",
        "data/System.json", "img/system/IconSet.png",
    ]
    missing = [x for x in required if not (root / x).is_file()]
    if missing:
        raise SystemExit(f"Missing core files: {missing}")
    sysdata = json.loads((root / "data/System.json").read_text(encoding="utf-8-sig"))
    if sysdata.get("hasEncryptedImages") or sysdata.get("hasEncryptedAudio"):
        raise SystemExit("Runtime encryption flags still enabled")
    encrypted = [p for ext in (".rpgmvp", ".rpgmvo", ".rpgmvm") for p in root.rglob("*" + ext)]
    if encrypted:
        raise SystemExit(f"Encrypted assets remain: {encrypted[:10]}")
    bad_json = []
    for p in (root / "data").glob("*.json"):
        try:
            json.loads(p.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            bad_json.append(f"{p.name}: {exc}")
    if bad_json:
        raise SystemExit("Invalid data JSON: " + repr(bad_json[:20]))
    win = [p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".dll", ".exe", ".pdb"}]
    if win:
        raise SystemExit(f"Windows binaries remain: {win[:20]}")
    files = [p for p in root.rglob("*") if p.is_file()]
    text = (
        "core_required=PASS\n"
        f"json_files={len(list((root / 'data').glob('*.json')))}\n"
        "encrypted_remaining=0\nwindows_binaries_remaining=0\n"
        f"source_files={len(files)}\nsource_bytes={sum(p.stat().st_size for p in files)}\n"
    )
    write_report(report, "prebuild-validation.txt", text)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: stable_v3_patch.py <game_webroot> <MainActivity.java> <report_dir>")
    root = Path(sys.argv[1]).resolve()
    java = Path(sys.argv[2]).resolve()
    report = Path(sys.argv[3]).resolve()
    strip_windows(root, report)
    decrypt_assets(root, report)
    audit_case_and_refs(root, report)
    patch_index(root, report)
    patch_java(java, report)
    validate(root, report)
    print("STABLE_V3_PATCH_COMPLETE")


if __name__ == "__main__":
    main()
