# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""火星の実地形の上で、車輪の滑りを不確かさ付きで予測し、滑りのリスクを避ける経路を引く —— Bekker / Wong–Reece と CVaR(2026-10-06)。

柔らかい砂の上では、車輪が回っても車体はその分だけ進まない(滑り率 s)。斜面が急になると s は 1 に近づき、
ローバーは立ち往生する。新モジュール roverslip(15 op)で次の連鎖を学習なしに組む:
土の定数 → Wong–Reece の車輪の応力の数値積分 → 斜面の角ごとの定常の滑り率 → 地面を見るカメラの像の並進と車輪の回転から
実際の滑り率を測る → 測った滑りに分位点回帰(共形の補正つき)とガウス過程で不確かさの帯 → 辺ごとの所要時間に CVaR を入れた
コスト地図 → 8 近傍の Dijkstra で「平均の最短」と「滑りのリスク最小」の 2 本。
背景: 不確かな滑りを予測して危険を避ける経路を引く研究(Sci. Rep. 2026、doi:10.1038/s41598-026-40109-1、本文は読めて
いない)と、その前身の公開コード(MIT、傾き → 滑りを GP で)。ここは同じ問いを、閉形式で確かめられる土の力学と、
外れたら分かる統計(被覆率)で解く。

何が外から来るか:
  * **土の定数**: arXiv:2606.06790 の表 2(乾いた砂、M90 火星模擬土)。
  * **地形**: HiRISE の DTM(Balvicar クレーターの中央丘、0.88 m/px、パブリックドメイン、NASA/JPL/University of Arizona)。
    データが無ければ合成の fBm 地形(driveterrain.fbm_height)で代える。
  * **閉形式**: Bekker の締め固め抵抗 b k z^(n+1)/(n+1)、n = 1 の垂直力、放物線の沈下の式(Γ 関数の厳密な係数)。
  * **物理シミュレータ**: MuJoCo の剛体の車輪(剛な地面でだけ一致するはずの相手)。
真値が既知のもの(合成): 実際の滑り(Wong–Reece の乾いた砂 + 斜面とともに広がる雑音、「崩れる殻」は仮想の二峰の土)。

