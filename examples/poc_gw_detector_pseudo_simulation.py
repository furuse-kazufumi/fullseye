# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 重力波望遠鏡の擬似シミュレーション —— 共振器の式・量子雑音の予算・整合フィルタを閉形式で繋ぎ、
GW150914 の実データ(GWOSC)と公表値で採点する。

【問い】km 級の Michelson 干渉計が 1e-21 のひずみを読む仕組みは、どこまで**閉じた式**で再現できるか。
検査装置の干渉計(エタロン・レーザー共振器・白色干渉・振動計)と同じ式なので、再現できた分だけ
Fullseye の設計規則になる。4 章:

  1. **腕共振器**(aLIGO の公表設計値 L 3994.5 m / T_ITM 1.4 % / T_ETM 5 ppm): フィネス・極・伝達関数・
     Pound-Drever-Hall 誤差信号。門: F ≈ 445(440〜450)、極 ≈ 42 Hz(41〜43)、PDH の傾きは Black 2001。
  2. **量子雑音の予算**(Kimble ら 2001 の通常干渉計): 散射 × 輻射圧 = SQL⁴/4 の恒等式、総和は SQL に
     K = 1 で触れる。**第二実装** = gwinc 0.6.2(信号再利用鏡を外した aLIGO)の 8 周波数の値と比 0.85〜1.15。
     公開設計感度曲線(LIGO-T1800044)との比は**報告**(信号再利用と熱雑音を含むので形が違う)。
  3. **実データ**(環境変数 ``FULLSEYE_GWOSC_DATA`` に GWOSC の GW150914 32 s 4 kHz の HDF5 2 本・NR 波形・
     PRL 図 1 の公表曲線・設計曲線、sha256 固定): Welch → 白色化 → 35〜350 Hz →
     **PRL 116, 061102 図 1 の公表曲線と相関 ≥ 0.9**、NR 波形の整合フィルタで **H1 SNR 17〜22 / L1 11〜15 /
     ネットワーク 22〜26**(公表 ≈ 20 / 13 / 24)、**L1 が 6〜8 ms 先**(公表 6.9 +0.5/−0.4 ms)、ニュートン近似の
     チャープは NR より小さい SNR(合体・リングダウンが無い)。周波数の軌跡からチャープ質量(報告と緩い門)。
     無ければ「未配置」と明示して飛ばす(CI は合成と閉形式だけ、図なしで数秒)。
  4. **Fullseye への持ち帰り**: 1/f² の色つき雑音(振動計・AE の典型)に埋めた既知の波形を、白色化 + 整合
     フィルタは最適 SNR どおりに拾う。素の相互相関と比べると、**狭帯域のトーンでは差が無く**(雑音の色を
     跨がない)、**広帯域のチャープ・減衰振動では半分**になる —— 白色化が効くのは波形が雑音の色を跨ぐとき。

【外部真値】GWOSC(CC BY 4.0、gwosc.org)、Abbott ら PRL 116, 061102 (2016) 図 1 の公表曲線、LIGO-T1800044
(aLIGO 設計感度)、gwinc 0.6.2(OSS、第二実装)。**データは repo に入れない**(環境変数で場所を渡す)。
【学習した数】0。【較正】0。

