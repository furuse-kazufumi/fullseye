# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""断面輪郭の「枠」を作る op を一巡する —— 正規化・取り直し・上下面の分離・位置合わせを閉形式で検算する。

``examples/profile_shape_inspection.py`` が「欠陥を測る」本筋なら、こちらはその手前で
形を**同じ土俵に載せる**4 つの op を、答えを知っている入力で一つずつ確かめる例。

★EXTEND: 実測の輪郭(3D スキャンの断面、影絵の輪郭、CAD の書き出し)を使うなら
``ref`` を差し替える。規約は ``(N, 2)`` の ``(x, y)``(行・列ではない)、一筆書きで
閉じているか、ほぼ閉じていること。設計形状が NACA でなければ節 3 の閉形式との
突き合わせは落とし、節 1・2・4 の「変換して戻す」検算だけを残す(これらは形に依らない)。

この例が示すこと(グラウンドトゥルース):

1. **正規化**(``profile_normalise``)—— 既知の相似変換(37.5 倍・23 度・並進)を掛けた
   輪郭を正規化すると、元の輪郭を正規化したものに 1e-9 で戻る(点の対応は保たれる)。
   正規化後は弦長 1・前縁が原点・弦が +x。
2. **等弧長の取り直し**(``profile_resample``)—— 角度を不均一に置いた円を取り直すと、
   隣接点の角度差が一様(半径 R の円なら 2π/n)になり、周長 2πR が保たれる。
3. **上面・下面の分離**(``profile_sides``)—— 対称翼 NACA 0012 の上面・下面は閉形式の
   厚み分布 ``±y_t(x)`` そのもの。開いた曲線(1 価の関数)は拒否される。
4. **位置合わせ**(``profile_align``)—— 既知の剛体変換(7 度・並進)を ``chord`` /
   ``rigid`` の両方が取り戻す。**スケールは推定しない**ので、2 % 大きい形は 2 % 大きいまま
   (大きさの誤差を吸収しない、という設計をそのまま検算する)。

読み方: 各節で「仕込んだ量」「取り戻した量」「差」を並べ、末尾の assert が閾値。
速さは印字するだけで assert しない。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

# リポジトリ直下を通す(この例は ``fullseye`` を import しないのでパスフックが効かない)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import profileops                                                # noqa: E402


def similarity(c, scale=1.0, angle_deg=0.0, shift=(0.0, 0.0)):
    """輪郭に相似変換(拡大 → 回転 → 並進)を掛ける。検算の「仕込み」側。"""
    a = np.radians(angle_deg)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return (c * scale) @ rot.T + np.asarray(shift, float)


def naca_thickness(x, t=0.12):
    """NACA 4 桁の閉形式の半厚 ``y_t(x)``(既定の開いた後縁の係数 -0.1015)。"""
    return 5.0 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2
                      + 0.2843 * x ** 3 - 0.1015 * x ** 4)


