# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 産業 CT のパイプ断面を仮想プローブで貫き、壁厚(肉厚)を計測する。

鋳造品や配管の産業 CT 検査では「肉厚が図面どおり残っているか」が合否の核心。
実務では体積全体をセグメンテーションせず、表面法線に沿った **仮想プローブ
(virtual probe / 線プローブ)** を撃ち、強度プロファイル上のエッジ対から壁厚を
直接読む(2D measure1d の縦持ち版)。ここでは外半径 R_out・内半径 R_in が既知の
円筒殻(パイプ)を部分体積効果つき(境界 1 voxel の線形ランプ)で合成し、
断面中心を貫くプローブで:

  1. vol_profile_line — プロファイルの物理長が異方 spacing 下の手計算と一致
  2. vol_edge_probe   — 4 エッジ(外壁入→内腔→内壁入→外壁出)を極性つきで検出
  3. vol_wall_thickness — 壁厚 2 箇所が真値 (R_out - R_in) * spacing と一致

検証(GT): パイプは自分で組んだので真値がわかる。エッジ位置はランプ中点
= 真の半径位置に一致するはずで、壁厚は sub-voxel 精度(< 0.2 voxel)で真値に
合うことを実測誤差で assert する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# 直接実行時もリポジトリルートの本物モジュールを確実に import させる(順序保証・無害)。
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

import volprobe  # noqa: E402


def make_pipe(shape=(16, 40, 40), center=(20.0, 20.0), r_in=8.0, r_out=12.0):
    """z 軸方向に一様な円筒殻(パイプ)体積を作る。

    境界は 1 voxel 幅の線形ランプ(部分体積効果の近似)にする: ランプの中点が
    ちょうど真の半径位置に来るので、エッジ検出の真値が解析的に決まる。"""
    D, H, W = shape
    cy, cx = center
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    r = np.hypot(yy - cy, xx - cx)
    # 内側ランプ: r_in - 0.5 -> r_in + 0.5 で 0 -> 1(中点 = r_in)
    # 外側ランプ: r_out - 0.5 -> r_out + 0.5 で 1 -> 0(中点 = r_out)
    shell = np.clip(r - (r_in - 0.5), 0.0, 1.0) * np.clip((r_out + 0.5) - r, 0.0, 1.0)
    vol = np.broadcast_to(shell[None, :, :], shape).copy()
    return vol


def main() -> int:
    # --- 真値(既知パラメータ)---
    R_IN, R_OUT = 8.0, 12.0                    # voxel 単位の内/外半径
    CY = CX = 20.0
    SPACING = (1.0, 0.5, 0.5)                  # (sz, sy, sx) mm — 異方 spacing
    SY = SPACING[1]
    TRUE_WALL_MM = (R_OUT - R_IN) * SY         # 真の壁厚 = 4 voxel * 0.5 mm = 2.0 mm

    vol = make_pipe((16, 40, 40), (CY, CX), R_IN, R_OUT)

    # プローブ: 断面中心 (z=8, x=20) を y 方向に端から端まで貫く
    p0 = (8.0, 0.0, 20.0)
    p1 = (8.0, 39.0, 20.0)

    # --- 1) vol_profile_line: 物理長の手計算一致 ----------------------------
    t_mm, prof = volprobe.vol_profile_line(vol, p0, p1, spacing=SPACING)
    expect_len = 39.0 * SY                     # y を 39 voxel 進む * 0.5 mm
    len_err = abs(t_mm[-1] - expect_len)
    print(f"プロファイル: {len(prof)} サンプル, 物理長 {t_mm[-1]:.4f} mm "
          f"(手計算 {expect_len:.4f} mm, 誤差 {len_err:.2e} mm)")
    assert len_err < 1e-9, f"プロファイル物理長が手計算と不一致: {len_err:.3e} mm"

    # --- 2) vol_edge_probe: 4 エッジ(極性列 +,-,+,-)-----------------------
    edges = volprobe.vol_edge_probe(vol, p0, p1, sigma=1.0, threshold=0.1,
                                    spacing=SPACING)
    print(f"検出エッジ数: {len(edges)}")
    for e in edges:
        pol = "立上り" if e["polarity"] > 0 else "立下り"
        print(f"  t={e['t_mm']:7.4f} mm  y={e['position'][1]:7.3f}  "
              f"{pol}  振幅 {e['amplitude']:.3f} /mm")
    assert len(edges) == 4, f"エッジ数が 4 でない: {len(edges)}"
    assert [e["polarity"] for e in edges] == [1, -1, 1, -1], "極性列が +,-,+,- でない"
    # エッジの真位置: y 増加方向に r = |y - 20| が R_OUT, R_IN, R_IN, R_OUT を横切る
    true_y = [CY - R_OUT, CY - R_IN, CY + R_IN, CY + R_OUT]   # 8, 12, 28, 32
    max_pos_err = max(abs(e["position"][1] - ty) for e, ty in zip(edges, true_y))
    print(f"エッジ位置の最大誤差: {max_pos_err:.4f} voxel (真位置 y={true_y})")
    assert max_pos_err < 0.2, f"エッジ位置誤差が大きい: {max_pos_err:.4f} voxel"

    # --- 3) vol_wall_thickness: 壁厚 2 箇所が真値と一致 ---------------------
    walls = volprobe.vol_wall_thickness(vol, p0, p1, sigma=1.0, threshold=0.1,
                                        spacing=SPACING)
    print(f"壁厚: {[f'{w:.4f}' for w in walls]} mm  (真値 {TRUE_WALL_MM:.4f} mm)")
    assert len(walls) == 2, f"壁厚が 2 箇所でない: {len(walls)}"
    wall_errs = [abs(w - TRUE_WALL_MM) for w in walls]
    max_wall_err = max(wall_errs)
    assert max_wall_err < 0.2 * SY, \
        f"壁厚誤差が sub-voxel でない: {max_wall_err:.4f} mm (> {0.2 * SY:.2f} mm)"

    print(f"PASS: パイプ壁厚をプローブ計測 — 壁厚 {walls[0]:.4f} / {walls[1]:.4f} mm "
          f"(真値 {TRUE_WALL_MM:.4f} mm, 誤差 {wall_errs[0]:.4f} / {wall_errs[1]:.4f} mm "
          f"< {0.2 * SY:.2f} mm)・エッジ 4/4 検出(位置誤差 {max_pos_err:.4f} voxel)・"
          f"プロファイル物理長 {t_mm[-1]:.2f} mm = 手計算一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
