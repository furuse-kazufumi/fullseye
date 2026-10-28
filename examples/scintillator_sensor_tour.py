# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""scintillator_sensor_tour — X 線 1 個は、Si フォトダイオードの電子何個になるか(シンチレータ積層のセンサ)。

    py -3.11 examples/scintillator_sensor_tour.py

X 線の平面検出器・CT・食品検査のラインセンサは、X 線を直接は数えない。シンチレータ(X 線を光に変える
結晶・蛍光体)で可視光に変え、その光を Si のフォトダイオードで電子にする。X 線 1 個が電子何個になるかは
3 つの掛け算で決まる —— **止める割合 × 光の数 × 光が電子になる割合**。この例は 7 種のシンチレータで、
その 3 つを 1 つずつ図にする(op は ``fs.ledger.scintillator_sensor_qe``)。

【この例が示すこと】
1. **止める割合は K 吸収端で跳ぶ** —— 厚さ 0.6 mm の吸収効率 1 − e^{−μt}。重い元素の K 殻を叩けるエネルギーを
   越えた瞬間に μ が数倍になる(Gd 50.2 keV で GOS:Tb の吸収が 0.76 → 1.00)。端の直前と直後を op で測る。
   「X 線をよく止める材料」はエネルギーの帯ごとに入れ替わる。
2. **よく止める材料が、電子を多く出すとは限らない** —— 電子の数 = 吸収 × 光収率 × E × 重なり。BGO は Bi の
   K 端の上でも CsI:Tl の数分の 1 の電子しか出さない(光収率 8,500 対 56,000)。op は K 蛍光の逃げを入れない
   (吸収した X 線はエネルギーを全部置いていくとみなす)ので、K 端の直上では高 Z の側に甘い —— Bi の K 端の
   直上では逃げる Kα(約 77 keV)が X 線のエネルギーの 8 割を持ち出しうるので、実際の BGO の電子の数はこれより
   少なく、「BGO の方が少ない」という結論はむしろ強まる。光収率は文献で大きくばらつく
   材料があり、その幅を帯で描く。CdWO4 の帯 20,000〜28,000 は、絶対値として測った 2 つの値(Si フォトダイオードの
   絶対測定 1988 / 推定 1995)の違い。7,800〜15,800 という更に低い文献値は、減衰 13 µs に対して短い整形時間と、
   光電子の数を光子の数として書いたことによるので帯に入れない。GOS:Tb は光収率の一次文献が無いので描かない。
3. **発光の形が重なりを変える** —— 光が電子になる割合 Q̄ = ∫ S(λ) QE(λ) dλ。材料表の発光の成分(エネルギー軸の
   ガウス、波長軸へはヤコビアン hc/λ² で移す。GOS:Tb は Tb³⁺ の線の束)と Si の QE を重ねる。QE は 500 nm 付近で
   上に凸の山なので、帯を極大の 1 本の線で近似すると Q̄ を大きく見積もる(BGO で +6.6 %)。LSO は厚い結晶を
   通ると Ce³⁺ の自己吸収で極大が 402 → 453 nm に動き、Q̄ が上がる。

【グラウンドトゥルース】吸収は閉形式 1 − exp(−ρ (μ/ρ) t)(μ/ρ と K 端の位置は NIST SRD 126 の表)。
発光の幅・重みは一次文献の図から読んだ値(材料表の成分ごとの出典と ``digitized_from_figure``)。
線の束の重なりは Σ wᵢ·QE(λᵢ) と一致することを確かめる。
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs              # noqa: E402
import fullseye as fs                  # noqa: E402  公開経路(fs.ledger.<名前>)から呼ぶ
import materials_xray_data as MX       # noqa: E402  K 端の位置(NIST SRD 126 の元素の表)

