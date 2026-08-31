# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: domain(処理領域)と boundary(境界殻)でメモリを絞って計測する.

現実の問題(平たく):
    産業 CT の視野には対象部品のほかに治具・ステージが写り込む。ボリューム全体
    (ここでは 96^3)を後段に流すとメモリも計算も無駄で、Hessian 系 op には
    サイズ上限(MAX_EIGEN_VOXELS)すらある。HALCON の 2-D には domain(処理領域)
    という解決があるが、3-D 側にはこれまで無かった。本例はその voxel 版 —
    「マスクで黙らせる → タイト AABB へ切り出す → 殻だけ点群化して計測 →
    元の座標系へ戻す」を一気通貫で検証する。

方法(domain / boundary ファミリを鎖状につなぐ):
    1) vol_reduce_domain   : 治具(スラブ)を 0 に(HALCON reduce_domain)
    2) vol_bounding_box    : 部品のタイト AABB(margin 付き・クリップ検証)
    3) vol_crop_domain     : AABB へ切り出し + offset(メモリ削減の本丸)
    4) vol_boundary        : 6 連結の内側境界殻(2-D region_boundary の 3-D 版)
    5) vol_boundary_points : 殻 voxel を物理 mm 座標の点群へ(origin=crop offset)
    6) fit_sphere3         : 殻点群から球の中心・半径を回収(measure3d と接続)
    7) vol_uncrop          : 切り出し結果を元の 96^3 フレームへ厳密に貼り戻す

Ground truth(検証):
    合成シーンは真値既知 — 球の中心 (24.0, 15.0, 15.0) mm・半径 4.5 mm、
    spacing は異方性 (0.5, 0.25, 0.25) mm(CT の常態: z だけ粗い)。
    - AABB: 手計算の voxel 範囲と厳密一致、margin=3 は境界クリップも厳密一致
    - メモリ: crop 後の voxel 数が全体の 1/59(実測)= 59 倍の削減
    - 殻: 中実球に対し殻は 18%(実測。表面積/体積 ~ 3/r の桁と整合)
    - 点群計測: crop した殻点群 + origin 補正で fit_sphere3 の中心誤差
      0.05 mm 未満・半径誤差 0.25 mm 未満(voxel 中心は表面の内側 ~spacing/2)
    - 貼り戻し: uncrop(crop(v)) が AABB 内で bit 一致・外は 0
    - 座標系: crop 経由の点群 = full 経由の点群(集合として厳密一致)
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from measure3d import fit_sphere3
from volops import (
    vol_bounding_box,
    vol_boundary,
    vol_boundary_points,
    vol_crop_domain,
    vol_reduce_domain,
    vol_uncrop,
)

SPACING = (0.5, 0.25, 0.25)          # (sz, sy, sx) mm — z だけ粗い異方性
CENTER_MM = (24.0, 15.0, 15.0)       # 球中心(物理 mm、(z, y, x))
RADIUS_MM = 4.5


def build_scene():
    """96^3 の合成 CT: 明るいスラブ(治具)+ 対象の球(真値既知)。"""
    n = 96
    vol = np.zeros((n, n, n), np.float64)
    vol[:, 80:96, :] = 0.6                       # 治具スラブ(y の奥側)
    z, y, x = np.mgrid[0:n, 0:n, 0:n].astype(np.float64)
    zm, ym, xm = z * SPACING[0], y * SPACING[1], x * SPACING[2]
    ball = ((zm - CENTER_MM[0]) ** 2 + (ym - CENTER_MM[1]) ** 2
            + (xm - CENTER_MM[2]) ** 2) <= RADIUS_MM ** 2
    vol[ball] = 1.0                              # 対象部品(高吸収)
    return vol, ball


