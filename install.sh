#!/usr/bin/env bash
# ROOT Kata installer: one supported path for students.
#
# Creates (or updates) the `root-kata` conda environment, installs the package
# with that environment's OWN Python (`python -m pip`, never a bare `pip`),
# and verifies the result before printing the next step.
set -euo pipefail
cd "$(dirname "$0")"

ENV_NAME="root-kata"

bold() { printf '\033[1m==> %s\033[0m\n' "$*"; }
die()  { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- prerequisite
PKG=""
if command -v conda >/dev/null 2>&1; then PKG="conda"
elif command -v mamba >/dev/null 2>&1; then PKG="mamba"
elif command -v micromamba >/dev/null 2>&1; then PKG="micromamba"
else
  die "conda (or mamba/micromamba) is required but was not found on PATH.
       Install Miniforge from https://github.com/conda-forge/miniforge (pick the Linux x86_64 script),
       open a new terminal, and run ./install.sh again."
fi
bold "Using $PKG from $(command -v "$PKG")"

in_env() {  # run a command inside the root-kata environment
  if [ "$PKG" = "micromamba" ]; then micromamba run -n "$ENV_NAME" "$@"
  else "$PKG" run -n "$ENV_NAME" "$@"; fi
}

# --------------------------------------------------------------- env creation
if "$PKG" env list 2>/dev/null | grep -qE "^ *${ENV_NAME}"; then
  bold "Updating existing '$ENV_NAME' environment"
  if [ "$PKG" = "micromamba" ]; then micromamba update -y -n "$ENV_NAME" -f environment.yml
  else "$PKG" env update -f environment.yml; fi
else
  bold "Creating '$ENV_NAME' environment (Python 3.12 + CERN ROOT + JupyterLab; this downloads ~2 GB)"
  if [ "$PKG" = "micromamba" ]; then micromamba create -y -n "$ENV_NAME" -f environment.yml
  else "$PKG" env create -f environment.yml; fi
fi

# ------------------------------------------------- install with the env's pip
bold "Installing ROOT Kata using the environment's own Python"
in_env python -m pip install --no-input -e .

# ------------------------------------------------------- interpreter checks
bold "Verifying that everything lives in the same environment"
in_env python - <<'VERIFY'
import pathlib, shutil, sys
print(f"python      {sys.executable}")
import root_kata
print(f"root_kata   {pathlib.Path(root_kata.__file__).resolve()}")
rk = shutil.which("root-kata")
print(f"root-kata   {rk}")
if rk is None or pathlib.Path(rk).resolve().parent != pathlib.Path(sys.executable).parent:
    sys.exit("MISMATCH: the `root-kata` command belongs to another Python environment.\n"
             "Fix: deactivate all environments, remove '~/.local/lib'/user installs of root-kata,\n"
             "then re-run ./install.sh")
import ROOT
print(f"ROOT        {ROOT.gROOT.GetVersion()}")
VERIFY

bold "ROOT Kata is ready. Next steps:

  conda activate root-kata
  root-kata lab

Then open http://127.0.0.1:8888/lab in your browser."
