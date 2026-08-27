# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 深度カメラの画像から「面の向き」と「段差(遮蔽エッジ)」を読み取る (range image).

平たく言うと: 深度カメラ(RGB-D / ToF)は、画素の格子ごとに「そこまでの距離」を並べた
organized(格子整列)な深度画像を出す。ロボットが物を掴んだり歩いたりするには、この
距離画像から (1) 各点の面がどっちを向いているか(法線) (2) 手前の物と奥の背景が切れる
「段差(遮蔽エッジ)」がどこか、を知りたい。

このサンプルは、傾いた背景平面(途中に段差あり)と、その手前に置いた球だけからなる
解析的な深度画像を合成し、次の 3 つの op を素直に数珠つなぎ(chain)する:
  1. depth_to_organized_points  深度画像 → 格子整列の 3D 点群 (H,W,3)
  2. normals_from_depth         格子構造を使い、隣接画素の外積で向き付き法線
  3. occlusion_edges            深度の不連続(段差)= 遮蔽エッジを検出

方法(なぜ格子構造を使うか): 非整列の点群だと近傍探索(kNN)が要り符号も曖昧だが、
organized 深度なら「隣の画素」がそのまま接線方向になり、外積一発で向き付き法線が出る。
段差は深度の「傾き(slope)」でなく「不連続(step)」なので、一階勾配ではなく二階差分で拾う。

検証(GT, 解析的真値):
  - 平面は depth = z0 + su*u の一次式なので、面の真の法線は解析的に (su,0,-1) 方向と分かる。
    → normals_from_depth の平面部の法線が、この真の向きと角度誤差 < 5 度で一致するか。
  - 段差は既知の列に仕込むので、occlusion_edges がその既知位置に立つ(検出率高)か、
    かつ平坦(傾いてはいるが連続)な平面部で誤検出しないか。

beat-the-null(ナイーブ手法に勝つことの明示):
  - 法線の null = 「全部カメラ正面向き (0,0,-1) だと決め打ち」。傾いた平面では大きく外す。
  - 段差の null = 「生の一階深度勾配がしきい値を超えたら段差」。一様な傾斜面でも勾配は立つので、
    傾きを段差と誤検出する。二階差分を使う occlusion_edges は一様傾斜では ≈0 で、段差だけを拾う。
  本サンプルは両方について、実手法が null を明確に上回ることを assert する。
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from range_image import (
    depth_to_organized_points,
    normals_from_depth,
    occlusion_edges,
)


def angle_between_deg(a, b):
    """2 つの単位ベクトル(群)のなす角(度)。a,b は (...,3)。"""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    dot = np.sum(a * b, axis=-1)
    return np.degrees(np.arccos(np.clip(dot, -1.0, 1.0)))


def naive_gradient_edges(depth, rel_thresh=0.05):
    """ナイーブな null: 一階勾配の大きさを局所深度で正規化して閾値化 → bool HxW。

    occlusion_edges と同じ正規化・同じ閾値だが、二階差分の代わりに一階勾配を使う。
    段差(step)では勾配が立つので検出できるが、一様な傾斜(slope)でも勾配は 0 でないため、
    傾いた平面をまるごと段差と誤検出してしまう(= これが打ち破るべき null)。
    """
    d = np.asarray(depth, float)
    gy = np.zeros_like(d)
    gx = np.zeros_like(d)
    gy[1:-1, :] = (d[2:, :] - d[:-2, :]) / 2.0   # 一階(中心差分)
    gx[:, 1:-1] = (d[:, 2:] - d[:, :-2]) / 2.0
    grad = np.maximum(np.abs(gx), np.abs(gy))
    valid = np.isfinite(d) & (d > 0)
    med = np.median(d[valid]) if np.any(valid) else 1.0
    denom = np.where(valid & (np.abs(d) > 1e-12), np.abs(d), med)
    rel = grad / denom
    return np.isfinite(rel) & (rel > rel_thresh)


