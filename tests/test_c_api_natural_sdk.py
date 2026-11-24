"""Consumer-facing source SDK gates / 利用者視点のソース SDK 門。"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

import fullseye
from fullseye import sdk
from fullseye.sdk import __main__ as sdk_cli

ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=True, timeout=600)


def test_sdk_cli_reports_the_active_python_and_a_complete_config():
    """The Config shim binds CMake to the Python that asked for it / Python 環境を固定する。"""
    result = _run([sys.executable, "-m", "fullseye.sdk", "--cmakedir"], cwd=ROOT)
    cmake_dir = Path(result.stdout.strip())
    config = cmake_dir / "fullseyeConfig.cmake"
    assert config.is_file()
    text = config.read_text(encoding="utf-8")
    assert str(Path(sys.executable).resolve()) in text
    assert str(sdk.package_root().parent) in text
    assert _run([sys.executable, "-m", "fullseye.sdk", "--python"], cwd=ROOT).stdout.strip() == sys.executable
    assert Path(_run([sys.executable, "-m", "fullseye.sdk", "--includedir"], cwd=ROOT).stdout.strip()).is_dir()


def test_doctor_reports_a_hidden_pybind11_dependency(monkeypatch, capsys):
    """Doctor names pybind11 instead of pretending a native build can work / 不足を明示する。"""
    monkeypatch.setitem(sys.modules, "pybind11", None)
    assert sdk_cli._doctor() == 1
    captured = capsys.readouterr()
    assert "pybind11" in captured.err and "MISSING:" in captured.err


@pytest.mark.parametrize("example", ("hello_cpp", "hello_c"))
def test_external_consumer_uses_default_runtime_and_matches_python(tmp_path, example):
    """Build C and C++ outside the checkout without an env var / 外部 C/C++ consumer 差分門。"""
    cmake = shutil.which("cmake")
    if cmake is None:
        raise AssertionError("CMake is required for the standard C/C++ SDK gate")
    cmake_dir = _run([sys.executable, "-m", "fullseye.sdk", "--cmakedir"], cwd=ROOT).stdout.strip()
    build = tmp_path / example / "build"
    env = os.environ.copy()
    env.pop("FULLSEYE_PYTHON_ROOT", None)
    _run([cmake, "-S", str(ROOT / "examples" / "c_api" / example), "-B", str(build),
          "-Dfullseye_DIR=" + cmake_dir], cwd=tmp_path, env=env)
    _run([cmake, "--build", str(build)], cwd=tmp_path, env=env)
    executable = build / ("app.exe" if sys.platform == "win32" else "app")
    actual = _run([str(executable)], cwd=tmp_path, env=env).stdout.strip()
    pixels = np.array([[0.0, 0.2, 0.0], [0.2, 1.0, 0.2], [0.0, 0.2, 0.0]])
    expected = float(np.asarray(fullseye.apply(pixels, "gaussian", 0.5, 0.5)).sum())
    fields = dict(part.split("=", 1) for part in actual.split())
    assert fields["result_count"] == "1"
    assert float(fields["output_sum"]) == expected
