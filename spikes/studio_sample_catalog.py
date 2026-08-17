"""Fullseye Studio サンプルカタログの種 — 2 ドメインをきれいに棲み分けて提示.

ユーザー要望(2026-08-18):「棲み分けをきれいに分けて、どちらも Fullseye Studio 上で
サンプルコード付きで用意されているといいね」。Studio(HDevelop 風 IDE)が op を
**ドメイン別に一覧し、各エントリに実行可能なサンプルコードを添える**ための最小カタログ。

★棲み分け(この分業を Studio でも崩さない):
  - **vision(視覚 op = fullseye が"計算する"層)**: 画像/点群を入力に、フィルタ・
    セグメント・6-DoF 姿勢などを算出。中身は自作 numpy(スキル化)。
  - **sim-source(物理が"供給する"層)**: 物理エンジン(MuJoCo 等)から RGB/depth/
    **LiDAR**/真値を取得し vision op へ渡す。fullseye は物理を"やらない"(off-mission)、
    出力を受けるだけ。→ 先の gap 分析・要件 F4 と同じ分業。

各 Sample は (name, domain, summary, code, run) を持つ = F3 introspection のミニ版。
Studio は domain でタブ分け → code を表示 → run で実行結果を返す、を想定。

  実行:  PYTHONPATH=. py -3.11 spikes/studio_sample_catalog.py
         PYTHONPATH=. py -3.11 spikes/studio_sample_catalog.py vision      # ドメイン絞り込み
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

# 同じ spikes/ の兄弟モジュール(Image チェーン / sim.MuJoCo LiDAR)を samples の実体に使う。
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lidar_adapter_spike as _sim  # noqa: E402  (sim.MuJoCo + LidarPattern + SCENE)
import unified_api_spike as _vis  # noqa: E402   (Image チェーン + 知覚設定オブジェクト)

import fullseye as fs  # noqa: E402


@dataclass(frozen=True)
class Sample:
    name: str
    domain: str            # "vision" | "sim-source"
    summary: str
    code: str              # Studio がそのまま表示するサンプルコード(人間が読んで自然)
    run: Callable[[], str]  # 実行して 1 行の結果要約を返す


# ── vision ドメイン(fullseye が計算する)────────────────────────────────────── #
def _s_image_chain() -> str:
    scene = np.random.default_rng(0).random((40, 60))
    edges = _vis.Image(scene).to_gray().gaussian(1.4).sobel().threshold(0.2)
    return f"edges {edges.array.shape} 非ゼロ {int((edges.array > 0).sum())} 画素"


def _s_cloud_perceive() -> str:
    rng = np.random.default_rng(0)
    xs, ys = np.meshgrid(np.linspace(-1, 1, 30), np.linspace(-1, 1, 30))
    plane = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(xs.size)])
    blob = rng.normal([0.4, 0.4, 0.5], 0.03, (60, 3))          # 床上の物体
    pts = np.vstack([plane + rng.normal(0, 0.002, plane.shape), blob])
    ng, gmask = fs.remove_ground(pts, thresh=0.03)
    clusters = fs.euclidean_clusters(ng, tol=0.1, min_size=5)
    return f"床 {int(gmask.sum())} 点除去 → 物体クラスタ {len(clusters)} 個"


# ── sim-source ドメイン(物理が供給する)──────────────────────────────────────── #
def _s_lidar_scan() -> str:
    scene = _sim.sim.MuJoCo(_sim.SCENE)
    pts = scene.lidar(origin=(0.0, 0.0, 1.0), pattern=_sim.LidarPattern(h_res=90, v_res=18))
    return f"LiDAR ヒット {len(pts)} 点(mj_ray 走査・GL 不要・真値)"


def _s_sim_to_vision() -> str:
    scene = _sim.sim.MuJoCo(_sim.SCENE)
    pts = scene.lidar(origin=(0.0, 0.0, 1.0))                  # sim-source
    ng, gmask = fs.remove_ground(pts, thresh=0.03)            # vision へ橋渡し
    clusters = fs.euclidean_clusters(ng, tol=0.25, min_size=5)
    return f"sim LiDAR → 床除去 {int(gmask.sum())} → 物体 {len(clusters)} 個(分業ループ)"


SAMPLES: list[Sample] = [
    Sample(
        "image.chain", "vision",
        "画像をチェーンで処理(グレー→ぼかし→エッジ→2値化)",
        "edges = Image(img).to_gray().gaussian(1.4).sobel().threshold(0.2)",
        _s_image_chain,
    ),
    Sample(
        "cloud.perceive", "vision",
        "点群から床を除去して物体クラスタを取り出す",
        "ng, _ = fs.remove_ground(points)\nclusters = fs.euclidean_clusters(ng)",
        _s_cloud_perceive,
    ),
    Sample(
        "sim.lidar", "sim-source",
        "物理エンジンから LiDAR 1 スキャン(点群を得る)",
        "pts = sim.MuJoCo(scene).lidar(origin=(0,0,1.0),\n"
        "                              pattern=LidarPattern(h_res=90, v_res=18))",
        _s_lidar_scan,
    ),
    Sample(
        "sim.to_vision", "sim-source",
        "sim LiDAR → fullseye 知覚 op の分業ループ(棲み分けの実演)",
        "pts = sim.MuJoCo(scene).lidar()          # 物理が供給\n"
        "ng, _ = fs.remove_ground(pts)            # fullseye が計算\n"
        "clusters = fs.euclidean_clusters(ng)",
        _s_sim_to_vision,
    ),
]

_DOMAIN_LABEL = {
    "vision": "vision(視覚 op = fullseye が計算する)",
    "sim-source": "sim-source(物理が供給する: RGB/depth/LiDAR/真値)",
}


def print_catalog(only: str | None = None) -> None:
    """Studio が domain 別にサンプルコード付きで一覧するのを、まず端末で再現する。"""
    for domain in ("vision", "sim-source"):
        if only and only != domain:
            continue
        print(f"\n=== {_DOMAIN_LABEL[domain]} ===")
        for s in (x for x in SAMPLES if x.domain == domain):
            print(f"\n  ● {s.name} — {s.summary}")
            for line in s.code.splitlines():
                print(f"      {line}")
            print(f"      ↳ 実行: {s.run()}")
    print("\n[catalog OK] 2 ドメインを棲み分けて samples を提示(Studio 露出=F6 の種)")


if __name__ == "__main__":
    print_catalog(sys.argv[1] if len(sys.argv) > 1 else None)
