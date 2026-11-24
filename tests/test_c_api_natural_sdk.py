"""Consumer-facing source SDK gates / 利用者視点のソース SDK 門。"""
from __future__ import annotations

import os
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

import fslib
import fullseye
from fullseye import sdk
from fullseye.sdk import __main__ as sdk_cli

ROOT = Path(__file__).resolve().parents[1]


def _run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=False, timeout=600)
    if result.returncode:
        raise AssertionError("consumer command failed (exit %d): %r\nstdout:\n%s\nstderr:\n%s" %
                             (result.returncode, args, result.stdout, result.stderr))
    return result


def _config_with_runtime_root(directory: Path, runtime_root: Path) -> Path:
    """Make a consumer Config shim for a selected root / 選んだ root 用 consumer Config。"""
    source, include = sdk.payload_paths()
    config = sdk.package_root() / "sdk" / "cmake" / "fullseyeConfig.cmake"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "fullseyeConfig.cmake").write_text("\n".join((
        "set(fullseye_PYTHON_EXECUTABLE %s)" % sdk_cli._bracket(str(Path(sys.executable).resolve())),
        "set(fullseye_PYTHON_RUNTIME_ROOT %s)" % sdk_cli._bracket(str(runtime_root)),
        "set(fullseye_PYTHON_HOME %s)" % sdk_cli._bracket(str(Path(sys.prefix).resolve())),
        "set(fullseye_SDK_ABI_VERSION %s)" % sdk_cli._bracket(sdk.abi_version()),
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
    """The Config records build inputs but never bakes a runtime root / build 入力だけを記録する。"""
    result = _run([sys.executable, "-m", "fullseye.sdk", "--cmakedir"], cwd=ROOT)
    cmake_dir = Path(result.stdout.strip())
    config = cmake_dir / "fullseyeConfig.cmake"
    assert config.is_file()
    text = config.read_text(encoding="utf-8")
    assert str(Path(sys.executable).resolve()) in text
    assert str(sdk.package_root().parent) in text
    assert "fullseye_PYTHON_HOME" in text
    assert sdk.abi_version() in text
    assert _run([sys.executable, "-m", "fullseye.sdk", "--python"], cwd=ROOT).stdout.strip() == sys.executable
    assert Path(_run([sys.executable, "-m", "fullseye.sdk", "--includedir"], cwd=ROOT).stdout.strip()).is_dir()


def test_relink_rewrites_a_runtime_manifest_without_running_cmake(tmp_path):
    """Relink updates all portable manifest facts / relink は再 configure なしで manifest を更新する。"""
    target = tmp_path / "app"
    target.mkdir()
    manifest = target / "fullseye_runtime.json"
    assert _run([sys.executable, "-m", "fullseye.sdk", "relink", str(target)], cwd=ROOT).stdout.strip() == str(manifest)
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["python_executable"] == str(Path(sys.executable).resolve())
    assert data["runtime_root"] == str(sdk.package_root().parent)
    assert data["sdk_abi_version"] == sdk.abi_version()
    assert data["created_at"].endswith("Z")
    assert _run([sys.executable, "-m", "fullseye.sdk", "relink", str(manifest)], cwd=ROOT).returncode == 0


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
    manifest = build / "fullseye_runtime.json"
    recorded = json.loads(manifest.read_text(encoding="utf-8"))
    assert recorded["runtime_root"] == str(sdk.package_root().parent)
    assert recorded["sdk_abi_version"] == sdk.abi_version()
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


def test_cpp_saved_pipeline_reloads_replaced_studio_json_without_rebuilding(tmp_path):
    """The same executable follows a replacement Studio save / JSON 差し替えで答えが変わる門。"""
    cmake = shutil.which("cmake")
    if cmake is None:
        raise AssertionError("CMake is required for the standard C/C++ SDK gate")
    cmake_dir = _run([sys.executable, "-m", "fullseye.sdk", "--cmakedir"], cwd=ROOT).stdout.strip()
    build = tmp_path / "hello-pipeline" / "build"
    env = os.environ.copy()
    env.pop("FULLSEYE_PYTHON_ROOT", None)
    _run([cmake, "-S", str(ROOT / "examples" / "c_api" / "hello_pipeline"), "-B", str(build),
          "-Dfullseye_DIR=" + cmake_dir], cwd=tmp_path, env=env)
    _run([cmake, "--build", str(build)], cwd=tmp_path, env=env)
    executable = build / ("app.exe" if sys.platform == "win32" else "app")
    pipeline_path = build / "inspect.json"
    pixels = np.array([[0.0, 0.2, 0.0], [0.2, 1.0, 0.2], [0.0, 0.2, 0.0]], dtype=np.float64)

    def run_same_binary() -> tuple[dict[str, str], int]:
        text = _run([str(executable)], cwd=build, env=_runtime_env_without_python_path(env)).stdout.strip()
        fields = dict(part.split("=", 1) for part in text.split())
        expected = fullseye.load_pipeline(pipeline_path).run(pixels.copy())
        return fields, len(fslib.Region(np.asarray(expected) > 0.5).runs())

    first, first_python = run_same_binary()
    assert first["input"] == "image" and first["output"] == "result"
    assert int(first["run_count"]) == first_python
    document = json.loads(pipeline_path.read_text(encoding="utf-8"))
    document["stages"][0][1] = 0.1
    pipeline_path.write_text(json.dumps(document), encoding="utf-8")
    second, second_python = run_same_binary()
    assert int(second["run_count"]) == second_python
    assert second["run_count"] != first["run_count"]


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
    if sys.platform != "win32":
        # The runtime root must remain UTF-8 even when a service starts under
        # the portable POSIX C locale. / POSIX C locale でも UTF-8 root を保つ。
        env["LC_ALL"] = "C"
        env["LANG"] = "C"
    _run([cmake, "-S", str(ROOT / "examples" / "c_api" / "hello_cpp"), "-B", str(build),
          "-Dfullseye_DIR=" + str(cmake_dir)], cwd=tmp_path, env=env)
    _run([cmake, "--build", str(build)], cwd=tmp_path, env=env)
    executable = build / ("app.exe" if sys.platform == "win32" else "app")
    assert "result_count=1" in _run([str(executable)], cwd=tmp_path,
                                      env=_runtime_env_without_python_path(env)).stdout


def test_moved_runtime_root_is_repaired_by_relink_without_rebuilding(tmp_path):
    """A moved venv is repaired by relink alone / 移動済み venv は relink だけで直る。"""
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
    manifest = build / "fullseye_runtime.json"
    assert json.loads(manifest.read_text(encoding="utf-8"))["runtime_root"] != str(sdk.package_root().parent)
    # This changes only the sidecar: no CMake configure/build invocation follows.
    _run([sys.executable, "-m", "fullseye.sdk", "relink", str(build)], cwd=ROOT)
    assert json.loads(manifest.read_text(encoding="utf-8"))["runtime_root"] == str(sdk.package_root().parent)
    assert "result_count=1" in _run([str(executable)], cwd=tmp_path,
                                      env=_runtime_env_without_python_path(env)).stdout


def test_missing_manifest_uses_environment_and_abi_mismatch_is_rejected(tmp_path):
    """Deleted sidecars fall back; a wrong ABI sidecar is never selected / 消去後探索と ABI 不一致拒否。"""
    cmake = shutil.which("cmake")
    if cmake is None:
        raise AssertionError("CMake is required for the standard C/C++ SDK gate")
    cmake_dir = _run([sys.executable, "-m", "fullseye.sdk", "--cmakedir"], cwd=ROOT).stdout.strip()
    build = tmp_path / "automatic" / "build"
    env = os.environ.copy()
    env.pop("FULLSEYE_PYTHON_ROOT", None)
    _run([cmake, "-S", str(ROOT / "examples" / "c_api" / "hello_cpp"), "-B", str(build),
          "-Dfullseye_DIR=" + cmake_dir], cwd=tmp_path, env=env)
    _run([cmake, "--build", str(build)], cwd=tmp_path, env=env)
    executable = build / ("app.exe" if sys.platform == "win32" else "app")
    manifest = build / "fullseye_runtime.json"
    manifest.unlink()
    automatic = _runtime_env_without_python_path(env)
    automatic["FULLSEYE_PYTHON_ROOT"] = str(sdk.package_root().parent)
    automatic["VIRTUAL_ENV"] = str(Path(sys.prefix).resolve())
    result = _run([str(executable)], cwd=tmp_path, env=automatic)
    assert "result_count=1" in result.stdout
    assert "FULLSEYE_PYTHON_ROOT" in result.stderr
    data = {
        "python_executable": str(Path(sys.executable).resolve()),
        "python_home": str(Path(sys.prefix).resolve()),
        "runtime_root": str(sdk.package_root().parent),
        "sdk_abi_version": "999.0",
        "created_at": "2026-11-24T00:00:00Z",
    }
    manifest.write_text(json.dumps(data), encoding="utf-8")
    result = _run([str(executable)], cwd=tmp_path, env=automatic)
    assert "result_count=1" in result.stdout
    assert "FULLSEYE_PYTHON_ROOT" in result.stderr
    assert "adjacent fullseye_runtime.json" not in result.stderr


def test_missing_every_candidate_explains_what_happened_and_how_to_fix(tmp_path):
    """The C error gives attempts and paste-ready repairs / C の失敗は探索履歴と修復コマンドを返す。"""
    cmake = shutil.which("cmake")
    if cmake is None:
        raise AssertionError("CMake is required for the standard C/C++ SDK gate")
    cmake_dir = _run([sys.executable, "-m", "fullseye.sdk", "--cmakedir"], cwd=ROOT).stdout.strip()
    build = tmp_path / "failure" / "build"
    env = os.environ.copy()
    _run([cmake, "-S", str(ROOT / "examples" / "c_api" / "hello_cpp"), "-B", str(build),
          "-Dfullseye_DIR=" + cmake_dir], cwd=tmp_path, env=env)
    _run([cmake, "--build", str(build)], cwd=tmp_path, env=env)
    manifest = build / "fullseye_runtime.json"
    manifest.write_text(json.dumps({"runtime_root": str(tmp_path / "gone"), "sdk_abi_version": "0.2"}),
                        encoding="utf-8")
    failed = _runtime_env_without_python_path(env)
    failed["FULLSEYE_PYTHON_ROOT"] = str(tmp_path / "no-fullseye")
    failed["VIRTUAL_ENV"] = str(tmp_path / "no-venv")
    failed["CONDA_PREFIX"] = str(tmp_path / "no-conda")
    result = subprocess.run([str(build / ("app.exe" if sys.platform == "win32" else "app"))], cwd=tmp_path,
                            env=failed, text=True, capture_output=True, check=False, timeout=120)
    assert result.returncode != 0
    for text in ("FS_E_NO_PYTHON", "Tried:", "FULLSEYE_PYTHON_ROOT", "fullseye_runtime.json",
                 "Fix in PowerShell:", "py -3.11 -m pip install fullseye",
                 "py -3.11 -m fullseye.sdk relink .\\build", "Fix in bash:",
                 "python3 -m fullseye.sdk relink ./build"):
        assert text in result.stderr