def build_scene(H=64, W=64, z0=5.0, su=0.8, u_step=40, step=6.0,
                uc=20, vc=45, radius=8.0, cz=11.0):
    """球 + 段差つき傾斜平面 の解析的な organized 深度画像を作る。

    背景平面: depth = z0 + su*u(列方向に一様傾斜)。u >= u_step で +step の段差(不連続)。
    球       : 中心画素 (uc,vc)・半径 radius・中心深度 cz。前面(手前=小さい深度)が平面より
               手前に出るように置く → 球のシルエットが遮蔽エッジになる。
    返り値: depth (H,W), および真値算出に使う格子 (uu,vv) と球マスク。
    """
    vv, uu = np.meshgrid(np.arange(H), np.arange(W), indexing="ij")
    uu = uu.astype(float)
    vv = vv.astype(float)

    # 傾いた背景平面(連続)。傾きは列方向のみ。
    depth = z0 + su * uu
    # 途中から一段(不連続な段差)を足す = 遮蔽エッジ。
    depth = depth + np.where(uu >= u_step, step, 0.0)

    # 手前に球。前面(近い側)の深度 = cz - sqrt(R^2 - r^2)。球が平面より手前なら見える。
    r2 = (uu - uc) ** 2 + (vv - vc) ** 2
    inside = r2 <= radius ** 2
    sphere_depth = np.full_like(depth, np.inf)
    sphere_depth[inside] = cz - np.sqrt(radius ** 2 - r2[inside])
    sphere_visible = inside & (sphere_depth < depth)  # 平面より手前だけ球が見える
    depth = np.where(sphere_visible, sphere_depth, depth)

    return depth, uu, vv, sphere_visible


