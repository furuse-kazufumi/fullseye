# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Static packaging gates; never execute the installer / インストーラーを実行しない静的な門。"""
from pathlib import Path
import tomllib

from fullseye.install_components import INSTALL_COMPONENTS, SDK_LAYOUT

ROOT = Path(__file__).resolve().parents[1]


def test_native_dependencies_are_optional_and_pybind11_is_pinned():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert not any("pybind11" in item or item.startswith("cmake") for item in project["dependencies"])
    native = project["optional-dependencies"]["native"]
    assert "pybind11==2.13.6" in native and any(item.startswith("cmake") for item in native)


def test_sdk_is_a_selectable_component_with_fixed_destinations():
    sdk = INSTALL_COMPONENTS["sdk"]
    assert sdk.selectable is True and sdk.python_extra == "native"
    assert sdk.development_only is True
    assert "FULLSEYE_PYTHON_ROOT" in sdk.runtime_note
    assert set(SDK_LAYOUT) == {"headers", "runtime_windows", "library", "cmake_config",
                               "python_runtime", "site_packages"}
    assert set(sdk.destinations) == set(SDK_LAYOUT.values())
    assert SDK_LAYOUT["headers"] == "include/fullseye"
    assert SDK_LAYOUT["cmake_config"] == "lib/cmake/Fullseye"


def test_cmake_exports_cxx_target_and_installs_all_headers():
    text = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
    assert "add_library(Fullseye::CXX ALIAS fullseye_cxx)" in text
    assert "fullseye.h fullseye.hpp fullseye_abi.h" in text
    assert (ROOT / "cmake" / "FullseyeConfig.cmake.in").is_file()
    config = (ROOT / "cmake" / "FullseyeConfig.cmake.in").read_text(encoding="utf-8")
    assert "development SDK" in config and "FULLSEYE_PYTHON_ROOT" in config
