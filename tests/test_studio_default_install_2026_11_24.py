"""標準 Studio 導入と初回メニュー登録の回帰試験 / default Studio-install regression tests.

The registration tests pass only temporary Linux-style folders to the real shortcut writer.
They never resolve a desktop, Start menu, registry key, or settings file from this machine.
"""
from __future__ import annotations

import io
import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import imgevolve  # noqa: E402
from fullseye import shortcuts  # noqa: E402
from fullseye import uninstall  # noqa: E402


def _linux_dirs(tmp_path: Path):
    return {"apps": tmp_path / "applications", "icon_dir": tmp_path / "icons", "desktop": tmp_path / "Desktop"}


def _auto(tmp_path: Path, *, env=None, is_tty=True, calls=None, out=None):
    dirs = _linux_dirs(tmp_path)
    ledger = tmp_path / "ledger.json"
    merged_env = {"DISPLAY": ":99", "FULLSEYE_STUDIO_SETTINGS": str(tmp_path / "Studio.conf")}
    merged_env.update(env or {})
    install_fn = shortcuts.install
    if calls is not None:
        def install_fn(**kw):
            calls.append(kw)
            return shortcuts.install(**kw)
    made = shortcuts.auto_register_on_first_command(
        platform="linux", python=sys.executable, dirs=dirs, ledger=ledger, env=merged_env,
        is_tty=is_tty, policy_fn=lambda: False, install_fn=install_fn, out=out,
    )
    return made, dirs, ledger


def test_default_dependencies_ship_studio_and_gui_extra_is_a_compatibility_alias():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = {x.lower() for x in data["project"]["dependencies"]}
    extras = data["project"]["optional-dependencies"]
    assert "pyside6-essentials>=6.5" in deps and "pillow>=13.0" in deps
    assert extras["gui"] == [] and extras["pil"] == []
    assert not any("pyside6" in x.lower() or "pillow" in x.lower() for x in extras["all"])


def test_import_fullseye_does_not_load_qt_in_a_fresh_python_process():
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONUTF8="1", FULLSEYE_NO_SHORTCUTS="1")
    code = ("import fullseye, sys; "
            "assert not any(n == 'PySide6' or n.startswith('PySide6.') for n in sys.modules)")
    run = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr


def test_first_command_registers_once_then_never_recreates_a_deleted_shortcut(tmp_path):
    calls = []
    out = io.StringIO()
    created, dirs, ledger = _auto(tmp_path, calls=calls, out=out)
    desktop = dirs["apps"] / "fullseye-studio.desktop"
    marker = dirs["icon_dir"] / shortcuts.AUTO_SHORTCUT_MARKER
    assert created and desktop.is_file() and marker.is_file() and len(calls) == 1
    assert out.getvalue().strip() == "スタートメニューに Fullseye Studio を登録しました(外す: fullseye-studio --remove-shortcuts)"
    assert shortcuts.auto_register_on_first_command(
        platform="linux", python=sys.executable, dirs=dirs, ledger=ledger,
        env={"DISPLAY": ":99", "FULLSEYE_STUDIO_SETTINGS": str(tmp_path / "Studio.conf")}, is_tty=True,
        policy_fn=lambda: False, install_fn=lambda **kw: pytest.fail("must not install twice"), out=io.StringIO(),
    ) is False
    desktop.unlink()                         # the user removed the menu entry themselves
    assert shortcuts.auto_register_on_first_command(
        platform="linux", python=sys.executable, dirs=dirs, ledger=ledger,
        env={"DISPLAY": ":99", "FULLSEYE_STUDIO_SETTINGS": str(tmp_path / "Studio.conf")}, is_tty=True,
        policy_fn=lambda: False, install_fn=lambda **kw: pytest.fail("must not recreate a deleted shortcut"), out=io.StringIO(),
    ) is False
    assert not desktop.exists() and marker.is_file()


@pytest.mark.parametrize("env,is_tty", [({"FULLSEYE_NO_SHORTCUTS": "1"}, True), ({"CI": "1"}, True), ({}, False)])
def test_auto_registration_is_suppressed_for_opt_out_ci_or_no_terminal(tmp_path, env, is_tty):
    created, dirs, _ledger = _auto(tmp_path, env=env, is_tty=is_tty, calls=[])
    assert not created
    assert not (dirs["apps"] / "fullseye-studio.desktop").exists()
    assert not (dirs["icon_dir"] / shortcuts.AUTO_SHORTCUT_MARKER).exists()


def test_settings_file_can_disable_auto_registration(tmp_path):
    settings = tmp_path / "Studio.conf"
    settings.write_text("[shortcuts]\nauto_register=false\n", encoding="utf-8")
    created, dirs, _ledger = _auto(tmp_path, env={"FULLSEYE_STUDIO_SETTINGS": str(settings)}, calls=[])
    assert not created and not (dirs["apps"] / "fullseye-studio.desktop").exists()


def test_administrator_menu_policy_can_disable_auto_registration(tmp_path):
    dirs = _linux_dirs(tmp_path)
    made = shortcuts.auto_register_on_first_command(
        platform="linux", python=sys.executable, dirs=dirs, ledger=tmp_path / "ledger.json",
        env={"DISPLAY": ":99", "FULLSEYE_STUDIO_SETTINGS": str(tmp_path / "Studio.conf")}, is_tty=True,
        policy_fn=lambda: True, install_fn=lambda **kw: pytest.fail("policy must prevent registration"), out=io.StringIO(),
    )
    assert made is False and not (dirs["apps"] / "fullseye-studio.desktop").exists()


def test_full_uninstall_plan_includes_and_can_remove_the_auto_marker(tmp_path, monkeypatch):
    created, dirs, ledger = _auto(tmp_path, calls=[])
    marker = dirs["icon_dir"] / shortcuts.AUTO_SHORTCUT_MARKER
    assert created and marker.is_file()
    plan = uninstall.collect(ledger=ledger, dirs=dirs, plat="linux", registry=False)
    entry = next(x for x in plan["made"] if x["path"] == str(marker))
    monkeypatch.setattr(shortcuts, "_platform", lambda platform=None: "linux")
    assert uninstall.remove_item(entry, dirs=dirs)
    assert not marker.exists()


def test_fullseye_command_calls_the_auto_registration_hook_but_uninstall_does_not(monkeypatch):
    calls = []
    monkeypatch.setattr(shortcuts, "auto_register_on_first_command", lambda: calls.append(1))
    monkeypatch.setattr(sys, "argv", ["fullseye", "--version"])
    with pytest.raises(SystemExit) as ended:
        imgevolve.main()
    assert ended.value.code == 0 and calls == [1]
    monkeypatch.setattr(sys, "argv", ["fullseye", "setup", "--uninstall", "--dry-run"])
    imgevolve._auto_register_studio_shortcut(sys.argv[1:])
    assert calls == [1]


def test_fullseye_studio_command_calls_the_auto_registration_hook(monkeypatch):
    import studio
    calls = []
    monkeypatch.setattr(shortcuts, "auto_register_on_first_command", lambda: calls.append(1))
    monkeypatch.setattr(shortcuts, "run_cli", lambda *args, **kwargs: 0)
    assert studio.main(["--version"]) == 0
    assert calls == [1]
    assert studio.main(["--remove-shortcuts"]) == 0
    assert calls == [1]
