# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""examples2d — the worked-example gallery for Fullseye's 2-D geometric vision ops.

An operator no one can *find or run* is invisible. This module is the discoverable
index for the 2-D geometric examples: every entry is a **self-contained,
self-asserting runnable script** under ``examples/`` that builds data, calls the
toolkit, prints a ground-truth check and asserts it. Studio's "2-D Examples" gallery
sources its list from here, and :func:`validate` runs every script so the gallery
only ever advertises examples that actually work.

Mirror of :mod:`examples3d`; kept separate so 2-D (image-plane) and 3-D (point-cloud
/ volume) galleries stay legible. Add a new example by dropping a runnable script in
``examples/`` and appending an entry here.

Usage::

    import examples2d
    examples2d.names()                         # every example id
    examples2d.by_task()["morphing"]           # ids grouped by task
    print(examples2d.code("image_morph"))      # the runnable source
    examples2d.validate()                      # run all; returns {id: (ok, note)}

Each script is also runnable directly::

    py -3.11 examples/image_morph.py
"""
from __future__ import annotations

import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(_ROOT, "examples")

# id -> metadata. `name`/`summary` are plain-language (what real problem it solves);
# `task` groups the gallery; `data` is the provenance. Every id maps to examples/<id>.py.
EXAMPLES = [
    # -- morphing / warping ------------------------------------------------------ #
    {"id": "image_morph", "task": "morphing", "data": "synthetic",
     "name": "2人の顔の中間を作る(対応点駆動モーフ)",
     "summary": "作業者が与えた対応点(目・鼻・口)で特徴を中間形状へワープしてからディゾルブし、"
                "単純αブレンドの二重像(ゴースト)を避けて『本物の中間顔』を作る。区分アフィン/TPS。"},
    # -- shape descriptors ------------------------------------------------------- #
    {"id": "contour_fourier", "task": "shape_descriptors", "data": "synthetic",
     "name": "輪郭の楕円フーリエ記述子(平滑化・不変マッチング)",
     "summary": "閉輪郭をフーリエ級数で表し、高調波打ち切りで平滑化、回転/拡大/移動/始点に不変な"
                "記述子で形状検索する(EFD, Kuhl-Giardina)。"},
    # -- drawing / annotation ---------------------------------------------------- #
    {"id": "draw_annotate", "task": "drawing", "data": "synthetic",
     "name": "画像にマーカー/線/円/輪郭を直接描く(ラスタ描画)",
     "summary": "作業者が指定した対応点を画像そのものに焼き込むラスタ描画op(imagedraw)。"
                "描いた既知シーンを検出器が回収し結果を描き返す(描画→検出→注釈)。"},
    # -- signal / point-sequence math -------------------------------------------- #
    {"id": "signal_filter", "task": "signal_processing", "data": "synthetic",
     "name": "点列の多項式近似・フーリエ・ローパス/ハイパス",
     "summary": "計測1D列をトレンド抽出(多項式)・周波数分析(FFT)・平滑化(ローパス)・"
                "細部抽出(ハイパス)する(signal1d)。各処理に beat-the-null のGT付き。"},
    {"id": "spline_curve", "task": "interpolation", "data": "synthetic",
     "name": "スプライン補間(開/閉曲線・2D/3D・時間変形)",
     "summary": "疎な点列を滑らかに補間・再サンプル。輪郭は閉曲線(滑らかに閉じる)、"
                "軌跡は開曲線、3D空間曲線も同API。座標を時間で補間すれば時間軸の変形も表せる。"},
    # -- family coverage galleries (exercise & GT-validate every op in a category family) -- #
    # Breadth exercisers: each drives its whole op family with finite/out_sort/determinism
    # checks plus beat-the-null GT on representative ops. They keep op→example coverage at
    # 100% (see tests/test_op_example_coverage.py) and double as runnable family demos.
    {"id": "gallery2d_smoothing_rank", "task": "family_coverage", "data": "synthetic",
     "name": "平滑化・ランク・復元フィルタ族を総なめ", "summary":
         "gaussian/median/bilateral/rank/restoration など平滑化フィルタ族の全 op を実行し、"
         "有限性・out_sort・決定性を機械検証(代表 op は beat-the-null GT)。"},
    {"id": "gallery2d_edges", "task": "family_coverage", "data": "synthetic",
     "name": "エッジ・微分・コーナー演算子族を総なめ", "summary":
         "sobel/laplace/canny/harris などエッジ・勾配・コーナー検出族の全 op を GT 検証。"},
    {"id": "gallery2d_morphology", "task": "family_coverage", "data": "synthetic",
     "name": "モルフォロジー(形態学)op 族を総なめ", "summary":
         "収縮/膨張/開閉/tophat/skeleton などグレー・二値形態学の全 op を GT 検証。"},
    {"id": "gallery2d_region", "task": "family_coverage", "data": "synthetic",
     "name": "領域(region)op 族を総なめ", "summary":
         "穴埋め/最大成分/距離変換/外接内接/RLE など region・region-morphology・region-transform を GT 検証。"},
    {"id": "gallery2d_segmentation", "task": "family_coverage", "data": "synthetic",
     "name": "セグメンテーション演算子族を総なめ", "summary":
         "otsu/dyn_threshold/watershed/local_max などしきい値・領域分割族の全 op を GT 検証。"},
    {"id": "gallery2d_features", "task": "family_coverage", "data": "synthetic",
     "name": "特徴抽出・テクスチャ・形状記述子族を総なめ", "summary":
         "特徴点/テクスチャ/形状記述/自己相似の全 op を有限性・決定性で GT 検証。"},
    {"id": "gallery2d_geometry", "task": "family_coverage", "data": "synthetic",
     "name": "2-D 幾何オペレータ族を総なめ", "summary":
         "アフィン/射影/回転/リサンプル/座標変換など幾何変換族の全 op を GT 検証。"},
    {"id": "gallery2d_gray_arith", "task": "family_coverage", "data": "synthetic",
     "name": "濃淡・階調変換・算術・定義域 op 族を総なめ", "summary":
         "gamma/contrast/算術演算/domain(定義域)など濃淡・階調族の全 op を GT 検証。"},
    {"id": "gallery2d_contour_measure", "task": "family_coverage", "data": "synthetic",
     "name": "輪郭・1次元計測・テンプレート照合族を総なめ", "summary":
         "輪郭抽出/subpix/1D 計測/テンプレートマッチ族の全 op を GT 検証。"},
    {"id": "gallery2d_texture_freq", "task": "family_coverage", "data": "synthetic",
     "name": "テクスチャ・周波数・分解 op 族を総なめ", "summary":
         "FFT/gabor/wavelet/分解(decomposition)などテクスチャ・周波数族の全 op を GT 検証。"},
    {"id": "gallery2d_color_artistic", "task": "family_coverage", "data": "synthetic",
     "name": "色・芸術・拡張(sim2real)op 族を総なめ", "summary":
         "色空間変換/芸術効果/augmentation など色・拡張族の全 op を GT 検証。"},
    {"id": "gallery2d_halcon_ext", "task": "family_coverage", "data": "synthetic",
     "name": "HALCON 拡充 tier(hx_ 一族)を総なめ", "summary":
         "HALCON 互換の拡充 op(``hx_`` prefix, category=halcon_ext)の全 op を GT 検証。"},
    {"id": "gallery2d_physics_alife_3d", "task": "family_coverage", "data": "synthetic",
     "name": "物理PDE・人工生命・トモグラフィ・3Dボリューム op 族を総なめ", "summary":
         "拡散/反応拡散/CA/tomography/volume など物理・人工生命・3D 族の全 op を GT 検証。"},
]

_BY_ID = {e["id"]: e for e in EXAMPLES}


def names() -> list[str]:
    """Every example id, in gallery order."""
    return [e["id"] for e in EXAMPLES]


def get(example_id: str) -> dict:
    """Metadata dict for an example id (KeyError if unknown)."""
    return _BY_ID[example_id]


def tasks() -> list[str]:
    """Distinct task categories, in first-seen order."""
    seen = []
    for e in EXAMPLES:
        if e["task"] not in seen:
            seen.append(e["task"])
    return seen


def by_task() -> dict:
    """``{task: [id, ...]}`` for grouping the gallery."""
    out: dict[str, list[str]] = {}
    for e in EXAMPLES:
        out.setdefault(e["task"], []).append(e["id"])
    return out


def by_data() -> dict:
    """``{provenance: [id, ...]}``."""
    out: dict[str, list[str]] = {}
    for e in EXAMPLES:
        out.setdefault(e["data"], []).append(e["id"])
    return out


def path(example_id: str) -> str:
    """Absolute path to the runnable script for an example id."""
    return os.path.join(DIR, example_id + ".py")


def code(example_id: str) -> str:
    """The runnable source of an example (for the 'view code' gallery panel)."""
    with open(path(example_id), encoding="utf-8") as f:
        return f.read()


def discover() -> list[str]:
    """Every ``examples/*.py`` on disk (superset check against EXAMPLES)."""
    if not os.path.isdir(DIR):
        return []
    return sorted(f[:-3] for f in os.listdir(DIR)
                  if f.endswith(".py") and not f.startswith("_"))


def run(example_id: str, timeout: int = 240) -> tuple[bool, str]:
    """Run one example as a subprocess (repo root on PYTHONPATH). -> (ok, tail_output)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = _ROOT + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUTF8"] = "1"
    try:
        p = subprocess.run([sys.executable, path(example_id)], cwd=_ROOT, env=env,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    tail = (p.stdout or "").strip().splitlines()
    note = tail[-1] if tail else ((p.stderr or "").strip().splitlines()[-1:] or [""])[0]
    return p.returncode == 0, note


def validate(ids=None) -> dict:
    """Run each example and report which are usable -> ``{id: (ok, note)}``.

    The gallery advertises only what passes here, so a broken example is surfaced,
    never silently shown. Pass ``ids`` to check a subset.
    """
    ids = ids or names()
    return {i: run(i) for i in ids}


if __name__ == "__main__":
    ok = 0
    results = validate()
    for i, (name, (good, note)) in enumerate(results.items(), 1):
        mark = "PASS" if good else "FAIL"
        print(f"[{i:2d}/{len(names())}] {mark}  {name}: {note}")
        ok += good
    print(f"\n{ok}/{len(names())} examples usable")
    sys.exit(0 if ok == len(names()) else 1)