参考: Kimble, Levin, Matsko, Thorne & Vyatchanin, *Phys. Rev. D* 65, 022002 (2001); E. D. Black, *Am. J. Phys.* 69,
79 (2001); Abbott ら, *Phys. Rev. Lett.* 116, 061102 (2016); Aasi ら, *Class. Quantum Grav.* 32, 074001 (2015);
M. Maggiore, *Gravitational Waves Vol. 1* (2008); P. R. Saulson, *Fundamentals of Interferometric GW Detectors* (1994).
"""
from __future__ import annotations

import hashlib
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import dsp  # noqa: E402
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

L = fs.ledger

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
DATA = os.environ.get("FULLSEYE_GWOSC_DATA", "").strip()
FS_HZ = 4096.0
T0 = 1126259447            # 32 s ファイルの GPS 開始
GPS_EVENT = 1126259462.4   # GWTC-1 の GW150914

#: aLIGO の公表設計値(Aasi ら 2015 表 1)
ARM_L = 3994.5
T_ITM, T_ETM = 0.014, 5e-6
MASS_KG = 40.0
WAVELENGTH_NM = 1064.0

#: 第二実装 gwinc 0.6.2: ``load_budget("aLIGO")`` で ``Optics.SRM.Transmittance = 1``(信号再利用鏡を外す)、
#: 入射光量は ``Laser.Power(125 W) × 2 / PRM.T(0.03) × 0.5 = 4166.7 W``、質量 39.6 kg、L 3995 m、T_ITM 0.014。
#: QuantumVacuum の ASD [1/√Hz](2026-10-14 実行、scratch の venv)。
GWINC_NOSRM = {20: 6.002e-23, 50: 6.996e-24, 100: 2.026e-24, 200: 3.291e-24,
               500: 8.058e-24, 1000: 1.629e-23, 2000: 3.233e-23, 4000: 6.419e-23}
GWINC_PBS_W, GWINC_MASS_KG, GWINC_L = 4166.6667, 39.6, 3995.0

#: 実データ(環境変数の dir に置く)。sha256 は取得時に固定。
FILES = {
    "H1": ("H-H1_GWOSC_4KHZ_R1-1126259447-32.hdf5", "c5ea87beced5094b56b4d694f3a36e6d59f74d3a46e546b980a6a199d1f252a9"),
    "L1": ("L-L1_GWOSC_4KHZ_R1-1126259447-32.hdf5", "9d65bde82f7ec035bea4c02228bce4acb3dcaae774c047edce71ef2ad64f1cc4"),
    "NR": ("GW150914_4_NR_waveform.txt", "ed49c3e83f90e70ac85386f183031b7de3d3d6aa78e75a7d284e5a53a5cc0b76"),
    "design": ("aLIGODesign.txt", "b90556e379ddb19e8784d3e3a1a45e7899a8337a9e8f10c7fdb644b93b64ec87"),
    "fig1H": ("fig1-observed-H.txt", "3ce5475160fd6b39c41205c2055bfaf4e507981721a2eb4c5df0c99e2fa48d94"),
    "fig1L": ("fig1-observed-L.txt", "dc41302512f3e28336680030a255cc1f4fb3ec43ea5267cc044c9015051ecd85"),
}

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------- #
#  1. 腕共振器                                                                   #
# ---------------------------------------------------------------------------- #
def chapter_cavity():
    print("\n== 1. 腕共振器(aLIGO の公表設計値) ==")
    r = L.fabry_perot_response(ARM_L, WAVELENGTH_NM, itm_transmittance=T_ITM, etm_transmittance=T_ETM)
    print("   FSR %.1f Hz / フィネス %.1f / 線幅 %.2f Hz / 極 %.2f Hz / 循環光量 %.0f 倍 / 蓄積時間 %.2f ms"
          % (r["fsr_hz"], r["finesse"], r["linewidth_hz"], r["pole_hz"], r["power_gain"], 1e3 * r["storage_time_s"]))
    NUMBERS.update(finesse=r["finesse"], pole_hz=r["pole_hz"], fsr_hz=r["fsr_hz"], power_gain=r["power_gain"])
    gate("フィネス 440〜450", 440.0 < r["finesse"] < 450.0, "%.1f" % r["finesse"])
    gate("共振器の極 41〜43 Hz", 41.0 < r["pole_hz"] < 43.0, "%.2f Hz" % r["pole_hz"])
    tf = L.cavity_strain_transfer(ARM_L, r["finesse"], f_min_hz=1.0, f_max_hz=1e5, n_points=400)
    i = int(np.argmin(np.abs(tf[:, 0] - r["pole_hz"])))
    dc = 2 * r["finesse"] / np.pi
    print("   伝達関数: DC 利得 %.1f(2F/π)、極で %.3f 倍、FSR で %.1e" % (dc, tf[i, 1] / dc, tf[-1, 1] / dc))
    gate("伝達関数は極で 1/√2(3 % 以内)", abs(tf[i, 1] / dc - 1 / np.sqrt(2)) < 0.03)
    e = L.pdh_error_signal(ARM_L, itm_transmittance=T_ITM, etm_transmittance=T_ITM, mod_freq_hz=9.1e6,
                           mod_depth=0.5, power_w=1.0, span_linewidths=3.0, n_points=1201)
    k = 600
    slope = (e[k + 1, 1] - e[k - 1, 1]) / (e[k + 1, 0] - e[k - 1, 0])
    from scipy.special import j0, j1
    sym = L.fabry_perot_response(ARM_L, WAVELENGTH_NM, itm_transmittance=T_ITM, etm_transmittance=T_ITM)
    black = -8.0 * np.sqrt(j0(0.5) ** 2 * j1(0.5) ** 2) / sym["linewidth_hz"]
    print("   PDH(対称共振器、9.1 MHz 変調): 共振近傍の傾き %.3e W/Hz、Black 2001 式 15 は %.3e(比 %.4f)"
          % (slope, black, slope / black))
    gate("PDH の傾き = Black 式 15(1 % 以内)", abs(slope / black - 1) < 0.01)
    NUMBERS["pdh_slope_ratio"] = slope / black
    # 単純 Michelson(共振器なし)の散射雑音限界: 腕 3994.5 m・5.2 kW で (1/2L)√(ħcλ/πP)。腕共振器の
    # 2F/π ≈ 284 倍の利得を掛けると量子雑音の予算の散射雑音(第 2 章)の桁になる。
    mi = L.michelson_dc_readout(5200.0, ARM_L, WAVELENGTH_NM, dc_offset_rad=0.01)
    print("   単純 Michelson(5.2 kW、オフセット 0.01 rad): 反対称ポート %.3f W、散射雑音限界 %.2e /√Hz、"
          "腕共振器の利得 %.0f 倍で %.2e /√Hz" % (mi["p_out_w"], mi["h_shot_limit_per_rthz"], dc, mi["h_shot_limit_per_rthz"] / dc))
    NUMBERS["michelson_shot_limit"] = mi["h_shot_limit_per_rthz"]
    gate("散射雑音限界はオフセットに依らない(0.01 rad と 0.3 rad で 1 % 以内)",
         abs(L.michelson_dc_readout(5200.0, ARM_L, WAVELENGTH_NM, dc_offset_rad=0.3)["h_shot_limit_per_rthz"]
             / mi["h_shot_limit_per_rthz"] - 1) < 0.01)
    return r, tf, e


# ---------------------------------------------------------------------------- #
#  2. 量子雑音の予算                                                             #
# ---------------------------------------------------------------------------- #
def chapter_quantum(design=None):
    print("\n== 2. 量子雑音の予算(Kimble ら 2001 の通常干渉計)==")
    q = L.quantum_noise_budget(GWINC_PBS_W, GWINC_MASS_KG, GWINC_L, WAVELENGTH_NM, itm_transmittance=T_ITM,
                               f_min_hz=10.0, f_max_hz=5000.0, n_points=300)
    prod = q["shot"] ** 2 * q["radiation_pressure"] ** 2 / (q["sql"] ** 4 / 4)
    print("   γ/2π %.2f Hz、I_SQL %.0f W、I₀/I_SQL %.1f、総和が SQL に触れる周波数 %s"
          % (q["pole_hz"], q["i_sql_w"], q["power_ratio"],
             "%.1f Hz" % q["f_sql_touch_hz"] if q["f_sql_touch_hz"] else "無し"))
    gate("散射 × 輻射圧 = SQL⁴/4(1e-10)", bool(np.allclose(prod, 1.0, rtol=1e-10)))
    gate("総和 ≥ SQL", bool((q["total"] >= q["sql"] * (1 - 1e-12)).all()))
    ratios = []
    print("   f [Hz]   自前 [1/√Hz]   gwinc(SRM 無し)   比    設計曲線(T1800044)   比")
    for f0, g in GWINC_NOSRM.items():
        mine = float(np.interp(f0, q["f_hz"], q["total"]))
        ratios.append(g / mine)
        d = float(np.interp(f0, design[:, 0], design[:, 1])) if design is not None else float("nan")
        print("   %5d   %.3e      %.3e        %.3f   %s" % (f0, mine, g, g / mine,
              ("%.3e            %.2f" % (d, d / mine)) if design is not None else "(未配置)"))
    NUMBERS["gwinc_ratio_min"], NUMBERS["gwinc_ratio_max"] = float(min(ratios)), float(max(ratios))
    gate("第二実装 gwinc と 8 周波数で比 0.85〜1.15", 0.85 < min(ratios) and max(ratios) < 1.15,
         "%.3f〜%.3f" % (min(ratios), max(ratios)))
    # 光量を振る: 100 Hz の総和が最小になる光量と、触れる周波数の動き
    powers = np.logspace(2, 5, 13)
    best = None
    for P in powers:
        qq = L.quantum_noise_budget(P, GWINC_MASS_KG, GWINC_L, WAVELENGTH_NM, itm_transmittance=T_ITM,
                                    f_min_hz=100.0, f_max_hz=200.0, n_points=2)
        if best is None or qq["total"][0] < best[1]:
            best = (P, float(qq["total"][0]), qq["f_sql_touch_hz"])
    q100 = L.quantum_noise_budget(best[0], GWINC_MASS_KG, GWINC_L, WAVELENGTH_NM, itm_transmittance=T_ITM,
                                  f_min_hz=10.0, f_max_hz=5000.0, n_points=300)
    print("   100 Hz の量子雑音が最小になる入射光量 ≈ %.0f W(総和 %.2e、SQL に触れる周波数 %s)"
          % (best[0], best[1], "%.0f Hz" % q100["f_sql_touch_hz"] if q100["f_sql_touch_hz"] else "無し"))
    NUMBERS["best_power_100hz_w"] = float(best[0])
    sql100 = float(np.interp(100.0, q["f_hz"], q["sql"]))
    gate("最適光量で 100 Hz の総和は SQL の 1.2 倍以内", best[1] < 1.2 * sql100, "%.3f 倍" % (best[1] / sql100))
    return q


# ---------------------------------------------------------------------------- #
#  3. 実データ(GW150914)                                                         #
# ---------------------------------------------------------------------------- #
def load_data():
    if not DATA:
        return None
    if not os.path.isdir(DATA):
        raise FileNotFoundError("FULLSEYE_GWOSC_DATA=%r is not a directory" % DATA)
    got = {}
    for key, (name, sha) in FILES.items():
        p = os.path.join(DATA, name)
        if not os.path.isfile(p):
            raise FileNotFoundError("%s: missing %s (GWOSC / LIGO DCC の公開ファイル)" % (DATA, name))
        if _sha256(p) != sha:
            raise ValueError("%s: sha256 mismatch (配布物が変わった、または破損)" % name)
        got[key] = p
    try:
        import h5py
    except ImportError:
        raise RuntimeError("FULLSEYE_GWOSC_DATA は設定されているが h5py が無い(pip install h5py)")
    strain = {}
    for det in ("H1", "L1"):
        with h5py.File(got[det], "r") as f:
            s = f["strain/Strain"][:]
            assert int(f["strain/Strain"].attrs["Xstart"]) == T0
            assert abs(float(f["strain/Strain"].attrs["Xspacing"]) - 1.0 / FS_HZ) < 1e-15
        strain[det] = np.asarray(s, dtype=np.float64)
    return {"strain": strain, "nr": np.loadtxt(got["NR"]), "design": np.loadtxt(got["design"]),
            "fig1": {"H1": np.loadtxt(got["fig1H"]), "L1": np.loadtxt(got["fig1L"])}}


def chapter_real(data):
    print("\n== 3. 実データ: GW150914(GWOSC、H1 / L1、32 s、4096 Hz)==")
    if data is None:
        print("   未配置: FULLSEYE_GWOSC_DATA が未設定。gwosc.org の GW150914(GWTC-1 v3)の 32 s 4 kHz HDF5 2 本、"
              "NR 波形 GW150914_4_NR_waveform.txt、PRL 図 1 の fig1-observed-{H,L}.txt、LIGO-T1800044 の "
              "aLIGODesign.txt を 1 つの dir に置き、環境変数で渡す。実データ門は未実行。")
        return None
    strain, nr, design, fig1 = data["strain"], data["nr"], data["design"], data["fig1"]
    t = np.arange(strain["H1"].size) / FS_HZ + T0
    psd = {d: L.psd_welch(strain[d], FS_HZ, 4.0) for d in strain}
    print("   O1 の実測 ASD と設計曲線(T1800044)の比:")
    worse = True
    for d in ("H1", "L1"):
        row = []
        for f0 in (50, 100, 200, 500, 1000):
            m = float(np.sqrt(np.interp(f0, psd[d][:, 0], psd[d][:, 1])))
            dd = float(np.interp(f0, design[:, 0], design[:, 1]))
            row.append("%d Hz %.1f×" % (f0, m / dd))
            worse &= m >= dd
            if f0 == 100:
                NUMBERS["o1_over_design_100hz_" + d] = m / dd
        print("   %s: %s" % (d, "  ".join(row)))
    gate("O1 の実測は 5 周波数すべてで設計曲線より上(2015 年の装置は設計未達)", worse)
    # 白色化 + 帯域通過 → PRL 図 1
    white, wb = {}, {}
    for d in ("H1", "L1"):
        white[d] = L.whiten_by_psd(strain[d], psd[d], FS_HZ)
        wb[d] = dsp.bandpass(white[d], FS_HZ, 35.0, 350.0)
        core = wb[d][int(2 * FS_HZ):-int(2 * FS_HZ)]
        fig = fig1[d]
        tt = fig[:, 0] + 1126259462.0
        c = float(np.corrcoef(np.interp(tt, t, wb[d]), fig[:, 1])[0, 1])
        c_raw = float(np.corrcoef(np.interp(tt, t, dsp.bandpass(strain[d], FS_HZ, 35.0, 350.0)), fig[:, 1])[0, 1])
        NUMBERS["fig1_corr_" + d] = c
        print("   %s: 白色化 + 35〜350 Hz の標準偏差 %.3f(白色なら √(315/2048) = 0.392)、PRL 図 1 との相関 %.3f"
              "(白色化なしの帯域通過だけなら %.3f)" % (d, core.std(), c, c_raw))
        gate("%s: PRL 図 1 の公表曲線と相関 ≥ 0.9" % d, c >= 0.9, "%.3f" % c)
        gate("%s: 白色化が効いている(帯域内の標準偏差 0.25〜0.6)" % d, 0.25 < core.std() < 0.6)
    # 整合フィルタ: NR 波形とニュートン近似
    h_nr = nr[:, 1]
    h_newt = L.chirp_newtonian(36.0 * 1.09, 29.0 * 1.09, FS_HZ, 1.0, f_low_hz=20.0)
    snr, peaks = {}, {}
    for d in ("H1", "L1"):
        for label, h in (("NR", h_nr), ("Newton", h_newt)):
            s = L.matched_filter_snr(strain[d], h, psd[d], FS_HZ, f_low_hz=20.0, taper_s=2.0)
            snr[(d, label)] = s
            i = int(np.argmax(s))
            peaks[(d, label)] = (float(s[i]), float(t[i]))
            print("   %s %-6s: 最大 SNR %.2f(GPS %.4f、事象 %.1f)" % (d, label, s[i], t[i], GPS_EVENT))
    NUMBERS.update(snr_h1_nr=peaks[("H1", "NR")][0], snr_l1_nr=peaks[("L1", "NR")][0],
                   snr_h1_newton=peaks[("H1", "Newton")][0], snr_l1_newton=peaks[("L1", "Newton")][0])
    gate("H1 の SNR(NR)17〜22(公表 ≈ 20)", 17.0 <= peaks[("H1", "NR")][0] <= 22.0)
    gate("L1 の SNR(NR)11〜15(公表 ≈ 13)", 11.0 <= peaks[("L1", "NR")][0] <= 15.0)
    co = L.coincidence_delay(snr[("H1", "NR")], snr[("L1", "NR")], FS_HZ, max_delay_s=0.010)
    NUMBERS["network_snr"], NUMBERS["delay_l1_minus_h1_ms"] = co["network_snr"], 1e3 * co["delay_s"]
    print("   ネットワーク SNR %.2f(公表 24)、L1 − H1 の到達時間差 %.2f ms(公表 −6.9 +0.5/−0.4 ms、光の走行 10 ms が上限)"
          % (co["network_snr"], 1e3 * co["delay_s"]))
    gate("ネットワーク SNR 22〜26", 22.0 <= co["network_snr"] <= 26.0)
    gate("L1 が 6〜8 ms 先に受けた", -8.0e-3 <= co["delay_s"] <= -6.0e-3)
    gate("ニュートン近似の SNR は NR より小さく、それでも 5 以上(合体・リングダウンが無い分だけ損)",
         peaks[("H1", "Newton")][0] < peaks[("H1", "NR")][0] and peaks[("H1", "Newton")][0] >= 5.0)
    for d in ("H1", "L1"):
        for label in ("NR", "Newton"):
            ev = abs(peaks[(d, label)][1] - GPS_EVENT)
            gate("%s %s の山は事象時刻の 0.25 s 以内" % (d, label), ev < 0.25, "%.3f s" % ev)
    # チャープ質量: NR 波形の零交差の軌跡(30〜75 Hz)と、白色化した実データのスペクトログラムの尾根
    tt, h = nr[:, 0], nr[:, 1]
    zc = np.where(np.diff(np.sign(h)) != 0)[0]
    tz = tt[zc] - h[zc] * (tt[zc + 1] - tt[zc]) / (h[zc + 1] - h[zc])
    f_inst = 1.0 / (2.0 * np.diff(tz))
    tm = 0.5 * (tz[:-1] + tz[1:])
    sel = (f_inst > 30) & (f_inst < 75) & (tm < -0.01)
    mc_nr = L.chirp_mass_from_track(np.stack([tm[sel], f_inst[sel]], axis=1))
    print("   NR 波形の零交差(30〜75 Hz、%d 点)からニュートン式 1 でチャープ質量 %.1f M☉(検出器系の公表値は"
          " ≈ 31 M☉ = 28.6 × (1+z) —— 40 Hz で周波数が 1 周期に 7 %% 上がる系では式 1 が高めに出る)"
          % (sel.sum(), mc_nr["chirp_mass_msun"]))
    NUMBERS["chirp_mass_nr_track"] = mc_nr["chirp_mass_msun"]
    gate("NR 軌跡のチャープ質量 25〜45 M☉(桁の門)", 25.0 < mc_nr["chirp_mass_msun"] < 45.0)
    for d in ("H1", "L1"):
        i0 = int((GPS_EVENT - 0.25 - T0) * FS_HZ)
        i1 = int((GPS_EVENT + 0.05 - T0) * FS_HZ)
        freqs, times, S = dsp.spectrogram(wb[d][i0:i1], FS_HZ, win=256, hop=16)
        band = (freqs > 30) & (freqs < 300)
        ridge_f = freqs[band][np.argmax(S[band], axis=0)]
        ridge_p = S[band].max(axis=0)
        tr = times + (i0 / FS_HZ + T0 - GPS_EVENT)
        sel = (tr > -0.12) & (tr < -0.01) & (ridge_p > 2.5 * np.median(ridge_p))
        if sel.sum() >= 3:
            try:
                r = L.chirp_mass_from_track(np.stack([tr[sel], ridge_f[sel]], axis=1))
                rel = abs(r["chirp_mass_msun"] - mc_nr["chirp_mass_msun"]) / mc_nr["chirp_mass_msun"]
                print("   %s の白色化データの尾根(%d 枠)からのチャープ質量 %.1f M☉(NR 軌跡との差 %.0f %%)"
                      % (d, sel.sum(), r["chirp_mass_msun"], 100 * rel))
                if d == "H1":
                    NUMBERS["chirp_mass_h1_ridge"] = r["chirp_mass_msun"]
                    gate("H1 の尾根と NR 軌跡のチャープ質量が 20 % 以内", rel < 0.2)
            except ValueError as e:
                print("   %s の尾根: 当てはめ不能(%s)" % (d, e))
        else:
            print("   %s の尾根: 中央値の 2.5 倍を超える枠が %d 枠しかなく当てはめない" % (d, sel.sum()))
    return {"t": t, "wb": wb, "snr": snr, "fig1": fig1, "psd": psd, "design": design}


# ---------------------------------------------------------------------------- #
#  4. Fullseye への持ち帰り: 色つき雑音の中の既知波形                              #
# ---------------------------------------------------------------------------- #
def chapter_industrial():
    print("\n== 4. 持ち帰り: 1/f² の色つき雑音(振動計・AE の典型)に埋めた既知の波形 ==")
    rng = np.random.default_rng(7)
    fs = 20000.0
    n = int(4.0 * fs)
    from scipy import signal as sg
    # 1/f² = 白色雑音の漏れ積分 + 180 Hz の線
    base = sg.lfilter([1.0], [1.0, -0.995], rng.standard_normal(n))
    tt = np.arange(n) / fs
    noise = base + 0.3 * base.std() * np.sin(2 * np.pi * 180.0 * tt)
    psd = L.psd_welch(noise, fs, 0.5)
    m = int(0.008 * fs)
    tb = np.arange(m) / fs
    env = np.exp(-0.5 * ((tb - 0.004) / 0.002) ** 2)
    shapes = {
        "5 kHz のトーン(AE の 1 ヒット)": np.exp(-0.5 * ((tb - 0.004) / 0.0006) ** 2) * np.sin(2 * np.pi * 5000.0 * tb),
        "100 → 4000 Hz のチャープ": env * sg.chirp(tb, 100.0, 0.008, 4000.0),
        "200 Hz の減衰振動(打撃の応答)": np.exp(-tb / 0.003) * np.sin(2 * np.pi * 200.0 * tb),
    }
    target = 12.0
    at = int(1.7 * fs)
    keep = None
    ratios = {}
    for label, burst in shapes.items():
        sigma = L.optimal_snr(burst, psd, fs, f_low_hz=None)
        x = noise.copy()
        x[at:at + m] += burst * (target / sigma)
        s = L.matched_filter_snr(x, burst, psd, fs, f_low_hz=None, taper_s=0.05)
        i = int(np.argmax(s))
        err = i - (at + int(np.argmax(np.abs(burst))))
        corr = np.correlate(x, burst, mode="valid")
        noise_part = np.concatenate([corr[: at - m], corr[at + 2 * m:]])
        plain = float(np.abs(corr[at]) / noise_part.std())
        ratios[label] = plain / float(s[i])
        print("   %-22s 埋めた高さ %.0f → 整合フィルタ %.1f(時刻ずれ %d 標本)、素の相互相関 %.1f(比 %.2f)"
              % (label, target, s[i], err, plain, plain / s[i]))
        gate("%s: 整合フィルタは埋めた時刻(±2 標本)に埋めた高さ(±25 %%)の山" % label.split("(")[0],
             abs(err) <= 2 and abs(s[i] - target) < 0.25 * target)
        if keep is None or "チャープ" in label:
            keep = (s, x, at, label)
    tone, chirp, ring = ratios.values()
    NUMBERS.update(ae_plain_over_mf_tone=tone, ae_plain_over_mf_chirp=chirp, ae_plain_over_mf_ring=ring)
    gate("狭帯域のトーンでは白色化の利得が無い(比 0.8〜1.2)", 0.8 < tone < 1.2, "%.2f" % tone)
    gate("広帯域のチャープと減衰振動では素の相関が 0.65 倍以下", chirp < 0.65 and ring < 0.65, "%.2f / %.2f" % (chirp, ring))
    return keep


# ---------------------------------------------------------------------------- #
#  図                                                                            #
# ---------------------------------------------------------------------------- #
def make_figures(cav, q, real, ind):
    """図。plot_series に対数軸は無いので、対数軸は log10 の値で描き軸名に書く。"""
    lg = np.log10
    r, tf, e = cav
    dc = 2 * r["finesse"] / np.pi
    keep = tf[:, 1] / dc >= 1e-5                       # sinc の零(1e-16)は対数で描けない
    figs.save_plot("cavity_transfer",
                   [("腕共振器 |H(f)| / |H(0)|", lg(tf[keep, 0]), lg(tf[keep, 1] / dc)),
                    ("極 %.1f Hz" % r["pole_hz"], np.array([lg(r["pole_hz"])] * 2), np.array([-5.0, 0.0])),
                    ("FSR %.1f kHz" % (r["fsr_hz"] / 1e3), np.array([lg(r["fsr_hz"])] * 2), np.array([-5.0, 0.0]))],
                   xlabel="log10 周波数 [Hz]", ylabel="log10 正規化した利得",
                   title="aLIGO の腕共振器: フィネス %.0f、極 %.1f Hz、FSR で零" % (r["finesse"], r["pole_hz"]),
                   styles=[None, "dashed", "dotted"], colors=["emphasis", "reference", "reference"], ylim=(-5.0, 0.2),
                   caption="単極 1/√(1+(f/f_p)²) × 往復伝搬の sinc(2πfL/c)。極で 1/√2、FSR = c/2L で零。")
    figs.save_plot("pdh_error_signal", [("PDH 誤差信号", e[:, 0], e[:, 1])],
                   xlabel="離調 [Hz]", ylabel="ε [W]",
                   title="Pound-Drever-Hall 誤差信号(対称共振器、傾きは Black 2001 の %.4f 倍)" % NUMBERS["pdh_slope_ratio"],
                   caption="反対称で共振で零。共振近傍の傾き −8√(P_c P_s)/δν が共振器の長さを合わせる誤差信号になる。")
    def _band(x, y, lo=-26.0, hi=-21.0):
        m = (lg(y) >= lo) & (lg(y) <= hi)
        return lg(x[m]), lg(y[m])

    series = [("散射雑音",) + _band(q["f_hz"], q["shot"]), ("輻射圧雑音",) + _band(q["f_hz"], q["radiation_pressure"]),
              ("標準量子限界",) + _band(q["f_hz"], q["sql"]), ("総和(自前、Kimble 2001)",) + _band(q["f_hz"], q["total"]),
              ("gwinc 0.6.2(SRM 無し)", lg(np.array(list(GWINC_NOSRM.keys()), float)), lg(np.array(list(GWINC_NOSRM.values()))))]
    styles = [None, None, "dashed", None, None]
    kinds = ["line", "line", "line", "line", "scatter"]
    colors = ["neutral", "neutral", "reference", "emphasis", "right"]
    if real is not None:
        d = real["design"]
        sel = (d[:, 0] >= 10.0) & (d[:, 0] <= 5000.0)
        series.append(("aLIGO 設計曲線(T1800044、全雑音)", lg(d[sel, 0]), lg(d[sel, 1])))
        styles.append("dotted")
        kinds.append("line")
        colors.append("wrong")
    figs.save_plot("quantum_noise_budget", series, xlabel="log10 周波数 [Hz]", ylabel="log10 ひずみ ASD [1/√Hz]",
                   title="量子雑音の予算: 散射 × 輻射圧 = SQL²/2、第二実装 gwinc と比 %.2f〜%.2f"
                   % (NUMBERS["gwinc_ratio_min"], NUMBERS["gwinc_ratio_max"]),
                   styles=styles, kinds=kinds, colors=colors, ylim=(-26.0, -21.0),
                   caption="通常干渉計(信号再利用なし)の量子雑音。設計曲線は信号再利用と熱雑音を含むので 20 Hz と 500 Hz 以上で形が違う。")
    frames = []
    powers = np.logspace(2, 5, 16)
    curves = [L.quantum_noise_budget(P, GWINC_MASS_KG, GWINC_L, WAVELENGTH_NM, itm_transmittance=T_ITM,
                                     f_min_hz=10.0, f_max_hz=5000.0, n_points=200) for P in powers]
    lo = min(float(lg(c["shot"]).min()) for c in curves)
    lo = min(lo, min(float(lg(c["radiation_pressure"]).min()) for c in curves))
    hi = max(float(lg(c["total"]).max()) for c in curves)
    for P, qq in zip(powers, curves):
        img = figs.render_plot([("散射", lg(qq["f_hz"]), lg(qq["shot"])), ("輻射圧", lg(qq["f_hz"]), lg(qq["radiation_pressure"])),
                                ("SQL", lg(qq["f_hz"]), lg(qq["sql"])), ("総和", lg(qq["f_hz"]), lg(qq["total"]))],
                               xlabel="log10 周波数 [Hz]", ylabel="log10 ASD [1/√Hz]",
                               title="入射光量 %.0f W(I₀/I_SQL = %.2f)" % (P, qq["power_ratio"]),
                               styles=[None, None, "dashed", None], colors=["neutral", "neutral", "reference", "emphasis"],
                               ylim=(lo - 0.1, hi + 0.1))
        frames.append(np.asarray(img))
    figs.save_gif("power_sweep", frames, fps=2.0,
                  caption="入射光量 100 W → 100 kW: 散射雑音は 1/√P で下がり、輻射圧雑音は √P で上がる。総和は K = 1 の周波数で SQL に触れ、その点が光量とともに高い周波数へ動く。")
    if real is not None:
        t, wb, snr, fig1 = real["t"], real["wb"], real["snr"], real["fig1"]
        series = []
        for d in ("H1", "L1"):
            f = fig1[d]
            f = f[(f[:, 0] >= 0.25) & (f[:, 0] <= 0.45)]
            tt = f[:, 0] + 1126259462.0
            mine = np.interp(tt, t, wb[d])
            off = 0.0 if d == "H1" else -6.0
            series.append(("%s 自前(白色化 + 35〜350 Hz)" % d, f[:, 0], mine / mine.std() + off))
            series.append(("%s PRL 2016 図 1(公表)" % d, f[:, 0], f[:, 1] / f[:, 1].std() + off))
        figs.save_plot("gw150914_whitened_vs_prl", series, xlabel="GPS 1126259462 からの時刻 [s]",
                       ylabel="白色化ひずみ(標準偏差で規格化、L1 は −6 ずらし)",
                       title="GW150914: 自前の白色化 + 帯域通過と PRL 図 1 の相関 H1 %.3f / L1 %.3f"
                       % (NUMBERS["fig1_corr_H1"], NUMBERS["fig1_corr_L1"]),
                       styles=[None, "dashed", None, "dashed"], colors=["emphasis", "reference", "right", "reference"],
                       caption="Welch の PSD で白色化し 35〜350 Hz を通しただけで、公表図 1 の曲線(帯域通過 + 線の除去)と 0.9 以上で重なる。")
        lo, hi = int((GPS_EVENT - 0.15 - T0) * FS_HZ), int((GPS_EVENT + 0.1 - T0) * FS_HZ)
        tt = t[lo:hi] - GPS_EVENT
        figs.save_plot("matched_filter_snr",
                       [("H1 NR 波形", tt, snr[("H1", "NR")][lo:hi]), ("L1 NR 波形", tt, snr[("L1", "NR")][lo:hi]),
                        ("H1 ニュートン近似", tt, snr[("H1", "Newton")][lo:hi]), ("L1 ニュートン近似", tt, snr[("L1", "Newton")][lo:hi])],
                       xlabel="事象時刻からの時間 [s]", ylabel="SNR", styles=[None, None, "dotted", "dotted"],
                       colors=["emphasis", "right", "neutral", "wrong"],
                       title="整合フィルタの SNR: NR 波形 H1 %.1f / L1 %.1f(公表 ≈ 20 / 13)、L1 が %.1f ms 先"
                       % (NUMBERS["snr_h1_nr"], NUMBERS["snr_l1_nr"], -NUMBERS["delay_l1_minus_h1_ms"]),
                       caption="数値相対論の波形は公表どおりの山を立て、ニュートン近似(合体・リングダウン無し)は半分以下。")
    s, x, at, label = ind
    fs = 20000.0
    lo, hi = at - int(0.02 * fs), at + int(0.03 * fs)
    tt = (np.arange(lo, hi) - at) / fs * 1e3
    figs.save_plot("burst_in_coloured_noise",
                   [("観測(1/f² 雑音 + %s)" % label, tt, x[lo:hi] / x.std()), ("整合フィルタの SNR", tt, s[lo:hi])],
                   xlabel="埋めた時刻からの時間 [ms]", ylabel="規格化した振幅 / SNR", colors=["neutral", "emphasis"],
                   title="色つき雑音の中の既知波形: 素の相関 / 整合フィルタ = トーン %.2f、チャープ %.2f、減衰振動 %.2f"
                   % (NUMBERS["ae_plain_over_mf_tone"], NUMBERS["ae_plain_over_mf_chirp"], NUMBERS["ae_plain_over_mf_ring"]),
                   caption="雑音が 1/f² のとき、波形が低周波を含むほど素の相関は損をし、白色化した整合フィルタは最適 SNR どおりに拾う。")


def main():
    t0 = time.time()
    print("PoC 重力波望遠鏡の擬似シミュレーション(予算 %s、実データ %s)" % ("reduced" if REDUCED else "full", "あり" if DATA else "未配置"))
    data = load_data()
    cav = chapter_cavity()
    q = chapter_quantum(data["design"] if data else None)
    real = chapter_real(data)
    ind = chapter_industrial()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(cav, q, real, ind)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
