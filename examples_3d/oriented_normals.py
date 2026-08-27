# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 閉じた曲面(球)の点群に「一貫して外向き」の法線を付ける (oriented normals).

3Dスキャンや点群処理では各点の「面の向き(法線)」が要る。ところが素の PCA 法線推定は
各点の接平面までは正しく当てるが、その**向き(符号)は点ごとにバラバラ**になる。
外を向く点もあれば、隣なのに内を向く点もある。表と裏がまだら模様になった状態で、
レンダリングも凹凸判定(shape index)も破綻する。

そこで estimate_oriented_normals は「まず PCA で向き未定の法線を出し(estimate_normals)、
次に隣接点どうしの向きが揃うよう大域伝播する(orient_normals, Hoppe の MST 法)」を
連結して掛け、全点を一貫した向きにそろえる。

なぜ球で検証できるか(GT): 原点中心の球なら、ある点の**真の外向き法線は
その点の位置ベクトルを正規化した向き**そのもの、と幾何だけで分かる。つまり
推定法線と「位置方向」の内積を測れば、当てずっぽうなしで正誤が判定できる。

beat-the-null(下駄を履かせない基準): 向き付けをしない生の PCA 法線(estimate_normals)は
符号が点ごとに任意なので、真の外向きとの一致率は**コイン投げの ~0.5**に落ちる。
向き付けありがこの 0.5 の基準を明確に上回って初めて「効いている」と言える。
"""
import sys
from pathlib import Path

import numpy as np

# examples_3d/ の 1 つ上(リポジトリルート)を import パスに通す。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from normals_orient import estimate_normals, estimate_oriented_normals, orient_normals


def sphere_points(n=800, radius=1.5, seed=0):
    """原点中心・半径 radius の球面に (n,3) 点をほぼ一様サンプル(フィボナッチ球)。

    原点中心にするのが要点。こうすると点 p の真の外向き法線が p/||p|| で厳密に分かり、
    ground truth として使える。わずかなノイズを載せて実スキャンらしくするが、
    法線の向き(符号)の話には効かない程度に留める。
    """
    rng = np.random.default_rng(seed)
    i = np.arange(n) + 0.5
    phi = np.arccos(1.0 - 2.0 * i / n)                 # 極角: 高さを均等に
    theta = np.pi * (1.0 + np.sqrt(5.0)) * i           # 方位角: 黄金角で回す
    unit = np.column_stack([
        np.sin(phi) * np.cos(theta),
        np.sin(phi) * np.sin(theta),
        np.cos(phi),
    ])
    pts = radius * unit
    pts += rng.normal(0.0, 0.005 * radius, pts.shape)  # スケール 0.5% の軽いノイズ
    return pts


def outward_agreement(normals, points):
    """各法線と「真の外向き(位置方向)」の内積 → (符号つき内積, 一致率, 精度) を返す。

    - dots      : 各点の内積(+1 で外向き一致, -1 で内向き反転)。
    - outward   : dots > 0.95 の割合 = 「正確 かつ 外向き」に付いている割合。
    - accuracy  : |dots| > 0.95 の割合 = 符号を無視した法線の当たり具合(接平面精度)。
    """
    P = np.asarray(points, np.float64)
    N = np.asarray(normals, np.float64)
    if P.shape != N.shape or P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"shape mismatch: points {P.shape} vs normals {N.shape}")
    mag = np.linalg.norm(P, axis=1, keepdims=True)
    if np.any(mag < 1e-12):
        raise ValueError("a point sits at the origin; its outward direction is undefined")
    true_out = P / mag                                 # 原点中心球の真の外向き法線
    dots = np.einsum("ij,ij->i", N, true_out)
    outward = float(np.mean(dots > 0.95))
    accuracy = float(np.mean(np.abs(dots) > 0.95))
    return dots, outward, accuracy


def main():
    k = 20
    points = sphere_points(n=800, radius=1.5, seed=0)

    # 入力の健全性チェック(縮退データで結果を捏造しない)。
    if points.ndim != 2 or points.shape[1] != 3:
        raise ValueError(f"points must be (N, 3), got {points.shape}")
    if len(points) < k:
        raise ValueError(f"need at least k={k} points, got {len(points)}")

    # --- 1) null(基準): 向き付けなしの生 PCA 法線。符号は点ごとに任意 ---
    raw = estimate_normals(points, k=k)

    # --- 2) 2 つの op を連結: estimate_normals -> orient_normals(Hoppe MST 大域伝播)---
    oriented = orient_normals(points, raw, k=k)

    # --- 3) 一発合成 op も同じ結果になることを確認(estimate + orient の合成)---
    oriented_oneshot = estimate_oriented_normals(points, k=k)

    _, raw_outward, raw_acc = outward_agreement(raw, points)
    dots_or, or_outward, or_acc = outward_agreement(oriented, points)
    _, one_outward, _ = outward_agreement(oriented_oneshot, points)

    print(f"点数 / 近傍数 k               : {len(points)} / {k}")
    print(f"法線の接平面精度 (|内積|>0.95): {or_acc:.3f}  (符号を無視した当たり具合)")
    print(f"null: 向き付けなしの外向き一致 : {raw_outward:.3f}  (符号任意 → コイン投げ ~0.5)")
    print(f"連結後: 外向き一致 (内積>0.95) : {or_outward:.3f}  (一貫して外を向く)")
    print(f"一発合成 op の外向き一致       : {one_outward:.3f}  (連結と一致するはず)")

    # GT 検証:
    # (a) 接平面精度が高い = PCA 法線自体は生も向き付け後も正確(向き付けは符号だけ変える)。
    assert or_acc > 0.9, f"法線の接平面精度が低い: {or_acc:.3f}"
    # (b) null は符号任意ゆえコイン投げ帯に収まる(=下駄なしの正当な基準)。
    assert 0.3 < raw_outward < 0.7, f"null 基準がコイン投げから外れている: {raw_outward:.3f}"
    # (c) 向き付けは null を明確に上回り、ほぼ全点が外向きにそろう(beat-the-null)。
    assert or_outward > 0.95, f"向き付け後の外向き一致が不十分: {or_outward:.3f}"
    assert or_outward - raw_outward > 0.4, \
        f"null に対する優位が小さい: {or_outward:.3f} vs {raw_outward:.3f}"
    # (d) 連結 (estimate_normals->orient_normals) と一発合成 op は同一結果。
    assert one_outward == or_outward, \
        f"合成 op と連結が食い違う: {one_outward:.3f} vs {or_outward:.3f}"

    print(f"PASS: 向き付けで外向き一致 {raw_outward:.2f}(null) → {or_outward:.2f} に改善"
          f"、接平面精度 {or_acc:.2f}、beat-the-null 差 {or_outward - raw_outward:.2f}")


if __name__ == "__main__":
    main()
