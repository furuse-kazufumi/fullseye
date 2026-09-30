# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC ㉖: 読みの誤差がラリーを終わらせる —— 知覚の雑音と遅れが着地点をどれだけ動かすかを、打つ前に閉形式で出す。

卓球ロボットは「球がどこにあるか」を読んでから、相手コートの狙った点へ落ちる打球を計算して打つ。読みが δ だけずれて
いれば、打球は **ずれた位置から** 狙った計算のまま **本当の位置から** 飛び出すので、着地点がずれる。ずれが台の縁までの
余白を越えるとアウトになり、ラリーが終わる。この PoC は「読みの誤差 → 着地点の誤差」の伝わり方(ヤコビアン J)を
打つ前に出し、雑音・遅れ・ラリーの本数がそれで説明できるかを確かめる。

門(真値の出どころ):
  1. **真空の閉形式**: 読んだ位置 p̂ = p + δ から時間 T で狙って本当の p から打つと、着地点のずれは
     ΔL_xy = −δ_xy − (v_xy / |v_z(T)|) δ_z(高さの読み違いは落ちる角の分だけ前後に増える)。狙い・ラケットの計画・衝突・飛翔を
     通した数値の J がこれと 1e-4 で一致。
  2. **一次の誤差伝播**(抗力 + マグヌスあり): 位置の雑音 σ の読みで打った 300 本の着地点のばらつきが、J Σ Jᵀ の予測と 10 % 以内。
  3. **アウトの確率**: 台の縁から 6 cm の点を σ = 3 cm の読みで狙うとき、ガウスの予測(J Σ Jᵀ)から出すアウトの確率が、
     実際に打った 300 本のアウトの割合と二項分布の 3σ 以内。★雑音が大きい側(縁から 12 cm・σ = 5 cm)も参考に出すが、300 本では
     一次の近似が裾を軽く見るのか重く見るのかは決まらない(乱数を変えると差の向きが入れ替わった: 2026-10-01)。
  4. **遅れ**: τ だけ古い読み(p(t − τ) = p − vτ − ½gτ² ẑ、g = 9.81 m/s²)で打つと、着地点のずれは J · (−vτ − ½gτ² ẑ) と 5 % 以内。
  5. **閉ループ**: 雑音 0 の送り合いは上限まで続き、アウトしない雑音の上限(J から出す)を越えるとラリーが途切れる。
  6. **零点**: 誤差 0 なら狙った点に 1 mm 以内で落ちる。

正直に書くこと: 読みの誤差は球の位置だけ(速度・回転は真値)、毎コマ独立のガウス。ラケットの面の向き・速さは計画どおりに
出せる(制御の誤差は無い)。台の縁の余白だけでアウトを判定し、ネットは狙いが遠いので考えない。

Run: py -3.11 examples/poc_table_tennis_rally_loop.py   (図は FULLSEYE_FIGURE_DIR を設定したときだけ書く。MP4 は extras [video] があるときだけ)
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import ballistics as B  # noqa: E402
import ballworld as BW  # noqa: E402
import racket as RK  # noqa: E402
import annotate as AN  # noqa: E402

T0 = time.time()
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
N_MC = 150 if REDUCED else 300          # モンテカルロの本数
T_FLIGHT = 0.42
OK = []


def gate(name, cond, detail=""):
    OK.append(bool(cond))
    print("  [%s] %s %s" % ("PASS" if cond else "FAIL", name, detail))


