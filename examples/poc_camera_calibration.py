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
 7. 速度

【★ この PoC が出した道具の穴】
(a) **内部パラメータ推定がファサードから呼べない**。``calib.camera_calibration``
    (Zhang 法)がリポジトリ唯一の内部行列推定だが、``import fullseye as fs`` の
    公開名にも op レジストリ 882 個にも**入っていない**。この PoC は
    ``import calib`` で裸のモジュールを直接叩いている。ファサードだけを見る
    利用者にとって「fullseye はカメラ校正ができないライブラリ」に見える。
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
(c2) **``camera_calibration`` は不確かさも条件数も返さない**。返るのは
    ``reproj_rms`` だけ —— まさに本 PoC が「保証しない」と示している数字である。
    第 3・4 章で見るとおり、配置の良し悪しを映すのは ``sigma_fx`` / ``sigma_cx``
    (ヤコビアンの逆行列の対角)であって再投影誤差ではない。
(c3) **閉形式は歪みを無視するので答えとしては使えない**。傾き 5 度で fx を
    41 %、傾き 32 度でも 2.7 % 誤る(k1 = -0.18 のレンズ)。初期値としては
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

import time

import numpy as np
from scipy.optimize import least_squares

import fullseye as fs
import calib                      # ★ 穴 (a): fs ファサードに出ていない
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


def calibrate(obj, obs, fit_dist: bool = True, fit_pp: bool = True):
    """内部パラメータ + 歪み + 全姿勢を同時に最小二乗で解く。

    初期値は Zhang 法(``calib.camera_calibration``、歪み無視の閉形式)+ 視点ごとの
    ``fs.solve_pnp``。残差は ``distort_points(project_points(...))`` の順方向モデル。
    Zhang が拒否した配置では「焦点距離 ~ 画像幅」という経験則の初期値に落として
    先へ進む(第 6 章 a の退化配置がこの経路。最適化は止まらず答えを返す)。"""
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
    sv = np.linalg.svd(np.asarray(V))[1]
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
            gate = ("零空間の次元" if "degenerate calibration views" in exc.args[0]
                    else "K が非有限/非正")
            print(f"  {tilt:>9.1f}{ratio:>15.2e}{'—':>13}{'—':>10}  {gate}")
    print("      → ★ **退化検出の門は歪みのあるカメラでは発火しない**。歪みなしなら")
    print("         設計どおり働く(傾き 0 度で比 3.8e-14、0.05 度で 8.6e-10、拒否)。")
    print("         だが k1=-0.18 を入れると平面ホモグラフィのモデル自体が合わなくなり、")
    print("         比が**傾きに関係なく 1.9e-06 に張り付く**。実カメラは必ず歪むので、")
    print("         現場で止めているのは後段の「fx が nan」の門のほう。")
    print("         しきい値を上げても直らない —— 歪みありでは完全退化 1.92e-06 と")
    print("         傾き 2 度 4.42e-06 の差が 2.3 倍しかなく、線が引けない。")
    print("      → 閉形式は 5 度で生き返るが fx を 41 % 誤る(歪みを無視するため)。")
    print("         非線形最適化の初期値としては使えるが、答えとしては使えない。")
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
    # 7. ★ 穴 (a): 内部パラメータ推定はファサードから見えない
    assert not hasattr(fs, "camera_calibration"), "穴 (a) が塞がった —— docstring を更新せよ"
    assert fs.find_op("camera_calibration") is None, "op レジストリに載った —— docstring を更新せよ"

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
