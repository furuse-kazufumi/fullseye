# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""仮想 SEM —— 電子を 1 個ずつ固体に撃ち、加速電圧で像も測れる線幅も変わる様子を、実測値で採点しながら見せる。

走査電子顕微鏡(SEM)の像は「表面の写真」ではない。一次電子は固体に入って何十回も散乱し、
その途中で二次電子(SE)を叩き出し、一部は反射電子(BSE)として戻ってくる。像の明るさは、その
**相互作用の体積**のどこから何が出てきたかの集計である。だから同じ部品でも、加速電圧を変えると
像も、像から測った線幅も変わる。この PoC は、その相互作用を Joy の単散乱モンテカルロ
(弾性散乱は Browning 1994 の Mott 近似、阻止能は Joy-Luo 1989)で解き、各段を**外の実測値**で
採点してから、外観検査・計測の問いに使う。

多段(各段に外部真値か閉形式の門):

1. **反射電子係数 η(Z, E)**: 7 元素(C〜Au)× 5/10/20/30 keV を、Joy の電子-固体相互作用
   データベース(rev. 04-02)に収録された実測の幅 ± 0.04 で採点する。遮蔽ラザフォードに戻すと
   重元素で外れる(門に歯があることの確認)。1 keV の比較は表に出すが門にしない。
2. **到達深さ**: 電子ごとの最大の深さを Kanaya-Okayama の R = 0.0276 A E^1.67/(Z^0.889 ρ) µm と比べ、
   電圧の指数(1.67)も当てはめで確かめる。相互作用の体積を軌跡の密度で描く。
3. **二次電子の収率の形**: δ(E)/δmax を Lin & Joy 2005 の普遍曲線と、Emax を同じ論文の Table 1 と比べる
   (λ・ε は表のまま入れ、δ の山には合わせていない)。
4. **CD-SEM の線幅**: PMMA の線(底辺 40 nm、高さ 40 nm)を 1 / 5 / 20 kV、側壁角 80 / 85 / 88 / 90 度で
   走査し、しきい値法と最大傾斜法で測る。測れる線幅が「側壁のどの高さか」を電圧と側壁角が決める
   (側壁 88 度では低加速ほど上寄り。80 度では差が小さく向きも逆)。
5. **同じ部品を 3 電圧 × 3 検出器で撮る**(レンズ内 SE / 側方 SE / 反射電子)。
6. **Si の中の W**: 表面に埋めた W(CMP 後の W プラグ相当、段差なし)は 1 kV の SE ではほとんど
   見えないのに、反射電子では浮かぶ。深さ 5〜150 nm に埋もれた W は、深いほど高い電圧が要る。
7. **帯電**: 絶縁物(PMMA)を走査し続けると、低加速では正に溜まって暗くなり(電位は
   η + δ·F(V*) = 1 の V* で止まる。二分法で別に解いた値と一致)、高加速では負に溜まって明るくなる。

予想(2026-10-15、着手前): ★ユーザーの見立て「異種材料の異物(Si の上の W)は SE では見えないのに、
反射電子の Z コントラストでは浮かぶ」。**結果は条件つきで当たった**: 段差の無い W を 1 kV で
見たときだけ成り立つ(SE +7 %、BSE +76 %)。5 kV 以上では SE も W を拾う —— 反射電子が表面を
抜けるときに叩き出す SE2 が、W の多い反射をそのまま運ぶから。「SE は表面だけ」は SE1 の話で、
SE2 は Z を見る。

外部真値の出典(数値は事実として引用し、文書は同梱しない):
  * η: Joy, D.C. "A database of electron-solid interactions", rev. 04-02 (2004); Scanning 17:270 (1995)
    に記述。収録元は Hunger & Küchler 1979 / Bishop 1963 / Heinrich 1966 / Reimer & Tollkamp 1980 /
    Neubert / Bongeler 1993 / Bronstein & Fraiman 1969 / El Gomati 1997。
  * 傾けた試料の η(θ): Arnal, Verdier & Vincensini 1969、(1 + cos θ)^(−9/√Z)(試験の門で使う)。
  * 到達深さ: Kanaya & Okayama, J. Phys. D 5:43 (1972)。
  * SE の普遍曲線と Table 1: Lin & Joy, Surf. Interface Anal. 37:895 (2005), DOI 10.1002/sia.2107。
  * 断面積と阻止能の式: Browning ほか J. Appl. Phys. 76:2016 (1994)、Joy & Luo, Scanning 11:176 (1989)、
    Joy 1995 の教科書。式の写しの確認に NIST の公開実装の記述(パブリックドメイン)を読んだ。コードは写していない。

実画像の章は未実施: CC BY 4.0 の候補(NFFA-EUROPE の SEM データセット、Aversa ほか 2018、
Sci. Data 5:180172)はあるが、線幅の真値が付いた格子・CD-SEM の像は見つからなかった(未解決)。

