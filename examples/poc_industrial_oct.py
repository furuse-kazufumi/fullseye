# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 工業用 OCT(光干渉断層)—— 塗装・コート・多層フィルムの層厚と中の欠陥を、1 本の干渉スペクトルの FFT で
深さ方向に見る。実測は公開の自動車塗装の生スペクトル(CC BY 4.0)で、論文の超音波・顕微鏡の値と突き合わせる。

【問い】白色干渉は表面の高さ、クロマティック共焦点は 1 点の距離、分光反射はサブ µm の膜厚を出す。その間 ——
数 µm〜数 mm の**層の並び**(透明なクリア層の下の着色層、基板の上のコンフォーマルコート、フィルムの積層)と、
層の中の空洞・剥離 —— を壊さずに見るのが OCT。新 op 13 本(`octscan`、`opsoptics` の `oct`)で、撮る前の閉形式
(軸分解能・深さ範囲・感度の roll-off・SNR・横分解能と焦点深度)を先に印字し、合成と実測で採点する。7 章:

  0. **撮る前の閉形式**: ``oct_design`` で 840 nm の分光器型(SD)、1310 nm の波長掃引型(SS)、実測の装置。
  1. **実測(主役)**: 自動車塗装の見本 4 枚 + 白 1 枚の生の干渉スペクトル(Liverpool 大のデータ、CC BY 4.0)を
     ``oct_from_spectra`` → ``oct_bscan``(k 線形化・窓・FFT)→ ``oct_bscan_boundaries``(表面)→
     ``oct_bscan_flatten``(表面に沿って平均)→ ``oct_layer_thickness``(群屈折率で厚さ)。論文の表 1 の
     OCT・超音波・顕微鏡の値と突き合わせる。ガラス板の 2 本で軸分解能、白の見本で「散乱で下の面が見えない」、
     透明層の光学厚の深さに水平に出る**自己相関の幽霊**も実データで確かめる。
  2. **多層フィルム(合成)**: PMMA / ポリカーボネート / ポリスチレンの積層(屈折率と分散は材料表 ``materials``)。
     群屈折率で割ると真値、位相屈折率で割ると数 % ずれる。軸分解能・SNR・roll-off が閉形式に合うか。
  3. **処理の段で壊れるもの**: k 線形化なし・線形補間・分散の不一致(と 3 通りの補償)・掃引の非線形。
  4. **鏡像・自己相関・折り返し**: 参照より手前の面、直交の組で鏡像を消す(位相誤差 δ で tan(δ/2) だけ残る)、
     層の光学厚に出る幽霊、深さ範囲の外の折り返し。
  5. **限界**: 薄すぎる層(点像の幅の 1.4 倍より狭いと拒否)と、散乱の強い塗装で下の面が雑音に沈む。
  6. **B スキャン**: 部品の段差を越えるコンフォーマルコートの厚さの地図、空洞と剥離の検出、横分解能と焦点深度、
     点照明とライン照明の焦点の外れ方。

EXTEND: 実機に差し替えるなら ``oct_from_spectra`` に装置の生のスペクトル(A ライン × 画素)と分光器の波長の較正
(画素ごとの波長)を渡し、参照腕だけのスペクトルを測ってあれば ``reference_spectrum`` に(無ければ ``dc="mean"``
か ``"smooth"``)。分散の不一致は ``oct_dispersion_estimate``(鏡で ``"mirror"``、試料で ``"sharpness"``)で
係数を測り、``oct_bscan`` の ``a2``・``a3`` と ``k_center`` に渡す。群屈折率は材料表の名前か、段差の既知の試料で
校正した値を ``oct_layer_thickness`` の ``n_group`` に。★実測の章の屈折率(透明層 1.56・着色層 1.64)は論文が
テラヘルツ帯の別の測定から借りた値で、近赤外の群屈折率ではない —— 厚さの絶対値はその分だけ不確か。
散乱は 1 回散乱(Beer–Lambert)の模型までで、多重散乱による深い所の背景の持ち上がりは入れていない。