L = fs.ledger
T_MM = 0.6                     # シンチレータの厚さ [mm](胸部 X 線の平面検出器の CsI:Tl の典型)
E_LO, E_HI, N_E = 10.0, 150.0, 561
#: (表の名前, 図の名前, 重い元素の記号)
MATERIALS = (("CSI:TL", "CsI:Tl", ("I", "Cs")), ("NAI:TL", "NaI:Tl", ("I",)),
             ("BI4GE3O12", "BGO", ("Ge", "Bi")), ("LU2SIO5:CE", "LSO", ("Lu",)),
             ("LU1.8Y0.2SIO5:CE", "LYSO", ("Y", "Lu")), ("CDWO4", "CdWO4", ("Cd", "W")),
             ("GD2O2S:TB", "GOS:Tb", ("Gd",)))
COLOURS = ("#0072B2", "#56B4E9", "#D55E00", "#009E73", "#8FBF3F", "#CC79A7", "#E69F00")   # Okabe–Ito 系


def _k_edge(symbol):
    el = {e["symbol"]: e for e in MX.XRAY_ELEMENTS}[symbol]
    return float([r[0] for r in el["rows"] if r[3] == "K"][0])


def _qe_curve():
    import spectralrad
    return np.asarray(spectralrad.silicon_photodiode_qe(), dtype=np.float64)


