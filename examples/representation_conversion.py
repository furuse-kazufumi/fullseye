# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""representation_conversion — 1 個の部品を 2 回スキャンし、**ずれ量を 8 つの表現で
測って往復させる**。戻るものは誤差 0、戻らないものは落ちた量を数値で言う。

    py -3.11 examples/representation_conversion.py

【この例が解く問題】
機械部品(12 x 8 x 6 mm のブロックの天面に半径 2.00 mm の半球ボスが 1 つ)を
2 回スキャンした。2 回目は治具にかけ直したので**既知の剛体変位**が乗っている。
現場の問いは 1 つ ——「**ずれは幾つで、それをどの表現で測っても同じ答えになるか**」。

同じ 1 つのずれを、12 系統の表現を経由して測る:

    点群 → 法線 → 拡張ガウス像      面の向きの地図(どの向きの面が何点あるか)
    点群 → 主曲率 → 統計表          ボスの曲率は閉形式で 1/R = 0.500
    点群 → 記述子 → 行列 → 記述子   形の指紋。往復と、1 ケースだけの非可逆点
    点群 → 添字 → ラベル → 添字     間引きの記録。逆向きは末尾の背景を落とす
    点群 → 位置(重心)→ 1 点の点群
    高さと断面積の対 → 表 / 密度画像 / 信号
    体積 → 相関スコア → 位置 / 最大値投影   ずれの本体
    体積 → 整数シフト → ベクトル → シフト
    体積 → (回転角, 倍率) → 行列 → (回転角, 倍率)
    点群 → 散在フロー → 点群        点ごとの対応
    点群 → TPS 変形 → 制御点
    複素スカラ → 極形式 → 複素スカラ

`examples/representation_roundtrip.py` は同じ族を「死んだ語彙をどう塞いだか」
の角度から一巡する。こちらは**現場の 1 課題を最後まで解く**筋で、
向き・曲率・記述子・添字・スコア・シフト・回転倍率・フロー・変形・複素の
**21 op はここでしか実行されない**。

【グラウンドトゥルース(数値で嘘を弾く)】
1. **保存則**: 拡張ガウス像は方向の計数ヒストグラムなので、総和は法線の本数に
   **厳密に等しい**(実測 6460 / 6460、差 0)。ブロックの 6 面はちょうど 6 つの
   bin に落ち、その 6 bin が全質量の **81.7 %** を占める(残りはボスが半球へ
   薄く散り、7 番目の bin は 6 点しかない)。
2. **閉形式**: 半径 R の球面の主曲率は両方とも 1/R。ボス R = 2.00 mm なので
   **0.500**、実測の中央値 **0.5040**(+0.79 %)。平面側は中央値 -0.0000。
3. **循環相関の厳密性**: b が a を s0 だけ ``np.roll`` したものなら、相関ピークは
   **厳密に** s0 に立つ(整数格子なので丸めも無い)。実測でピーク値 1.000000、
   位置 (3, 46, 4) = (3, -2, 4) mod 48。
4. **可逆性**: 位置・シフト・記述子・制御点の往復は **bit 一致**。回転倍率は
   max|Δ| = 7.1e-15、極形式は 3.8e-16。
5. **周回積分**: 単位円上の ∮dz/z = 2πi。極形式で r = 6.283175(真値 2π =
   6.283185、差 9.9e-06 は 2048 点の離散化)、θ = 90.000000 度ちょうど。

【この例が出す正直な結論】
**「往復して戻った」だけでは何も言えない。** 戻らない側を 12 件、すべて量つきで
残す。とくに次の 4 つは、例外が出ないので測らないと気付けない:
  * 添字 → ラベル → 添字 は bit 一致だが、**逆向き**は末尾の背景 129 個を落とす
    (長さが max(index)+1 に切り詰まる。値は落ちていない、長さが落ちている)。
  * (1, n) の 2-D 記述子だけは往復で 1-D になる(値は全部残り、「行が 1 本だった」
    というメタ情報だけが落ちる)。どちらを非可逆にするか選ばされた結果である。
  * せん断を含む行列を (回転角, 倍率) にすると**例外は出ず**、残差 0.300 が黙って消える。
  * 最近傍フローは、移動量が点間隔を超えると全単射でなくなる —— 実測で 256 点が
    224 か所へ落ち、**32 点ぶん形が縮む**。