Fullseye 寄与: CD-SEM・外観検査の「加速電圧の選び方」を数で —— 線幅の偏り(側壁のどこを測るか)、
埋もれた異物の情報深さ、SE と BSE の使い分け、帯電の向き。``sem_render`` の sec θ を仮定でなく
軌跡の集計として出す上位の選択肢でもある。
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import examplefig as figs                                        # noqa: E402
import materials as MT                                           # noqa: E402
import semsim as SM                                              # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

#: Joy のデータベース(rev. 04-02)に収録された η の実測。(材料, keV) → 値の列。
ETA_MEASURED = {
    ("C", 5): (0.082, 0.085), ("C", 10): (0.066, 0.072, 0.069), ("C", 20): (0.049, 0.061, 0.060),
    ("C", 30): (0.051, 0.06, 0.052),
    ("AL", 5): (0.153, 0.186), ("AL", 10): (0.150, 0.177), ("AL", 20): (0.148,), ("AL", 30): (0.144, 0.149),
    ("SI", 5): (0.188, 0.206), ("SI", 10): (0.174, 0.200), ("SI", 20): (0.159, 0.194, 0.164),
    ("SI", 30): (0.152, 0.19, 0.159),
    ("CU", 5): (0.323,), ("CU", 10): (0.316, 0.339), ("CU", 20): (0.306, 0.309), ("CU", 30): (0.301, 0.306),
    ("AG", 5): (0.393, 0.418), ("AG", 10): (0.394, 0.42), ("AG", 20): (0.398, 0.408), ("AG", 30): (0.396, 0.407),
    ("W", 5): (0.449, 0.472), ("W", 10): (0.46, 0.483), ("W", 20): (0.469, 0.494), ("W", 30): (0.478, 0.501),
    ("AU", 5): (0.469, 0.489), ("AU", 10): (0.476, 0.501), ("AU", 20): (0.485, 0.506, 0.516),
    ("AU", 30): (0.49, 0.521, 0.512),
}
#: 1 keV の実測(門にしない。遮蔽ラザフォードも Browning も外れうる低エネルギーの参考)。
ETA_1KEV = {"C": (0.076, 0.133), "AL": (0.19, 0.23), "SI": (0.228, 0.235), "CU": (0.265, 0.4375),
            "W": (0.459,), "AU": (0.289, 0.419)}
ETA_MARGIN = 0.04
ELEMENTS = ("C", "AL", "SI", "CU", "AG", "W", "AU")
ZOF = {"C": 6, "AL": 13, "SI": 14, "CU": 29, "AG": 47, "W": 74, "AU": 79}


def _eta(mat, e, model, n):
    m = SM._electron_material(mat, "poc", model)
    geom = SM._ProfileGeom([0.0, 1.0], [0.0, 0.0], coll_window=1.0)
    r = SM._transport([m, m], geom, np.zeros(n), np.zeros(n), float(e), np.random.default_rng(11))
    return float(r["bse"].mean())