【外部真値】Y. Dong ら, Appl. Opt. 55(13) 3695 (2016) の表 1(同じ見本を超音波の膜厚計と光学顕微鏡で測った層厚)と
その生データ(University of Liverpool Research Data Catalogue 126、CC BY 4.0、``data/oct_real/README.md``)。
閉形式: 軸分解能 (2 ln 2/π) λ0²/Δλ と深さ範囲 λ0²/(4δλ)(Drexler & Fujimoto 編 *Optical Coherence Tomography*
2nd ed. 2015、Fercher ら Rep. Prog. Phys. 66, 239, 2003)、roll-off の |sinc|·ガウス(Yun ら Opt. Express 11,
3598, 2003 の式 2)、ショット雑音律の SNR(Leitgeb ら Opt. Express 11, 889, 2003)、分散補償(Wojtkowski ら
Opt. Express 12, 2404, 2004)、ガウスビームの横分解能 (4λ/π)(f/d) と焦点深度 πΔx²/(2λ)。
層の厚さ・空洞・剥離の位置は合成で仕込んだ真値。【学習】0。【較正】0。
"""
from __future__ import annotations

import itertools
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import octscan as O  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL = os.path.join(ROOT, "data", "oct_real", "paint_sdoct_cc_by.npz")

#: 合成の装置(840 nm の分光器型)。光子は「参照腕 2 万・反射率 1 の鏡で 100 万 / 画素」(典型的な桁の模型)。
SD = {"center_nm": 840.0, "bandwidth_nm": 50.0, "n_pixels": 2048}
PHOT = {"photons_ref_per_pixel": 2e4, "photons_mirror_per_pixel": 1e6, "eta": 0.8, "sigma_d": 10.0}
#: B スキャン用: 参照腕を試料腕より十分強く(表面の反射 4 % が参照の 1/25)—— 自己相関の幽霊を抑える実機の常套。
PHOT_B = {"photons_ref_per_pixel": 3e4, "photons_mirror_per_pixel": 3e4, "eta": 0.8, "sigma_d": 10.0}

#: 実測の論文の表 1(µm)。鍵は表の見本の名前。
TABLE1 = {
    "黒 A": {"clear": (99.8, 102.4, 103.3), "base": (20.9, 19.8, 20.6)},
    "黒 B": {"clear": (72.3, 74.9, 74.4), "base": (15.3, 15.2, 14.7)},
    "濃色 A": {"clear": (44.6, 45.7, 45.5), "base": (11.8, 11.4, 12.2)},
    "濃色 B": {"clear": (85.5, 87.4, 87.9), "base": (15.4, 17.5, 18.0)},
}
#: 原本のファイル名の色(公開側の書き方)。
FILE_COLOUR = {"V-D": "黒", "VI-D": "黒", "III-B": "濃色", "IV-C": "濃色", "II-A": "白"}
N_CLEAR, N_BASE = 1.56, 1.64          # 論文が使った屈折率(テラヘルツ帯の値)

FAILS: list[str] = []
GATES: list[str] = []


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def fwhm(z, y, z_min=None, z_max=None):
    """|A| の最大ピークの半値全幅(線形補間で半値の交点を求める)と位置。"""
    z = np.asarray(z, float)
    y = np.asarray(y, float)
    m = np.ones(z.shape, bool)
    if z_min is not None:
        m &= z > z_min
    if z_max is not None:
        m &= z < z_max
    i = int(np.argmax(np.where(m, y, -np.inf)))
    h = y[i] / 2
    lft = i
    while lft > 0 and y[lft] > h:
        lft -= 1
    rgt = i
    while rgt < y.size - 1 and y[rgt] > h:
        rgt += 1
    zl = np.interp(h, [y[lft], y[lft + 1]], [z[lft], z[lft + 1]])
    zr = np.interp(h, [y[rgt], y[rgt - 1]], [z[rgt], z[rgt - 1]])
    return float(zr - zl), float(z[i])


def mirror(z_um, n2=1.05):
    """空気の中に置いた弱い反射体(屈折率 n2 の基板の面)。光路 z_um。"""
    return {"layers": [{"material": 1.0, "thickness_um": 10.0}], "substrate": {"n": n2, "n_group": n2},
            "surface_um": z_um - 10.0}


# --------------------------------------------------------------------------- #
# 0. 撮る前の閉形式                                                              #
# --------------------------------------------------------------------------- #
def chapter_design():
    print("\n0. 撮る前の閉形式(oct_design)")
    rows = []
    cases = [
        ("SD 840/50 nm・λ 等間隔 2048", O.oct_design(840, 50, 2048, n_group=1.5, beam_waist_um=6.0,
                                                      photons_mirror_per_pixel=1e6, photons_ref_per_pixel=2e4)),
        ("SD 840/50 nm・k 等間隔 2048", O.oct_design(840, 50, 2048, n_group=1.5, beam_waist_um=6.0, grid="k",
                                                     photons_mirror_per_pixel=1e6, photons_ref_per_pixel=2e4)),
        ("SS 1310/100 nm・線幅 0.1 nm", O.oct_design(1310, 100, 2048, mode="ss", linewidth_nm=0.1, n_group=1.5,
                                                     beam_waist_um=9.0)),
        ("実測の装置 840/47 nm", O.oct_design(840, 47, 2048, wl_min_nm=797.24, wl_max_nm=972.04, n_group=1.56,
                                               focal_mm=30.0, beam_diameter_mm=2.6)),
    ]
    for name, d in cases:
        print("   %-28s 軸分解能 %.2f µm(空気)/ %.2f µm(媒質)、深さ範囲 %.0f µm、−6 dB %s、端の roll-off %.2f、"
              "感度 %s、横 %s、焦点深度 %s" % (
                  name, d["axial_resolution_air_um"], d["axial_resolution_um"], d["depth_range_air_um"],
                  "%.0f µm" % d["rolloff_6db_air_um"] if d["rolloff_6db_air_um"] else "なし",
                  d["rolloff_at_depth_range"], "%.1f dB" % d["sensitivity_db"] if d["sensitivity_db"] else "—",
                  "%.1f µm" % d["lateral_resolution_um"] if d["lateral_resolution_um"] else "—",
                  "%.0f µm" % d["depth_of_focus_um"] if d["depth_of_focus_um"] else "—"))
        rows.append((name, d))
    d0 = cases[0][1]
    gate("閉形式の 2 通りの書き方が一致(δz = 0.441 λ0²/Δλ、z_max = λ0²/(4δλ))",
         abs(d0["axial_resolution_air_um"] - 2 * math.log(2) / math.pi * 0.84 ** 2 / 0.05) < 1e-9
         and abs(d0["depth_range_air_um"] - 0.84 ** 2 / (4 * d0["pixel_nm"] / 1000.0)) < 1e-6,
         "δz %.4f µm、z_max %.1f µm" % (d0["axial_resolution_air_um"], d0["depth_range_air_um"]))
    return dict(rows)


# --------------------------------------------------------------------------- #
# 1. 実測(CC BY 4.0)                                                           #
# --------------------------------------------------------------------------- #
def load_real():
    if not os.path.exists(REAL):
        print("FAIL: 実測データ %s が無い(tools/gen_oct_real.py で作る)" % REAL)
        raise SystemExit(1)
    return np.load(REAL)


def real_sample(data, key, n_lines=None):
    """1 枚の見本: 生スペクトル → B スキャン → 表面 → 平らに並べた平均の断面 → 透明層と着色層の界面。"""
    sp = data["spectra_" + key].astype(float)
    if n_lines is not None and n_lines < sp.shape[0]:
        sp = sp[np.linspace(0, sp.shape[0] - 1, n_lines).round().astype(int)]
    t = O.oct_from_spectra(sp, data["wavelength_nm"], center_nm=840.0, bandwidth_nm=47.0,
                           x_um=np.linspace(0.0, 1000.0, sp.shape[0]))
    b = O.oct_bscan(t, dc="smooth", window="hann", zero_pad=2)
    dz = b["dz_um"]
    img = b["image_db"]
    surf = O.oct_bscan_boundaries(img[:int(600 / dz)], 1, um_per_px=dz, top_px=int(15 / dz), max_jump_px=3)
    s = surf["rows"][0]
    fl = O.oct_bscan_flatten(b, s, above_um=20.0, below_um=300.0)
    i2 = O.oct_layer_thickness(fl, n_interfaces=1, z_range_um=(50.0, 320.0))
    z2 = float(i2["z_opt_um"][0])
    out = {"bscan": b, "surface_rows": s, "flat": fl, "z2": z2, "clear": (z2 - 20.0) / N_CLEAR}
    try:
        i3 = O.oct_layer_thickness(fl, n_interfaces=1, z_range_um=(z2 + 8.0, z2 + 60.0), min_prominence_db=1.0)
        z3 = float(i3["z_opt_um"][0])
        out.update({"z3": z3, "base": (z3 - z2) / N_BASE, "base_prominence_db": float(i3["prominence_db"][0]),
                    "refused": None})
    except ValueError as e:
        out.update({"z3": None, "base": None, "refused": str(e)})
    # 列ごとの透明層(表面からの相対で、平均の位置 ±6 µm の窓)—— ばらつきの尺度
    o2 = int(round((z2 - 20.0) / dz))
    w = int(round(6.0 / dz))
    c2 = O.oct_bscan_boundaries(img[:int(700 / dz)], 1, um_per_px=dz, reference_rows=s, offset_px=(o2 - w, o2 + w),
                                max_jump_px=2, jump_penalty=1.0, n_group=N_CLEAR)
    out["clear_cols"] = c2["thickness_um"][0]
    out["rows2"] = c2["rows"][1]
    if out["z3"] is not None:
        o3 = int(round((out["z3"] - z2) / dz))
        c3 = O.oct_bscan_boundaries(img[:int(700 / dz)], 1, um_per_px=dz, reference_rows=c2["rows"][1],
                                    offset_px=(o3 - w, o3 + w), max_jump_px=2, jump_penalty=1.0, n_group=N_BASE)
        out["rows3"] = c3["rows"][1]
    return out


def chapter_real():
    print("\n1. 実測: 自動車塗装の見本の生スペクトル(Liverpool Research Data Catalogue 126、CC BY 4.0)")
    data = load_real()
    wl = data["wavelength_nm"]
    dwl = np.diff(wl)
    print("   分光器: %d 画素、%.2f〜%.2f nm、画素の幅 %.4f〜%.4f nm(等間隔でない較正)" % (
        wl.size, wl[0], wl[-1], dwl.min(), dwl.max()))
    # 1a. ガラス板 2 本で軸分解能
    gp = data["glass_pair"].astype(float)
    mean = gp.mean(axis=0)
    env = O.oct_k_linearize(O.oct_from_spectra(mean - np.percentile(mean, 1), wl, center_nm=840.0, bandwidth_nm=47.0))
    S = np.clip(env["spectrum"], 0, None)
    kk = env["k_rad_per_um"]
    Q = 64 * kk.size
    psf = {}
    for win in ("none", "hann"):
        w = np.ones(kk.size) if win == "none" else np.hanning(kk.size)
        g = np.abs(np.fft.fft(S * w, Q))
        zq = np.arange(Q) * np.pi / (Q * (kk[1] - kk[0]))
        g = np.concatenate([g[Q // 2:], g[:Q // 2]])
        zq = np.concatenate([zq[Q // 2:] - zq[-1] - zq[1], zq[:Q // 2]])
        psf[win] = fwhm(zq, g)[0]
    meas = {}
    for win in ("none", "hann"):
        ws = []
        for r in (0, 1):
            t = O.oct_from_spectra(gp[r], wl, center_nm=840.0, bandwidth_nm=47.0)
            a = O.oct_ascan(O.oct_k_linearize(t), window=win, dc="smooth", zero_pad=16)
            ws.append(fwhm(a["z_um"], a["amplitude"], z_min=15.0))
        meas[win] = ws
    est = O.oct_from_spectra(mean, wl)
    print("   ガラス板(2 本): 半値全幅 窓なし %.2f / %.2f µm、hann %.2f / %.2f µm(位置 %.1f µm)" % (
        meas["none"][0][0], meas["none"][1][0], meas["hann"][0][0], meas["hann"][1][0], meas["none"][0][1]))
    print("   実測の光源スペクトルの |FT|: 窓なし %.2f µm、hann %.2f µm / 公称 47 nm のガウスの閉形式 %.2f µm"
          "(実測の重心 %.1f nm・2.355σ %.1f nm —— ガウスより広く、裾が重い)" % (
              psf["none"], psf["hann"], 2 * math.log(2) / math.pi * 0.84 ** 2 / 0.047, est["center_nm"],
              est["bandwidth_nm"]))
    nominal = 2 * math.log(2) / math.pi * 0.84 ** 2 / 0.047
    gate("実測の点像の幅が、記録された光源スペクトルの |FT| と 0.35 µm 以内、公称のガウスの式より 2 割以上細い",
         max(abs(m[0] - psf[w]) for w in ("none", "hann") for m in meas[w]) < 0.35
         and max(m[0] for m in meas["none"]) < 0.8 * nominal,
         "論文の値 5.5 µm(Tukey 窓)も公称の 6.6 µm より細い。hann で 0.3 µm 広いのは、干渉項の包絡 √(S_r S_s) が"
         "記録された和 S_r + S_s と形が違うため")
    # 1b. 見本 5 枚
    keys = ["V-D", "VI-D", "III-B", "IV-C", "II-A"]
    res = {k: real_sample(data, k) for k in keys}
    for k in keys:
        r = res[k]
        print("   見本 %-5s(%s): 透明層 %.2f µm(列ごと %.2f ± %.2f)、着色層 %s" % (
            k, FILE_COLOUR[k], r["clear"], float(np.mean(r["clear_cols"])), float(np.std(r["clear_cols"])),
            "%.2f µm(谷から %.1f dB)" % (r["base"], r["base_prominence_db"]) if r["base"] is not None
            else "拒否 —— " + r["refused"][:90]))
    # 対応: 透明層の厚さだけで決める(4! 通りを全部比べる)
    cand = ["V-D", "VI-D", "III-B", "IV-C"]
    labels = list(TABLE1)
    costs = []
    for perm in itertools.permutations(labels):
        costs.append((sum(abs(res[c]["clear"] - TABLE1[p]["clear"][0]) for c, p in zip(cand, perm)), perm))
    costs.sort()
    best, second = costs[0], costs[1]
    mapping = dict(zip(cand, best[1]))
    print("   対応(透明層だけで決める): %s —— ずれの和 %.2f µm、2 番目の並べ替えは %.2f µm" % (
        ", ".join("%s→%s" % (c, mapping[c]) for c in cand), best[0], second[0]))
    gate("透明層の厚さで対応が 1 通りに決まる(最良 < 5 µm、次点 > 20 µm)", best[0] < 5.0 and second[0] > 20.0,
         "★ファイル名の色と表の色名が入れ替わって見える(黒のファイル → 表の濃色)。論文に対応の記載は無く、推定")
    rows = []
    dc_us, dc_mic, db_mic, db_oct = [], [], [], []
    for c in cand:
        t1 = TABLE1[mapping[c]]
        r = res[c]
        dc_us.append(r["clear"] - t1["clear"][1])
        dc_mic.append(r["clear"] - t1["clear"][2])
        bb = r["base"] if r["base"] is not None else float("nan")
        db_mic.append(bb - t1["base"][2])
        db_oct.append(bb - t1["base"][0])
        rows.append([c, mapping[c], "%.1f" % r["clear"], "%.1f" % t1["clear"][0], "%.1f" % t1["clear"][1],
                     "%.1f" % t1["clear"][2], "%.1f" % bb if r["base"] is not None else "拒否",
                     "%.1f" % t1["base"][0], "%.1f" % t1["base"][1], "%.1f" % t1["base"][2]])
        print("     %-5s → %-5s 透明層 %.1f(論文 OCT %.1f・超音波 %.1f・顕微鏡 %.1f)、着色層 %.1f(%.1f・%.1f・%.1f)" % (
            c, mapping[c], r["clear"], *t1["clear"], bb, *t1["base"]))
    dc_oct = [res[c]["clear"] - TABLE1[mapping[c]]["clear"][0] for c in cand]
    gate("透明層: 4 枚とも論文の OCT と 2 µm 以内、顕微鏡と 4 µm 以内",
         max(abs(v) for v in dc_oct) < 2.0 and max(abs(v) for v in dc_mic) < 4.0,
         "論文の OCT との差 %s、顕微鏡との差 %s、超音波との差 %s µm(論文の OCT 自身も顕微鏡より 0.9〜3.5 µm 薄い —— "
         "同じ屈折率 1.56 を使うので、差の大半は屈折率の借り物の分)" % (", ".join("%+.1f" % v for v in dc_oct),
                                                    ", ".join("%+.1f" % v for v in dc_mic),
                                                    ", ".join("%+.1f" % v for v in dc_us)))
    n_ok = sum(bool(abs(v) <= 2.5) for v in db_mic)
    worst = cand[int(np.nanargmax(np.abs(db_mic)))]
    gate("着色層(対応とは独立): 4 枚中 3 枚が顕微鏡と 2.5 µm 以内", n_ok >= 3,
         "顕微鏡との差 %s µm。★%s は %.1f µm ずれる(平均の断面の 2 つの山の間隔は %.1f µm(光路)で、論文の OCT の "
         "値 %.1f µm とも合わない。未解決)" % (", ".join("%+.1f" % v for v in db_mic), worst,
                                         db_mic[cand.index(worst)], res[worst]["z3"] - res[worst]["z2"],
                                         TABLE1[mapping[worst]]["base"][0]))
    # 1c. 白: 着色層が強く散乱し、下の面が立たない → 拒否。減衰の傾きから減衰係数
    w = res["II-A"]
    fl = w["flat"]
    z = fl["z_um"]
    sel = (z > w["z2"] + 10) & (z < w["z2"] + 60)
    slope = np.polyfit(z[sel], fl["db"][sel], 1)[0]
    mu = -slope * N_BASE / (20 * math.log10(math.e))           # 振幅は exp(−µ z_phys)、往復で × 2 は µ_t の定義に含めた
    others = [res[k]["base_prominence_db"] for k in cand]
    print("   白の見本: 透明層 %.1f µm は測れる。着色層の中は %.2f dB/µm(光路)で滑らかに減衰 → 1 回散乱の模型で "
          "µ_t ≈ %.0f /mm(推定)" % (w["clear"], -slope, mu * 1000))
    gate("白の見本の着色層の下の面は拒否(谷から 1 dB 立つ山が無い)、黒・濃色の 4 枚は受理",
         w["refused"] is not None and all(v is not None and v >= 1.0 for v in others),
         "黒・濃色の下の面は谷から %s dB" % ", ".join("%.1f" % v for v in others))
    # 1d. 自己相関の幽霊(III-B): 表面の傾きに従わず、透明層の光学厚の深さに水平に出る
    r = res["III-B"]
    b = r["bscan"]
    dz = b["dz_um"]
    lag = r["z2"] - 20.0                                          # 表面から透明層の下の面までの光路
    lo_px, hi_px = int((lag - 12) / dz), int((lag + 12) / dz)
    gh = O.oct_bscan_boundaries(b["image_db"][:int(600 / dz)], 1, um_per_px=dz, top_px=lo_px, bottom_px=hi_px,
                                max_jump_px=1, jump_penalty=2.0)
    x = np.arange(r["surface_rows"].size)
    s_slope = np.polyfit(x, r["surface_rows"] * dz, 1)[0] * x.size
    g_slope = np.polyfit(x, gh["rows"][0] * dz, 1)[0] * x.size
    g_depth = float(np.mean(gh["rows"][0])) * dz
    print("   自己相関の幽霊(III-B): 深さ %.1f µm(透明層の光学厚 %.1f µm)、横 1 mm での傾き %.1f µm(表面は %.1f µm)" % (
        g_depth, lag, g_slope, s_slope))
    gate("実測の幽霊が透明層の光学厚の深さ(±3 µm)に、表面の傾きの 1/4 未満で水平に出る",
         abs(g_depth - lag) < 3.0 and abs(g_slope) < 0.25 * abs(s_slope),
         "参照光とでなく表面と下の面の間の干渉(自己相関)。位相をずらした 2 枚の差でしか消えない")
    return {"res": res, "mapping": mapping, "rows": rows, "glass": (gp, meas, psf), "ghost": (gh, g_depth, lag),
            "white_mu": mu}


# --------------------------------------------------------------------------- #
# 2. 多層フィルム(合成)                                                        #
# --------------------------------------------------------------------------- #
FILM = {"layers": [{"material": "PMMA", "thickness_um": 25.0, "name": "PMMA"},
                   {"material": "POLYCARBONATE", "thickness_um": 40.0, "name": "PC"},
                   {"material": "POLYSTYRENE", "thickness_um": 15.0, "name": "PS"}],
        "substrate": {"n": 1.51, "n_group": 1.53, "name": "glass"}, "surface_um": 400.0}


def chapter_film():
    print("\n2. 多層フィルム(合成): 空気 / PMMA 25 / ポリカーボネート 40 / ポリスチレン 15 µm / ガラス相当の基板")
    import materials as M
    it = O.oct_interferogram(FILM, grid="k", seed=1, **SD, **PHOT)
    a = O.oct_ascan(it, window="hann", zero_pad=8)
    mats = ["PMMA", "POLYCARBONATE", "POLYSTYRENE"]
    L = O.oct_layer_thickness(a, n_group=mats, n_interfaces=4, z_range_um=(300.0, 700.0))
    truth = np.array([25.0, 40.0, 15.0])
    n_ph = np.array([M.material_optical_constants(m, 840.0)["n"] for m in mats])
    by_phase = L["optical_thickness_um"] / n_ph
    pred_phase = truth * L["group_index"] / n_ph
    for i, m in enumerate(mats):
        print("   %-14s 群屈折率 %.4f → %.3f µm(真値 %.0f)、位相屈折率 %.4f で割ると %.3f µm(閉形式 %.3f)" % (
            m, L["group_index"][i], L["thickness_um"][i], truth[i], n_ph[i], by_phase[i], pred_phase[i]))
    err = np.abs(L["thickness_um"] - truth)
    gate("群屈折率で割った厚さが真値と 0.05 µm 以内(3 層)", float(err.max()) < 0.05, "最大 %.3f µm" % err.max())
    gate("位相屈折率で割ると t·n_g/n だけ厚く出る(閉形式と 0.05 µm)",
         float(np.max(np.abs(by_phase - pred_phase))) < 0.05,
         "ずれ +%.1f〜+%.1f %%" % (100 * (by_phase / truth - 1).min(), 100 * (by_phase / truth - 1).max()))
    # 軸分解能: 窓なし・hann
    d = O.oct_design(grid="k", **SD)
    an = O.oct_ascan(it, window="none", zero_pad=16)
    w0, _ = fwhm(an["z_um"], an["amplitude"], z_min=380, z_max=420)
    wh, _ = fwhm(a["z_um"], a["amplitude"], z_min=380, z_max=420)
    print("   表面の点像: 窓なし %.3f µm(閉形式 %.3f)、hann %.3f µm(閉形式 %.3f)" % (
        w0, d["axial_resolution_air_um"], wh, d["axial_resolution_air_um"] * d["window_broadening"]))
    gate("表面の点像の幅が閉形式と 1 % 以内(窓なし・hann)",
         abs(w0 / d["axial_resolution_air_um"] - 1) < 0.01
         and abs(wh / (d["axial_resolution_air_um"] * d["window_broadening"]) - 1) < 0.01)
    # SNR: 弱い鏡(R = 1e-4)を 500 µm に、k 等間隔と λ 等間隔(3 次補間)
    seeds = range(3 if REDUCED else 8)
    snr = {}
    for grid in ("k", "lambda"):
        R = ((1 - 1.02) / 2.02) ** 2
        dd = O.oct_design(grid=grid, reflectivity=R, **SD, photons_mirror_per_pixel=PHOT["photons_mirror_per_pixel"],
                          photons_ref_per_pixel=PHOT["photons_ref_per_pixel"])
        ro = float(np.interp(500.0, dd["rolloff"][:, 0], dd["rolloff"][:, 1]))
        ms = []
        for sd in seeds:
            itx = O.oct_interferogram(mirror(500.0, 1.02), grid=grid, seed=sd, **SD, **PHOT)
            if not itx["k_linear"]:
                itx = O.oct_k_linearize(itx)
            ms.append(O.oct_ascan(itx, window="hann", zero_pad=4)["snr_db"])
        snr[grid] = (float(np.mean(ms)), dd["snr_db"] + 20 * math.log10(ro))
        print("   SNR(R = %.1e、500 µm): %s 等間隔 実測 %.2f dB / 閉形式 %.2f dB" % (
            R, "k" if grid == "k" else "λ(3 次補間で k へ)", snr[grid][0], snr[grid][1]))
    gate("k 等間隔の分光器の SNR がショット雑音律の閉形式と 0.3 dB 以内", abs(snr["k"][0] - snr["k"][1]) < 0.3)
    gate("λ 等間隔 + 3 次補間は SNR が閉形式より 0.5〜1.5 dB 良く見える(補間で雑音が相関し、床が下がる)",
         0.5 < snr["lambda"][0] - snr["lambda"][1] < 1.5,
         "差 %+.2f dB —— 窓の外の床が白色雑音でなくなる。感度を言うときは補間の前の雑音で" % (
             snr["lambda"][0] - snr["lambda"][1]))
    # roll-off(SD、λ 等間隔): 鏡を深さごとに
    zs = [200, 600, 1000, 1400, 1800] if REDUCED else [150, 400, 700, 1000, 1300, 1600, 1900, 2150]
    ro = {}
    for grid in ("k", "lambda"):
        d = O.oct_design(grid=grid, **SD)
        amps = []
        for zz in zs:
            itx = O.oct_interferogram(mirror(zz), noise=False, grid=grid, **SD, **PHOT)
            if not itx["k_linear"]:
                itx = O.oct_k_linearize(itx)
            aa = O.oct_ascan(itx, window="hann", zero_pad=8)
            amps.append(float(aa["amplitude"][aa["z_um"] > 20].max()))
        amps = np.array(amps)
        closed = np.interp(zs, d["rolloff"][:, 0], d["rolloff"][:, 1])
        ro[grid] = (amps / amps[0] * closed[0], closed, d)
        print("   roll-off(SD・%s 等間隔): 実測 %s / 閉形式 %s(−6 dB の深さ %.0f µm)" % (
            "k" if grid == "k" else "λ", np.round(ro[grid][0], 3), np.round(closed, 3), d["rolloff_6db_air_um"]))
    gate("k 等間隔の分光器の roll-off(画素の箱の |sinc| × 分光器のガウス)が閉形式と 0.02 以内",
         float(np.max(np.abs(ro["k"][0] - ro["k"][1]))) < 0.02)
    deep = np.asarray(zs) >= 1400
    gate("λ 等間隔 + 3 次補間は深いところで閉形式より 0.03 以上低い(補間の減衰が roll-off に乗る)",
         bool(np.all(ro["lambda"][1][deep] - ro["lambda"][0][deep] > 0.03)),
         "最深 %d µm で %.3f(閉形式 %.3f)。k 等間隔の分光器が深い所で有利な理由" % (
             zs[-1], ro["lambda"][0][-1], ro["lambda"][1][-1]))
    return {"it": it, "a": a, "L": L, "rolloff_sd": (zs, ro["k"][0], ro["k"][1]), "rolloff_lam": (zs, ro["lambda"][0]),
            "snr": snr}


# --------------------------------------------------------------------------- #
# 3. 処理の段で壊れるもの                                                        #
# --------------------------------------------------------------------------- #
def chapter_processing():
    print("\n3. 処理の段で壊れるもの")
    out = {}
    # k 線形化なし
    rows = []
    for zz in (300, 900, 1500):
        it = O.oct_interferogram(mirror(zz), noise=False, **SD, **PHOT)
        ok = fwhm(*_za(O.oct_ascan(O.oct_k_linearize(it), window="hann", zero_pad=8)), z_min=20)
        bad = fwhm(*_za(O.oct_ascan(O.oct_k_linearize(it, method="none"), window="hann", zero_pad=8)), z_min=20)
        rows.append((zz, ok[0], bad[0]))
    print("   k 線形化なし(λ 等間隔をそのまま FFT): 点像の幅 %s µm(線形化すると %s)" % (
        [round(r[2], 1) for r in rows], [round(r[1], 2) for r in rows]))
    gate("k 線形化しないと深さに比例して広がる(1500 µm で 3 倍超)、すれば一定(1 %)",
         rows[-1][2] > 3 * rows[-1][1] and max(r[1] for r in rows) / min(r[1] for r in rows) < 1.01)
    out["klin"] = rows
    # 線形補間 vs 3 次: 深い鏡の裾
    it = O.oct_interferogram(mirror(1900), noise=False, **SD, **PHOT)
    side = {}
    for meth in ("linear", "cubic"):
        a = O.oct_ascan(O.oct_k_linearize(it, method=meth), window="hann", zero_pad=4)
        z, y = a["z_um"], a["amplitude"]
        pk = int(np.argmax(y * (z > 20)))
        far = (np.abs(z - z[pk]) > 60) & (z > 20)
        side[meth] = 20 * math.log10(y[far].max() / y[pk])
    print("   深さ 1900 µm の鏡の裾(主ピークから 60 µm より外の最大): 線形補間 %.1f dB、3 次 %.1f dB" % (
        side["linear"], side["cubic"]))
    gate("線形補間は深いところで 3 次より 5 dB 以上高い裾を作る", side["linear"] > side["cubic"] + 5.0)
    out["interp"] = side
    # 分散の不一致: 試料腕だけに溶融石英 L mm
    Ls = [5.0, 10.0, 20.0] if REDUCED else [2.5, 5.0, 10.0, 15.0, 20.0, 30.0]
    d = O.oct_design(grid="k", **SD)
    rr = []
    for Lmm in Ls:
        it = O.oct_interferogram(mirror(500.0), grid="k", noise=False, mismatch_material="SILICA",
                                 mismatch_length_mm=Lmm, **SD, **PHOT)
        b = O.oct_dispersion_broadening("SILICA", Lmm, 840.0, 50.0)
        w_raw = fwhm(*_za(O.oct_ascan(it, window="none", zero_pad=16)), z_min=20)[0]
        # 既知の材料: 閉形式の係数で解析信号の位相を戻してから A スキャンに(oct_dispersion_compensate)
        comp = O.oct_dispersion_compensate(it, a2=b["a2"], a3=b["a3"], k_center=b["k_center"])
        w_known = fwhm(*_za(O.oct_ascan(comp, window="none", zero_pad=16)), z_min=20)[0]
        em = O.oct_dispersion_estimate(it, method="mirror")
        w_mirror = fwhm(*_za(O.oct_ascan(it, window="none", zero_pad=16, a2=em["a2"], a3=em["a3"],
                                        k_center=em["k_center"])), z_min=20)[0]
        es = O.oct_dispersion_estimate(it, method="sharpness", a2_range=(-3 * b["a2"] - 5, 3 * b["a2"] + 5),
                                       a3_range=(-4 * b["a3"] - 1, 4 * b["a3"] + 1))
        w_sharp = fwhm(*_za(O.oct_ascan(it, window="none", zero_pad=16, a2=es["a2"], a3=es["a3"],
                                       k_center=es["k_center"])), z_min=20)[0]
        rr.append((Lmm, w_raw / d["axial_resolution_air_um"], b["broadening"], w_known, w_mirror, w_sharp, b))
        print("   溶融石英 %4.1f mm(GVD %.1f fs²/mm): 広がり %.3f 倍(閉形式 √(1+σ⁴φ₂²) = %.3f)→ 補償後 %.2f / %.2f / %.2f µm"
              "(既知の材料 / 鏡の位相 / 鋭さ最大)" % (Lmm, b["gvd_fs2_per_mm"], w_raw / d["axial_resolution_air_um"],
                                                   b["broadening"], w_known, w_mirror, w_sharp))
    gate("分散の不一致の広がりが閉形式 √(1 + σ⁴φ₂²) と 0.5 % 以内", max(abs(r[1] / r[2] - 1) for r in rr) < 0.005)
    gate("3 通りの補償(既知の材料・鏡の位相・鋭さ最大)で点像の幅が閉形式の 2 % 以内に戻る",
         max(abs(v / d["axial_resolution_air_um"] - 1) for r in rr for v in r[3:6]) < 0.02)
    out["disp"] = rr
    # 波長掃引の非線形と k クロック
    eps = 0.05
    it = O.oct_interferogram(mirror(1500.0), center_nm=1310.0, bandwidth_nm=100.0, mode="ss", sweep_nonlinearity=eps,
                             linewidth_nm=0.05, noise=False, n_pixels=2048, **PHOT)
    good = fwhm(*_za(O.oct_ascan(O.oct_k_linearize(it), window="none", zero_pad=8)), z_min=20)[0]
    uni = np.linspace(it["k_rad_per_um"][0], it["k_rad_per_um"][-1], it["k_rad_per_um"].size)
    bad = fwhm(*_za(O.oct_ascan(O.oct_k_linearize(it, k_calibration=uni), window="none", zero_pad=8)), z_min=20)[0]
    dss = O.oct_design(1310.0, 100.0, 2048, mode="ss", linewidth_nm=0.05)
    print("   波長掃引 1310/100 nm、掃引の非線形 ε = %.2f: k を等間隔と仮定 %.1f µm、k クロック(真の k)%.2f µm"
          "(閉形式 %.2f)" % (eps, bad, good, dss["axial_resolution_air_um"]))
    gate("掃引の非線形は k の較正で消える(閉形式と 1 %)、仮定のままなら 3 倍超",
         abs(good / dss["axial_resolution_air_um"] - 1) < 0.01 and bad > 3 * good)
    zs = [200, 800, 1400, 2000, 2600]
    amps = []
    for zz in zs:
        itx = O.oct_interferogram(mirror(zz), center_nm=1310.0, bandwidth_nm=100.0, mode="ss", linewidth_nm=0.1,
                                  noise=False, n_pixels=2048, **PHOT)
        aa = O.oct_ascan(O.oct_k_linearize(itx), window="hann", zero_pad=8)
        amps.append(float(aa["amplitude"][aa["z_um"] > 20].max()))
    dss = O.oct_design(1310.0, 100.0, 2048, mode="ss", linewidth_nm=0.1)
    closed = np.interp(zs, dss["rolloff"][:, 0], dss["rolloff"][:, 1])
    meas = np.array(amps) / amps[0] * closed[0]
    print("   波長掃引の roll-off(瞬時線幅 0.1 nm): 実測 %s / 閉形式 %s(−6 dB %.0f µm = ln2·λ0²/(π δλ))" % (
        np.round(meas, 3), np.round(closed, 3), 1310.0 ** 2 * math.log(2) / (math.pi * 0.1) / 1000.0))
    gate("波長掃引の roll-off(線幅のガウス)が閉形式と 0.01 以内", float(np.max(np.abs(meas - closed))) < 0.01)
    out["ss"] = (zs, meas, closed)
    return out


def _za(a):
    return a["z_um"], a["amplitude"]


# --------------------------------------------------------------------------- #
# 4. 鏡像・自己相関・折り返し                                                    #
# --------------------------------------------------------------------------- #
def chapter_artifacts():
    print("\n4. 鏡像・自己相関・折り返し")
    out = {}
    it0 = O.oct_interferogram(mirror(-300.0), grid="k", noise=False, **SD, **PHOT)
    a = O.oct_ascan(it0, window="hann", zero_pad=4)
    seen = fwhm(*_za(a), z_min=20)[1]
    print("   参照より 300 µm 手前の面: 実数のスペクトルでは +%.1f µm に見える(鏡像)" % seen)
    gate("参照より手前の面は同じ深さの正の側に折り返す(±0.5 µm)", abs(seen - 300.0) < 0.5)
    sup = []
    for dphi in (0.02, 0.05, 0.1, 0.2, 0.4):
        itp = O.oct_interferogram(mirror(-300.0), grid="k", noise=False, reference_phase_rad=math.pi / 2 + dphi,
                                  **SD, **PHOT)
        a2 = O.oct_ascan(it0, quadrature=itp, window="hann", zero_pad=4)
        z, y = a2["z_um"], a2["amplitude"]
        s_meas = 20 * math.log10(y[z > 20].max() / y[z < -20].max())
        sup.append((dphi, s_meas, 20 * math.log10(math.tan(dphi / 2))))
    print("   直交の組 I₀ + i I_{π/2}(参照の位相の誤差 δ): 鏡像の残り %s dB / 閉形式 20 log tan(δ/2) %s dB" % (
        [round(s[1], 2) for s in sup], [round(s[2], 2) for s in sup]))
    gate("直交の組の鏡像の残りが閉形式 tan(δ/2) と 0.1 dB 以内(5 通りの δ)",
         max(abs(s[1] - s[2]) for s in sup) < 0.1, "本物の面は −300 µm の側に正しく出る")
    out["mirror"] = (a, sup)
    # 自己相関: PMMA 60 µm の 1 層、試料腕が強い(参照光と同じ桁)
    film = {"layers": [{"material": "PMMA", "thickness_um": 60.0}], "substrate": {"n": 1.70, "n_group": 1.74},
            "surface_um": 400.0}
    it = O.oct_interferogram(film, grid="k", seed=2, **SD, photons_ref_per_pixel=2e4, photons_mirror_per_pixel=5e5)
    ng = O.oct_dispersion_broadening("PMMA", 0.0)["group_index"]
    ghost = 60.0 * ng
    pr = {}
    for dc in ("reference", "reference+sample"):
        a = O.oct_ascan(it, window="hann", zero_pad=8, dc=dc)
        z, y = a["z_um"], a["amplitude"]
        win = np.abs(z - ghost) < 4
        pr[dc] = (20 * math.log10(y[win].max() / a["noise_sigma"]), float(z[win][np.argmax(y[win])]), a)
    print("   自己相関: PMMA 60 µm の上下の面の干渉が光路 %.1f µm(= n_g·d)に %.1f dB で出る → 試料腕だけのスペクトルを"
          "引くと %.1f dB" % (ghost, pr["reference"][0], pr["reference+sample"][0]))
    gate("自己相関の幽霊が n_g·d の位置(±1 µm)に立ち、試料腕だけのスペクトルを引くと 20 dB 以上下がる",
         abs(pr["reference"][1] - ghost) < 1.0 and pr["reference"][0] - pr["reference+sample"][0] > 20.0)
    out["autocorr"] = (pr, ghost)
    # 折り返し
    d = O.oct_design(grid="k", **SD)
    zm = d["depth_range_air_um"]
    folds = []
    for zz in (zm - 150.0, zm + 150.0):
        a = O.oct_ascan(O.oct_interferogram(mirror(zz), grid="k", noise=False, **SD, **PHOT), window="hann", zero_pad=4)
        folds.append((zz, fwhm(*_za(a), z_min=20)[1]))
    print("   深さ範囲 z_max = %.0f µm の外: 真の光路 %.0f → %.0f µm に見える(2 z_max − z = %.0f)" % (
        zm, folds[1][0], folds[1][1], 2 * zm - folds[1][0]))
    gate("深さ範囲の外の面は 2 z_max − z に折り返す(±1 µm)", abs(folds[1][1] - (2 * zm - folds[1][0])) < 1.0
         and abs(folds[0][1] - folds[0][0]) < 1.0)
    out["fold"] = (folds, zm)
    return out


# --------------------------------------------------------------------------- #
# 5. 限界: 薄い層と散乱                                                          #
# --------------------------------------------------------------------------- #
def chapter_limits():
    print("\n5. 限界: 薄すぎる層、散乱で沈む下の面")
    out = {}
    ng = O.oct_dispersion_broadening("PMMA", 0.0)["group_index"]
    ts = [3.0, 5.0, 7.0, 9.0, 12.0] if REDUCED else list(np.arange(2.0, 14.01, 0.5))
    res = {}
    for win in ("none", "hann"):
        rr = []
        for t in ts:
            s = {"layers": [{"material": "PMMA", "thickness_um": float(t)}], "substrate": {"n": 1.60, "n_group": 1.63},
                 "surface_um": 300.0}
            a = O.oct_ascan(O.oct_interferogram(s, grid="k", seed=3, **SD, **PHOT), window=win, zero_pad=8)
            try:
                L = O.oct_layer_thickness(a, n_group=["PMMA"], n_interfaces=2, z_range_um=(200.0, 450.0))
                rr.append((t, float(L["thickness_um"][0])))
            except ValueError:
                rr.append((t, None))
        lim = 1.4 * a["psf_fwhm_um"] / ng
        res[win] = (rr, lim, a["psf_fwhm_um"])
        acc = [(t, v) for t, v in rr if v is not None]
        print("   窓 %-4s: 点像の幅 %.2f µm(光路)→ 測れる下限 1.4 × %.2f / n_g = %.2f µm。受理 %d / %d、偏り最大 %.2f %%" % (
            win, a["psf_fwhm_um"], a["psf_fwhm_um"], lim, len(acc), len(rr),
            100 * max(abs(v / t - 1) for t, v in acc)))
    ok = True
    for win, (rr, lim, _p) in res.items():
        for t, v in rr:
            if t < lim - 0.3 and v is not None:
                ok = False
            if t > lim + 0.3 and v is None:
                ok = False
            if v is not None and abs(v / t - 1) > 0.015:
                ok = False
    gate("下限(点像の幅の 1.4 倍 / n_g)より薄い層は拒否、厚い層は 1.5 % 以内(窓 2 通り)", ok,
         "下限の近くで受けた値は偏る —— 2 つの点像が重なり、頂点が引き寄せ合う")
    out["thin"] = res
    # 散乱(減衰)で下の面が沈む: 50 µm の塗膜の減衰係数 µ_t を振る
    mus = [0.0, 20.0, 60.0, 100.0] if REDUCED else [0.0, 10.0, 20.0, 40.0, 60.0, 80.0, 100.0, 120.0]
    d_um = 50.0
    rows = []
    base = None
    for mu in mus:
        s = {"layers": [{"material": {"n": 1.55, "n_group": 1.58, "name": "paint"}, "thickness_um": d_um,
                         "attenuation_per_mm": mu}], "substrate": {"n": 1.75, "n_group": 1.80}, "surface_um": 200.0}
        a = O.oct_ascan(O.oct_interferogram(s, grid="k", seed=4, **SD, **PHOT), window="hann", zero_pad=4)
        z, y = a["z_um"], a["amplitude"]
        zb = 200.0 + 1.58 * d_um
        bot = 20 * math.log10(y[np.abs(z - zb) < 3].max() / a["noise_sigma"])
        if base is None:
            base = bot
        pred = base - 20 * math.log10(math.e) * mu * d_um / 1000.0
        try:
            O.oct_layer_thickness(a, n_group=[1.58], n_interfaces=2, min_snr_db=12.0)
            acc = True
        except ValueError:
            acc = False
        rows.append((mu, bot, pred, acc))
    print("   塗膜 50 µm の下の面の SNR(dB): 実測 %s / 閉形式 SNR₀ − 8.69 µ_t d %s、受理 %s" % (
        [round(r[1], 1) for r in rows], [round(r[2], 1) for r in rows], [r[3] for r in rows]))
    lim_mu = (base - 12.0) / (20 * math.log10(math.e) * d_um / 1000.0)
    gate("下の面の SNR が Beer–Lambert の閉形式と 1 dB 以内(雑音の床の上で)",
         max(abs(r[1] - r[2]) for r in rows if r[2] > 6.0) < 1.0)
    gate("SNR の予算で決まる µ_t の上限 %.0f /mm を境に、下は受理・上は拒否(±10 /mm を除く)" % lim_mu,
         all(r[3] == (r[0] < lim_mu) for r in rows if abs(r[0] - lim_mu) > 10.0))
    out["scatter"] = (rows, lim_mu)
    return out


# --------------------------------------------------------------------------- #
# 6. B スキャン: コンフォーマルコート                                            #
# --------------------------------------------------------------------------- #
def coat_sample(width, seed=0):
    """部品の段差(高さ 60 µm)を越えるコンフォーマルコート: 低い側で厚く、空洞 1 つと剥離 1 か所。"""
    rng = np.random.default_rng(seed)
    xs = np.linspace(0.0, width, 401)
    step = 60.0 / (1 + np.exp(-(xs - 0.55 * width) / 15.0))           # 部品の縁(なだらかな段)
    board = 160.0 - step + 1.5 * np.sin(xs / 37.0)                      # 板の面(上が浅い)
    # コートの表面は流れて段差を和らげる(段の 45 % だけ表面に出る)
    surf = 60.0 - 0.45 * step + 0.8 * np.sin(xs / 53.0 + 1.0)
    gap_l, gap_r = 0.15 * width, 0.30 * width
    # 剥離: 板との間の空気の隙間が 3 → 8 µm に広がる(厚さで上下の面の反射の干渉が変わり、明るさが揺れる)
    gap = np.where((xs > gap_l) & (xs < gap_r), 3.0 + 5.0 * (xs - gap_l) / (gap_r - gap_l), 0.0)
    # 剥離のところは 4 界面(表面 / コート→空気 / 空気→板)。他は空気の層の厚さ 0(界面が重なる)
    ifs = [surf, board - gap, board]
    mats = ["air", {"n": 1.48, "n_group": 1.50, "name": "coat"}, "air",
            {"n": 1.60, "n_group": 1.65, "name": "board"}]
    void = {"x_um": 0.72 * width, "z_um": float(np.interp(0.72 * width, xs, (surf + board) / 2)), "radius_um": 11.0,
            "material": "air"}
    s2 = {"materials": mats, "interfaces_um": ifs, "surface_um": 80.0, "inclusions": [void],
          "scatter": [{"layer": 1, "density_per_mm2": 300.0, "amplitude": 6e-4},
                      {"layer": 3, "density_per_mm2": 60000.0, "amplitude": 2.5e-3, "depth_um": 260.0}],
          "attenuation_per_mm": [0.0, 1.0, 0.0, 25.0]}
    _ = rng
    return s2, xs, surf, board, gap, void


def chapter_bscan():
    print("\n6. B スキャン: 部品の段差を越えるコンフォーマルコート(空洞・剥離)、横分解能と焦点深度")
    width = 1200.0
    ncol = 96 if REDUCED else 240
    npx = 1024
    s2, xs, surf, board, gap, void = coat_sample(width)
    t0 = time.time()
    b = O.oct_bscan_simulate(s2, width_um=width, n_columns=ncol, n_pixels=npx, beam_waist_um=7.0, focus_um=90.0,
                             seed=5, **PHOT_B)
    img = O.oct_bscan(b, dc="reference", zero_pad=2)
    dz = img["dz_um"]
    print("   合成 %d 列 × %d 画素(%.1f s)、縦 %.2f µm/画素" % (ncol, npx, time.time() - t0, dz))
    x = b["x_um"]
    im = img["image_db"]
    S = O.oct_bscan_boundaries(im[:int(900 / dz)], 1, um_per_px=dz, top_px=int(40 / dz), max_jump_px=30,
                               jump_penalty=0.15)
    s_rows = S["rows"][0]
    surf_t = np.interp(x, xs, surf)
    board_t = np.interp(x, xs, board)
    off_lo = int(10 / dz)
    off_hi = int(1.50 * 140 / dz)
    Bd = O.oct_bscan_boundaries(im[:int(900 / dz)], 1, um_per_px=dz, reference_rows=s_rows,
                                offset_px=(off_lo, off_hi), max_jump_px=40, jump_penalty=0.15, n_group=1.50)
    th = Bd["thickness_um"][0]
    truth = board_t - surf_t
    in_void = np.abs(x - void["x_um"]) < void["radius_um"] + 6
    in_gap = (x > 0.15 * width - 6) & (x < 0.30 * width + 6)
    in_edge = np.abs(x - 0.55 * width) < 3 * 7.0 + 2 * 15.0           # 部品の縁(段の幅 ±2×15 µm + ビーム)
    ok_cols = ~in_void & ~in_gap & ~in_edge
    err = th - truth
    ae = np.abs(err[ok_cols])
    print("   コートの厚さ(表面 → 板の面、群屈折率 1.50): 剥離・空洞・部品の縁の外 %d 列で誤差の中央値 %.2f µm、"
          "95 %% 点 %.2f µm、平均 %+.2f µm(真値 %.0f〜%.0f µm)/ 縁では最大 %.1f µm" % (
              ok_cols.sum(), float(np.median(ae)), float(np.percentile(ae, 95)), float(np.mean(err[ok_cols])),
              truth.min(), truth.max(), float(np.max(np.abs(err[in_edge])))))
    gate("段差を越えるコートの厚さの地図: 誤差の中央値 < 0.6 µm・95 % 点 < 5 µm(剥離・空洞・縁の外)",
         float(np.median(ae)) < 0.6 and float(np.percentile(ae, 95)) < 5.0,
         "外れは板の面のすぐ下の散乱(スペックル)が界面の山と干渉した列 —— 縁は段がビームの中で混ざる")
    if not REDUCED:
        # 内訳: 板の散乱を消して同じ処理 —— 偏りと裾が散乱から来ているかを確かめる
        s_ns = dict(s2)
        s_ns["scatter"] = [s2["scatter"][0]]
        bn = O.oct_bscan_simulate(s_ns, width_um=width, n_columns=ncol, n_pixels=npx, beam_waist_um=7.0, focus_um=90.0,
                                  seed=5, **PHOT_B)
        imn = O.oct_bscan(bn, dc="reference", zero_pad=2)["image_db"]
        Sn = O.oct_bscan_boundaries(imn[:int(900 / dz)], 1, um_per_px=dz, top_px=int(40 / dz), max_jump_px=30,
                                    jump_penalty=0.15)
        Bn = O.oct_bscan_boundaries(imn[:int(900 / dz)], 1, um_per_px=dz, reference_rows=Sn["rows"][0],
                                    offset_px=(off_lo, off_hi), max_jump_px=40, jump_penalty=0.15, n_group=1.50)
        en = Bn["thickness_um"][0] - truth
        aen = np.abs(en[ok_cols])
        print("   内訳: 板の散乱を消すと 中央値 %.2f µm、95 %% 点 %.2f µm、平均 %+.2f µm" % (
            float(np.median(aen)), float(np.percentile(aen, 95)), float(np.mean(en[ok_cols]))))
        gate("板の散乱を消すと平均の偏りが 0.3 µm 未満・95 % 点が 6 割未満に(偏りの出どころは板の中の散乱)",
             abs(float(np.mean(en[ok_cols]))) < 0.3 and float(np.percentile(aen, 95)) < 0.6 * float(np.percentile(ae, 95)))
    # 剥離: 板の面の反射が強くなる(コート→板 0.04 → 空気→板 0.23)
    A = 10 ** (im / 20)
    rows_b = np.round(Bd["rows"][1]).astype(int)
    peak_b = 20 * np.log10(np.array([A[max(0, r - 2):r + 3, c].max() for c, r in enumerate(rows_b)]))
    ref_level = float(np.median(peak_b[ok_cols]))
    flag_gap = peak_b > ref_level + 15.0
    dx = float(x[1] - x[0])
    tol = 2 * 7.0 + dx                                                  # ビームの 2 w0 + 列の間隔
    true_gap = (x > 0.15 * width) & (x < 0.30 * width)
    near_gap = (x > 0.15 * width - tol) & (x < 0.30 * width + tol)
    # 空洞: コートの中(表面 +15 µm 〜 板 −15 µm、界面の点像の裾を避ける)に雑音 +30 dB の反射
    flag_void = np.zeros(ncol, bool)
    for c in range(ncol):
        r0, r1 = int(s_rows[c] + 15 / dz), int(rows_b[c] - 15 / dz)
        if r1 > r0:
            flag_void[c] = im[r0:r1, c].max() > img["noise_db"] + 30.0
    true_void = np.abs(x - void["x_um"]) < void["radius_um"]
    near_void = np.abs(x - void["x_um"]) < void["radius_um"] + tol
    rec_gap = float(np.mean(flag_gap[true_gap]))
    print("   剥離(板の面の反射が中央値 +15 dB): 隙間の列の %.0f %% を検出、外れの検出 %d 列 / 空洞(コートの中に雑音 +30 dB の"
          "反射): 真値の %d 列のうち %d 列、外れ %d 列" % (100 * rec_gap, int(np.sum(flag_gap & ~near_gap)),
                                                 int(true_void.sum()), int(np.sum(flag_void & true_void)),
                                                 int(np.sum(flag_void & ~near_void))))
    gate("剥離の 6 割以上・空洞の全列を検出し、ビームの幅の外に誤検出が無い",
         rec_gap >= 0.6 and bool(np.all(flag_void[true_void])) and not np.any(flag_gap & ~near_gap)
         and not np.any(flag_void & ~near_void),
         "剥離の隙間 3 → 8 µm は上下の面の反射が干渉し、厚さで明るさが揺れる(取りこぼしはそこ)")
    # 横分解能と焦点深度
    lat = []
    configs = [(w0, u, il) for w0 in (4.0, 10.0) for (u, il) in ((0.0, "point"), (1.0, "point"), (1.0, "line"))]
    if not REDUCED:
        configs += [(6.0, u, il) for u in (0.0, 0.5, 1.5, 2.0) for il in ("point", "line")]
    for w0, uu, illum in configs:
        zr = math.pi * w0 ** 2 * 1.5 / 0.84
        zf = 150.0 + uu * zr
        s = {"materials": ["air", {"n": 1.5, "n_group": 1.5}], "interfaces_um": [np.array([50.0, 50.0])],
             "surface_um": 100.0, "points": [{"x_um": 150.0, "z_um": 150.0, "amplitude": 0.01}]}
        bb = O.oct_bscan_simulate(s, width_um=300.0, n_columns=301, n_pixels=512, beam_waist_um=w0, focus_um=zf,
                                  illumination=illum, noise=False, **PHOT)
        ii = O.oct_bscan(bb, dc="reference+sample", zero_pad=4)
        Am = 10 ** (ii["image_db"] / 20)
        zz = ii["z_um"]
        row = int(np.argmax(Am[:, 150] * (zz > 200)))
        prof = Am[row]
        wl, _ = fwhm(bb["x_um"], prof)
        u = (150.0 - zf) / zr
        lat.append((w0, illum, u, wl, math.sqrt(2 * math.log(2)) * w0 * math.sqrt(1 + u * u), float(prof.max())))
    for (w0, illum, u, wl, cl, pk) in lat:
        print("   w0 %4.1f µm・%-5s・焦点から %.1f z_R: 点像の横の半値幅 %.2f µm(閉形式 √(2 ln2)·w(z) = %.2f)" % (
            w0, "点照明" if illum == "point" else "ライン", abs(u), wl, cl))
    gate("横の点像の幅が閉形式 √(2 ln 2)·w(z) と 3 % 以内(焦点・z_R 外れ)", max(abs(r[3] / r[4] - 1) for r in lat) < 0.03)
    drop = {}
    for w0 in (4.0, 10.0):
        p0 = [r[5] for r in lat if r[0] == w0 and r[2] == 0.0][0]
        drop[w0] = {illum: [r[5] for r in lat if r[0] == w0 and abs(r[2] + 1.0) < 1e-9 and r[1] == illum][0] / p0
                    for illum in ("point", "line")}
    print("   焦点から z_R 外れた点の振幅: 点照明 %.4f(閉形式 2^(−1/2) = %.4f)、ライン照明 %.4f(2^(−1/4) = %.4f)" % (
        drop[4.0]["point"], 2 ** -0.5, drop[4.0]["line"], 2 ** -0.25))
    gate("焦点の外れ方: 点照明 (1+u²)^(−1/2)、ライン照明 (1+u²)^(−1/4) と 0.5 % 以内",
         all(abs(drop[w]["point"] / 2 ** -0.5 - 1) < 0.005 and abs(drop[w]["line"] / 2 ** -0.25 - 1) < 0.005
             for w in drop), "ライン照明は片方向だけ共焦点なので、焦点を外れても信号が落ちにくい(その分、散乱の背景も拾う)")
    return {"b": b, "img": img, "S": S, "Bd": Bd, "truth": (x, surf_t, board_t), "flags": (flag_gap, flag_void),
            "lat": lat, "drop": drop, "sample": (s2, xs, surf, board, gap, void)}


# --------------------------------------------------------------------------- #
# 図                                                                             #
# --------------------------------------------------------------------------- #
def _gray(a, lo, hi):
    return np.clip((a - lo) / (hi - lo), 0.0, 1.0)


def _overlay(g, rows_list, colors, step=1):
    rgb = np.stack([g, g, g], axis=-1)
    for rows, col in zip(rows_list, colors):
        for c in range(0, rgb.shape[1], step):
            y = int(round(rows[c]))
            if 0 <= y < rgb.shape[0]:
                rgb[y, c] = col
    return rgb


def _scale(a, sy, sx):
    return np.repeat(np.repeat(a, sy, axis=0), sx, axis=1)


def make_figures(design, real, film, proc, art, lim, bs):
    # 1. 実測の B スキャン 5 枚 + 界面
    panels, caps = [], []
    for k in ("V-D", "VI-D", "III-B", "IV-C", "II-A"):
        r = real["res"][k]
        b = r["bscan"]
        dz = b["dz_um"]
        top = max(0, int(np.mean(r["surface_rows"]) - 40.0 / dz))
        im = b["image_db"][top:top + int(260 / dz)]
        lo, hi = np.percentile(im, 35), np.percentile(im, 99.7)
        rows = [r["surface_rows"] - top, r["rows2"] - top] + ([r["rows3"] - top] if "rows3" in r else [])
        cols = [(1.0, 0.25, 0.2), (0.2, 0.9, 0.3), (0.3, 0.6, 1.0)]
        rgb = _overlay(_gray(im, lo, hi), rows, cols, step=2)
        panels.append(_scale(rgb, 1, 4))
        t1 = real["mapping"].get(k)
        caps.append("見本 %s(%s)%s" % (k, FILE_COLOUR[k], " → 表の %s" % t1 if t1 else "・着色層の下は見えない"))
    figs.save_grid("real_paint_bscans", panels, captions=caps, ncols=1,
                   title="実測の自動車塗装 5 枚: 表面(赤)・透明層の下の面(緑)・着色層の下の面(青)",
                   caption="生の干渉スペクトル(CC BY 4.0、Liverpool Research Data Catalogue 126)を Fullseye の op だけで "
                           "k 線形化・FFT し、界面を動的計画法で辿った。横 1 mm(100 本)、縦は表面の 40 µm 上から光路 260 µm。白の見本は"
                           "着色層が強く散乱し、下の面が立たない。III-B の表面の下の水平な線は自己相関の幽霊。")
    figs.save_table("real_thickness_table",
                    ["見本", "表の見本(推定)", "透明層 本 PoC", "論文 OCT", "超音波", "顕微鏡",
                     "着色層 本 PoC", "論文 OCT", "超音波", "顕微鏡"], real["rows"],
                    title="実測の層厚 [µm]: 本 PoC と論文の表 1(OCT・超音波・光学顕微鏡)",
                    caption="屈折率は論文と同じ 1.56(透明層)・1.64(着色層)。表のどの行がどのファイルかは論文に無く、"
                            "透明層の厚さで決めた(推定)。着色層はその対応と独立の突き合わせ。")
    ser = []
    for k in ("V-D", "VI-D", "III-B", "IV-C", "II-A"):
        r = real["res"][k]
        fl = r["flat"]
        ser.append(("%s(%s)" % (k, FILE_COLOUR[k]), fl["z_um"] - 20.0, fl["db"] - 20 * np.log10(fl["noise_sigma"])))
    ser = [(lab, zz[(zz > -10) & (zz < 260)], yy[(zz > -10) & (zz < 260)]) for lab, zz, yy in ser]
    figs.save_plot("real_flattened_profiles", ser, xlabel="表面からの光路 [µm]", ylabel="雑音の床からの dB",
                   xlim=(-10, 260), title="表面に沿って平均した深さの断面(実測)",
                   caption="黒・濃色は透明層の下の面と着色層の下の面の 2 つの山。白は透明層の下の面のあと滑らかに減衰する"
                           "(強い散乱)。この断面に oct_layer_thickness を掛けて層厚を出した。")
    gp, meas, psf = real["glass"]
    data = load_real()
    t = O.oct_from_spectra(gp[0], data["wavelength_nm"], center_nm=840.0, bandwidth_nm=47.0)
    a = O.oct_ascan(O.oct_k_linearize(t), window="none", zero_pad=16, dc="smooth")
    ah = O.oct_ascan(O.oct_k_linearize(t), window="hann", zero_pad=16, dc="smooth")
    z0 = meas["none"][0][1]
    sel = np.abs(a["z_um"] - z0) < 25
    figs.save_plot("real_glass_axial_psf",
                   [("窓なし(半値幅 %.2f µm)" % meas["none"][0][0], a["z_um"][sel] - z0,
                     a["amplitude"][sel] / a["amplitude"][sel].max()),
                    ("hann(%.2f µm)" % meas["hann"][0][0], ah["z_um"][sel] - z0, ah["amplitude"][sel] / ah["amplitude"][sel].max())],
                   xlabel="ピークからの光路 [µm]", ylabel="振幅(最大で 1)",
                   title="実測のガラス板の点像: 光源スペクトルの |FT|(%.2f µm)どおり" % psf["none"],
                   caption="公称 47 nm のガウスの閉形式 6.6 µm より細い —— 実測のスペクトルはガウスより広く裾が重い。")
    # 2. 合成の多層フィルム
    A = film["a"]
    z = A["z_um"]
    sel = (z > 350) & (z < 570)
    ser = [("A スキャン(hann)", z[sel], A["db"][sel] - 20 * np.log10(A["noise_sigma"]))]
    for zt in film["L"]["z_opt_um"]:
        ser.append(("", [zt, zt], [0, 75]))
    figs.save_plot("film_ascan", ser, xlabel="光路 [µm]", ylabel="雑音の床からの dB",
                   styles=[None] + ["dashed"] * len(film["L"]["z_opt_um"]),
                   colors=["emphasis"] + ["reference"] * len(film["L"]["z_opt_um"]),
                   title="多層フィルム(PMMA 25 / PC 40 / PS 15 µm)の A スキャン",
                   caption="破線は見つけた界面。光学厚を材料表の群屈折率で割ると真値と 0.05 µm 以内。")
    zs, meas_r, closed = film["rolloff_sd"]
    _zl, meas_l = film["rolloff_lam"]
    zss, mss, css = proc["ss"]
    d_sd = O.oct_design(grid="k", **SD)
    d_ss = O.oct_design(1310.0, 100.0, 2048, mode="ss", linewidth_nm=0.1)
    figs.save_plot("rolloff", [("SD k 等間隔", zs, meas_r), ("SD 閉形式", d_sd["rolloff"][:, 0], d_sd["rolloff"][:, 1]),
                               ("SD λ 等間隔 + 3 次補間", zs, meas_l),
                               ("SS 実測", zss, mss), ("SS 閉形式", d_ss["rolloff"][:, 0], d_ss["rolloff"][:, 1])],
                   xlabel="光路 [µm]", ylabel="振幅(roll-off)", kinds=["scatter", "line", "scatter", "scatter", "line"],
                   styles=[None, "dashed", None, None, "dashed"],
                   colors=["emphasis", "emphasis", "wrong", "right", "right"],
                   ylim=(0, 1.05), title="感度の roll-off: 分光器型(画素の箱 × 分解能)と波長掃引型(線幅)",
                   caption="SD 840/50 nm 2048 画素(深さ範囲 2.26 mm)、SS 1310/100 nm・瞬時線幅 0.1 nm。点 = 鏡を深さごとに置いた合成。")
    rr = proc["disp"]
    Lg = np.linspace(0, max(r[0] for r in rr), 60)
    figs.save_plot("dispersion_broadening",
                   [("実測", [r[0] for r in rr], [r[1] for r in rr]),
                    ("閉形式 √(1+σ⁴φ₂²)", Lg, [O.oct_dispersion_broadening("SILICA", L)["broadening"] for L in Lg]),
                    ("補償後(鋭さ最大)", [r[0] for r in rr], [r[5] / O.oct_design(grid="k", **SD)["axial_resolution_air_um"]
                                                          for r in rr])],
                   xlabel="試料腕だけにある溶融石英 [mm]", ylabel="点像の幅 / 分散なし",
                   kinds=["scatter", "line", "scatter"], styles=[None, "dashed", None],
                   colors=["wrong", "reference", "right"],
                   title="分散の不一致で点像が広がり、数値補償で戻る",
                   caption="840/50 nm。補償は exp(−i(a2Δk²+a3Δk³))、係数は A スキャンの鋭さが最大になるよう探した。")
    # 4. 鏡像・自己相関
    a_m, sup = art["mirror"]
    figs.save_plot("quadrature_suppression",
                   [("実測", [s[0] for s in sup], [s[1] for s in sup]),
                    ("閉形式 20 log tan(δ/2)", np.linspace(0.015, 0.45, 50),
                     20 * np.log10(np.tan(np.linspace(0.015, 0.45, 50) / 2)))],
                   xlabel="参照の位相の誤差 δ [rad]", ylabel="鏡像の残り [dB]", kinds=["scatter", "line"],
                   styles=[None, "dashed"], colors=["emphasis", "reference"],
                   title="直交の組で鏡像を消す: 位相の誤差 δ で tan(δ/2) だけ残る",
                   caption="I₀ + i I_{π/2} の複素スペクトルで ±z を分ける(full range)。")
    pr, ghost = art["autocorr"]
    ser = []
    for dc, lab in (("reference+sample", "試料腕だけも引く"), ("reference", "参照だけ引く")):
        aa = pr[dc][2]
        sel = aa["z_um"] < 520
        ser.append((lab, aa["z_um"][sel], aa["db"][sel] - 20 * np.log10(aa["noise_sigma"])))
    figs.save_plot("autocorrelation_ghost", ser, xlabel="光路 [µm]", ylabel="雑音の床からの dB",
                   colors=["right", "wrong"], styles=[None, "dashed"],
                   title="自己相関の幽霊: PMMA 60 µm の上下の面の干渉が n_g·d = %.0f µm に出る" % ghost,
                   caption="試料腕が参照光と同じ桁に強いと、層の上下の面どうしの干渉が 0 の近くに立つ。試料腕だけのスペクトルを"
                           "引けば消える(実機では位相を π ずらした 2 枚の差)。")
    rr_thin = lim["thin"]
    ser = []
    for win, col in (("none", "emphasis"), ("hann", "right")):
        rr, lm, _p = rr_thin[win]
        acc = [(t, v) for t, v in rr if v is not None]
        ser.append(("窓 %s(受理した厚さ)" % win, [t for t, _ in acc], [100 * (v / t - 1) for t, v in acc]))
    ser.append(("下限 窓なし", [rr_thin["none"][1]] * 2, [-1.0, 1.0]))
    ser.append(("下限 hann", [rr_thin["hann"][1]] * 2, [-1.0, 1.0]))
    figs.save_plot("thin_layer_limit", ser, xlabel="PMMA の厚さ [µm](真値)", ylabel="厚さの偏り [%]",
                   kinds=["scatter", "scatter", "line", "line"], colors=["emphasis", "right", "emphasis", "right"],
                   styles=[None, None, "dashed", "dashed"], xlim=(1.5, 14.5), ylim=(-1.0, 1.0),
                   title="薄い層の限界: 点像の幅の 1.4 倍(÷ n_g)より薄いと拒否",
                   caption="下限: 窓なし %.2f µm、hann %.2f µm。点が無い厚さは op が拒否した(2 つの点像が重なり、頂点が"
                           "引き寄せ合うので、見えても厚さが偏る)。" % (rr_thin["none"][1], rr_thin["hann"][1]))
    rows, lim_mu = lim["scatter"]
    figs.save_plot("scattering_snr", [("実測", [r[0] for r in rows], [r[1] for r in rows]),
                                      ("閉形式", [r[0] for r in rows], [r[2] for r in rows]),
                                      ("受理の下限 12 dB", [0, rows[-1][0]], [12, 12])],
                   xlabel="塗膜の減衰係数 µ_t [/mm](厚さ 50 µm)", ylabel="下の面の SNR [dB]",
                   kinds=["scatter", "line", "line"], styles=[None, "dashed", "dotted"],
                   colors=["emphasis", "reference", "wrong"],
                   title="散乱で下の面が沈む: SNR₀ − 8.69 µ_t d、%.0f /mm を超えると拒否" % lim_mu,
                   caption="1 回散乱(Beer–Lambert)の模型。実測の白の見本は µ_t ≈ %.0f /mm と推定(着色層の中の減衰の傾き)。" % (
                       real["white_mu"] * 1000))
    # 6. B スキャン
    img = bs["img"]
    dz = img["dz_um"]
    r0 = int(25 / dz)
    im = img["image_db"][r0:int(440 / dz)]
    lo, hi = img["noise_db"] + 3, np.percentile(im, 99.8)
    g = _gray(im, lo, hi)
    gr = np.stack([g, g, g], axis=-1)
    figs.save_grid("coat_bscan", [_scale(gr, 1, 2), _scale(_overlay(g, [bs["S"]["rows"][0] - r0, bs["Bd"]["rows"][1] - r0],
                                                                    [(1.0, 0.25, 0.2), (0.3, 0.6, 1.0)]), 1, 2)],
                   captions=["B スキャン(合成)", "表面(赤)と板の面(青)"], ncols=1, gray=True,
                   title="部品の段差を越えるコンフォーマルコート: 空洞と剥離",
                   caption="横 1.2 mm、縦は光路 25〜440 µm。左の剥離(3〜8 µm の空気の隙間)で板の面が明るくなり、右の空洞"
                           "(半径 11 µm)は上下の面が点で見え、その上の点線は空洞と表面の自己相関。板(基板)は散乱の多い層。")
    x, surf_t, board_t = bs["truth"]
    th = bs["Bd"]["thickness_um"][0]
    figs.save_plot("coat_thickness_map", [("OCT(群屈折率 1.50)", x, th), ("真値", x, board_t - surf_t)],
                   xlabel="横 [µm]", ylabel="コートの厚さ [µm]", kinds=["line", "line"], styles=[None, "dashed"],
                   colors=["emphasis", "reference"], title="コートの厚さの地図",
                   caption="段差の上でコートが薄くなる(表面は段差の 45 % しか追わない)。剥離・空洞の列は外れる。")
    lat = bs["lat"]
    uu = np.linspace(0.0, 2.1, 60)
    six = [r for r in lat if r[0] == 6.0]
    p0 = [r[5] for r in six if r[2] == 0.0 and r[1] == "point"][0]
    figs.save_plot("lateral_vs_dof",
                   [("横の半値幅 / 焦点での値(実測)", [-r[2] for r in lat if r[1] == "point"],
                     [r[3] / (math.sqrt(2 * math.log(2)) * r[0]) for r in lat if r[1] == "point"]),
                    ("√(1+u²)", uu, np.sqrt(1 + uu ** 2)),
                    ("信号 点照明(実測)", [-r[2] for r in six if r[1] == "point"], [r[5] / p0 for r in six if r[1] == "point"]),
                    ("(1+u²)^(−1/2)", uu, (1 + uu ** 2) ** -0.5),
                    ("信号 ライン照明(実測)", [-r[2] for r in six if r[1] == "line"], [r[5] / p0 for r in six if r[1] == "line"]),
                    ("(1+u²)^(−1/4)", uu, (1 + uu ** 2) ** -0.25)],
                   xlabel="焦点からのずれ |u| = |z − z_f| / z_R", ylabel="焦点での値を 1 とした比",
                   kinds=["scatter", "line", "scatter", "line", "scatter", "line"],
                   styles=[None, "dashed", None, "dashed", None, "dashed"],
                   colors=["emphasis", "emphasis", "right", "right", "wrong", "wrong"],
                   title="横分解能と焦点深度: 焦点を外れると点像が太り、信号が落ちる",
                   caption="z_R = π w0² n/λ(w0 4 µm で 90 µm、6 µm で 202 µm、10 µm で 561 µm)。細く絞るほど深さの"
                           "見える範囲が短い。ライン照明は片方向だけ共焦点なので信号の落ち方が緩い。")


def make_gif():
    """分散補償の係数 a2 を 0 から最適値まで動かすと、多層フィルムの B スキャンが締まる。"""
    xs = np.linspace(0, 600.0, 81)
    wav = 3 * np.sin(xs / 120.0)
    s2 = {"materials": ["air", "PMMA", "POLYCARBONATE", "POLYSTYRENE", {"n": 1.51, "n_group": 1.53}],
          "interfaces_um": [40 + wav, 65 + wav, 105 + wav * 0.6, 120 + wav * 0.6], "surface_um": 150.0,
          "scatter": [{"layer": 2, "density_per_mm2": 2000.0, "amplitude": 8e-4}]}
    b = O.oct_bscan_simulate(s2, width_um=600.0, n_columns=120, n_pixels=1024, beam_waist_um=6.0, focus_um=80.0,
                             seed=7, **PHOT)
    # 試料腕に溶融石英 12 mm: 全列に同じ位相を掛けて模擬(op は 1 本の面ごとに掛けるのと同じ)
    k = b["k_rad_per_um"]
    import octscan as _o
    fn, _ = _o._index_fn("SILICA", 2 * np.pi / 0.84, "gif")
    ngm = _o._group_index_at("SILICA", 840.0, "gif")
    disp = O.oct_dispersion_broadening("SILICA", 12.0, 840.0, 50.0)
    # 分散の位相は干渉項だけに掛かる: 参照を引いた交流分を解析信号にして位相を掛け、実部に戻す
    from scipy.signal import hilbert
    ac = b["spectra"] - b["reference_spectrum"]
    lam = O.oct_k_linearize(dict(b, spectra=ac, reference_spectrum=np.zeros_like(b["reference_spectrum"])))
    kk = lam["k_rad_per_um"]
    ph = 2 * kk * 12000.0 * (fn(kk) - ngm)
    lam["spectra"] = np.real(hilbert(lam["spectra"], axis=-1) * np.exp(1j * ph))
    lam["dc_removed"] = False
    lam["reference_spectrum"] = np.zeros(kk.size)
    _ = k
    frames = []
    a2s = np.concatenate([np.linspace(0, disp["a2"], 14), np.full(4, disp["a2"])])
    for a2 in a2s:
        r = O.oct_bscan(lam, dc="none", zero_pad=1, a2=float(a2), a3=float(disp["a3"] * a2 / disp["a2"]),
                        k_center=disp["k_center"])
        im = r["image_db"][int(130 / r["dz_um"]):int(380 / r["dz_um"])]
        frames.append(_scale(im, 2, 3))
    lo = float(np.percentile(frames[-1], 40))
    hi = float(np.percentile(frames[-1], 99.8))
    gfr = []
    for f in frames:
        gg = np.clip((f - lo) / (hi - lo), 0, 1)
        gfr.append(np.stack([gg, gg, gg], axis=-1))
    figs.save_gif("dispersion_compensation", gfr,
                  caption="試料腕に溶融石英 12 mm の分散の不一致。補償の係数 a2 を 0 から %.1f µm² まで動かすと、"
                          "PMMA / PC / PS の 3 層の界面がにじみから線に締まる(横 0.6 mm、光路 130〜380 µm)。" % disp["a2"],
                  fps=6.0)


def main():
    t0 = time.time()
    print("PoC 工業用 OCT(予算 %s)" % ("reduced" if REDUCED else "full"))
    design = chapter_design()
    real = chapter_real()
    film = chapter_film()
    proc = chapter_processing()
    art = chapter_artifacts()
    lim = chapter_limits()
    bs = chapter_bscan()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(design, real, film, proc, art, lim, bs)
        make_gif()
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
