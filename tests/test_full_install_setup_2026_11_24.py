"""2026-11-24 の「可能な限り全部入り」setup を検査する / verify it without writing to the real machine."""
from __future__ import annotations

import io
import json
import subprocess
import sys

from fullseye import setup_cmd


def _info(*, installed: bool, skill: bool = False, mcp: bool = False, claude: bool = False):
    probes = {name: {"installed": installed, "version": "1.0" if installed else ""}
              for name, *_ in setup_cmd.PROBES}
    return {"python": "3.11.0", "executable": sys.executable, "venv": False, "fullseye": "1.2.0",
            "probes": probes, "qt": "ok", "skill": skill, "mcp": mcp, "claude": claude,
            "shortcut": False}


def _call(argv, *, info, run=None, mcp=None, cuda=False):
    pip_calls, mcp_calls = [], []
    out = io.StringIO()
    rc = setup_cmd.main(
        argv, info=info, is_tty=False, out=out, cuda_fn=lambda: cuda,
        run_fn=run or (lambda cmd: (pip_calls.append(cmd), 0)[1]),
        mcp_fn=mcp or (lambda cmd: (mcp_calls.append(cmd), 0)[1]),
        shortcuts_fn=lambda desktop: ["menu"], rag_fn=lambda: "skill",
        launch_fn=lambda: (_ for _ in ()).throw(AssertionError("--yes must not open Studio")),
    )
    return rc, out.getvalue(), pip_calls, mcp_calls


def test_dry_run_lists_every_group_and_cuda_skip_without_mutating():
    rc, out, pips, mcps = _call(["--yes", "--dry-run", "--lang", "en"], info=_info(installed=False))
    assert rc == 0 and not pips and not mcps
    assert "opencv" in out and "wavelets" in out and "handpose" in out and "e57" in out
    assert "skipped the GPU extra" in out
    assert "GPL-3.0-or-later" in out and "--include export-verify" in out
    assert "nothing was changed" in out


def test_one_dependency_failure_does_not_stop_the_other_groups_and_is_tabled():
    seen = []

    def run(cmd):
        seen.append(cmd)
        return 23 if any("opencv-python" in part for part in cmd) else 0

    rc, out, _pips, _mcps = _call(["--yes", "--lang", "en"], info=_info(installed=False), run=run, cuda=True)
    assert rc == 1 and len(seen) == len(setup_cmd.FULL_SETUP_GROUPS)
    assert "[Installation results]" in out and "opencv" in out and "failed" in out
    assert "handpose" in out and "installed" in out


def test_gpl_export_verifier_is_excluded_by_default_and_requires_explicit_include():
    info = _info(installed=False)
    default_groups = setup_cmd.planned_dependency_groups(info, has_cuda=False)
    explicit_groups = setup_cmd.planned_dependency_groups(info, has_cuda=False, include=["export-verify"])
    assert "export-verify" not in {group[0] for group in default_groups}
    assert "export-verify" in {group[0] for group in explicit_groups}
    assert setup_cmd.requirements_for(["export-verify"])[-1].startswith("plyfile>=1.0")


def test_claude_present_registers_mcp_through_an_injected_command_only(monkeypatch):
    monkeypatch.setattr(setup_cmd, "mcp_add_command", lambda: ["claude", "mcp", "add", "fullseye", "--", "safe"])
    rc, out, pips, mcps = _call(["--yes", "--lang", "en"], info=_info(installed=True, claude=True))
    assert rc == 0 and not pips
    assert mcps == [["claude", "mcp", "add", "fullseye", "--", "safe"]]
    assert "Claude Code was found" in out and "registered MCP" in out


def test_mcp_command_uses_safe_module_fallback_when_no_console_script(monkeypatch):
    monkeypatch.setattr(setup_cmd, "_path_executable", lambda name: "claude.exe" if name == "claude" else None)
    monkeypatch.setattr(setup_cmd, "_has_fullseye_mcp_script", lambda: False)
    cmd = setup_cmd.mcp_add_command()
    assert cmd[:5] == ["claude.exe", "mcp", "add", "fullseye", "--"]
    assert cmd[-3:] == ["-P", "-m", "fullseye.mcp"]


def test_first_run_hint_is_a_single_explicit_command():
    assert setup_cmd.full_install_hint("en", _info(installed=False)) == "fullseye setup --yes"
    assert setup_cmd.full_install_hint("ja", _info(installed=False)) == "fullseye setup --yes"


def test_import_fullseye_does_not_eagerly_load_the_large_optional_runtimes():
    code = "import json,sys,fullseye; print(json.dumps(sorted(sys.modules)))"
    got = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert got.returncode == 0, got.stderr
    loaded = set(json.loads(got.stdout))
    assert not {"torch", "cupy", "mitsuba", "mediapipe", "PySide6"} & loaded
