"""Packaging script to bundle the tool into a standalone single executable using PyInstaller.

Usage:
    python build_exe.py
"""

import os
import sys
import subprocess


def build():
    print("🚀 Building Standalone Executable via PyInstaller...")
    
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "AndroidAdwareCleaner",
        "--add-data", "core:core",
        "--add-data", "gui:gui",
        "--hidden-import", "customtkinter",
        "--hidden-import", "reportlab",
        "--hidden-import", "PIL",
        "--hidden-import", "pyaxmlparser",
        "--collect-all", "customtkinter",
        "main.py"
    ]
    
    print("Running:", " ".join(cmd))
    res = subprocess.run(cmd)
    if res.returncode == 0:
        print("✅ Build successful! Output in dist/AndroidAdwareCleaner")
    else:
        print(f"❌ Build failed with exit code {res.returncode}")


if __name__ == "__main__":
    build()