def main():
    vol, ball = build_scene()
    n_total = vol.size

    # 1) 治具を domain マスクで黙らせる(部品だけの世界にする)
    part_mask = (vol > 0.9).astype(np.float64)   # 治具 0.6 は落ち、球 1.0 が残る
    quiet = vol_reduce_domain(vol, part_mask)
    print("[reduce_domain]")
    print(f"  治具スラブの voxel は 0 に: 残る非ゼロ = {int((quiet > 0).sum())}"
          f" (= 球 {int(ball.sum())} voxel)")
    assert int((quiet > 0).sum()) == int(ball.sum()), "治具が黙っていない"

    # 2) タイト AABB(margin=3 の境界クリップも機械検証)
    box = vol_bounding_box(part_mask)
    # 手計算: 球の z 範囲 = (24±4.5)/0.5 = [39, 57] → voxel 39..57(端含む)
    #         y/x 範囲 = (15±4.5)/0.25 = [42, 78] → voxel 42..78(端含む)
    print("[bounding_box]")
    print(f"  box = {box}")
    assert box == (39, 42, 42, 58, 79, 79), f"AABB が手計算と不一致: {box}"
    box_m = vol_bounding_box(part_mask, margin=3)
    assert box_m == (36, 39, 39, 61, 82, 82), f"margin+クリップ不一致: {box_m}"

    # 3) 切り出し = メモリ削減の本丸
    part, offset = vol_crop_domain(vol, part_mask)
    factor = n_total / part.size
    print("[crop_domain]")
    print(f"  {vol.shape} → {part.shape} @ offset {offset}: メモリ 1/{factor:.0f}")
    assert offset == (39, 42, 42)
    assert factor > 34.0, f"削減率が想定未満: {factor}"   # 96^3 / (19*37*37) = 34.01

    # 4) 境界殻: 中実球の内部が丸ごと落ちる
    part_mask_c = (part > 0.9).astype(np.float64)
    shell = vol_boundary(part_mask_c, connectivity=6)
    ratio = shell.sum() / part_mask_c.sum()
    print("[boundary]")
    print(f"  中実 {int(part_mask_c.sum())} voxel → 殻 {int(shell.sum())} voxel"
          f" ({100.0 * ratio:.0f}%)")
    assert 0.05 < ratio < 0.30, f"殻の比率が球の 3/r の桁から外れた: {ratio}"

    # 5) 殻を物理 mm 座標の点群へ(origin=crop offset で元フレームに合わせる)
    pts = vol_boundary_points(part_mask_c, spacing=SPACING, origin=offset)
    assert pts.shape == (int(shell.sum()), 3)

    # 6) 省メモリ表現のまま計測が閉じる: 殻点群 → 球フィット
    fit = fit_sphere3(pts)
    c_err = float(np.linalg.norm(
        np.array([fit["cd"], fit["cr"], fit["cc"]]) - np.array(CENTER_MM)))
    print("[fit_sphere3]")
    print(f"  中心 ({fit['cd']:.3f}, {fit['cr']:.3f}, {fit['cc']:.3f}) mm"
          f" 誤差 {c_err:.3f} mm / 半径 {fit['r']:.3f} mm (真値 {RADIUS_MM})")
    assert c_err < 0.05, f"中心誤差が大きい: {c_err}"
    # 内側境界の voxel 中心は表面より ~spacing/2 内側 → 半径はわずかに小さく出る
    assert RADIUS_MM - 0.25 < fit["r"] < RADIUS_MM + 0.05, f"半径: {fit['r']}"

    # 7) 元のフレームへ厳密に貼り戻す(AABB 内 bit 一致・外は 0)
    back = vol_uncrop(part, offset, vol.shape)
    z0, y0, x0 = offset
    d, h, w = part.shape
    assert np.array_equal(back[z0:z0 + d, y0:y0 + h, x0:x0 + w], part)
    inside = np.zeros(vol.shape, bool)
    inside[z0:z0 + d, y0:y0 + h, x0:x0 + w] = True
    assert np.all(back[~inside] == 0.0)

    # 座標系の一貫性: crop 経由の点群 = full 経由の点群(集合一致)
    pts_full = vol_boundary_points(part_mask, spacing=SPACING)
    assert np.array_equal(np.sort(pts, axis=0), np.sort(pts_full, axis=0))

    print(
        f"\nPASS: 治具を reduce_domain で消し、crop でメモリ 1/{factor:.0f}、"
        f"殻 {100.0 * ratio:.0f}% の点群だけで球中心誤差 {c_err:.3f} mm・"
        f"半径 {fit['r']:.2f}/{RADIUS_MM} mm を回収、uncrop は bit 一致。"
    )


if __name__ == "__main__":
    main()
