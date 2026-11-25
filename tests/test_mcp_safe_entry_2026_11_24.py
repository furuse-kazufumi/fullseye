# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""cwd の ``fullseye/`` が MCP の入口を乗っ取れないこと / MCP safe entry (2026-11-24).

同名 package があるプロジェクトの cwd から実際の ``fullseye-mcp`` console
script を起動し、本物の help が返ることを見る。偽 package は import された
瞬間に終了するので、成功は console script の起動で cwd が先頭にならない実測で
ある。別に、``python -m fullseye.mcp`` が cwd のコピーを選んだ場合は、登録済み
wheel/editable の場所でないことを検出して fail-closed にする。

The test runs the real console script from a cwd with a decoy package, then
checks that a copied package selected by ``-m`` is rejected against install metadata.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
import tomllib
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECOY_MARKER = "cwd decoy fullseye was imported"


def _clean_env() -> dict[str, str]:
    """Measure the normal console entry without injecting the checkout / checkout を子へ渡さない。"""
    env = {key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "PYTHONHOME")}
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _console_script() -> Path:
    """Return ``fullseye-mcp`` installed by packaging / packaging が置いた script を返す。"""
    suffix = ".exe" if os.name == "nt" else ""
    script = Path(sysconfig.get_path("scripts")) / ("fullseye-mcp" + suffix)
    assert script.is_file(), "editable/package install did not create fullseye-mcp: %s" % script
    return script


def _make_decoy(cwd: Path) -> Path:
    """Create an unmistakable cwd decoy package / import されたら分かる偽 package を作る。"""
    package = cwd / "fullseye"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("raise SystemExit(%r)\n" % DECOY_MARKER, encoding="utf-8")
    return package


def _copy_mcp_module_entry(package: Path) -> None:
    """Copy only enough of the module entry to reach the location guard / 入口の location guard までを写す。"""
    shutil.copy2(ROOT / "fullseye" / "__init__.py", package / "__init__.py")
    (package / "mcp").mkdir()
    shutil.copy2(ROOT / "fullseye" / "mcp" / "__main__.py", package / "mcp" / "__main__.py")


def _venv_python(path: Path) -> Path:
    """Create an uninstalled interpreter / fullseye の metadata が無い Python を作る。"""
    venv.EnvBuilder(with_pip=False).create(path)
    return path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _site_packages(venv_dir: Path) -> Path:
    """Return the venv site-packages location / venv の site-packages を返す。"""
    return venv_dir / ("Lib/site-packages" if os.name == "nt" else "lib/python%s.%s/site-packages" % sys.version_info[:2])


def test_project_declares_the_cwd_safe_console_entry_point():
    """Packaging contract for the same wheel/editable console script / packaging の契約。"""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["scripts"]["fullseye-mcp"] == "fullseye.mcp.server:main"


def test_console_script_imports_the_installed_package_not_a_cwd_decoy(tmp_path):
    """The console script returns real help despite ``cwd/fullseye`` / 偽 package を読まない。"""
    _make_decoy(tmp_path)
    done = subprocess.run([str(_console_script()), "--help"], cwd=tmp_path, env=_clean_env(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    seen = done.stdout + done.stderr
    assert done.returncode == 0, seen[-1200:]
    assert "usage: fullseye-mcp" in done.stdout
    assert DECOY_MARKER not in seen


def test_module_entry_refuses_a_cwd_package_not_declared_by_the_install(tmp_path):
    """The ``-m`` location guard rejects an undeclared cwd copy / 理由付きで止める。"""
    package = _make_decoy(tmp_path)
    _copy_mcp_module_entry(package)
    done = subprocess.run([sys.executable, "-m", "fullseye.mcp", "--help"], cwd=tmp_path, env=_clean_env(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert done.returncode != 0
    assert "refusing to start fullseye MCP" in done.stderr
    assert "fullseye MCP の起動を拒否しました" in done.stderr
    assert "pip install -e ." in done.stderr


def test_module_entry_refuses_a_pythonpath_package_not_declared_by_the_install(tmp_path):
    """The ``-m`` guard checks PYTHONPATH too / cwd 外の注入先も allow-list と照合する。"""
    work = tmp_path / "work"
    injected = tmp_path / "injected"
    work.mkdir()
    package = _make_decoy(injected)
    _copy_mcp_module_entry(package)
    env = _clean_env()
    env["PYTHONPATH"] = str(injected)
    done = subprocess.run([sys.executable, "-m", "fullseye.mcp", "--help"], cwd=work, env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert done.returncode != 0
    assert "refusing to start fullseye MCP" in done.stderr
    assert str(package) in done.stderr


def test_module_entry_refuses_a_plain_source_tree_without_distribution_metadata(tmp_path):
    """A source tree without install metadata fails closed / metadata の無い source tree は理由付きで止める。"""
    source = tmp_path / "source"
    package = _make_decoy(source)
    _copy_mcp_module_entry(package)
    python = _venv_python(tmp_path / "without-fullseye-metadata")
    done = subprocess.run([str(python), "-m", "fullseye.mcp", "--help"], cwd=source, env=_clean_env(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert done.returncode != 0
    assert "refusing to start fullseye MCP" in done.stderr
    assert "PEP 610 editable checkout" in done.stderr
    assert "fullseye MCP の起動を拒否しました" in done.stderr


def test_module_entry_accepts_legacy_editable_metadata_that_resolves_the_checkout(tmp_path):
    """Legacy egg-info + easy-install.pth remains allowed / 古い editable の解決済み metadata は許す。"""
    source = tmp_path / "legacy-source"
    package = _make_decoy(source)
    _copy_mcp_module_entry(package)
    egg_info = source / "fullseye.egg-info"
    egg_info.mkdir()
    (egg_info / "PKG-INFO").write_text("Metadata-Version: 2.1\nName: fullseye\nVersion: 0\n", encoding="utf-8")
    venv_dir = tmp_path / "legacy-editable"
    python = _venv_python(venv_dir)
    site_packages = _site_packages(venv_dir)
    (site_packages / "easy-install.pth").write_text(str(source) + "\n", encoding="utf-8")
    work = tmp_path / "work"
    work.mkdir()
    done = subprocess.run([str(python), "-m", "fullseye.mcp", "--help"], cwd=work, env=_clean_env(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    assert "refusing to start fullseye MCP" not in done.stderr
    assert "No module named 'api'" in done.stderr
