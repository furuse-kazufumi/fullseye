# -*- coding: utf-8 -*-
"""事例: 3-D テンプレートを NCC/形状/chamfer/Hough/MIP/曲率 の 6 手法で定位する (match_localize).

平たく言うと: 「この部品(テンプレート)はシーンのどこにあるか」を 3-D voxel / 点群で答えるのが
テンプレート定位。cv2 に 3-D matchTemplate は無く、match3d はこれを **6 通りの原理** で解く:
    - match_points_ncc  : 点群を splat して voxel 化 → 正規化相互相関(NCC)
    - match_shape_3d    : 単位勾配ベクトルの内積和(輪郭/形状ベース、強度不変)
    - match_chamfer_3d  : シーン・エッジの距離場にテンプレ・エッジを載せた距離和(遮蔽に頑健)
    - match_hough_3d    : 勾配方向ビンごとの投票(generalized Hough)
    - match_mip_2d      : 直交 3 方向の最大値投影 → 2-D NCC を 3 枚束ねて 3-D 復元
    - match_curvature_3d: shape-index(曲率)場の NCC(局所曲面形状で一致を測る)
本事例はこの 6 手法を **同一シーン・同一真値** に当て、全員が同じ場所へ収束することを示す。

シーンは「同じピーク濃度」の **球(=テンプレート形状)** と **立方体(=おとり)** を離して置く。
球の表面点群(match_points_ncc 用)と、球の解析的 smooth 占有場(voxel 5 手法用)は同一幾何から
生成するので、6 手法は文字通り同じ対象を別表現で見ている(compose)。

検証(GT): 球の中心の真の連続座標 p_true をコード側が握っている(world 座標 == voxel index に
なる bounds を張るため、点群 splat と解析 voxel が同一座標系)。各手法が返すピーク位置(テンプレ
中心)が p_true を **2 voxel 以内**(球半径 R=8 の 1/4 未満)で復元することを assert する。

beat-the-null: おとりの立方体は球と **ピーク濃度が一致**(下で数値確認)するので、明るさ/サイズだけ
見る素朴な blob 探索では球と区別できない(=null)。各手法の復元位置が真の球には ~0.5vox・おとりには
~29vox という桁違いの差で寄る=6 手法とも「形/エッジ/曲率」で球を選び、濃度 null を判別的に棄却した
証拠。さらに 6 手法の復元位置が互いに 2.5vox 以内へ収束することも確かめる(独立手法の合致)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np
import match3d as X

# ── パラメータ(すべて voxel 単位。bounds=(0,N-1) なので world 座標 == voxel index)──
N = 56                                   # シーン格子
R = 8.0                                  # 球(テンプレート)半径
W = 1.2                                  # 表面の滑らかさ(tanh 帯幅)
M = 23                                   # テンプレート格子(中心に球を描く)
p_true = np.array([19.0, 23.5, 33.6])    # ★真値: 球の中心(コードだけが知る)
p_decoy = np.array([39.2, 35.8, 16.8])   # おとりの立方体の中心(離して配置)
half = R * 0.85                          # 立方体の半辺
bounds = (np.zeros(3), np.full(3, N - 1.0))
sep = float(np.linalg.norm(p_true - p_decoy))    # 真値↔おとり間隔(~29vox)


# ── 幾何: 解析的な smooth 占有場(球/立方体)と表面点群(同一幾何)──────────────
def _grid(n):
    a = np.arange(n)
    return np.stack(np.meshgrid(a, a, a, indexing="ij"), -1).astype(np.float64)


def sphere_vol(n, center, r, w=W):
    """符号付き距離の tanh = 滑らかな充実球(等値面がきれいで曲率が安定)。"""
    d = np.linalg.norm(_grid(n) - center, axis=-1)
    return 0.5 * (1.0 - np.tanh((d - r) / w))


def cube_vol(n, center, h, w=W):
    """chebyshev 距離の tanh = 滑らかな立方体(球と同じピーク濃度のおとり)。"""
    d = np.max(np.abs(_grid(n) - center), axis=-1)
    return 0.5 * (1.0 - np.tanh((d - h) / w))


def sphere_surf(center, r, k, seed):
    g = np.random.default_rng(seed)
    u = g.standard_normal((k, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)
    return np.asarray(center) + r * u


def cube_surf(center, h, k, seed):
    g = np.random.default_rng(seed)
    p = g.uniform(-h, h, (k, 3))
    face = g.integers(0, 3, k)
    p[np.arange(k), face] = g.choice([-1.0, 1.0], k) * h
    return np.asarray(center) + p


# voxel 表現(球=ターゲット と 立方体=おとり を同一格子へ)。max=論理和的な重ね置き。
scene_vol = np.maximum(sphere_vol(N, p_true, R), cube_vol(N, p_decoy, half))
template_vol = sphere_vol(M, np.full(3, (M - 1) / 2.0), R)     # 中心に球を描いたテンプレ

# 点群表現(同一幾何の表面点)。model は任意位置でよい(内部で bbox 切出し→探索)。
scene_pts = np.vstack([sphere_surf(p_true, R, 4000, 1),
                       cube_surf(p_decoy, half, 4000, 2)])
model_pts = sphere_surf(np.full(3, N / 2.0), R, 4000, 3)

# beat-the-null の前提: 球とおとりの「ピーク濃度」が一致 = 明るさでは区別不能 ----------
core_sphere = float(scene_vol[tuple(np.floor(p_true).astype(int))])
core_decoy = float(scene_vol[tuple(np.floor(p_decoy).astype(int))])
assert abs(core_sphere - core_decoy) < 1e-2, \
    f"おとりと球のピーク濃度が違うと濃度nullが成立しない: {core_sphere:.4f} vs {core_decoy:.4f}"


def err_true(pos):
    return float(np.linalg.norm(np.asarray(pos, float)[:3] - p_true))


def err_decoy(pos):
    return float(np.linalg.norm(np.asarray(pos, float)[:3] - p_decoy))


TOL = 2.0        # 真値許容(voxel)。R=8 の 1/4 未満
NULL = 20.0      # おとりまでこれ以上離れていれば「球を選んだ」と言える(間隔 ~29)

recovered = {}   # 手法名 -> 復元位置(3,)

# ── 1) 点群 NCC: 表面点を splat → 3-D NCC ─────────────────────────────────────
r_pts = X.match_points_ncc(scene_pts, model_pts, N, bounds, smooth=0.8)
recovered["points_ncc"] = r_pts[1:]
r_pts2 = X.match_points_ncc(scene_pts, model_pts, N, bounds, smooth=0.8)
assert np.array_equal(r_pts, r_pts2), "点群NCCが非決定的"
assert r_pts[0] > 0.5, f"NCCスコアが低すぎ(一致が弱い): {r_pts[0]:.3f}"
assert err_true(r_pts[1:]) <= TOL and err_decoy(r_pts[1:]) > NULL
print(f"points_ncc   : pos={np.round(r_pts[1:],2)} ncc={r_pts[0]:.3f} "
      f"e_true={err_true(r_pts[1:]):.2f} e_decoy={err_decoy(r_pts[1:]):.2f}")

# ── 2) 形状(勾配方向)マッチング ─────────────────────────────────────────────
r_shape = X.match_shape_3d(scene_vol, template_vol)
recovered["shape_3d"] = r_shape[1:]
assert r_shape[0] > 0.5, f"形状一致スコアが低い: {r_shape[0]:.3f}"
assert err_true(r_shape[1:]) <= TOL and err_decoy(r_shape[1:]) > NULL
print(f"shape_3d     : pos={np.round(r_shape[1:],2)} score={r_shape[0]:.3f} "
      f"e_true={err_true(r_shape[1:]):.2f} e_decoy={err_decoy(r_shape[1:]):.2f}")

# ── 3) chamfer / 距離場マッチング(スコアは低いほど良い)──────────────────────
r_cham = X.match_chamfer_3d(scene_vol, template_vol)
recovered["chamfer_3d"] = r_cham[1:]
assert r_cham[0] < 1.0, f"chamfer距離が大(エッジが重なっていない): {r_cham[0]:.3f}"
assert err_true(r_cham[1:]) <= TOL and err_decoy(r_cham[1:]) > NULL
print(f"chamfer_3d   : pos={np.round(r_cham[1:],2)} dist={r_cham[0]:.3f}(小=良) "
      f"e_true={err_true(r_cham[1:]):.2f} e_decoy={err_decoy(r_cham[1:]):.2f}")

# ── 4) generalized Hough(投票 accumulator、topk 対応)────────────────────────
r_hough = X.match_hough_3d(scene_vol, template_vol)
assert r_hough.shape == (1, 4), f"topk=1 の形が想定外: {r_hough.shape}"
recovered["hough_3d"] = r_hough[0, 1:]
assert r_hough[0, 0] > 0.4, f"投票ピークが弱い: {r_hough[0,0]:.3f}"
assert err_true(r_hough[0, 1:]) <= TOL and err_decoy(r_hough[0, 1:]) > NULL
print(f"hough_3d     : pos={np.round(r_hough[0,1:],2)} votes={r_hough[0,0]:.3f} "
      f"e_true={err_true(r_hough[0,1:]):.2f} e_decoy={err_decoy(r_hough[0,1:]):.2f}")

# ── 5) MIP 投影 → 2-D NCC(位置のみ返す)─────────────────────────────────────
r_mip = X.match_mip_2d(scene_vol, template_vol)
recovered["mip_2d"] = r_mip
assert r_mip.shape == (3,), f"MIP は 3 座標を返すはず: {r_mip.shape}"
assert err_true(r_mip) <= TOL and err_decoy(r_mip) > NULL
print(f"mip_2d       : pos={np.round(r_mip,2)} "
      f"e_true={err_true(r_mip):.2f} e_decoy={err_decoy(r_mip):.2f}")

# ── 6) 曲率(shape-index)マッチング ─────────────────────────────────────────
r_curv = X.match_curvature_3d(scene_vol, template_vol)
recovered["curvature_3d"] = r_curv[1:]
assert r_curv[0] > 0.3, f"曲率場NCCが低い: {r_curv[0]:.3f}"
assert err_true(r_curv[1:]) <= TOL and err_decoy(r_curv[1:]) > NULL
print(f"curvature_3d : pos={np.round(r_curv[1:],2)} score={r_curv[0]:.3f} "
      f"e_true={err_true(r_curv[1:]):.2f} e_decoy={err_decoy(r_curv[1:]):.2f}")

# ── 合議: 6 手法の復元位置が同一点へ収束(独立手法の合致)────────────────────
P6 = np.array([recovered[k] for k in
               ("points_ncc", "shape_3d", "chamfer_3d", "hough_3d", "mip_2d", "curvature_3d")])
centroid = P6.mean(0)
spread = float(np.max(np.linalg.norm(P6 - centroid, axis=1)))     # 合議のばらつき
mean_e_true = float(np.mean(np.linalg.norm(P6 - p_true, axis=1)))
mean_e_decoy = float(np.mean(np.linalg.norm(P6 - p_decoy, axis=1)))
assert spread <= 2.5, f"6 手法が同一点へ収束していない(spread={spread:.2f})"
assert mean_e_true < 0.15 * mean_e_decoy, \
    f"真値への寄りがおとりnullを判別的に上回れていない: {mean_e_true:.2f} vs {mean_e_decoy:.2f}"

print(f"\n合議: centroid={np.round(centroid,2)} 真値={p_true} "
      f"spread={spread:.2f}vox / 平均 e_true={mean_e_true:.2f} vs e_decoy={mean_e_decoy:.2f}")
print(f"PASS: 6 手法(points_ncc/shape/chamfer/hough/mip/curvature)が同一シーンの球テンプレを "
      f"真値±{TOL}vox(実測 spread {spread:.2f}vox)で定位。球とおとり立方体は濃度一致 "
      f"({core_sphere:.3f}≈{core_decoy:.3f})=明るさでは不可分だが、全手法が形状で球を選び "
      f"おとり(~{sep:.0f}vox 先)を判別的に棄却")
