# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Windows の差し替え再現: doctor と起動エラーが事実・修復・詳細を同時に出すことを確かめる。"""
from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fullseye import doctor, startup_errors  # noqa: E402


def _finding(report, ident):
    return next(item for item in report["findings"] if item["id"] == ident)


def test_cp932_console_has_a_measured_cause_and_a_pasteable_repair(monkeypatch):
    class Cp932:
        encoding = "cp932"
    monkeypatch.setattr(doctor.sys, "stdout", Cp932())
    report = doctor.collect(env={"PATH": ""}, executable=r"C:\\Python311\\python.exe",
                            platform="win32", include_sdk=False)
    item = _finding(report, "console_encoding")
    shown = doctor._present_finding(item, "en")
    assert item["status"] == "warning"
    assert "cp932" in item["checked"] and "chcp 65001" in shown["commands"][0]["powershell"]


def test_japanese_and_space_path_is_reported_without_rejecting_it():
    report = doctor.collect(env={"PATH": ""}, executable=r"C:\\Users\\山田 太郎\\Python\\python.exe",
                            platform="win32", include_sdk=False)
    item = _finding(report, "unicode_space_path")
    shown = doctor._present_finding(item, "ja")
    assert item["status"] == "info"
    assert "山田 太郎" in shown["checked"] and "venv" in shown["commands"][0]["powershell"]
    assert report["setup_environment"]["status"] in {"ok", "warning"}


def test_missing_qt_plugin_path_is_a_safe_fix_but_pipe_cannot_apply_it(monkeypatch):
    bad = str(ROOT / "does-not-exist-qt-plugins")
    report = doctor.collect(env={"PATH": "", "QT_PLUGIN_PATH": bad}, executable=sys.executable,
                            include_sdk=False)
    item = _finding(report, "native_dll")
    assert item["status"] == "warning" and item["fixable"]
    monkeypatch.setenv("QT_PLUGIN_PATH", bad)
    out = io.StringIO()
    rc = doctor.main(["--lang", "en", "--fix"], collect_fn=lambda: report, is_tty=False, out=out)
    assert rc == 1 and os.environ["QT_PLUGIN_PATH"] == bad
    assert "made no changes" in out.getvalue()


def test_qt_fix_shows_plan_then_requires_confirmation_without_touching_windows(monkeypatch):
    report = doctor.collect(env={"PATH": "", "QT_PLUGIN_PATH": "C:\\missing"}, executable=sys.executable,
                            include_sdk=False)
    item = _finding(report, "native_dll")
    if not item["fixable"]:
        pytest.skip("persistent QT_PLUGIN_PATH repair is Windows-only")
    applied = []
    out = io.StringIO()
    rc = doctor.main(["--lang", "en", "--fix"], collect_fn=lambda: report, is_tty=True, input_fn=lambda _: "y",
                     apply_fn=lambda plan: applied.append(list(plan)) or ["test change"], out=out)
    assert rc == 0 and applied and "Planned change" in out.getvalue() and "Changed: test change" in out.getvalue()


def test_python_missing_from_path_has_cause_and_explicit_python_repair():
    report = doctor.collect(env={"PATH": ""}, executable=r"C:\\Python311\\python.exe",
                            platform="win32", include_sdk=False)
    item = _finding(report, "python_path")
    shown = doctor._present_finding(item, "en")
    assert item["status"] == "warning"
    assert "current interpreter explicitly" in item["fix"]
    assert "-m fullseye doctor" in shown["commands"][0]["powershell"]


def test_dll_import_error_keeps_original_exception_and_doctor_route():
    text = startup_errors.explain(OSError("DLL load failed while importing QtCore"), "Studio", lang="en")
    assert "native DLL" in text and "fullseye[gui]" in text
    assert "fullseye doctor" in text and "Original exception: OSError" in text


def test_cli_studio_and_mcp_startup_errors_share_the_japanese_kind_explanation():
    for entrypoint in ("CLI", "Studio", "MCP server"):
        text = startup_errors.explain(ImportError("No module named 'PIL'"), entrypoint, lang="ja")
        assert "何が起きたか: ImportError" in text
        assert "考えられる理由: Python パッケージが不足" in text
        assert "対処: py -3.11 -m pip install --upgrade fullseye" in text
        assert "元の例外: ImportError" in text


