# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_camera_calibration — 再投影誤差 0.05 px は**何も保証しない**。

    py -3.11 examples/poc_camera_calibration.py

【この PoC が答える問題】
現場では「再投影誤差 0.2 px だから良い校正だ」と言う。これは**誤り**である。
再投影誤差は「私の推定したパラメータで観測を再現できるか」しか測っておらず、
「そのパラメータが正しいか」は一切測っていない。焦点距離 fx と板までの距離 Z は
画像上ではほぼ同じ効果を持つので、fx を 20 % 間違えて Z も 20 % 間違えれば
**画素は 1 つも動かない**。板を傾けなければこの相殺を破る情報が観測に入らない。

そこで内部パラメータと各姿勢を**自分で決めて**格子点を投影し、そこから推定し
直して真値と突き合わせる。誤差は焦点距離・主点・歪み・姿勢に分けて出す。

    EXTEND: 実データ(自分で撮ったチェッカーボード)に差し替えるには
    ``observe`` を捨てて ``obs_list`` を実測の角点 (N,2) 画素 (x=col, y=row) の
    リストに置き換えるだけでよい。角点検出は fullseye 側にもある
    (``caltab.find_marks_and_pose`` / ``fs.apply(img, "hx_find_caltab")``)。
    ``BOARD`` の格子間隔 ``SPACING`` は**実測したミリ値**を入れること —— 印刷や
    貼り付けの伸びが 0.3 % あれば焦点距離も 0.3 % ずれる(この PoC の第 4 章で
    見る「配置の悪さ」より小さいが、それでも系統誤差として残り続ける)。
    真値が無い実データでは第 2 章の「真の誤差」は出せないので、代わりに
    第 4 章の ``sigma_fx``(ヤコビアンから出す標準偏差)を見る。

【章立て】
 1. 真値と観測の作り方 —— 往復で検算する
 2. 良い配置での校正 —— 誤差を成分ごとに分ける
 3. ゼロ点 —— 「歪みを無視」「主点は画像中心」に勝てるか(勝てない条件がある)
 4. ★ 再投影誤差はほぼ同じなのに焦点距離の誤差が桁で違う配置
 5. なぜ相殺するのか —— fx と Z の比は保存される
 6. 壊れる条件 —— 退化配置 / 中央のみ / 雑音
 7. 速度  /  8. 実写の校正板 —— OpenCV の 13 枚と、その質感で描いた板(写真が無ければ記録値)

【★ この PoC が出した道具の穴】
(a) **【解消済み 2026-09-19】内部パラメータ推定がファサードから呼べなかった**。
    ``calib.camera_calibration``(Zhang 法)がリポジトリ唯一の内部行列推定だが、
    以前は ``import fullseye as fs`` の公開名に入っておらず、この PoC は
    ``import calib`` で裸のモジュールを直接叩いていた。現在は ``fs.camera_calibration``
    として facade に露出し(能力ノート ``camera-intrinsics-calibration``、最小例
    ``examples/camera_intrinsics_calibration.py``)、下の ``import calib`` は
    この PoC の教材的な直呼びとして残している(挙動の比較のため)。
(b) **``fs.reprojection_error`` に歪み引数が無い**。歪んだ実画像の観測に対して
    真の K・真の姿勢を渡しても、返るのは「歪み分の誤差」であって 0 ではない
    (第 1 章の実測で 9.42 px)。歪みのあるレンズで使うと**正しい答えを
    不合格と判定する**。正しく使うには先に ``fs.undistort_points`` を通す必要が
    あるが、シグネチャからはそれが読み取れない。
(c) **``camera_calibration`` の退化検出の門は、歪みのあるカメラでは発火しない**。
    実装は ``sv[-2] <= 1e-8 * sv[0]`` で「全視点が正面平行」を弾く。**歪みが
    無ければ設計どおり働く** —— 傾き 0 度で比 3.821e-14、0.05 度で 8.584e-10、
    どちらも拒否する(この PoC の初稿では「門は死んでいる」と書いたが、
    歪みなしで測り直したら発火した。**歪みが原因**だった)。
    ところが現実的な樽型歪み k1=-0.18 を入れると、平面ホモグラフィのモデル
    そのものが合わなくなって零空間が濁り、比が**傾きに関係なく 1.9e-06 前後に
    張り付く**(0 度 1.916e-06 / 0.05 度 1.935e-06 / 0.2 度 2.005e-06)。
    条件は 2 つ揃ったときだけで、**歪みがある**ことと、**視点間で板が横に動く**
    こと —— どちらか片方なら門は設計どおり鳴る。そして実際の校正は板を手で
    動かして撮るので必ず両方が揃い、この門は現場では鳴らない。実際に止めるのは
    後段の「K が非有限/非正」の門になる。
    **しきい値を上げれば済む話ではない**: 歪みありでは完全退化 1.92e-06 と
    傾き 2 度 4.42e-06 の差が 2.3 倍しかなく、分ける線が引けない。
    2026-09-06 の対応は (1) しきい値は据え置き (2) 比を
    ``orientation_rank_ratio`` として返す (3) 後段の門の文言に「板を傾けよ」を
    入れる —— 直せないものを直したことにせず、判断材料を渡す形にした。
    2026-11-09 に、比とは別の**雑音込みの門**が足された(op 監査 g2_calib_ct): 閉形式を
    解いたあと、ホモグラフィの残差で画像点を揺らして 32 回解き直し、K の相対標準偏差が
    5 % を超えたら拒否する。第 6 章の表では傾き 5 度を拒否するようになった(広がり 10.6 %、
    通していた頃の fx 誤差 −31.8 %)。ただし歪みによる**偏り**は測らない(8 度は広がり 2.5 % で
    通過し、fx を 18.5 % 誤る)。
(c2) **``camera_calibration`` は偏りを含む不確かさを返さない**。返るのは ``reproj_rms``
    —— まさに本 PoC が「保証しない」と示している数字 —— と、2026-11-09 からは雑音だけから
    見積もった広がり ``intrinsics_rel_std``(偏りは含まない、上の (c) を見よ)。
    第 3・4 章で見るとおり、配置の良し悪しを映すのは ``sigma_fx`` / ``sigma_cx``
    (ヤコビアンの逆行列の対角)であって再投影誤差ではない。
(c3) **閉形式は歪みを無視するので答えとしては使えない**。傾き 8 度で fx を
    18.5 %、傾き 32 度でも 3.1 % 誤る(k1 = -0.18 のレンズ)。初期値としては
    使えるが、``camera_calibration`` の戻り値をそのまま K として使う利用者は
    その旨を docstring から読み取れない。
(d) **座標規約が兄弟 API と食い違う**。``camera.project_points`` は (x, y) を
    返すのに ``calib.camera_calibration`` の画像点入力は (row, col)。docstring に
    は書いてあるが、``obs[:, ::-1]`` の入れ忘れは fx と fy が入れ替わるだけで
    例外は出ず、再投影誤差も小さいままになりうる。
(e) **歪みを含む非線形バンドル調整が無い**。この PoC は ``scipy.optimize.
    least_squares`` で 60 行ほど自前で書いた(scipy は fullseye の必須依存)。
    ``fs.intrinsic_matrix`` / ``fs.rodrigues`` / ``fs.project_points`` /
    ``fs.distort_points`` の 4 つを合成するだけなので、族としては 1 op 分の穴。
