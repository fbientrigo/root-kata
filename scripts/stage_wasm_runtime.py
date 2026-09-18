#!/usr/bin/env python3
"""Stage ROOT WebAssembly runtime assets into the product static directory.

Deterministically links or copies verified ROOT WASM runtime assets into
docs/wasm/ so the real product frontend can lazily load them.
Avoids duplicating binary files on disk by preferring hardlinks when supported.

Usage:
  python3 scripts/stage_wasm_runtime.py [target_dir]
"""
import os
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_TARGET = REPO / "docs" / "wasm"
SOURCE_WEB = REPO / "wasm" / "build" / "rootweb" / "web"
ROOTWEB_RUN = REPO / "wasm" / "gates" / "rootweb" / "run.sh"

REQUIRED_FILES = [
    "xcpp.js",
    "xcpp.wasm",
    "xcpp.data",
    "libxeus.so",
    "libclangCppInterOp.so",
    "libCore.so",
    "libThread.so",
    "libRIO.so",
    "libMathCore.so",
    "libMatrix.so",
    "libHist.so",
    "libMinuit2.so",
    "libroota.so",
    "libCling.so",
    "rootsys.js",
]


def ensure_source_web() -> pathlib.Path:
    """Ensure that the verified ROOT WASM runtime files are available."""
    missing = [f for f in REQUIRED_FILES if not (SOURCE_WEB / f).is_file()]
    if missing:
        print(f"stage_wasm_runtime: source web missing {len(missing)} files, running rootweb payload...")
        res = subprocess.run(["bash", str(ROOTWEB_RUN), "payload"], cwd=str(REPO), capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stdout, file=sys.stderr)
            print(res.stderr, file=sys.stderr)
            raise RuntimeError("Failed to stage rootweb payload")

    for f in REQUIRED_FILES:
        path = SOURCE_WEB / f
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Required runtime artifact missing or empty: {path}")

    return SOURCE_WEB


def link_or_copy(src: pathlib.Path, dst: pathlib.Path) -> str:
    """Link src to dst using hardlinks if possible, falling back to copy."""
    if dst.exists():
        # Check if already pointing to the same file or identical
        try:
            if src.stat().st_ino == dst.stat().st_ino and src.stat().st_dev == dst.stat().st_dev:
                return "identical"
        except OSError:
            pass
        dst.unlink()

    try:
        os.link(src, dst)
        return "hardlinked"
    except OSError:
        shutil.copy2(src, dst)
        return "copied"


def stage(target_dir: pathlib.Path | None = None) -> int:
    target = target_dir or DEFAULT_TARGET
    target.mkdir(parents=True, exist_ok=True)
    source = ensure_source_web()

    total_bytes = 0
    counts = {"hardlinked": 0, "copied": 0, "identical": 0}

    for name in REQUIRED_FILES:
        src = source / name
        dst = target / name
        mode = link_or_copy(src, dst)
        counts[mode] += 1
        total_bytes += dst.stat().st_size

    mb = total_bytes / (1024 * 1024)
    print(f"Staged {len(REQUIRED_FILES)} runtime files ({mb:.1f} MB) into {target}")
    print(f"  Actions: {counts['hardlinked']} hardlinked, {counts['identical']} already linked, {counts['copied']} copied")
    return 0


if __name__ == "__main__":
    target_path = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else None
    sys.exit(stage(target_path))
