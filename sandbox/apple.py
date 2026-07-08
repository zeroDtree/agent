from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from config.sandbox import NetworkPolicy, SandboxProfile
from sandbox.sbpl import build_sbpl

SANDBOX_EXEC = Path("/usr/bin/sandbox-exec")


@dataclass
class SandboxRunResult:
    returncode: int
    stdout: str
    stderr: str


class AppleSandboxRunner:
    def is_available(self) -> bool:
        return SANDBOX_EXEC.is_file()

    def run(
        self,
        command: list[str],
        profile: SandboxProfile,
        network: NetworkPolicy,
        *,
        cwd: Path,
        timeout: int,
    ) -> SandboxRunResult:
        if not self.is_available():
            raise RuntimeError("sandbox-exec is not available on this system")

        sbpl = build_sbpl(profile, network)
        completed = subprocess.run(
            [str(SANDBOX_EXEC), "-p", sbpl, "--", *command],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
        )
        return SandboxRunResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


def is_apple_sandbox_available() -> bool:
    return AppleSandboxRunner().is_available()
