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
    development_only: bool
    runtime_note: str


SDK_LAYOUT = {
    "headers": "fullseye/sdk/include/fullseye",
    "bridge_source": "fullseye/sdk/src",
    "cmake_config": "fullseye/sdk/cmake",
    "runtime_abi": "fullseye/sdk/ABI_VERSION",
    "sdk_cli": "python -m fullseye.sdk",
}

INSTALL_COMPONENTS = {
    "sdk": InstallComponent(
        component_id="sdk",
        selectable=False,
        python_extra=None,
        destinations=tuple(SDK_LAYOUT.values()),
        development_only=False,
        runtime_note=("Installed by default with pip install fullseye. Run python -m fullseye.sdk "
                      "--cmakedir and call fullseye_deploy_runtime(app); relink a moved environment "
                      "with python -m fullseye.sdk relink <executable-directory>."),
    ),
}
