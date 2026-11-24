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


def _config_with_runtime_root(directory: Path, runtime_root: Path) -> Path:
    """Make a consumer Config shim for a selected root / 選んだ root 用 consumer Config。"""
    source, include = sdk.payload_paths()
    config = sdk.package_root() / "sdk" / "cmake" / "fullseyeConfig.cmake"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "fullseyeConfig.cmake").write_text("\n".join((
        "set(fullseye_PYTHON_EXECUTABLE %s)" % sdk_cli._bracket(str(Path(sys.executable).resolve())),
        "set(fullseye_PYTHON_RUNTIME_ROOT %s)" % sdk_cli._bracket(str(runtime_root)),
        "set(fullseye_SDK_SOURCE_FILE %s)" % sdk_cli._bracket(str(source.resolve())),
        "set(fullseye_SDK_INCLUDE_DIR %s)" % sdk_cli._bracket(str(include.resolve())),
        "include(%s)" % sdk_cli._bracket(str(config.resolve())),
        "",
    )), encoding="utf-8", newline="\n")
    return directory


def _runtime_env_without_python_path(env: dict[str, str]) -> dict[str, str]:
    """Keep Windows system DLL lookup only / Windows の system DLL 検索だけを残す。"""
    if sys.platform != "win32":
        return env
    isolated = env.copy()
    isolated["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
    return isolated


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
    run_env = _runtime_env_without_python_path(env)
    if sys.platform == "win32":
        dll = executable.parent / ("python%d%d.dll" % sys.version_info[:2])
        assert dll.is_file(), "CMake must deploy CPython beside the consumer executable"
    actual = _run([str(executable)], cwd=tmp_path, env=run_env).stdout.strip()
    pixels = np.array([[0.0, 0.2, 0.0], [0.2, 1.0, 0.2], [0.0, 0.2, 0.0]])
    expected = float(np.asarray(fullseye.apply(pixels, "gaussian", 0.5, 0.5)).sum())
    fields = dict(part.split("=", 1) for part in actual.split())
    assert fields["result_count"] == "1"
    assert float(fields["output_sum"]) == expected


def test_external_consumer_uses_a_non_ascii_runtime_root(tmp_path):
    """The Config passes a Japanese UTF-8 path byte-for-byte / 日本語・空白 path の門。"""
    cmake = shutil.which("cmake")
    if cmake is None:
        raise AssertionError("CMake is required for the standard C/C++ SDK gate")
    unicode_root = tmp_path / "日本語 runtime root"
    if sys.platform == "win32":
        created = subprocess.run(["cmd", "/c", "mklink", "/J", str(unicode_root), str(ROOT)],
                                 text=True, capture_output=True, timeout=30)
        assert created.returncode == 0, created.stderr
    else:
        unicode_root.symlink_to(ROOT, target_is_directory=True)
    cmake_dir = _config_with_runtime_root(tmp_path / "unicode-config", unicode_root)
    build = tmp_path / "unicode-consumer" / "build"
    env = os.environ.copy()
    env.pop("FULLSEYE_PYTHON_ROOT", None)
    _run([cmake, "-S", str(ROOT / "examples" / "c_api" / "hello_cpp"), "-B", str(build),
          "-Dfullseye_DIR=" + str(cmake_dir)], cwd=tmp_path, env=env)
    _run([cmake, "--build", str(build)], cwd=tmp_path, env=env)
    executable = build / ("app.exe" if sys.platform == "win32" else "app")
    assert "result_count=1" in _run([str(executable)], cwd=tmp_path,
                                      env=_runtime_env_without_python_path(env)).stdout


def test_moved_runtime_root_fails_closed_with_a_reconfigure_instruction(tmp_path):
    """A vanished Config runtime reports FS_E_NO_PYTHON / 移動済み venv の復旧手順。"""
    cmake = shutil.which("cmake")
    if cmake is None:
        raise AssertionError("CMake is required for the standard C/C++ SDK gate")
    cmake_dir = _config_with_runtime_root(tmp_path / "moved-config", tmp_path / "moved environment")
    build = tmp_path / "moved-consumer" / "build"
    env = os.environ.copy()
    env.pop("FULLSEYE_PYTHON_ROOT", None)
    _run([cmake, "-S", str(ROOT / "examples" / "c_api" / "hello_cpp"), "-B", str(build),
          "-Dfullseye_DIR=" + str(cmake_dir)], cwd=tmp_path, env=env)
    _run([cmake, "--build", str(build)], cwd=tmp_path, env=env)
    executable = build / ("app.exe" if sys.platform == "win32" else "app")
    result = subprocess.run([str(executable)], cwd=tmp_path,
                            env=_runtime_env_without_python_path(env), text=True,
                            capture_output=True, check=False, timeout=120)
    assert result.returncode != 0
    assert "FS_E_NO_PYTHON" in result.stderr
    assert "no longer exists" in result.stderr and "Re-run CMake" in result.stderr
