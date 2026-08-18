"""Fullseye 3D アニメ再生の別プロセス起動エントリ(rollout の qpos 軌道を動きで見る).

sim_source.launch_animation からこのスクリプトを detached 起動する。本プロセスが Open3D
窓を所有し、qpos を毎フレーム流し込んで歩行/着陸を再生する(Studio 側は固まらない)。

  py -3.11 anim_launch.py <manifest.json>
"""
from __future__ import annotations

import os
import sys

# imgevolve ルート(sim_source.py がある)を import path に
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import sim_source  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: anim_launch.py <manifest.json>", file=sys.stderr)
        return 2
    manifest = sys.argv[1]
    ok = sim_source.play_animation(manifest)
    try:
        import shutil
        shutil.rmtree(os.path.dirname(manifest), ignore_errors=True)
    except Exception:
        pass
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
