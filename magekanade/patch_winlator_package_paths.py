#!/usr/bin/env python3
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(sys.argv[1]).resolve()
APP = ROOT / "app"
MAIN = APP / "src/main"
ASSETS = MAIN / "assets"

OLD = b"/data/data/com.winlator"
NEW = b"/data/data/com.magekana"
OLD_TEXT = OLD.decode("ascii")
NEW_TEXT = NEW.decode("ascii")

if len(OLD) != len(NEW):
    raise SystemExit("Package path replacement must be exactly the same byte length")

def patch_regular_file(path: Path) -> int:
    try:
        data = path.read_bytes()
    except (OSError, PermissionError):
        return 0
    count = data.count(OLD)
    if count:
        path.write_bytes(data.replace(OLD, NEW))
    return count

def patch_symlink(path: Path) -> int:
    try:
        target = os.readlink(path)
    except OSError:
        return 0
    count = target.count(OLD_TEXT)
    if count:
        patched = target.replace(OLD_TEXT, NEW_TEXT)
        path.unlink()
        os.symlink(patched, path)
    return count

def patch_tree(root: Path, skip_tzst: bool = False):
    byte_hits = 0
    link_hits = 0
    files_changed = 0
    links_changed = 0
    if not root.exists():
        return byte_hits, link_hits, files_changed, links_changed

    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in list(dirs):
            p = current_path / name
            if p.is_symlink():
                count = patch_symlink(p)
                if count:
                    link_hits += count
                    links_changed += 1
                dirs.remove(name)
        for name in files:
            p = current_path / name
            if p.is_symlink():
                count = patch_symlink(p)
                if count:
                    link_hits += count
                    links_changed += 1
                continue
            if skip_tzst and p.suffix == ".tzst":
                continue
            count = patch_regular_file(p)
            if count:
                byte_hits += count
                files_changed += 1
    return byte_hits, link_hits, files_changed, links_changed

def ensure_no_old_path(root: Path, skip_tzst: bool = False):
    leftovers = []
    if not root.exists():
        return leftovers
    for current, dirs, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in list(dirs):
            p = current_path / name
            if p.is_symlink():
                try:
                    if OLD_TEXT in os.readlink(p):
                        leftovers.append(str(p))
                except OSError:
                    pass
                dirs.remove(name)
        for name in files:
            p = current_path / name
            if p.is_symlink():
                try:
                    if OLD_TEXT in os.readlink(p):
                        leftovers.append(str(p))
                except OSError:
                    pass
                continue
            if skip_tzst and p.suffix == ".tzst":
                continue
            try:
                if OLD in p.read_bytes():
                    leftovers.append(str(p))
            except (OSError, PermissionError):
                pass
    return leftovers

# Patch source/config paths that become classes.dex / native .so files.
raw_hits = patch_tree(MAIN, skip_tzst=True)
raw_leftovers = ensure_no_old_path(MAIN, skip_tzst=True)
if raw_leftovers:
    raise SystemExit("Unpatched raw package paths remain: " + ", ".join(raw_leftovers[:20]))

archive_byte_hits = 0
archive_link_hits = 0
archives_changed = 0

for archive in sorted(ASSETS.rglob("*.tzst")):
    with tempfile.TemporaryDirectory(prefix="mage-pathpatch-") as tmp:
        tmpdir = Path(tmp)
        extracted = tmpdir / "root"
        extracted.mkdir()

        subprocess.run(
            ["tar", "--zstd", "-xf", str(archive), "-C", str(extracted)],
            check=True,
            stdout=subprocess.DEVNULL,
        )

        byte_hits, link_hits, _, _ = patch_tree(extracted)
        leftovers = ensure_no_old_path(extracted)
        if leftovers:
            raise SystemExit(f"Unpatched path remains in {archive}: {leftovers[:10]}")

        if byte_hits or link_hits:
            output = tmpdir / "patched.tzst"
            subprocess.run(
                ["tar", "--zstd", "-cf", str(output), "-C", str(extracted), "."],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            shutil.copy2(output, archive)
            archive_byte_hits += byte_hits
            archive_link_hits += link_hits
            archives_changed += 1
            print(f"PATCHED_ARCHIVE {archive.relative_to(ASSETS)} bytes={byte_hits} symlinks={link_hits}")

# Pinned Winlator 11.2 contains package-path occurrences in compressed assets
# plus the container-pattern Z: symlink. Failing low is safer than shipping
# another APK with a partially patched Android sandbox path.
total_archive_hits = archive_byte_hits + archive_link_hits
if total_archive_hits < 459:
    raise SystemExit(
        f"Package path audit unexpectedly low: archive_hits={total_archive_hits}; expected at least 459"
    )

print(
    "MAGE_PACKAGE_PATH_PATCH_OK "
    f"raw_bytes={raw_hits[0]} raw_links={raw_hits[1]} "
    f"archive_bytes={archive_byte_hits} archive_links={archive_link_hits} "
    f"archives_changed={archives_changed}"
)
print("package_path=/data/data/com.magekana")
