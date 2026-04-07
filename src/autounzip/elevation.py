from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path


def is_running_as_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_as_admin() -> bool:
    executable, parameters = _build_launch_command()
    working_directory = str(Path(executable).resolve().parent)
    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        parameters,
        working_directory,
        1,
    )
    return result > 32


def _build_launch_command() -> tuple[str, str]:
    if getattr(sys, "frozen", False):
        return sys.executable, subprocess.list2cmdline(sys.argv[1:])

    main_script = Path(__file__).resolve().with_name("main.py")
    args = [str(main_script), *sys.argv[1:]]
    return sys.executable, subprocess.list2cmdline(args)
