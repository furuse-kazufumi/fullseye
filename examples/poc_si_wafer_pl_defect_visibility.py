# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Si ウェハの PL 像で細い溝はなぜ見えなくなるか —— 論文の図を生画像から再現し、拡散 PSF で切り分ける。

フォトルミネッセンス(PL)像は、励起で作った過剰キャリアが**拡散してから**光る。だから像には
光学の PSF のほかに、拡散長 ``L = √(Dτ)`` で決まる**もう 1 つの PSF** が掛かる。細い溝・転位・
粒界が見える/見えないは、この拡散 PSF と**欠陥の種類**で決まる。この PoC は、その見え方を
閉形式の真値と公開実データの両方で採点する。

多段(各段に閉形式の真値か外部実データの門):

1. **生画像の読み込みと論文図の再現**(実データ、外部真値の門): RAW の型・エンディアンを
   値の分布で決め(候補 4 通りを印字)、Figure 4a の挿入図(ヒストグラム、256 区間)を生画像から
   再計算して CSV と一致させる。Figure 6a の線走査(0 min / 1 week)を生画像の行・列から探し、
   相対 RMS で一致を門にする。読めなかった CSV は「使わなかった」と書く。
2. **キャリア拡散の PSF**(合成、閉形式の門): ``pl_diffusion_psf`` の総和 = G·τ、半質量半径
   ∝ L。幅 1〜49 µm の溝を L = 5〜160 µm で描き、**影の溝**(励起・発光の欠け)は
   ``1 − e^{−w/2L}`` で消え、**沈みの溝**(再結合の線)は ``SL/(SL+2D)`` で L と共に深くなる
   ことを ``pl_image_simulate`` の厳密解と照合。CNR = 1 の境界(L*)が閉形式と一致。
3. **HF 処理後の時間変化**(実データ、Figure 6a の同じ溝、0 min / 55 min / 1 week): コントラスト・
   半値幅・雑音を数え、拡散長の推定が 3 本(深さ・幅・PL 水準)で同じ向きかを見る。
4. **埋め込み POD**: 実データの良品域の雑音に合成の溝(影型・沈み型)を埋め、拡散長と雑音の
   違いで a90/95 がどう動くかを ``pod_hitmiss_fit`` で出す。
5. まとめ表(地 = 合成 / 実データ を明記)。

予想(2026-10-13、着手前): ★「同じ溝でも拡散長が長い良質なウェハほど見えなくなる」。
**結果は半分だけ当たった**: それは**影の溝**(励起・発光の欠け)にだけ当てはまる。
**沈みの溝**(再結合活性な欠陥)は逆で、L が長いほど深く・広く見える(供給を上回って吸う)。
実データ(レーザー溝、HF 直後 0 min → 1 week)は沈み型の向き —— 良質なほど溝は目立つ。
予想どおりでない部分もそのまま書く。

実データ(repo には同梱しない。環境変数 ``FULLSEYE_SI_PL_DATA`` に RAW と CSV のある dir を渡す。
無ければ合成のみを走らせ「実データ門は未実行」と明示。CI は合成のみ):

  Sutinen, K., Golovleva, M., Liu, X., Patana, M., Timperi, I., Mustonen, K., Vähänissi, V.,
  Savin, H. (2026). Dataset for "Non-disruptive HF pretreatment to enhance defect visibility in
  silicon wafer manufacturing via photoluminescence imaging". Zenodo.
  DOI 10.5281/zenodo.19603335, CC BY 4.0. 論文は DOI 10.1088/1361-6641/aea702。
  是非クレジットを(CC BY 4.0)。ダウンロード物は信頼しない入力として扱い、RAW・CSV を
  読むだけ(その中のコードは実行しない)。論文本文は手元に無く、各 CSV の意味は record の
  説明文・ヘッダ・図番号からの**推定**である(本文で明記)。