def run() -> dict:
    t0 = time.perf_counter()
    out = {}
    ref = profileops.profile_synth_naca4("2412", n=801)          # 弦 1・前縁 (0,0) の設計形状

    # ------------------------------------------------------------------ 1
    print("=== 1. 正規化 —— 相似変換を掛けた輪郭が、元と同じ枠へ戻るか ===")
    moved = similarity(ref, scale=37.5, angle_deg=23.0, shift=(120.0, -45.0))
    norm_ref = profileops.profile_normalise(ref)
    norm_moved = profileops.profile_normalise(moved)
    fr = profileops.profile_chord_frame(norm_moved)
    gap_norm = float(np.max(np.hypot(*(norm_moved - norm_ref).T)))
    gap_raw = float(np.max(np.hypot(*(norm_ref - ref).T)))
    print(f"  仕込み: 37.5 倍・23 度・並進 (120, -45)")
    print(f"  正規化後の枠: 弦長 {fr['chord']:.9f} / 前縁 ({fr['le'][0]:+.2e}, {fr['le'][1]:+.2e})"
          f" / 弦の角 {fr['angle_deg']:+.2e} 度")
    print(f"  正規化(変換後) と 正規化(元) の点ごとの最大差 {gap_norm:.2e}(点の対応は保たれる)")
    print(f"  正規化(元) と 元そのものの最大差 {gap_raw:.2e}"
          "(後縁を隙間の中点に取り直すので、生成座標とは弦がわずかに違う —— 隠さず印字)")
    out["normalise"] = {"chord": fr["chord"], "le": fr["le"].tolist(), "angle_deg": fr["angle_deg"],
                        "gap_vs_ref_normalised": gap_norm, "gap_vs_raw": gap_raw}

    # ------------------------------------------------------------------ 2
    print("\n=== 2. 等弧長の取り直し —— 不均一に置いた円が一様な角度刻みに戻るか ===")
    R, n_out = 2.5, 240
    rng = np.random.default_rng(0)
    # 角度を「密 → 疎」に偏らせて置く(cos で歪めた上に乱れも足す)
    th = np.sort(np.mod(np.pi * (1.0 - np.cos(np.linspace(0, np.pi, 1500))) + rng.normal(0, 0.002, 1500), 2 * np.pi))
    circle = np.column_stack([R * np.cos(th), R * np.sin(th)])
    seg_in = np.hypot(*np.diff(circle, axis=0).T)
    res = profileops.profile_resample(circle, n=n_out)
    ang = np.unwrap(np.arctan2(res[:, 1], res[:, 0]))
    dang = np.diff(ang)
    radius_err = float(np.max(np.abs(np.hypot(res[:, 0], res[:, 1]) - R)))
    perim = float(np.sum(np.hypot(*np.diff(np.vstack([res, res[:1]]), axis=0).T)))
    print(f"  入力 {len(circle)} 点: 隣接間隔 {seg_in.min():.2e}..{seg_in.max():.2e}"
          f"(比 {seg_in.max() / seg_in.min():.0f} 倍の粗密)")
    print(f"  取り直し {len(res)} 点: 角度刻み {np.degrees(dang.min()):.4f}..{np.degrees(dang.max()):.4f} 度"
          f"(真値 {360 / n_out:.4f})/ 半径の最大ずれ {radius_err:.1e} / 周長 {perim:.6f}(2πR = {2 * np.pi * R:.6f})")
    # 翼型でも: 余弦分布で前縁に密な点が、等弧長では均される
    res_ref = profileops.profile_resample(ref, n=400)
    s_in = np.hypot(*np.diff(ref, axis=0).T)
    s_out = np.hypot(*np.diff(res_ref, axis=0).T)
    print(f"  NACA 2412: 隣接間隔の比(最大/最小) 入力 {s_in.max() / s_in.min():.0f} → 取り直し {s_out.max() / s_out.min():.2f}")
    out["resample"] = {"n": len(res), "dang_err_deg": float(np.degrees(np.max(np.abs(dang - 2 * np.pi / n_out)))),
                       "radius_err": radius_err, "perimeter_rel_err": perim / (2 * np.pi * R) - 1.0,
                       "naca_spacing_ratio_in": float(s_in.max() / s_in.min()),
                       "naca_spacing_ratio_out": float(s_out.max() / s_out.min())}

    # ------------------------------------------------------------------ 3
    print("\n=== 3. 上面・下面の分離 —— 対称翼は閉形式の ±y_t(x) そのもの ===")
    sym = profileops.profile_synth_naca4("0012", n=801)
    sides = profileops.profile_sides(sym, n=101)
    x = sides["x"]
    yt = naca_thickness(x)
    inner = slice(1, -1)                                  # 端は前縁 (0,0) と開いた後縁
    up_err = float(np.max(np.abs(sides["upper"][inner] - yt[inner])))
    lo_err = float(np.max(np.abs(sides["lower"][inner] + yt[inner])))
    print(f"  NACA 0012 / 101 駅: 上面 − y_t の最大 {up_err:.1e} / 下面 + y_t の最大 {lo_err:.1e}"
          f" / normalised={sides['normalised']}")
    # 回して動かしても同じ(normalise=True が先に枠を合わせる)
    sides_m = profileops.profile_sides(similarity(sym, 3.0, -50.0, (7.0, 2.0)), n=101)
    moved_err = float(np.nanmax(np.abs(sides_m["upper"] - sides["upper"])))
    # 既に正規化済みなら normalise=False でも同じ
    sides_pre = profileops.profile_sides(profileops.profile_normalise(sym), n=101, normalise=False)
    pre_err = float(np.nanmax(np.abs(sides_pre["upper"] - sides["upper"])))
    print(f"  3 倍・-50 度・並進のあと {moved_err:.1e} / 正規化済みを normalise=False で {pre_err:.1e}")
    print("  (相似変換後の差が 1e-5 級なのは、後縁中点を選ぶ帯の縁で点が 1 つ入れ替わり弦の枠が"
          "わずかに動くため。厚み 0.12 に対して 1e-4 なら検査には効かないが、隠さず印字)")
    # キャンバー翼: 上下面の差は厚み(法線方向)を弦方向へ射影したもの。閉形式に近いが一致はしない
    cam = profileops.profile_sides(ref, n=101)
    mid = 0.5 * (cam["upper"] + cam["lower"])
    print(f"  NACA 2412: 上下面の中線の最大 {np.nanmax(mid):.5f}(公称キャンバー 0.02、"
          "厚みが法線方向に付くので弦方向の中線は少し低い —— 定義差)")
    # 開いた曲線(1 価の関数)は断面ではない → 拒否される
    xs = np.linspace(0.0, 1.0, 200)
    open_curve = np.column_stack([xs, 0.3 * np.exp(-3.0 * xs)])
    try:
        profileops.profile_sides(open_curve, n=51)
        refused = False
    except ValueError as e:
        refused = True
        print(f"  開いた曲線 → 拒否: {str(e)[:60]}...")
    out["sides"] = {"upper_err": up_err, "lower_err": lo_err, "moved_err": moved_err,
                    "prenormalised_err": pre_err, "camber_mid_max": float(np.nanmax(mid)),
                    "open_curve_refused": refused}

    # ------------------------------------------------------------------ 4
    print("\n=== 4. 位置合わせ —— 既知の剛体変換を取り戻し、スケールは吸収しない ===")
    ang_in, shift_in = 7.0, (0.3, -0.2)
    measured = similarity(ref, 1.0, ang_in, shift_in)
    align_res = {}
    print(f"  仕込み: 回転 {ang_in} 度・並進 {shift_in}")
    print(f"  {'mode':<7} {'角 [度]':>9} {'並進':>22} {'scale':>6} {'残差 最大':>10}")
    for mode in profileops.ALIGN_MODES:
        aligned, info = profileops.profile_align(measured, ref, mode=mode)
        resid = float(np.max(np.hypot(*(aligned - ref).T)))
        align_res[mode] = {"angle_deg": info["angle_deg"], "translation": np.asarray(info["translation"]).tolist(),
                           "scale": info["scale"], "resid": resid}
        print(f"  {mode:<7} {info['angle_deg']:>+9.4f} ({info['translation'][0]:>+8.4f}, {info['translation'][1]:>+8.4f})"
              f"      {info['scale']:>6.2f} {resid:>10.2e}")
    print("  → chord は前縁・弦角だけで、rigid は等弧長に取り直した点の最小二乗で合わせる。"
          "同じ形どうしならどちらも機械精度で戻る(並進の表し方は前縁基準と重心基準で違う)。none は動かさない。")
    # スケールは推定しない: 2 % 大きい形は 2 % 大きいまま
    bigger = similarity(ref, 1.02, ang_in, shift_in)
    al_big, info_big = profileops.profile_align(bigger, ref, mode="chord")
    chord_big = profileops.profile_chord_frame(al_big)["chord"]
    chord_ref = profileops.profile_chord_frame(ref)["chord"]
    print(f"  2 % 大きい形を chord で合わせる → 弦長 {chord_big:.5f}(設計 {chord_ref:.5f} の 1.02 倍のまま)"
          f" / scale={info_big['scale']}(推定していないことの明示)")
    out["align"] = align_res
    out["align"]["scale_kept_chord"] = chord_big
    out["align"]["chord_ref"] = chord_ref

    elapsed = time.perf_counter() - t0
    out["elapsed_s"] = elapsed
    print(f"\n所要 {elapsed:.2f} 秒")

    # ---- 自己検査(速さではなく正しさだけを assert する)---------------------
    nm = out["normalise"]
    assert abs(nm["chord"] - 1.0) < 1e-9 and np.hypot(*nm["le"]) < 1e-9 and abs(nm["angle_deg"]) < 1e-7, nm
    assert nm["gap_vs_ref_normalised"] < 1e-9, nm
    assert nm["gap_vs_raw"] < 5e-3, nm                       # 後縁中点の取り直しぶん(印字済)
    rs = out["resample"]
    assert rs["n"] == n_out and rs["dang_err_deg"] < 1e-3 and rs["radius_err"] < 2e-4, rs
    assert abs(rs["perimeter_rel_err"]) < 1e-4, rs
    assert rs["naca_spacing_ratio_out"] < 1.5 < 100 < rs["naca_spacing_ratio_in"], rs
    sd = out["sides"]
    assert sd["upper_err"] < 5e-4 and sd["lower_err"] < 5e-4, sd    # 801 点の折れ線の線形補間
    assert sd["moved_err"] < 1e-4 and sd["prenormalised_err"] < 1e-12, sd   # 後縁中点の帯(印字済)
    assert 0.015 < sd["camber_mid_max"] < 0.02, sd
    assert sd["open_curve_refused"], sd
    al = out["align"]
    assert abs(al["chord"]["angle_deg"] + ang_in) < 1e-9 and al["chord"]["resid"] < 1e-9, al
    assert abs(al["rigid"]["angle_deg"] + ang_in) < 1e-9 and al["rigid"]["resid"] < 1e-9, al
    assert al["none"]["angle_deg"] == 0.0 and al["none"]["resid"] > 0.1, al
    assert all(v["scale"] == 1.0 for k, v in al.items() if k in profileops.ALIGN_MODES), al
    assert abs(al["scale_kept_chord"] - 1.02 * al["chord_ref"]) < 1e-9, al
    print("PASS")
    return out


if __name__ == "__main__":
    result = run()
    for k, v in result.items():
        print(f"{k}: {v}")
