import os
import platform
import shutil
import subprocess
from pathlib import Path

# --- Configuration ---
APP_NAME = "SqlParserPlus"
ENTRY_POINT = "SqlParserPlusGUI.py"
ICON_PATH = "icon.ico"  # Recommended: Create an icon for your app

# --- Platform Specifics ---
system = platform.system()
EXE_NAME = f"{APP_NAME}.exe" if system == "Windows" else APP_NAME
DIST_PATH = Path("dist")
BUILD_PATH = Path("build")

# --- PyInstaller Command ---
# --noconfirm: Overwrite output directory without asking
# --log-level: Set to WARN to reduce output noise
pyinstaller_command = [
    "pyinstaller",
    "--noconfirm",
    "--log-level=WARN",
    "--onefile",
    "--windowed",  # Use for GUI apps to hide the console
    f"--name={APP_NAME}",
    ENTRY_POINT,
]

if os.path.exists(ICON_PATH):
    pyinstaller_command.append(f"--icon={ICON_PATH}")
else:
    print(f"Warning: Icon file not found at '{ICON_PATH}'. The executable will have a default icon.")


def build():
    """Runs the PyInstaller build process."""
    print(f"--- Starting build for {system} ---")

    # 1. Clean previous builds
    print("1. Cleaning previous build artifacts...")
    if DIST_PATH.exists():
        shutil.rmtree(DIST_PATH)
    if BUILD_PATH.exists():
        shutil.rmtree(BUILD_PATH)
    for file in Path(".").glob("*.spec"):
        file.unlink()

    # 2. Run PyInstaller
    print(f"2. Running PyInstaller...")
    print(f"   Command: {' '.join(pyinstaller_command)}")
    try:
        subprocess.run(pyinstaller_command, check=True, text=True, capture_output=True)
        print("   PyInstaller completed successfully.")
    except subprocess.CalledProcessError as e:
        print("\n--- PyInstaller Build Failed ---")
        print(f"  Exit Code: {e.returncode}")
        print("\n--- STDOUT ---")
        print(e.stdout)
        print("\n--- STDERR ---")
        print(e.stderr)
        print("----------------------------------")
        return

    # 3. Post-build cleanup and verification
    print("3. Verifying build output...")
    final_executable = DIST_PATH / EXE_NAME
    if final_executable.exists():
        print(f"   Success! Executable created at: {final_executable.resolve()}")
        print("\n--- Build Complete ---")
    else:
        print(f"   Error: Expected executable not found at '{final_executable}'.")
        print("--- Build Failed ---")


if __name__ == "__main__":
    # Ensure build requirements are installed
    print("--- Checking build dependencies ---")
    try:
        subprocess.run(
            ["pip", "install", "-r", "build_requirements.txt"],
            check=True,
            capture_output=True,
            text=True
        )
        print("   Build dependencies are satisfied.")
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print("Error: Could not install dependencies from 'build_requirements.txt'.")
        print("Please ensure 'pip' is installed and the requirements file exists.")
        if isinstance(e, subprocess.CalledProcessError):
            print(e.stderr)
        exit(1)

    build()