def test_cli_entrypoint_turns_import_failure_into_helpful_error(monkeypatch, capsys):
    import imgevolve

    def fail():
        raise ImportError("No module named 'PIL'")

    monkeypatch.setattr(startup_errors, "_detect_lang", lambda override=None: "ja")
    monkeypatch.setattr(imgevolve, "_main", fail)
    assert imgevolve.main() == 1
    err = capsys.readouterr().err
    assert "別の Python" in err and "fullseye doctor" in err and "ImportError" in err


def test_doctor_subcommand_is_visible_and_json_is_machine_readable(monkeypatch, capsys):
    import imgevolve
    monkeypatch.setattr(sys, "argv", ["fullseye", "--help"])
    with pytest.raises(SystemExit):
        imgevolve.main()
    assert "doctor" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["fullseye", "doctor", "--lang", "ja", "--json"])
    assert imgevolve.main() in (0, 1)
    text = capsys.readouterr().out
    assert '"findings"' in text and '"summary"' in text and "問題" in text


def test_doctor_japanese_output_has_a_measured_summary_and_single_windows_backslashes():
    report = doctor.collect(env={"PATH": ""}, executable=r"C:\Program Files\Python311\python.exe",
                            platform="win32", include_sdk=False)
    out = io.StringIO()
    doctor.main(["--lang", "ja"], collect_fn=lambda: report, out=out)
    text = out.getvalue()
    assert text.startswith("問題 3 件・確認のお願い 7 件・OK 7 件。まず [ACTION] から。\n")
    assert "コンソールの文字エンコーディング" in text
    assert '& "C:\\Program Files\\Python311\\python.exe" -m venv C:\\venvs\\fullseye' in text
    assert r"C:\\venvs\\fullseye" not in text


def _bash():
    if sys.platform == "win32":
        candidates = [Path(os.environ.get("ProgramFiles", r"C:\\Program Files")) / "Git" / "bin" / "bash.exe",
                      Path(os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)")) / "Git" / "bin" / "bash.exe"]
        return next((str(path) for path in candidates if path.is_file()), None)
    return shutil.which("bash")


def test_every_repair_command_is_pasteable_power_shell_and_bash_syntax():
    rendered = [doctor._render_command(command) for commands in doctor._repair_commands(r"C:\Program Files\Python311\python.exe").values()
                for command in commands]
    assert rendered
    bash = _bash()
    assert bash, "bash is required to validate the commands advertised to bash users"
    for command in rendered:
        parsed = subprocess.run([bash, "-n", "-c", command["bash"]], capture_output=True, text=True)
        assert parsed.returncode == 0, (command["bash"], parsed.stderr)
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if powershell is None:
        pytest.skip("PowerShell is unavailable on this OS; Windows CI performs ScriptBlock parsing")
    parser = "$source = [Console]::In.ReadToEnd(); [ScriptBlock]::Create($source) | Out-Null"
    for command in rendered:
        parsed = subprocess.run([powershell, "-NoProfile", "-NonInteractive", "-Command", parser],
                                input=command["powershell"], capture_output=True, text=True)
        assert parsed.returncode == 0, (command["powershell"], parsed.stderr)


def test_troubleshooting_tables_and_doctor_items_cannot_drift():
    expected = set(doctor.TROUBLESHOOTING_IDS)
    for name in ("TROUBLESHOOTING.md", "TROUBLESHOOTING.en.md"):
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        documented = set(re.findall(r"<!-- doctor: ([a-z_]+) -->", text))
        assert documented == expected, (name, documented ^ expected)
        for ident in expected:
            assert "`%s`" % ident in text
    japanese = re.sub(r"[`*]", "", (ROOT / "docs" / "TROUBLESHOOTING.md").read_text(encoding="utf-8"))
    for ident, (_what, fix) in doctor._JA_TEXT.items():
        assert fix in japanese, (ident, fix)
    english = re.sub(r"[`*]", "", (ROOT / "docs" / "TROUBLESHOOTING.en.md").read_text(encoding="utf-8"))
    for ident, fix in doctor._EN_FIX.items():
        assert fix in english, (ident, fix)


def test_mcp_entrypoint_uses_stderr_friendly_startup_reporting():
    source = (ROOT / "fullseye" / "mcp" / "__main__.py").read_text(encoding="utf-8")
    assert "startup_errors.report(exc, \"MCP server\")" in source
    studio = (ROOT / "studio.py").read_text(encoding="utf-8")
    cli = (ROOT / "imgevolve.py").read_text(encoding="utf-8")
    assert "startup_errors.report(e, \"Studio\")" in studio
    assert "startup_errors.report(exc, \"CLI\")" in cli
