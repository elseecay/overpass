import subprocess
import os
import shutil

from pathlib import Path

from utils.common import is_os_windows


APPNAME = "overpass"


if is_os_windows():
    EXEC_FILE = APPNAME + ".exe"
else:
    EXEC_FILE = APPNAME


PROJECT_DIR = Path(__file__).resolve().parent
DIST_DIR = Path(PROJECT_DIR, "dist")
BUILD_DIR = Path(PROJECT_DIR, "build")
DEFAULT_EXECUTABLE_PATH = Path(DIST_DIR, EXEC_FILE)
OUTPUT_EXECUTABLE_PATH = Path(PROJECT_DIR, EXEC_FILE)


args = [
    "--onefile",
    "--noconfirm",
    "--clean",
    "--console",
    "--noupx",

    "--name",
    APPNAME,

    "--exclude-module",
    "test",

    "--exclude-module",
    "main_helpers.testing",

    "--exclude-module",
    "mkexe",
]


try:
    subprocess.run(["pyinstaller", *args, "main.py"], check=True)
except subprocess.CalledProcessError:
    print("Build failed!")
    raise


shutil.rmtree(BUILD_DIR)
os.remove(APPNAME + ".spec")
shutil.move(DEFAULT_EXECUTABLE_PATH, OUTPUT_EXECUTABLE_PATH)
shutil.rmtree(DIST_DIR)
