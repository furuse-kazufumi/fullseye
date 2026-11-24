# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Static packaging gates; never execute the installer / インストーラーを実行しない静的な門。"""
from pathlib import Path
import tomllib

from fullseye.install_components import INSTALL_COMPONENTS, SDK_LAYOUT

ROOT = Path(__file__).resolve().parents[1]


def test_native_sdk_is_standard_and_pybind11_is_pinned_without_a_build_tool():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert "pybind11==2.13.6" in project["dependencies"]
    assert not any(item.startswith("cmake") for item in project["dependencies"])
    native = project["optional-dependencies"]["native"]
    assert native == []


def test_sdk_is_a_standard_component_with_fixed_wheel_destinations():
    sdk = INSTALL_COMPONENTS["sdk"]
    assert sdk.selectable is False and sdk.python_extra is None
    assert sdk.development_only is False
    assert "--cmakedir" in sdk.runtime_note
    assert set(SDK_LAYOUT) == {"headers", "bridge_source", "cmake_config", "sdk_cli"}
    assert set(sdk.destinations) == set(SDK_LAYOUT.values())
    assert SDK_LAYOUT["headers"] == "fullseye/sdk/include/fullseye"
    assert SDK_LAYOUT["cmake_config"] == "fullseye/sdk/cmake"


def test_cmake_exports_cxx_target_and_installs_all_headers():
    text = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "add_library(Fullseye::CXX ALIAS fullseye_cxx)" in text
    assert "fullseye.h fullseye.hpp fullseye_opencv.hpp fullseye_abi.h" in text
    config = ROOT / "fullseye" / "sdk" / "cmake" / "fullseyeConfig.cmake"
    assert config.is_file()
    text = config.read_text(encoding="utf-8")
    assert "fullseye::fullseye" in text and "FULLSEYE_DEFAULT_RUNTIME_ROOT" in text
    assert "string(HEX" in text and "copy_if_different" in text
