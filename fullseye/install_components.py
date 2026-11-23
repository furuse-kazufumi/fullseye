# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Static installer component catalogue / インストーラーの静的な部品カタログ。

This module defines choices and destinations only.  It deliberately performs no
installation; ``fullseye setup`` or a platform installer may consume the table.

このモジュールは選択肢と配置先だけを定義し、導入処理を実行しない。``fullseye setup``
または各 OS のインストーラーがこの表を読む。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InstallComponent:
    """One selectable payload and its SDK-relative destination / 選択可能な部品と SDK 内配置。"""

    component_id: str
    selectable: bool
    python_extra: str | None
    destinations: tuple[str, ...]


SDK_LAYOUT = {
    "headers": "include/fullseye",
    "runtime_windows": "bin",
    "library": "lib",
    "cmake_config": "lib/cmake/Fullseye",
    "python_runtime": "runtime/python",
    "site_packages": "runtime/site-packages",
}

INSTALL_COMPONENTS = {
    "sdk": InstallComponent(
        component_id="sdk",
        selectable=True,
        python_extra="native",
        destinations=tuple(SDK_LAYOUT.values()),
    ),
}