class Shot:
    """1 本の打球: 真の球の状態 (p, v_in, ω_in) を読み違えた p̂ = p + δ から狙って、本当の p から打つ。"""

    def __init__(self, bp, tp, rp, ip, p, v_in, w_in, target, T=T_FLIGHT):
        self.bp, self.tp, self.rp, self.ip = bp, tp, rp, ip
        self.p, self.v_in, self.w_in = np.asarray(p, float), np.asarray(v_in, float), np.asarray(w_in, float)
        self.target, self.T = np.asarray(target, float), T

    def fly(self, delta):
        ph = self.p + np.asarray(delta, float)
        wg = np.zeros(3)
        for _ in range(3):                                   # 打球後の回転を込みで狙いを合わせる(rally_simulate と同じ)
            aim = RK.aim_velocity(ph, self.target, self.T, self.bp, wg)
            pl = RK.racket_plan(self.v_in, self.w_in, aim["v"], self.bp, self.rp)
            wg = pl["omega_out"]
        b = RK.racket_impact(self.v_in, self.w_in, pl["normal"], pl["v_racket"], self.bp, self.rp)
        # 使うのは最初の着地だけ: T + 0.2 s で打ち切る(読みが 15 cm 狂っても着地は 0.06 s しか動かない)。
        # 刻みは同じなので、最初の接触までは 1.2 s 回したときとビット一致(時間は 1/2 以下)。
        s = B.flight_simulate(self.p, b["v"], b["omega"], self.bp, self.ip, self.T + 0.2, 2e-4, table_z=self.tp["height"])
        if not s["contacts"]:
            raise RuntimeError("T + 0.2 s までに台に落ちなかった(読みの誤差が大きすぎる)")
        c = s["contacts"][0]
        return {"L": c["p"][:2], "v_out": b["v"], "sim": s, "aim": aim["v"]}

    def jacobian(self, h=1e-3):
        return np.column_stack([(self.fly(h * e)["L"] - self.fly(-h * e)["L"]) / (2 * h) for e in np.eye(3)])


def p_out_gaussian(mean, cov, box, n=200_000, seed=0):
    """2 次元ガウス N(mean, cov) が箱 box = (xmin, xmax, ymin, ymax) の外に出る確率(標本 n で数値積分)。"""
    z = np.random.default_rng(seed).multivariate_normal(mean, cov, size=n)
    inside = (z[:, 0] > box[0]) & (z[:, 0] < box[1]) & (z[:, 1] > box[2]) & (z[:, 1] < box[3])
    return 1.0 - inside.mean()


