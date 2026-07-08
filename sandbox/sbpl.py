from __future__ import annotations

import sys
from pathlib import Path

from config.sandbox import NetworkPolicy, SandboxProfile

_SYSTEM_READ_PREFIXES = (
    "/usr",
    "/bin",
    "/sbin",
    "/private/tmp",
    "/var",
    "/etc",
    "/opt",
    "/Library",
    "/System",
    "/Applications",
    "/dev",
)


def _python_prefixes() -> tuple[str, ...]:
    prefixes = {sys.base_prefix, sys.prefix}
    return tuple(str(Path(prefix).resolve()) for prefix in prefixes if prefix)


def _sbpl_quote(path: str) -> str:
    return path.replace("\\", "\\\\").replace('"', '\\"')


def build_sbpl(profile: SandboxProfile, network: NetworkPolicy) -> str:
    lines = [
        "(version 1)",
        "(allow default)",
    ]

    if profile.readonly or not profile.write_paths:
        lines.append("(deny file-write*)")

    for write_path in profile.write_paths:
        lines.append(f'(allow file-write* (subpath "{_sbpl_quote(str(write_path))}"))')

    lines.append('(allow file-write* (literal "/dev/null"))')

    for read_path in profile.read_paths:
        lines.append(f'(allow file-read* (subpath "{_sbpl_quote(str(read_path))}"))')

    for deny_path in profile.deny_read_paths:
        lines.append(f'(deny file-read* (subpath "{_sbpl_quote(str(deny_path))}"))')
        lines.append(f'(deny file-write* (subpath "{_sbpl_quote(str(deny_path))}"))')

    for prefix in _SYSTEM_READ_PREFIXES + _python_prefixes():
        lines.append(f'(allow file-read* (subpath "{_sbpl_quote(prefix)}"))')

    if network.enabled:
        lines.append("(allow network*)")
    else:
        lines.append("(deny network*)")
        lines.append("(allow network* (local unix-socket))")

    return "\n".join(lines)
