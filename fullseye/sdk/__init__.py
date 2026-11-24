"""Installed source SDK discovery / インストール済みソース SDK の検出。"""

from __future__ import annotations

from pathlib import Path


def abi_version() -> str:
    """Return the C SDK ABI carried by this package / 同梱 C SDK ABI を返す。"""
    return (Path(__file__).resolve().parent / "ABI_VERSION").read_text(encoding="utf-8").strip()


def package_root() -> Path:
    """Return the installed ``fullseye`` package directory.

    Its parent is the bridge's default ``runtime_root`` because that parent
    must be on ``sys.path`` to import ``fullseye``. / ``fullseye`` を import
    するには親 directory を ``sys.path`` に置く必要がある。
    """
    return Path(__file__).resolve().parents[1]


def payload_paths() -> tuple[Path, Path]:
    """Return bridge source and include directory for wheel or editable use."""
    sdk = Path(__file__).resolve().parent
    source = sdk / "src" / "fullseye_c_api.cpp"
    include = sdk / "include" / "fullseye"
    if source.is_file() and include.is_dir():
        return source, include
    # Editable installs intentionally do not copy a second mutable SDK tree.
    # The wheel always takes the branch above. / editable 導入では二重の可変
    # SDK を作らず、wheel だけが上の同梱経路を使う。
    root = package_root().parent
    return root / "native" / "fullseye_c_api.cpp", root