def run() -> dict:
    t0 = time.perf_counter()
    out = {}
    res = {}
    for name, label, _ in MATERIALS:
        kw = {"light_yield_per_mev": 1.0} if name == "GD2O2S:TB" else {}   # GOS: 吸収と重なりだけ使う
        res[name] = L.scintillator_sensor_qe(name, T_MM, E_LO, E_HI, N_E, **kw)

    # ---- 1. K 吸収端で吸収が跳ぶ ---------------------------------------------------- #
    print("1. 厚さ %.1f mm のシンチレータが X 線を止める割合 —— K 吸収端の直前と直後(op で測る)" % T_MM)
    jumps = []
    for name, label, heavy in MATERIALS:
        for sym in heavy:
            ek = _k_edge(sym)
            if not (E_LO < ek < E_HI):
                continue
            kw = {"light_yield_per_mev": 1.0} if name == "GD2O2S:TB" else {}
            a = L.scintillator_sensor_qe(name, T_MM, ek * (1 - 1e-4), ek * (1 + 1e-4), 2, **kw)["absorption_efficiency"]
            jumps.append((label, sym, ek, float(a[0]), float(a[1])))
            print("   %-7s %-2s K 端 %6.2f keV:  %.3f → %.3f%s" % (label, sym, ek, a[0], a[1],
                                                           "   (両側とも止め切っていて跳びが見えない)"
                                                           if a[0] > 0.995 else ""))
    assert all(after >= before for *_, before, after in jumps), jumps
    # 手前で 98 % 未満しか止めていない端は、どれも 0.1 以上跳ぶ(Cs は I の端の直後なので 0.991 → 1.000 と小さい)
    seen = [j for j in jumps if j[3] <= 0.98]
    assert {j[1] for j in seen} == {"I", "Bi", "Lu", "W", "Gd"} and all(j[4] - j[3] > 0.1 for j in seen), seen
    gd = [j for j in jumps if j[1] == "Gd"][0]
    out["gd_jump"] = (gd[3], gd[4])
    i100 = int(np.argmin(np.abs(res["CSI:TL"]["energy_kev"] - 100.0)))
    best100 = max(MATERIALS, key=lambda m: res[m[0]]["absorption_efficiency"][i100])
    print("   100 keV を一番よく止めるのは %s(%.2f)、CsI:Tl は %.2f しか止めない"
          % (best100[1], res[best100[0]]["absorption_efficiency"][i100], res["CSI:TL"]["absorption_efficiency"][i100]))

    # ---- 2. 電子の数と光収率の幅 ---------------------------------------------------- #
    E = res["CSI:TL"]["energy_kev"]
    i60 = int(np.argmin(np.abs(E - 60.0)))
    print("\n2. X 線 1 個あたりの電子の数(Si フォトダイオード、光が全部届く理想)—— %.1f keV" % E[i60])
    for name, label, _ in MATERIALS:
        r = res[name]
        if name == "GD2O2S:TB":
            print("   %-7s (光収率の一次文献が無い —— 描かない)" % label)
            continue
        rng = r["electrons_light_yield_range"]
        extra = "" if rng is None else "   幅 %.0f〜%.0f(光収率 %s〜%s)" % (
            rng[0][i60], rng[1][i60], *("{:,.0f}".format(v) for v in r["light_yield_range_photons_per_mev"]))
        print("   %-7s %6.0f 電子%s" % (label, r["electrons"][i60], extra))
        if rng is not None:
            y = r["light_yield_photons_per_mev"]
            lo, hi = r["light_yield_range_photons_per_mev"]
            np.testing.assert_allclose(rng[0], r["electrons"] * lo / y, rtol=1e-12)
            np.testing.assert_allclose(rng[1], r["electrons"] * hi / y, rtol=1e-12)
    ratio = res["CSI:TL"]["electrons"][i60] / res["BI4GE3O12"]["electrons"][i60]
    ia = int(np.argmin(np.abs(E - 95.0)))
    print("   BGO は 95 keV(Bi の K 端の上)で CsI:Tl の %.2f 倍を止めるのに、電子は %.2f 倍"
          % (res["BI4GE3O12"]["absorption_efficiency"][ia] / res["CSI:TL"]["absorption_efficiency"][ia],
             res["BI4GE3O12"]["electrons"][ia] / res["CSI:TL"]["electrons"][ia]))
    print("   (K 蛍光の逃げを入れない模型なので、K 端の直上では高 Z の BGO に甘い —— Bi の Kα 約 77 keV が逃げる分を"
          "数えれば、BGO の電子はさらに少ない)")
    assert res["BI4GE3O12"]["absorption_efficiency"][ia] > res["CSI:TL"]["absorption_efficiency"][ia]
    assert res["BI4GE3O12"]["electrons"][ia] < res["CSI:TL"]["electrons"][ia]
    cd = res["CDWO4"]
    spread = (cd["light_yield_range_photons_per_mev"][1] - cd["light_yield_range_photons_per_mev"][0]) \
        / cd["light_yield_photons_per_mev"]
    print("   CdWO4 は光収率の幅だけで電子の数が %.0f %% 動く(%s)" % (100 * spread, cd["sources"]
                                                               ["light_yield_range_photons_per_mev"]))
    out["csi_over_bgo_60kev"] = float(ratio)

    # ---- 3. 発光の形と重なり ------------------------------------------------------ #
    qe = _qe_curve()
    print("\n3. 光が電子になる割合 Q̄ = ∫S·QE —— 発光の形(材料表の成分)と、極大の 1 本の線で近似したとき")
    over = {}
    for name, label, _ in MATERIALS:
        r = res[name]
        line = float(np.interp(r["emission_peak_nm"], qe[:, 0], qe[:, 1]))
        over[name] = (r["overlap"], line)
        print("   %-7s Q̄ = %.3f   線で近似 %.3f(%+.1f %%)   %s" % (label, r["overlap"], line,
                                                             100 * (line / r["overlap"] - 1), r["emission_model"][:60]))
    assert over["BI4GE3O12"][1] > over["BI4GE3O12"][0] and over["CDWO4"][1] > over["CDWO4"][0]
    gos = res["GD2O2S:TB"]
    want = sum(c["weight"] * float(np.interp(c["center_nm"], qe[:, 0], qe[:, 1])) for c in gos["emission_components"])
    assert abs(gos["overlap"] - want) < 1e-12
    lso_thick = L.scintillator_sensor_qe("LSO", T_MM, E_LO, E_HI, N_E, emission_geometry="thick_crystal_transmission")
    print("   LSO の厚い結晶(自己吸収で極大 453 nm): Q̄ = %.3f(表面 %.3f)" % (lso_thick["overlap"],
                                                                   res["LU2SIO5:CE"]["overlap"]))
    assert lso_thick["overlap"] > res["LU2SIO5:CE"]["overlap"]
    out["bgo_line_over_band"] = over["BI4GE3O12"][1] / over["BI4GE3O12"][0] - 1.0

    if figs.enabled():
        _figures(res, jumps, qe, lso_thick)
    assert not figs.errors(), figs.errors()
    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  scintillator_sensor_tour  (%.3f s)" % out["elapsed_s"])
    return out


