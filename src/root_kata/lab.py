"""`root-kata lab`: one command that starts the local learning environment.

Starts JupyterLab bound to this environment's own interpreter, with
--no-browser so WSL/Linux terminals never try to open a GUI browser, and
prepares a tiny bootstrap notebook per exercise under ./notebooks/ so each
kata opens with a single click.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from .catalog import list_exercises

DEFAULT_PORT = 8888


def notebook_dir() -> Path:
    return Path(os.environ.get("ROOT_KATA_NOTEBOOKS", "notebooks"))


def starter_notebook(exercise_id: str) -> dict:
    return {
        "cells": [{
            "cell_type": "code",
            "execution_count": None,
            "id": exercise_id,
            "metadata": {},
            "outputs": [],
            "source": [f"import root_kata as rk\nrk.start(\"{exercise_id}\")\n"],
        }],
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def ensure_notebooks(base: Path | None = None) -> list[Path]:
    """Create one bootstrap notebook per published exercise; never overwrite."""
    root = Path(base) if base is not None else notebook_dir()
    root.mkdir(parents=True, exist_ok=True)
    written = []
    for ex in list_exercises():
        path = root / f"{ex['id']}.ipynb"
        if not path.exists():
            path.write_text(json.dumps(starter_notebook(ex["id"]), indent=1), encoding="utf-8")
            written.append(path)
    return written


def lab(port: int = DEFAULT_PORT, host: str = "127.0.0.1") -> int:
    written = ensure_notebooks()
    for path in written:
        print(f"prepared {path}")
    cmd = [sys.executable, "-m", "jupyter", "lab", "--no-browser",
           f"--ip={host}", f"--port={port}"]
    url = f"http://{host}:{port}/lab"
    print(f"\nROOT Kata Jupyter: {url}")
    print("Open that URL in your browser. Press Ctrl-C here to stop.\n")
    try:
        return subprocess.run(cmd).returncode
    except KeyboardInterrupt:
        return 0
