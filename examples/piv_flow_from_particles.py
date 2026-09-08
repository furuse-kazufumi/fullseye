# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""粒子画像 2 枚から流れを測る —— 真値を自分で作って、誤差を数字で出す。

EXTEND: 実験の粒子画像を読み込んで差し替えるなら ``a``/``b`` を
``imgio.load`` の返りに置き換え、``truth`` を使う節を落とす(真値が無い場合は、
下の**発散による独立検算**だけが残る —— それでも「どれくらい信じてよいか」は
言える、というのがこの例の要点)。

この例が示すこと:

1. **真値は定義から作れる** —— 変位場を決めてから画像を作るので、答えを知って
   いる状態で測れる。
2. **零方向への偏り**は補正しないと必ず出る。補正の有無を並べて印字する。
3. **発散は独立な検算** —— 非圧縮の場なら 0 のはずで、真値と比べるのとは別の
   経路で信頼度が分かる。
4. 既知の系統誤差(**ピークロッキング**)が、推定法を変えると**出る**。

速さは assert しない(印字するだけ)。assert するのは**正しさ**だけ。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# ★repo 直下のモジュール(pivops)を import するので、チェックアウトから
# そのまま走らせても通るように repo 直下を先頭に置く。他の例と同じ作法。
# これが無いと `py -3.11 examples/<name>.py` が ModuleNotFoundError で落ちる
# (2026-09-09 実測: 走らせる門が無かった 83 本のうち、落ちたのはこの型の 2 本だけ)。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pivops  # noqa: E402

H = W = 256
CY, CX = (H - 1) / 2.0, (W - 1) / 2.0


def rankine_like_vortex(rows, cols, gamma=700.0, core=28.0):
    """中心付近は剛体回転、外側は 1/r で落ちる渦(非圧縮 = 発散 0)。

    実験でよく見る渦の形で、**発散が厳密に 0** になるので独立検算が効く。

    ``gamma`` は循環。最大の変位は ``gamma / (2*pi*core)`` [px] で決まるので、
    既定は芯で約 4 px —— **窓 32 の 1/4 則(8 px)に収まりつつ、零方向への
    偏りが見える大きさ**に選んである(変位が 0.3 px しか無いと、補正の有無で
    差が出ず、この例の主眼が消える)。
    """
    dy_c, dx_c = rows - CY, cols - CX
    r = np.hypot(dy_c, dx_c)
    r_safe = np.maximum(r, 1e-9)
    # 接線速度: r < core は r に比例、外は 1/r
    v_t = np.where(r < core, gamma * r / (2.0 * np.pi * core ** 2),
                   gamma / (2.0 * np.pi * r_safe))
    # 接線方向の単位ベクトル(画像座標。行が下向き)
    return v_t * (-dx_c / r_safe), v_t * (dy_c / r_safe)


