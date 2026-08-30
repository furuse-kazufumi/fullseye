# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: CT ボリュームの「管・粒・肉厚」計測 — Hessian 特徴 → ピーク → ラベル → 物理量.

現実の問題(平たく):
    医用 CT なら血管(管)と結節(粒)、産業 CT なら細い流路と気孔(欠陥)。
    どちらも「細長い構造」と「丸い構造」を区別して数え、大きさを物理単位
    (mm)で報告したい。CT のボクセルは z 方向だけ粗い(異方性 spacing)のが
    常態なので、距離・体積は spacing を考慮しないと系統誤差になる。

方法(volops の ops を鎖状につなぐ):
    1) vol_frangi / vol_sato      : Hessian 固有値の管状度。管で強く、粒で弱い
    2) vol_hessian_blobness       : 同じ Hessian の粒状度。粒で強く、管で弱い
    3) vol_gradient_magnitude     : 表面(境界)で強い勾配場 — 内外の確認
    4) vol_local_maxima           : 粒の中心 = 強度ピークを (z,y,x) で列挙
    5) vol_label                  : 二値化した前景を 6/26 連結でラベリング
    6) vol_region_props           : 成分ごとの体積(mm^3)・重心・球形度
    7) vol_distance_transform     : spacing 対応 EDT = 肉厚(壁までの物理距離)

Ground truth(検証):
    合成シーンは真値既知 — z 軸に沿う管 1 本 + 球 2 個(中心・半径・強度は既知)。
    - 管状度/粒状度の相互判別: frangi は管の軸で球中心より強く、blobness は逆。
      **互いが互いの否定対照**(どちらも「明るい所に反応するだけ」なら両者の
      優劣は一致してしまう。逆転することが Hessian 固有値を見ている証明)
    - ピーク: 孤立した強度ピーク 2 つを過不足なく検出(座標一致)
    - 連結: 斜め接触ペアは 26 連結で 1 成分 / 6 連結で 2 成分(規約の機械検証)
    - 物理量: spacing (2,1,1) の板の中心 EDT = 10.0 mm(手計算と一致)、
      球の体積 = ボクセル数 x 2.0 mm^3、重心 = 既知中心
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from volops import (
    vol_frangi,
    vol_sato,
    vol_hessian_blobness,
    vol_gradient_magnitude,
    vol_local_maxima,
    vol_label,
    vol_region_props,
    vol_distance_transform,
)


def build_scene(n=48):
    """管 1 本 + 球 2 個の合成 CT。強度はなだらか(Hessian が効く)で真値既知。"""
    zz, yy, xx = np.mgrid[0:n, 0:n, 0:n].astype(np.float64)
    vol = np.zeros((n, n, n), np.float64)
    # 管: z 軸に沿い (y,x)=(12,12)、ガウス断面(半径感 ~2.5)
    r2_tube = (yy - 12.0) ** 2 + (xx - 12.0) ** 2
    vol += 1.0 * np.exp(-r2_tube / (2 * 2.5 ** 2))
    # 球 2 個: 中心既知、ガウス球(孤立ピーク)
    centers = [(14, 32, 34), (34, 30, 14)]
    for cz, cy, cx in centers:
        r2 = (zz - cz) ** 2 + (yy - cy) ** 2 + (xx - cx) ** 2
        vol += 1.0 * np.exp(-r2 / (2 * 3.0 ** 2))
    return vol, centers


