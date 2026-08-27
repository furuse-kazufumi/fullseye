# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""itokawa_symmetry_honest — 対称性検出(正直な結果: 小惑星は非対称)。

【この例が示すこと — 正直なネガティブ結果】
対称性検出器は、対称な形状には高い対称性を、非対称な形状には低い対称性を報告すべきである。
実在の小惑星イトカワは重力的に緩く集積したラブルパイル(瓦礫の寄せ集め)で、
「ラッコ / 落花生」形の **明確に非対称** な天体である。したがって正しく動く検出器なら、
イトカワには合成した対称形状(楕円体)より **明らかに低い対称性** を報告するはずだ。
これは検出器の失敗ではなく、実データに対する正しいネガティブ結果である。

【指標の向き(honest)】
symmetry3d.reflection_symmetry_score が返す生値は「鏡映残差 = chamfer(鏡映, 元) / 点間隔」で、
**小さいほど対称**(距離的な残差)。人間に分かりやすいよう、ここではこれを
symmetry_score = 1 / (1 + 残差) に変換し、**大きいほど対称** の「対称性スコア」にする。
検証は両方の向きで assert する:
  - 対称性スコア: 楕円体 > イトカワ(タスクの要求どおり)
  - 生の鏡映残差: イトカワ > 楕円体(= イトカワはより非対称、正直なネガティブ)

対象データ: studio_assets/sample_3d/itokawa_points.npy(実測イトカワ点群, ~3000 点)。
使う op: symmetry3d.detect_reflection_symmetry(PCA 主軸を法線とする候補平面で採点)。
"""
import sys
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import symmetry3d  # detect_reflection_symmetry(反射対称の残差スコア。小さいほど対称)

DATA = _REPO / "studio_assets" / "sample_3d" / "itokawa_points.npy"


def symmetry_score(residual):
    """鏡映残差(小さいほど対称)→ 対称性スコア(大きいほど対称)。範囲 (0, 1]。"""
    return 1.0 / (1.0 + residual)


def make_symmetric_ellipsoid(n_half=1500, semi=(280.0, 150.0, 120.0), seed=3):
    """z=0 平面に対して厳密に鏡映対称な楕円体表面点群を作る(合成の対称形状)。

    上半分を一様サンプルし、その z 反転コピーを加える。z 平面での鏡映が集合を
    自分自身へ厳密に写すため、その主軸平面での反射残差はほぼ 0 になる。
    """
    rng = np.random.default_rng(seed)
    u = rng.normal(size=(n_half, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    half = u * np.asarray(semi)
    half[:, 2] = np.abs(half[:, 2])                 # 上半分
    mirror = half * np.array([1.0, 1.0, -1.0])      # 厳密な z 鏡映
    return np.vstack([half, mirror])


def main():
    # --- イトカワ(実在の非対称天体) ---
    pts = np.load(DATA).astype(np.float64)
    pts = pts - pts.mean(axis=0)
    res_itokawa = symmetry3d.detect_reflection_symmetry(pts)
    r_itokawa = res_itokawa["score"]                # 生の鏡映残差(小さいほど対称)

    # --- 合成の対称形状(楕円体) ---
    ellipsoid = make_symmetric_ellipsoid()
    res_ell = symmetry3d.detect_reflection_symmetry(ellipsoid)
    r_ell = res_ell["score"]

    s_itokawa = symmetry_score(r_itokawa)           # 対称性スコア(大きいほど対称)
    s_ell = symmetry_score(r_ell)

    print("=== 反射対称の検出(PCA 主軸を候補平面に採点) ===")
    print("[生の鏡映残差 — 小さいほど対称]")
    print(f"  イトカワ(実データ) : {r_itokawa:.4f}  "
          f"(3 主軸: {[round(s, 3) for s in res_itokawa['all_scores']]})")
    print(f"  楕円体(合成対称)   : {r_ell:.4e}  "
          f"(3 主軸: {[round(s, 4) for s in res_ell['all_scores']]})")
    print("[対称性スコア = 1/(1+残差) — 大きいほど対称]")
    print(f"  イトカワ(実データ) : {s_itokawa:.4f}")
    print(f"  楕円体(合成対称)   : {s_ell:.4f}")

    # --- 検証(両方の向きで) ---
    # タスク要求: 対称形状のスコア > イトカワのスコア
    assert s_ell > s_itokawa, \
        f"対称形状のスコアがイトカワ以下: 楕円体={s_ell:.4f}, イトカワ={s_itokawa:.4f}"
    # 正直なネガティブ: 生残差はイトカワのほうが大きい(= より非対称)
    assert r_itokawa > r_ell, \
        f"イトカワの残差が楕円体以下(非対称が示せていない): {r_itokawa:.4f} vs {r_ell:.4e}"

    print("\nPASS(正直なネガティブ結果): 検出器はイトカワを楕円体より明確に非対称と報告した"
          f"(対称性スコア {s_itokawa:.3f} < {s_ell:.3f})。"
          "これは検出器の欠陥ではなく、ラブルパイル小惑星が実際に非対称であることの正しい反映。")


if __name__ == "__main__":
    main()