そして相関スコアの最大値投影は、ピークが 0.98 倍で 1 画素と一意でありながら、
0.90 倍の裾は x に 5 px / y に 3 px と**等方でない** —— 部品が長い向きほど
位置合わせが緩いことを、画そのものが見せている。
"""
from __future__ import annotations

import colorsys
import math
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mathops                                                   # noqa: E402
import ops3d                                                     # noqa: E402
import reprconv as R                                             # noqa: E402

OP = ops3d.OPS3D

# ---- 部品(すべて mm。半分の寸法で持つ) ---------------------------------- #
HALF = (6.0, 4.0, 3.0)          # ブロックの半寸法 (x, y, z) -> 12 x 8 x 6 mm
BOSS_R = 2.0                    # 天面のボス半径 -> 曲率の閉形式 1/R = 0.5
FACE_GRID = 30                  # 1 面あたり 30 x 30 = 900 点(格子。乱数ではない)
BOSS_N = 1200                   # ボスの点数(フィボナッチ半球。乱数ではない)

# ---- 2 回目のスキャンに乗る既知のずれ ------------------------------------- #
TRUE_ROLL = (3, -2, 4)          # (dz, dy, dx) voxel
TRUE_ANGLE_DEG = 20.0           # z 軸まわりの回転
VOX_N = 48                      # 体積の一辺


def _rule(title):
    print(f"\n{'=' * 76}\n{title}\n{'=' * 76}")


# --------------------------------------------------------------------------- #
def build_part():
    """部品の表面点群と**解析的に正しい法線**を返す ((z,y,x) 順)。

    面は規則格子、ボスはフィボナッチ半球 —— どちらも決定的で、乱数は 1 つも
    使わない。法線は式から書けるので、推定した法線の答え合わせに使える。
    """
    hx, hy, hz = HALF
    t = (np.arange(FACE_GRID) + 0.5) / FACE_GRID * 2.0 - 1.0      # (-1, 1) の格子
    u, v = np.meshgrid(t, t, indexing="ij")
    u, v = u.ravel(), v.ravel()
    pts, nrm = [], []
    for axis, sign in ((0, +1), (0, -1), (1, +1), (1, -1), (2, +1), (2, -1)):
        p = np.empty((u.size, 3))
        free = [a for a in (0, 1, 2) if a != axis]
        p[:, axis] = sign
        p[:, free[0]], p[:, free[1]] = u, v
        n = np.zeros((u.size, 3))
        n[:, axis] = sign
        pts.append(p * np.array([hx, hy, hz]))
        nrm.append(n)
    p = np.concatenate(pts)
    n = np.concatenate(nrm)

    # ボスが天面から食う四角い足跡を外す(この点数は後で帳尻が合うか確かめる)
    footprint = ((np.abs(p[:, 0]) < BOSS_R) & (np.abs(p[:, 1]) < BOSS_R)
                 & (p[:, 2] > hz - 1e-9))
    n_eaten = int(footprint.sum())
    p, n = p[~footprint], n[~footprint]

    # フィボナッチ半球(決定的)
    k = np.arange(BOSS_N) + 0.5
    cz = 1.0 - k / BOSS_N                                # (0, 1] の上半球
    r_xy = np.sqrt(np.maximum(0.0, 1.0 - cz ** 2))
    phi = k * math.pi * (3.0 - math.sqrt(5.0))
    dirs = np.stack([r_xy * np.cos(phi), r_xy * np.sin(phi), cz], 1)
    boss = dirs * BOSS_R + np.array([0.0, 0.0, hz])

    p = np.concatenate([p, boss])
    n = np.concatenate([n, dirs])
    return p[:, ::-1], n[:, ::-1], n_eaten            # (x,y,z) -> (z,y,x)


def build_volume():
    """同じ部品の**中身の詰まった**体積 (D, H, W)。相関・位相相関の入力。"""
    zz, yy, xx = np.mgrid[0:VOX_N, 0:VOX_N, 0:VOX_N].astype(float)
    c = (VOX_N - 1) / 2.0
    block = ((np.abs(xx - c) <= 2.0 * HALF[0]) & (np.abs(yy - c) <= 2.0 * HALF[1])
             & (np.abs(zz - c) <= 2.0 * HALF[2]))
    top = c + 2.0 * HALF[2]
    boss = ((np.sqrt((xx - c) ** 2 + (yy - c) ** 2 + (zz - top) ** 2)
             <= 2.0 * BOSS_R) & (zz >= top))
    return (block | boss).astype(np.float64)


# --------------------------------------------------------------------------- #
def main():
    ok = True
    losses = []          # (表現, 可逆か, 落ちた量) —— 最後に表にする

    # ------------------------------------------------------------------ #
    _rule("1) 部品 ―― 構造のあるデータ(乱数は 1 つも使わない)")
    # ------------------------------------------------------------------ #
    points, true_normals, n_eaten = build_part()
    n_planar = int((np.abs(true_normals).max(1) == 1).sum())
    print(f"   ブロック {2 * HALF[0]:.0f} x {2 * HALF[1]:.0f} x {2 * HALF[2]:.0f} mm "
          f"+ 半径 {BOSS_R:.2f} mm の半球ボス")
    print(f"   点群 {points.shape}  (z,y,x) 順  "
          f"範囲 z[{points[:, 0].min():+.2f}, {points[:, 0].max():+.2f}] "
          f"y[{points[:, 1].min():+.2f}, {points[:, 1].max():+.2f}] "
          f"x[{points[:, 2].min():+.2f}, {points[:, 2].max():+.2f}]")
    print(f"   内訳: 平面 {n_planar} 点 (6 面 x {FACE_GRID}^2 から、"
          f"ボスの足跡 {n_eaten} 点を引いた) + ボス {BOSS_N} 点")
    assert n_planar == 6 * FACE_GRID ** 2 - n_eaten
    assert len(points) == n_planar + BOSS_N

    # ------------------------------------------------------------------ #
    _rule("2) 向き ―― 法線 → 拡張ガウス像(方向の計数ヒストグラム)")
    # ------------------------------------------------------------------ #
    egi = R.normals_to_egi(true_normals, n_az=36, n_el=18)
    print(f"   normals {true_normals.shape} -> EGI {egi.shape} "
          f"(行 = 仰角 18、列 = 方位 36、bin 幅 10 度)")
    print(f"   ★保存則: EGI の総和 = {egi.sum():.0f} / 法線の本数 = "
          f"{len(true_normals)}  差 {egi.sum() - len(true_normals):.0f}")
    assert egi.sum() == len(true_normals)

    order = np.argsort(egi.ravel())[::-1]
    top6 = np.unravel_index(order[:6], egi.shape)
    share = egi.ravel()[order[:6]].sum() / egi.sum()
    print(f"   最大 6 bin の計数 = "
          f"{[int(egi[r, c]) for r, c in zip(*top6)]}  "
          f"(全質量の {share:.1%})")
    print(f"   平坦な 6 面がちょうど 6 つの bin に落ちる。"
          f"7 番目以降は {int(egi.ravel()[order[6]])} 以下 = ボスが半球へ薄く散った分。")
    n_big = int((egi > 100).sum())
    print(f"   計数 100 超の bin は {n_big} 個 ―― 立方体の面の数そのもの。")
    assert n_big == 6 and share > 0.80
    assert egi.ravel()[order[6]] < 0.05 * egi.ravel()[order[5]]

    # 天面だけが他の 5 面より少ない = ボスに食われた分。EGI が帳簿になっている
    face_counts = sorted(int(egi[r, c]) for r, c in zip(*top6))
    print(f"   ★天面の bin だけ {face_counts[0]} 点(他の 5 面は "
          f"{face_counts[1]}-{face_counts[-1]} 点)。1 面 {FACE_GRID ** 2} 点から"
          f"ボスの足跡 {n_eaten} 点が抜けて {FACE_GRID ** 2 - n_eaten} 点、")
    print(f"     そこへボス頂上付近の真上を向いた法線が "
          f"{face_counts[0] - (FACE_GRID ** 2 - n_eaten)} 本入って "
          f"{face_counts[0]} 点 —— **計数は 1 本単位で追える**。")
    assert face_counts[0] >= FACE_GRID ** 2 - n_eaten
    losses.append(("normals -> EGI", False,
                   f"方向を bin 幅 10 度へ量子化(計数は保存、向きの解像度が落ちる)"))

    # 推定した法線でも同じ 6 山が立つか(現場では真の法線は無い)
    est = np.asarray(OP["estimate_oriented_normals"]["func"](points))
    agree = float(np.abs((est * true_normals).sum(1)).mean())
    egi_est = R.normals_to_egi(est, 36, 18)
    n_big_est = int((egi_est > 100).sum())
    print(f"   estimate_oriented_normals で推定 -> 真の法線との |内積| 平均 "
          f"{agree:.4f}、計数 100 超の bin は {n_big_est} 個")
    assert agree > 0.9

    # ------------------------------------------------------------------ #
    _rule("3) 曲率 ―― ボスの主曲率は閉形式で 1/R。統計は一方向")
    # ------------------------------------------------------------------ #
    k1, k2 = OP["principal_curvatures"]["func"](points, k=25)
    k1, k2 = np.asarray(k1), np.asarray(k2)
    boss_sel = np.zeros(len(points), bool)
    boss_sel[n_planar:] = True

    t_boss = R.curvature_to_table((k1[boss_sel], k2[boss_sel]))
    t_flat = R.curvature_to_table((k1[~boss_sel], k2[~boss_sel]))
    print(f"   閉形式の真値: 半径 {BOSS_R:.2f} mm の球面は k1 = k2 = "
          f"1/R = {1.0 / BOSS_R:.4f}")
    print(f"   ボス上 {t_boss['n']} 点   p05 {t_boss['p05']:+.4f} / "
          f"p50 {t_boss['p50']:+.4f} / p95 {t_boss['p95']:+.4f}   "
          f"(中央値の誤差 {t_boss['p50'] * BOSS_R - 1:+.2%})")
    print(f"   平面上 {t_flat['n']} 点   p05 {t_flat['p05']:+.4f} / "
          f"p50 {t_flat['p50']:+.4f} / p95 {t_flat['p95']:+.4f}")
    print(f"   ガウス曲率の平均  ボス {t_boss['gauss_mean']:+.4f} "
          f"(真値 1/R² = {1.0 / BOSS_R ** 2:.4f})  /  平面 "
          f"{t_flat['gauss_mean']:+.4f} (真値 0)")
    print(f"   ★平面側の p95 が {t_flat['p95']:+.4f} と大きいのは、"
          f"ブロックの**稜と角**が近傍に混ざるため。")
    print(f"     平らな面の中身は p50 = {t_flat['p50']:+.4f} で正しく 0。"
          f"「平均を見ると平面が曲がって見える」ので")
    print(f"     中央値を見るのが正しい —— それが分布を要約する op の存在理由である。")
    assert abs(t_boss["p50"] * BOSS_R - 1.0) < 0.02
    assert abs(t_flat["p50"]) < 1e-9
    assert t_boss["kind"] == "principal_pair"
    losses.append(("curvature -> table", False,
                   f"{t_boss['n'] + t_flat['n']} 点 -> 統計 9 個(点ごとの値は戻らない)"))

    # ------------------------------------------------------------------ #
    _rule("4) 記述子 ―― 形の指紋。往復と、1 ケースだけの非可逆点")
    # ------------------------------------------------------------------ #
    desc = np.asarray(OP["describe"]["func"](points))
    mat = np.asarray(R.descriptor_to_matrix(desc))
    back = np.asarray(R.matrix_to_descriptor(mat))
    print(f"   describe(points) -> descriptor {desc.shape}")
    print(f"   descriptor {desc.shape} -> matrix {mat.shape} -> descriptor "
          f"{back.shape}   max|Δ| = {np.abs(back - desc).max():.3e} (bit 一致)")
    assert back.shape == desc.shape and np.array_equal(back, desc)

    two = np.stack([desc, desc[::-1]])
    print(f"   2 行以上はそのまま: matrix {two.shape} -> descriptor "
          f"{np.asarray(R.matrix_to_descriptor(two)).shape}")
    assert np.asarray(R.matrix_to_descriptor(two)).shape == two.shape

    one_row = desc.reshape(1, -1)                     # **記述子として** (1, n)
    rt = np.asarray(R.matrix_to_descriptor(np.asarray(R.descriptor_to_matrix(one_row))))
    print(f"   ★非可逆点はここ 1 つだけ: **元から (1, n) の 2-D だった記述子**は "
          f"{one_row.shape} -> {rt.shape} と 1-D になる。")
    print(f"     値は {np.array_equal(np.ravel(rt), np.ravel(one_row))} = 全部残る。"
          f"落ちるのは「行が 1 本だった」というメタ情報だけ。")
    print(f"     (1, n) の行列は「1-D 記述子を包んだもの」と「行が 1 本の記述子束」を"
          f"区別できないので、")
    print(f"     どちらかを非可逆にするしかない。多数派の 1-D を厳密側に倒してある。")
    assert rt.ndim == 1 and np.array_equal(np.ravel(rt), np.ravel(one_row))
    losses.append(("descriptor(1,n) -> matrix -> descriptor", False,
                   "値は全保存。「行が 1 本」というメタ情報のみ"))

    tab = R.descriptor_to_table(desc)
    print(f"   descriptor_to_table: 次元 {tab['n']}  L2 {tab['l2']:.5f}  "
          f"非ゼロ率 {tab['nonzero_fraction']:.2%}  "
          f"上位 10 % がエネルギーの {tab['top10pct_energy']:.2%}")
    print(f"     -> 「次元だけ多くて実質ほとんど使っていない」を可視化する量。"
          f"この部品では {tab['nonzero_fraction']:.0%} の要素が働いている。")
    assert 0.0 < tab["top10pct_energy"] <= 1.0

    # ------------------------------------------------------------------ #
    _rule("5) 添字 ―― 間引きの記録。片道は bit 一致、逆向きは背景を落とす")
    # ------------------------------------------------------------------ #
    idx = np.asarray(OP["farthest_point_sampling"]["func"](points, 64))
    sub = np.asarray(R.select_points(points, idx))
    print(f"   farthest_point_sampling -> indices {idx.shape} "
          f"(値域 {idx.min()}..{idx.max()})")
    print(f"   select_points(points, indices) -> {sub.shape}  "
          f"(添字は元の集合とセットでしか意味を持たないので 2 入力)")

    def min_sep(p):
        d, _ = cKDTree(p).query(p, k=2)
        return float(d[:, 1].min())

    even = points[np.linspace(0, len(points) - 1, 64).astype(int)]
    print(f"   間引きが効いているか(最近接点間距離の最小値、大きいほど均等):")
    print(f"       FPS で 64 点   {min_sep(sub):.4f} mm")
    print(f"       等間隔に 64 点 {min_sep(even):.4f} mm   "
          f"-> FPS は {min_sep(sub) / min_sep(even):.1f} 倍離れている")
    assert sub.shape == (64, 3) and min_sep(sub) > 2.0 * min_sep(even)

    labels = np.asarray(R.indices_to_labels(idx))
    idx_back = np.asarray(R.labels_to_indices(labels))
    print(f"\n   indices {idx.shape} -> labels {labels.shape} -> indices "
          f"{idx_back.shape}   bit 一致 = "
          f"{np.array_equal(np.unique(idx), idx_back)} (重複と順序を除く)")
    assert np.array_equal(np.unique(idx), idx_back)

    full = np.zeros(len(points), dtype=np.int64)
    full[idx] = 1
    round_trip = np.asarray(R.indices_to_labels(R.labels_to_indices(full)))
    lost = len(full) - len(round_trip)
    print(f"   ★逆向きは戻らない: labels {full.shape} -> indices -> labels "
          f"{round_trip.shape}")
    print(f"     長さが max(index)+1 = {len(round_trip)} に切り詰まり、"
          f"**末尾の背景 {lost} 個**が落ちる。")
    print(f"     重なる範囲の値は完全一致 "
          f"({np.array_equal(full[:len(round_trip)], round_trip)}) なので、"
          f"落ちたのは値ではなく**配列の長さ**である。")
    assert np.array_equal(full[:len(round_trip)], round_trip) and lost > 0
    losses.append(("labels -> indices -> labels", False,
                   f"末尾の背景 {lost} 個(長さが max+1 に切り詰まる)"))

    # ------------------------------------------------------------------ #
    _rule("6) 位置 ―― 重心は (z, y, x)。1 点の点群へ戻せる")
    # ------------------------------------------------------------------ #
    pos = R.points_to_position(points)
    one_pt = np.asarray(R.position_to_points(pos))
    spread = float(np.sqrt(np.mean(np.sum((points - np.asarray(pos)) ** 2, 1))))
    print(f"   points {points.shape} -> position (z,y,x) = "
          f"({pos[0]:+.6f}, {pos[1]:+.6f}, {pos[2]:+.6f})")
    print(f"   position -> points {one_pt.shape}  bit 一致 = "
          f"{np.array_equal(one_pt[0], np.asarray(pos, float))}")
    print(f"   ★捨てた広がり RMS = {spread:.4f} mm  "
          f"({len(points)} 点 -> 1 点。position->points は可逆だが、")
    print(f"     points->position は**この量を捨てている**。可逆なのは往路が 1 点の側だけ)")
    assert np.array_equal(one_pt[0], np.asarray(pos, float))
    losses.append(("points -> position", False, f"広がり RMS {spread:.4f} mm"))

    # ------------------------------------------------------------------ #
    _rule("7) 対 ―― 高さ vs 断面積。表・密度画像・信号の 3 出口")
    # ------------------------------------------------------------------ #
    z_mm = np.arange(-8.0, 8.01, 0.25)
    area = np.where(np.abs(z_mm) <= HALF[2], 4.0 * HALF[0] * HALF[1], 0.0)
    cap = (z_mm > HALF[2]) & (z_mm <= HALF[2] + BOSS_R)
    area = area + np.where(cap, math.pi * np.maximum(
        0.0, BOSS_R ** 2 - (z_mm - HALF[2]) ** 2), 0.0)
    pairs = np.stack([z_mm, area], 1)
    tp = R.pairs_to_table(pairs)
    print(f"   高さ z [mm] と断面積 [mm²] の対 {pairs.shape}")
    print(f"   pairs_to_table: n {tp['n']}  x [{tp['x_min']:+.2f}, {tp['x_max']:+.2f}]  "
          f"y [{tp['y_min']:.2f}, {tp['y_max']:.2f}]  x_uniform {tp['x_uniform']}  "
          f"x_step {tp['x_step']:.2f}")
    print(f"     断面積の最大 {tp['y_max']:.2f} mm² は "
          f"{2 * HALF[0]:.0f} x {2 * HALF[1]:.0f} = "
          f"{4 * HALF[0] * HALF[1]:.0f} mm² ちょうど(閉形式)")
    assert tp["x_uniform"] is True and abs(tp["x_step"] - 0.25) < 1e-12
    assert abs(tp["y_max"] - 4 * HALF[0] * HALF[1]) < 1e-12

    dens = np.asarray(R.pairs_to_image2d(pairs, shape=(32, 32)))
    print(f"   pairs_to_image2d -> {dens.shape}  最大 {dens.max():.1f}  "
          f"非ゼロ bin {int((dens > 0).sum())} / {dens.size}")
    print(f"     ★x_uniform が True の対だけが :func:`pairs_to_signal` で "
          f"x を落として良い。実際 signal は")
    sig = np.asarray(R.pairs_to_signal(pairs))
    print(f"     {sig.shape} で y 列と一致 = {np.array_equal(sig, area)} —— "
          f"x が等間隔でなければ黙って壊れる。")
    assert dens.max() == 1.0 and np.array_equal(sig, area)
    losses.append(("pairs -> image2d", False,
                   f"bin 幅への量子化 + 最小-最大正規化(絶対スケールを捨てる)"))

    # ------------------------------------------------------------------ #
    _rule("8) ずれの本体 ―― 相関スコアと位相相関。整数格子なので厳密")
    # ------------------------------------------------------------------ #
    vol_a = build_volume()
    vol_b = np.roll(vol_a, TRUE_ROLL, axis=(0, 1, 2))
    print(f"   体積 {vol_a.shape}  占有 {int(vol_a.sum())} voxel。"
          f"2 回目は (dz,dy,dx) = {TRUE_ROLL} だけ巡回シフト")

    score = R.correlation_score(vol_a, vol_b)
    peak = R.score_to_position(score)
    expect = tuple(s % VOX_N for s in TRUE_ROLL)
    print(f"   correlation_score -> score {np.asarray(score).shape}  "
          f"最大 {float(np.asarray(score).max()):.6f}")
    print(f"   score_to_position -> {tuple(int(v) for v in peak)}  "
          f"真値(巡回なので mod {VOX_N}) {expect}   ★厳密一致")
    assert tuple(int(v) for v in peak) == expect
    assert abs(float(np.asarray(score).max()) - 1.0) < 1e-9

    mip = np.asarray(R.score_to_image2d(score, axis=0))
    print(f"   score_to_image2d(axis=0) -> {mip.shape} 最大値投影(z を潰す)")
    extents = {}
    for frac in (0.98, 0.95, 0.90):
        sel = mip > frac * mip.max()
        rows, cols = np.nonzero(sel)
        extents[frac] = (int(rows.max() - rows.min()) + 1,
                         int(cols.max() - cols.min()) + 1)
        print(f"     ピークの {frac:.2f} 倍以上: {int(sel.sum()):2d} 画素  "
              f"(y 方向 {extents[frac][0]} px x x 方向 {extents[frac][1]} px)")
    print(f"   ★{0.98:.2f} 倍では 1 画素 = 対応は一意。ただし裾は等方ではない —— "
          f"0.90 倍で見ると")
    print(f"     x 方向 {extents[0.90][1]} px に対し y 方向 {extents[0.90][0]} px と、"
          f"**部品が長い x 方向のほうが緩い**。")
    print(f"     ブロックは x に {4 * HALF[0]:.0f} voxel、y に {4 * HALF[1]:.0f} voxel "
          f"なので、長辺に沿って滑らせても重なりが減りにくい。")
    print(f"     最大値投影は「ピークが 1 本か」だけでなく"
          f"**どの向きの位置合わせが効いていないか**を見せる。")
    assert int((mip > 0.98 * mip.max()).sum()) == 1
    assert extents[0.90][1] > extents[0.90][0]
    losses.append(("score -> position", False,
                   "体積 1 個 -> 1 点(整数格子の argmax。副画素は refine_peak_newton の仕事)"))

    shift = OP["match_phase_3d"]["func"](vol_a, vol_b)
    vec = np.asarray(R.shift_to_vector(shift))
    shift_back = R.vector_to_shift(vec)
    print(f"\n   match_phase_3d -> shift {tuple(int(s) for s in shift)}  "
          f"(b を a に合わせる向きなので roll の符号違い)")
    print(f"   shift -> vector {vec.tolist()} -> shift "
          f"{tuple(int(s) for s in shift_back)}   bit 一致 = "
          f"{tuple(shift_back) == tuple(int(s) for s in shift)}")
    assert tuple(shift_back) == tuple(int(s) for s in shift)
    assert tuple(-int(s) for s in shift) == TRUE_ROLL

    frac = np.array([1.4, -2.6, 0.5])
    rounded = R.vector_to_shift(frac)
    resid = float(np.abs(frac - np.asarray(rounded, float)).max())
    print(f"   ★逆向きは不可逆: vector {frac.tolist()} -> shift {tuple(rounded)}  "
          f"丸め残差 max {resid:.3f}")
    print(f"     上界は各軸 0.5(最近接偶数丸めなので 0.5 は 0 へ落ちる)。"
          f"整数を渡した往復だけが bit 一致する。")
    assert resid <= 0.5
    losses.append(("vector -> shift", False, f"最近接整数への丸め(上界 0.5、実測 {resid:.3f})"))

    # ------------------------------------------------------------------ #
    _rule("9) 回転と倍率 ―― 2 数と行列の往復。せん断は黙って消える")
    # ------------------------------------------------------------------ #
    rotated = ndimage.rotate(vol_a, TRUE_ANGLE_DEG, axes=(1, 2),
                             reshape=False, order=1)
    rs = OP["match_logpolar_z"]["func"](vol_a, rotated)
    print(f"   match_logpolar_z -> (角度 {rs[0]:+.3f} 度, 倍率 {rs[1]:.4f})  "
          f"真値 ({TRUE_ANGLE_DEG:+.1f} 度, 1.0000)")
    print(f"     誤差 角度 {abs(rs[0] - TRUE_ANGLE_DEG):.3f} 度 / 倍率 "
          f"{rs[1] - 1.0:+.4f}  —— coarse 推定器の公称 2-5 度と一致")
    M = np.asarray(R.rot_scale_to_matrix(rs))
    rs_back = R.matrix_to_rot_scale(M)
    err = max(abs(rs_back[0] - rs[0]), abs(rs_back[1] - rs[1]))
    print(f"   rot_scale -> matrix {M.shape} -> rot_scale   max|Δ| = {err:.3e}")
    print("   きれいな値でも同じか(度と無次元、範囲を広く取る):")
    worst = 0.0
    for pair in ((30.0, 1.25), (-75.0, 0.4), (179.0, 3.0), (0.0, 1.0)):
        b = R.matrix_to_rot_scale(R.rot_scale_to_matrix(pair))
        e = max(abs(b[0] - pair[0]), abs(b[1] - pair[1]))
        worst = max(worst, e)
        print(f"     ({pair[0]:+7.1f} 度, x{pair[1]:.2f}) -> "
              f"({b[0]:+.10f}, {b[1]:.10f})  max|Δ| = {e:.1e}")
    assert worst < 1e-13 and err < 1e-13

    sheared = np.array([[1.0, 0.3], [0.0, 1.0]])
    rs_sh = R.matrix_to_rot_scale(sheared)
    residual = float(np.abs(sheared - np.asarray(R.rot_scale_to_matrix(rs_sh))).max())
    print(f"   ★せん断を含む行列 [[1, 0.3], [0, 1]] を渡すと "
          f"({rs_sh[0]:+.4f} 度, x{rs_sh[1]:.4f}) が**例外なく**返る。")
    print(f"     残差 |M - rot_scale_to_matrix(...)| = {residual:.3f} が"
          f"黙って消えているので、")
    print(f"     相似変換だと信じてよいかは呼び出し側が残差を取って確かめるしかない。")
    assert abs(residual - 0.3) < 1e-12
    losses.append(("matrix -> rot_scale", False,
                   f"相似成分だけを読む(せん断の残差 {residual:.3f} が例外なく消える)"))

    # ------------------------------------------------------------------ #
    _rule("10) フロー ―― 点ごとの対応。小運動は厳密、大運動で形が縮む")
    # ------------------------------------------------------------------ #
    grid = np.stack(np.meshgrid(np.arange(8.0), np.arange(8.0), np.arange(4.0),
                                indexing="ij"), -1).reshape(-1, 3) * 1.5
    small = np.array([0.20, -0.35, 0.15])          # 点間隔 1.5 より十分小さい
    moved_truth = grid + small
    flow = np.asarray(OP["estimate_flow"]["func"](grid, moved_truth))
    applied = np.asarray(R.flow_apply(grid, flow))
    speed = np.asarray(R.flow_speed(flow))
    print(f"   格子 {grid.shape}(間隔 1.5 mm)を {small.tolist()} 動かす")
    print(f"   estimate_flow -> flow {flow.shape}  "
          f"真の変位との max|Δ| = {np.abs(flow - small).max():.3e}")
    print(f"   flow_apply(points, flow) -> 移動後との max|Δ| = "
          f"{np.abs(applied - moved_truth).max():.3e}  ★厳密")
    print(f"   flow_speed -> {speed.shape}  平均 {speed.mean():.6f}  "
          f"|変位| = {np.linalg.norm(small):.6f}")
    assert np.abs(applied - moved_truth).max() < 1e-12
    assert abs(speed.mean() - np.linalg.norm(small)) < 1e-12

    big = np.array([2.0, 0.0, 0.0])                # 点間隔 1.5 を超える
    applied_big = np.asarray(R.flow_apply(
        grid, np.asarray(OP["estimate_flow"]["func"](grid, grid + big))))
    uniq = len(np.unique(np.round(applied_big, 9), axis=0))
    print(f"   ★変位 {big[0]:.1f} mm(点間隔 1.5 mm 超)にすると: "
          f"移動後との max|Δ| = {np.abs(applied_big - (grid + big)).max():.3f}")
    print(f"     {len(grid)} 点が {uniq} か所へ落ちる = **{len(grid) - uniq} 点ぶん"
          f"形が縮む**。最近傍フローは")
    print(f"     対応が全単射のときだけ厳密で、そうでなければ複数の点が同じ点を"
          f"選ぶ —— 例外は出ない。")
    assert uniq < len(grid)
    losses.append(("flow_apply(大運動)", False,
                   f"{len(grid)} 点 -> {uniq} か所({len(grid) - uniq} 点が潰れる)"))

    # 密フロー -> 色相環。dz は捨てる(捨てたことを明示するのが契約)
    depth, hgt, wid = 5, 32, 48
    gy, gx = np.mgrid[0:hgt, 0:wid].astype(float)
    cyy, cxx = (hgt - 1) / 2.0, (wid - 1) / 2.0
    dense = np.zeros((3, depth, hgt, wid))
    dense[0] = 1.0                                  # dz(捨てられる)
    dense[1] = (gx - cxx)[None]                     # dy
    dense[2] = -(gy - cyy)[None]                    # dx
    rgb = np.asarray(R.flow_to_rgbimage(dense))
    print(f"\n   密フロー {dense.shape}(回転場)-> flow_to_rgbimage {rgb.shape}  "
          f"値域 [{rgb.min():.1f}, {rgb.max():.1f}]")
    print("     位置            dy      dx    色相 [度]   atan2(dy,dx) [度]")
    hue_err = 0.0
    for row, col, tag in ((int(cyy), wid - 1, "右端"), (0, int(cxx), "上端"),
                          (int(cyy), 0, "左端"), (hgt - 1, int(cxx), "下端")):
        h, _, v = colorsys.rgb_to_hsv(*rgb[row, col])
        dy, dx = dense[1, depth // 2, row, col], dense[2, depth // 2, row, col]
        want = math.degrees(math.atan2(dy, dx)) % 360.0
        hue_err = max(hue_err, abs((h * 360.0 - want + 180.0) % 360.0 - 180.0))
        print(f"     {tag:6s}   {dy:+8.1f} {dx:+7.1f}   {h * 360.0:8.2f}   "
              f"{want:12.2f}")
    print(f"   色相 = atan2(dy, dx) の最大差 {hue_err:.2e} 度。"
          f"**dz は捨てている** —— 混ぜると")
    print(f"     「見えている色が何の量か」が誰にも言えなくなるため。凡例は"
          f"図の側で必ず一緒に焼くこと。")
    assert hue_err < 1e-6 and 0.0 <= rgb.min() and rgb.max() <= 1.0
    losses.append(("flow_dense -> rgbimage", False,
                   "z 成分と、明度の基準にした絶対速さ(一方向)"))

    # ------------------------------------------------------------------ #
    _rule("11) 変形 ―― TPS の制御点だけが取り出せる")
    # ------------------------------------------------------------------ #
    src = points[np.linspace(0, len(points) - 1, 24).astype(int)]
    dst = src + np.array([0.10, -0.20, 0.30])
    model = OP["tps_fit"]["func"](src, dst)
    ctrl = np.asarray(R.deformation_to_points(model))
    print(f"   tps_fit({src.shape}, {dst.shape}) -> deformation "
          f"{{{', '.join(sorted(model))}}}")
    print(f"   deformation_to_points -> {ctrl.shape}  src と bit 一致 = "
          f"{np.array_equal(ctrl, src)}")
    print(f"   ★一方向: 制御点だけからは曲げ係数 w {np.asarray(model['w']).shape} と "
          f"アフィン項 a {np.asarray(model['a']).shape} は復元できない。")
    print(f"     「この歪みはどこに固定されているか」しか答えられない変換である。")
    assert np.array_equal(ctrl, src)
    losses.append(("deformation -> points", False,
                   f"曲げ係数 w{np.asarray(model['w']).shape} と "
                   f"アフィン項 a{np.asarray(model['a']).shape}"))

    # ------------------------------------------------------------------ #
    _rule("12) 複素スカラ ―― 周回積分 ∮dz/z = 2πi(閉形式)")
    # ------------------------------------------------------------------ #
    m = 2048
    theta = np.linspace(0.0, 2.0 * math.pi, m, endpoint=False)
    circle = np.exp(1j * theta)
    val = mathops.cplx_contour_integral(circle, 1.0 / circle)
    polar = np.asarray(R.cscalar_to_polar(val))
    restored = R.polar_to_cscalar(polar)
    print(f"   単位円 {m} 点上の ∮dz/z = {val:.9f}   真値 2πi = {2j * math.pi:.9f}")
    print(f"   cscalar_to_polar -> pairs {polar.shape} = "
          f"[|z| {polar[0, 0]:.6f}, arg {polar[0, 1]:.6f} 度]")
    print(f"     真値 |2πi| = {2 * math.pi:.6f}(差 "
          f"{abs(polar[0, 0] - 2 * math.pi):.2e} = {m} 点の離散化)、"
          f"arg = 90 度ちょうど(差 {abs(polar[0, 1] - 90.0):.1e})")
    rt_c = max(abs(restored.real - val.real), abs(restored.imag - val.imag))
    print(f"   polar_to_cscalar -> {restored:.9f}   往復 max|Δ| = {rt_c:.3e}")
    print(f"   ★複素スカラが measurement(実スカラ)と別の型なのは、混ぜると"
          f"下流が生の TypeError で落ちるから。")
    print(f"     極形式の**対**にすると 1-D 語彙へ渡せる —— それがこの 2 op の仕事。")
    assert abs(polar[0, 1] - 90.0) < 1e-9
    assert abs(polar[0, 0] - 2 * math.pi) < 1e-4
    assert rt_c < 1e-12

    # ------------------------------------------------------------------ #
    _rule("13) まとめ ―― 戻るものと、戻らないときに落ちる量")
    # ------------------------------------------------------------------ #
    exact = [("position -> points", "bit 一致"),
             ("indices -> labels -> indices", "bit 一致(重複と順序を除く)"),
             ("descriptor(1-D) -> matrix -> descriptor", "bit 一致"),
             ("shift -> vector -> shift", "bit 一致"),
             ("deformation -> points(ctrl)", "bit 一致"),
             ("correlation_score のピーク位置", "厳密一致(整数格子)"),
             ("flow_apply(小運動)", f"max|Δ| < 1e-12"),
             ("rot_scale -> matrix -> rot_scale", f"max|Δ| = {worst:.1e}"),
             ("cscalar -> polar -> cscalar", f"max|Δ| = {rt_c:.1e}")]
    print("   ● 戻るもの")
    for tag, note in exact:
        print(f"       {tag:44s} {note}")
    print("   ● 戻らないもの(落ちた量を必ず数字で)")
    for tag, _, note in losses:
        print(f"       {tag:44s} {note}")
    print(f"\n   ★★正直な結論 ―― 「往復して戻った」は主張ではない。"
          f"戻らない側を {len(losses)} 件、")
    print(f"     すべて**量つきで**書けて初めて、この一覧は表現変換の仕様になる。")
    assert len(exact) == 9 and len(losses) == 12

    # ------------------------------------------------------------------ #
    _rule("14) fail-closed ―― 黙って通さない")
    # ------------------------------------------------------------------ #
    cases = [
        ("主曲率を np.asarray してから渡す((2,N) は (N,2) ではない)",
         lambda: R.curvature_to_table(np.asarray(OP["principal_curvatures"]["func"](
             points[:50], k=10)))),
        ("零ベクトルの法線から EGI",
         lambda: R.normals_to_egi(np.zeros((4, 3)))),
        ("EGI の bin 数 0", lambda: R.normals_to_egi(true_normals, n_az=0)),
        ("範囲外の添字で点を選ぶ",
         lambda: R.select_points(points, np.array([0, len(points)]))),
        ("負の添字をラベルにする",
         lambda: R.indices_to_labels(np.array([-1, 3]))),
        ("非背景が 1 つも無いラベル",
         lambda: R.labels_to_indices(np.zeros(16, int))),
        ("長さ 2 の position", lambda: R.position_to_points((1.0, 2.0))),
        ("倍率 0 の rot_scale", lambda: R.rot_scale_to_matrix((30.0, 0.0))),
        ("退化した (2,2) から rot_scale",
         lambda: R.matrix_to_rot_scale(np.zeros((2, 2)))),
        ("(1,2) でない極形式", lambda: R.polar_to_cscalar(np.zeros((2, 2)))),
        ("負の |z| の極形式", lambda: R.polar_to_cscalar(np.array([[-1.0, 0.0]]))),
        ("散在フローを密 op へ", lambda: R.flow_to_rgbimage(flow)),
        ("密フローを散在 op へ", lambda: R.flow_speed(dense)),
        ("行数の違う点群とフロー", lambda: R.flow_apply(grid, flow[:10])),
        ("範囲外の z スライス",
         lambda: R.flow_to_rgbimage(dense, index=99)),
        ("3-D でない score", lambda: R.score_to_position(np.zeros((4, 4)))),
        ("範囲外の axis", lambda: R.score_to_image2d(np.zeros((4, 4, 4)), axis=3)),
        ("定数体積どうしの相関",
         lambda: R.correlation_score(np.ones((8,) * 3), np.ones((8,) * 3))),
        ("ctrl を持たない変形", lambda: R.deformation_to_points({"w": 1})),
        ("非有限を含む対", lambda: R.pairs_to_table(
            np.array([[0.0, 1.0], [1.0, np.inf]]))),
        ("小入力から巨大な密度画像",
         lambda: R.pairs_to_image2d(np.zeros((3, 2)), shape=(40000, 40000))),
    ]
    leaked = 0
    for tag, fn in cases:
        try:
            fn()
        except ValueError as exc:
            print(f"   拒否 {tag:44s}: {str(exc).split(';')[0][:52]}")
        else:
            leaked += 1
            print(f"   ★通過 {tag:44s}: 拒否されなかった")
    print(f"\n   {len(cases) - leaked}/{len(cases)} が文書化された ValueError で拒否")
    if leaked:
        ok = False

    print(f"\nPASS: 部品 1 個のずれ (dz,dy,dx)={TRUE_ROLL} / 回転 "
          f"{TRUE_ANGLE_DEG:.0f} 度 を 12 系統の表現で往復させ、")
    print(f"      可逆 {len(exact)} 件は誤差 0 〜 {max(rt_c, worst):.0e}、"
          f"不可逆 {len(losses)} 件は落ちた量を数値で確定した。")
    print(f"      reprconv 42 op のうち 26 op を実行 "
          f"(例の無かった 21 op すべてを含む)。")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