# --------------------------------------------------------------------------- #
# 図(matplotlib で描いて examplefig に渡す。FULLSEYE_FIGURE_DIR があるときだけ)        #
# --------------------------------------------------------------------------- #
def _setup_matplotlib():
    """matplotlib と日本語の書体を用意する。無ければ None(図だけ飛ばし、数値の検査は済んでいる)。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib import font_manager
    except ImportError:
        print("[skip] 図: matplotlib が無い")
        return None
    import annotate
    for path in annotate.FONT_CANDIDATES:
        if os.path.isfile(path) and "DejaVu" not in path:
            font_manager.fontManager.addfont(path)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=path).get_name()
            plt.rcParams["axes.unicode_minus"] = False
            return plt
    print("[skip] 図: 日本語の書体が見つからない(annotate.FONT_CANDIDATES)")
    return None


def _to_rgb(fig):
    fig.canvas.draw()
    rgb = np.asarray(fig.canvas.buffer_rgba())[:, :, :3].copy()
    import matplotlib.pyplot as plt
    plt.close(fig)
    return rgb


def _figures(res, jumps, qe, lso_thick):
    plt = _setup_matplotlib()
    if plt is None:
        return
    E = res["CSI:TL"]["energy_kev"]

    # 図 1: 吸収効率と K 端 -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10.5, 5.6), dpi=110)
    for (name, label, _), c in zip(MATERIALS, COLOURS):
        ax.plot(E, res[name]["absorption_efficiency"], color=c, lw=2, label=label)
    seen = set()
    saturated = sorted({(sym, ek) for _, sym, ek, before, _ in jumps if before > 0.995}, key=lambda x: x[1])
    for label, sym, ek, before, after in jumps:
        if before > 0.995:                 # 手前で止め切っている端(跳びが見えない)は印を付けない
            continue
        c = COLOURS[[m[1] for m in MATERIALS].index(label)]
        ax.plot([ek, ek], [before, after], "o", color=c, ms=4)
        if sym not in seen:
            ax.axvline(ek, color="0.55", lw=0.8, ls=":", zorder=0)
            ax.text(ek, 1.035, "%s K\n%.1f" % (sym, ek), ha="center", va="bottom", fontsize=8, color="0.3")
            seen.add(sym)
    gd = [j for j in jumps if j[1] == "Gd"][0]
    ax.annotate("Gd の K 端(%.1f keV)を越えると\nGOS:Tb の吸収 %.2f → %.2f" % (gd[2], gd[3], gd[4]),
                xy=(gd[2], 0.5 * (gd[3] + gd[4])), xytext=(13.0, 0.55), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="0.3"), bbox=dict(boxstyle="round", fc="white", ec="0.7"))
    ax.text(13.0, 0.30, "%s の K 端は、厚さ %.1f mm だと\n端の手前でも止め切っているので跳びが見えない"
            % (" / ".join("%s %.1f keV" % s for s in saturated), T_MM), fontsize=8, color="0.35")
    ax.semilogx()          # x を対数に
    ax.set_xlim(E[0], E[-1])
    ax.set_ylim(0, 1.13)
    ax.set_xticks([10, 20, 30, 50, 70, 100, 150])
    ax.set_xticklabels(["10", "20", "30", "50", "70", "100", "150"])
    ax.set_xlabel("X 線のエネルギー [keV](対数)")
    ax.set_ylabel("吸収効率 1 − exp(−μt)")
    ax.set_title("厚さ %.1f mm のシンチレータが X 線を止める割合 —— 重い元素の K 端で跳ぶ" % T_MM, fontsize=11)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=8, loc="lower left", ncol=2)
    fig.tight_layout()
    figs.save("absorption_k_edges", _to_rgb(fig),
              caption="7 種のシンチレータ(厚さ %.1f mm)の吸収効率。μ/ρ は NIST SRD 126 の表と材料の密度(付活剤は無視)。"
                      "点線と上の数字は K 吸収端 [keV]、端の上の 2 つの点は直前と直後の値(op を端の ±0.01 %% で呼んで測った値)。"
                      "Gd の K 端で GOS:Tb は %.2f → %.2f。100 keV を超えると Bi・W・Lu を含む結晶が CsI:Tl を大きく上回る。"
                      % (T_MM, gd[3], gd[4]))

    # 図 2: 電子の数(光収率の幅を帯で) --------------------------------------------------
    fig, ax = plt.subplots(figsize=(10.5, 5.6), dpi=110)
    for (name, label, _), c in zip(MATERIALS, COLOURS):
        if name == "GD2O2S:TB":
            continue
        r = res[name]
        ax.plot(E, r["electrons"], color=c, lw=2, label="%s(光収率 %s)" % (label, "{:,.0f}".format(
            r["light_yield_photons_per_mev"])))
        if r["electrons_light_yield_range"] is not None:
            lo, hi = r["electrons_light_yield_range"]
            y0, y1 = r["light_yield_range_photons_per_mev"]
            ax.fill_between(E, lo, hi, color=c, alpha=0.25, lw=0,
                            label="%s の光収率の幅 %s〜%s" % (label, "{:,.0f}".format(y0), "{:,.0f}".format(y1)))
    i_txt = int(np.argmin(np.abs(E - 45.0)))
    cd = res["CDWO4"]
    ax.annotate("CdWO4 の帯 = 絶対測定どうしの違い\n下限 20,000: Si フォトダイオードで絶対測定(1988)\n"
                "上限 ~28,000: 推定(1995)\n※ 7,800〜15,800 という文献値は、減衰 13 µs に対して\n"
                "   整形時間が短いのと、光電子数(phe/MeV)を光子数と\n   混同したもの —— 帯に入れない",
                xy=(E[i_txt], math.sqrt(cd["electrons_light_yield_range"][0][i_txt] * cd["electrons"][i_txt])), xytext=(10.6, 1050),
                fontsize=8, arrowprops=dict(arrowstyle="->", color="0.3"),
                bbox=dict(boxstyle="round", fc="white", ec="0.7"))
    ax.set_ylim(40, 5000)
    ax.loglog()            # 両軸を対数に(op 名と同じ綴りの文字列を書かない —— 例の索引が op の呼び出しと誤認する)
    ax.set_xlim(E[0], E[-1])
    ax.set_xticks([10, 20, 30, 50, 70, 100, 150])
    ax.set_xticklabels(["10", "20", "30", "50", "70", "100", "150"])
    ax.set_xlabel("X 線のエネルギー [keV](対数)")
    ax.set_ylabel("電子の数 / X 線 1 個(対数)")
    ax.set_title("X 線 1 個 → Si フォトダイオードの電子の数(集光率 1、厚さ %.1f mm)" % T_MM, fontsize=11)
    ax.grid(alpha=0.3, which="both")
    ax.legend(fontsize=7.5, loc="lower right", ncol=2)
    fig.tight_layout()
    figs.save("electrons_per_xray", _to_rgb(fig),
              caption="電子の数 = 吸収効率 × 光収率 × E × 重なり Q̄。帯は材料表の光収率の幅の両端で数えた電子の数"
                      "(電子の数は光収率に比例するので、帯は線と同じ形で上下にずれる)。CdWO4 20,000〜28,000 は絶対測定の"
                      "違い、LYSO 26,000〜27,000 は同じ結晶を APD と PD で測った違い。GOS:Tb は光収率の一次文献が無いので描かない。"
                      "K 蛍光の逃げは入れていないので、K 端の直上では高 Z の材料(Bi の K 端 90.5 keV の上の BGO など)の"
                      "電子の数が大きめに出る(偏りの向きは BGO に甘い側)。")

    # 図 3: 発光スペクトルと Si の QE -----------------------------------------------------
    fig, ax = plt.subplots(figsize=(10.5, 5.6), dpi=110)
    ax2 = ax.twinx()
    ax2.plot(qe[:, 0], qe[:, 1], color="k", lw=2.5, label="Si フォトダイオードの QE(右の軸)")
    ax2.set_ylim(0, 1.0)
    ax2.set_ylabel("QE")
    for (name, label, _), c in zip(MATERIALS, COLOURS):
        r = res[name]
        line = float(np.interp(r["emission_peak_nm"], qe[:, 0], qe[:, 1]))
        tag = r"%s $\bar{Q}$ %.3f(線なら %.3f)" % (label, r["overlap"], line)
        if r["emission"] is not None:
            lam, s = r["emission"][:, 0], r["emission"][:, 1]
            ax.plot(lam, s / s.max(), color=c, lw=2, label=tag)
        elif r["emission_components"] is not None:            # 線の束(GOS:Tb)
            ws = np.array([x["weight"] for x in r["emission_components"]])
            for k, x in enumerate(r["emission_components"]):
                ax.plot([x["center_nm"]] * 2, [0, x["weight"] / ws.max()], color=c, lw=3,
                        label=tag + "(Tb³⁺ の線の束)" if k == 0 else None)
        else:                                                 # 幅が未確認: 極大の 1 本の線
            ax.plot([r["emission_peak_nm"]] * 2, [0, 1.0], color=c, lw=1.5, ls="--",
                    label=tag.split("(")[0] + "(幅が未確認 → 極大の線)")
    lam, s = lso_thick["emission"][:, 0], lso_thick["emission"][:, 1]
    ax.plot(lam, s / s.max(), color=COLOURS[3], lw=1.6, ls=":",
            label=r"LSO 厚い結晶を通った光 $\bar{Q}$ %.3f(中心 453 nm)" % lso_thick["overlap"])
    ax.set_xlim(330, 760)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("波長 [nm]")
    ax.set_ylabel("発光(極大で 1 に揃えた形)")
    ax.set_title(r"発光の形と Si の QE —— 山頂の近くでは、帯を線で近似すると $\bar{Q}$ を大きく見積もる", fontsize=11)
    ax.grid(alpha=0.3)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper right", ncol=1, framealpha=0.9)
    fig.tight_layout()
    figs.save("emission_and_qe", _to_rgb(fig),
              caption="材料表の発光の成分(エネルギー軸のガウスをヤコビアン hc/λ² で波長へ移したもの。幅は一次文献の図から"
                      "読んだ値)と Si フォトダイオードの QE。GOS:Tb は Tb³⁺ の線の束(高さは積分の重み、Q̄ = Σ wᵢ·QE(λᵢ))、"
                      "CsI:Tl と NaI:Tl は幅を確かめられなかったので極大の 1 本の線(破線)。LYSO の 2 帯の強度比は 1:1 の仮定。"
                      "LSO は厚い結晶を通ると自己吸収で発光が長波長へ動く(点線)。成分の中心はエネルギー軸の中心なので、"
                      "波長軸の山はヤコビアンの分だけ数 nm 短波長に見える(BGO は中心 480 nm で山 468 nm)。")


if __name__ == "__main__":
    run()