def main():
    vol, ball_centers = build_scene()
    tube_axis = [(z, 12, 12) for z in range(8, 40, 4)]      # 管の軸上の代表点

    # ---- (1)(2) 管状度と粒状度の相互判別(互いが否定対照) ----
    fr = vol_frangi(vol, scales=(2, 3))
    sa = vol_sato(vol, scales=(2, 3))
    bl = vol_hessian_blobness(vol, scale=3)
    fr_tube = float(np.mean([fr[p] for p in tube_axis]))
    fr_ball = float(np.mean([fr[c] for c in ball_centers]))
    sa_tube = float(np.mean([sa[p] for p in tube_axis]))
    sa_ball = float(np.mean([sa[c] for c in ball_centers]))
    bl_tube = float(np.mean([bl[p] for p in tube_axis]))
    bl_ball = float(np.mean([bl[c] for c in ball_centers]))
    print("[管状度 vs 粒状度]")
    print(f"  frangi   : 管軸 {fr_tube:.4f}  球中心 {fr_ball:.4f}  (管 > 球 が正解)")
    print(f"  sato     : 管軸 {sa_tube:.4f}  球中心 {sa_ball:.4f}  (同上)")
    print(f"  blobness : 管軸 {bl_tube:.4f}  球中心 {bl_ball:.4f}  (球 > 管 が正解)")
    assert fr_tube > 2.0 * fr_ball, f"frangi が管を選べていない: {fr_tube} vs {fr_ball}"
    assert sa_tube > 2.0 * sa_ball, f"sato が管を選べていない: {sa_tube} vs {sa_ball}"
    assert bl_ball > 2.0 * bl_tube, f"blobness が球を選べていない: {bl_ball} vs {bl_tube}"

    # ---- (3) 勾配場: 球の表面で強く、中心と背景で弱い ----
    gm = vol_gradient_magnitude(vol)
    cz, cy, cx = ball_centers[0]
    g_surface = float(gm[cz + 3, cy, cx])                    # 表面近傍(強度が変わる所)
    g_center = float(gm[cz, cy, cx])                         # 中心(ピーク = 勾配 0)
    g_bg = float(gm[4, 44, 44])                              # 背景
    print("[勾配場]")
    print(f"  表面 {g_surface:.4f} / 中心 {g_center:.4f} / 背景 {g_bg:.4f}")
    assert g_surface > 5.0 * max(g_center, g_bg, 1e-9), "勾配が表面に乗っていない"

    # ---- (4) ピーク検出: 孤立ピーク = 球の中心を過不足なく ----
    # 管の軸は「z 方向に平坦な稜線」なので軸上も局所最大になり得る。閾値で
    # 球ピーク(強度 ~1)だけを残し、座標一致を要求する
    peaks = vol_local_maxima(vol, min_distance=3, threshold=0.9)
    got = {tuple(p) for p in peaks.tolist()}
    want = set(ball_centers)
    print("[ピーク検出]")
    print(f"  検出 {sorted(got)} / 真値 {sorted(want)}")
    assert got == want, f"ピークが真値と不一致: got={got} want={want}"

    # ---- (5) ラベリング: 26/6 連結の規約を機械検証 ----
    labels26, n26 = vol_label(vol > 0.35, connectivity=26)
    print("[ラベリング]")
    print(f"  前景(>0.35)の 26 連結成分: {n26}(管 1 + 球 2 = 3 が正解)")
    assert n26 == 3, f"成分数が 3 でない: {n26}"
    # 斜め接触ペア: 26 連結なら 1 成分、6 連結なら 2 成分
    pair = np.zeros((4, 4, 4), bool)
    pair[1, 1, 1] = pair[2, 2, 2] = True
    _, c26 = vol_label(pair, connectivity=26)
    _, c6 = vol_label(pair, connectivity=6)
    print(f"  斜め接触ペア: 26連結={c26} 成分 / 6連結={c6} 成分")
    assert c26 == 1 and c6 == 2, f"連結規約が仕様と違う: {c26}, {c6}"

    # ---- (6) 物理量: spacing 付き region props(体積・重心) ----
    spacing = (2.0, 1.0, 1.0)                                # z だけ粗い CT の常態
    props = vol_region_props(labels26, spacing=spacing)
    ball_mask = vol > 0.35
    # 球 1 個目の成分を重心の近さで対応付け
    tgt = np.array(ball_centers[0], np.float64)
    comp = min(props, key=lambda p: np.linalg.norm(np.array(p["centroid"]) - tgt))
    vox = int(comp["voxel_count"])
    print("[物理量 (spacing=(2,1,1))]")
    print(f"  球成分: voxel_count={vox} volume={comp['volume']:.1f} mm^3 "
          f"centroid={tuple(round(c, 1) for c in comp['centroid'])}")
    assert abs(comp["volume"] - vox * 2.0) < 1e-6, "volume が spacing を反映していない"
    assert np.linalg.norm(np.array(comp["centroid"]) - tgt) < 1.0, "重心が真値とずれた"

    # ---- (7) 肉厚: spacing 対応 EDT の手計算一致 ----
    slab = np.zeros((24, 40, 40), bool)
    slab[8:17, 2:38, 2:38] = True                            # z に 9 voxel 厚の板
    d = vol_distance_transform(slab, spacing=spacing)
    center = float(d[12, 20, 20])
    # 中心 z=12 → 最寄り背景 z=7 or z=17 → 5 voxel x sz=2.0 = 10.0 mm
    # (y/x 方向は 18 voxel x 1.0 = 18 mm で z が最短)
    print("[肉厚 EDT]")
    print(f"  板中心の壁まで距離: {center:.1f} mm(手計算 10.0)")
    assert abs(center - 10.0) < 1e-6, f"EDT が spacing を反映していない: {center}"

    print(
        "\nPASS: frangi/sato は管を、blobness は球を選び(相互否定対照で逆転)、"
        f"勾配は表面に乗り、ピーク {len(got)}/2 座標一致、26/6 連結が仕様どおり、"
        f"体積 {comp['volume']:.0f} mm^3 = voxel x sz、板中心 EDT 10.0 mm 一致。"
    )


if __name__ == "__main__":
    main()
