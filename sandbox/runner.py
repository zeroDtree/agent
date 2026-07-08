from __future__ import annotations

import sys
from pathlib import Path
from typing import Protocol

from config.sandbox import NetworkPolicy, SandboxProfile
from sandbox.apple import AppleSandboxRunner, SandboxRunResult
from sandbox.bubblewrap import BubblewrapRunner


class SandboxRunner(Protocol):
    def run(
        self,
        command: list[str],
        profile: SandboxProfile,
        network: NetworkPolicy,
        *,
        cwd: Path,
        timeout: int,
    ) -> SandboxRunResult: ...


def get_sandbox_runner() -> SandboxRunner:
    if sys.platform == "darwin":
        runner = AppleSandboxRunner()
        if runner.is_available():
            return runner
        raise RuntimeError("Apple sandbox-exec is required on macOS but is not available")

    if sys.platform.startswith("linux"):
        runner = BubblewrapRunner()
        if runner.is_available():
            return runner
        raise RuntimeError("bubblewrap (bwrap) is required on Linux but is not available")

    raise RuntimeError(f"No sandbox runner available for platform: {sys.platform}")


__all__ = [
    "SandboxRunner",
    "SandboxRunResult",
    "get_sandbox_runner",
    "AppleSandboxRunner",
    "BubblewrapRunner",
]