def main() -> int:
    """PoC の本体(examples の門: 実行は __main__ の守りの下で)。"""
    print("BUDGET: %s(FULLSEYE_POC_BUDGET、CI では reduced が既定。展示の数字は full)" % ("reduced" if REDUCED else "full"))
    tp = BW.table_params()
    H = tp["height"]
    rp = RK.racket_params()
    ip = B.impact_params(0.9, 0.25)
    bp = B.ball_params()
    L_half, W_half = 0.5 * tp["length"], 0.5 * tp["width"]
    box = (0.0, L_half, -W_half, W_half)                          # 相手コート(x > 0)
    p = np.array([-1.55, 0.1, H + 0.25])                           # 打つ瞬間の球(こちらのコートの外、台の高さ + 25 cm)
    v_in = np.array([-4.0, 0.2, -0.5])
    w_in = np.array([0.0, -50.0, 0.0])

    # ─────────────────────────────── 1. 真空の閉形式 ─────────────────────────────
    print("== 1. 真空の閉形式: ΔL_xy = −δ_xy − (v_xy / |v_z(T)|) δ_z")
    tgt_c = np.array([0.75, 0.3, H + 0.02])
    sv = Shot(B.ball_params(rho=0.0), tp, rp, ip, p, v_in, w_in, tgt_c)
    f0 = sv.fly(np.zeros(3))
    Jv = sv.jacobian()
    vz_T = f0["v_out"][2] - 9.81 * T_FLIGHT
    Jc = np.array([[-1.0, 0.0, -f0["v_out"][0] / abs(vz_T)], [0.0, -1.0, -f0["v_out"][1] / abs(vz_T)]])
    err_v = float(np.abs(Jv - Jc).max())
    print("  打球 v = %s m/s、T 秒後の v_z = %.2f m/s → 高さの読み違い 1 cm で前後に %.1f cm" % (np.round(f0["v_out"], 2), vz_T, abs(Jc[0, 2])))
    print("  数値の J = %s、閉形式 = %s、差 %.1e" % (np.round(Jv, 4).tolist(), np.round(Jc, 4).tolist(), err_v))
    gate("真空の閉形式 = 狙い・計画・衝突・飛翔を通した J(1e-4)", err_v < 1e-4)

    # ─────────────────────────────── 2. 一次の誤差伝播 ─────────────────────────────
    print("== 2. 抗力 + マグヌスあり: 位置の雑音 σ の読みで %d 本打つ → 着地点のばらつき vs J Σ Jᵀ" % N_MC)
    sa = Shot(bp, tp, rp, ip, p, v_in, w_in, tgt_c)
    Ja = sa.jacobian()
    L0 = sa.fly(np.zeros(3))["L"]
    zero_err = float(np.linalg.norm(L0 - tgt_c[:2]))
    sig = 0.02
    cov_pred = Ja @ (sig ** 2 * np.eye(3)) @ Ja.T
    rng = np.random.default_rng(26)
    t_mc = time.time()
    Ls = np.array([sa.fly(rng.normal(0.0, sig, 3))["L"] for _ in range(N_MC)])
    sd_mc, sd_pr = Ls.std(axis=0, ddof=1), np.sqrt(np.diag(cov_pred))
    rel = np.abs(sd_mc / sd_pr - 1)
    print("  J(空気あり)= %s(真空の %.2f に対し前後の増幅 %.2f)" % (np.round(Ja, 3).tolist(), abs(Jc[0, 2]), abs(Ja[0, 2])))
    print("  σ = %.0f mm: 着地点のばらつき 実測 (x %.1f, y %.1f) cm、予測 (x %.1f, y %.1f) cm、差 %s %%(%d 本、%.1f s)" % (
        1e3 * sig, 100 * sd_mc[0], 100 * sd_mc[1], 100 * sd_pr[0], 100 * sd_pr[1], np.round(100 * rel, 1).tolist(), N_MC, time.time() - t_mc))
    gate("一次の誤差伝播: ばらつきが J Σ Jᵀ と 10 % 以内", rel.max() < 0.10)

    # ─────────────────────────────── 3. アウトの確率 ─────────────────────────────
    print("== 3. 台の縁から 6 cm の点を狙うとアウトはどれだけ出るか(ガウスの予測 vs 打った本数)")
    tgt_e = np.array([0.75, W_half - 0.06, H + 0.02])
    se = Shot(bp, tp, rp, ip, p, v_in, w_in, tgt_e)
    Je = se.jacobian()
    Le0 = se.fly(np.zeros(3))["L"]
    sig_e = 0.03
    P_pred = p_out_gaussian(Le0, Je @ (sig_e ** 2 * np.eye(3)) @ Je.T, box)
    Le = np.array([se.fly(rng.normal(0.0, sig_e, 3))["L"] for _ in range(N_MC)])
    out = ~((Le[:, 0] > box[0]) & (Le[:, 0] < box[1]) & (Le[:, 1] > box[2]) & (Le[:, 1] < box[3]))
    P_mc = float(out.mean())
    se_bin = np.sqrt(P_pred * (1 - P_pred) / N_MC)
    print("  σ = %.0f mm: アウトの確率 予測 %.3f、打った %d 本で %.3f(二項の標準誤差 %.3f、差 %.1f σ)" % (
        1e3 * sig_e, P_pred, N_MC, P_mc, se_bin, abs(P_mc - P_pred) / se_bin))
    gate("アウトの確率が予測と二項の 3σ 以内", abs(P_mc - P_pred) <= 3 * se_bin)
    if not REDUCED:                                             # 参考: 雑音が大きい側。300 本では近似の良し悪しの向きは決まらない
        s12 = Shot(bp, tp, rp, ip, p, v_in, w_in, np.array([0.75, W_half - 0.12, H + 0.02]))
        J12, L12 = s12.jacobian(), s12.fly(np.zeros(3))["L"]
        P12 = p_out_gaussian(L12, J12 @ (0.05 ** 2 * np.eye(3)) @ J12.T, box)
        Lb = np.array([s12.fly(rng.normal(0.0, 0.05, 3))["L"] for _ in range(N_MC)])
        o12 = ~((Lb[:, 0] > box[0]) & (Lb[:, 0] < box[1]) & (Lb[:, 1] > box[2]) & (Lb[:, 1] < box[3]))
        se12 = np.sqrt(P12 * (1 - P12) / N_MC)
        print("  (参考)縁から 12 cm を σ = 50 mm で: 予測 %.3f、打った %d 本で %.3f(二項の %.1f σ)—— 300 本では近似が裾を軽く見るか重く見るかは決まらない" % (
            P12, N_MC, o12.mean(), abs(o12.mean() - P12) / se12))
    # アウトしない雑音の上限: strategy_feeder は縁から 12 cm の内側を狙うので、余白 12 cm を横の 2σ に取る
    sig_ok = 0.12 / (2.0 * np.sqrt((Je @ Je.T)[1, 1]))
    print("  縁から 12 cm の余白を横の 2σ に収める読みの雑音の上限 σ* = %.1f cm(J から、送り合いの狙いは縁から 12 cm の内側)" % (100 * sig_ok))

    # ─────────────────────────────── 4. 遅れ ─────────────────────────────
    print("== 4. 遅れ: τ だけ古い読み p(t − τ) で打つ")
    lat_ok = True
    for tau in (0.005, 0.010, 0.020):
        d_tau = -v_in * tau + np.array([0.0, 0.0, -0.5 * 9.81 * tau ** 2])    # 古い読み − 今の位置(等加速度の近似: τ 前の球は上にいた分と、落ちる速さが遅かった分)
        dL_sim = sa.fly(d_tau)["L"] - L0
        dL_pred = Ja @ d_tau
        e = float(np.linalg.norm(dL_sim - dL_pred) / np.linalg.norm(dL_pred))
        lat_ok &= e < 0.05
        print("  τ = %2.0f ms: 読みのずれ %s cm → 着地点のずれ 実測 %s cm、J からの予測 %s cm(差 %.1f %%)" % (
            1e3 * tau, np.round(100 * d_tau, 2).tolist(), np.round(100 * dL_sim, 2).tolist(), np.round(100 * dL_pred, 2).tolist(), 100 * e))
    gate("遅れは J · (−vτ − ½gτ² ẑ) と 5 % 以内", lat_ok)

    # ─────────────────────────────── 5. 閉ループ ─────────────────────────────
    print("== 5. 閉ループ: 2 本のラケットで送り合う(毎コマの読みに雑音)")
    t_r = time.time()
    n_seed = 1 if REDUCED else 4                                # CI(reduced)は 1 本ずつ: 送り合いは 0.2 ms 刻みで重い
    rallies = {}
    for s_r in (0.0, 0.06):
        hs = []
        for seed in range(n_seed):
            g = np.random.default_rng(100 + seed)

            def perceive(t, pp, vv, ww, s_r=s_r, g=g):
                return pp + g.normal(0.0, s_r, 3), vv, ww

            r = RK.rally_simulate(bp, rp, tp, perceive=perceive, retries=0, max_hits=10, seed=seed, table_ip=ip)
            hs.append((r["hits"], r["end_reason"]))
            rallies.setdefault(s_r, r)
        rallies[("hits", s_r)] = hs
    h0 = [h for h, _ in rallies[("hits", 0.0)]]
    h6 = [h for h, _ in rallies[("hits", 0.06)]]
    print("  雑音 0: %s、雑音 6 cm(σ* の %.1f 倍): %s(%.1f s)" % (rallies[("hits", 0.0)], 0.06 / sig_ok, rallies[("hits", 0.06)], time.time() - t_r))
    gate("閉ループ: 雑音 0 は上限 10 本、σ* を越える雑音ではアウトで途切れる", all(h == 10 for h in h0) and np.mean(h6) < 10
         and any(e == "out" for _, e in rallies[("hits", 0.06)]))
    gate("零点: 誤差 0 なら狙った点に 1 mm 以内", zero_err < 1e-3, "(%.2f mm)" % (1e3 * zero_err))

    if figs.enabled():
        print("== 6. 図と動画")
        t_f = time.time()
        _figures(tp, Ls, cov_pred, L0, Le, out, Le0, Je, sig_e, rallies, sa, sig)
        print("  図と動画(%.1f s)" % (time.time() - t_f))
        if figs.errors():
            print("図の書き出しで失敗:", "; ".join(figs.errors()))
            OK.append(False)
    print("所要 %.1f s" % (time.time() - T0))
    print("SUMMARY: %d / %d gates PASS" % (sum(OK), len(OK)))
    print("PASS" if all(OK) else "FAIL")
    return 0 if all(OK) else 1


