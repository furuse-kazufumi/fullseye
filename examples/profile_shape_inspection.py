# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""断面形状の検査 —— 既知の欠陥を入れて、検出できる大きさを数字で出す。

EXTEND: 実測の輪郭(3D スキャンの断面、撮影した影絵の輪郭、CAD の書き出し)を
使うなら ``measured`` を差し替える。設計形状 ``ref`` が NACA でないなら、
``profile_synth_naca4`` の代わりに設計座標を読み込む。

この例が示すこと:

1. **真値は閉形式から作れる**(NACA 4 桁)。厚み・前縁半径が式と一致する。
2. **対称翼で 0 になるべき量が 0 になる** —— 規約の破れを暴く一番効く検査。
3. **検査の床**(同じ形どうしの偏差)が、狙う欠陥より 2 桁小さいこと。
4. ★**位置合わせが欠陥を移す** —— 前縁の欠陥を弦合わせで測ると、最悪点が
   後縁に出る。都合の良い設定だけを見せない。

速さは印字するだけ。assert するのは**正しさ**だけ。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# ★repo 直下のモジュール(profileops)を import するので、チェックアウトから
# そのまま走らせても通るように repo 直下を先頭に置く。他の例と同じ作法。
# これが無いと `py -3.11 examples/<name>.py` が ModuleNotFoundError で落ちる
# (2026-09-09 実測: 走らせる門が無かった 83 本のうち、落ちたのはこの型の 2 本だけ)。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import profileops  # noqa: E402


def main():
    print("=== 1. 閉形式の設計形状 ===")
    ref = profileops.profile_synth_naca4("2412", n=801)
    t = profileops.profile_thickness(ref, 401)
    cam = profileops.profile_camber(ref, 401)
    r_le = profileops.profile_leading_edge_radius(ref)
    gap = profileops.profile_trailing_edge_gap(ref)
    ti, ci = int(np.argmax(t[:, 1])), int(np.argmax(cam[:, 1]))
    print(f"  NACA 2412 / 点 {len(ref)}")
    print(f"  最大厚み       {t[ti, 1]:.5f} @ x={t[ti, 0]:.3f}   (閉形式 0.12)")
    print(f"  最大キャンバー {cam[ci, 1]:.5f} @ x={cam[ci, 0]:.3f}   (公称 0.02、定義差で 6 % 低い)")
    print(f"  前縁半径       {r_le:.5f}            (閉形式 1.1019 t^2 = {1.1019 * 0.12 ** 2:.5f})")
    print(f"  後縁隙間       {gap:.5f}            (既定係数は開く)")

    print("\n=== 2. 対称翼で 0 になるか(規約の破れを暴く)===")
    for code in ("0008", "0012", "0021"):
        c = profileops.profile_synth_naca4(code, 801)
        cm = float(np.max(np.abs(profileops.profile_camber(c, 401)[:, 1])))
        fr = profileops.profile_chord_frame(c)
        print(f"  NACA {code}: |キャンバー| {cm:.6f} / 弦角 {fr['angle_deg']:+.4f} 度")
    print("  → 後縁を隙間の中点に取り直す前は 0.001257(後縁の半隙間)が出ていた。")

    print("\n=== 3. 検査の床(同じ形どうし)===")
    for mode in profileops.ALIGN_MODES:
        d = profileops.profile_deviation(ref, ref, n=400, align=mode)
        print(f"  align={mode:<6} rms {d['rms']:.2e}")
    print("  → 床が狙う欠陥(1e-3)と同じ桁なら検査になっていない。")

    print("\n=== 4. 一様な厚み増を測り返す ===")
    print(f"  {'注入 [翼弦]':<14}{'平均偏差':>12}{'rms':>12}")
    for amount in (0.002, 0.0005, 0.0001):
        bad = profileops.profile_perturb(ref, "thicken", amount)
        d = profileops.profile_deviation(bad, ref, n=400)
        print(f"  {amount:<14.4f}{d['mean']:>+12.6f}{d['rms']:>12.6f}")
    print("  → 0.0001 翼弦は、弦 1 m の羽根なら 0.1 mm。")

    print("\n=== 5. 回して・ずらしても消えないか ===")
    bad = profileops.profile_perturb(ref, "thicken", 0.002)
    a = np.radians(3.0)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    moved = bad @ rot.T + np.array([0.7, -0.3])
    for mode in ("chord", "rigid"):
        d = profileops.profile_deviation(moved, ref, n=400, align=mode)
        print(f"  align={mode:<6} 平均偏差 {d['mean']:+.6f}(仕込み 0.002)")

    print("\n=== 6. ★ 欠陥が合わせの基準に乗ると、結果が変わる ===")
    eroded = profileops.profile_perturb(ref, "le_erosion", 0.003, extent=0.1)
    print(f"  {'合わせ方':<8}{'最悪偏差':>12}{'その位置 x':>12}{'前縁側の最悪':>14}")
    nose_worst = {}
    for mode in profileops.ALIGN_MODES:
        d = profileops.profile_deviation(eroded, ref, n=400, align=mode)
        where = d["points"][int(np.argmin(d["deviation"]))][0]
        nose = float(np.min(d["deviation"][d["points"][:, 0] < 0.15]))
        nose_worst[mode] = nose
        print(f"  {mode:<8}{d['min']:>+12.5f}{where:>12.3f}{nose:>+14.5f}")
    print("  → 前縁を削ると前縁の位置そのものが動く。弦合わせは損失を後縁へ移し、")
    print("     前縁の落ち込みを 3 分の 1 に見せる。同じ座標系(none)だけが真値を返す。")

    print("\n=== 7. ほかの欠陥 ===")
    for kind, amount in (("le_erosion", 0.003), ("waviness", 0.001), ("twist", 0.5)):
        d = profileops.profile_deviation(
            profileops.profile_perturb(ref, kind, amount), ref, n=400, align="none")
        print(f"  {kind:<11} {amount:<6} max {d['max']:+.5f} / min {d['min']:+.5f} "
              f"/ 平均 {d['mean']:+.6f}")

    # ---- 自己検査 ---------------------------------------------------------
    assert abs(np.max(t[:, 1]) - 0.12) < 5e-4
    assert abs(r_le - 1.1019 * 0.12 ** 2) < 0.05 * r_le
    assert profileops.profile_deviation(ref, ref, n=400)["rms"] < 1e-5
    assert abs(profileops.profile_deviation(
        profileops.profile_perturb(ref, "thicken", 0.002), ref, n=400)["mean"]
        - 0.002) < 2e-4
    # 弦合わせが前縁の欠陥を過小に見せることも固定する(都合の良い側だけ残さない)
    assert nose_worst["chord"] > 2.0 * nose_worst["none"]
    print("\nPASS")


if __name__ == "__main__":
    main()