"""
from __future__ import annotations

import os, sys, time  # noqa: E401
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # repo 直下を先に(editable install の古い本体を読まない)
import numpy as np
from scipy.optimize import least_squares

import fullseye as fs
import calib                      # ★ 穴 (a)【解消済み】: 現在は fs.camera_calibration で公開。ここは教材的直呼び
import examplefig as figs         # ★fullseye を先に import しないと解決しない

# ── 真値(私が決める)────────────────────────────────────────────────────────── #
IMG_W, IMG_H = 1280, 960
CENTER = ((IMG_W - 1) / 2.0, (IMG_H - 1) / 2.0)          # 画像中心 = ゼロ点の主点
TRUE_FX, TRUE_FY = 1200.0, 1188.0                        # 画素はわずかに非正方
TRUE_CX, TRUE_CY = 648.0, 492.0                          # 中心から (+8.5, +12.5) px
TRUE_DIST = np.array([-0.180, 0.050, 6.0e-4, -4.0e-4])   # [k1, k2, p1, p2]
K_TRUE = fs.intrinsic_matrix(TRUE_FX, TRUE_FY, TRUE_CX, TRUE_CY)

COLS, ROWS, SPACING = 9, 7, 0.030                        # 9x7 格子, 30 mm 間隔
N_VIEWS = 10
NULL_B_DCX = abs(CENTER[0] - TRUE_CX)                    # ゼロ点 B が背負う主点誤差


def board_points(cols: int = COLS, rows: int = ROWS, spacing: float = SPACING) -> np.ndarray:
    """z=0 平面の格子ターゲット (N, 3)。原点は板の中心。"""
    xs = (np.arange(cols) - (cols - 1) / 2.0) * spacing
    ys = (np.arange(rows) - (rows - 1) / 2.0) * spacing
    xx, yy = np.meshgrid(xs, ys)
    return np.stack([xx.ravel(), yy.ravel(), np.zeros(xx.size)], axis=1)


def make_poses(n: int, tilt_deg: float, offset_m: float, z_lo: float, z_hi: float):
    """n 視点の (R, t)。``tilt_deg`` は光軸に垂直な軸まわりの傾き量、
    ``offset_m`` は視野内での板の振り幅、z は撮影距離の範囲。"""
    poses = []
    for i in range(n):
        phi = 2.0 * np.pi * i / n + 0.30
        axis = np.array([np.cos(phi), np.sin(phi), 0.0])          # 面内軸まわり = 傾き
        rvec = axis * np.deg2rad(tilt_deg)
        rvec = rvec + np.array([0.0, 0.0, 1.0]) * np.deg2rad(12.0 * np.sin(3.0 * phi))
        R = fs.rodrigues(rvec)
        z = z_lo + (z_hi - z_lo) * (i / (n - 1) if n > 1 else 0.5)
        t = np.array([offset_m * np.cos(2.0 * phi),
                      offset_m * 0.72 * np.sin(2.0 * phi), z])
        poses.append((R, t))
    return poses


def observe(obj, poses, sigma_px: float, seed: int = 0):
    """真値カメラで格子点を撮る。ピンホール投影 -> 歪み -> 画素雑音。"""
    rng = np.random.default_rng(seed)
    obs = []
    for R, t in poses:
        uv, depth = fs.project_points(obj, K_TRUE, R, t)
        if np.any(depth <= 0):
            raise ValueError("カメラ背後の点がある —— 配置が不正")
        uvd = fs.distort_points(uv, K_TRUE, TRUE_DIST)
        if sigma_px > 0:
            uvd = uvd + rng.normal(0.0, sigma_px, uvd.shape)
        obs.append(uvd)
    return obs


def frame_fill(obs) -> float:
    """観測点が画像のどれだけの範囲に散っているか(面積比 0..1)。"""
    p = np.vstack(obs)
    return float((np.ptp(p[:, 0]) / IMG_W) * (np.ptp(p[:, 1]) / IMG_H))


# ── 校正(自前の最小バンドル調整。★ 穴 (e))──────────────────────────────────── #
def _unpack(p, n_views, fit_dist, fit_pp):
    fx, fy = p[0], p[1]
    i = 2
    if fit_pp:
        cx, cy = p[2], p[3]
        i = 4
    else:
        cx, cy = CENTER
    if fit_dist:
        dist = p[i:i + 4]
        i += 4
    else:
        dist = np.zeros(4)
    return fx, fy, cx, cy, dist, p[i:].reshape(n_views, 6)


def calibrate(obj, obs, fit_dist: bool = True, fit_pp: bool = True, trace=None):
    """内部パラメータ + 歪み + 全姿勢を同時に最小二乗で解く。

    初期値は Zhang 法(``calib.camera_calibration``、歪み無視の閉形式)+ 視点ごとの
    ``fs.solve_pnp``。残差は ``distort_points(project_points(...))`` の順方向モデル。
    Zhang が拒否した配置では「焦点距離 ~ 画像幅」という経験則の初期値に落として
    先へ進む(第 6 章 a の退化配置がこの経路。最適化は止まらず答えを返す)。

    ``trace`` に list を渡すと、残差を評価するたびに ``(パラメータ, 残差二乗和)`` を積む
    (動画用。計算そのものは変えない —— 既定の None では何も積まない)。"""
    n = len(obs)
    try:
        # ★ 穴 (d): camera_calibration の画像点は (row, col)。project_points は (x, y)。
        z = calib.camera_calibration(obj[:, :2], [o[:, ::-1] for o in obs])
        fx0, fy0, cx0, cy0 = z["fx"], z["fy"], z["cx"], z["cy"]
        init = "Zhang"
        if not (200.0 < fx0 < 2.0e4 and 200.0 < fy0 < 2.0e4):
            raise ValueError(f"Zhang の K が非現実的 (fx={fx0:.0f}, fy={fy0:.0f})")
    except ValueError:
        fx0 = fy0 = float(IMG_W)                     # 経験則: 焦点距離 ~ 画像幅
        cx0, cy0 = CENTER
        init = "経験則(Zhang 拒否)"
    if not fit_pp:
        cx0, cy0 = CENTER

    head = [fx0, fy0] + ([cx0, cy0] if fit_pp else []) + ([0.0] * 4 if fit_dist else [])
    K0 = fs.intrinsic_matrix(fx0, fy0, cx0, cy0)
    tail = []
    for o in obs:
        R, t, _ = fs.solve_pnp(obj, o, K0)
        tail.append(np.concatenate([fs.rotation_log(R), t]))
    p0 = np.concatenate([np.asarray(head, float), np.concatenate(tail)])

    def resid(p):
        fx, fy, cx, cy, dist, rt = _unpack(p, n, fit_dist, fit_pp)
        K = fs.intrinsic_matrix(fx, fy, cx, cy)
        out = np.empty((n, obj.shape[0], 2))
        for k in range(n):
            uv, _ = fs.project_points(obj, K, fs.rodrigues(rt[k, :3]), rt[k, 3:])
            out[k] = fs.distort_points(uv, K, dist) - obs[k]
        if trace is not None:
            trace.append((np.array(p, dtype=float, copy=True), float(np.sum(out * out))))
        return out.ravel()

    t0 = time.perf_counter()
    sol = least_squares(resid, p0, method="lm", xtol=1e-13, ftol=1e-13, max_nfev=20000)
    elapsed = 1e3 * (time.perf_counter() - t0)

    fx, fy, cx, cy, dist, rt = _unpack(sol.x, n, fit_dist, fit_pp)
    m, npar = sol.fun.size, sol.x.size
    rms = float(np.sqrt(np.mean(sol.fun.reshape(-1, 2) ** 2) * 2.0))   # 点あたり px
    # ヤコビアンから推定分散: cov = s2 * (J^T J)^-1(これが「保証」の側の数字)
    s2 = float(2.0 * sol.cost / max(m - npar, 1))
    try:
        cov = s2 * np.linalg.inv(sol.jac.T @ sol.jac)
        sig = np.sqrt(np.clip(np.diag(cov), 0.0, None))
    except np.linalg.LinAlgError:
        sig = np.full(npar, np.inf)
    return {"fx": fx, "fy": fy, "cx": cx, "cy": cy, "dist": np.asarray(dist, float),
            "rt": rt, "rms": rms, "sigma_fx": float(sig[0]),
            "sigma_cx": float(sig[2]) if fit_pp else float("nan"),
            "init": init, "ms": elapsed, "nfev": sol.nfev}


def zhang_null_ratio(obj, obs) -> float:
    """Zhang 法の退化検出が見る量 sv[-2] / sv[0] を再現する(``calib`` 内部と同じ式)。
    実装は ``sv[-2] <= 1e-8 * sv[0]`` で退化を弾こうとしている。"""
    V = []
    for o in obs:
        H = calib._homography_dlt(obj[:, :2], o)      # o は (x, y) —— 内部と同じ向き
        V.append(calib._vij(H, 0, 1))
        V.append(calib._vij(H, 0, 0) - calib._vij(H, 1, 1))
    sv = np.linalg.svd(np.asarray(V), compute_uv=False)
    return float(sv[-2] / sv[0])


def pose_errors(rt, poses):
    """姿勢誤差: 回転角 [deg] と並進 [mm] の最大値。"""
    rot, tra = [], []
    for k, (R, t) in enumerate(poses):
        Re = fs.rodrigues(rt[k, :3])
        rot.append(np.degrees(np.linalg.norm(fs.rotation_log(Re @ R.T))))
        tra.append(1e3 * np.linalg.norm(rt[k, 3:] - t))
    return float(np.max(rot)), float(np.max(tra))


def report(name, r, poses, extra=""):
    dfx = 100.0 * abs(r["fx"] - TRUE_FX) / TRUE_FX
    dcx = abs(r["cx"] - TRUE_CX)
    dcy = abs(r["cy"] - TRUE_CY)
    dk1 = abs(r["dist"][0] - TRUE_DIST[0])
    rot, tra = pose_errors(r["rt"], poses)
    print(f"  {name:<22}{r['rms']:>9.4f}{dfx:>10.3f}{dcx:>9.2f}{dcy:>8.2f}"
          f"{dk1:>10.4f}{rot:>9.3f}{tra:>9.2f}  {extra}")


HEAD = (f"  {'配置 / モデル':<22}{'再投影RMS':>9}{'fx誤差%':>10}{'|dcx|':>9}{'|dcy|':>8}"
        f"{'|dk1|':>10}{'姿勢deg':>9}{'姿勢mm':>9}")

# 再投影 RMS は 1 点あたりの距離 sqrt(dx^2+dy^2) の二乗平均平方根(OpenCV の
# calibrateCamera が返す量と同じ定義)。成分ごとに sigma px の白色雑音なら
# 期待値は sigma * sqrt(2) —— sigma=0.05 px なら 0.0707 px。


def sweep_seeds(obj, poses, sigma, seeds=(2, 7, 11)):
    """同じ配置を種違いで解き、成分別の誤差を平均する(1 回の当たり外れを排す)。"""
    acc = {"rms": [], "fx_full": [], "fx_nodist": [], "dcx_full": [], "sigma_cx": []}
    for sd in seeds:
        ob = observe(obj, poses, sigma_px=sigma, seed=sd)
        full = calibrate(obj, ob, fit_dist=True, fit_pp=True)
        nod = calibrate(obj, ob, fit_dist=False, fit_pp=True)
        acc["rms"].append(full["rms"])
        acc["fx_full"].append(100 * abs(full["fx"] - TRUE_FX) / TRUE_FX)
        acc["fx_nodist"].append(100 * abs(nod["fx"] - TRUE_FX) / TRUE_FX)
        acc["dcx_full"].append(abs(full["cx"] - TRUE_CX))
        acc["sigma_cx"].append(full["sigma_cx"])
    return {k: float(np.mean(v)) for k, v in acc.items()}


# ── 動画: 最適化が収束していく過程と、fx を固定して振ったときの相殺 ───────────── #
def _vid_txt(img, s, xy, anchor="lt", fs_=12):
    import annotate as AN
    return np.asarray(AN.text_box(img, s, xy, anchor=anchor, font_size=fs_), dtype=np.float64)


def _fit_fixed_fx(obj, obs, fx, p_start):
    """fx だけを固定し、残り(fy, 主点, 歪み, 全姿勢)を解き直す。動画の第 2 部専用。"""
    n = len(obs)

    def resid(q):
        pp = np.concatenate([[fx], q])
        _fx, fy, cx, cy, dist, rt = _unpack(pp, n, True, True)
        K = fs.intrinsic_matrix(_fx, fy, cx, cy)
        out = np.empty((n, obj.shape[0], 2))
        for k in range(n):
            uv, _ = fs.project_points(obj, K, fs.rodrigues(rt[k, :3]), rt[k, 3:])
            out[k] = fs.distort_points(uv, K, dist) - obs[k]
        return out.ravel()

    sol = least_squares(resid, np.asarray(p_start, float)[1:], method="lm", max_nfev=4000)
    pp = np.concatenate([[fx], sol.x])
    return pp, float(np.sqrt(np.mean(sol.fun.reshape(-1, 2) ** 2) * 2.0))


def fig_convergence_video(obj):
    """傾き 32 度(良い配置)と 2 度(ほぼ正面)を並べ、2 部構成の動画を作る。

    第 1 部: バンドル調整の反復。残差二乗和がそれまでの最良を更新した評価点だけを拾う
    (``calibrate(trace=...)`` で記録。数値微分のための評価は最良を更新しないので落ちる)。
    第 2 部: fx を真値の 0.92〜1.08 倍に**固定**して残りを解き直す。悪い配置では板までの距離 Z が
    fx と同じ比で動いて画素がほとんど動かず、再投影 RMS は平らなまま。
    ★図を出すときだけ計算する。観測は本文 4 章と同じ(seed=3、``observe`` は自分の Generator を使う)。
    """
    if not figs.enabled():
        return None
    import annotate as AN
    import imagedraw as ID

    cfgs = (("傾き 32 度(良い配置)", 32.0), ("傾き 2 度(ほぼ正面)", 2.0))
    runs = []
    for label, tilt in cfgs:
        poses = make_poses(N_VIEWS, tilt_deg=tilt, offset_m=0.14, z_lo=0.55, z_hi=0.85)
        ob = observe(obj, poses, sigma_px=0.05, seed=3)
        tr = []
        r = calibrate(obj, ob, trace=tr)
        best, steps = np.inf, []
        for prm, c in tr:
            if c < best * (1.0 - 1e-3):
                best = c
                steps.append(prm)
        runs.append(dict(label=label, poses=poses, obs=ob, r=r, steps=steps,
                         p_final=np.asarray(tr[-1][0]) if False else None))
        # 最終解のパラメータ(trace の中の最良)
        runs[-1]["p_best"] = min(tr, key=lambda t: t[1])[0]

    def state(run, prm):
        n = len(run["obs"])
        fx, fy, cx, cy, dist, rt = _unpack(prm, n, True, True)
        K = fs.intrinsic_matrix(fx, fy, cx, cy)
        uv, _ = fs.project_points(obj, K, fs.rodrigues(rt[0, :3]), rt[0, 3:])
        proj0 = fs.distort_points(uv, K, dist)
        res = []
        for k in range(n):
            u2, _ = fs.project_points(obj, K, fs.rodrigues(rt[k, :3]), rt[k, 3:])
            res.append(fs.distort_points(u2, K, dist) - run["obs"][k])
        rms_ = float(np.sqrt(np.mean(np.concatenate(res) ** 2) * 2.0))
        zt = np.array([t[2] for _, t in run["poses"]])
        return dict(fx=float(fx), proj0=proj0, rms=rms_, zr=float(np.mean(rt[:, 5] / zt)),
                    z0=float(rt[0, 5]), z0t=float(zt[0]))

    # 第 2 部: fx を固定して振る(最終解から温めて開始)
    ratios = np.round(np.linspace(0.92, 1.08, 25), 4)
    for run in runs:
        prof = []
        pb = np.asarray(run["p_best"], float)
        n = len(run["obs"])
        for sr in ratios:
            start = pb.copy()
            start[0] = sr * TRUE_FX
            start[1] = pb[1] * sr / (pb[0] / TRUE_FX)
            rt = start[8:].reshape(n, 6)
            rt[:, 5] *= sr / (pb[0] / TRUE_FX)        # Z も同じ比で寄せておく(初期値だけ)
            pp, rr = _fit_fixed_fx(obj, run["obs"], sr * TRUE_FX, start)
            prof.append((float(sr), pp, rr))
        run["prof"] = prof

    SC = 0.25
    PW, PH = int(IMG_W * SC), int(IMG_H * SC)       # 320 x 240
    GAP, TOP, LAB, SIDE, PLOT_H = 12, 34, 64, 58, 226
    FW = 2 * PW + 3 * GAP
    FH = TOP + PH + LAB + SIDE + PLOT_H
    MAG = 20.0
    colors = ((0.35, 0.75, 1.0), (1.0, 0.55, 0.0))

    def panel(f, ci, run, st, head):
        x0 = GAP + ci * (PW + GAP)
        f[TOP:TOP + PH, x0:x0 + PW] = 0.12
        o = run["obs"][0] * SC + np.array([x0, TOP])
        pj = st["proj0"] * SC + np.array([x0, TOP])
        tip = o + MAG * (pj - o)
        tip = np.column_stack([np.clip(tip[:, 0], x0, x0 + PW - 1), np.clip(tip[:, 1], TOP, TOP + PH - 1)])
        for a, b in zip(o, tip):
            f = ID.draw_line(f, tuple(a), tuple(b), color=colors[ci], width=1)
        f = ID.draw_markers(f, o, color=(0.95, 0.95, 0.95), size=1, shape="square", width=1)
        f = np.asarray(f, float)
        f = _vid_txt(f, run["label"], (x0 + 4, TOP + 4), fs_=12)
        dfx = 100.0 * (st["fx"] - TRUE_FX) / TRUE_FX
        f = _vid_txt(f, "%s\n再投影 RMS %.3f px\nfx %.1f(真 %.0f、誤差 %+.2f %%)"
                     % (head, st["rms"], st["fx"], TRUE_FX, dfx), (x0 + 2, TOP + PH + 4), fs_=11)
        # 横から見た図: 視点 0 の板までの距離(真 = 白、推定 = 色)
        y0 = TOP + PH + LAB
        ax = AN.axes_transform((x0 + 8, y0 + 4, PW - 16, 14), (0.40, 0.75), (0.0, 1.0))
        f = np.asarray(AN.axes_frame(f, ax), float)
        for z, c, w in ((st["z0t"], (0.95, 0.95, 0.95), 1), (st["z0"], colors[ci], 3)):
            px, _ = AN.data_to_pixel(ax, z, 0.5)
            f = np.asarray(ID.draw_line(f, (px, y0 + 1), (px, y0 + 21), color=c, width=w), float)
        f = _vid_txt(f, "板までの距離 Z  推定 %.3f m / 真 %.3f m(比 %.4f)" % (st["z0"], st["z0t"], st["z0"] / st["z0t"]),
                     (x0 + 4, y0 + 22), fs_=10)
        return f

    def plots(f, xs_list, rms_list, right_list, xlim, xlab, cur_i, right, xticks):
        """左 = 再投影 RMS(対数)、右 = ``right``("fx": |fx 誤差| % 対数 / "z": Z 比 線形 + 対角線)。"""
        y0 = TOP + PH + LAB + SIDE + 22
        w = (FW - 3 * GAP) // 2 - 50
        hgt = PLOT_H - 82
        allr = np.concatenate([np.asarray(v) for v in rms_list])
        axr = AN.axes_transform((GAP + 44, y0, w, hgt), xlim,
                                (np.log10(0.05), np.log10(max(allr.max(), 0.1) * 1.3)))
        if right == "fx":
            alle = np.concatenate([np.abs(np.asarray(v)) for v in right_list])
            axe = AN.axes_transform((GAP * 2 + 88 + w, y0, w, hgt), xlim,
                                    (np.log10(0.005), np.log10(max(alle.max(), 0.1) * 1.5)))
            rttl = "|fx 誤差| [%%](対数、0.005〜%.1f)" % (max(alle.max(), 0.1) * 1.5)
            conv = lambda v: np.log10(np.maximum(np.abs(np.asarray(v)), 0.005))
        else:
            axe = AN.axes_transform((GAP * 2 + 88 + w, y0, w, hgt), xlim, xlim)
            rttl = "推定 Z / 真 Z(灰の対角線 = fx と同じ比)"
            conv = lambda v: np.asarray(v, float)
        lttl = "再投影 RMS [px](対数、0.05〜%.2f)" % (max(allr.max(), 0.1) * 1.3)
        for ax, ttl in ((axr, lttl), (axe, rttl)):
            f = np.asarray(AN.axes_frame(f, ax), float)
            f = np.asarray(AN.ticks(f, ax, xticks=xticks, yticks=[], font_size=9), float)
            x, y, ww, hh = ax["rect"]
            f = _vid_txt(f, ttl, (x, y - 3), anchor="lb", fs_=10)
            f = _vid_txt(f, xlab, (x + ww // 2, y + hh + 18), anchor="ct", fs_=10)
        if right == "z":
            f = np.asarray(AN.plot_series(f, axe, np.asarray(xlim), np.asarray(xlim), color=(0.5, 0.5, 0.5), width=1), float)
        for ci in range(2):
            xs = np.asarray(xs_list[ci], float)
            k = min(cur_i, len(xs) - 1)
            for ax, ys in ((axr, np.log10(np.asarray(rms_list[ci]))),
                           (axe, conv(right_list[ci]))):
                if k >= 1:
                    f = np.asarray(AN.plot_series(f, ax, xs[:k + 1], ys[:k + 1], color=colors[ci], width=2), float)
                f = np.asarray(AN.plot_series(f, ax, xs[k:k + 1], ys[k:k + 1], kind="scatter",
                                              color=colors[ci], marker_size=3), float)
        return f

    frames = []
    # ---- 第 1 部 ----
    sts = [[state(run, prm) for prm in run["steps"]] for run in runs]
    n1 = max(len(v) for v in sts)
    xs1 = [np.arange(len(v), dtype=float) for v in sts]
    for i in range(n1):
        f = np.full((FH, FW, 3), 0.06)
        f = _vid_txt(f, "第 1 部: バンドル調整の反復(残差 ×%.0f 倍で表示。白 = 観測した角点)" % MAG, (GAP, 8), fs_=13)
        for ci, run in enumerate(runs):
            k = min(i, len(sts[ci]) - 1)
            f = panel(f, ci, run, sts[ci][k], "反復 %d / %d" % (k, len(sts[ci]) - 1))
        f = plots(f, xs1, [[s_["rms"] for s_ in v] for v in sts],
                  [[100 * (s_["fx"] - TRUE_FX) / TRUE_FX for s_ in v] for v in sts],
                  (0.0, float(n1 - 1)), "反復(最良を更新した評価)", i, "fx", list(range(n1)))
        frames += [np.clip(f, 0, 1)] * (8 if i < n1 - 1 else 16)
    # ---- 第 2 部 ----
    prst = [[(sr, state(run, pp), rr) for sr, pp, rr in run["prof"]] for run in runs]
    for i in range(len(ratios)):
        f = np.full((FH, FW, 3), 0.06)
        f = _vid_txt(f, "第 2 部: fx を真値の %.3f 倍に固定し、残りを解き直す" % ratios[i], (GAP, 8), fs_=13)
        for ci, run in enumerate(runs):
            sr, st, rr = prst[ci][i]
            f = panel(f, ci, run, st, "fx 固定 %.3f 倍" % sr)
        f = plots(f, [ratios, ratios], [[t[2] for t in v] for v in prst],
                  [[t[1]["zr"] for t in v] for v in prst],
                  (float(ratios[0]), float(ratios[-1])), "固定した fx / 真の fx", i, "z",
                  [0.92, 0.96, 1.0, 1.04, 1.08])
        frames += [np.clip(f, 0, 1)] * (3 if i < len(ratios) - 1 else 16)

    g, b = runs
    pg, pb_ = g["prof"], b["prof"]
    rg_end = (pg[0][2], pg[-1][2])
    rb_end = (pb_[0][2], pb_[-1][2])
    zb = [state(b, pp)["zr"] for _, pp, _ in (pb_[0], pb_[-1])]
    cap = ("第 1 部: 同じ雑音 0.05 px の観測を、傾き 32 度(左)と 2 度(右)の配置で解く反復。"
           "再投影 RMS はどちらも %.3f / %.3f px まで下がるが、fx は左が %.1f(誤差 %.3f %%)、"
           "右が %.1f(誤差 %.2f %%)で止まる。第 2 部: fx を真値の 0.92〜1.08 倍に固定して残りを"
           "解き直すと、左は RMS が %.2f / %.2f px(両端)まで跳ね上がるのに、右は %.3f / %.3f px と"
           "ほとんど動かない —— 板までの距離 Z が fx と同じ比で動いて(Z 比 %.3f / %.3f)、画素の位置を"
           "保つため。右の配置では再投影誤差が焦点距離について何も言っていない。"
           % (g["r"]["rms"], b["r"]["rms"], g["r"]["fx"], 100 * abs(g["r"]["fx"] - TRUE_FX) / TRUE_FX,
              b["r"]["fx"], 100 * abs(b["r"]["fx"] - TRUE_FX) / TRUE_FX,
              rg_end[0], rg_end[1], rb_end[0], rb_end[1], zb[0], zb[1]))
    print(f"  [動画] 第 2 部の両端 RMS: 良い配置 {rg_end[0]:.3f}/{rg_end[1]:.3f} px, "
          f"悪い配置 {rb_end[0]:.3f}/{rb_end[1]:.3f} px")
    return figs.save_video("calibration_convergence", frames, caption=cap, fps=8.0,
                           gif_every=2, gif_width=None)


def main():
    obj = board_points()
    good = make_poses(N_VIEWS, tilt_deg=32.0, offset_m=0.14, z_lo=0.55, z_hi=0.85)

    print("=== 1. 真値と観測 —— 往復で検算する ===")
    d = fs.decompose_intrinsics(K_TRUE)
    print(f"  真値 fx={d['fx']:.1f} fy={d['fy']:.1f} cx={d['cx']:.1f} cy={d['cy']:.1f}"
          f"  歪み k1={TRUE_DIST[0]:+.3f} k2={TRUE_DIST[1]:+.3f}"
          f" p1={TRUE_DIST[2]:+.1e} p2={TRUE_DIST[3]:+.1e}")
    obs0 = observe(obj, good, sigma_px=0.0)
    uv, dep = fs.project_points(obj, K_TRUE, *good[0])
    back = fs.undistort_points(fs.distort_points(uv, K_TRUE, TRUE_DIST),
                               K_TRUE, TRUE_DIST, iters=30)
    print(f"  歪み -> 歪み除去 の往復残差 最大 {np.abs(back - uv).max():.2e} px")
    print(f"  歪みが画素をどれだけ動かすか 最大 "
          f"{np.abs(fs.distort_points(uv, K_TRUE, TRUE_DIST) - uv).max():.2f} px")
    xc = fs.backproject(uv, dep, K_TRUE)
    print(f"  投影 -> 逆投影 の往復残差 最大 "
          f"{np.abs(xc - (obj @ good[0][0].T + good[0][1])).max():.2e} m")
    p = np.vstack(obs0)
    inside = bool(p.min() > 0 and p[:, 0].max() < IMG_W and p[:, 1].max() < IMG_H)
    print(f"  観測 {p.shape[0]} 点 / {N_VIEWS} 視点、画像内に収まる: {inside}"
          f"、視野占有 {100 * frame_fill(obs0):.0f} %")
    # ★ 穴 (b): reprojection_error は歪みを知らない。真値を渡しても 0 にならない。
    re_true = fs.reprojection_error(obj, obs0[0], K_TRUE, *good[0])
    print(f"  fs.reprojection_error に**真の K と真の姿勢**を渡した RMS "
          f"{np.sqrt(np.mean(re_true ** 2)):.2f} px  ← 歪み引数が無いため 0 にならない")
    re_ud = fs.reprojection_error(obj, fs.undistort_points(obs0[0], K_TRUE, TRUE_DIST, iters=30),
                                  K_TRUE, *good[0])
    print(f"  先に undistort_points を通すと {np.sqrt(np.mean(re_ud ** 2)):.2e} px")

    print("\n=== 2. 良い配置での校正 —— 誤差を成分ごとに分ける ===")
    print(HEAD)
    obs_g0 = observe(obj, good, sigma_px=0.0, seed=1)
    r = calibrate(obj, obs_g0)
    report("傾き32度・雑音なし", r, good, f"init={r['init']}")
    obs_g = observe(obj, good, sigma_px=0.05, seed=1)
    rg = calibrate(obj, obs_g)
    report("傾き32度・雑音0.05px", rg, good, f"init={rg['init']}")
    print(f"  → 雑音なしなら真値をそのまま取り戻す(モデルが完全に一致するから)。")
    print(f"     0.05 px の雑音で fx は {rg['fx']:.2f}(真 {TRUE_FX:.1f})、"
          f"ヤコビアンから出る標準偏差 sigma_fx = {rg['sigma_fx']:.2f} px。")
    print(f"     実際の誤差 {abs(rg['fx'] - TRUE_FX):.2f} px は sigma_fx の "
          f"{abs(rg['fx'] - TRUE_FX) / rg['sigma_fx']:.1f} 倍 —— 統計と整合。")

    print("\n=== 3. ゼロ点 —— 手を抜いたモデルに勝てるか ===")
    print("  ゼロ点 A: 歪みを無視する(k を 0 に固定)")
    print(f"  ゼロ点 B: 主点を画像中心に固定する = 常に |dcx| {NULL_B_DCX:.2f} px の誤差")
    print("  各行は種違い 3 回の平均(1 回の当たり外れで語らないため)")
    print(f"  {'条件':<22}{'視野':>6}{'RMS':>8}{'fx%全部':>9}{'fx%ゼロA':>10}"
          f"{'|dcx|全部':>10}{'sigma_cx':>10}  判定")
    narrow = make_poses(N_VIEWS, tilt_deg=32.0, offset_m=0.0, z_lo=1.80, z_hi=2.00)
    verdicts = {}
    for label, poses, sigma in (("広い視野 雑音0.05px", good, 0.05),
                                ("狭い視野 雑音0.05px", narrow, 0.05),
                                ("狭い視野 雑音0.30px", narrow, 0.30)):
        s = sweep_seeds(obj, poses, sigma)
        fill = 100 * frame_fill(observe(obj, poses, 0.0))
        if s["dcx_full"] < 0.5 * NULL_B_DCX and s["fx_full"] < 0.5 * s["fx_nodist"]:
            v = "推定が勝つ"
        elif s["dcx_full"] > NULL_B_DCX:
            v = "★ ゼロ点 B が勝つ"
        else:
            v = "引き分け"
        verdicts[label] = (s, v)
        print(f"  {label:<22}{fill:>5.0f}%{s['rms']:>8.4f}{s['fx_full']:>9.3f}"
              f"{s['fx_nodist']:>10.3f}{s['dcx_full']:>10.2f}{s['sigma_cx']:>10.2f}  {v}")
    print("  → 広い視野では歪みも主点も推定した方が良い(ゼロ点 A の fx 誤差は 2 桁悪い)。")
    print("  → **狭い視野では上回らない**。中央だけを見ていると歪みの信号(半径の")
    print("     2 乗以上)も遠近の手がかりも入らず、推定した主点は雑音を拾うだけになる。")
    print("     雑音 0.30 px では推定した主点の誤差が、画像中心に固定したときの")
    print(f"     {NULL_B_DCX:.2f} px を**超える** —— 手を抜いた方が正しい。")
    print("  → 見分ける規則は再投影誤差ではなく sigma_cx。sigma_cx が『画像中心から")
    print("     の真のずれ』と同じ大きさになったら、その推定には情報が入っていない。")

    print("\n=== 4. ★ 再投影誤差はほぼ同じ、焦点距離の誤差は桁で違う ===")
    print(HEAD)
    cfgs = (("傾き 32 度(良い)", 32.0, 0.14, 0.55, 0.85),
            ("傾き 8 度", 8.0, 0.14, 0.55, 0.85),
            ("傾き 2 度(ほぼ正面)", 2.0, 0.14, 0.55, 0.85))
    keep = {}
    for label, tilt, off, zlo, zhi in cfgs:
        poses = make_poses(N_VIEWS, tilt_deg=tilt, offset_m=off, z_lo=zlo, z_hi=zhi)
        ob = observe(obj, poses, sigma_px=0.05, seed=3)
        r = calibrate(obj, ob)
        report(label, r, poses, f"sigma_fx={r['sigma_fx']:.1f}")
        keep[label] = (r, poses)
    rms = [v[0]["rms"] for v in keep.values()]
    dfx = [100 * abs(v[0]["fx"] - TRUE_FX) / TRUE_FX for v in keep.values()]
    print(f"  再投影 RMS の幅 {min(rms):.4f}〜{max(rms):.4f} px(比 {max(rms) / min(rms):.2f} 倍)")
    print(f"  fx 誤差の幅 {min(dfx):.4f}〜{max(dfx):.4f} %(比 {max(dfx) / min(dfx):.0f} 倍)")
    print("  → **同じ数字を見ている限り区別できない**。再投影 RMS はどれも雑音の")
    print("     大きさ(成分 0.05 px = 1 点あたり 0.0707 px)にほぼ張り付く —— 当然で、")
    print("     最小二乗は残差を雑音まで落とすのが仕事だから。落ちた先が真値かは別の話。")
    print("  → 区別できる数字は sigma_fx(ヤコビアンの逆行列)の方。上の列を見よ。")
    # この PoC の主題そのもの。RMS の列だけ横に読むと 3 行が同じに見える。
    figs.save_table("reproj_vs_truth",
                    ["配置", "再投影 RMS px", "fx 誤差 %", "|dcx| px", "sigma_fx px"],
                    [[label, "%.4f" % v[0]["rms"],
                      "%.4f" % (100 * abs(v[0]["fx"] - TRUE_FX) / TRUE_FX),
                      "%.2f" % abs(v[0]["cx"] - TRUE_CX),
                      "%.1f" % v[0]["sigma_fx"]] for label, v in keep.items()],
                    title="再投影誤差はほぼ同じ、真の誤差は桁で違う", col_w=125,
                    caption="RMS は %.2f 倍しか動かないのに fx 誤差は %.0f 倍動く。"
                            "配置の良し悪しを映すのは sigma_fx のほう。"
                            % (max(rms) / min(rms), max(dfx) / min(dfx)))

    print("\n=== 5. なぜ相殺するのか —— fx と Z の比は保存される ===")
    print(f"  {'配置':<22}{'fx比':>10}{'Z比(平均)':>12}{'|差|':>10}")
    tilt_ax, fx_ratio, z_ratio = [], [], []
    for (label, (r, poses)), (_, tilt, _, _, _) in zip(keep.items(), cfgs):
        zt = np.array([t[2] for _, t in poses])
        ze = r["rt"][:, 5]
        fr = r["fx"] / TRUE_FX
        zr = float(np.mean(ze / zt))
        tilt_ax.append(tilt)
        fx_ratio.append(fr)
        z_ratio.append(zr)
        print(f"  {label:<22}{fr:>10.5f}{zr:>12.5f}{abs(fr - zr):>10.2e}")
    # 2 本が重なることが主張なので、片方を散布で描いて重なりを見せる。
    figs.save_plot("fx_z_coupling",
                   [("fx / 真の fx", np.array(tilt_ax), np.array(fx_ratio)),
                    ("推定 Z / 真の Z(平均)", np.array(tilt_ax), np.array(z_ratio))],
                   xlabel="板の傾き [度]", ylabel="真値に対する比",
                   title="焦点距離の誤りは距離の誤りと同じ比で動く",
                   kinds=["line", "scatter"],
                   caption="2 本は重なる。画像上の大きさは fx·X/Z なので、"
                           "同じ比で動く限り画素は 1 つも動かない。")
    print("  → 焦点距離を 1 % 大きく推定すると、板までの距離も 1 % 遠くに推定される。")
    print("     画像上の大きさは fx * X / Z で決まるので、この 2 つが同じ比で動く")
    print("     限り**画素は 1 つも動かない**。板を傾けると 1 枚の板の中で Z が")
    print("     変化し、この自由度が破れる。傾きが校正の情報源そのもの。")

    print("\n=== 6. 壊れる条件 ===")
    print("  (a) 退化配置 —— 板の傾きを 0 度から増やすと閉形式はどこで生き返るか")
    print(f"  {'傾き deg':>9}{'sv[-2]/sv[0]':>15}{'Zhang の fx':>13}{'誤差 %':>10}  止めた門")
    for tilt in (0.0, 2.0, 5.0, 8.0, 20.0, 32.0):
        poses_t = make_poses(N_VIEWS, tilt_deg=tilt, offset_m=0.14, z_lo=0.55, z_hi=0.85)
        ob_t = observe(obj, poses_t, sigma_px=0.05, seed=4)
        ratio = zhang_null_ratio(obj, ob_t)
        try:
            z = calib.camera_calibration(obj[:, :2], [o[:, ::-1] for o in ob_t])
            print(f"  {tilt:>9.1f}{ratio:>15.2e}{z['fx']:>13.1f}"
                  f"{100 * abs(z['fx'] - TRUE_FX) / TRUE_FX:>10.1f}  通過")
        except ValueError as exc:
            msg = exc.args[0]
            gate = ("零空間の次元" if "degenerate calibration views" in msg
                    else "雑音込み(K が決まらない)" if "do not determine K" in msg
                    else "K が非有限/非正")
            print(f"  {tilt:>9.1f}{ratio:>15.2e}{'—':>13}{'—':>10}  {gate}")
    print("      → ★ **退化検出の門は歪みのあるカメラでは発火しない**。歪みなしなら")
    print("         設計どおり働く(傾き 0 度で比 3.8e-14、0.05 度で 8.6e-10、拒否)。")
    print("         だが k1=-0.18 を入れると平面ホモグラフィのモデル自体が合わなくなり、")
    print("         比が**傾きに関係なく 1.9e-06 に張り付く**。実カメラは必ず歪むので、")
    print("         現場で止めているのは後段の「fx が nan」の門のほう。")
    print("         しきい値を上げても直らない —— 歪みありでは完全退化 1.92e-06 と")
    print("         傾き 2 度 4.42e-06 の差が 2.3 倍しかなく、線が引けない。")
    print("      → 2026-11-09 から閉形式の後に雑音込みの門がある(残差で点を揺らして解き直し、")
    print("         K の相対標準偏差が 5 % を超えたら拒否)。上の表の 5 度はこれで止まる。")
    print("      → 閉形式は 8 度で通るが fx を 18.5 % 誤る(歪みを無視した偏り。雑音込みの")
    print("         門は偏りを測らない)。非線形最適化の初期値としては使えるが、答えとしては使えない。")
    flat = make_poses(N_VIEWS, tilt_deg=0.0, offset_m=0.14, z_lo=0.55, z_hi=0.85)
    ob = observe(obj, flat, sigma_px=0.05, seed=4)
    rflat = calibrate(obj, ob)
    print(HEAD)
    report("  傾き0度(退化)", rflat, flat, f"init={rflat['init']}")
    print("      → 閉形式は拒否するが、**非線形最適化は拒否せず答えを返す**。")
    print("         再投影 RMS は小さいまま。ここが一番危ない。")

    print("  (b) 画像の中央にしか点が無い —— 板の占める面積を変える")
    print(f"  {'視野占有':>10}{'再投影RMS':>11}{'fx誤差%':>10}{'|dcx|px':>10}{'|dk1|':>10}{'sigma_fx':>11}")
    fill_tab = []
    for zlo, zhi in ((0.55, 0.85), (0.9, 1.1), (1.4, 1.6), (2.2, 2.4)):
        poses = make_poses(N_VIEWS, tilt_deg=32.0, offset_m=0.0, z_lo=zlo, z_hi=zhi)
        ob = observe(obj, poses, sigma_px=0.05, seed=5)
        r = calibrate(obj, ob)
        print(f"  {100 * frame_fill(ob):>9.0f}%{r['rms']:>11.4f}"
              f"{100 * abs(r['fx'] - TRUE_FX) / TRUE_FX:>10.3f}"
              f"{abs(r['cx'] - TRUE_CX):>10.2f}{abs(r['dist'][0] - TRUE_DIST[0]):>10.4f}"
              f"{r['sigma_fx']:>11.2f}")
        fill_tab.append(["%.0f%%" % (100 * frame_fill(ob)), "%.4f" % r["rms"],
                         "%.3f" % (100 * abs(r["fx"] - TRUE_FX) / TRUE_FX),
                         "%.2f" % abs(r["cx"] - TRUE_CX),
                         "%.4f" % abs(r["dist"][0] - TRUE_DIST[0]),
                         "%.2f" % r["sigma_fx"]])
    figs.save_table("frame_fill",
                    ["視野占有", "再投影 RMS", "fx 誤差 %", "|dcx| px",
                     "|dk1|", "sigma_fx"],
                    fill_tab, title="中央にしか点が無いと何が決まらなくなるか",
                    caption="RMS はどの行も 0.067 px(= 0.05·√2)で動かない。"
                            "歪みは半径の 2 乗以上でしか効かず、中央にその信号は無い。")
    print("      → 再投影 RMS はどの行でも 0.067 px(= 0.05 x sqrt2)。歪み係数と主点は視野を")
    print("         占めなくなると決まらなくなる(歪みは半径の 2 乗以上でしか効かず、")
    print("         中央にはその信号が無い)。")
    print("      注: 1 % の行は条件が悪く、本体ライブラリの版で値が動く(同じこのコードで、2026-11-05 より前の本体では")
    print("         fx 誤差 0.069 % / |dcx| 13.26 / |dk1| 0.063、それ以降は 0.122 % / 2.90 / 0.436 —— Zhang 法の初期値の変更で")
    print("         LM の行き先が変わる。2026-11-09 に solve_pnp の平面の初期値を正規化してからは 0.069 % / 13.28 / 0.064)。")
    print("         この行の数は『決まらない』ことの例として読み、値そのものは読まない。")

    print("  (c) 雑音 —— 良い配置と悪い配置で感度がどれだけ違うか")
    print(f"  {'雑音 px':>9}{'良: RMS':>10}{'良: fx%':>10}{'悪: RMS':>10}{'悪: fx%':>10}{'比':>8}")
    bad = make_poses(N_VIEWS, tilt_deg=2.0, offset_m=0.14, z_lo=0.55, z_hi=0.85)
    nz_ax, nz_good, nz_bad = [], [], []
    for sigma in (0.0, 0.05, 0.20, 0.50, 1.00):
        rg2 = calibrate(obj, observe(obj, good, sigma_px=sigma, seed=6))
        rb2 = calibrate(obj, observe(obj, bad, sigma_px=sigma, seed=6))
        eg = 100 * abs(rg2["fx"] - TRUE_FX) / TRUE_FX
        eb = 100 * abs(rb2["fx"] - TRUE_FX) / TRUE_FX
        ratio = f"{eb / eg:>8.0f}" if eg > 1e-9 else f"{'—':>8}"
        print(f"  {sigma:>9.2f}{rg2['rms']:>10.4f}{eg:>10.4f}"
              f"{rb2['rms']:>10.4f}{eb:>10.4f}{ratio}")
        nz_ax.append(sigma)
        nz_good.append(eg)
        nz_bad.append(eb)
    figs.save_plot("noise_amplification",
                   [("傾き 32 度(良い配置)", np.array(nz_ax), np.array(nz_good)),
                    ("傾き 2 度(悪い配置)", np.array(nz_ax), np.array(nz_bad))],
                   xlabel="角点の雑音 [px]", ylabel="fx の誤差 [%]",
                   title="校正の質は雑音でなく配置で決まる",
                   caption="どちらも雑音 0 では真値。伸びる係数だけが違い、"
                           "悪い配置の増幅率は 3 桁。RMS には差が出ない。")
    print("      → 雑音 0 ではどちらも真値を返す(モデルが完全に一致するから)。")
    print("         再投影 RMS はどちらも雑音そのもの(sigma x sqrt2)。fx 誤差は")
    print("         雑音に比例して伸びるが、伸びる**係数**が配置で決まる。悪い配置の")
    print("         増幅率は 3 桁。校正の質は雑音でなく配置で決まる。")
    print("         悪い配置の 0.5 px 以上の行は 100 % 近くで頭打ち —— 焦点距離が")
    print("         もはや解かれておらず、初期値の近くに留まっているだけ。")

    print("\n=== 7. 速度(この機械での実測)===")
    big = np.tile(obj, (40, 1))
    for label, fn in (("project_points (25200 点)",
                       lambda: fs.project_points(big, K_TRUE, *good[0])),
                      ("distort_points (25200 点)", lambda: fs.distort_points(
                          fs.project_points(big, K_TRUE, *good[0])[0], K_TRUE, TRUE_DIST)),
                      ("undistort_points (25200 点)", lambda: fs.undistort_points(
                          fs.project_points(big, K_TRUE, *good[0])[0], K_TRUE, TRUE_DIST)),
                      ("solve_pnp (63 点)", lambda: fs.solve_pnp(obj, obs_g[0], K_TRUE)),
                      ("Zhang 閉形式 (10 視点)", lambda: calib.camera_calibration(
                          obj[:, :2], [o[:, ::-1] for o in obs_g]))):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<28}{1e3 * (time.perf_counter() - t0):>9.2f} ms")
    print(f"  バンドル調整 10 視点 x 63 点 (86 パラメータ){rg['ms']:>9.1f} ms"
          f"  ({rg['nfev']} 回の残差評価)")

    # ---- 自己検査(速さは assert しない)-------------------------------------
    # 1. 雑音ゼロ・良い配置なら真値を取り戻せる(モデルが正しいことの確認)
    r0 = calibrate(obj, observe(obj, good, sigma_px=0.0, seed=1))
    assert abs(r0["fx"] - TRUE_FX) < 1e-3, f"雑音ゼロで fx が戻らない: {r0['fx']}"
    assert abs(r0["cx"] - TRUE_CX) < 1e-3, f"雑音ゼロで cx が戻らない: {r0['cx']}"
    assert abs(r0["dist"][0] - TRUE_DIST[0]) < 1e-5, "雑音ゼロで k1 が戻らない"
    assert r0["rms"] < 1e-6, "雑音ゼロで再投影誤差が残る"
    # 2. ★ 主役: 再投影 RMS はほぼ同じなのに fx 誤差が 1 桁以上違う
    rg_, pg_ = keep["傾き 32 度(良い)"]
    rb_, pb_ = keep["傾き 2 度(ほぼ正面)"]
    assert 0.5 < rb_["rms"] / rg_["rms"] < 2.0, (
        f"再投影 RMS が同程度でない: {rg_['rms']:.4f} vs {rb_['rms']:.4f}")
    eg_ = abs(rg_["fx"] - TRUE_FX) / TRUE_FX
    eb_ = abs(rb_["fx"] - TRUE_FX) / TRUE_FX
    assert eb_ / eg_ > 10.0, f"fx 誤差が桁で違わない: {eg_:.2e} vs {eb_:.2e}"
    # 3. ★ 相殺の仕組み: fx の比と Z の比が一致する
    for r_, p_ in (keep["傾き 2 度(ほぼ正面)"], keep["傾き 8 度"]):
        zr_ = float(np.mean(r_["rt"][:, 5] / np.array([t[2] for _, t in p_])))
        assert abs(r_["fx"] / TRUE_FX - zr_) < 5e-3, "fx 比と Z 比が一致しない"
    # 4. 不確かさは真の誤差の桁を当てる(再投影 RMS は当てない)
    assert rb_["sigma_fx"] > 10.0 * rg_["sigma_fx"], "sigma_fx が配置の差を映さない"
    # 4b. ★ 正直な負けの記録: 狭い視野 + 雑音 0.30 px では主点を推定するより
    #     画像中心に固定するゼロ点 B の方が正しい(上回れない条件が実在する)
    s_wide = verdicts["広い視野 雑音0.05px"][0]
    s_narrow = verdicts["狭い視野 雑音0.30px"][0]
    assert s_wide["dcx_full"] < NULL_B_DCX, "広い視野でゼロ点 B に負けた"
    assert s_wide["fx_full"] < 0.2 * s_wide["fx_nodist"], "広い視野でゼロ点 A に勝てない"
    assert s_narrow["dcx_full"] > NULL_B_DCX, (
        "狭い視野 + 雑音でもゼロ点 B に勝ってしまった —— 章 3 の結論を書き直せ")
    assert s_narrow["sigma_cx"] > NULL_B_DCX, "sigma_cx が情報の欠如を映さない"
    # 5. 完全退化(全視点正面平行)は閉形式が fail-closed で拒否する
    flat_ = make_poses(N_VIEWS, tilt_deg=0.0, offset_m=0.14, z_lo=0.55, z_hi=0.85)
    ob_ = observe(obj, flat_, sigma_px=0.0, seed=4)
    try:
        calib.camera_calibration(obj[:, :2], [o[:, ::-1] for o in ob_])
        raise AssertionError("退化配置が素通りした")
    except ValueError as exc:
        # ★ 穴 (c): 歪んだ点なので止めたのは退化門ではなく後段の非有限 K の門。
        #    その文言に「板を傾けよ」が入っていることまで確かめる(2026-09-06 追加)。
        assert "degenerate calibration views" not in exc.args[0], (
            "歪みありで退化門が発火した —— 直ったなら docstring の穴 (c) を更新せよ")
        assert "tilted" in exc.args[0], (
            "非有限 K の門が傾き不足を名指ししていない —— 利用者に原因が届かない")
    assert zhang_null_ratio(obj, ob_) > 1e-8, (
        "歪みありでも退化門のしきい値に到達した —— docstring の穴 (c) を更新せよ")
    # 5b. ★ 穴 (c3): 閉形式は歪みのぶんだけ系統的に外れる(初期値専用)
    z_good = calib.camera_calibration(obj[:, :2], [o[:, ::-1] for o in obs_g])
    assert abs(z_good["fx"] - TRUE_FX) / TRUE_FX > 0.01, (
        "閉形式が歪み込みで当たった —— 前提が変わった")
    # 6. ★ 穴 (b): reprojection_error は歪みを知らない -> 真値を渡しても大きい
    e_true = float(np.sqrt(np.mean(fs.reprojection_error(obj, obs0[0], K_TRUE, *good[0]) ** 2)))
    assert e_true > 1.0, "歪みがあるのに reprojection_error が小さい(前提が変わった)"
    e_ud = float(np.sqrt(np.mean(fs.reprojection_error(
        obj, fs.undistort_points(obs0[0], K_TRUE, TRUE_DIST, iters=30), K_TRUE, *good[0]) ** 2)))
    assert e_ud < 1e-3, "undistort を通しても誤差が残る"
    # 7. ★ 穴 (a)【解消済み 2026-09-19】: 内部パラメータ推定を facade に露出した。
    #    以前は fs から見えず、この tripwire は「塞がったら docstring を更新せよ」と鳴らしていた。
    #    いまは fs.camera_calibration で呼べる(能力ノート camera-intrinsics-calibration)。
    #    ただし facade 関数であって op レジストリの op ではない((画像,a,b) 固定でないため)。
    assert hasattr(fs, "camera_calibration"), "穴 (a) を塞いだはず —— facade 露出が外れた"
    assert fs.find_op("camera_calibration") is None, "op ではなく facade 関数(レジストリには載せない)"

    fig_convergence_video(obj)
    real_chessboard_chapter(dfx)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


# ── 8. 実写の校正板(OpenCV が配布する 13 枚)と、その実写の質感で描いた板 ─────────── #
# データ: OpenCV samples/data の left01..14.jpg(left10 は配布元に無い、640x480、内角 9x6)。
#   OpenCV のリポジトリの Apache License 2.0。取得 ``py -3.11 tools/fetch_stereoreal_data.py chessboard``
#   (固定コミットから取り、バイト数と SHA-256 を照合。データは repo に入れない)。
# CI(写真が無い)では取得せず、手元で測った記録値 ``REAL_RECORDED`` を印字して章を閉じる。
REAL_PATTERN = (9, 6)                    # 内角の数 (列, 行)
REAL_TILTS = (32.0, 8.0, 2.0)            # 第 4 章と同じ 3 配置
REAL_SEEDS = (0, 1, 2, 3, 4)             # 描いた板の雑音の種(1 回の当たり外れで語らない)
REAL_SUBSET = 4                          # 実写の部分集合の枚数(13 枚から 4 枚 = 715 通り)
REAL_TEX_PPS = 32                        # 板面の質感の解像度 [px / 升目]
REAL_SUBPIX_WIN = (5, 5)                 # cornerSubPix の窓(半幅)。理由は real_render_views の注記
#: 板そのもの(灰色の枠まで)の範囲 [升目](x0, x1, y0, y1)。left04.jpg の質感を目で見て決めた。
#: この外は板ではなく部屋なので、板の平面に貼らず、カメラに固定した実写の背景から読む。
REAL_RIM = (-1.25, 9.3, -1.3, 6.3)
#: 描き直す視点の置き方(距離の範囲 [升目]・視野内の振り幅 [升目]・面内の回り [度])。
REAL_POSE = dict(zlo=10.0, zhi=12.0, off=0.6, spin=5.0)
#: 写真ありで手元で測った記録値(2026-11-08)。CI では写真が無いのでこれを印字し、記録どうしの門を通す。
REAL_RECORDED = {
    "lines": [
        '写真 13 枚の校正(自前の calibrate、4 係数): fx 536.46 px、再投影 RMS 0.409 px、傾き 15.1〜40.7 度',
        '自前の calibrate と OpenCV の fx の差 0.000 %',
        '外れの 1 枚 left02.jpg(RMS 1.22 px)、13 枚の fx 536.46 → 12 枚 534.44',
        '相関(RMS と |fx の差|): 13 枚基準・全組 +0.030 / 12 枚基準・全組 +0.536 / 12 枚基準・外れを含まない 495 組 -0.045',
        '外れを含まない組: RMS 0.148〜0.318 px、fx の差 -1.46〜+2.53 %',
        '外れを順に除いた相関: 1 枚除き 495 組 -0.045 / 2 枚除き 330 組 -0.055 / 3 枚除き 210 組 +0.244',
        '描いた板 傾き 32 度: 角点の誤差 0.152 px、再投影 RMS 0.146 px、|fx 誤差| 種 5 個で 0.02〜0.08 %、sigma_fx 0.3 px',
        '描いた板 傾き 8 度: 角点の誤差 0.158 px、再投影 RMS 0.154 px、|fx 誤差| 種 5 個で 0.22〜0.43 %、sigma_fx 2.2 px',
        '描いた板 傾き 2 度: 角点の誤差 0.157 px、再投影 RMS 0.153 px、|fx 誤差| 種 5 個で 2.14〜7.38 %、sigma_fx 35.3 px',
    ],
    'sub_corr': -0.0448,
    'render_fx': {'32': 0.0475, '8': 0.3483, '2': 5.4052},
    'render_rms': {'32': 0.1463, '8': 0.1541, '2': 0.1525},
}


def _real_corners(gray, cv2, win=(11, 11)):
    """OpenCV の市松角点 + 副画素化。見つからなければ None。返りは (54, 2) の (x, y)。"""
    ok, c = cv2.findChessboardCorners(gray, REAL_PATTERN)
    if not ok:
        return None
    crit = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 1e-4)
    return cv2.cornerSubPix(gray, c, win, (-1, -1), crit).reshape(-1, 2).astype(np.float64)


def _real_obj():
    """板の座標 [升目]。原点は角点 (0, 0)、z = 0。OpenCV と同じ並び(列が速い)。"""
    o = np.zeros((REAL_PATTERN[0] * REAL_PATTERN[1], 3))
    o[:, :2] = np.mgrid[0:REAL_PATTERN[0], 0:REAL_PATTERN[1]].T.reshape(-1, 2)
    return o


def _cv_calib(cv2, obj, pts, size):
    """OpenCV の calibrateCamera(k3 は 0 に固定 = この PoC の 4 係数モデルと同じ)。"""
    O = [obj.astype(np.float32)] * len(pts)
    I = [p.reshape(-1, 1, 2).astype(np.float32) for p in pts]
    rms, K, d, rv, tv = cv2.calibrateCamera(O, I, size, None, None, flags=cv2.CALIB_FIX_K3)
    return float(rms), K, d.ravel()[:4].astype(np.float64), rv, tv


def real_board_texture(cv2, img, K, dist, rvec, tvec):
    """実写 1 枚から「板面の質感」を取り出す(板の座標系での正面像)。

    板面上の各点を推定した K・歪み・姿勢で写真へ投影して読む。写真の外と、歪みの式が折り返す
    遠い半径は使わず、そこは周囲から埋める(cv2.inpaint、ぼかして継ぎ目を消す)。
    推定の誤差で質感の角が升目の格子から 0.2 px ほどずれるので、質感の中で角点を拾い直し、
    3 次の多項式の変位で格子に揃える —— これをしないと、描いた板に「印刷の歪んだ板」の系統誤差が入る。
    返り: (質感 [0,1], 板座標の x 軸, y 軸, 揃える前 / 後の角のずれ RMS [質感 px])。
    """
    from scipy.ndimage import gaussian_filter, map_coordinates

    H, W = img.shape
    xs = np.arange(-7.0, 16.0, 1.0 / REAL_TEX_PPS)
    ys = np.arange(-6.0, 12.0, 1.0 / REAL_TEX_PPS)
    gx, gy = np.meshgrid(xs, ys)
    P = np.stack([gx.ravel(), gy.ravel(), np.zeros(gx.size)], axis=1)
    uv, _ = cv2.projectPoints(P, rvec, tvec, K, dist)
    uv = uv.reshape(-1, 2)
    R0 = cv2.Rodrigues(rvec)[0]
    Pc = P @ R0.T + tvec.ravel()
    rn = np.hypot(Pc[:, 0] / Pc[:, 2], Pc[:, 1] / Pc[:, 2])
    cn = cv2.undistortPoints(np.array([[[0.0, 0.0]], [[W - 1.0, 0.0]], [[0.0, H - 1.0]], [[W - 1.0, H - 1.0]]]),
                             K, dist).reshape(-1, 2)
    inside = ((uv[:, 0] >= 0) & (uv[:, 0] <= W - 1) & (uv[:, 1] >= 0) & (uv[:, 1] <= H - 1)
              & (rn <= np.hypot(cn[:, 0], cn[:, 1]).max()))
    tex = map_coordinates(img, [uv[:, 1], uv[:, 0]], order=1, mode="nearest").reshape(gx.shape)
    mask = cv2.erode(inside.reshape(gx.shape).astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
    t8 = (np.clip(tex, 0, 1) * 255).astype(np.uint8)
    small = cv2.resize(t8, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    hole = cv2.resize((~mask).astype(np.uint8), (small.shape[1], small.shape[0]), interpolation=cv2.INTER_NEAREST)
    small = cv2.inpaint(small, hole, 15, cv2.INPAINT_TELEA)
    filled = gaussian_filter(cv2.resize(small, (tex.shape[1], tex.shape[0]),
                                        interpolation=cv2.INTER_CUBIC).astype(np.float64) / 255.0, 6.0)
    wgt = np.clip(gaussian_filter(mask.astype(float), 4.0) * 2.0 - 1.0, 0.0, 1.0) * mask
    tex = wgt * tex + (1.0 - wgt) * filled

    obj = _real_obj()
    ideal = np.column_stack([(obj[:, 0] - xs[0]) * REAL_TEX_PPS, (obj[:, 1] - ys[0]) * REAL_TEX_PPS])

    def corners_in(t):
        c = _real_corners((np.clip(t, 0, 1) * 255).astype(np.uint8), cv2)
        if c is None:
            raise RuntimeError("質感の中で角点が見つからない")
        if np.linalg.norm(c[0] - ideal[0]) > np.linalg.norm(c[-1] - ideal[0]):
            c = c[::-1].copy()                       # 9x6 は 180 度回しても同じ形 —— 並びを揃える
        return c

    c = corners_in(tex)
    before = float(np.sqrt(((c - ideal) ** 2).sum(1).mean()))

    def basis(x, y):
        return np.column_stack([np.ones_like(x), x, y, x * x, x * y, y * y, x ** 3, x * x * y, x * y * y, y ** 3])

    B0 = basis(ideal[:, 0] / 100.0, ideal[:, 1] / 100.0)
    ax_, *_ = np.linalg.lstsq(B0, c[:, 0] - ideal[:, 0], rcond=None)
    ay_, *_ = np.linalg.lstsq(B0, c[:, 1] - ideal[:, 1], rcond=None)
    yy, xx = np.mgrid[0:tex.shape[0], 0:tex.shape[1]].astype(np.float64)
    B = basis(xx.ravel() / 100.0, yy.ravel() / 100.0)
    tex = map_coordinates(tex, [yy.ravel() + B @ ay_, xx.ravel() + B @ ax_], order=3,
                          mode="nearest").reshape(tex.shape)
    after = float(np.sqrt(((corners_in(tex) - ideal) ** 2).sum(1).mean()))
    return np.clip(tex, 0.0, 1.0), xs, ys, before, after


def _rim_outline(n_per_edge=60):
    """板の枠の外周を板の座標で(歪みのある投影で縁が曲がるので、辺ごとに細かく刻む)。"""
    x0, x1, y0, y1 = REAL_RIM
    t = np.linspace(0.0, 1.0, n_per_edge, endpoint=False)
    edges = [np.column_stack([x0 + (x1 - x0) * t, np.full_like(t, y0)]),
             np.column_stack([np.full_like(t, x1), y0 + (y1 - y0) * t]),
             np.column_stack([x1 - (x1 - x0) * t, np.full_like(t, y1)]),
             np.column_stack([np.full_like(t, x0), y1 - (y1 - y0) * t])]
    e = np.concatenate(edges)
    return np.column_stack([e, np.zeros(len(e))])


def real_backdrop(cv2, img8, K, dist, R, t):
    """背景 = 写真そのもの(カメラに固定)。写っている板の範囲だけ周囲から埋める。

    カメラは動かず板だけが動く、という実際の校正の撮り方に合わせる(部屋は板と一緒に傾かない)。
    返り: (背景 [0,1], 埋めた範囲の印 bool)。埋めた範囲は新しい板がほぼ覆うが、覆い残しは数えて印字する。
    """
    uv, _ = fs.project_points(_rim_outline(), K, R, t)
    poly = fs.distort_points(uv, K, dist)
    hole = np.zeros(img8.shape, np.uint8)
    cv2.fillPoly(hole, [np.round(poly).astype(np.int32)], 1)
    hole = cv2.dilate(hole, np.ones((7, 7), np.uint8))
    filled = cv2.inpaint(img8, hole, 9, cv2.INPAINT_TELEA)
    return filled.astype(np.float64) / 255.0, hole.astype(bool)


def real_board_poses(n, tilt_deg, base=None, zlo=12.0, zhi=16.0, off=1.8, spin=12.0):
    """第 4 章の ``make_poses`` と同じ傾き・回り方の規則を、升目の単位で。

    ``base = (R0, t0)`` を渡すと、板の中心をその写真の板の中心と同じ視線の上に、面内の向きもその写真に
    合わせて置く(背景の写真に写っていた板を新しい板が覆うように)。傾きの量は ``tilt_deg`` だけで決まる。
    """
    out = []
    centre = np.array([(REAL_PATTERN[0] - 1) / 2.0, (REAL_PATTERN[1] - 1) / 2.0, 0.0])
    ray, roll = np.array([0.0, 0.0, 1.0]), 0.0
    if base is not None:
        R0, t0 = base
        c0 = R0 @ centre + t0
        ray = c0 / c0[2]
        roll = float(np.arctan2(R0[1, 0], R0[0, 0]))
    for i in range(n):
        phi = 2.0 * np.pi * i / n + 0.30
        axis = np.array([np.cos(phi), np.sin(phi), 0.0])
        rvec = axis * np.deg2rad(tilt_deg)
        R = fs.rodrigues(rvec) @ fs.rodrigues(np.array([0.0, 0.0, roll + np.deg2rad(spin * np.sin(3.0 * phi))]))
        z = zlo + (zhi - zlo) * i / (n - 1)
        t = ray * z + np.array([off * np.cos(2.0 * phi), off * 0.72 * np.sin(2.0 * phi), 0.0]) - R @ centre
        out.append((R, t))
    return out


def real_render_views(cv2, tex, xs, ys, K, dist, size, poses, seed, backdrop=None, hole=None):
    """質感の板を、真の K・歪みのカメラで撮ったように描き、OpenCV で角点を拾う。

    各画素の光線(歪みを外して正規化)と板の平面 z = 0 の交点が板の枠の内側なら質感を、外側なら
    ``backdrop``(カメラに固定した実写の背景)を読む。そのうえでレンズのぼけ
    (σ 0.6 px)・光子雑音(満杯 4000 電子)・読み出し雑音(σ 0.4 %)・8 bit 量子化を足す。
    ★cornerSubPix の窓は (5, 5)。OpenCV の手引きの (11, 11) だと、32 度に傾いて縮んだ升目で
    隣の角へ跳び、1 枚あたり最大 8 px の外れが出た(再投影 RMS 0.68 px、fx 誤差 1.8 %)。
    返り: 角点の列・描いた画像・角点の真値との差 RMS [px]・背景の埋めた範囲が見えている画素の割合。
    """
    from scipy.ndimage import gaussian_filter, map_coordinates

    W, H = size
    pix = np.stack(np.meshgrid(np.arange(W, dtype=np.float64), np.arange(H, dtype=np.float64)), -1).reshape(-1, 2)
    und = fs.undistort_points(pix, K, dist, iters=40)
    ray = np.column_stack([(und[:, 0] - K[0, 2]) / K[0, 0], (und[:, 1] - K[1, 2]) / K[1, 1], np.ones(len(und))])
    rng = np.random.default_rng(seed)
    obj = _real_obj()
    pts, ims, errs, seen = [], [], [], []
    x0, x1, y0, y1 = REAL_RIM
    for R, t in poses:
        a = R.T @ ray.T
        b = R.T @ t
        X = a * (b[2] / a[2]) - b[:, None]          # 光線と板の平面の交点(板の座標)
        img = map_coordinates(tex, [(X[1] - ys[0]) * REAL_TEX_PPS, (X[0] - xs[0]) * REAL_TEX_PPS],
                              order=1, mode="nearest").reshape(H, W)
        if backdrop is not None:
            on = ((X[0] >= x0) & (X[0] <= x1) & (X[1] >= y0) & (X[1] <= y1) & (b[2] / a[2] > 0)).reshape(H, W)
            w = np.clip(gaussian_filter(on.astype(np.float64), 0.5), 0.0, 1.0)   # 縁の 1 px をなめらかに
            img = w * img + (1.0 - w) * backdrop
            seen.append(float(np.mean(hole & ~on)))
        e = np.clip(gaussian_filter(img, 0.6), 0.0, 1.0) * 4000.0
        e = rng.poisson(e) / 4000.0 + rng.normal(0.0, 0.004, e.shape)
        im8 = np.clip(np.round(e * 255.0), 0, 255).astype(np.uint8)
        c = _real_corners(im8, cv2, REAL_SUBPIX_WIN)
        if c is None:
            raise RuntimeError("描いた板で角点が見つからない(傾き・距離の設定を見直す)")
        uv, _ = fs.project_points(obj, K, R, t)
        tr = fs.distort_points(uv, K, dist)
        if np.linalg.norm(c[0] - tr[0]) > np.linalg.norm(c[-1] - tr[0]):
            c = c[::-1].copy()
        pts.append(c)
        ims.append(im8)
        errs.append(np.linalg.norm(c - tr, axis=1))
    return pts, ims, float(np.sqrt(np.mean(np.concatenate(errs) ** 2))), (float(np.mean(seen)) if seen else 0.0)


def real_chessboard_chapter(syn_fx):
    """第 8 章: 実写の校正板。(a) 13 枚の部分集合 715 通り (b) 実写の質感で描いた 3 配置。

    ``syn_fx`` は第 4 章(合成の点)の fx 誤差 [%] を傾き 32 / 8 / 2 度の順に。比べて印字するだけ。
    """
    print("\n=== 8. 実写の校正板 —— OpenCV が配布する 13 枚と、その質感で描いた板 ===")
    import itertools
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import fetch_stereoreal_data as boarddata

    paths = boarddata.files("chessboard", required=False)
    if paths is None:
        print("  校正板の写真が手元に無い(CI の既定)。取得: py -3.11 tools/fetch_stereoreal_data.py chessboard")
        if REAL_RECORDED is None:
            raise AssertionError("記録値 REAL_RECORDED が空 —— 手元で写真ありの実行をして転記する")
        for line in REAL_RECORDED["lines"]:
            print("  [記録値] " + line)
        # ★ここは記録値どうしの門で、記録の形と結論の向きしか見ない(記録が古いかはデータありの実行が見る)。
        r = REAL_RECORDED
        assert r["sub_corr"] < 0.3, "記録値: 部分集合で再投影 RMS が fx 誤差を言い当てている"
        assert r["render_fx"]["2"] > 10.0 * max(r["render_fx"]["32"], 1e-3), "記録値: 描いた板で配置の差が出ていない"
        assert 0.5 < r["render_rms"]["2"] / r["render_rms"]["32"] < 2.0, "記録値: 描いた板の RMS が同程度でない"
        return r
    import cv2
    from PIL import Image

    cv2.setNumThreads(1)       # calibrateCamera はスレッドの足し順で末尾の桁が揺れる(基準は下の自前の解で決める)
    names = sorted(paths)
    obj = _real_obj()
    imgs, pts = [], []
    for nm in names:
        g = np.asarray(Image.open(paths[nm]).convert("L"))
        c = _real_corners(g, cv2)
        assert c is not None, "%s で角点が見つからない" % nm
        imgs.append(g)
        pts.append(c)
    import realdata
    realdata.mark_read("opencv_samples:left*.jpg")
    H, W = imgs[0].shape
    rms_cv, K_cv, dist_cv, _rv, _tv = _cv_calib(cv2, obj, pts, (W, H))
    # 基準(描いた板の真値)はこの PoC の自前の解(scipy の LM、決定的)。OpenCV は別実装の検算に回す。
    mine = calibrate(obj, pts)
    K = fs.intrinsic_matrix(mine["fx"], mine["fy"], mine["cx"], mine["cy"])
    dist = np.asarray(mine["dist"], np.float64)
    rms = mine["rms"]
    rv = [np.asarray(r[:3], np.float64) for r in mine["rt"]]
    tv = [np.asarray(r[3:], np.float64) for r in mine["rt"]]
    tilt = [float(np.degrees(np.arccos(abs(fs.rodrigues(r)[2, 2])))) for r in rv]
    print(f"  写真 {len(names)} 枚(640x480、内角 9x6)。この PoC の calibrate(4 係数): 再投影 RMS {rms:.3f} px")
    print(f"  fx {K[0, 0]:.2f} fy {K[1, 1]:.2f} cx {K[0, 2]:.2f} cy {K[1, 2]:.2f}  k1 {dist[0]:+.4f} k2 {dist[1]:+.4f}"
          f"  sigma_fx {mine['sigma_fx']:.2f} px")
    print(f"  板の傾き(推定): {min(tilt):.1f}〜{max(tilt):.1f} 度 —— **正面に近い写真は 1 枚も無い**")
    # 別実装で検算: OpenCV の calibrateCamera(k3=0 = 同じ 4 係数モデル)で同じ 13 枚を解く
    d_fx = 100.0 * abs(K_cv[0, 0] - K[0, 0]) / K[0, 0]
    print(f"  OpenCV の calibrateCamera(k3=0)で同じ 13 枚: fx {K_cv[0, 0]:.2f}(自前との差 {d_fx:.3f} %)"
          f"、再投影 RMS {rms_cv:.3f} px")
    assert d_fx < 0.1, "自前の校正と OpenCV が 0.1 % 以上食い違う"

    # (a) 4 枚の部分集合 715 通り。★2026-11-08 の再レビュー: 13 枚の推定を基準にした「相関 +0.03」は基準の
    #     取り方の産物だった —— 再投影の外れた 1 枚(left02)が 13 枚の推定を引っ張り、その 1 枚を含む組は全部
    #     RMS が大きい。基準と組を変えると相関が +0.03 にも +0.54 にもなる。ここでは外れの 1 枚をデータから
    #     決めて明示し、その 1 枚を除いた 12 枚の推定を基準に、除いた組(495 通り)で見る。
    per_view = []
    Kk = fs.intrinsic_matrix(mine["fx"], mine["fy"], mine["cx"], mine["cy"])
    for k_, o_ in enumerate(pts):
        uv_, _ = fs.project_points(obj, Kk, fs.rodrigues(mine["rt"][k_, :3]), mine["rt"][k_, 3:])
        per_view.append(float(np.sqrt(np.mean(np.sum((fs.distort_points(uv_, Kk, dist) - o_) ** 2, axis=1)))))
    k_out = int(np.argmax(per_view))
    rest = [i for i in range(len(names)) if i != k_out]
    fx12 = calibrate(obj, [pts[i] for i in rest])["fx"]
    sub = []
    for idx in itertools.combinations(range(len(names)), REAL_SUBSET):
        r2, K2, _d, _r, _t = _cv_calib(cv2, obj, [pts[i] for i in idx], (W, H))
        sub.append((r2, K2[0, 0], float(k_out in idx)))
    sub = np.array(sub)
    has = sub[:, 2] > 0.5
    d13 = 100.0 * (sub[:, 1] / K[0, 0] - 1.0)
    d12 = 100.0 * (sub[:, 1] / fx12 - 1.0)
    corr13 = float(np.corrcoef(sub[:, 0], np.abs(d13))[0, 1])
    corr12_all = float(np.corrcoef(sub[:, 0], np.abs(d12))[0, 1])
    clean = sub[~has]
    dc = d12[~has]
    corr = float(np.corrcoef(clean[:, 0], np.abs(dc))[0, 1])
    print(f"  (a) 再投影の外れの 1 枚: {names[k_out]}(1 枚ごとの RMS {per_view[k_out]:.2f} px、他は "
          f"{min(per_view[i] for i in rest):.2f}〜{max(per_view[i] for i in rest):.2f} px)。")
    print(f"      13 枚の推定 fx {K[0, 0]:.2f} → {names[k_out]} を除いた 12 枚では {fx12:.2f}(外れの 1 枚が基準を引っ張る)。")
    print(f"      4 枚組 {len(sub)} 通りのうち {names[k_out]} を含む {int(has.sum())} 組は RMS {sub[has, 0].min():.3f} px 以上、"
          f"含まない組は {clean[:, 0].max():.3f} px 以下 —— RMS は外れの写真を見分けている。")
    print(f"      RMS と |fx の差| の相関は基準の取り方で変わる: 13 枚基準・全組 {corr13:+.3f} / 12 枚基準・全組 {corr12_all:+.3f}"
          f" / 12 枚基準・{names[k_out]} を含まない {len(clean)} 組 {corr:+.3f}。")
    print(f"      → 言えるのは最後の一つ: 外れの写真が無い組どうしでは、RMS {clean[:, 0].min():.3f}〜{clean[:, 0].max():.3f} px の"
          f"範囲で fx が {dc.min():+.2f}〜{dc.max():+.2f} % 散り、RMS の小さい組ほど 12 枚の推定に近いという関係は無い")
    print("        (組は写真を共有するので独立な標本ではない)。実写の 13 枚は全部 15 度以上傾いているので、第 4 章の")
    print("        『傾き 2 度』は実写では作れない —— 同じ RMS で fx が狂う話は (b) の描いた板で見る。")
    assert all(sub[has, 0] > clean[:, 0].max()), "外れの 1 枚を含む組と含まない組の RMS が分かれない —— 記述を書き直せ"
    # ★再々レビュー: 外れを含まない組の RMS は 0.2 と 0.3 の 2 つの塊に分かれる。0.3 の塊は 2 番目に外れた写真を
    #   含む組。外れの数を 1 → 2 → 3 枚と増やして除き、そのたびに基準も残りの写真で推定し直した相関も出す。
    order_out = list(np.argsort(per_view)[::-1])
    second = order_out[1]
    n_sec = int(np.sum([(second in idx) for idx in itertools.combinations(range(len(names)), REAL_SUBSET)
                        if k_out not in idx]))
    seq = []
    for n_drop in (1, 2, 3):
        drop = set(order_out[:n_drop])
        keep_i = [i for i in range(len(names)) if i not in drop]
        ref = calibrate(obj, [pts[i] for i in keep_i])["fx"] if n_drop > 1 else fx12
        mask = np.array([not (set(idx) & drop) for idx in itertools.combinations(range(len(names)), REAL_SUBSET)])
        dd_ = np.abs(100.0 * (sub[mask, 1] / ref - 1.0))
        seq.append((n_drop, [names[i] for i in order_out[:n_drop]], int(mask.sum()),
                    float(np.corrcoef(sub[mask, 0], dd_)[0, 1]), float(sub[mask, 0].max())))
    print(f"      外れを含まない組の RMS は 2 つの塊に分かれる: 0.3 px 付近の {n_sec} 組は全部 {names[second]}"
          f"(1 枚ごとの RMS {per_view[second]:.2f} px、2 番目に外れた写真)を含む。")
    print("      外れの写真を RMS の大きい順に除き、基準もそのつど残りで推定し直すと:")
    for n_drop, dn, cnt, cc, rmax in seq:
        print(f"        {n_drop} 枚除く({'・'.join(dn)}): {cnt} 組、RMS ≤ {rmax:.3f} px、相関 {cc:+.3f}")
    print(f"      → 3 枚除くと相関 {seq[2][3]:+.3f} で、門の 0.3 に近い。『RMS の小さい組ほど fx が推定に近い関係は無い』は")
    print("        1〜2 枚除いた範囲の話で、組が減ると弱い正の相関が出始める(門は 1 枚除いた組に掛け、動かさない)。")

    # (b) 実写の質感で描いた板: 真の K・歪み = 13 枚の自前の推定値(★外から来た真値ではない —— 描いた板の
    #     真値として置いただけ。外から来ているのは板の質感・部屋の背景と OpenCV の角点検出)。
    k_src = int(np.argmin(tilt))
    tex, xs, ys, before, after = real_board_texture(cv2, imgs[k_src].astype(np.float64) / 255.0, K,
                                                    np.r_[dist, 0.0], rv[k_src], tv[k_src])
    backdrop, hole = real_backdrop(cv2, imgs[k_src], K, dist, fs.rodrigues(rv[k_src]), tv[k_src])
    print(f"  (b) いちばん正面に近い {names[k_src]}(傾き {tilt[k_src]:.1f} 度)から板面の質感を取り出し、")
    print(f"      角の格子へのずれを {before:.3f} → {after:.3f} 質感 px(1 升 = {REAL_TEX_PPS} px)に揃えてから、")
    print("      13 枚の推定値を真値に置いたカメラで 10 視点ずつ描き、OpenCV で角点を拾ってこの PoC の calibrate で解く。")
    print("      板の外(部屋)はカメラに固定した同じ写真から読む(板と一緒に傾かない)。写っていた板の範囲は周囲から埋めた。")
    print(f"      {'配置':<16}{'角点の誤差':>10}{'再投影RMS':>11}{'fx 誤差 %':>11}{'sigma_fx':>10}  (種 {len(REAL_SEEDS)} 個の平均)")
    rend = {}
    shown = {}
    seen_all = []
    for tilt_deg in REAL_TILTS:
        ce, rr, fe, sg = [], [], [], []
        for sd in REAL_SEEDS:
            ps = real_board_poses(N_VIEWS, tilt_deg, base=(fs.rodrigues(rv[k_src]), tv[k_src]), **REAL_POSE)
            p2, ims, cerr, seen = real_render_views(cv2, tex, xs, ys, K, dist, (W, H), ps,
                                                    seed=1000 * int(tilt_deg) + sd, backdrop=backdrop, hole=hole)
            r = calibrate(obj, p2)
            ce.append(cerr)
            rr.append(r["rms"])
            fe.append(100.0 * (r["fx"] - K[0, 0]) / K[0, 0])
            sg.append(r["sigma_fx"])
            seen_all.append(seen)
            if sd == REAL_SEEDS[0]:
                shown[tilt_deg] = (ims[0], p2[0], r)
        rend[tilt_deg] = dict(cerr=float(np.mean(ce)), rms=float(np.mean(rr)), fx=float(np.mean(np.abs(fe))),
                              fx_lo=float(np.min(np.abs(fe))), fx_hi=float(np.max(np.abs(fe))),
                              fx_signed=fe, sigma=float(np.mean(sg)))
        print(f"      傾き {tilt_deg:>4.0f} 度       {np.mean(ce):>9.3f}{np.mean(rr):>11.3f}{np.mean(np.abs(fe)):>11.3f}"
              f"{np.mean(sg):>10.2f}   (符号つき {', '.join('%+.2f' % v for v in fe)})")
    seen_frac = float(np.mean(seen_all))
    print(f"      埋めた背景が板に覆われずに見えている画素: 平均 {100 * seen_frac:.2f} %(最大 {100 * max(seen_all):.2f} %)"
          " —— 門は平均で見る(最大は 5 % を超える視点がある)")
    g, b = rend[REAL_TILTS[0]], rend[REAL_TILTS[-1]]
    print(f"  → 再投影 RMS は {g['rms']:.3f} / {b['rms']:.3f} px(比 {b['rms'] / g['rms']:.2f})でほぼ同じなのに、"
          f"|fx 誤差| は種 {len(REAL_SEEDS)} 個で 32 度 {g['fx_lo']:.2f}〜{g['fx_hi']:.2f} %、"
          f"2 度 {b['fx_lo']:.1f}〜{b['fx_hi']:.1f} %(2 度のいちばん小さい値でも 32 度のいちばん大きい値の "
          f"{b['fx_lo'] / g['fx_hi']:.0f} 倍)。")
    print("    ★値は範囲で読む: 描き直しの経路は敏感で、真値(13 枚の推定)が 1e-5 px 動くだけで描いた画像と角点が")
    print("      動き(角点で中央値 0.03 px、2026-11-09 実測)、雑音の実現が別物になって種ごとの値が入れ替わる")
    print("      (傾き 2 度の平均は本体の版で 3.99 % にも 5.41 % にもなった)。1 つの種・1 つの平均の有効数字に意味は無い。")
    print(f"    合成の点(第 4 章、雑音 0.05 px)では {syn_fx[0]:.3f} % と {syn_fx[-1]:.3f} %。角点の誤差は {b['cerr']:.2f} px"
          f"(合成の 0.05 px の約 {b['cerr'] / 0.05:.1f} 倍)。正面寄りの誤差は種で 2 倍ほど揺れるが、どれも同じ向き。")
    print(f"    警報になるのは sigma_fx(傾き 2 度で {b['sigma']:.1f} px、32 度で {g['sigma']:.2f} px)—— 再投影 RMS ではない。")
    assert after < before and after < 0.2, "質感の角を格子に揃えられていない"
    assert corr < 0.3, "外れを除いた部分集合で再投影 RMS が fx のずれを言い当てた —— 結論を書き直せ"
    assert 0.5 < b["rms"] / g["rms"] < 2.0, "描いた板で再投影 RMS が同程度でない"
    assert b["fx"] > 10.0 * g["fx"], "描いた板で fx 誤差が桁で違わない"
    # ★展示台帳の lead の「28 倍以上」は 1 回の実現の値(門は 10 倍)。データありの実行で REAL_RECORDED が変わったら、lead も見直すこと。
    assert b["fx_lo"] > 10.0 * g["fx_hi"], "描いた板で fx 誤差の範囲が桁で離れていない(主張は範囲で書いている)"
    assert b["sigma"] > 10.0 * g["sigma"], "描いた板で sigma_fx が配置の差を映さない"
    assert seen_frac < 0.05, "埋めた背景が 5 %% 以上見えている(%.3f)—— 背景の作り方を見直す" % seen_frac

    lines = [
        "写真 %d 枚の校正(自前の calibrate、4 係数): fx %.2f px、再投影 RMS %.3f px、傾き %.1f〜%.1f 度"
        % (len(names), K[0, 0], rms, min(tilt), max(tilt)),
        "自前の calibrate と OpenCV の fx の差 %.3f %%" % d_fx,
        "外れの 1 枚 %s(RMS %.2f px)、13 枚の fx %.2f → 12 枚 %.2f" % (names[k_out], per_view[k_out], K[0, 0], fx12),
        "相関(RMS と |fx の差|): 13 枚基準・全組 %+.3f / 12 枚基準・全組 %+.3f / 12 枚基準・外れを含まない %d 組 %+.3f"
        % (corr13, corr12_all, len(clean), corr),
        "外れを含まない組: RMS %.3f〜%.3f px、fx の差 %+.2f〜%+.2f %%" % (clean[:, 0].min(), clean[:, 0].max(), dc.min(), dc.max()),
        "外れを順に除いた相関: " + " / ".join("%d 枚除き %d 組 %+.3f" % (a_, c_, r_) for a_, _d, c_, r_, _m in seq),
    ] + ["描いた板 傾き %.0f 度: 角点の誤差 %.3f px、再投影 RMS %.3f px、|fx 誤差| 種 %d 個で %.2f〜%.2f %%、sigma_fx %.1f px"
         % (t, rend[t]["cerr"], rend[t]["rms"], len(REAL_SEEDS), rend[t]["fx_lo"], rend[t]["fx_hi"], rend[t]["sigma"])
         for t in REAL_TILTS]
    rec = {"lines": lines, "sub_corr": round(corr, 4),
           "render_fx": {"%.0f" % t: round(rend[t]["fx"], 4) for t in REAL_TILTS},
           "render_rms": {"%.0f" % t: round(rend[t]["rms"], 4) for t in REAL_TILTS}}
    print("  REAL_RECORDED = %r" % (rec,))
    # ★データがあるときは、測った値と埋め込みの記録値を突き合わせる。CI(データ無し)の門は記録値どうしの
    #   比較なので、記録が古くなっても気づけない —— その穴はここで塞ぐ(決定的な計算なので許容幅は丸めの分だけ)。
    if REAL_RECORDED is not None:
        stale = []
        if abs(rec["sub_corr"] - REAL_RECORDED["sub_corr"]) > 2e-4:
            stale.append("sub_corr %r != %r" % (rec["sub_corr"], REAL_RECORDED["sub_corr"]))
        for key in ("render_fx", "render_rms"):
            for t_, v in rec[key].items():
                if abs(v - REAL_RECORDED[key][t_]) > 2e-4:
                    stale.append("%s[%s] %r != %r" % (key, t_, v, REAL_RECORDED[key][t_]))
        if rec["lines"] != list(REAL_RECORDED["lines"]):
            stale.append("lines が違う")
        assert not stale, "REAL_RECORDED が実測と違う(記録を転記し直す): " + "; ".join(stale)
    fig_real_board(imgs[k_src], pts[k_src], names[k_src], K, rms, len(names), shown, rend, syn_fx,
                   np.column_stack([sub[:, 0], d12, sub[:, 2]]), corr, names[k_out], fx12, names[second], n_sec, seq, seen_frac,
                   max(seen_all))
    return rec


def fig_real_board(photo, photo_pts, photo_name, K, rms, n_photos, shown, rend, syn_fx, sub, corr, out_name, fx12,
                   sec_name, n_sec, seq, seen_mean, seen_max):
    """代表の図: 上段 = 実写そのもの(写真 1 枚 + 4 枚組 715 通りの散布)、下段 = 実写の質感で描いた板 2 配置。"""
    if not figs.enabled():
        return None
    from PIL import Image, ImageDraw, ImageFont

    font = ImageFont.truetype(str(figs._japanese_font_path()), 22)
    font_s = ImageFont.truetype(str(figs._japanese_font_path()), 17)
    font_m = ImageFont.truetype(str(figs._japanese_font_path()), 20)
    font_b = ImageFont.truetype(str(figs._japanese_font_path(bold=True)), 23)
    PW, PH, HEAD, GAP, TOP = 640, 480, 74, 12, 84
    W = 2 * PW + 3 * GAP
    Hh = TOP + 2 * (HEAD + PH) + 3 * GAP + 34
    sheet = Image.new("RGB", (W, Hh), (14, 18, 24))
    d = ImageDraw.Draw(sheet)
    g, b = rend[REAL_TILTS[0]], rend[REAL_TILTS[-1]]
    has = sub[:, 2] > 0.5
    d.text((GAP, 10), "上: 実写 %d 枚の 4 枚組。外れの 1 枚(%s)を除く %d 組でも fx は %+.1f〜%+.1f %% 散る"
           % (n_photos, out_name, int((~has).sum()), sub[~has, 1].min(), sub[~has, 1].max()),
           font=font_b, fill=(240, 240, 240))
    d.text((GAP, 44), "下: 実写の質感で描き直した板。RMS %.3f〜%.3f px のまま |fx 誤差| %.2f %% → %.1f %%(種ごと %.1f〜%.1f %%)"
           % (min(rend[t]["rms"] for t in REAL_TILTS), max(rend[t]["rms"] for t in REAL_TILTS), g["fx"], b["fx"],
              b["fx_lo"], b["fx_hi"]), font=font_b, fill=(240, 240, 240))

    def head(i, title, subt, col):
        x0 = GAP + (i % 2) * (PW + GAP)
        y0 = TOP + (i // 2) * (HEAD + PH + GAP)
        d.rectangle((x0, y0, x0 + PW - 1, y0 + HEAD - 1), fill=(26, 34, 46))
        d.text((x0 + 10, y0 + 6), title, font=font, fill=(235, 235, 235))
        d.text((x0 + 10, y0 + 40), subt, font=font_m, fill=col)
        return x0, y0 + HEAD

    def photo_panel(i, im, p, title, subt, col):
        x0, y0 = head(i, title, subt, col)
        rgb = Image.fromarray(np.asarray(im, np.uint8)).convert("RGB")
        dd = ImageDraw.Draw(rgb)
        for (x, y) in p:
            dd.line((x - 6, y, x + 6, y), fill=col, width=2)
            dd.line((x, y - 6, x, y + 6), fill=col, width=2)
        sheet.paste(rgb, (x0, y0))

    photo_panel(0, photo, photo_pts, "実写 %s(OpenCV 配布の校正板)" % photo_name,
                "13 枚の推定: fx = %.1f px、再投影 RMS %.2f px" % (K[0, 0], rms), (120, 200, 255))
    # 上右: 実写の 4 枚組 715 通り —— 横 = 再投影 RMS、縦 = fx の 13 枚の推定との差
    x0, y0 = head(1, "4 枚組 %d 通り(縦 = 12 枚の推定 fx %.1f との差 [%%])" % (len(sub), fx12),
                  "青 = %s を含まない(相関 %+.3f)/ 橙 = 含む" % (out_name, corr), (120, 200, 255))
    pl = Image.new("RGB", (PW, PH), (18, 25, 34))
    dp = ImageDraw.Draw(pl)
    ax0, ax1, ay0, ay1 = 70, PW - 20, 20, PH - 60
    xlo, xhi = 0.1, float(np.ceil(sub[:, 0].max() * 10) / 10)
    ylo, yhi = float(np.floor(sub[:, 1].min())), float(np.ceil(sub[:, 1].max()))
    xp = lambda v: ax0 + (v - xlo) / (xhi - xlo) * (ax1 - ax0)
    yp = lambda v: ay1 - (v - ylo) / (yhi - ylo) * (ay1 - ay0)
    dp.rectangle((ax0, ay0, ax1, ay1), outline=(150, 160, 170))
    dp.line((ax0, yp(0.0), ax1, yp(0.0)), fill=(110, 110, 110), width=1)
    for v in np.arange(xlo, xhi + 1e-9, 0.1):
        dp.text((xp(v) - 14, ay1 + 6), "%.1f" % v, font=font_s, fill=(190, 190, 190))
    for v in np.arange(ylo, yhi + 1e-9, 1.0):
        dp.text((ax0 - 44, yp(v) - 10), "%+.0f" % v, font=font_s, fill=(190, 190, 190))
    for r_, f_, h_ in sub:
        cx, cy = xp(r_), yp(f_)
        dp.ellipse((cx - 2, cy - 2, cx + 2, cy + 2), fill=(255, 170, 60) if h_ > 0.5 else (120, 200, 255))
    dp.text((ax0 + 10, ay0 + 6), "灰線 = 12 枚の推定と同じ fx", font=font_s, fill=(200, 200, 200))
    dp.text((xp(0.27), yp(-1.6)), "0.3 付近 = %s を含む %d 組" % (sec_name, n_sec), font=font_s, fill=(200, 220, 240))
    dp.text((ax0 + 10, ay1 + 30), "外れを順に除いた相関 " + " / ".join("%d 枚 %+.3f" % (a_, r_) for a_, _d, _c, r_, _m in seq),
            font=font_s, fill=(220, 220, 220))
    sheet.paste(pl, (x0, y0))
    for i, t in ((2, REAL_TILTS[0]), (3, REAL_TILTS[-1])):
        im, p, _r = shown[t]
        bad = t == REAL_TILTS[-1]
        rt = rend[t]
        subt = ("RMS %.3f px → |fx 誤差| %.1f〜%.1f %%(種 %d 個)・sigma_fx %.1f"
                % (rt["rms"], rt["fx_lo"], rt["fx_hi"], len(REAL_SEEDS), rt["sigma"]) if bad else
                "RMS %.3f px → |fx 誤差| %.2f〜%.2f %%(種 %d 個)、sigma_fx %.2f px"
                % (rt["rms"], rt["fx_lo"], rt["fx_hi"], len(REAL_SEEDS), rt["sigma"]))
        photo_panel(i, im, p, "描き直した板 傾き %.0f 度 × 10 視点(真値 = 13 枚の推定)" % t, subt,
                    (255, 120, 90) if bad else (120, 230, 140))
    d.text((GAP, Hh - 30), "十字 = OpenCV が拾った角点。傾き 8 度は |fx 誤差| %.2f〜%.2f %%。描いた板の背景はカメラに固定した同じ写真。"
           "写真: OpenCV samples/data(Apache-2.0)" % (rend[8.0]["fx_lo"], rend[8.0]["fx_hi"]), font=font_s, fill=(190, 190, 190))
    cap = ("上: 実写の校正板(OpenCV が配布する 13 枚、Apache-2.0)から 4 枚を選ぶ %d 通りを校正し直した。再投影の外れの 1 枚(%s)を"
           "含む組は RMS が大きく、含まない %d 組では 12 枚の推定 fx との差が %+.2f〜%+.2f %% 散り、RMS と |差| の相関は %+.3f"
           "(基準を 13 枚の推定にすると値が変わる)。含まない組の RMS が 0.3 px 付近に固まる %d 組は 2 番目に外れた %s を含む。"
           "外れを RMS の大きい順に 1 / 2 / 3 枚除くと相関は %+.3f / %+.3f / %+.3f で、3 枚除くと門の 0.3 に近づく。"
           "下: 最も正面に近い 1 枚の板面の質感を、13 枚の推定値を真値に置いた"
           "カメラで傾き 32 / 8 / 2 度に 10 視点ずつ描き直し、OpenCV で角点を拾って校正した結果。再投影 RMS は "
           "%.3f / %.3f / %.3f px でほぼ同じなのに、|fx 誤差| は雑音の種 %d 個で %.2f〜%.2f / %.2f〜%.2f / %.1f〜%.1f %%。"
           "警報になるのは sigma_fx(%.2f → %.1f px)。合成の点(第 4 章)では %.3f / %.3f / %.3f %% だった。"
           "値は範囲で読む: 描き直しの経路は敏感で、真値が 1e-5 px 動くだけで角点が中央値 0.03 px 動いて雑音の実現が変わる。"
           "描いた板の背景で、写っていた板を埋めた部分が見えている画素は平均 %.1f %%(最大 %.1f %%)。"
           % (len(sub), out_name, int((~has).sum()), sub[~has, 1].min(), sub[~has, 1].max(), corr, n_sec, sec_name, seq[0][3], seq[1][3], seq[2][3], g["rms"], rend[8.0]["rms"], b["rms"], len(REAL_SEEDS), g["fx_lo"],
              g["fx_hi"], rend[8.0]["fx_lo"], rend[8.0]["fx_hi"], b["fx_lo"], b["fx_hi"], g["sigma"], b["sigma"],
              syn_fx[0], syn_fx[1], syn_fx[2],
              100 * seen_mean, 100 * seen_max))
    return figs.save("real_board", np.asarray(sheet, np.float64) / 255.0, caption=cap)


if __name__ == "__main__":
    main()