Fullseye 寄与: PL/EL 検査(太陽電池・ウェハ)の検出限界の設計規則 —— 欠陥の種類(影か沈みか)
で拡散長の効く向きが逆。拡散 PSF ``K₀(r/L)`` は蛍光の拡散・ロックインサーモグラフィの熱拡散
(``μ = √(2α/ω)``)にも同形。
"""
from __future__ import annotations

import csv
import io
import os
import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy import signal as sig

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import examplefig as figs                                        # noqa: E402
import plsim as PL                                               # noqa: E402
import pod as POD                                                # noqa: E402

SEED = 11
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"
DATA = os.environ.get("FULLSEYE_SI_PL_DATA", "").strip()
RAW_SHAPE = (1024, 1024)                 #: record.json: 1024 × 1024 px, 32-bit, 4 MB
NOISE_SYN = {"0 min": 0.029, "1 week": 0.011}    #: 合成の地の雑音(実データ不在時の代表値)
L_SYN_PX = {"0 min": 32.0, "1 week": 10.0}       #: 合成の地の拡散長[px](同上、30 µm/px)
CNR_K = 3.0                                      #: 検出しきい値 = 背景 − CNR_K·σ(平滑後)


# --------------------------------------------------------------------------- #
# 実データの読み込み(信頼しない入力: 読むだけ)                                   #
# --------------------------------------------------------------------------- #
def _read_csv(path):
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    return rows[0], rows[1:]


def _col(rows, j):
    return np.array([float(r[j]) if j < len(r) and r[j].strip() else np.nan for r in rows])


def decide_raw_dtype(path):
    """RAW(4 MB、32 bit)の型とエンディアンを**値の分布**で決める。

    候補 4 通り(<f4 / >f4 / <u4 / >u4)で読み、(1) 全て有限 (2) 99 % 以上が整数値(カメラの
    カウント)(3) 中央値が 1e2〜1e6(16 bit カメラのカウントの範囲)の 3 条件を満たす候補を
    選ぶ。該当が 1 つでなければ fail-closed。
    """
    raw = Path(path).read_bytes()
    if len(raw) != 4 * RAW_SHAPE[0] * RAW_SHAPE[1]:
        raise ValueError("RAW のサイズが 1024²×4 でない: %d" % len(raw))
    table, ok = [], []
    for dt in ("<f4", ">f4", "<u4", ">u4"):
        a = np.frombuffer(raw, dtype=dt).astype(np.float64)
        fin = bool(np.isfinite(a).all())
        med = float(np.median(a)) if fin else float("nan")
        intlike = float(np.mean(np.abs(a - np.round(a)) < 1e-6)) if fin else 0.0
        good = fin and intlike >= 0.99 and 1e2 <= med <= 1e6
        table.append((dt, fin, med, intlike, good))
        if good:
            ok.append(dt)
    for dt, fin, med, il, good in table:
        print("     %-4s 有限 %-5s 中央値 %-12.6g 整数値率 %.3f %s"
              % (dt, fin, med, il, "← 採用" if good else ""))
    if len(ok) != 1:
        raise ValueError("RAW の型が一意に決まらない: %r" % ok)
    return ok[0]


def load_raw(path, dtype):
    return np.frombuffer(Path(path).read_bytes(), dtype=dtype).reshape(RAW_SHAPE).astype(np.float64)


def locate_scan(img, y):
    """線走査 y(長さ n)を画像の全行・全列の窓から正規化相互相関で探す。

    返り: (向き, 行/列, 開始位置, 相関, 相対 RMS, 切り出した窓)。FFT 畳み込みで数えるので
    1024² × 2 向きでも 1 秒かからない。
    """
    n = y.size
    yc = (y - y.mean()) / (y.std() + 1e-12)
    best = None
    for axis, name in ((0, "行"), (1, "列")):
        A = img if axis == 0 else img.T
        num = sig.fftconvolve(A, yc[None, ::-1], mode="valid")                 # Σ A·yc
        s1 = sig.fftconvolve(A, np.ones((1, n)), mode="valid")
        s2 = sig.fftconvolve(A * A, np.ones((1, n)), mode="valid")
        var = np.maximum(s2 / n - (s1 / n) ** 2, 1e-12)
        corr = num / (n * np.sqrt(var))
        k = np.unravel_index(int(np.argmax(corr)), corr.shape)
        seg = A[k[0], k[1]:k[1] + n]
        rel = float(np.sqrt(np.mean((seg - y) ** 2)) / y.mean())
        cand = (float(corr[k]), name, int(k[0]), int(k[1]), rel, seg)
        if best is None or cand[0] > best[0]:
            best = cand
    c, name, line, off, rel, seg = best
    return name, line, off, c, rel, seg


def dip_stats(pos_mm, y):
    """線走査の 背景・最小・コントラスト・半値幅[mm]・相対雑音(両端 25 点、1 次トレンド除去)。"""
    tails = np.r_[y[:25], y[-25:]]
    xt = np.r_[pos_mm[:25], pos_mm[-25:]]
    p = np.polyfit(xt, tails, 1)
    bg = float(np.polyval(p, pos_mm[int(np.argmin(y))]))
    mn = float(y.min())
    c = 1.0 - mn / bg
    half = bg - 0.5 * (bg - mn)
    step = float(np.median(np.diff(pos_mm)))
    fwhm = float(np.sum(y < half)) * step
    noise = float(np.std(tails - np.polyval(p, xt)) / bg)
    return bg, mn, c, fwhm, noise


def fit_sink_profile(pos_mm, y):
    """沈み型 ``bg·(1 − A·e^{−|x−x0|/L})`` を最小二乗で当てる(L は格子探索、A と x0 は解析)。"""
    bg, mn, c, fwhm, _ = dip_stats(pos_mm, y)
    x0 = float(pos_mm[int(np.argmin(y))])
    best = None
    for L in np.geomspace(0.03, 3.0, 160):
        e = np.exp(-np.abs(pos_mm - x0) / L)
        # y/bg = 1 − A e  → A = Σ e(1 − y/bg)/Σ e²
        A = float(np.sum(e * (1.0 - y / bg)) / np.sum(e * e))
        res = float(np.sqrt(np.mean((bg * (1.0 - A * e) - y) ** 2)) / bg)
        if best is None or res < best[0]:
            best = (res, L, A)
    return best[1], best[2], best[0]


# --------------------------------------------------------------------------- #
# 段 1: 生画像と論文図の再現(外部真値の門)                                        #
# --------------------------------------------------------------------------- #
def stage1_real():
    print("1) 生画像の読み込みと論文図の再現(外部真値の門、DOI 10.5281/zenodo.19603335、CC BY 4.0)")
    need = ["Figure_4a_PLI_raw_image.raw", "Figure_4a_inset_data.csv", "Figure_6a_data.csv",
            "Figure_6a_0min_raw_image.raw", "Figure_6a_1week_raw_image.raw"]
    if not DATA or not all(os.path.exists(os.path.join(DATA, f)) for f in need):
        print("   実データ門は未実行(FULLSEYE_SI_PL_DATA が未設定/不在)。合成のみ。")
        return None
    out = {}
    print("   RAW の型を値の分布で決める(Figure_4a_PLI_raw_image.raw):")
    dt = decide_raw_dtype(os.path.join(DATA, "Figure_4a_PLI_raw_image.raw"))
    out["dtype"] = dt
    img4a = load_raw(os.path.join(DATA, "Figure_4a_PLI_raw_image.raw"), dt)
    print("   → %s(ビッグエンディアン float32、値は整数のカウント)。中央値 %.0f、範囲 %.0f〜%.0f"
          % (dt, np.median(img4a), img4a.min(), img4a.max()))

    # --- Figure 4a 挿入図: 30000〜39960.938 を 256 区間(CSV のヘッダ: PL count, Count) ---
    hdr, rows = _read_csv(os.path.join(DATA, "Figure_4a_inset_data.csv"))
    x = _col(rows, 0); cnt = _col(rows, 1)
    step_raw = (x[-1] - x[0]) / (x.size - 1)                   # CSV の丸め(39960.938)でわずかにずれる
    step = round(step_raw * 16.0) / 16.0                       # 推定: 刻みは 10000/256 = 39.0625(2 進分数)
    edges = x[0] + step * np.arange(x.size + 1)
    h, _ = np.histogram(img4a, bins=edges)
    l1 = float(np.abs(h - cnt).sum() / cnt.sum())
    print("   Figure 4a 挿入図(ヒストグラム %d 区間、刻み CSV %.6f → 推定 %.4f = 10000/256): 画素数 CSV %d / "
          "生画像 %d、相対 L1 誤差 %.2e、最大差 %d"
          % (x.size, step_raw, step, cnt.sum(), h.sum(), l1, np.abs(h - cnt).max()))
    out["hist_l1"] = l1
    assert l1 < 0.01, "挿入図のヒストグラムが生画像から再現できない: L1 %.3f" % l1

    # --- Figure 6a 線走査(推定: 列 1 = t=0 min、列 3 = t=1 week、位置 mm、刻み 0.03 mm) ---
    hdr, rows = _read_csv(os.path.join(DATA, "Figure_6a_data.csv"))
    pos = _col(rows, 0)
    cols = {"0 min": _col(rows, 1), "55 min": _col(rows, 2), "1 week": _col(rows, 3)}
    ok = np.isfinite(cols["0 min"])
    pos = pos[ok]
    cols = {k: v[ok] for k, v in cols.items()}
    pitch = float(np.median(np.diff(pos)))
    print("   Figure 6a CSV(ヘッダ: %s): %d 点、位置 %.2f〜%.2f mm、刻み %.3f mm"
          % (" | ".join(h.strip() for h in hdr[:4]), pos.size, pos[0], pos[-1], pitch))
    out["pos"] = pos; out["scans"] = cols
    raws = {"0 min": "Figure_6a_0min_raw_image.raw", "1 week": "Figure_6a_1week_raw_image.raw"}
    out["imgs"] = {}
    out["match"] = {}
    for key, fn in raws.items():
        img = load_raw(os.path.join(DATA, fn), dt)
        out["imgs"][key] = img
        name, line, off, c, rel, seg = locate_scan(img, cols[key])
        out["match"][key] = (name, line, off, c, rel)
        print("   %-7s ← %s: %s %d の %d〜%d 画素に一致(相関 %.4f、相対 RMS %.2f %%、"
              "尺度 生/CSV %.4f)" % (key, fn, name, line, off, off + pos.size - 1, c, 100 * rel,
                                   seg.mean() / cols[key].mean()))
        assert rel < 0.02, "%s の線走査が生画像から再現できない: RMS %.3f" % (key, rel)
    print("   → 推定: CSV の 1 点 = 生画像の 1 画素、画素ピッチ %.0f µm(位置の刻みから)。"
          % (1000 * pitch))
    out["pitch_mm"] = pitch

    if not REDUCED:
        for fn, csvf, j, key in (("Figure_6b_90min_raw_image.raw", "Figure_6b_data.csv", 1, "6b 90 min"),
                                 ("Figure_6b_1week_raw_image.raw", "Figure_6b_data.csv", 3, "6b 1 week")):
            if not (os.path.exists(os.path.join(DATA, fn)) and os.path.exists(os.path.join(DATA, csvf))):
                continue
            _h, rws = _read_csv(os.path.join(DATA, csvf))
            y = _col(rws, j); y = y[np.isfinite(y)]
            name, line, off, c, rel, _seg = locate_scan(load_raw(os.path.join(DATA, fn), dt), y)
            verdict = "一致" if rel < 0.02 else ("弱い一致(門にしない)" if c > 0.8 else "見つからず(使わなかった)")
            print("   %-10s ← %s: 最良 %s %d(相関 %.3f、相対 RMS %.1f %%)→ %s"
                  % (key, fn, name, line, c, 100 * rel, verdict))
    print("   使わなかった CSV: Figure_2a/2b/3a/3b/4b/5/S1a/S1b(対応する生画像が無い、または"
          "位置列が無く生画像と突き合わせられない)。")
    return out


# --------------------------------------------------------------------------- #
# 段 2: キャリア拡散の PSF(合成、閉形式の門)                                       #
# --------------------------------------------------------------------------- #
WIDTHS_UM = (1, 3, 5, 9, 15, 25, 49)
LS_UM = (5, 10, 20, 40, 80, 160)
S_PER_UM = 0.02           #: 段 2 の沈み型の溝の再結合速度(s = S·px/D、幅 1 µm あたり、画素 1 µm)
S_PER_UM_POD = 0.002      #: 段 4(画素 30 µm)の沈み型。κ = s·w·L² が µm 幅で数 % のコントラストになる値
NOISE2 = 0.01             #: 段 2 の像の雑音(地 1 に対して 1 %)


def stage2_synthetic():
    print("\n2) キャリア拡散の PSF(合成、画素 = 1 µm、閉形式の門)")
    k = PL.pl_diffusion_psf(20.0)
    c = k.shape[0] // 2
    yy, xx = np.mgrid[-c:c + 1, -c:c + 1]
    r = np.hypot(xx, yy)
    rh = {}
    for L in (10.0, 20.0):
        kk = PL.pl_diffusion_psf(L); cc = kk.shape[0] // 2
        y2, x2 = np.mgrid[-cc:cc + 1, -cc:cc + 1]; rr = np.hypot(x2, y2)
        cum = np.array([kk[rr <= R].sum() for R in np.arange(0.5, 3 * L, 0.5)])
        rh[L] = float(np.arange(0.5, 3 * L, 0.5)[np.argmax(cum >= 0.5)])
    print("   pl_diffusion_psf(L=20): 総和 %.5f(真値 1 = G·τ)、半質量半径 L=10 → %.1f px、"
          "L=20 → %.1f px(真値 1.2572·L)" % (k.sum(), rh[10.0], rh[20.0]))
    assert 0.99 < k.sum() <= 1.0 + 1e-9
    assert abs(rh[20.0] / rh[10.0] - 2.0) < 0.12

    print("   影の溝(励起の欠け)と沈みの溝(再結合の線)の中心コントラスト[%]: 厳密解 / 閉形式")
    print("   %-8s" % "w[µm]" + "".join("%12s" % ("L=%d" % L) for L in LS_UM))
    err_grid = err_cont = 0.0
    table = {"shadow": {}, "sink": {}}
    for w in WIDTHS_UM:
        line_sh, line_sk = [], []
        for L in LS_UM:
            W = int(max(401, 24 * L)) | 1
            cx = W // 2; m = (w - 1) // 2
            g = np.ones((1, W)); g[0, cx - m:cx + m + 1] = 0.0
            u = PL.pl_image_simulate(g, diffusion_length_px=float(L))
            t = PL.pl_groove_visibility(float(w), float(L), sink_velocity=S_PER_UM * w, noise_rel=NOISE2)
            c_sh = 1.0 - float(u[0, cx])
            err_grid = max(err_grid, abs(c_sh - t["contrast_shadow_grid"]))
            if L >= 10:
                err_cont = max(err_cont, abs(c_sh / t["contrast_shadow"] - 1.0))
            kmap = np.zeros((1, W)); kmap[0, cx - m:cx + m + 1] = S_PER_UM * w * L * L / w
            us = PL.pl_image_simulate(np.ones((1, W)), kmap, diffusion_length_px=float(L))
            c_sk = 1.0 - float(us[0, cx])
            table["shadow"][(w, L)] = (c_sh, t["contrast_shadow"])
            table["sink"][(w, L)] = (c_sk, t["contrast_sink"])
            line_sh.append("%5.1f/%5.1f" % (100 * c_sh, 100 * t["contrast_shadow"]))
            line_sk.append("%5.1f/%5.1f" % (100 * c_sk, 100 * t["contrast_sink"]))
        print("   影 %-5d" % w + "".join("%12s" % s for s in line_sh))
        print("   沈み %-3d" % w + "".join("%12s" % s for s in line_sk))
    sink_err = max(abs(a / b - 1.0) for (w, L), (a, b) in table["sink"].items() if w / L <= 0.16)
    wide = abs(table["sink"][(49, 5)][0] / table["sink"][(49, 5)][1] - 1.0)
    print("   → 影: 格子の閉形式との最大差 %.1e(厳密)、連続 1−e^(−w/2L) との最大相対差 %.1f %%"
          "(L ≥ 10)。沈み: Donolato 型 SL/(SL+2D)(線の近似)との最大相対差 %.1f %%(w/L ≤ 0.16)。"
          "線の近似は w ≪ L でだけ効く(w=49, L=5 では %.0f %% ずれる —— 幅の中で供給が尽きる)。"
          % (err_grid, 100 * err_cont, 100 * sink_err, 100 * wide))
    assert err_grid < 1e-8 and err_cont < 0.03 and sink_err < 0.04

    # 見える/見えない(CNR ≥ 1、雑音 1 %)の境界が閉形式の L* と一致するか
    print("   見える(CNR ≥ 1、雑音 %.0f %%)= ●、見えない = ·:   影 | 沈み" % (100 * NOISE2))
    flips_ok = True
    for w in WIDTHS_UM:
        t = PL.pl_groove_visibility(float(w), 10.0, sink_velocity=S_PER_UM * w, noise_rel=NOISE2)
        row_sh = "".join("●" if table["shadow"][(w, L)][0] >= NOISE2 else "·" for L in LS_UM)
        row_sk = "".join("●" if table["sink"][(w, L)][0] >= NOISE2 else "·" for L in LS_UM)
        pred_sh = "".join("●" if L <= t["L_star_shadow_px"] else "·" for L in LS_UM)
        pred_sk = "".join("●" if L >= t["L_star_sink_px"] else "·" for L in LS_UM)
        flips_ok &= (row_sh == pred_sh) and (row_sk == pred_sk)
        print("   w=%-3d µm  %s | %s   (閉形式 L*: 影 %.0f µm より長いと消える / 沈み %.1f µm より短いと消える)"
              % (w, row_sh, row_sk, t["L_star_shadow_px"], t["L_star_sink_px"]))
    assert flips_ok, "見える/見えないの境界が閉形式の L* と食い違う"
    ratio = table["shadow"][(5, 160)][0] / table["shadow"][(5, 20)][0]
    print("   → ★影の溝(w=5 µm)は L を 20 → 160 µm にすると %.1f %% → %.1f %%(%.2f 倍)に消え、"
          "沈みの溝は %.1f %% → %.1f %% に**深くなる**。拡散長が長い良質なウェハほど隠れるのは"
          "影だけ —— 再結合活性な欠陥はむしろ目立つ。"
          % (100 * table["shadow"][(5, 20)][0], 100 * table["shadow"][(5, 160)][0], ratio,
             100 * table["sink"][(5, 20)][0], 100 * table["sink"][(5, 160)][0]))
    assert ratio < 0.2 and table["sink"][(5, 160)][0] > table["sink"][(5, 20)][0]
    return table, err_grid, err_cont, sink_err


# --------------------------------------------------------------------------- #
# 段 3: HF 処理後の時間変化(実データ、Figure 6a の同じ溝)                          #
# --------------------------------------------------------------------------- #
def stage3_real(real):
    print("\n3) HF 処理後の時間変化(実データ、Figure 6a: 220 µm 深・裏面の同じ溝、0 min / 55 min / 1 week)")
    pos = real["pos"]
    res = {}
    print("   %-8s %9s %9s %8s %9s %8s %9s %7s" %
          ("時刻", "背景[cnt]", "最小[cnt]", "深さ[%]", "半値幅[mm]", "雑音[%]", "L推定[mm]", "A当て"))
    for key in ("0 min", "55 min", "1 week"):
        y = real["scans"][key]
        bg, mn, c, fwhm, noise = dip_stats(pos, y)
        Lmm, A, rms = fit_sink_profile(pos, y)
        res[key] = dict(bg=bg, mn=mn, c=c, fwhm=fwhm, noise=noise, L=Lmm, A=A, rms=rms)
        print("   %-8s %9.0f %9.0f %8.1f %9.2f %8.1f %9.2f %7.2f" %
              (key, bg, mn, 100 * c, fwhm, 100 * noise, Lmm, A))
    c0, c1 = res["0 min"]["c"], res["1 week"]["c"]
    f0, f1 = res["0 min"]["fwhm"], res["1 week"]["fwhm"]
    L0, L1 = res["0 min"]["L"], res["1 week"]["L"]
    print("   拡散長の比 L(0 min)/L(1 week) を 3 本で: 深さ(沈み型 SL/(SL+2D)) %.2f、半値幅 %.2f、"
          "当てた L %.2f。PL 水準の比 %.2f(√ は %.2f)—— 55 min は水準が最低(%.0f)なのに深さ・幅は中間で、"
          "**水準は拡散長の代理にならない**。"
          % ((c0 / (1 - c0)) / (c1 / (1 - c1)), f0 / f1, L0 / L1,
             res["0 min"]["bg"] / res["1 week"]["bg"], np.sqrt(res["0 min"]["bg"] / res["1 week"]["bg"]),
             res["55 min"]["bg"]))
    kind = "沈み型(L が長いほど深く・広い)" if (c0 > c1 and f0 > f1) else \
           ("影型(L が長いほど浅い)" if (c0 < c1 and f0 > f1) else "どちらとも言えない")
    print("   → ★HF 直後(0 min)は 1 week 後より溝が**深く(%.1f → %.1f %%)広い(%.2f → %.2f mm)**: %s。"
          "予想「良質なほど隠れる」は実データでは**逆**。" % (100 * c0, 100 * c1, f0, f1, kind))
    assert kind.startswith("沈み型"), "実データの溝が沈み型の向きでない: " + kind
    return res


# --------------------------------------------------------------------------- #
# 段 4: 埋め込み POD                                                             #
# --------------------------------------------------------------------------- #
PATCH = (48, 640)         #: 地の切り出し(行 × 列)。溝は列方向に幅 w で縦に走る(行平均で横顔にする)


def real_backgrounds(img, n=8):
    """溝の無い平らな領域を PATCH 大で n 枚拾う(相対 σ が小さく、暗い画素を含まない窓)。"""
    H, W = PATCH
    cands = []
    for r0 in range(0, img.shape[0] - H, 16):
        for c0 in range(0, img.shape[1] - W, 32):
            p = img[r0:r0 + H, c0:c0 + W]
            med = np.median(p)
            if med <= 0 or p.min() < 0.85 * med:
                continue
            cands.append((float(p.std() / med), r0, c0))
    cands.sort()
    out = []
    for _s, r0, c0 in cands[:n]:
        p = img[r0:r0 + H, c0:c0 + W]
        out.append(p / p.mean())
    return out


def synthetic_backgrounds(noise, n=8):
    rng = np.random.default_rng(SEED + int(1000 * noise))
    return [1.0 + rng.normal(0.0, noise, PATCH) for _ in range(n)]


def _coverage(W, cx, w_px):
    """列 cx を中心に幅 w_px の帯が各画素を覆う割合(0〜1、面積で厳密)。"""
    x = np.arange(W, dtype=np.float64)
    lo, hi = cx - 0.5 * w_px, cx + 0.5 * w_px
    return np.clip(np.minimum(x + 0.5, hi) - np.maximum(x - 0.5, lo), 0.0, 1.0)


def _detect(bg, L_px, w_um, kind, pitch_um, cx):
    """地 bg に幅 w_um[µm]の溝(影型/沈み型)を列 cx に埋めて、平滑した横顔のへこみで検出。

    判定は**像だけから**: 行平均 → 箱(= 沈みの半値幅 2L·ln2)で平滑 → 溝の窓(±3 箱)を除いた
    点で 1 次トレンドを引き、残差の頑健 σ の ``CNR_K`` 倍より深ければ hit。``w_um = 0`` は
    溝なし(空振り率の測定)。
    """
    H, W = bg.shape
    w_px = w_um / pitch_um
    cov = _coverage(W, cx, w_px) if w_px > 0 else np.zeros(W)
    g = np.ones((1, W)); kmap = np.zeros((1, W))
    if kind == "shadow":
        g[0] = 1.0 - cov
    elif cov.sum() > 0:
        kmap[0] = S_PER_UM_POD * w_um * L_px * L_px * cov / cov.sum()   # κ = s·w·L² を帯に配る
    u = PL.pl_image_simulate(g, kmap, diffusion_length_px=L_px)[0]
    box = max(1, int(round(2 * L_px * np.log(2))))
    img = bg * u[None, :]
    prof = ndi.uniform_filter1d(img.mean(axis=0), box, mode="nearest")
    x = np.arange(W)
    far = np.ones(W, bool); far[max(0, cx - 3 * box):cx + 3 * box + 1] = False
    if far.sum() < 16:
        far[:] = True
    p = np.polyfit(x[far], prof[far], 1)
    resid = prof - np.polyval(p, x)
    sigma = float(np.median(np.abs(resid[far] - np.median(resid[far]))) * 1.4826) + 1e-9
    return (-float(resid[cx])) > CNR_K * sigma


def _white_noise_a90(bgs, L_px, kind, pitch_um):
    """地が白色雑音ならどこまで小さい溝で閾値に届くか(閉形式、参考): 同じ検出器・同じ閾値。"""
    sig_pix = float(np.median([np.median(np.abs(b - np.median(b))) * 1.4826 for b in bgs]))
    box = max(1, int(round(2 * L_px * np.log(2))))
    sig_w = sig_pix / np.sqrt(PATCH[0] * box)                     # 行平均と箱平滑で落ちる
    f = (2 * L_px / box) * (1.0 - np.exp(-box / (2 * L_px)))         # 箱の中の横顔 e^{−|x|/L} の平均
    c_star = CNR_K * sig_w / f
    if c_star >= 1.0:
        return float("inf")
    if kind == "shadow":
        return float(-2 * L_px * np.log(1.0 - c_star) * pitch_um)
    kappa = 2 * L_px * c_star / (1.0 - c_star)
    return float(kappa / (S_PER_UM_POD * L_px * L_px))


def stage4_pod(bgs, L_px, label, pitch_um):
    print("\n4) 埋め込み POD(地 = %s、L = %.1f px = %.2f mm、%d 枚 %d×%d)"
          % (label, L_px, L_px * pitch_um / 1000, len(bgs), PATCH[0], PATCH[1]))
    rng = np.random.default_rng(SEED)
    reps = 10 if REDUCED else 24
    out = {}
    for kind in ("shadow", "sink"):
        # 幅の範囲は型ごと(影は画素 30 µm を跨ぐ幅まで、沈みは κ = s·w·L² が効く幅)
        sizes_um = np.geomspace(0.3, 300.0, 14) if kind == "shadow" else np.geomspace(0.01, 30.0, 14)
        a, hit, rate = [], [], []
        fa = 0
        for _ in range(reps):
            bg = bgs[rng.integers(len(bgs))]
            cx = int(rng.integers(PATCH[1] // 4, 3 * PATCH[1] // 4))
            fa += _detect(bg, L_px, 0.0, kind, pitch_um, cx)
        for w in sizes_um:
            got = 0
            for _ in range(reps):
                bg = bgs[rng.integers(len(bgs))]
                cx = int(rng.integers(PATCH[1] // 4, 3 * PATCH[1] // 4))
                h = _detect(bg, L_px, float(w), kind, pitch_um, cx)
                a.append(float(w)); hit.append(int(h)); got += h
            rate.append(got / reps)
        a90 = a9095 = float("nan"); note = ""
        try:
            fit = POD.pod_hitmiss_fit({"a": np.array(a), "hit": np.array(hit)}, log_size=True)
            a90, a9095 = float(fit["a90"]), float(fit["a90_95"])
            if fit.get("a90_95_beyond_data"):
                note = "(a90/95 は試した最大 %.0f µm の外 = 外挿)" % sizes_um[-1]
        except ValueError as ex:
            note = "(POD 当ては立たず: %s)" % str(ex).split(" — ")[0][:60]
            idx = next((i for i, r in enumerate(rate) if r >= 0.9), None)
            a90 = float(sizes_um[idx]) if idx is not None else float("nan")
        wn = _white_noise_a90(bgs, L_px, kind, pitch_um)
        out[kind] = (a90, a9095, rate, wn, fa / reps)
        print("   %-6s 空振り(溝なし)%.2f  検出率: %s" % ("影型" if kind == "shadow" else "沈み型", fa / reps,
              " ".join("%.2g:%.2f" % (w, r) for w, r in zip(sizes_um, rate))))
        print("          a90 %.3g µm / a90/95 %.3g µm %s  白色雑音なら閾値到達 %.3g µm(実地は %.1f 倍甘い)"
              % (a90, a9095, note, wn, a90 / wn if wn > 0 else float("nan")))
    return out


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def make_figures(real, res3):
    """図は ``FULLSEYE_FIGURE_DIR`` があるときだけ書く(既定の走行は図なしで 60 秒未満)。"""
    n = 0
    panels, caps = [], []
    for kind in ("影", "沈み"):
        for L in (4.0, 16.0, 64.0):
            # 帯の幅は最長の L の 4.5 倍(288 µm)。96 µm の箱では L = 64 µm の沈みが Neumann 境界の
            # 箱ごと吸って全面が黒くなる(1 次元の閉形式でも端は 1 − A e^{−144/64} ≈ 0.91 まで戻る)。
            H, W = 96, 288; cx = W // 2
            g = np.ones((H, W)); kmap = np.zeros((H, W))
            if kind == "影":
                g[:, cx - 1:cx + 2] = 0.0
            else:
                kmap[:, cx - 1:cx + 2] = S_PER_UM * 3 * L * L / 3
            u = PL.pl_image_simulate(g, kmap, diffusion_length_px=L, noise_rel=0.01, seed=1)
            panels.append(u); caps.append("%sの溝 w=3 µm, L=%d µm" % (kind, int(L)))
    assert all(np.isfinite(u).all() and 0.3 < float(np.median(u)) < 1.2 for u in panels), "帯の中央値が地から外れた"
    figs.save_grid("pl_groove_vs_diffusion_length", panels, captions=caps, ncols=3, gray=True,
                   vrange=(0.6, 1.05), title="同じ幅 3 µm の溝: 影は L と共に消え、沈みは深く広くなる(PL 像、1 px = 1 µm)",
                   caption="同じ幅 3 µm の溝を拡散長 L = 4 / 16 / 64 µm で描いた PL 像(雑音 1 %)。"
                           "上段 = 影の溝(励起の欠け): L が長いほど拡散が埋めて消える。"
                           "下段 = 沈みの溝(再結合の線): L が長いほど深く・広く見える。"
                           "良質なウェハで隠れるのは影だけ。")
    n += 1
    Ls = np.geomspace(3, 300, 40)
    sh = [100 * PL.pl_groove_visibility(5.0, float(L))["contrast_shadow"] for L in Ls]
    sk = [100 * PL.pl_groove_visibility(5.0, float(L), sink_velocity=S_PER_UM * 5)["contrast_sink"] for L in Ls]
    figs.save_plot("pl_contrast_vs_diffusion_length",
                   [("影の溝 1−exp(−w/2L)", Ls, sh), ("沈みの溝 SL/(SL+2D)", Ls, sk),
                    ("雑音 1 %(CNR = 1)", Ls, [1.0] * len(Ls))],
                   xlabel="拡散長 L [µm]", ylabel="中心のコントラスト [%]",
                   title="幅 5 µm の溝の中心コントラスト対拡散長(閉形式): 影と沈みは逆向き",
                   styles=[None, None, "dashed"], colors=["wrong", "right", "reference"],
                   caption="幅 5 µm の溝の中心コントラスト対拡散長(閉形式)。影は L と共に消え、"
                           "沈みは L と共に深くなる。雑音 1 % の線を切る L が見える/見えないの境界。")
    n += 1
    if real is not None and res3 is not None:
        pos = real["pos"]
        series = []
        for key in ("0 min", "55 min", "1 week"):
            y = real["scans"][key]
            series.append(("t = %s(深さ %.0f %%、半値幅 %.2f mm)" % (key, 100 * res3[key]["c"], res3[key]["fwhm"]),
                           pos, y / res3[key]["bg"]))
        figs.save_plot("pl_real_groove_after_hf", series, xlabel="位置 [mm]", ylabel="PL / 背景",
                       title="実データ(Figure 6a): 同じ溝が HF 直後ほど深く広い = 沈み型",
                       caption="公開実データ(Sutinen ほか 2026、Zenodo 10.5281/zenodo.19603335、CC BY 4.0)"
                               "の Figure 6a: 同じ 220 µm 深の溝を HF 処理後 0 min / 55 min / 1 week に走査した"
                               "線(背景で割った)。HF 直後ほど深く広い —— 沈み型の向き。")
        n += 1
    return n


# --------------------------------------------------------------------------- #
def main():
    t0 = time.perf_counter()
    print("Si ウェハの PL 像: 細い溝はなぜ見えなくなるか(拡散 PSF と欠陥の種類)")
    print("=" * 68)
    t_r0 = time.perf_counter()
    real = stage1_real()
    t_real = time.perf_counter() - t_r0

    t_s0 = time.perf_counter()
    table, err_grid, err_cont, sink_err = stage2_synthetic()
    t_syn = time.perf_counter() - t_s0

    t_r0 = time.perf_counter()
    res3 = stage3_real(real) if real is not None else None
    t_real += time.perf_counter() - t_r0

    # --- 段 4: 埋め込み POD(地は実データの良品域、無ければ合成) ---
    t_p0 = time.perf_counter()
    pod = {}
    pitch_um = 1000 * real["pitch_mm"] if real is not None else 30.0
    for key in ("0 min", "1 week"):
        if real is not None:
            bgs = real_backgrounds(real["imgs"][key])
            L_px = res3[key]["L"] / real["pitch_mm"]
            label = "実データ良品域 %s" % key
        else:
            bgs = synthetic_backgrounds(NOISE_SYN[key])
            L_px = L_SYN_PX[key]
            label = "合成の雑音地(%s 相当 σ=%.1f %%)" % (key, 100 * NOISE_SYN[key])
        pod[key] = (label, L_px, stage4_pod(bgs, L_px, label, pitch_um))
    t_pod = time.perf_counter() - t_p0

    nfig = make_figures(real, res3)
    if figs.errors():
        print("   図の書き出しで失敗:", "; ".join(figs.errors()))
    elif figs.enabled():
        print("   図 %d 枚を書き出した。" % nfig)

    # --- 段 5: まとめ ---
    print("\n5) まとめ(地を明記)")
    print("   合成: 拡散 PSF 総和 1、影の溝は格子閉形式と %.0e で一致・連続形と %.1f %% 以内、"
          "沈みは Donolato 型と %.1f %% 以内。影 w=5 µm は L 20→160 µm で %.1f→%.1f %%、沈みは %.1f→%.1f %%。"
          % (err_grid, 100 * err_cont, 100 * sink_err,
             100 * table["shadow"][(5, 20)][0], 100 * table["shadow"][(5, 160)][0],
             100 * table["sink"][(5, 20)][0], 100 * table["sink"][(5, 160)][0]))
    if real is not None:
        print("   実データ: RAW = %s、Figure 4a 挿入図の再現 L1 %.1e、Figure 6a 線走査 0 min RMS %.2f %% / "
              "1 week RMS %.2f %%。HF 後 0 min → 1 week: 深さ %.1f → %.1f %%、半値幅 %.2f → %.2f mm、"
              "L 推定 %.2f → %.2f mm(沈み型)。"
              % (real["dtype"], real["hist_l1"], 100 * real["match"]["0 min"][4],
                 100 * real["match"]["1 week"][4], 100 * res3["0 min"]["c"], 100 * res3["1 week"]["c"],
                 res3["0 min"]["fwhm"], res3["1 week"]["fwhm"], res3["0 min"]["L"], res3["1 week"]["L"]))
    else:
        print("   実データ門は未実行(合成のみ)。")
    for key in ("0 min", "1 week"):
        label, L_px, p = pod[key]
        print("   POD(地 = %s、L = %.1f px): 影型 a90/95 %.3g µm、沈み型 a90/95 %.3g µm、"
              "空振り %.2f / %.2f、白色雑音比 %.0f / %.0f 倍"
              % (label, L_px, p["shadow"][1], p["sink"][1], p["shadow"][4], p["sink"][4],
                 p["shadow"][0] / p["shadow"][3], p["sink"][0] / p["sink"][3]))
    sh0, sh1 = pod["0 min"][2]["shadow"][0], pod["1 week"][2]["shadow"][0]
    sk0, sk1 = pod["0 min"][2]["sink"][0], pod["1 week"][2]["sink"][0]
    wn_ratio = [pod[k][2][t][0] / pod[k][2][t][3] for k in ("0 min", "1 week") for t in ("shadow", "sink")
                if pod[k][2][t][3] > 0 and np.isfinite(pod[k][2][t][0])]
    print("   → ★同じ地の作法で、拡散長の長い 0 min 側は**影型の a90 が %.1f 倍大きく(隠れる)、沈み型の a90 が "
          "%.2f 倍(目立つ)**。a90 は白色雑音の閉形式の %.0f〜%.0f 倍%s"
          % (sh0 / sh1, sk0 / sk1, min(wn_ratio), max(wn_ratio),
             "(1 桁以上甘い —— 限界を決めるのは雑音でなく地の構造)。" if min(wn_ratio) >= 10
             else "(白色の地では閉形式に近い。実データの地では 1 桁以上甘くなる)。"))
    assert sh0 > sh1, "影型: 拡散長の長い側で a90 が大きくならない: %.3g vs %.3g" % (sh0, sh1)
    assert sk0 < sk1, "沈み型: 拡散長の長い側で a90 が小さくならない: %.3g vs %.3g" % (sk0, sk1)
    print("   所要: 実データ段 %.2f 秒 / 合成段 %.2f 秒 / POD %.2f 秒 / 合計 %.2f 秒"
          % (t_real, t_syn, t_pod, time.perf_counter() - t0))

    print("\nPASS: 拡散 PSF は総和 1・半質量半径 ∝ L。影の溝は 1−e^(−w/2L) で消え(格子閉形式と %.0e)、"
          "沈みの溝は SL/(SL+2D) で L と共に深くなる(%.1f %% 以内)。%s"
          % (err_grid, 100 * sink_err,
             ("実データ門も通過(RAW 型 %s、Figure 4a 挿入図 L1 %.0e、6a 線走査 RMS ≤ %.1f %%、"
              "HF 直後ほど溝が深く広い = 沈み型)。"
              % (real["dtype"], real["hist_l1"],
                 100 * max(real["match"]["0 min"][4], real["match"]["1 week"][4]))
              if real is not None else "実データ門は未実行(合成のみ)。")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