# ─────────────────────────────── 2 次元の模式図(上から / 横から) ─────────────────────────────
SCALE = 170.0                             # px / m
TABLE_BG = (0.05, 0.16, 0.36)
FLOOR_BG = (0.72, 0.74, 0.70)


def _canvas(w, h, bg=FLOOR_BG):
    img = np.empty((h, w, 3))
    img[:] = bg
    return img


def _to_px(x, y, cx, cy, scale=None):
    sc = SCALE if scale is None else scale
    return cx + sc * x, cy - sc * y


def _rect(img, x0, y0, x1, y1, color, fill=True, width=2):
    h, w = img.shape[:2]
    # 両端とも [0, w] に収める: 画面の左の外にある矩形で b が負になると、スライスが末尾から数えて帯を塗る
    a, b = int(np.clip(min(x0, x1), 0, w)), int(np.clip(max(x0, x1), 0, w))
    c, d = int(np.clip(min(y0, y1), 0, h)), int(np.clip(max(y0, y1), 0, h))
    if fill:
        img[c:d, a:b] = color
    else:
        img[c:c + width, a:b] = color
        img[d - width:d, a:b] = color
        img[c:d, a:a + width] = color
        img[c:d, b - width:b] = color


def _dot(img, x, y, r, color):
    h, w = img.shape[:2]
    if not (np.isfinite(x) and np.isfinite(y)):
        return
    y0, y1, x0, x1 = max(0, int(y - r - 1)), min(h, int(y + r + 2)), max(0, int(x - r - 1)), min(w, int(x + r + 2))
    if y0 >= y1 or x0 >= x1:                         # 画面の外(アウトして飛んでいった球)は描かない
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    m = (xx - x) ** 2 + (yy - y) ** 2 <= r * r
    img[yy[m], xx[m]] = color