def main():
    print("=== 1. 真値つきの粒子画像対を作る ===")
    a, b, truth = pivops.piv_synth_pair((H, W), rankine_like_vortex,
                                        density=0.02, diameter_px=2.5, seed=7)
    print(f"  画像 {a.shape}  輝度 {a.min():.3f}..{a.max():.3f}")
    print(f"  真の変位 |d| の範囲 {np.hypot(*truth).min():.3f}..{np.hypot(*truth).max():.3f} px")

    print("\n=== 2. 相互相関で測る(補正の有無を並べる)===")
    print(f"  {'設定':<28} {'偏り dy':>9} {'偏り dx':>9} {'RMS':>8}")
    best = None
    for label, kw in (("補正なし(素の相関)", {"normalize": "none"}),
                      ("重なり補正 + 1/4 則(既定)", {})):
        flow, info = pivops.piv_cross_correlate(a, b, window=32, overlap=0.5, **kw)
        t = pivops.piv_sample_at_windows(truth, info)
        s = pivops.piv_error_stats(flow, t)
        print(f"  {label:<28} {s['bias_dy']:>+9.4f} {s['bias_dx']:>+9.4f} {s['rms']:>8.4f}")
        if not kw:
            best = (flow, info, t, s)
    flow, info, t, stats = best

    print("\n=== 3. 多段(粗い窓 → 細かい窓)===")
    mflow, minfo = pivops.piv_multipass(a, b, windows=(64, 32), overlap=0.5)
    mt = pivops.piv_sample_at_windows(truth, minfo)
    ms = pivops.piv_error_stats(mflow, mt)
    print(f"  単段 32: 格子 {tuple(flow.shape[1:])}  RMS {stats['rms']:.4f}")
    print(f"  多段 64→32: 格子 {tuple(mflow.shape[1:])}  RMS {ms['rms']:.4f}")

    print("\n=== 4. 外れ値検定 —— ここでは**害になる**(正直に出す)===")
    for thr in (2.0, 3.0, 5.0):
        m = pivops.piv_outlier_mask(mflow, threshold=thr)
        rep = pivops.piv_replace_outliers(mflow, m, "median")
        print(f"  閾値 {thr:.0f}: {int(m.sum()):2d} 本を外れ値と判定 -> 置換後 RMS "
              f"{pivops.piv_error_stats(rep, mt)['rms']:.4f}"
              f"(置換しなければ {ms['rms']:.4f})")
    bad = pivops.piv_outlier_mask(mflow, threshold=2.0)
    rr, cc = np.nonzero(bad)
    core_r = np.hypot(minfo["rows"][rr] - CY, minfo["cols"][cc] - CX)
    print(f"  判定された点の中心からの距離 {np.round(np.sort(core_r), 1)} px"
          "(芯の半径 28 px の**縁**に並ぶ)")
    print("  -> 速度勾配が折れる場所を「外れ値」と呼んでしまい、近傍中央値で"
          "均すと**本物の構造が消える**。")
    print("  -> 検定は万能ではない。勾配の急な場では閾値を上げるか、"
          "そもそも掛けない判断が要る。")
    clean = pivops.piv_replace_outliers(mflow, bad, "median")

    print("\n=== 5. 場の量と、独立な検算 ===")
    vort = pivops.piv_vorticity(clean, minfo["step"])
    div = pivops.piv_divergence(clean, minfo["step"])
    inner = (slice(2, -2), slice(2, -2))
    print(f"  渦度 中心付近 {vort[inner].max():+.5f} / 外周寄り {np.median(vort):+.5f}")
    print(f"  発散 平均 {np.mean(div[inner]):+.6f}(非圧縮なら 0。真値を使わない検算)")
    print(f"  相関のピーク比 中央値 {np.nanmedian(minfo['peak_ratio']):.2f}"
          "(1 に近い窓は当てにならない)")

    print("\n=== 6. 既知の系統誤差が出るか(ピークロッキング)===")
    print(f"  {'推定法':<12} {'真 0.1 →':>10} {'真 0.9 →':>10}")
    locked = {}
    for mode in pivops.PEAK_MODES:
        got = []
        for x in (0.1, 0.9):
            pa, pb, _ = pivops.piv_synth_pair((192, 192), (0.0, 3.0 + x),
                                              density=0.02, seed=int(x * 100) + 2)
            pf, _ = pivops.piv_cross_correlate(pa, pb, 32, 0.5, peak=mode)
            got.append(float(np.median(pf[1])) - 3.0)
        locked[mode] = got
        print(f"  {mode:<12} {got[0]:>10.3f} {got[1]:>10.3f}")
    print("  → centroid は整数へ引き寄せる(教科書どおり)。gauss3 は乗る。")

    print("\n=== 7. 物理速度へ(画素寸法と時間差は必須)===")
    v = pivops.piv_to_velocity(clean, pixel_size_m=1e-5, dt_s=2e-4)   # 10 um/px, 200 us
    print(f"  最大速さ {np.hypot(v[0], v[1]).max():.4f} m/s")

    # ---- 自己検査(速さではなく正しさだけを assert する)-------------------
    assert stats["rms"] < 0.30, stats
    assert abs(np.mean(div[inner])) < 5e-3, np.mean(div[inner])
    # 「検定を掛けると悪くなる」ことも固定する —— 都合の良い結果だけを例に
    # 残すと、次に同じ罠へ落ちる
    assert pivops.piv_error_stats(clean, mt)["rms"] > ms["rms"],         "この場では検定が害になるはず(前提が変わったら本文を書き直すこと)"
    assert locked["centroid"][0] < locked["gauss3"][0], "centroid のロッキングが出ていない"
    assert locked["centroid"][1] > locked["gauss3"][1], "centroid のロッキングが出ていない"
    assert np.isfinite(clean).all()
    print("\nPASS")


if __name__ == "__main__":
    main()
