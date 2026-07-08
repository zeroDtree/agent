from __future__ import annotations

from pathlib import Path

import pytest

from zdt_agent.config.config_class import GraphConfig, WorkConfig
from zdt_agent.config.sandbox import NetworkPolicy, SandboxProfile, WorkMode, resolve_path_layout
from zdt_agent.sandbox.sbpl import build_sbpl
from zdt_agent.tools.capability import MODE_CAPS, ToolCapability, capability_allowed_in_mode
from zdt_agent.tools.path_policy import PathPolicyError, resolve_plan_path, resolve_workspace_path


def test_mode_caps_matrix():
    assert ToolCapability.SHELL_RW not in MODE_CAPS[WorkMode.RO]
    assert ToolCapability.RW in MODE_CAPS[WorkMode.SW]
    assert ToolCapability.SHELL_RO in MODE_CAPS[WorkMode.SW]
    assert ToolCapability.RW_PLAN in MODE_CAPS[WorkMode.PL]
    assert capability_allowed_in_mode(ToolCapability.SHELL_RW, WorkMode.AW)


def test_workspace_path_escape(tmp_path: Path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    with pytest.raises(PathPolicyError):
        resolve_workspace_path(workspace, "../outside.txt")


def test_plan_path_uses_basename_only(tmp_path: Path):
    plan_dir = tmp_path / "plans"
    plan_dir.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("secret")
    resolved = resolve_plan_path(plan_dir, "../outside.md")
    assert resolved == (plan_dir / "outside.md").resolve()
    assert resolved != outside.resolve()


def test_build_sbpl_readonly_denies_writes_and_network():
    profile = SandboxProfile(
        readonly=True,
        read_paths=(Path("/tmp/project"),),
        write_paths=(),
        deny_read_paths=(Path("/tmp/project/.env"),),
    )
    network = NetworkPolicy(enabled=False)
    sbpl = build_sbpl(profile, network)
    assert "(deny file-write*)" in sbpl
    assert "(deny network*)" in sbpl
    assert '"/tmp/project/.env"' in sbpl


def test_build_sbpl_rw_allows_writes_when_network_enabled():
    profile = SandboxProfile(
        readonly=False,
        read_paths=(Path("/tmp/project"),),
        write_paths=(Path("/tmp/project"),),
        deny_read_paths=(),
    )
    network = NetworkPolicy(enabled=True)
    sbpl = build_sbpl(profile, network)
    assert "(allow network*)" in sbpl
    assert '(allow file-write* (subpath "/tmp/project"))' in sbpl


def test_filter_tools_for_mode_filters_write_tools():
    from zdt_agent.tools import build_tool_catalog, filter_tools_for_mode

    work_config = WorkConfig(work_mode=WorkMode.RO)
    graph_config = GraphConfig()
    tool_catalog = build_tool_catalog(work_config, graph_config)
    tools = filter_tools_for_mode(tool_catalog, work_config)
    names = {tool.name for tool in tools}
    assert "read_file" in names
    assert "write_file" not in names
    assert "run_shell" not in names
    assert "run_shell_readonly" in names


def test_resolve_path_layout_includes_plan_dir(tmp_path: Path):
    layout = resolve_path_layout(
        tmp_path,
        plan_directory=".agent/plans",
        thread_id="abc",
        deny_read_globs=(".env",),
    )
    assert layout.plan_dir == (tmp_path / ".agent/plans/abc").resolve()


def test_apply_plan_patch_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from zdt_agent.tools.plan import get_plan_tools

    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.chdir(workspace)

    work_config = WorkConfig(working_directory=str(workspace))
    graph_config = GraphConfig(thread_id="test-thread")
    tools = {tool.name: tool for tool in get_plan_tools(work_config, graph_config)}

    write_result = tools["write_plan"].invoke({"filename": "roadmap", "content": "step one\nstep two\n"})
    assert write_result.startswith("ok:")

    patch_result = tools["apply_plan_patch"].invoke(
        {"filename": "roadmap.md", "old_text": "step two", "new_text": "step two (revised)"}
    )
    assert patch_result == "ok: patched plan roadmap.md"
    assert tools["read_plan"].invoke({"filename": "roadmap"}) == "step one\nstep two (revised)\n"


def test_apply_plan_patch_old_text_not_found(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from zdt_agent.tools.plan import get_plan_tools

    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.chdir(workspace)

    work_config = WorkConfig(working_directory=str(workspace))
    graph_config = GraphConfig(thread_id="test-thread")
    tools = {tool.name: tool for tool in get_plan_tools(work_config, graph_config)}

    tools["write_plan"].invoke({"filename": "roadmap.md", "content": "step one\n"})
    patch_result = tools["apply_plan_patch"].invoke(
        {"filename": "roadmap.md", "old_text": "missing", "new_text": "replacement"}
    )
    assert patch_result == "error: old_text not found in plan file"


def test_plan_tools_follow_thread_id_change(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from zdt_agent.tools.plan import get_plan_tools

    workspace = tmp_path / "project"
    workspace.mkdir()
    monkeypatch.chdir(workspace)

    work_config = WorkConfig(working_directory=str(workspace))
    graph_config = GraphConfig(thread_id="a")
    tools = {tool.name: tool for tool in get_plan_tools(work_config, graph_config)}

    plan_dir_a = workspace / ".agent" / "plans" / "a"
    plan_dir_b = workspace / ".agent" / "plans" / "b"

    assert tools["write_plan"].invoke({"filename": "first", "content": "plan a\n"}).startswith("ok:")
    assert (plan_dir_a / "first.md").read_text(encoding="utf-8") == "plan a\n"

    graph_config.thread_id = "b"
    assert tools["write_plan"].invoke({"filename": "second", "content": "plan b\n"}).startswith("ok:")
    assert (plan_dir_b / "second.md").read_text(encoding="utf-8") == "plan b\n"
    assert (plan_dir_a / "first.md").read_text(encoding="utf-8") == "plan a\n"
