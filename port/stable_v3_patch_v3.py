from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import stable_v3_patch as base

ART_HEADER = bytes([
    0x41,0x52,0x54,0x00,0x45,0x4E,0x43,0x52,
    0x59,0x50,0x54,0x45,0x52,0x31,0x30,0x30,
    0x46,0x52,0x45,0x45,0x00,0x56,0x45,0x52,
    0x53,0x49,0x4F,0x4E,0x00,0x00,0x00,0x00,
])


def art_key(password: str) -> bytes:
    # Exact behavior of Art_Decrypterator3000 v1.01:
    # SparkMD5.hash(password) -> pairs -> append pairs in reverse -> parseInt(hex, 16).
    digest = hashlib.md5(password.encode('utf-8')).hexdigest()
    first = bytes(int(digest[i:i+2], 16) for i in range(0, len(digest), 2))
    return first + first[::-1]


def decrypt_art_file(raw: bytes, key: bytes) -> bytes:
    if len(raw) < len(ART_HEADER):
        raise ValueError('encrypted file shorter than ART header')
    if raw[:32] != ART_HEADER:
        raise ValueError('Art Decrypterator header mismatch')
    body = bytearray(raw[32:])
    n = min(len(raw), len(key))  # mirrors plugin maxBytes = min(source.byteLength, key.length)
    # source is always larger than 32 in this game; plugin XORs first maxBytes bytes of body.
    for i in range(min(n, len(body))):
        body[i] ^= key[i]
    return bytes(body)


def magic_ok(ext: str, data: bytes) -> bool:
    if ext == '.png':
        return data.startswith(b'\x89PNG\r\n\x1a\n')
    if ext == '.ogg':
        return data.startswith(b'OggS')
    if ext == '.m4a':
        return len(data) >= 12 and data[4:8] == b'ftyp'
    return False


def repair_system_case(root: Path) -> list[tuple[str,str]]:
    system = root / 'img' / 'system'
    system.mkdir(parents=True, exist_ok=True)
    fixes: list[tuple[str,str]] = []

    # Names that RPG Maker MV itself requests with fixed case.
    canonical = {
        'IconSet','Balloon','ButtonSet','Damage','GameOver','MadeWithMv',
        'Shadow1','Shadow2','States','Weapons1','Weapons2','Weapons3','Window',
    }
    # Also collect names passed literally to loadSystem/reserveSystem from game JS.
    rx = re.compile(r'(?:loadSystem|reserveSystem)\s*\(\s*[\'\"]([^\'\"]+)[\'\"]')
    for p in root.rglob('*.js'):
        try:
            text = p.read_text(encoding='utf-8-sig', errors='ignore')
        except Exception:
            continue
        canonical.update(rx.findall(text))

    existing = {p.name.lower(): p for p in system.glob('*.png') if p.is_file()}
    # Also allow a root-level img/IconSet.png from the supplied package as a last-resort real asset source.
    root_images = {p.name.lower(): p for p in (root/'img').glob('*.png') if p.is_file()}

    for name in sorted(canonical):
        wanted = system / (name + '.png')
        if wanted.exists():
            continue
        src = existing.get((name + '.png').lower()) or root_images.get((name + '.png').lower())
        if src and src.is_file():
            shutil.copy2(src, wanted)
            fixes.append((wanted.relative_to(root).as_posix(), src.relative_to(root).as_posix()))
    return fixes


def decrypt_assets(root: Path, report: Path) -> None:
    sysf = root/'data'/'System.json'
    system = json.loads(sysf.read_text(encoding='utf-8-sig'))
    password = str(system.get('encryptionKey',''))
    if not password:
        raise SystemExit('System.json encryptionKey missing')
    key = art_key(password)
    if len(key) != 32:
        raise SystemExit(f'Art transformed key must be 32 bytes, got {len(key)}')

    mapping = {'.rpgmvp':'.png','.rpgmvo':'.ogg','.rpgmvm':'.m4a'}
    counts = {}
    failures = []
    decrypted_bytes = 0
    header_mismatches = 0

    for enc_ext, out_ext in mapping.items():
        files = list(root.rglob('*'+enc_ext))
        counts[enc_ext] = len(files)
        for p in files:
            raw = p.read_bytes()
            try:
                body = decrypt_art_file(raw, key)
            except Exception as exc:
                header_mismatches += 1
                failures.append(f'{p.relative_to(root)}: {exc}')
                continue
            if not magic_ok(out_ext, body):
                failures.append(
                    f'{p.relative_to(root)} -> {p.with_suffix(out_ext).relative_to(root)}: '
                    f'bad {out_ext} magic {body[:32].hex()}'
                )
                continue
            out = p.with_suffix(out_ext)
            out.write_bytes(body)
            decrypted_bytes += len(body)

    if failures:
        base.write_report(report,'art-decrypt-failures.txt','\n'.join(failures[:5000]))
        raise SystemExit(f'Art Decrypterator conversion failed for {len(failures)} assets')

    # Only after every asset validates do we switch the game to plain resource loading.
    system['hasEncryptedImages'] = False
    system['hasEncryptedAudio'] = False
    sysf.write_text(json.dumps(system,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    for enc_ext in mapping:
        for p in root.rglob('*'+enc_ext):
            p.unlink()

    fixes = repair_system_case(root)
    icon = root/'img'/'system'/'IconSet.png'
    if not icon.is_file() or not magic_ok('.png',icon.read_bytes()):
        raise SystemExit('Canonical img/system/IconSet.png is still missing/invalid after case repair')

    text = (
        f'art_header={ART_HEADER.hex()}\n'
        f'md5_transform_key_bytes={len(key)}\n'
        + '\n'.join(f'{k}={v}' for k,v in counts.items())
        + f'\ndecrypted_bytes={decrypted_bytes}\nheader_mismatches={header_mismatches}\n'
        + 'hasEncryptedImages=false\nhasEncryptedAudio=false\n'
        + f'IconSet.png={icon.stat().st_size}\n'
        + f'system_case_aliases={len(fixes)}\n'
        + '\n'.join(f'CASE_ALIAS {a} <- {b}' for a,b in fixes)
        + '\n'
    )
    base.write_report(report,'art-decryption.txt',text)


base.decrypt_assets = decrypt_assets

if __name__ == '__main__':
    base.main()
