from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from config.sandbox import NetworkPolicy, SandboxProfile


@dataclass
class SandboxRunResult:
    returncode: int
    stdout: str
    stderr: str


def require_bwrap() -> str:
    path = shutil.which("bwrap")
    if path is None:
        raise RuntimeError("bubblewrap (bwrap) is not available on this system")
    return path


class BubblewrapRunner:
    def is_available(self) -> bool:
        try:
            require_bwrap()
            return True
        except RuntimeError:
            return False

    def run(
        self,
        command: list[str],
        profile: SandboxProfile,
        network: NetworkPolicy,
        *,
        cwd: Path,
        timeout: int,
    ) -> SandboxRunResult:
        bwrap = require_bwrap()
        args = [
            bwrap,
            "--die-with-parent",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
        ]

        if not network.enabled:
            args.append("--unshare-net")

        mounted: set[Path] = set()
        for read_path in profile.read_paths:
            resolved = read_path.resolve()
            if resolved in mounted:
                continue
            mounted.add(resolved)
            mount_point = f"/workspace_{len(mounted)}"
            if profile.readonly or resolved not in profile.write_paths:
                args.extend(["--ro-bind", str(resolved), mount_point])
            else:
                args.extend(["--bind", str(resolved), mount_point])

        for write_path in profile.write_paths:
            resolved = write_path.resolve()
            if resolved in mounted:
                continue
            mounted.add(resolved)
            mount_point = f"/workspace_{len(mounted)}"
            args.extend(["--bind", str(resolved), mount_point])

        workspace = cwd.resolve()
        workspace_mount = None
        for index, read_path in enumerate(profile.read_paths, start=1):
            if read_path.resolve() == workspace:
                workspace_mount = f"/workspace_{index}"
                break
        if workspace_mount is None and mounted:
            workspace_mount = "/workspace_1"
        if workspace_mount is None:
            args.extend(["--ro-bind", str(workspace), "/workspace"])
            workspace_mount = "/workspace"

        args.extend(["--chdir", workspace_mount, "--", *command])

        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return SandboxRunResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )
