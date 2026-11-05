#!/usr/bin/env python3
"""
Build a single-file executable with PyInstaller.

    python build_exe.py            # builds for the current OS
    python build_exe.py --dir      # one-folder mode (faster startup)

Output goes to release/ (NOT dist/ — build tooling directories are commonly
excluded from archives and snapshots).

Notes
-----
* PyInstaller cannot cross-compile. Run this on Windows to get a .exe, on
  macOS to get a .app bundle, on Linux to get an ELF binary. The included
  GitHub Actions workflow builds all three from a single push.
* sklearn and matplotlib are excluded: sklearn is imported lazily and is only
  needed if you enable the (off by default) ML filter, and matplotlib is only
  used by the offline report generator. Removing them roughly halves the size.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys

SEP = os.pathsep          # ';' on Windows, ':' elsewhere
EXE_SUFFIX = ".exe" if platform.system() == "Windows" else ""

HIDDEN = [
    "uvicorn.logging",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.protocols.websockets.websockets_impl",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "aitrader.brokers.simulator",
    "aitrader.brokers.mt5",
    "aitrader.brokers.crypto",
    "aitrader.dashboard.server",
    "sqlite3",
    "pandas._libs.tslibs.timedeltas",
]

EXCLUDES = [
    "sklearn", "scipy", "matplotlib", "pytest", "PIL", "tkinter",
    "IPython", "jupyter", "notebook", "torch", "tensorflow",
    "setuptools", "pip", "wheel", "black", "mypy",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", action="store_true", help="one-folder mode")
    ap.add_argument("--name", default="ai-trader")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)

    mode = [] if args.dir else ["--onefile"]
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "app.py",
        f"--name={args.name}",
        "--noconfirm", "--clean",
        "--distpath=release",
        "--workpath=build_tmp",
        "--specpath=build_tmp",
        *mode,
        # Absolute source paths are required: with --specpath set, PyInstaller
        # resolves relative --add-data entries against the spec's directory.
        f"--add-data={os.path.join(here, 'aitrader', 'dashboard', 'static')}{SEP}aitrader/dashboard/static",
        f"--add-data={os.path.join(here, 'data')}{SEP}data",
        f"--add-data={os.path.join(here, 'reports')}{SEP}reports",
    ]
    for h in HIDDEN:
        cmd.append(f"--hidden-import={h}")
    for x in EXCLUDES:
        cmd.append(f"--exclude-module={x}")

    # keep the console on all platforms: this is a server, and seeing the
    # engine log is the whole point
    cmd.append("--console")

    print("Building with PyInstaller...")
    print(" ".join(cmd[:8]), "...")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print("\nBUILD FAILED")
        return 1

    out = os.path.join("release", args.name + EXE_SUFFIX)
    if not os.path.exists(out):
        print("\nBuild finished but output missing:", out)
        return 1

    size = os.path.getsize(out) / (1024 * 1024)
    print(f"\nBUILD OK -> {out}  ({size:.1f} MB)")
    print("\nRun it:")
    print(f"  {out}")
    print("\nOr with options:")
    print(f"  APP_TOKEN=your-secret PORT=8080 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