def _table_top(img, tp, cx, cy, scale=None):
    L, W = 0.5 * tp["length"], 0.5 * tp["width"]
    x0, y0 = _to_px(-L, W, cx, cy, scale)
    x1, y1 = _to_px(L, -W, cx, cy, scale)
    _rect(img, x0, y0, x1, y1, TABLE_BG)
    _rect(img, x0, y0, x1, y1, (1.0, 1.0, 1.0), fill=False, width=2)
    nx, _ = _to_px(0.0, 0.0, cx, cy, scale)
    _rect(img, nx - 1, y0, nx + 2, y1, (0.85, 0.85, 0.85))              # ネット
    _rect(img, x0, cy - 1, x1, cy + 1, (0.9, 0.9, 0.9))                  # センターライン


def _ellipse(img, mean, cov, k, cx, cy, color, scale=None):
    vals, vecs = np.linalg.eigh(cov)
    for a in np.linspace(0, 2 * np.pi, 240):
        q = mean + k * vecs @ (np.sqrt(np.maximum(vals, 0)) * np.array([np.cos(a), np.sin(a)]))
        px, py = _to_px(q[0], q[1], cx, cy, scale)
        _dot(img, px, py, 1.6, color)


def _figures(tp, Ls, cov_pred, L0, Le, out, Le0, Je, sig_e, rallies, sa, sig):
    W_, H_ = 640, 360
    # (1) 着地点の雲: 縁から 6 cm を狙った 300 本が 1 本ずつ落ちる(黄 = 入った、赤 = アウト)。楕円 = J Σ Jᵀ の 2σ
    cov_e = Je @ (sig_e ** 2 * np.eye(3)) @ Je.T
    frames = []
    # 狙いの周りを拡大(1 m = 1100 px): 全体の縮尺(170 px/m)では雲も楕円も 20 px ほどで見えない。
    Z = 1100.0
    zx, zy = W_ // 2 - Z * Le0[0], H_ // 2 + 20 + Z * Le0[1]
    base = _canvas(W_, H_)
    _table_top(base, tp, zx, zy, Z)
    ex, ey = _to_px(0.0, 0.5 * tp["width"], zx, zy, Z)
    base = np.asarray(AN.text_box(base, "台の縁", (int(W_ - 90), int(ey) - 26), font_size=13), dtype=np.float64)
    img = base.copy()
    tx, ty = _to_px(Le0[0], Le0[1], zx, zy, Z)
    per = max(1, len(Le) // 75)
    for k in range(len(Le)):
        px, py = _to_px(Le[k, 0], Le[k, 1], zx, zy, Z)
        _dot(img, px, py, 3.0, (0.95, 0.2, 0.2) if out[k] else (1.0, 0.85, 0.1))
        if k % per == per - 1 or k == len(Le) - 1:
            f = img.copy()
            _ellipse(f, Le0, cov_e, 2.0, zx, zy, (0.35, 0.95, 1.0), Z)       # 予測は点の上に重ねる
            _dot(f, tx, ty, 5, (1.0, 1.0, 1.0))
            f = np.asarray(AN.text_box(f, "読みの雑音 σ = %.0f mm で %3d 本  アウト %d 本(%.0f %%)" % (
                1e3 * sig_e, k + 1, int(out[:k + 1].sum()), 100 * out[:k + 1].mean()), (8, 8), font_size=14), dtype=np.float64)
            f = np.asarray(AN.text_box(f, "白 = 狙った点  水色の楕円 = 打つ前に J から出した 2σ(拡大、10 cm = 110 px)", (8, H_ - 34), font_size=13), dtype=np.float64)
            frames.append(np.clip(f, 0, 1))
    frames += [frames[-1]] * 20
    figs.save_video("landing_cloud", frames, fps=15.0, gif_every=1, gif_width=None,
                    caption="台の縁から 6 cm の点(白)を狙い、球の位置の読みに σ = %.0f mm の雑音を入れて %d 本打つ。黄 = 入った、赤 = アウト(%.0f %%)。"
                            "水色の楕円は打つ前に誤差の伝わり方 J から出した 2σ —— 高さの読み違いが前後に伸びる。" % (1e3 * sig_e, len(Le), 100 * out.mean()))
    # (2) 横から: 高さを 5 cm 高く読んだ打球(狙いの計算は幽霊の球から、飛ぶのは本当の球から)
    delta = np.array([0.0, 0.0, 0.05])
    f_true = sa.fly(np.zeros(3))
    f_bad = sa.fly(delta)
    ghost = B.flight_simulate(sa.p + delta, f_bad["aim"], np.zeros(3), sa.bp, sa.ip, 1.2, 2e-4, table_z=tp["height"])
    H = tp["height"]
    cx2, cy2 = 330, 300
    fr2 = []
    for i in range(0, int(T_FLIGHT * 1.15 / 0.004)):
        t = i * 0.004
        img = _canvas(W_, H_, (0.62, 0.75, 0.92))
        x0, y0 = _to_px(-0.5 * tp["length"], H, cx2, cy2 + SCALE * H)
        x1, y1 = _to_px(0.5 * tp["length"], H - 0.03, cx2, cy2 + SCALE * H)
        _rect(img, x0, y0, x1, y1, TABLE_BG)
        nx, ny = _to_px(0.0, H + 0.1525, cx2, cy2 + SCALE * H)
        _rect(img, nx - 1, ny, nx + 2, y0, (0.3, 0.3, 0.3))
        for sim, col in ((ghost, (0.7, 0.7, 0.7)), (f_bad["sim"], (0.95, 0.25, 0.2)), (f_true["sim"], (1.0, 0.85, 0.1))):
            m = sim["t"] <= t
            for q in sim["p"][m][::40]:
                px, py = _to_px(q[0], q[2], cx2, cy2 + SCALE * H)
                _dot(img, px, py, 1.4, col)
            q = sim["p"][int(np.searchsorted(sim["t"], min(t, sim["t"][-1])))]
            px, py = _to_px(q[0], q[2], cx2, cy2 + SCALE * H)
            _dot(img, px, py, 5, col)
        tx, ty = _to_px(sa.target[0], H, cx2, cy2 + SCALE * H)
        _rect(img, tx - 6, ty - 2, tx + 7, ty + 2, (1, 1, 1))
        f = np.asarray(AN.text_box(img, "横から  t = %3.0f ms" % (1e3 * t), (8, 8), font_size=14), dtype=np.float64)
        f = np.asarray(AN.text_box(f, "灰 = 読んだ位置(5 cm 高い)から狙った計算  赤 = その計算で本当の位置から打った球  黄 = 正しく読んだ球",
                                   (8, H_ - 34), font_size=12, max_width=W_ - 16), dtype=np.float64)
        fr2.append(np.clip(f, 0, 1))
    fr2 += [fr2[-1]] * 15
    dL = f_bad["L"] - f_true["L"]
    figs.save_video("height_misread", fr2, fps=25.0, gif_every=2, gif_width=None,
                    caption="高さを 5 cm 高く読むと、狙いの計算(灰)は低い弾道を選び、本当の位置から打った球(赤)は狙いより %.1f cm 手前に落ちる。"
                            "J の前後の増幅 %.2f × 5 cm = %.1f cm(一次の予測)。" % (-100 * dL[0], abs(sa.jacobian()[0, 2]), 5 * abs(sa.jacobian()[0, 2])))
    # (3) 送り合いの並べ比べ(上から): 雑音 0 と 6 cm
    r0, r6 = rallies[0.0], rallies[0.06]
    # ★送り合いの刻みは dt = 0.2 ms。刻みごとにコマを作ると 10 本で 2 万コマ超・数百 GB になり、
    #   図づくりがメモリ逼迫で止められた(2026-10-01)。コマは**シミュレーションの時刻**で刻む:
    #   1/2 速・25 fps = 0.02 s ごとに 1 コマ、軌跡は直近 0.3 s。コマは uint8 で持つ。
    t_end = max(float(r0["t"][-1]), float(r6["t"][-1]))
    fr3 = []
    END = {"out": "アウト", "max_hits": "上限の本数", "net": "ネット", "double_bounce": "2 度跳ね",
           "wrong_side_bounce": "自分のコートで跳ねた", "volley": "ボレー", "max_time": "時間切れ"}
    # 最後のコマは各ラリーの終わりの時刻ちょうどに置く(0.02 s の刻みだけだと最後の 1 本が写らない)
    for tv in list(np.arange(0.0, t_end, 0.02)) + [t_end]:
        panels = []
        for r, lab in ((r0, "読みの雑音 0"), (r6, "読みの雑音 σ = 6 cm")):
            img = _canvas(W_ // 2 * 2, H_)
            cxp, cyp = W_ // 2, H_ // 2
            _table_top(img, tp, cxp, cyp)
            k = min(int(np.searchsorted(r["t"], tv)), len(r["t"]) - 1)
            k0 = int(np.searchsorted(r["t"], r["t"][k] - 0.3))
            for q in r["p"][k0:k + 1:max(1, (k + 1 - k0) // 40)]:
                px, py = _to_px(q[0], q[1], cxp, cyp)
                _dot(img, px, py, 1.3, (1.0, 0.85, 0.1))
            q = r["p"][k]
            px, py = _to_px(q[0], q[1], cxp, cyp)
            _dot(img, px, py, 4, (1.0, 0.6, 0.1))
            for s_, col in ((0, (0.9, 0.2, 0.2)), (1, (0.2, 0.4, 0.95))):
                rk = r["racket_pos"][k][s_]
                ax, ay = _to_px(rk[0], rk[1] - 0.075, cxp, cyp)
                bx, by = _to_px(rk[0], rk[1] + 0.075, cxp, cyp)
                _rect(img, ax - 3, by, ax + 4, ay, col)
            hits = int(np.sum(np.asarray(r["hit_times"]) <= r["t"][k]))
            end = "" if tv < float(r["t"][-1]) else "  終わり: %s" % END.get(r["end_reason"], r["end_reason"])
            img = np.asarray(AN.text_box(img, "%s  %d 本%s" % (lab, hits, end), (8, 8), font_size=14), dtype=np.float64)
            panels.append(img)
        fr3.append((np.clip(np.concatenate(panels, axis=0), 0, 1) * 255 + 0.5).astype(np.uint8))
    fr3 += [fr3[-1]] * 20
    assert len(fr3) < 2000, len(fr3)
    figs.save_video("rally_compare", fr3, fps=25.0, gif_every=3, gif_width=480,
                    caption="上から見た送り合い(1/2 速)。上 = 読みの雑音 0 で上限の %d 本、下 = 毎コマの読みに σ = 6 cm で %d 本(%s)。"
                            "ラケットは届いている —— 途切れる理由は空振りでなく、読み違いから狙った打球のアウト。" % (
                                r0["hits"], r6["hits"], END.get(r6["end_reason"], r6["end_reason"])))
    # (4) 静止: 実測と予測のばらつき
    figs.save_plot("spread_vs_prediction", [("打った %d 本の着地点" % len(Ls), 100 * (Ls[:, 0] - L0[0]), 100 * (Ls[:, 1] - L0[1]))],
                   kinds=["scatter"], xlabel="前後のずれ [cm]", ylabel="左右のずれ [cm]", title="着地点のずれ(σ = %.0f mm の読み)" % (1e3 * sig),
                   caption="読みの雑音は 3 方向に同じ大きさでも、着地点のずれは前後に %.1f 倍伸びる(高さの読み違いが落ちる角の分だけ増える)。" % (
                       np.sqrt(cov_pred[0, 0] / cov_pred[1, 1])))


if __name__ == "__main__":
    sys.exit(main())
