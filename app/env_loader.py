from __future__ import annotations

import os
import platform
from typing import Iterable


def _read_windows_user_env(name: str) -> str:
    """Read a Windows user-level environment variable from HKCU\\Environment.

    This is a fallback for cases where the variable was added in Windows settings
    but the current terminal process has not been restarted yet.
    """
    if platform.system().lower() != "windows":
        return ""
    try:
        import winreg  # type: ignore[attr-defined]
    except Exception:
        return ""

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
            return str(value).strip()
    except OSError:
        return ""


def get_env_value(name: str, default: str = "", aliases: Iterable[str] | None = None) -> str:
    """Get a config value from process env, then Windows user env registry.

    Priority:
    1. Current process environment, including values loaded by python-dotenv.
    2. Windows HKCU\\Environment user-level variables.
    3. The provided default.

    `aliases` lets you support compatibility names without hard-coding provider keys
    throughout the codebase.
    """
    names = [name]
    if aliases:
        names.extend(alias for alias in aliases if alias and alias not in names)

    for candidate in names:
        value = os.getenv(candidate, "").strip()
        if value:
            return value

    for candidate in names:
        value = _read_windows_user_env(candidate)
        if value:
            return value

    return default


def get_env_int(name: str, default: int) -> int:
    value = get_env_value(name, str(default))
    try:
        return int(value)
    except ValueError:
        return default


def get_env_float(name: str, default: float) -> float:
    value = get_env_value(name, str(default))
    try:
        return float(value)
    except ValueError:
        return default