門(既定): 閉形式 3、Bekker の近似の罠、剛な地面での MuJoCo との一致・砂での不一致、視覚オドメトリの滑り率、
被覆率(分位点回帰とガウス過程)、ガウス過程の外挿の罠、実地形の 2 経路(CVaR 経路が CVaR 時間で勝ち、平均時間では負ける、
真の滑りでの立ち往生の確率)、差が出る場面と出ない場面、図の中身。
既定(図なし = CI の経路)は絞る: 滑りの曲線は 5° 刻み・真値は 2° 刻み、学習データは真の滑りの観測をそのまま(視覚
オドメトリの精度は門 [4] で別に固定)、データが無いときの fBm は計画の格子で直に。--full と図を書く実行は 1° / 0.5° 刻み、
種 0 の学習データを視覚オドメトリ経由(240 回)、fBm は DTM の解像度。--full: さらに不確かさの学習データの種を 5 通りに増やす。
図(既定の出力先は out/figures/<PoC 名>/、FULLSEYE_FIGURE_DIR で変更): 実地形の 2 経路と滑りの CVaR の地図(DTM の等倍
1024 × 1024)、ローバーが進むと滑りの推定(帯)が更新される GIF、滑り–傾きの帯、牽引–滑り曲線、MuJoCo との比較、
2 種の土の場面。データの置き場は環境変数 FULLSEYE_ROVERSLIP_DATA(PROVENANCE.md のあるディレクトリ)。
Run: py -3.11 examples/poc_rover_slip_risk_path.py [--full]
"""
from __future__ import annotations

import math
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import roverslip as R  # noqa: E402

FULL = "--full" in sys.argv
#: 重い経路(1° 刻みの曲線・0.5° 刻みの真値・学習データを視覚オドメトリ経由・fBm を DTM の解像度で)を通すか。既定(図なし)は
#: CI の PoC の門の経路なので絞る(CI は手元の約 9 倍遅い)。--full と図を書く実行は重い経路。
HEAVY = FULL or figs.enabled()
WHEEL = {"r": 0.15, "b": 0.12}              # 車輪の半径・幅 [m](直径 30 cm、幅 12 cm)
MASS, NW, G = 50.0, 4, 3.72                 # 車体 50 kg、4 輪、火星の重力
SPEED = 0.05                                # 指令の速さ [m/s]
S_MAX = 0.6                                 # これ以上の(悲観的な)滑りの辺は通らない
ALPHA = 0.9
DTM_NAME = "balvicar_dtm_L10800_S3860_1024.npy"
DTM_CELL = 0.88208367396075                 # m/px(ラベルの MAP_SCALE)
F_PLAN = 4                                  # 計画の格子 = DTM の 4 × 4 平均(3.53 m)
_GATES: list[tuple[str, bool]] = []


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail))


def _data_dir():
    d = os.environ.get("FULLSEYE_ROVERSLIP_DATA", "").strip()
    return Path(d) if d and (Path(d) / DTM_NAME).is_file() else None


# ======================================================================================================================
# 真の滑り(合成): 乾いた砂の Wong–Reece + 斜面とともに広がる雑音、仮想の「崩れる殻」
_TRUTH = {}


def sand_truth():
    if "f" not in _TRUTH:
        grid = np.linspace(-30, 30, 121 if HEAVY else 31)
        sc = R.slope_slip_curve(grid, WHEEL, "dry_sand", mass=MASS, n_wheels=NW, gravity=G)
        ok = sc["feasible"]
        _TRUTH.update(g=grid[ok], s=sc["slip"][ok], max=sc["max_slope"])
        _TRUTH["f"] = lambda x: np.interp(x, _TRUTH["g"], _TRUTH["s"], left=_TRUTH["s"][0], right=1.0)
    return _TRUTH["f"]


def sand_noise(x):
    return 0.015 + 0.004 * np.abs(x)


def obs_sand(x, rng):
    return sand_truth()(x) + rng.normal(0, 1, np.shape(x)) * sand_noise(x)


def obs_crust(x, rng):
    br = rng.random(np.shape(x)) < 0.15
    s = sand_truth()(x)
    return np.where(br, s + 0.03 * np.abs(x), 0.3 * s) + rng.normal(0, 0.015, np.shape(x))


def texture(shape, off_r, off_c, seed=3):
    """地面の模様(帯域制限の正弦波 120 本、任意の副画素のずれで厳密に標本化できる)。"""
    rng = np.random.default_rng(seed)
    f = rng.uniform(-0.2, 0.2, (120, 2))
    ph = rng.uniform(0, 2 * np.pi, 120)
    a = rng.uniform(0.3, 1.0, 120) / (1 + 20 * np.hypot(f[:, 0], f[:, 1]))
    i, j = np.mgrid[0:shape[0], 0:shape[1]].astype(float)
    arg = 2 * np.pi * (f[:, 0, None, None] * (i + off_r) + f[:, 1, None, None] * (j + off_c)) + ph[:, None, None]
    return np.sum(a[:, None, None] * np.cos(arg), axis=0)


def measure_slip_vo(s_true, rng, px=0.002, dphi=0.05, n=6):
    """真の滑り s_true で進むローバーの、地面を見るカメラのコマを合成し、像の並進と車輪の回転から滑り率を測る。"""
    step = (1 - s_true) * WHEEL["r"] * dphi / px
    lat = rng.normal(0, 0.2)
    seed = int(rng.integers(0, 10_000))
    frames = [texture((48, 48), lat * t, step * t, seed) + rng.normal(0, 0.02, (48, 48)) for t in range(n)]
    tr = R.ground_shift_track(frames, px)
    return R.odometry_slip(-tr["position"][:, 1], dphi * np.arange(n), WHEEL["r"], window=n - 1)["slip_total"]


# ======================================================================================================================
# 描画(numpy だけの簡単な線と点。文字は fullseye の text_box)
def hillshade(Z, cell, az=315.0, alt=45.0):
    gy, gx = np.gradient(Z, cell)
    a, e = math.radians(az), math.radians(alt)
    L = np.array([math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), math.sin(e)])
    n = np.stack([-gx, gy, np.ones_like(Z)])
    n /= np.linalg.norm(n, axis=0)
    return np.clip(np.tensordot(L, n, axes=1), 0, 1)


def stamp(img, pts, rgb, radius):
    H, W = img.shape[:2]
    r = int(math.ceil(radius))
    oy, ox = np.mgrid[-r:r + 1, -r:r + 1]
    disk = (oy * oy + ox * ox) <= radius * radius
    for (y, x) in pts:
        yi, xi = int(round(y)), int(round(x))
        ys, xs = yi + oy[disk], xi + ox[disk]
        ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
        img[ys[ok], xs[ok]] = rgb


def polyline(img, pts, rgb, radius, dash=None):
    pts = np.asarray(pts, float)
    dense = []
    acc = 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        L = float(np.hypot(*(b - a)))
        k = max(2, int(L * 2))
        for t in np.linspace(0, 1, k, endpoint=False):
            p = a + (b - a) * t
            if dash is None or (acc % dash) < dash * 0.6:
                dense.append(p)
            acc += L / k
    dense.append(pts[-1])
    stamp(img, dense, rgb, radius)


def colormap(v, lo, hi):
    """0 → 青緑、中 → 黄、1 → 赤みの橙(色覚に配慮した 3 点の線形補間)。"""
    t = np.clip((v - lo) / (hi - lo), 0, 1)[..., None]
    c0, c1, c2 = np.array([0.0, 0.45, 0.70]), np.array([0.94, 0.89, 0.26]), np.array([0.84, 0.37, 0.0])
    return np.where(t < 0.5, c0 + (c1 - c0) * (t / 0.5), c1 + (c2 - c1) * ((t - 0.5) / 0.5))


def label(img, text, xy, size=14, anchor="lt"):
    try:
        import fullseye as fs
        return np.asarray(fs.text_box(img, text, xy, anchor=anchor, font_size=size))
    except Exception:                                    # noqa: BLE001 (文字が描けなくても図は出す)
        return img


C_MEAN = (0.90, 0.62, 0.00)                 # 平均の最短(橙)
C_CVAR = (0.00, 0.45, 0.70)                 # 滑りのリスク最小(青)


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    print("roverslip PoC —— 車輪の滑りを不確かさ付きで予測し、滑りのリスクを避ける経路")

    # [1] 閉形式
    print("[1] Bekker / Wong–Reece の閉形式")
    front = dict(R.SOILS["dry_sand"], a0=0.0, a1=0.0, b0=0.0, b1=0.0, c=0.0, phi=0.0)
    r, b = WHEEL["r"], WHEEL["b"]
    errs = []
    for n in (0.6, 1.0, 1.9):
        S = dict(front, n=n)
        f = R.wheel_forces(0.012, 0.3, WHEEL, S)
        k = (S["kc"] / b + S["kphi"]) * 1e3
        errs.append(abs(f["DP"] / -(b * k * 0.012 ** (n + 1) / (n + 1)) - 1))
    gate("τ = 0 の牽引 = −Bekker の締め固め抵抗(n = 0.6 / 1 / 1.9)", max(errs) < 1e-6, "(相対誤差 最大 %.1e)" % max(errs))
    S = dict(front, n=1.0)
    f = R.wheel_forces(0.02, 0.0, WHEEL, S)
    tf = f["theta_f"]
    k = (S["kc"] / b + S["kphi"]) * 1e3
    e = abs(f["Fz"] / (b * k * r * r * (tf - math.sin(tf) * math.cos(tf)) / 2) - 1)
    gate("n = 1 の垂直力の閉形式", e < 1e-9, "(相対誤差 %.1e)" % e)
    S19 = dict(front, n=1.9)
    conv = [abs(R.bekker_wheel_sinkage(W, WHEEL, S19, "parabolic") / float(R.wheel_sinkage(W, WHEEL, S19)) - 1) for W in (0.5, 5.0, 50.0)]
    cls = R.bekker_wheel_sinkage(5.0, WHEEL, S19) / float(R.wheel_sinkage(5.0, WHEEL, S19)) - 1
    gate("放物線の沈下の式(厳密な Γ の係数)は z/D → 0 で数値積分に収束", conv[0] < 0.002 and conv[0] < conv[1] < conv[2],
         "(誤差 %.4f / %.4f / %.4f、荷重 0.5 / 5 / 50 N)" % tuple(conv))
    gate("罠: 教科書の (3 − n)/3 の式は n = 1.9 で沈下を深く出す", cls > 0.15, "(+%.1f %%)" % (100 * cls))

    # [2] 土 → 滑りの曲線
    print("[2] 斜面の角 → 定常の滑り率(Wong–Reece、火星の重力、50 kg・4 輪)")
    slopes = np.arange(-20, 36, 1.0 if HEAVY else 5.0)
    curves = {nm: R.slope_slip_curve(slopes, WHEEL, nm, mass=MASS, n_wheels=NW, gravity=G)
              for nm in ("dry_sand", "mars_simulant_m90", "rigid_ground")}
    for nm, c in curves.items():
        s = c["slip"]
        at = [s[int(np.flatnonzero(slopes == v)[0])] for v in (0.0, 10.0, 20.0)]
        print("    %-18s 0°: %+.3f  10°: %+.3f  20°: %+.3f  登れる最大 %.1f°" % (nm, at[0], at[1], at[2], c["max_slope"]))
    mono = all(np.all(np.diff(c["slip"][c["feasible"] & (slopes >= 0)]) > 0) for c in curves.values())
    gate("登りの滑りは角とともに単調に増える(3 種の土)", mono)
    gate("剛な地面の極限: 登れる最大の角 → atan(tan φ) = 26.57°", abs(curves["rigid_ground"]["max_slope"] - 26.565) < 0.5,
         "(%.2f°)" % curves["rigid_ground"]["max_slope"])
    W1 = MASS * G / NW
    trac = {nm: R.wheel_traction_curve(W1, WHEEL, nm, np.linspace(0, 0.9, 46)) for nm in ("dry_sand", "mars_simulant_m90")}

    # [3] MuJoCo
    print("[3] MuJoCo の剛体の車輪と比べる(剛な地面で一致、砂で不一致のはず)")
    mj = None
    try:
        import mujoco  # noqa: F401
        mj_sl = np.arange(0, 40, 1.0)
        mj = {"rigid": R._mujoco_slope_slip(mj_sl, 0.5, r, b, MASS / NW, gravity=G),
              "sand_mu": R._mujoco_slope_slip(mj_sl, math.tan(math.radians(R.SOILS["dry_sand"]["phi"])), r, b, MASS / NW, gravity=G)}

        def cross(x, s, lvl=0.5):
            s = np.where(np.isfinite(s), s, 9.0)
            kk = int(np.argmax(s >= lvl))
            return float(x[kk - 1] + (x[kk] - x[kk - 1]) * (lvl - s[kk - 1]) / (s[kk] - s[kk - 1])) if kk > 0 else float("nan")
        lim_mj = cross(mj_sl, mj["rigid"])
        fine = np.arange(24, 28.01, 0.125)
        lim_mjf = cross(fine, R._mujoco_slope_slip(fine, 0.5, r, b, MASS / NW, gravity=G))
        low = np.max(np.abs(mj["rigid"][:21]))
        gate("剛な地面: MuJoCo の滑り < 0.05(0〜20°)、Wong–Reece の極限も < 0.05",
             low < 0.05 and np.nanmax(np.abs(curves["rigid_ground"]["slip"][(slopes >= 0) & (slopes <= 20)])) < 0.05, "(MuJoCo 最大 %.4f)" % low)
        gate("剛な地面: 限界の角が一致(MuJoCo で滑り 0.5 を越える角 vs Wong–Reece)",
             abs(lim_mjf - curves["rigid_ground"]["max_slope"]) < 0.75,
             "(%.2f° vs %.2f°)" % (lim_mjf, curves["rigid_ground"]["max_slope"]))
        s20_mj = float(mj["sand_mu"][20])
        gate("砂: 一致しない(剛体は沈まず、20° でも滑らない)", sand_truth()(20.0) - s20_mj > 0.15,
             "(20° の滑り Wong–Reece %.3f / MuJoCo %.3f、限界 %.1f° / %.1f°)"
             % (sand_truth()(20.0), s20_mj, curves["dry_sand"]["max_slope"], cross(mj_sl, mj["sand_mu"])))
        print("    (MuJoCo の剛な地面の限界、1° 刻みの粗い内挿 %.2f°)" % lim_mj)
    except ImportError:
        print("    mujoco が無いので飛ばす(門に数えない)")

    # [4] 視覚オドメトリで実際の滑り率を測る
    print("[4] 地面を見るカメラ + 車輪の回転 → 実際の滑り率")
    rng = np.random.default_rng(11)
    vo_err = []
    for s_true in (0.0, 0.1, 0.25, 0.5, 0.75):
        vo_err.append(abs(measure_slip_vo(s_true, rng) - s_true))
    gate("視覚オドメトリの滑り率の誤差(雑音つきのコマ、5 通りの滑り)", max(vo_err) < 0.01, "(最大 %.4f)" % max(vo_err))

    # [5] 不確かさ: ローバーが走りながら測った滑り(視覚オドメトリ経由)を学習データに
    print("[5] 滑りの不確かさ: 分位点回帰(共形の補正) vs ガウス過程、名目 90 %")
    seeds = range(5) if FULL else range(3)
    cov = {"q": [], "g": []}
    steep = {"q": [], "g": []}
    gentle = {"q": [], "g": []}
    models_last = None
    for sd in seeds:
        rng = np.random.default_rng(100 + sd)
        u = rng.random(240) < 0.5
        x = np.where(u, rng.uniform(-20, 24, 240), np.clip(rng.normal(2, 9, 240), -20, 24))
        s_true = obs_sand(x, rng)
        y = np.array([measure_slip_vo(float(np.clip(v, -0.9, 0.95)), rng, n=4) for v in s_true]) if (sd == 0 and HEAVY) else s_true
        xt = np.where(rng.random(3000) < 0.5, rng.uniform(-20, 24, 3000), np.clip(rng.normal(2, 9, 3000), -20, 24))
        yt = obs_sand(xt, rng)
        mq, mg = R.slip_quantile_fit(x, y), R.slip_gp_fit(x, y)
        for kind, m in (("q", mq), ("g", mg)):
            p = R.slip_predict(m, xt, 0.9)
            inb = (yt >= p["lower"]) & (yt <= p["upper"])
            cov[kind].append(inb.mean())
            steep[kind].append(inb[xt >= 8].mean())
            gentle[kind].append(inb[(xt > -5) & (xt < 8)].mean())
        if sd == 0:
            models_last = (x, y, mq, mg)
    print("    被覆率(全体)  分位点回帰 %s  ガウス過程 %s" % (np.round(cov["q"], 3), np.round(cov["g"], 3)))
    print("    被覆率(8° 以上) 分位点回帰 %s  ガウス過程 %s" % (np.round(steep["q"], 3), np.round(steep["g"], 3)))
    gate("分位点回帰 + 共形の補正の被覆率が名目 90 % の近く", 0.86 <= np.mean(cov["q"]) <= 0.96, "(平均 %.3f)" % np.mean(cov["q"]))
    # 閾値は種の組を 30 通り振って決めた(2026-10-06): 「急斜面で分位点回帰より 0.05 低い」は 30 組中 2 組で落ちた(差の最小 0.033)ので、
    # 急斜面で 0.02 低い かつ 緩斜面で広すぎる(> 0.97、最小 0.985)の両側にした —— 30 組とも通る。被覆の門 [0.86, 0.96] は 30 組で 0.869〜0.946
    gate("罠: ガウス過程(一様な雑音)は急斜面で帯が足りず、緩斜面で広すぎる", np.mean(steep["g"]) < np.mean(steep["q"]) - 0.02 and np.mean(gentle["g"]) > 0.97,
         "(8° 以上の被覆 %.3f vs 分位点回帰 %.3f、−5〜8° は %.3f)" % (np.mean(steep["g"]), np.mean(steep["q"]), np.mean(gentle["g"])))
    x0, y0, mq, mg = models_last
    hi = mg["x_range"][1]
    gp_out = float(R.slip_predict(mg, np.array([hi + 8]))["mean"][0])
    gate("罠: ガウス過程はデータの外(> %.0f°)で事前の平均に戻る —— 真は立ち往生" % hi, gp_out < 0.6 and sand_truth()(hi + 8) == 1.0,
         "(%.0f° で GP の平均 %.3f)" % (hi + 8, gp_out))

    # [6] 実地形の 2 経路
    data = _data_dir()
    print("[6] 実地形の上の 2 経路(%s)" % ("HiRISE DTM" if data else "合成の fBm 地形 —— データが無い"))
    if data is not None:
        Zfull = np.load(data / DTM_NAME).astype(np.float64)
        # 出発・到着: 無作為の 40 組(距離 150 セル超)を試作で走らせ、2 経路の離れ方(Hausdorff)が最大の組を選んだ
        # (中央値は 3 セル = 10 m でほぼ重なる。--full で 40 組を走らせ直して分布を出す)。
        start, goal = (71, 21), (241, 61)
    else:
        import driveterrain as DT
        p = DT.fbm_params(seed=4, hurst=0.8, n_waves=256, f_min=1 / 600.0, f_max=1 / 12.0, amplitude=18.0)
        if HEAVY:
            ii, jj = np.mgrid[0:1024, 0:1024] * DTM_CELL
            Zfull = DT.fbm_height(jj, ii, p)
        else:
            # 既定: 4 × 4 の区画の平均を閉形式で(正弦の和なので、区画の平均 = 区画の中心で振幅に Dirichlet 核
            # sin(F ω d/2) / (F sin(ω d/2)) を x・y ごとに掛けたもの)。重い経路の D と丸めの範囲で同じ、評価点は 1/16
            pb = dict(p)
            wx = 2 * np.pi * p["f"] * np.cos(p["theta"]) * DTM_CELL
            wy = 2 * np.pi * p["f"] * np.sin(p["theta"]) * DTM_CELL

            def _dk(w):
                den = F_PLAN * np.sin(w / 2)
                return np.where(np.abs(den) > 1e-12, np.sin(F_PLAN * w / 2) / np.where(den == 0, 1.0, den), 1.0)
            pb["A"] = p["A"] * _dk(wx) * _dk(wy)
            ii, jj = (np.mgrid[0:256, 0:256] * F_PLAN + (F_PLAN - 1) / 2) * DTM_CELL
            Zfull = np.kron(DT.fbm_height(jj, ii, pb), np.ones((F_PLAN, F_PLAN)))
        start, goal = (20, 20), (240, 40)
    H0 = Zfull.shape[0] // F_PLAN
    D = Zfull[:H0 * F_PLAN, :H0 * F_PLAN].reshape(H0, F_PLAN, H0, F_PLAN).mean((1, 3))
    cell = DTM_CELL * F_PLAN
    res = {}
    for a in (0.0, ALPHA):
        cm = R.cvar_cost_map(D, cell, mq, alpha=a, speed=SPEED, s_max=S_MAX)
        pth = R.risk_aware_path(cm, start, goal)
        ev = R.path_slip_risk(pth["path"], D, cell, mq, alpha=ALPHA, speed=SPEED, s_max=S_MAX)
        res[a] = (cm, pth, ev)
    # 真の滑りで走らせたときの所要時間と立ち往生の確率(モンテカルロ、辺ごとに独立)
    mc = {}
    rng = np.random.default_rng(7)
    for a in (0.0, ALPHA):
        ev = res[a][2]
        th = ev["pitch"]
        L = np.hypot(cell * np.hypot(*np.diff(res[a][1]["path"], axis=0).T), np.diff(D[tuple(res[a][1]["path"].T)]))
        smp = np.where(th >= 0, 1, -1) * obs_sand(np.repeat(th[None], 4000, 0), rng)
        stuck = np.any(smp >= 0.6, axis=1)
        t = np.sum(L / (SPEED * (1 - np.clip(smp, 0, 0.999))), axis=1)
        mc[a] = (float(stuck.mean()), float(np.median(t[~stuck])) if (~stuck).any() else float("inf"))
    e0, e9 = res[0.0][2], res[ALPHA][2]
    for a, nm in ((0.0, "平均の最短"), (ALPHA, "リスク最小")):
        ev = res[a][2]
        print("    %-10s 長さ %.0f m、平均の時間 %.0f s、CVaR の時間 %.0f s、最大の傾き %.1f°、CVaR の滑り 最大 %.3f、"
              "真の滑りで立ち往生(s ≥ 0.6) %.2f %%" % (nm, ev["length"], ev["time_mean"], ev["time_cvar"], ev["max_pitch"],
                                                 ev["max_cvar_slip"], 100 * mc[a][0]))
    gate("2 経路とも届く", res[0.0][1]["reached"] and res[ALPHA][1]["reached"])
    gate("CVaR 経路は CVaR の時間で勝ち、平均の時間では負けない程度(Dijkstra の最適性の検算)",
         e9["time_cvar"] <= e0["time_cvar"] * 1.002 and e0["time_mean"] <= e9["time_mean"] * 1.002,
         "(CVaR %.0f vs %.0f s、平均 %.0f vs %.0f s)" % (e9["time_cvar"], e0["time_cvar"], e9["time_mean"], e0["time_mean"]))
    # 最悪の辺の CVaR の滑りは目的関数(和)ではないので門にしない(下がる保証が無い)。数字だけ出す。
    print("    最悪の辺の CVaR の滑り %.3f → %.3f、平均の時間は +%.2f %%"
          % (e0["max_cvar_slip"], e9["max_cvar_slip"], 100 * (e9["time_mean"] / e0["time_mean"] - 1)))
    gate("真の滑りで立ち往生の確率がリスク最小の経路で下がる(または両方 0)", mc[ALPHA][0] <= mc[0.0][0],
         "(%.2f %% → %.2f %%)" % (100 * mc[0.0][0], 100 * mc[ALPHA][0]))

    if FULL and data is not None:
        # 出発・到着を無作為に 40 組(距離 150 セル超)選び、2 経路がどれだけ離れるか(Hausdorff、セル)の分布を出す。
        # 図の組はこの中で最も離れる組 —— 1 種の土では CVaR は傾きの単調な関数なので、ほとんどの組で 2 本はほぼ重なる。
        rs = np.random.default_rng(5)
        cm0, cm9 = res[0.0][0], res[ALPHA][0]
        hd, red = [], []
        for _ in range(40):
            while True:
                aa, bb = tuple(int(v) for v in rs.integers(10, H0 - 10, 2)), tuple(int(v) for v in rs.integers(10, H0 - 10, 2))
                if math.hypot(aa[0] - bb[0], aa[1] - bb[1]) > 150:
                    break
            q0, q9 = R.risk_aware_path(cm0, aa, bb), R.risk_aware_path(cm9, aa, bb)
            if not (q0["reached"] and q9["reached"]):
                continue
            dd = np.sqrt(((q0["path"][:, None, :] - q9["path"][None]) ** 2).sum(-1))
            hd.append(max(dd.min(1).max(), dd.min(0).max()))
            e_0 = R.path_slip_risk(q0["path"], D, cell, mq, ALPHA, SPEED, S_MAX)
            e_9 = R.path_slip_risk(q9["path"], D, cell, mq, ALPHA, SPEED, S_MAX)
            red.append(e_0["max_cvar_slip"] - e_9["max_cvar_slip"])
        print("    --full: 40 組の 2 経路の離れ方 中央値 %.1f セル(%.0f m)、最大 %.1f セル、最悪の辺の CVaR の滑りの差 中央値 %.3f"
              % (np.median(hd), np.median(hd) * cell, max(hd), np.median(red)))

    # [7] 差が出る場面と出ない場面(2 種の土)
    print("[7] 2 種の土(砂と仮想の崩れる殻)—— 差が出る場面と出ない場面")
    rng = np.random.default_rng(1)
    xs, xc = rng.uniform(-20, 24, 300), rng.uniform(-20, 24, 300)
    two = [R.slip_quantile_fit(xs, obs_sand(xs, rng)), R.slip_quantile_fit(xc, obs_crust(xc, rng))]
    Hs = Ws = 48
    ii, jj = np.mgrid[0:Hs, 0:Ws]
    soil = np.zeros((Hs, Ws), dtype=np.int64)
    soil[(ii >= 10) & (ii <= 38) & (jj >= 16) & (jj <= 32)] = 1
    scene = {}
    for incl in (12.0, 0.0):
        Z = ((Hs - 1 - ii) * math.tan(math.radians(incl))).astype(float)
        scene[incl] = {a: R.risk_aware_path(R.cvar_cost_map(Z, 1.0, two, alpha=a, s_max=S_MAX, soil_map=soil), (45, 24), (2, 24))["path"]
                       for a in (0.0, ALPHA)}
    cr = {incl: [int(sum(soil[tuple(q)] for q in scene[incl][a])) for a in (0.0, ALPHA)] for incl in scene}
    gate("12° の斜面: 平均は殻を突っ切り、CVaR は避ける", cr[12.0][0] >= 20 and cr[12.0][1] <= 3,
         "(殻の上のセル数 %d → %d)" % tuple(cr[12.0]))
    gate("平らな地面: 2 本は同じ経路(差が出ないはずの場面)", np.array_equal(scene[0.0][0.0], scene[0.0][ALPHA]),
         "(殻の上のセル数 %d / %d)" % tuple(cr[0.0]))

    # 図
    if figs.enabled():
        t_fig = time.time()
        _figures(Zfull, D, cell, res, start, goal, mq, mg, x0, y0, curves, slopes, trac, mj, scene, soil, data is not None)
        n_fig = len(figs.manifest())
        gate("図が書けて空でない", n_fig >= 6 and not figs.errors(), "(%d 枚、errors %r、%.1f s)" % (n_fig, figs.errors(), time.time() - t_fig))

    n_ok = sum(ok for _, ok in _GATES)
    print("\n門 %d / %d、所要 %.1f s" % (n_ok, len(_GATES), time.time() - t_all))
    if n_ok == len(_GATES) and not figs.errors():
        print("PASS")
        return 0
    print("FAIL")
    return 1


def _figures(Zfull, D, cell, res, start, goal, mq, mg, x0, y0, curves, slopes, trac, mj, scene, soil, real):
    # (1) 実地形の等倍の地図: 陰影 + 最悪の向きの CVaR の滑り + 2 経路
    hs = hillshade(Zfull, DTM_CELL)
    worst = res[ALPHA][0]["worst_slip"]
    wf = np.repeat(np.repeat(np.nan_to_num(worst, nan=1.0), F_PLAN, 0), F_PLAN, 1)
    col = colormap(wf, 0.0, S_MAX)
    img = (0.55 * hs[..., None] + 0.45 * col) * (0.35 + 0.65 * hs[..., None])
    img = np.clip(img / img.max(), 0, 1)
    sc = F_PLAN
    p0 = res[0.0][1]["path"] * sc + sc / 2
    p9 = res[ALPHA][1]["path"] * sc + sc / 2
    polyline(img, p9, C_CVAR, 4.0)
    polyline(img, p0, C_MEAN, 2.6, dash=14)              # 平均の経路を上に破線で(重なる区間でも両方見える)
    stamp(img, [np.array(start) * sc + sc / 2], (1, 1, 1), 8)
    stamp(img, [np.array(goal) * sc + sc / 2], (0, 0, 0), 8)
    e0, e9 = res[0.0][2], res[ALPHA][2]
    img = label(img, "orange dashed = shortest on mean slip   blue = minimum slip risk (CVaR %.1f)" % ALPHA, (10, 10), 15)
    img = label(img, "colour = worst-direction CVaR slip (teal 0 -> yellow -> orange %.1f, no-go beyond)" % S_MAX, (10, 38), 13)
    img = label(img, "mean path: %.0f s, worst CVaR slip %.2f   |   risk-aware path: %.0f s, worst CVaR slip %.2f"
                % (e0["time_mean"], e0["max_cvar_slip"], e9["time_mean"], e9["max_cvar_slip"]), (10, 64), 13)
    src = "HiRISE DTEEC_017951_1965_017806_1965_A01 (NASA/JPL/University of Arizona), 0.88 m/px" if real else "synthetic fBm terrain"
    img = label(img, src, (1014, 1014), 12, anchor="rb")
    figs.save("dtm_two_paths", (img * 255).astype(np.uint8),
              caption="real Mars terrain at 1:1 pixels: the mean-slip shortest path and the minimum slip-risk path")
    # 経路に沿った滑りの予測と 90 % の帯(下りは −s = 空走・横滑りの大きさで測る)
    ser, sty, colr = [], [], []
    for a, nm, cname in ((0.0, "mean path", "emphasis"), (ALPHA, "risk-aware path", "right")):
        ev = res[a][2]
        pth = res[a][1]["path"]
        dz = np.diff(D[tuple(pth.T)])
        dist = np.concatenate([[0.0], np.cumsum(np.hypot(cell * np.hypot(*np.diff(pth, axis=0).T), dz))])[1:]
        pr = R.slip_predict(mq, ev["pitch"], 0.9)
        up = ev["pitch"] >= 0
        lo = np.where(up, pr["lower"], -pr["upper"])
        hi = np.where(up, pr["upper"], -pr["lower"])
        ser += [(nm + " (mean)", dist, ev["mean_slip"]), (nm + " 90 %", dist, lo), ("", dist, hi)]
        sty += [None, "dotted", "dotted"]
        colr += [cname] * 3
    L_max = max(float(x.max()) for _, x, _ in ser)
    ser.append(("no-go slip %.1f" % S_MAX, np.array([0.0, L_max]), np.full(2, S_MAX)))
    sty.append("dashed")
    colr.append("wrong")
    yl = (min(float(y.min()) for _, _, y in ser) - 0.02, max(float(y.max()) for _, _, y in ser) + 0.02)
    figs.save_plot("slip_band_along_paths", ser, xlabel="distance along path [m]", ylabel="predicted slip (downhill: skid)",
                   title="slip and its 90 % band along the two paths", size=(1024, 420), ylim=yl,
                   styles=sty, colors=colr, caption="the risk-aware path trims the peaks of the upper band at almost no extra length")

    # (2) GIF: ローバーがリスク最小の経路を進み、測った滑りで帯を更新する
    path = res[ALPHA][1]["path"]
    pitch = res[ALPHA][2]["pitch"]
    rng = np.random.default_rng(3)
    meas_x = list(np.clip(rng.normal(0, 3, 12), -6, 6))           # 出発前: 平地の試走 12 点だけ
    meas_y = list(obs_sand(np.array(meas_x), rng))
    frames = []
    base = np.clip(0.25 + 0.75 * hillshade(D, cell), 0, 1)
    base = np.repeat(np.repeat(base, 2, 0), 2, 1)
    xs = np.linspace(-20, 26, 93)
    n_steps = len(pitch)
    picks = np.unique(np.linspace(0, n_steps, 28).astype(int))
    # 右の枠: 軸と真の曲線は 1 回だけ examplefig.render_plot で描き(1 枚 2 s かかる)、点と帯はコマごとに numpy で重ねる。
    # 座標の写像は render_plot と同じ(枠 (72, 44, w − 96, h − 108)、y の範囲は上下に 6 % 広げる)。
    XL, YL = (-20.0, 26.0), (-0.4, 1.05)
    ok_t = xs <= _TRUTH["max"]                           # 登れる最大の角より先は立ち往生(曲線を描かない)
    base_plot = np.asarray(figs.render_plot([("truth: Wong-Reece dry sand (dashed)", xs[ok_t], sand_truth()(xs[ok_t]))],
                                            xlabel="edge pitch [deg]", ylabel="slip ratio   |   green band = 90 %, dots = measured",
                                            title="slip vs slope, updated as the rover drives", size=(512, 512),
                                            xlim=XL, ylim=YL, styles=["dashed"], colors=["reference"]))[:512, :512].copy()
    pad = 0.06 * (YL[1] - YL[0])
    ylo, yhi = YL[0] - pad, YL[1] + pad

    def to_px(xv, yv):
        return (44 + (yhi - yv) / (yhi - ylo) * (512 - 108), 72 + (xv - XL[0]) / (XL[1] - XL[0]) * (512 - 96))

    t_gif = time.time()
    for kk, upto in enumerate(picks):
        if kk > 0:
            for e in range(picks[kk - 1], upto):
                meas_x.append(float(pitch[e]))
                meas_y.append(float(obs_sand(np.array([pitch[e]]), rng)[0]))
        mx, my = np.array(meas_x), np.array(meas_y)
        if mx.size >= 10 and np.ptp(mx) > 0:
            m = R.slip_quantile_fit(mx, my, n_knots=min(6, mx.size // 3), calibrate=0.25 if mx.size >= 40 else 0.0)
            pr = R.slip_predict(m, xs, 0.9)
        left = np.repeat(base[..., None], 3, 2).copy()
        polyline(left, path * 2 + 1, (0.6, 0.6, 0.6), 1.5, dash=8)
        if upto > 0:
            polyline(left, path[:upto + 1] * 2 + 1, C_CVAR, 2.2)
        stamp(left, [path[min(upto, n_steps)] * 2 + 1], (0.84, 0.37, 0.0), 6)
        left = label(left, "rover on the risk-aware path: %d / %d edges" % (upto, n_steps), (6, 6), 13)
        right = base_plot.copy()
        band = np.zeros(right.shape[:2], dtype=bool)
        for xv, lo_v, hi_v in zip(xs, pr["lower"], pr["upper"]):
            c0 = int(round(to_px(xv, 0)[1]))
            r_hi, r_lo = to_px(xv, min(hi_v, YL[1]))[0], to_px(xv, max(lo_v, YL[0]))[0]
            band[int(max(r_hi, 44)):int(min(r_lo, 404)) + 1, max(c0 - 3, 72):min(c0 + 3, 488)] = True
        right[band] = 0.65 * right[band] + 0.35 * np.array([0.0, 0.62, 0.45])
        polyline(right, [to_px(xv, yv) for xv, yv in zip(xs, pr["median"]) if YL[0] <= yv <= YL[1]], (0.0, 0.5, 0.35), 1.6)
        inside = (my >= YL[0]) & (my <= YL[1])
        stamp(right, [to_px(xv, yv) for xv, yv in zip(mx[inside], my[inside])], (0.2, 0.2, 0.2), 2.2)
        stamp(right, [to_px(xv, yv) for xv, yv in zip(mx[-3:], my[-3:]) if YL[0] <= yv <= YL[1]], (0.84, 0.37, 0.0), 4.0)
        right = label(right, "n = %d measured slips (orange = newest)" % mx.size, (80, 50), 12)
        frames.append((np.clip(np.hstack([left, right]), 0, 1) * 255).astype(np.uint8))
    print("    (GIF のコマ組み %d コマ %.1f s)" % (len(frames), time.time() - t_gif))
    figs.save_gif("rover_slip_update", frames, fps=4,
                  caption="as the rover drives, measured slips tighten the slip-vs-slope band (quantile regression, 90 %)")

    # (3) 滑り–傾きの帯(最終の模型、GP と分位点回帰)
    pq, pg = R.slip_predict(mq, xs, 0.9), R.slip_predict(mg, xs, 0.9)
    figs.save_plot("slip_band_gp_vs_quantile",
                   [("truth (stuck beyond %.1f deg)" % _TRUTH["max"], xs[ok_t], sand_truth()(xs[ok_t])), ("data", x0, y0),
                    ("quantile 90 %", xs, pq["lower"]), ("", xs, pq["upper"]),
                    ("GP 90 %", xs, pg["lower"]), ("", xs, pg["upper"])],
                   xlabel="pitch [deg]", ylabel="slip ratio", title="90 % bands: quantile regression (conformal) vs GP",
                   size=(900, 520), xlim=(-20, 30), ylim=(-0.5, 1.1),
                   kinds=["line", "scatter", "line", "line", "line", "line"],
                   styles=["dashed", None, None, None, "dotted", "dotted"],
                   colors=["reference", "neutral", "right", "right", "wrong", "wrong"],
                   caption="GP's uniform noise is too wide on gentle slopes, too narrow on steep ones, and reverts to the mean past the data")
    # (4) 牽引–滑り
    figs.save_plot("traction_slip",
                   [("dry sand DP/W", trac["dry_sand"]["slip"], trac["dry_sand"]["DP_over_W"]),
                    ("M90 simulant DP/W", trac["mars_simulant_m90"]["slip"], trac["mars_simulant_m90"]["DP_over_W"]),
                    ("sin(20 deg)", np.array([0, 0.9]), np.full(2, math.sin(math.radians(20))))],
                   xlabel="slip ratio", ylabel="drawbar pull / wheel load", title="Wong-Reece traction vs slip (one wheel, Mars g)",
                   size=(900, 480), styles=[None, None, "dashed"], colors=["right", "emphasis", "reference"],
                   caption="the slope a wheel can hold is where DP/W reaches sin(slope)")
    # (5) MuJoCo
    if mj is not None:
        sl = np.arange(0, 40, 1.0)
        okr = curves["rigid_ground"]["feasible"] & (slopes >= 0)     # 登れない角(nan)と下りは描かない
        oks = curves["dry_sand"]["feasible"] & (slopes >= 0)
        ser = [("Wong-Reece rigid ground", slopes[okr], curves["rigid_ground"]["slip"][okr]),
               ("MuJoCo rigid wheel (mu 0.5)", sl, np.clip(mj["rigid"], -0.1, 1.2)),
               ("Wong-Reece dry sand", slopes[oks], curves["dry_sand"]["slip"][oks]),
               ("MuJoCo (mu = tan 33.3 deg)", sl, np.clip(mj["sand_mu"], -0.1, 1.2))]
        figs.save_plot("mujoco_vs_wong_reece", ser, xlabel="slope [deg]", ylabel="steady slip ratio",
                       title="rigid simulator agrees only on rigid ground", size=(900, 480), xlim=(0, 40), ylim=(-0.1, 1.2),
                       styles=[None, "dashed", None, "dashed"], colors=["reference", "reference", "wrong", "wrong"],
                       caption="no sinkage, no shear deformation: a rigid-contact simulator cannot show soft-soil slip")
    # (6) 2 種の土の場面
    tiles = []
    for incl in (12.0, 0.0):
        im = np.ones((48, 48, 3)) * 0.92
        im[soil == 1] = (0.96, 0.80, 0.55)
        im = np.repeat(np.repeat(im, 8, 0), 8, 1)
        polyline(im, scene[incl][0.0] * 8 + 4, C_MEAN, 3.0, dash=12)
        polyline(im, scene[incl][ALPHA] * 8 + 4, C_CVAR, 3.0)
        im = label(im, "%g deg incline, crust patch%s" % (incl, "" if incl else " (both paths coincide)"), (6, 6), 13)
        tiles.append(im)
    figs.save("two_soils_scene", (np.hstack([tiles[0], np.ones((384, 8, 3)), tiles[1]]) * 255).astype(np.uint8),
              caption="left: on a 12 deg incline the risk-aware path avoids the bimodal crust; right: on flat ground both coincide")


if __name__ == "__main__":
    raise SystemExit(main())