# --------------------------------------------------------------------------- #
def stage1_eta():
    print("\n1) 反射電子係数 η(Z, E) —— Joy のデータベースの実測の幅 ± %.2f で採点" % ETA_MARGIN)
    n = 1500 if REDUCED else 5000
    energies = (5, 20) if REDUCED else (5, 10, 20, 30)
    rows, miss_b, miss_r = [], [], []
    res = {}
    for mat in ELEMENTS:
        for e in energies:
            vals = ETA_MEASURED[(mat, e)]
            lo, hi = min(vals) - ETA_MARGIN, max(vals) + ETA_MARGIN
            eb = _eta(mat, e, "browning", n)
            er = _eta(mat, e, "rutherford", n)
            res[(mat, e)] = (eb, er)
            ok_b, ok_r = lo <= eb <= hi, lo <= er <= hi
            if not ok_b:
                miss_b.append((mat, e))
            if not ok_r:
                miss_r.append((mat, e))
            rows.append((mat, e, eb, er, vals))
    print("   %-3s %4s  %-8s %-9s  実測" % ("", "keV", "Browning", "Rutherford"))
    for mat, e, eb, er, vals in rows:
        print("   %-3s %4d  %.3f    %.3f      %s" % (mat, e, eb, er, " / ".join("%.3f" % v for v in vals)))
    print("   1 keV(門にしない): " + ", ".join(
        "%s %.2f(実測 %s)" % (m, _eta(m, 1.0, "browning", n // 2), "〜".join("%.2f" % v for v in ETA_1KEV[m]))
        for m in ("SI", "CU", "AU")))
    print("   → Browning で外れた組: %s / 遮蔽ラザフォードで外れた組: %s"
          % (miss_b or "なし", miss_r or "なし"))
    assert not miss_b, "Browning の η が実測の幅から外れた: %r" % miss_b
    assert any(m in ("AG", "W", "AU") for m, _ in miss_r), "遮蔽ラザフォードでも全部通った(門に歯が無い)"
    return res, energies


def _density_image(tracks, rko, nx=200, nz=100):
    """軌跡の折れ線を細かく刻んで (x, z) の 2-D 密度にする(相互作用の体積の絵)。

    枠は横 ±1.1 R_KO・深さ 1.1 R_KO で、横 200 × 深さ 100 区間 = 縦横の 1 区間が同じ長さ
    (縮尺が違うと梨形が潰れて見える)。
    """
    pts = []
    for t in tracks:
        if t.shape[0] < 2:
            continue
        seg = np.diff(t, axis=0)
        ln = np.linalg.norm(seg, axis=1)
        k = np.maximum(1, np.ceil(ln / (rko / 200.0)).astype(int))
        for a, s, kk in zip(t[:-1], seg, k):
            f = (np.arange(kk) + 0.5) / kk
            pts.append(a[None, :] + f[:, None] * s[None, :])
    p = np.concatenate(pts)
    h, _, _ = np.histogram2d(p[:, 2], p[:, 0], bins=(nz, nx), range=((0.0, 1.1 * rko), (-1.1 * rko, 1.1 * rko)))
    return np.log1p(h) / max(np.log1p(h).max(), 1e-12)


def stage2_range():
    print("\n2) 到達深さ —— Kanaya-Okayama の R_KO と比べる")
    nt = 120 if REDUCED else 400
    out, imgs, caps = {}, [], []
    for mat in ("SI", "AU"):
        p95 = []
        for e in (5.0, 10.0, 20.0):
            r = SM.sem_electron_mc(mat, e, tol=0.02, batch=1000, max_electrons=2000 if REDUCED else 4000,
                                   seed=3, n_tracks=nt)
            out[(mat, e)] = r
            p95.append(r["depth_p95_nm"])
            print("   %-2s %4.0f keV: R_KO %7.0f nm、最大 %.2f R_KO、p95 %.2f R_KO、p50 %.2f R_KO、横の 95 %% 半径 %.2f R_KO"
                  % (mat, e, r["range_ko_nm"], r["depth_max_nm"] / r["range_ko_nm"],
                     r["depth_p95_nm"] / r["range_ko_nm"], r["depth_p50_nm"] / r["range_ko_nm"],
                     r["lateral_p95_nm"] / r["range_ko_nm"]))
            assert 0.75 <= r["depth_max_nm"] / r["range_ko_nm"] <= 1.05, (mat, e)
        slope = float(np.polyfit(np.log([5.0, 10.0, 20.0]), np.log(p95), 1)[0])
        out[(mat, "slope")] = slope
        print("   %-2s: p95 の深さ ∝ E^%.2f(Kanaya-Okayama は E^1.67)" % (mat, slope))
        assert 1.45 <= slope <= 1.85, (mat, slope)
    for mat, e in (("SI", 5.0), ("SI", 20.0), ("AU", 20.0)):
        r = out[(mat, e)]
        imgs.append(_density_image(r["tracks"], r["range_ko_nm"]))
        caps.append("%s %d keV(横 ±%.0f nm、深さ %.0f nm)" % (mat, e, 1.1 * r["range_ko_nm"], 1.1 * r["range_ko_nm"]))
    r1 = SM.sem_electron_mc("SI", 1.0, tol=0.05, batch=nt, max_electrons=nt, seed=3, n_tracks=nt)
    imgs.insert(0, _density_image(r1["tracks"], r1["range_ko_nm"]))
    caps.insert(0, "SI 1 keV(横 ±%.0f nm、深さ %.0f nm)" % (1.1 * r1["range_ko_nm"], 1.1 * r1["range_ko_nm"]))
    figs.save_grid("sem_interaction_volume", imgs, captions=caps, ncols=2,
                   title="相互作用の体積(軌跡の密度、各パネルは自分の R_KO で正規化した枠)",
                   caption="一次電子 %d 本の軌跡の密度(対数)。枠は各条件の Kanaya-Okayama の到達深さ R_KO の "
                           "1.1 倍。Si は 1 → 5 → 20 keV で R_KO が 31 nm → 0.47 µm → 4.7 µm と伸び、形は"
                           "「梨形」のまま相似に広がる。Au(20 keV)は R_KO が Si の 1/5.5 で、浅い所で大きく曲がって"
                           "戻る(反射電子が多い)。" % nt)
    return out


def stage3_se_curve():
    print("\n3) 二次電子の収率 δ(E) —— Lin & Joy 2005 の普遍曲線と Table 1 の Emax")
    es = np.geomspace(0.1, 12.0, 12 if REDUCED else 18)
    n = 700 if REDUCED else 2500
    series, res = [], {}
    for mat in ELEMENTS:
        r = SM.sem_yield_curve(mat, es, n_electrons=n, seed=5)
        ref = MT.material_electron_properties(mat)["se_ref"]
        res[mat] = r
        print("   %-2s: Emax %.3f keV(表 %.2f、%+.0f %%)、δmax %.2f(表 %.2f)、形の RMS %.3f"
              % (mat, r["emax_kev"], ref[1], 100 * (r["emax_kev"] / ref[1] - 1), r["delta_max"], ref[0], r["shape_rms"]))
        x = np.log10(r["energies_kev"] / r["emax_kev"])
        label = {"C": "C / Al / Si / Cu / Ag", "W": "W / Au"}.get(mat, "")
        series.append((label, x, r["se_yield"] / r["delta_max"]))
    for mat in ("C", "AL", "SI", "CU", "AG"):
        r = res[mat]
        assert r["shape_rms"] <= 0.08, (mat, r["shape_rms"])
        assert abs(r["emax_kev"] / MT.material_electron_properties(mat)["se_ref"][1] - 1) <= 0.20, mat
    xs = np.geomspace(0.1, 40.0, 120)
    series.append(("普遍曲線(Lin & Joy 2005)", np.log10(xs), SM.sem_se_universal_curve(xs)))
    dmr = np.mean([res[m]["delta_max"] / MT.material_electron_properties(m)["se_ref"][0] for m in ELEMENTS])
    print("   → 軽〜中の 5 元素は形が普遍曲線に RMS ≤ 0.08、Emax も表の ±20 %% に入る(合わせていない)。"
          "δmax は表の平均 %.2f 倍(低め)。W・Au は裾が厚く形が合わない(SE2 が主になる。未解決)。" % dmr)
    figs.save_plot("sem_se_universal_curve", series, xlabel="log10(E / Emax)", ylabel="δ / δmax",
                   title="二次電子の収率の形: 7 元素の MC と普遍曲線",
                   styles=[None] * len(ELEMENTS) + ["dashed"],
                   colors=["neutral"] * 5 + ["wrong", "wrong", "reference"],
                   caption="δ(E) を各元素の MC の山(Emax, δmax)で割った形(横軸は対数)。破線は Lin & Joy 2005 の普遍曲線"
                           "(式 12)。C〜Ag の 5 元素は重なる。W と Au(赤)は E > 3 Emax で裾が厚い —— 重元素は"
                           "反射電子が多く、表面を抜けるときに作る SE2 が主になるので、SE1 だけを仮定した普遍曲線"
                           "からずれる(未解決のまま数で固定)。")
    return res


def _cd(r, det="inlens"):
    out = {}
    for m in ("threshold", "max_slope"):
        out[m] = SM.sem_cd_measure(np.stack([r["x_nm"], r[det]], axis=1), method=m, smooth_nm=1.5)["width_nm"]
    return out


def stage4_cd():
    print("\n4) CD-SEM: PMMA の線(底辺 40 nm、高さ 40 nm)を Si の上で測る")
    npp = 250 if REDUCED else 900
    step = 2.0 if REDUCED else 1.0
    kvs = (1.0, 5.0, 20.0)
    swas = (80.0, 88.0) if REDUCED else (80.0, 85.0, 88.0, 90.0)
    table, prof = {}, {}
    print("   %5s %5s  %6s %6s  %8s %8s  %s" % ("kV", "側壁", "底辺", "上辺", "しきい値", "最大傾斜", "測った高さ(底=0,上=1)"))
    for swa in swas:
        for kv in kvs:
            r = SM.sem_line_profile("PMMA", "SI", kv, width_nm=40, height_nm=40, sidewall_deg=swa,
                                    beam_sigma_nm=1.0, x_half_range_nm=50, x_step_nm=step,
                                    electrons_per_point=npp, seed=1)
            c = _cd(r)
            wb, wt = r["width_bottom_nm"], r["width_top_nm"]
            frac = (wb - c["threshold"]) / max(wb - wt, 1e-9) if swa < 90 else float("nan")
            table[(swa, kv)] = (c["threshold"], c["max_slope"], wb, wt, frac)
            prof[(swa, kv)] = r
            print("   %5.0f %5.0f  %6.1f %6.1f  %8.1f %8.1f  %s"
                  % (kv, swa, wb, wt, c["threshold"], c["max_slope"], "%.2f" % frac if swa < 90 else "-"))
            assert wt - 2.0 <= c["threshold"] <= wb + 2.0, "線幅が上辺〜底辺の外: %r" % ((swa, kv, c),)
    for swa in swas:
        if swa < 90:
            f1, f20 = table[(swa, 1.0)][4], table[(swa, 20.0)][4]
            print("   側壁 %.0f 度: 1 kV は側壁の高さ %.2f を、20 kV は %.2f を測っている" % (swa, f1, f20))
    f1, f20 = table[(88.0, 1.0)][4], table[(88.0, 20.0)][4]
    assert f1 > f20 + 0.2, "側壁 88 度で、1 kV が 20 kV より上を測っていない: %.2f vs %.2f" % (f1, f20)
    d = table[(88.0, 20.0)][0] - table[(88.0, 1.0)][0]
    print("   → ★側壁が立った線(88 度)では、しきい値法の線幅が 1 kV と 20 kV で %.1f nm 違う: 低加速は側壁の"
          "上寄り(%.2f)を、高加速は根元(%.2f)を測る。" % (d, f1, f20))
    f80 = (table[(80.0, 1.0)][4], table[(80.0, 20.0)][4])
    print("   → ただし側壁 80 度では電圧の差は小さく、向きも逆(1 kV %.2f / 20 kV %.2f)。"
          "「低加速ほど上を測る」は一般則ではなく、側壁角しだい。" % f80)
    if (90.0, 1.0) in table:
        print("   → 垂直の側壁(90 度)では、どの電圧でも真の幅より太く測る(1 / 5 / 20 kV で %+.1f / %+.1f / %+.1f nm)。"
              % tuple(table[(90.0, kv)][0] - 40.0 for kv in kvs))
    series = []
    for kv, col in zip(kvs, ("right", "emphasis", "wrong")):
        r = prof[(88.0, kv)]
        y = r["inlens"] / np.median(r["inlens"][np.abs(r["x_nm"]) >= 35])
        series.append(("%d kV" % kv, r["x_nm"], y))
    figs.save_plot("sem_cd_profiles_by_kv", series, xlabel="x [nm]", ylabel="信号 / 基板の水準",
                   title="同じ PMMA の線(底辺 40 nm・側壁 88 度)の線プロファイル: 1 / 5 / 20 kV",
                   colors=["right", "emphasis", "wrong"],
                   caption="レンズ内の SE の線プロファイル(基板の水準で割った)。1 kV は PMMA の上面そのものが明るく"
                           "(PMMA は Si より δ が大きく、電子が線の中に収まる)、5 kV と 20 kV は縁だけが明るい山になる。"
                           "線幅を測る縁の位置が電圧で動く。")
    rows = [["%.0f" % kv, "%.0f" % swa, "%.1f" % v[2], "%.1f" % v[3], "%.1f" % v[0], "%.1f" % v[1],
             "%.2f" % v[4] if swa < 90 else "-"] for (swa, kv), v in sorted(table.items())]
    figs.save_table("sem_cd_bias_table", ["kV", "側壁 [度]", "底辺", "上辺", "しきい値法", "最大傾斜法", "測った高さ"],
                    rows, title="CD-SEM の線幅 [nm]: 加速電圧と側壁角で、測っている高さが動く",
                    caption="PMMA の線(高さ 40 nm)を Si の上で。測った高さ = (底辺 − しきい値法の線幅)/(底辺 − 上辺)、"
                            "0 = 根元、1 = 上端。ビーム σ = 1 nm、平滑 1.5 nm。")
    return table


def _device(n, p):
    """同じ部品: PMMA の線 2 本(高さ 30 nm)と、その間の Si の上の W の粒(高さ 4 nm)。"""
    yy, xx = np.mgrid[:n, :n]
    h = np.zeros((n, n))
    mm = np.zeros((n, n), dtype=np.int64)
    w = max(3, int(round(16.0 / p)))
    c1, c2 = n // 4, 3 * n // 4
    for c in (c1, c2):
        h[:, c - w // 2:c - w // 2 + w] = 30.0
    rr = max(2.0, 7.0 / p)
    dot = (xx - n / 2) ** 2 + (yy - n / 2) ** 2 <= rr ** 2
    h[dot] = 4.0
    mm[dot] = 1
    return h, mm, dot


def stage5_device_images():
    print("\n5) 同じ部品を 3 電圧 × 3 検出器で撮る(PMMA の線 2 本 + Si の上の W の粒)")
    n, p = (24, 4.0) if REDUCED else (40, 2.4)
    npp = 12 if REDUCED else 90
    h, mm, dot = _device(n, p)
    panels, caps, stats = [], [], {}
    for kv in (1.0, 5.0, 20.0):
        sig = SM.sem_image(h, mm, materials=("PMMA", "W"), substrate="SI", energy_kev=kv, pixel_nm=p,
                           beam_sigma_nm=1.0, electrons_per_pixel=npp, return_signals=True, seed=4)
        ring = (~dot) & (h == 0)
        line = h == 30.0
        stats[(kv, "eta_line")] = float(sig["eta"][line].mean())
        stats[(kv, "eta_sub")] = float(sig["eta"][ring].mean())
        for det in ("inlens", "everhart", "bse"):
            img = sig[det]
            bg = float(np.median(img[ring]))
            c = float(img[dot].mean() / bg - 1.0)
            stats[(kv, det)] = c
            panels.append(img)
            caps.append("%d kV %s(W の粒 %+.0f %%)" % (kv, {"inlens": "レンズ内 SE", "everhart": "側方 SE",
                                                         "bse": "反射電子"}[det], 100 * c))
        print("   %4.0f kV: W の粒のコントラスト  レンズ内 SE %+.0f %%  側方 SE %+.0f %%  反射電子 %+.0f %%"
              "   (η: PMMA の線の上 %.2f / 線の間の Si %.2f)"
              % (kv, 100 * stats[(kv, "inlens")], 100 * stats[(kv, "everhart")], 100 * stats[(kv, "bse")],
                 stats[(kv, "eta_line")], stats[(kv, "eta_sub")]))
    print("   → 反射電子では PMMA の線と Si の差がほぼ消える: 細い線(幅 16 nm)は電子が側壁から抜けて η が"
          "バルクの PMMA より大きく、線の間の Si は溝の影で η がバルクの Si より小さい。")
    # 濃淡: SE はパネルごとにコントラストを合わせる(実機の明るさ・コントラスト調整と同じ。SE の総量は
    # 電圧で 1 桁落ちるので、共通にすると 20 kV が真っ暗で形が読めない)。反射電子は 3 電圧で共通
    # (パネルごとに引き伸ばすと、差の無い 20 kV で雑音だけが強調される)。
    allb = np.concatenate([panels[3 * k + 2].ravel() for k in range(3)])
    vb = (float(np.percentile(allb, 1)), float(np.percentile(allb, 99.5)))
    vrange = [vb if i % 3 == 2 else (float(np.percentile(panels[i], 1)), float(np.percentile(panels[i], 99.5)))
              for i in range(len(panels))]
    figs.save_grid("sem_same_part_3kv_3detectors", panels, captions=caps, ncols=3, gray=True, vrange=vrange,
                   title="同じ部品(PMMA の線 2 本 + W の粒)を 1 / 5 / 20 kV × 3 検出器で",
                   caption="行 = 加速電圧、列 = 検出器。SE の 2 列はパネルごとにコントラストを合わせた(実機の調整と同じ。"
                           "SE の総量は 1 → 20 kV で 1 桁落ちる)。反射電子の列は 3 電圧で共通の濃淡。"
                           "1 kV のレンズ内 SE は PMMA の上面が明るい。5 / 20 kV では線の縁だけが明るい帯になる。側方の SE は"
                           "検出器(右)を向く縁が明るい。反射電子は W の粒が 1 kV で最も浮き、電圧を上げると電子が粒を"
                           "突き抜けて薄まる。PMMA の線は反射電子ではほぼ消える(細い線は側壁から電子が抜け、溝の Si は"
                           "影になるので η の差が相殺する)。1 画素 %.1f nm、画素あたり %d 電子(雑音は撃った電子の数そのもの)。"
                           % (p, npp))
    return stats


def stage6_tungsten():
    print("\n6) Si の中の W —— 表面に埋めた W と、深さ 5〜150 nm に埋もれた W")
    npp = 1200 if REDUCED else 4000
    depths = (0.0, 20.0, 150.0) if REDUCED else (0.0, 5.0, 20.0, 50.0, 150.0)
    kvs = (1.0, 5.0, 20.0) if REDUCED else (1.0, 3.0, 5.0, 10.0, 20.0)
    tab = {}
    for d in depths:
        for kv in kvs:
            r = SM.sem_line_profile("SI", "SI", kv, width_nm=60, height_nm=0.0, x_half_range_nm=400,
                                    x_step_nm=400, electrons_per_point=npp, beam_sigma_nm=0.0,
                                    buried=[("W", -50.0, 50.0, d, d + 60.0)], seed=2)
            c = {k: float(r[k][1] / (0.5 * (r[k][0] + r[k][2])) - 1.0) for k in ("inlens", "everhart", "bse")}
            tab[(d, kv)] = c
    print("   W の上端の深さ  " + "  ".join("%5.0f kV(BSE / SE)" % kv for kv in kvs))
    for d in depths:
        print("   %8.0f nm    " % d + "  ".join("%+6.0f%% / %+5.0f%%" % (100 * tab[(d, kv)]["bse"],
                                                                         100 * tab[(d, kv)]["inlens"]) for kv in kvs))
    flush = tab[(0.0, 1.0)]
    print("   → ★表面に埋めた W を 1 kV で: 反射電子 %+.0f %%、レンズ内 SE %+.0f %% —— SE ではほとんど見えない。"
          % (100 * flush["bse"], 100 * flush["inlens"]))
    assert flush["bse"] > 0.5 and abs(flush["inlens"]) < 0.15, flush
    deep = tab[(150.0, 1.0)]["bse"], tab[(150.0, 20.0)]["bse"]
    print("   → 深さ 150 nm の W: 1 kV では反射電子でも %+.0f %%(電子が届かない)、20 kV で %+.0f %%。"
          % (100 * deep[0], 100 * deep[1]))
    assert abs(deep[0]) < 0.1 and deep[1] > 0.4, deep
    f5 = tab[(0.0, 5.0)]
    print("   → ただし 5 kV では表面の W も SE で %+.0f %%(反射電子が抜けるときの SE2 が Z を運ぶ)。"
          "「SE では見えない」は低加速の SE1 の話。" % (100 * f5["inlens"]))
    rows = [["%.0f" % d] + ["%+.0f / %+.0f" % (100 * tab[(d, kv)]["bse"], 100 * tab[(d, kv)]["inlens"]) for kv in kvs]
            for d in depths]
    figs.save_table("sem_buried_w_contrast", ["W の上端の深さ [nm]"] + ["%.0f kV" % kv for kv in kvs], rows,
                    title="埋もれた W のコントラスト [%](BSE / SE)",
                    caption="Si に埋もれた W(幅 100 nm、厚さ 60 nm)の、真上と 400 nm 離れた Si の平均との比 − 1"
                            "(反射電子 / レンズ内 SE)。深い W ほど高い電圧が要る(情報深さ)。"
                            "表面の W は 1 kV の SE ではほぼ見えないのに反射電子では浮く。")
    # 2-D: 表面に埋めた W を 1 kV で SE と BSE、深さ 50 nm の W を 1 / 10 kV の BSE で。
    n, p = (20, 6.0) if REDUCED else (40, 3.0)
    yy, xx = np.mgrid[:n, :n]
    disk = (xx - (n - 1) / 2) ** 2 + (yy - (n - 1) / 2) ** 2 <= (n / 4) ** 2
    e_pp = 15 if REDUCED else 50
    panels, caps = [], []
    for kv, top, det, lab in ((1.0, 0.0, "inlens", "表面 1 kV SE"),
                              (1.0, 0.0, "bse", "表面 1 kV BSE"),
                              (1.0, 50.0, "bse", "深さ 50 nm 1 kV BSE"),
                              (10.0, 50.0, "bse", "深さ 50 nm 10 kV BSE")):
        img = SM.sem_image(np.zeros((n, n)), energy_kev=kv, pixel_nm=p, electrons_per_pixel=e_pp,
                           detector=det, buried=[("W", disk, top, top + 60.0)], seed=6, return_signals=True)[det]
        panels.append(img / max(float(np.median(img[~disk])), 1e-9))
        caps.append(lab)
    figs.save_grid("sem_tungsten_se_vs_bse", panels, captions=caps, ncols=2, gray=True, vrange=(0.0, 3.0),
                   title="Si の中の W の円板: SE では消え、反射電子では浮く(深いと電圧が要る)",
                   caption="各パネルは Si の水準で割った信号(0〜3 で共通の濃淡)。表面に埋めた W(段差なし)は 1 kV の"
                           "レンズ内 SE ではほぼ見えず、反射電子では明るい円板。深さ 50 nm の W は 1 kV の反射電子では"
                           "見えず、10 kV で浮かぶ。1 画素 %.0f nm、画素あたり %d 電子。" % (p, e_pp))
    return tab


def stage7_charging():
    print("\n7) 帯電: PMMA を走査し続ける(コマ送り)")
    n = 6 if REDUCED else 10
    fr = 30 if REDUCED else 60
    h = np.zeros((n, n))
    series, out = [], {}
    for kv, col in ((0.5, "right"), (1.0, "emphasis"), (5.0, "neutral"), (20.0, "wrong")):
        kw = dict(materials=("PMMA",), substrate="PMMA", energy_kev=kv, electrons_per_pixel=40, seed=3)
        r = SM.sem_charging_series(h, frames=fr, spread_px=0.0, return_potential=True, **kw)
        sig = SM.sem_image(h, return_signals=True, **kw)
        balance = float((sig["eta"] + sig["se_total"]).mean())
        v = r["potential_v"].mean(axis=(1, 2))
        i = r["video"].mean(axis=(1, 2))
        out[kv] = (balance, float(v[-1]), float(i[-5:].mean() / i[0]))
        print("   %4.1f kV: η + δ = %.2f、%d コマ後の電位 %+.1f V、明るさ %.2f 倍"
              % (kv, balance, fr, v[-1], i[-5:].mean() / i[0]))
        series.append(("%.1f kV(η+δ = %.2f)" % (kv, balance), np.arange(fr), i / i[0]))
        if kv == 0.5:
            eta, dl = sig["eta"], sig["se_total"]
            worst = 0.0
            for (a, b) in zip(*np.nonzero(eta + dl > 1.05)):
                lo, hi = 0.0, 1e4
                for _ in range(80):
                    mid = 0.5 * (lo + hi)
                    if eta[a, b] + dl[a, b] * float(SM.sem_se_escape_fraction(mid)) > 1.0:
                        lo = mid
                    else:
                        hi = mid
                worst = max(worst, abs(r["potential_v"][-1, a, b] - lo))
            print("        正に帯電した画素の電位は、η + δ·F(V*) = 1 を二分法で別に解いた V* と最大 %.1e V で一致" % worst)
            assert worst < 1e-3, worst
    assert out[0.5][2] < 0.8 and out[20.0][2] > 1.2, out
    print("   → 低加速(η + δ > 1)は正に溜まって暗く、自己調整で止まる。高加速(η + δ < 1)は負に溜まり続けて明るくなる"
          "(漏れ・着地エネルギーの低下は入れていない現象論)。")
    figs.save_plot("sem_charging_by_kv", series, xlabel="コマ", ylabel="明るさ / 1 コマ目",
                   title="PMMA の帯電: 低加速は暗くなって止まり、高加速は明るくなり続ける",
                   colors=["right", "emphasis", "neutral", "wrong"],
                   caption="同じ PMMA の面を走査し続けたときの平均の明るさ(1 コマ目で割った)。η + δ > 1 の 0.5 / 1 kV は"
                           "正に帯電して二次電子が引き戻され暗くなり、η + δ·F(V*) = 1 の電位で止まる。η + δ < 1 の 5 / 20 kV は"
                           "負に溜まり続け明るくなる(漏れを入れない上限の振る舞い)。")
    # 動く図: PMMA の線(Si の上)を 5 kV で走査し続けると縁から明るくなる。
    m = 16 if REDUCED else 32
    hh = np.zeros((m, m)); mm = np.zeros((m, m), dtype=np.int64)
    hh[:, m // 3:2 * m // 3] = 30.0
    vid = SM.sem_charging_series(hh, mm, materials=("PMMA",), substrate="SI", energy_kev=5.0, pixel_nm=3.0,
                                 electrons_per_pixel=20, frames=24, spread_px=1.0, seed=8)
    figs.save_gif("sem_charging_pmma_line", list(vid), fps=6.0,
                  caption="Si の上の PMMA の線を 5 kV で 24 コマ走査し続けた像。PMMA だけが負に帯電して明るくなり、"
                          "接地した Si は変わらない。")
    return out


# --------------------------------------------------------------------------- #
def main():
    t0 = time.process_time()
    print("仮想 SEM: 電子と固体の相互作用のモンテカルロ(%s)" % ("縮小" if REDUCED else "全量"))
    print("=" * 68)
    eta, energies = stage1_eta()
    rng = stage2_range()
    se = stage3_se_curve()
    cd = stage4_cd()
    dev = stage5_device_images()
    w = stage6_tungsten()
    ch = stage7_charging()
    if figs.errors():
        print("   図の書き出しで失敗:", "; ".join(figs.errors()))
    elif figs.enabled():
        print("   図を書き出した。")
    cpu = time.process_time() - t0
    print("\n8) まとめ")
    print("   η: 7 元素 × %s keV が実測の幅に入る(Browning)。遮蔽ラザフォードは重元素で過大。" % "/".join(map(str, energies)))
    print("   到達深さ: 最大は R_KO の 0.75〜1.05 倍、p95 ∝ E^%.2f(Si)/ E^%.2f(Au)。"
          % (rng[("SI", "slope")], rng[("AU", "slope")]))
    print("   SE: C〜Ag の形は普遍曲線に RMS ≤ %.3f、W・Au は裾が厚い(未解決)。"
          % max(se[m]["shape_rms"] for m in ("C", "AL", "SI", "CU", "AG")))
    print("   CD: 側壁 88 度で 1 kV %.1f nm / 20 kV %.1f nm(底辺 40、上辺 %.1f)。"
          % (cd[(88.0, 1.0)][0], cd[(88.0, 20.0)][0], cd[(88.0, 1.0)][3]))
    print("   W: 表面の W は 1 kV で BSE %+.0f %% / SE %+.0f %%。部品の W の粒は 1 kV のレンズ内 SE で %+.0f %%、反射電子で %+.0f %%。"
          % (100 * w[(0.0, 1.0)]["bse"], 100 * w[(0.0, 1.0)]["inlens"], 100 * dev[(1.0, "inlens")],
             100 * dev[(1.0, "bse")]))
    print("   帯電: 0.5 kV は %+.1f V で停止、20 kV は %+.0f V まで負に。" % (ch[0.5][1], ch[20.0][1]))
    print("   所要(CPU 時間): %.1f 秒" % cpu)
    if REDUCED:
        assert cpu < 120.0, "縮小の走行が CPU 120 秒を超えた: %.1f" % cpu
    print("\nPASS: η(Z,E) は実測の幅に、到達深さは Kanaya-Okayama に、SE の形と Emax は Lin & Joy 2005 に合う。"
          "線幅は加速電圧と側壁角で「側壁のどの高さを測るか」が変わり、表面の W は低加速の SE では消えて反射電子で浮かび、"
          "帯電は低加速で自己調整・高加速で溜まり続ける。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
