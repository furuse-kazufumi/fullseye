"""Fullseye 3D ビューアの別プロセス起動エントリ(desktop 常用).

Studio(Qt)は ``viewer3d.launch_detached`` からこのスクリプトを detached 起動する。
本プロセスが Open3D の GL ウィンドウを所有し run() でブロックする(Studio 側は固まらない)。
GL クラッシュもこのプロセスに隔離される。

  py -3.11 viewer3d_launch.py <manifest.json> [title]
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import viewer3d  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: viewer3d_launch.py <manifest.json> [title]", file=sys.stderr)
        return 2
    manifest = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else "Fullseye 3D"
    if not viewer3d.available():
        print("open3d not available", file=sys.stderr)
        return 1
    geoms = viewer3d.load_scene(manifest)
    if not geoms:
        print("no geometry to show", file=sys.stderr)
        return 1
    ok = viewer3d.show_interactive(geoms, title=title, grid=True)
    # 一時シーンの後片付け(親は detached なので子が消す)
    try:
        import shutil
        shutil.rmtree(os.path.dirname(manifest), ignore_errors=True)
    except Exception:
        pass
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
