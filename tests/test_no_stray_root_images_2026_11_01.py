"""受け取り検査の撮影画像が repo 直下に紛れ込まない門。

#216 で光弾性の受け取り検査の画像(after5_*.png、panels/)が repo 直下に commit され、
#219 で取り除いた。画像は ALLOWED_TOP の下にだけ置く(repo 直下と未登録の最上位ディレクトリは不可)。
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
# 画像を置いてよい最上位ディレクトリ(2026-11-01 時点で実在するもの)。足すときは理由を書く。
ALLOWED_TOP = {"docs", "examples", "examples_3d", "tests", "data", "assets", "spikes",
               "studio_assets", "tools"}


def _tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True)
    return out.stdout.splitlines()


def test_no_images_outside_allowed_top_level_directories():
    files = _tracked()
    assert len(files) > 1000, "git ls-files が空に近い: 門が対象を読めていない"
    stray = [f for f in files
             if Path(f).suffix.lower() in IMAGE_SUFFIXES and f.split("/")[0] not in ALLOWED_TOP]
    assert not stray, "repo 直下などに画像が紛れ込んでいる: %s" % stray[:20]
