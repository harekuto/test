from __future__ import annotations

import json
import shutil
from pathlib import Path

import stable_v3_patch as base

PNG16 = bytes.fromhex('89504e470d0a1a0a0000000d49484452')


def decrypt_assets(root: Path, report: Path) -> None:
    sysf = root / 'data' / 'System.json'
    data = json.loads(sysf.read_text(encoding='utf-8-sig'))
    system_key_hex = str(data.get('encryptionKey', '')).strip()
    try:
        system_key = bytes.fromhex(system_key_hex)[:16]
    except Exception:
        system_key = b''

    png_files = list(root.rglob('*.rpgmvp'))
    if not png_files:
        raise SystemExit('No .rpgmvp files found; cannot verify encrypted asset pipeline')

    sample = png_files[0]
    sample_raw = sample.read_bytes()
    if len(sample_raw) < 32:
        raise SystemExit('Encrypted PNG sample is too small')
    header16 = sample_raw[:16]
    encrypted_first16 = sample_raw[16:32]

    def decrypt_first(raw: bytes, key: bytes) -> bytes:
        if len(key) != 16 or len(raw) < 32:
            return b''
        body = bytearray(raw[16:32])
        for i in range(16):
            body[i] ^= key[i]
        return bytes(body)

    system_ok = len(system_key) == 16 and decrypt_first(sample_raw, system_key) == PNG16
    if system_ok:
        key = system_key
        source = 'System.json'
    else:
        key = bytes(a ^ b for a, b in zip(encrypted_first16, PNG16))
        source = 'derived-from-encrypted-PNG-header'
        # Prove the recovered key against many independent encrypted PNG files.
        probes = png_files[: min(64, len(png_files))]
        bad = [p for p in probes if decrypt_first(p.read_bytes(), key) != PNG16]
        if bad:
            raise SystemExit(f'Could not recover a consistent RPG Maker encryption key; {len(bad)} PNG probes failed')

    mapping = {'.rpgmvp': '.png', '.rpgmvo': '.ogg', '.rpgmvm': '.m4a'}
    counts: dict[str, int] = {}
    failures: list[str] = []
    out_bytes = 0

    def valid(ext: str, b: bytes | bytearray) -> bool:
        bb = bytes(b)
        if ext == '.png':
            return bb.startswith(b'\x89PNG\r\n\x1a\n')
        if ext == '.ogg':
            return bb.startswith(b'OggS')
        if ext == '.m4a':
            return len(bb) >= 12 and bb[4:8] == b'ftyp'
        return False

    for enc_ext, out_ext in mapping.items():
        files = list(root.rglob('*' + enc_ext))
        counts[enc_ext] = len(files)
        for p in files:
            raw = p.read_bytes()
            if len(raw) < 32:
                failures.append(f'{p.relative_to(root)}: encrypted file too small')
                continue
            body = bytearray(raw[16:])
            for i in range(min(16, len(body))):
                body[i] ^= key[i]
            out = p.with_suffix(out_ext)
            out.write_bytes(body)
            out_bytes += len(body)
            if not valid(out_ext, body):
                failures.append(f'{p.relative_to(root)} -> {out.relative_to(root)}: invalid {out_ext} magic {bytes(body[:16]).hex()}')

    if failures:
        base.write_report(report, 'decrypt-failures-v2.txt', '\n'.join(failures[:5000]))
        raise SystemExit(f'Asset decrypt validation still failed for {len(failures)} files')

    data['hasEncryptedImages'] = False
    data['hasEncryptedAudio'] = False
    sysf.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

    for ext in mapping:
        for p in root.rglob('*' + ext):
            p.unlink()

    # The supplied Windows build contains IconSet at img/IconSet.*, while MV loads img/system/IconSet.png.
    # Repair that packaging defect without substituting a placeholder.
    wanted = root / 'img' / 'system' / 'IconSet.png'
    if not wanted.is_file():
        candidates = [p for p in (root / 'img').rglob('*.png') if p.name.lower() == 'iconset.png']
        if not candidates:
            raise SystemExit('No decrypted IconSet.png exists anywhere in the game')
        preferred = next((p for p in candidates if p.parent == root / 'img'), candidates[0])
        wanted.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(preferred, wanted)

    if wanted.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':
        raise SystemExit('Repaired img/system/IconSet.png is not a valid PNG')

    text = (
        f'header16={header16.hex()}\n'
        f'system_key_present={bool(system_key_hex)}\n'
        f'system_key_matched={system_ok}\n'
        f'key_source={source}\n'
        + '\n'.join(f'{k}={v}' for k, v in counts.items())
        + f'\ndecrypted_bytes={out_bytes}\n'
        + 'hasEncryptedImages=false\nhasEncryptedAudio=false\n'
        + f'img/system/IconSet.png={wanted.stat().st_size} bytes\n'
    )
    base.write_report(report, 'decryption-v2.txt', text)


base.decrypt_assets = decrypt_assets

if __name__ == '__main__':
    base.main()
