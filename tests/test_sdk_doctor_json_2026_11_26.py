"""C/C++ SDK の診断と MSVC の設定(2026-11-26、1.2.0 の公開前の利用者検証で見つかった 3 件の回帰試験)。

1. ``fullseye doctor`` は ``python -m fullseye.sdk --doctor --json`` を呼ぶが、SDK の CLI は ``--json`` を知らず、
   SDK の節が毎回 warning になっていた。
2. ``python -m fullseye.sdk --doctor`` は、ビルドが失敗すると「コンパイラ・Python.h・pybind11 が無い」と言っていた
   (どれも在るのに)。Visual Studio のジェネレータでは実行ファイルの場所(build/Debug/)も外していた。
3. 利用者側の CMake 設定に MSVC 向けの /utf-8 と NOMINMAX が無く、MSVC で bridge がコンパイルできなかった
   (C2589 と、日本語 Windows では C2001)。CI の C API の job は Linux だけなので、ここでは設定の中身を固定する。
"""
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

from fullseye import doctor
from fullseye.sdk import __main__ as sdk_cli

ROOT = Path(__file__).resolve().parents[1]


def test_sdk_doctor_json_is_one_json_document_and_does_not_build(monkeypatch, capsys):
    def no_build(*args, **kwargs):
        raise AssertionError("--doctor --json must not configure or build anything")
    monkeypatch.setattr(subprocess, "run", no_build)
    assert sdk_cli.main(["--doctor", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["schema"] == 1 and data["build_probe"] == "not_run"
    assert data["build_probe_command"] == "python -m fullseye.sdk --doctor"
    assert isinstance(data["missing"], list) and set(data["remedies"]) == set(data["missing"])


def test_sdk_doctor_json_lists_what_is_missing_with_remedies(monkeypatch, capsys):
    monkeypatch.setattr(sdk_cli.shutil, "which", lambda name: None)
    assert sdk_cli.main(["--doctor", "--json"]) == 0          # 任意の機能: 足りなくても失敗にしない
    data = json.loads(capsys.readouterr().out)
    assert {"cmake", "compiler"} <= set(data["missing"])
    assert data["cmake"] is None
    assert set(data["remedies"]["cmake"]) == {"Windows", "Linux", "macOS"}


def test_sdk_json_without_doctor_is_refused(capsys):
    with pytest.raises(SystemExit) as stop:
        sdk_cli.main(["--cmakedir", "--json"])
    assert stop.value.code == 2
    assert "--json is only valid with --doctor" in capsys.readouterr().err


def test_a_failed_consumer_build_is_not_reported_as_missing_parts(monkeypatch, capsys):
    monkeypatch.setattr(sdk_cli, "_missing_prerequisites", lambda: ([], "cmake"))

    def failing(cmd, **kwargs):
        raise subprocess.CalledProcessError(1, cmd)
    monkeypatch.setattr(subprocess, "run", failing)
    assert sdk_cli._doctor() == 1
    err = capsys.readouterr().err
    assert "BROKEN" in err and "not a missing part" in err and "部品の入れ直しでは" in err
    assert "MISSING:" not in err


def test_the_probe_finds_the_binary_of_a_multi_config_generator(monkeypatch, capsys):
    """Visual Studio は build/Debug/app.exe に置く。build/app.exe の決め打ちでは通ったビルドを失敗と言う。"""
    monkeypatch.setattr(sdk_cli, "_missing_prerequisites", lambda: ([], "cmake"))
    name = "app.exe" if sys.platform == "win32" else "app"
    ran = []

    def fake(cmd, **kwargs):
        if "--build" in cmd:
            out = Path(cmd[cmd.index("--build") + 1]) / "Debug"
            out.mkdir(parents=True)
            (out / name).write_bytes(b"")
        elif len(cmd) == 1:
            ran.append(Path(cmd[0]))
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(subprocess, "run", fake)
    assert sdk_cli._doctor() == 0
    assert len(ran) == 1 and ran[0].parent.name == "Debug" and ran[0].name == name


@pytest.mark.parametrize("returncode, stdout, stderr, expected", [
    (0, json.dumps({"schema": 1, "missing": []}), "", "ok"),
    (0, json.dumps({"schema": 1, "missing": ["cmake", "compiler"]}), "", "info"),
    (2, "", "usage: __main__.py ... error: unrecognized arguments: --json", "warning"),
    (0, json.dumps({"unexpected": True}), "", "warning"),
])
def test_fullseye_doctor_maps_the_sdk_answer(monkeypatch, returncode, stdout, stderr, expected):
    def fake(cmd, **kwargs):
        assert cmd[1:] == ["-m", "fullseye.sdk", "--doctor", "--json"]
        return subprocess.CompletedProcess(cmd, returncode, stdout=stdout, stderr=stderr)
    monkeypatch.setattr(doctor.subprocess, "run", fake)
    assert doctor._sdk_doctor()["status"] == expected


def test_the_real_sdk_cli_answers_fullseye_doctor_in_the_form_it_expects():
    """入口の両側を本物で繋ぐ(片側だけ直しても通らない)。"""
    answer = doctor._sdk_doctor()
    assert answer is not None and answer["status"] in ("ok", "info"), answer
    assert "missing" in answer["result"] and "raw" not in answer["result"]


@pytest.mark.parametrize("lang, missing, wanted", [
    ("ja", ["cmake"], ("足りない部品: cmake", "python -m fullseye.sdk --doctor")),
    ("ja", [], ("前提の部品は揃っています", "python -m fullseye.sdk --doctor")),
    ("en", ["compiler"], ("Missing for the optional C/C++ SDK: compiler", "python -m fullseye.sdk --doctor")),
])
def test_the_text_report_says_what_the_sdk_section_means(lang, missing, wanted):
    report = doctor.collect(env={"PATH": ""}, executable=sys.executable, platform=sys.platform, include_sdk=False)
    report["sdk"] = {"status": "info" if missing else "ok", "result": {"schema": 1, "missing": missing}}
    out = io.StringIO()
    doctor.main(["--lang", lang], collect_fn=lambda: report, out=out)
    text = out.getvalue()
    for fragment in wanted:
        assert fragment in text


def test_the_consumer_cmake_config_tells_msvc_utf8_and_nominmax():
    config = (ROOT / "fullseye" / "sdk" / "cmake" / "fullseyeConfig.cmake").read_text(encoding="utf-8")
    block = config[config.index("if(MSVC)"):]
    block = block[:block.index("endif()")]
    assert "target_compile_options(fullseye_source_bridge PUBLIC /utf-8)" in block
    assert "target_compile_definitions(fullseye_source_bridge PRIVATE NOMINMAX)" in block
    assert config.index("add_library(fullseye_source_bridge") < config.index("if(MSVC)")


def test_the_bridge_source_defines_nominmax_before_windows_h():
    source = (ROOT / "native" / "fullseye_c_api.cpp").read_text(encoding="utf-8")
    assert source.count("#  include <windows.h>") == 1
    head = source[:source.index("#  include <windows.h>")]
    assert "#    define NOMINMAX" in head and "#    define WIN32_LEAN_AND_MEAN" in head
