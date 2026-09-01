# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""tomography_reconstruct — 投影から**ボクセルと体積 mm³ まで**一本で閉じる。

    py -3.11 examples/tomography_reconstruct.py

【この例が解く問題】
X 線 CT で撮った部品の**体積を mm³ で答える**。fullseye には CT ボリュームを
「扱う」op(窓・ラベリング・境界抽出・メッシュ化・領域統計)は前からあったが、
**投影から作る**側が 1 つも無かった。ここは新しい `tomography` 族でサイノグラム
から再構成し、そこから先は**既存の 3-D op をそのまま呼ぶ**(1 つも作り直さない)。

    解析ファントム(真の体積が閉形式)
      → radon_volume         投影(サイノグラム束)
      → fbp_volume           再構成 → ボリューム
      → vol_window_level     CT 窓
      → 二値化 → vol_label   部品を 1 成分に分離
      → vol_region_props     体積 mm³(spacing つき)
      → marching_cubes       メッシュ
      → vol_boundary_points  境界点群
      → vol_rle_encode       占有表現

【グラウンドトゥルース(数値で嘘を弾く)】
ファントムは**楕円体から楕円体をくり抜いたもの**なので、体積が閉形式で分かる:
V = 4/3 π (a b c − a' b' c')。しかも楕円体の z 断面はちょうど楕円なので、各
スライスは `ellipse_phantom` / `ellipse_sinogram` の厳密な入力になる。

【この例が数字にすること】
(1) 投影数を減らすと体積誤差がどう動くか(**1 つの数字で「投影が足りない」が出る**)
(2) 誤差の内訳: **格子の粗さ(digitisation)** と **再構成** のどちらが効くか
(3) 異方性 spacing (z だけ粗い = CT の常態) を無視すると体積が何倍ずれるか
(4) 二値化しきい値を動かすと体積がどれだけ動くか
    ―― **再構成の誤差より、しきい値の任意性の方が効く**なら、それは正直に書く

【前提】面内 0.5 mm/画素、スライス間隔 2.0 mm(**異方性 4:1**)。実機 CT の常態。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fullseye as fs                                            # noqa: E402
import tomography as T                                           # noqa: E402

# ---- 撮像・再構成の幾何(すべて mm) ------------------------------------- #
PIX_MM = 0.5          # 面内の画素ピッチ
SLICE_MM = 2.0        # スライス間隔(z だけ 4 倍粗い = 異方性)
SIZE = 128            # 面内の再構成格子(128 x 0.5 mm = 64 mm 視野)
HALF_MM = SIZE * PIX_MM / 2.0        # 正規化座標 [-1,1] が覆う半幅 = 32 mm
N_SLICES = 17         # 17 x 2.0 mm = 32 mm

# ---- ファントム: 楕円体の殻(外側)から楕円体の空洞をくり抜いたもの ------ #
OUTER = (20.0, 12.0, 14.0)      # 半軸 (a, b, c) mm
VOID = (8.0, 4.0, 6.0)          # 空洞の半軸 mm(同心)
RHO = 0.025                     # 画素あたり減弱 -> 最大線積分 ~2.0(実機並み)

VOXEL_MM3 = SLICE_MM * PIX_MM * PIX_MM          # = 0.5 mm^3


def true_volume_mm3():
    """閉形式の真の体積: 4/3 π (abc - a'b'c')。"""
    f = 4.0 / 3.0 * np.pi
    return f * (OUTER[0] * OUTER[1] * OUTER[2] - VOID[0] * VOID[1] * VOID[2])


def slice_ellipses(z_mm):
    """高さ *z_mm* での断面 = 楕円(外側)と楕円(空洞)。

    楕円体 x²/a²+y²/b²+z²/c² <= 1 の z 断面は半軸 a√(1-z²/c²), b√(1-z²/c²) の
    楕円ちょうど。だから 3-D ファントムの各スライスが `ellipse_phantom` の
    厳密な入力になり、真値が最後まで解析的に追える。
    """
    out = []
    a, b, c = OUTER
    if abs(z_mm) < c:
        k = np.sqrt(1.0 - (z_mm / c) ** 2)
        out.append((0.0, 0.0, a * k / HALF_MM, b * k / HALF_MM, 0.0, RHO))
    a2, b2, c2 = VOID
    if abs(z_mm) < c2:
        k = np.sqrt(1.0 - (z_mm / c2) ** 2)
        out.append((0.0, 0.0, a2 * k / HALF_MM, b2 * k / HALF_MM, 0.0, -RHO))
    return out


def build_phantom():
    """(Z, H, W) の真のボリューム。空洞は減弱を打ち消す負の楕円で作る。

    端の 4 スライスは楕円体の外(= 空気だけ)になる。`ellipse_phantom` は
    空の楕円リストを **fail-closed で拒否する**(何も描かない指示は入力ミス)
    ので、空スライスはここで明示的にゼロ画像として作る ―― 「部品がスキャン
    範囲を埋めていない」は普通に起きることで、黙って握り潰す話ではない。
    """
    z = (np.arange(N_SLICES) - (N_SLICES - 1) / 2.0) * SLICE_MM
    planes = []
    for zz in z:
        ell = slice_ellipses(zz)
        planes.append(T.ellipse_phantom(SIZE, ell, supersample=4) if ell
                      else np.zeros((SIZE, SIZE)))
    return np.stack(planes), z


def measure_volume(vol, threshold, spacing=(SLICE_MM, PIX_MM, PIX_MM)):
    """ボリューム → 二値化 → ラベリング → **最大成分の体積 mm³**。

    既存 op だけ: `vol_label` + `vol_region_props`。spacing を渡すのが要点で、
    渡さないと返るのは「ボクセル数」であって体積ではない。
    """
    labels, n = fs.vol_label((vol > threshold).astype(np.float64), connectivity=26)
    if n == 0:
        return 0.0, 0, 0
    props = fs.vol_region_props(labels, spacing=spacing)
    big = max(props, key=lambda p: p["voxel_count"])
    return float(big["volume"]), int(big["voxel_count"]), int(n)


def main():
    truth_vol, z_mm = build_phantom()
    v_true = true_volume_mm3()
    thr = 0.5 * RHO                     # 部品(RHO)と空気(0)の中点

    print("=" * 78)
    print("1) 設計 ―― 撮る前に決まってしまう限界")
    print("=" * 78)
    d = T.sinogram_design(n_angles=128, size=SIZE, detector_pitch_mm=PIX_MM)
    print(f"   視野                 = {d['field_of_view_mm']:.1f} mm "
          f"({d['n_detectors']} 検出器 x {PIX_MM} mm)")
    print(f"   分解できる最小構造   = {d['resolvable_feature_mm']:.2f} mm "
          f"(= 検出器ピッチ x 2、Nyquist)")
    print(f"   完全標本化に要る視点 = {d['views_for_full_sampling']} 本 "
          f"(実際 128 本 -> 不足率 {d['undersampling_factor']:.2f}x, "
          f"{d['verdict']})")
    print(f"   ストリークの出ない半径 = {d['streak_free_radius_px']:.1f} px "
          f"(= {d['streak_free_radius_px'] * PIX_MM:.1f} mm)")

    print()
    print("=" * 78)
    print("2) ファントムと、閉形式の真値")
    print("=" * 78)
    print(f"   外側の楕円体 半軸 = {OUTER} mm / 空洞 = {VOID} mm")
    print(f"   真の体積 V = 4/3 pi (abc - a'b'c') = {v_true:.1f} mm^3")
    print(f"   ボリューム格子 = {truth_vol.shape} (z {SLICE_MM} mm / 面内 {PIX_MM} mm)")
    print(f"   ボクセル体積 = {VOXEL_MM3} mm^3")

    # 格子で digitise しただけの体積 = 再構成が完璧でも越えられない天井
    v_digital, n_vox, _ = measure_volume(truth_vol, thr)
    print(f"   この格子で二値化した真ファントムの体積 = {v_digital:.1f} mm^3 "
          f"({n_vox} ボクセル, 真値比 {v_digital / v_true:+.1%} … "
          f"誤差 {100 * (v_digital / v_true - 1):+.1f} %)")
    print("   ★これが digitisation の天井。以降の誤差はこの上に乗る。")

    print()
    print("=" * 78)
    print("3-5) 投影 -> 再構成 -> ボクセル -> 体積(投影数を振る)")
    print("=" * 78)
    print("   views |  再構成 nRMS | 体積 mm^3 |  真値比 | 天井比 | 成分数")
    print("   ------+--------------+-----------+---------+--------+-------")
    rows = []
    for n_views in (8, 16, 32, 64, 128):
        ang = T.projection_angles(n_views, 180.0, "uniform")
        stack = T.radon_volume(truth_vol, ang)          # (Z, A, D) サイノグラム束
        rec = T.fbp_volume(stack, ang, size=SIZE)       # (Z, H, W) ボリューム
        nrms = float(np.sqrt(((rec - truth_vol) ** 2).mean())
                     / (truth_vol.max() - truth_vol.min()))
        v_meas, _, n_comp = measure_volume(rec, thr)
        rows.append((n_views, nrms, v_meas))
        print(f"   {n_views:5d} |   {nrms:10.4f} | {v_meas:9.1f} | "
              f"{v_meas / v_true - 1:+6.1%} | {v_meas / v_digital - 1:+5.1%} | "
              f"{n_comp:5d}")
    best = rows[-1]
    worst = rows[0]
    print(f"   ★投影 {worst[0]} 本と {best[0]} 本で体積は "
          f"{abs(worst[2] - best[2]):.1f} mm^3 違う "
          f"({abs(worst[2] - best[2]) / v_true:.1%} of 真値)。"
          f"再構成 nRMS は {worst[1] / best[1]:.1f} 倍。")

    # 以降は 128 views の再構成を使う
    ang = T.projection_angles(128, 180.0, "uniform")
    rec = T.fbp_volume(T.radon_volume(truth_vol, ang), ang, size=SIZE)

    print()
    print("=" * 78)
    print("6) 異方性 spacing を無視すると体積は何倍ずれるか")
    print("=" * 78)
    v_sp, n_vox_r, _ = measure_volume(rec, thr)
    v_nosp, _, _ = measure_volume(rec, thr, spacing=None)
    v_iso, _, _ = measure_volume(rec, thr, spacing=(PIX_MM, PIX_MM, PIX_MM))
    print(f"   spacing=(2.0, 0.5, 0.5) mm  ->  {v_sp:9.1f} mm^3   (正しい)")
    print(f"   spacing を渡さない          ->  {v_nosp:9.1f}      "
          f"= ボクセル数そのもの、{v_nosp / v_sp:.1f} 倍")
    print(f"   等方 0.5 mm と思い込む      ->  {v_iso:9.1f} mm^3   "
          f"{v_iso / v_sp:.2f} 倍 (z が 4 倍粗いぶん {SLICE_MM / PIX_MM:.0f} 倍小さく出る)")
    print("   ★どちらも例外は出ない。有限で、もっともらしく、桁が違う。")

    print()
    print("=" * 78)
    print("7) 二値化しきい値の任意性 ―― 再構成誤差とどちらが効くか")
    print("=" * 78)
    print("   しきい値 (RHO 比) | 体積 mm^3 |  真値比")
    print("   ------------------+-----------+--------")
    sweep = []
    for frac in (0.30, 0.40, 0.45, 0.50, 0.55, 0.60, 0.70):
        v, _, _ = measure_volume(rec, frac * RHO)
        sweep.append((frac, v))
        print(f"   {frac:17.2f} | {v:9.1f} | {v / v_true - 1:+6.1%}")
    span_thr = max(v for _, v in sweep) - min(v for _, v in sweep)
    span_views = max(v for _, _, v in rows) - min(v for _, _, v in rows)
    print(f"   ★しきい値 0.30-0.70 の振れ幅 = {span_thr:.1f} mm^3 "
          f"({span_thr / v_true:.1%} of 真値)")
    print(f"     投影数 8-128 の振れ幅       = {span_views:.1f} mm^3 "
          f"({span_views / v_true:.1%} of 真値)")
    print(f"     -> {'しきい値' if span_thr > span_views else '投影数'}"
          f" の方が {max(span_thr, span_views) / max(min(span_thr, span_views), 1e-9):.1f} 倍効く。"
          f" 体積を報告するときに書くべきなのは"
          f"{'「どのしきい値で」' if span_thr > span_views else '「何本で撮ったか」'}。")

    print()
    print("=" * 78)
    print("8) ここから先は既存の 3-D op(1 つも作り直していない)")
    print("=" * 78)
    windowed = fs.vol_window_level(rec, center=0.5 * RHO, width=1.2 * RHO)
    print(f"   vol_window_level     -> {windowed.shape} 値域 "
          f"[{windowed.min():.3f}, {windowed.max():.3f}]")
    binary = (rec > thr).astype(np.float64)
    labels, n_comp = fs.vol_label(binary, connectivity=26)
    print(f"   vol_label            -> {n_comp} 成分 "
          f"(部品は 1 つ、残りはストリーク由来の粒)")
    verts, faces = fs.marching_cubes(rec, thr)[:2]
    print(f"   marching_cubes       -> 頂点 {np.asarray(verts).shape[0]} / "
          f"面 {np.asarray(faces).shape[0]}")
    cloud = fs.mesh_to_points(verts, faces, 4000, seed=0)
    print(f"   mesh_to_points       -> 点群 {np.asarray(cloud).shape}")
    shell = fs.vol_boundary_points(binary, spacing=(SLICE_MM, PIX_MM, PIX_MM))
    print(f"   vol_boundary_points  -> 境界点群 {np.asarray(shell).shape} "
          f"(mm 単位、(z,y,x) 順)")
    rle = fs.vol_rle_encode(binary)
    n_runs = len(getattr(rle, "runs", []))
    print(f"   vol_rle_encode       -> {n_runs} run "
          f"(占有 {int(binary.sum())} ボクセルを run 長で圧縮)")
    cropped = fs.vol_crop_domain(rec, binary > 0.5)
    crop_shape = np.asarray(cropped[0] if isinstance(cropped, tuple)
                            else cropped).shape
    print(f"   vol_crop_domain      -> {crop_shape} "
          f"(元 {rec.shape} から外接箱へ)")

    print()
    print("=" * 78)
    print("9) fail-closed ―― 黙って通らないこと")
    print("=" * 78)
    stack = T.radon_volume(truth_vol, ang)
    checks = [
        ("角度をラジアンで渡す", lambda: T.fbp_volume(stack, np.deg2rad(ang))),
        ("投影 0 本", lambda: T.radon_volume(truth_vol, np.array([]))),
        ("検出器がファントムを覆わない",
         lambda: T.radon_volume(truth_vol, ang, n_detectors=16)),
        ("角度数とスライス束の行数が不一致",
         lambda: T.fbp_volume(stack, ang[:7])),
        ("小さい引数で巨大な出力", lambda: T.fbp_volume(stack, ang, size=100000)),
        ("ボリュームをサイノグラム束のつもりで再構成…は通ってしまう",
         lambda: None),
    ]
    refused = 0
    for tag, fn in checks[:-1]:
        try:
            fn()
            print(f"   [FAIL] {tag} が拒否されなかった")
            return False
        except ValueError as exc:
            refused += 1
            print(f"   拒否 {tag}: {str(exc).split('.')[0][:66]}")
    wrong = T.fbp_volume(truth_vol)
    print(f"   ★通ってしまう: 本物のボリュームを fbp_volume に渡すと "
          f"{wrong.shape} の有限な「再構成」が返る "
          f"(値域 [{wrong.min():.5f}, {wrong.max():.5f}])。")
    print("     z 軸を角度軸として読んだだけの、意味の無い有限値。だから "
          "opstomography は sinostack を別の型にしてある。")

    assert refused == 5
    assert abs(rows[-1][2] / v_true - 1) < 0.10, "128 views の体積が 10% 以内に入らない"
    assert rows[0][1] > 2.0 * rows[-1][1], "投影数を減らしても誤差が増えていない"

    print()
    print(f"PASS: 投影 -> 再構成 -> ボクセル -> {rows[-1][2]:.1f} mm^3 "
          f"(真値 {v_true:.1f} mm^3, {rows[-1][2] / v_true - 1:+.1%}) まで閉じた。"
          f"tomography 17 op のうち 6 op と、既存 3-D op 8 種を実行。")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