def main():
    # --- 1) 合成: 球 + 段差つき傾斜平面 の深度画像(既知パラメータ=解析的真値) ---
    H = W = 64
    z0, su = 5.0, 0.8            # 平面: depth = z0 + su*u
    u_step, step = 40, 6.0       # 列 u_step で深度が step だけ不連続に飛ぶ(段差)
    uc, vc, radius, cz = 20, 45, 8.0, 11.0
    depth, uu, vv, sphere_visible = build_scene(
        H, W, z0, su, u_step, step, uc, vc, radius, cz)

    # --- 2) chain その 1: 深度画像 → 格子整列 3D 点群 ---
    pts = depth_to_organized_points(depth)          # 正射(intrinsics 無し)→ P=(u,v,depth)
    # GT: intrinsics 無しでは点は素直に (列, 行, 深度)。既知画素で厳密一致を確認。
    vv_i, uu_i = 33, 7                              # 平面上の適当な画素(球・段差の外)
    expect = np.array([uu_i, vv_i, depth[vv_i, uu_i]])
    recon_err = float(np.linalg.norm(pts[vv_i, uu_i] - expect))
    assert pts.shape == (H, W, 3), f"点群の形が不正: {pts.shape}"
    assert recon_err < 1e-9, f"格子点の復元が真値と一致しない: {recon_err}"

    # --- 3) chain その 2: 深度 → 向き付き法線 ---
    normals = normals_from_depth(depth)             # 正射・カメラ向きに符号統一
    assert normals.shape == (H, W, 3), f"法線の形が不正: {normals.shape}"

    # 真の平面法線(解析): 面 z=z0+su*u の法線 ∝ (-su,0,1)。カメラ(原点)向きに符号を
    # 揃えると (su,0,-1)/|.|(視線 -P との内積が負のとき反転される、と op 仕様に一致)。
    true_n = np.array([su, 0.0, -1.0])
    true_n = true_n / np.linalg.norm(true_n)

    # 平面だけの清浄な帯(球 v37-53 と段差 u=40 から離す)で法線誤差を測る。
    strip = (vv >= 5) & (vv <= 25) & (uu >= 5) & (uu <= 30)
    ang = angle_between_deg(normals[strip], true_n[None, :])
    plane_mean_ang = float(ang.mean())
    plane_max_ang = float(ang.max())

    # 法線の null: 「全部カメラ正面 (0,0,-1)」と決め打ち。傾いた平面では真値と大きくずれる。
    null_n = np.array([0.0, 0.0, -1.0])
    null_normal_ang = float(angle_between_deg(true_n, null_n))

    # --- 4) chain その 3: 深度 → 遮蔽エッジ(段差検出) ---
    edges = occlusion_edges(depth, rel_thresh=0.05)
    null_edges = naive_gradient_edges(depth, rel_thresh=0.05)

    # 既知の段差位置 = 列 u_step の両隣(二階差分は段差の両側で立つ)。
    step_mask = (uu == u_step) | (uu == (u_step - 1))
    step_detection = float(edges[step_mask].mean())

    # 平坦(傾いてはいるが連続)な平面部 = 段差±2・球周辺・画像端を除いた領域。
    r2 = (uu - uc) ** 2 + (vv - vc) ** 2
    near_sphere = r2 <= (radius + 2.0) ** 2
    border = (uu < 1) | (uu > W - 2) | (vv < 1) | (vv > H - 2)
    flat_mask = (~near_sphere) & (np.abs(uu - u_step) > 2) & (~border)
    method_fp = float(edges[flat_mask].mean())       # 実手法の誤検出率(理論上 0)
    null_fp = float(null_edges[flat_mask].mean())    # null の誤検出率(傾きを拾う)

    # 球のシルエット(遮蔽エッジ)も拾えることを確認(chain の締め、補助チェック)。
    r = np.sqrt(r2)
    ring = (r >= radius - 1.5) & (r <= radius + 1.5) & (~border)
    sphere_edge_detection = float(edges[ring].mean())

    # --- 5) 結果表示 ---
    print(f"深度画像                    : {H}x{W}  (平面 depth=z0+su*u, z0={z0}, su={su})")
    print(f"段差(遮蔽)                  : 列 u={u_step} で深度 +{step}")
    print(f"球                          : 中心画素({uc},{vc}) 半径{radius:.0f} 中心深度{cz}")
    print("-")
    print(f"格子点の復元誤差            : {recon_err:.2e}  (真値 (u,v,depth) と一致)")
    print("-")
    print(f"平面法線 平均角度誤差       : {plane_mean_ang:.3f} 度")
    print(f"平面法線 最大角度誤差       : {plane_max_ang:.3f} 度")
    print(f"法線 null(正面決め打ち)誤差 : {null_normal_ang:.3f} 度  (これを大きく下回れば勝ち)")
    print("-")
    print(f"段差の検出率(既知位置)     : {step_detection:.3f}  (1.0 に近いほど良い)")
    print(f"実手法の平面部 誤検出率     : {method_fp:.3f}  (二階差分: 一様傾斜は ≈0)")
    print(f"null の平面部 誤検出率      : {null_fp:.3f}  (一階勾配: 傾きを段差と誤検出)")
    print(f"球シルエットの検出率        : {sphere_edge_detection:.3f}  (遮蔽エッジとして検出)")

    # --- 6) GT アサーション(真値との一致 + beat-the-null) ---
    # 法線: 真の向きと角度誤差 < 5 度、かつ正面決め打ち null を明確に上回る。
    assert plane_max_ang < 5.0, f"平面法線が真値からずれすぎ: 最大 {plane_max_ang:.3f} 度"
    assert plane_mean_ang < 0.5 * null_normal_ang, \
        f"法線が null(正面決め打ち {null_normal_ang:.1f} 度)に勝てていない: {plane_mean_ang:.3f} 度"

    # 段差: 既知位置での検出率が高い。
    assert step_detection > 0.9, f"既知の段差位置での検出率が低い: {step_detection:.3f}"

    # beat-the-null(誤検出): 実手法は平坦部でほぼ誤検出せず、null は傾きを拾って誤検出する。
    assert method_fp < 0.02, f"実手法が平坦な傾斜面を誤検出している: {method_fp:.3f}"
    assert null_fp > 0.10, f"null が誤検出しない設定になっている(比較が成立しない): {null_fp:.3f}"
    assert null_fp > 5.0 * max(method_fp, 1e-6), \
        f"実手法が null を誤検出で上回れていない: 手法 {method_fp:.3f} vs null {null_fp:.3f}"

    # 球シルエットも遮蔽エッジとして拾えている(chain の締め)。
    assert sphere_edge_detection > 0.3, \
        f"球のシルエット(遮蔽エッジ)を拾えていない: {sphere_edge_detection:.3f}"

    print(
        f"PASS: 平面法線 {plane_mean_ang:.2f}度 < 5度 (null {null_normal_ang:.1f}度に勝利)、"
        f"段差検出 {step_detection:.2f}、平坦部の誤検出 手法 {method_fp:.3f} << null {null_fp:.3f}"
    )


if __name__ == "__main__":
    main()
