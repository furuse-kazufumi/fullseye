# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""エアホッケーのパック追跡・予測・打ち返し —— 学習なし、全部ルールで(台帳 ``puck``、2026-10-04)。

低価格のエアホッケーロボット(Shinjo, Beltran-Hernandez, Hamaya, Tanaka, IROS 2024, doi 10.1109/iros58592.2024.10801458)の鎖
**カメラ → パック検出 → 速度推定 → 軌道予測 → 5 節リンクの動作計画(位置制御サーボ)** を、Fullseye の既存部品
(:func:`balltrack.ball_detect` / :func:`balltrack.ball_track` / :func:`balltrack.kalman_ca`、:func:`ballistics.slide_stop_distance`、
:func:`calib.image_to_world_plane`)と閉形式だけで組む。真値は外から 3 系統:

1. **閉形式**: 空気膜上の滑りは Coulomb の等減速 a = μg(v(t) = v₀ − μg t、停止距離 v₀²/(2μg))、壁は法線成分を −e 倍・
   接線成分を kₜ 倍(法線・接線の 2 つの反発係数。記法は Cross 2022, Eur. J. Phys., doi 10.1088/1361-6404/ac4b47 の「ディスクの
   斜め衝突」から。Spong 2001, Syst. Control Lett., doi 10.1016/s0167-6911(00)00105-5 の衝突模型は原文を読めていないので **未検証**)。
   壁の間の経路は区間ごとに閉形式で繋ぐ(鏡映法と一致、門)。
2. **外部シム(第 2 実装、MIT)**: Robot Air Hockey Challenge の台の MJCF(Liu ほか、arXiv 2411.05718)。★読んで分かったこと:
   パックと台面の接触は ``<exclude>`` で切ってあり、減速は **滑り関節の粘性減衰 c = 0.005 N·s/m(m = 0.01 kg → 時定数 2 s)**。
   Coulomb ではない。壁は軟接触で e はパラメータでなく **測って出る**(実測 e_n ≈ 0.74、kₜ ≈ 0.85)。この MJCF は repo に
   同梱せず、環境変数 ``FULLSEYE_AIRHOCKEY_DATA`` の下(``table.xml`` と ``table_rim.stl``)に置いたときだけ使う。
3. **5 節リンクの運動学**: 2 本の 2 リンク腕の先端が一致する閉形式(円と円の交点)。FK∘IK = 恒等(1e-9)が門。

命名の規約: world は台の中心が原点、x が長手(ロボットは −x 側)、y が幅、単位 m。画素は (col, row)。壁の内面は ``x_half`` /
``y_half``、パック中心が届く範囲はそれから半径を引いた所。失敗は fail-closed: 届かない打点・交わらない予測線・知らない綴りは
``None`` か ``ValueError``。
正直に: 5 節リンクの寸法・サーボの角速度(6 rad/s)・打具の半径・守備線の位置・閉形式の既定 μ / e / kₜ は **仮定**(論文の
実機の数は読めていない)。実機映像は使っていない(合成 + MuJoCo)。壁の「滑り/把持」の 2 領域と回転は入れていない。
mujoco か配布物が要るもの(facade のみ、台帳の外): :func:`puck_challenge_mjcf`(配布物の MJCF を読む)、:func:`puck_mujoco_run`。
"""
from __future__ import annotations

import os

import numpy as np

import balltrack as _BT
import calib as _CAL

__all__ = [
    "puck_table", "puck_wall_bounce", "puck_slide_predict", "puck_state_at", "puck_crossing_point", "puck_mirror_path",
    "puck_stop_distance", "puck_camera", "puck_world_to_pixel", "puck_pixel_to_world", "puck_render_frame", "puck_synth_frames",
    "puck_detect", "puck_track", "puck_velocity_estimate", "puck_mu_from_decel", "puck_restitution_from_wall",
    "fivebar_link", "fivebar_fk", "fivebar_ik", "fivebar_workspace", "fivebar_reach_interval", "striker_plan", "fivebar_trajectory",
    "puck_scene_mjcf", "puck_pinhole_camera",
    # mujoco か配布物が要る(facade のみ、台帳の外)
    "puck_challenge_mjcf", "puck_mujoco_run",
]

G = 9.81
_MODELS = ("coulomb", "viscous", "none")


def _choice(name: str, value, allowed) -> None:
    """知らない綴りは黙って既定に落とさず止める(fail-closed)。"""
    if value not in allowed:
        raise ValueError("%s must be one of %s, got %r" % (name, sorted(allowed), value))


def _v2(x, name="vector") -> np.ndarray:
    a = np.asarray(x, np.float64).reshape(-1)
    if a.size != 2 or not np.all(np.isfinite(a)):
        raise ValueError("%s must be a finite 2-vector" % name)
    return a


# ─────────────────────────────── 台 ───────────────────────────────

def puck_table(*, x_half: float = 0.974, y_half: float = 0.519, puck_radius: float = 0.03165, mass: float = 0.01,
               mu: float = 0.02, e: float = 0.8, kt: float = 1.0, g: float = G, goal_half: float = 0.125,
               damping: float = 0.005) -> dict:
    """台とパックの数(既定は Robot Air Hockey Challenge の ``table.xml`` から読んだ値、MIT、arXiv 2411.05718)。

    壁の内面: 端の rim は中心 |x| = 1.019・半厚 0.045 → ``x_half`` = 0.974、横の rim は |y| = 0.564・半厚 0.045 → ``y_half`` = 0.519。
    端の rim は |y| < 0.125 が空いている(ゴール、``goal_half``)。パック: 円柱 半径 0.03165、質量 0.01 kg。
    ``mu``(Coulomb)と ``e``・``kt``(壁の法線・接線の反発係数)は MJCF に **無い**(減速は粘性 ``damping``、壁は軟接触)ので
    こちらの既定は仮定。返り値は dict(``table`` sort)。"""
    if not (x_half > puck_radius > 0 and y_half > puck_radius and mass > 0 and g > 0):
        raise ValueError("need x_half, y_half > puck_radius > 0, mass > 0, g > 0")
    if not (0.0 <= e <= 1.0 and 0.0 <= kt <= 1.0 and mu >= 0 and damping >= 0 and 0 <= goal_half < y_half):
        raise ValueError("need 0 <= e, kt <= 1, mu >= 0, damping >= 0, 0 <= goal_half < y_half")
    return {"x_half": float(x_half), "y_half": float(y_half), "puck_radius": float(puck_radius), "mass": float(mass),
            "mu": float(mu), "e": float(e), "kt": float(kt), "g": float(g), "goal_half": float(goal_half),
            "damping": float(damping)}


# ─────────────────────────────── 壁の反発 ───────────────────────────────

def puck_wall_bounce(v, normal, e: float, kt: float = 1.0) -> dict:
    """壁との衝突: 法線成分 vₙ' = −e vₙ、接線成分 vₜ' = kₜ vₜ(e = 法線の反発係数、kₜ = 接線の保持率 = 接線の反発係数)。

    回転は持たない(壁の摩擦で入る回転は接線の減りに畳んである。Cross 2022 のディスク衝突は「滑りか把持か」で接線の
    反発係数を書く —— その 2 領域は入れていない)。返り値
    ``{"v", "vn_in", "vn_out", "vt_in", "vt_out", "energy_ratio"}``。法線だけの衝突なら energy_ratio = e²(門)。
    ``v·n ≥ 0``(離れていく)なら何もしない。"""
    v = _v2(v, "v")
    n = _v2(normal, "normal")
    nn = float(np.linalg.norm(n))
    if nn <= 0:
        raise ValueError("normal must be non-zero")
    n = n / nn
    if not (0.0 <= e <= 1.0 and 0.0 <= kt <= 1.0):
        raise ValueError("need 0 <= e <= 1 and 0 <= kt <= 1")
    vn = float(v @ n)
    vt_vec = v - vn * n
    if vn >= 0:
        return {"v": v.copy(), "vn_in": vn, "vn_out": vn, "vt_in": float(np.linalg.norm(vt_vec)),
                "vt_out": float(np.linalg.norm(vt_vec)), "energy_ratio": 1.0}
    v2 = kt * vt_vec - e * vn * n
    k_in = float(v @ v)
    return {"v": v2, "vn_in": vn, "vn_out": float(-e * vn), "vt_in": float(np.linalg.norm(vt_vec)),
            "vt_out": float(kt * np.linalg.norm(vt_vec)), "energy_ratio": float((v2 @ v2) / k_in) if k_in > 0 else 1.0}


# ─────────────────────────────── 閉形式の滑り ───────────────────────────────

def _decel_params(table: dict, model: str):
    _choice("model", model, _MODELS)
    if model == "coulomb":
        return table["mu"] * table["g"]
    if model == "viscous":
        return table["damping"] / table["mass"]
    return 0.0


def _dist_at(model: str, s0: float, k: float, tau):
    """区間の始めからの移動距離 d(τ)(向きは一定)。coulomb: s₀τ − ½kτ²(k = μg)/ viscous: s₀(1 − e^{−kτ})/k / none: s₀τ。"""
    tau = np.asarray(tau, np.float64)
    if model == "coulomb":
        return s0 * tau - 0.5 * k * tau * tau
    if model == "viscous":
        return s0 * (1.0 - np.exp(-k * tau)) / k if k > 0 else s0 * tau
    return s0 * tau


def _speed_at(model: str, s0: float, k: float, tau):
    tau = np.asarray(tau, np.float64)
    if model == "coulomb":
        return np.maximum(s0 - k * tau, 0.0)
    if model == "viscous":
        return s0 * np.exp(-k * tau)
    return np.full_like(tau, s0)


def _time_to_distance(model: str, s0: float, k: float, d: float):
    """d(τ) = d を解く(届かなければ None)。"""
    if d <= 0:
        return 0.0
    if model == "coulomb":
        if k <= 0:
            return d / s0
        disc = s0 * s0 - 2.0 * k * d
        if disc < 0:
            return None
        return (s0 - np.sqrt(disc)) / k
    if model == "viscous":
        if k <= 0:
            return d / s0
        x = 1.0 - k * d / s0
        if x <= 0:
            return None
        return -np.log(x) / k
    return d / s0


def _stop_time(model: str, s0: float, k: float):
    if model == "coulomb" and k > 0:
        return s0 / k
    return np.inf


def puck_slide_predict(p0, v0, table: dict, t_end: float, *, model: str = "coulomb", max_bounces: int = 50,
                       goals: bool = True, t0: float = 0.0) -> dict:
    """パックの経路を閉形式で繋ぐ: 区間(壁から壁)ごとに向き一定・等減速、壁で :func:`puck_wall_bounce`。

    時計: p₀・v₀ は時刻 ``t0``(既定 0)の状態、``t_end`` はそこからの長さ。区間の時刻と交点の時刻は **t0 を含む絶対時刻**
    (速度推定の ``t_ref`` を t0 に渡せば交点の時刻がカメラの時計で出る)。
    ``model`` = "coulomb"(a = μg、停止あり)/ "viscous"(a = (c/m) v、Challenge の MJCF の減衰)/ "none"(摩擦なし)。
    壁に当たる時刻は d(τ) = 必要距離 の閉形式解(二次方程式か対数)。``goals=True`` なら端の壁の |y| < goal_half は
    ゴール(そこで終わる、event "goal")。速さが 0 になれば "stop"、時間切れは "end"。
    返り値 ``{"segments": [{"t0","t1","p0","v0","u","s0","event"}, …], "t_end", "p_end", "v_end", "n_bounces", "events"}``。
    経路の位置は :func:`puck_state_at`。鏡映法(:func:`puck_mirror_path`、摩擦なし・e = kₜ = 1)と 1e-9 で一致(門)。"""
    p = _v2(p0, "p0").copy()
    v = _v2(v0, "v0").copy()
    if t_end < 0:
        raise ValueError("t_end must be >= 0")
    k = _decel_params(table, model)
    r = table["puck_radius"]
    xb, yb = table["x_half"] - r, table["y_half"] - r
    if abs(p[0]) > xb + 1e-12 or abs(p[1]) > yb + 1e-12:
        raise ValueError("p0 is outside the table")
    segs, events = [], []
    t = float(t0)
    t_final = float(t0) + float(t_end)
    nb = 0
    while True:
        s0 = float(np.linalg.norm(v))
        if s0 <= 1e-15:
            segs.append({"t0": t, "t1": t_final, "p0": p.copy(), "v0": v.copy(), "u": np.zeros(2), "s0": 0.0, "event": "stop"})
            events.append("stop")
            break
        u = v / s0
        cands = []
        for ax, bound, name in ((0, xb, "x"), (1, yb, "y")):
            if u[ax] > 1e-15:
                cands.append(((bound - p[ax]) / u[ax], ax, +1, name + "+"))
            elif u[ax] < -1e-15:
                cands.append(((-bound - p[ax]) / u[ax], ax, -1, name + "-"))
        d_wall, ax, sgn, wname = min(cands, key=lambda c: c[0])
        tau_wall = _time_to_distance(model, s0, k, d_wall)
        tau_stop = _stop_time(model, s0, k)
        remain = t_final - t
        tau_free = tau_stop if tau_wall is None else tau_wall
        if tau_free >= remain or tau_wall is None:
            tau = min(remain, tau_free)
            ev = "end" if tau >= remain else "stop"
            d = float(_dist_at(model, s0, k, tau))
            p1 = p + d * u
            v1 = float(_speed_at(model, s0, k, tau)) * u
            segs.append({"t0": t, "t1": t + tau, "p0": p.copy(), "v0": v.copy(), "u": u, "s0": s0, "event": ev})
            events.append(ev)
            t, p, v = t + tau, p1, v1
            if ev == "stop" and t < t_final:
                segs.append({"t0": t, "t1": t_final, "p0": p.copy(), "v0": np.zeros(2), "u": np.zeros(2), "s0": 0.0, "event": "stop"})
            break
        d = float(_dist_at(model, s0, k, tau_wall))
        p1 = p + d * u
        v_hit = float(_speed_at(model, s0, k, tau_wall)) * u
        if goals and ax == 0 and abs(p1[1]) < table["goal_half"]:
            segs.append({"t0": t, "t1": t + tau_wall, "p0": p.copy(), "v0": v.copy(), "u": u, "s0": s0, "event": "goal"})
            events.append("goal")
            t, p, v = t + tau_wall, p1, v_hit
            break
        normal = np.zeros(2)
        normal[ax] = -sgn
        b = puck_wall_bounce(v_hit, normal, table["e"], table["kt"])
        segs.append({"t0": t, "t1": t + tau_wall, "p0": p.copy(), "v0": v.copy(), "u": u, "s0": s0, "event": "wall_" + wname})
        events.append("wall_" + wname)
        t, p, v = t + tau_wall, p1, b["v"]
        nb += 1
        if nb > max_bounces:
            raise ValueError("more than %d bounces before t_end" % max_bounces)
    return {"segments": segs, "model": model, "k": k, "t0": float(t0), "t_end": t, "p_end": p, "v_end": v, "n_bounces": nb,
            "events": events, "table": table}


def puck_state_at(pred: dict, t) -> dict:
    """:func:`puck_slide_predict` の経路上の位置と速度を時刻 t(スカラーか (N,))で。終端より後は終端の状態のまま(位置は動かない、速度は終端の値 = 止まっていれば 0)。
    返り値 ``{"p" (N,2), "v" (N,2)}``。"""
    tt = np.atleast_1d(np.asarray(t, np.float64))
    P = np.empty((tt.size, 2))
    V = np.empty((tt.size, 2))
    segs = pred["segments"]
    model, k = pred["model"], pred["k"]
    for i, ti in enumerate(tt):
        seg = None
        for s in segs:
            if s["t0"] - 1e-12 <= ti <= s["t1"] + 1e-12:
                seg = s
                break
        if seg is None:
            seg = segs[-1] if ti > segs[-1]["t1"] else segs[0]
        tau = float(np.clip(ti - seg["t0"], 0.0, seg["t1"] - seg["t0"]))
        if seg["s0"] <= 0:
            P[i] = seg["p0"]
            V[i] = 0.0
        else:
            P[i] = seg["p0"] + float(_dist_at(model, seg["s0"], k, tau)) * seg["u"]
            V[i] = float(_speed_at(model, seg["s0"], k, tau)) * seg["u"]
    return {"p": P, "v": V}


def puck_crossing_point(pred: dict, x_line: float):
    """予測経路が守備線 x = ``x_line`` を最初に横切る時刻と場所(閉形式: 区間ごとに d(τ)·uₓ = 必要距離 を解く)。

    返り値 ``{"t", "p", "v", "segment"}``、横切らなければ ``None``(fail-closed —— 止まる・ゴールに入る・時間切れ)。"""
    model, k = pred["model"], pred["k"]
    for j, s in enumerate(pred["segments"]):
        if s["s0"] <= 0 or abs(s["u"][0]) < 1e-15:
            continue
        need = (x_line - s["p0"][0]) / s["u"][0]
        if need < -1e-12:
            continue
        tau = _time_to_distance(model, s["s0"], k, max(need, 0.0))
        if tau is None or tau > (s["t1"] - s["t0"]) + 1e-12:
            continue
        p = s["p0"] + float(_dist_at(model, s["s0"], k, tau)) * s["u"]
        v = float(_speed_at(model, s["s0"], k, tau)) * s["u"]
        return {"t": float(s["t0"] + tau), "p": p, "v": v, "segment": j}
    return None


def puck_mirror_path(p0, v0, table: dict, t_end: float) -> np.ndarray:
    """鏡映法(摩擦なし・e = kₜ = 1 専用): 直線 p₀ + v₀ t を壁の格子で折り返した位置を返す(第 2 実装、門の相手)。
    ゴールは無視(壁として扱う)。返り値 = 終端位置 (2,)。"""
    p = _v2(p0, "p0") + _v2(v0, "v0") * float(t_end)
    r = table["puck_radius"]
    out = np.empty(2)
    for ax, bound in ((0, table["x_half"] - r), (1, table["y_half"] - r)):
        period = 4.0 * bound
        q = (p[ax] + bound) % period
        out[ax] = (q if q <= 2.0 * bound else period - q) - bound
    return out


def puck_stop_distance(v0: float, table: dict) -> float:
    """停止距離 v₀²/(2μg)(:func:`ballistics.slide_stop_distance` と同じ式、こちらは table から μ・g を取る)。"""
    if table["mu"] <= 0:
        raise ValueError("mu must be > 0 for a finite stop distance")
    return float(v0 * v0 / (2.0 * table["mu"] * table["g"]))


# ─────────────────────────────── 合成カメラ(真上) ───────────────────────────────

def puck_camera(table: dict, *, px_per_m: float = 200.0, margin: float = 0.06) -> dict:
    """真上から見た合成カメラ: 台を等倍率で画素へ写すホモグラフィ(アフィン)。
    col = (x + x_half + margin)·s、row = (y_half + margin − y)·s。返り値 ``{"H" world→(col,row), "Hinv", "shape", "px_per_m", "margin", "table"}``。"""
    if px_per_m <= 0 or margin < 0:
        raise ValueError("need px_per_m > 0, margin >= 0")
    s = float(px_per_m)
    H = np.array([[s, 0.0, s * (table["x_half"] + margin)],
                  [0.0, -s, s * (table["y_half"] + margin)],
                  [0.0, 0.0, 1.0]])
    W = int(round(2.0 * (table["x_half"] + margin) * s))
    Hh = int(round(2.0 * (table["y_half"] + margin) * s))
    return {"H": H, "Hinv": np.linalg.inv(H), "shape": (Hh, W), "px_per_m": s, "margin": float(margin), "table": table}


def puck_pinhole_camera(table: dict, height: float, fovy_deg: float, shape) -> dict:
    """真上の針穴カメラ(位置 (0, 0, h)、−z を見る、up = +y、MuJoCo のカメラ規約)をホモグラフィに: col = W/2 + f x/h、
    row = H/2 − f y/h、f = (H/2)/tan(fovy/2)。パック上面の高さ(≈ 0.02 m)は無視(視差 h に対して 1 % 強、残差は門で測る)。
    ``shape`` = (H, W)。返り値は :func:`puck_camera` と同じ形。"""
    Hh, W = int(shape[0]), int(shape[1])
    if height <= 0 or not (0 < fovy_deg < 180) or Hh < 2 or W < 2:
        raise ValueError("need height > 0, 0 < fovy_deg < 180, shape >= 2x2")
    f = (Hh / 2.0) / np.tan(np.deg2rad(fovy_deg) / 2.0)
    s = f / height
    H = np.array([[s, 0.0, W / 2.0], [0.0, -s, Hh / 2.0], [0.0, 0.0, 1.0]])
    return {"H": H, "Hinv": np.linalg.inv(H), "shape": (Hh, W), "px_per_m": float(s), "margin": 0.0, "table": table}


def puck_world_to_pixel(cam: dict, xy) -> np.ndarray:
    """world (N,2) → 画素 (col, row) (N,2)(:func:`calib.image_to_world_plane` に H を渡す)。"""
    return _CAL.image_to_world_plane(np.asarray(xy, np.float64).reshape(-1, 2), cam["H"])


def puck_pixel_to_world(cam: dict, colrow) -> np.ndarray:
    """画素 (col, row) (N,2) → world (N,2)(:func:`calib.image_to_world_plane` に逆行列を渡す)。"""
    return _CAL.image_to_world_plane(np.asarray(colrow, np.float64).reshape(-1, 2), cam["Hinv"])


def _disk_coverage(shape, col: float, row: float, radius_px: float, roi: int) -> tuple:
    """円盤の被覆率(1 次の反エイリアス: clip(r + ½ − 距離, 0, 1))を ROI の窓だけ計算。返り値 (窓の slice, 被覆)。"""
    Hh, W = shape
    c0, c1 = max(0, int(col - roi)), min(W, int(col + roi) + 1)
    r0, r1 = max(0, int(row - roi)), min(Hh, int(row + roi) + 1)
    rr, cc = np.mgrid[r0:r1, c0:c1].astype(np.float64)
    d = np.hypot(cc - col, rr - row)
    return (slice(r0, r1), slice(c0, c1)), np.clip(radius_px + 0.5 - d, 0.0, 1.0)


def puck_render_frame(cam: dict, p, *, v=None, exposure: float = 0.0, n_sub: int = 16, noise: float = 0.0, rng=None,
                      puck_value: float = 0.12, table_value: float = 0.92, wall_value: float = 0.55) -> np.ndarray:
    """真上の 1 コマを合成(float (H,W)、0〜1): 白い台・灰色の壁・暗いパック(1 次の反エイリアス)。

    ``exposure`` > 0 なら露光の間 [t, t+exposure] にパックが v·exposure 動く分を n_sub 個の副露光の平均で入れる(モーションブラー)。
    コマの時刻は **露光の始め**: ブラーした像の重心は v·exposure/2 だけ進む(閉形式、門)。``noise`` はガウス雑音の σ。"""
    table = cam["table"]
    Hh, W = cam["shape"]
    s = cam["px_per_m"]
    img = np.full((Hh, W), wall_value, np.float64)
    cr0 = puck_world_to_pixel(cam, [[-table["x_half"], table["y_half"]]])[0]
    cr1 = puck_world_to_pixel(cam, [[table["x_half"], -table["y_half"]]])[0]
    img[int(round(cr0[1])):int(round(cr1[1])), int(round(cr0[0])):int(round(cr1[0]))] = table_value
    for xg in (-table["x_half"], table["x_half"]):
        g0 = puck_world_to_pixel(cam, [[xg - 0.03 if xg < 0 else xg, table["goal_half"]]])[0]
        g1 = puck_world_to_pixel(cam, [[xg if xg < 0 else xg + 0.03, -table["goal_half"]]])[0]
        img[int(round(g0[1])):int(round(g1[1])), int(round(g0[0])):int(round(g1[0]))] = 0.3
    p = _v2(p, "p")
    rp = table["puck_radius"] * s
    roi = int(rp + 3)
    if exposure > 0:
        if v is None:
            raise ValueError("exposure > 0 needs v")
        v = _v2(v, "v")
        taus = (np.arange(n_sub) + 0.5) / n_sub * exposure
        acc = np.zeros_like(img)
        for tau in taus:
            cr = puck_world_to_pixel(cam, [p + v * tau])[0]
            sl, cov = _disk_coverage((Hh, W), cr[0], cr[1], rp, roi + int(np.linalg.norm(v) * exposure * s) + 2)
            acc[sl] += cov / n_sub
        cov_full = acc
    else:
        cr = puck_world_to_pixel(cam, [p])[0]
        sl, cov = _disk_coverage((Hh, W), cr[0], cr[1], rp, roi)
        cov_full = np.zeros_like(img)
        cov_full[sl] = cov
    img = img * (1.0 - cov_full) + puck_value * cov_full
    if noise > 0:
        rng = np.random.default_rng(rng)
        img = img + rng.normal(0.0, noise, img.shape)
    return img


def puck_synth_frames(table: dict, cam: dict, p0, v0, *, fps: float = 120.0, n_frames: int = 24, exposure: float = 0.0,
                      noise: float = 0.0, rng=None, model: str = "coulomb") -> dict:
    """合成の連続コマと真値: 閉形式の経路(:func:`puck_slide_predict`)を fps で標本化し :func:`puck_render_frame` で描く。

    返り値 ``{"frames" [N], "t" (N,), "truth_xy" (N,2) 露光始めの位置, "truth_v" (N,2), "truth_px" (N,2), "pred", "cam", "fps", "exposure"}``。"""
    if fps <= 0 or n_frames < 1:
        raise ValueError("need fps > 0 and n_frames >= 1")
    t = np.arange(n_frames) / fps
    pred = puck_slide_predict(p0, v0, table, float(t[-1] + exposure + 1.0 / fps), model=model)
    st = puck_state_at(pred, t)
    rng = np.random.default_rng(rng)
    frames = [puck_render_frame(cam, st["p"][i], v=st["v"][i], exposure=exposure, noise=noise, rng=rng) for i in range(n_frames)]
    return {"frames": frames, "t": t, "truth_xy": st["p"], "truth_v": st["v"], "truth_px": puck_world_to_pixel(cam, st["p"]),
            "pred": pred, "cam": cam, "fps": float(fps), "exposure": float(exposure)}


# ─────────────────────────────── 検出・追跡 ───────────────────────────────

def puck_detect(frame, cam: dict, *, mode: str = "dark", thresh: float = 0.85, radius_tol: float = 0.5, color=None,
                color_tol: float = 0.25):
    """:func:`balltrack.ball_detect` の facade: 真上のコマから円盤を 1 つ取り、ホモグラフィで台の平面 (x, y) [m] に写す。

    ``mode`` = "dark"(白い台に暗いパック、合成)/ "color"・"chroma"(色で、MuJoCo の赤いパック)。``thresh`` は台の値
    (0.92)の少し下に置く: ``ball_detect`` の重みは (thresh − 画素値) なので、しきい値が台に近いほど重み ∝ 被覆率で
    重心が面積重心に一致する。中間の 0.5 では縁の画素が切れて位相依存の偏りが出る(実測 2026-10-04、r = 6.3 px:
    thresh 0.5 → 最大 0.08 px / 0.7 → 0.03 / 0.85 → 0.005、雑音 σ 0.01 でも 0.014)。半径が期待
    (puck_radius·px_per_m)の (1 ± radius_tol) 倍から外れる塊は捨てる。返り値 ``{"col","row","radius","fill","x","y"}`` か、
    見つからなければ ``None``(fail-closed)。知らない ``mode`` は ValueError。"""
    _choice("mode", mode, ("dark", "bright", "color", "chroma"))
    rp = cam["table"]["puck_radius"] * cam["px_per_m"]
    rr = ((1.0 - radius_tol) * rp, (1.0 + radius_tol) * rp)
    if mode in ("color", "chroma"):
        cands = _BT.ball_detect(frame, mode=mode, color=color, color_tol=color_tol, radius_range=rr)
    else:
        cands = _BT.ball_detect(frame, mode=mode, thresh=thresh, radius_range=rr)
    if not cands:
        return None
    b = cands[0]
    xy = puck_pixel_to_world(cam, [[b["col"], b["row"]]])[0]
    return {"col": b["col"], "row": b["row"], "radius": b["radius"], "fill": b["fill"], "x": float(xy[0]), "y": float(xy[1])}


def puck_track(frames, cam: dict, *, max_jump_px: float = 40.0, **detect_kw) -> dict:
    """コマ列 → コマごとの候補 → :func:`balltrack.ball_track`(等速予測で繋ぐ、``max_jump_px`` 超えは落とす)→ world 座標。

    返り値 ``{"frame" (N,), "col","row" (N,), "xy" (N,2), "found" (K,) bool}``。速いパック(1 コマの移動 > max_jump_px)では
    対応が切れてコマが落ちる —— その破れ方は門で測る。"""
    if not isinstance(frames, (list, tuple)) or len(frames) == 0 or not all(isinstance(f, np.ndarray) and f.ndim in (2, 3) for f in frames):
        raise ValueError("frames must be a non-empty list of 2-D (or RGB) arrays")
    dets = []
    for f in frames:
        d = puck_detect(f, cam, **detect_kw)
        dets.append([] if d is None else [{"col": d["col"], "row": d["row"], "radius": d["radius"], "score": d["fill"]}])
    tr = _BT.ball_track(dets, max_jump=max_jump_px)
    xy = puck_pixel_to_world(cam, np.column_stack([tr["col"], tr["row"]])) if tr["frame"].size else np.zeros((0, 2))
    return {"frame": tr["frame"], "col": tr["col"], "row": tr["row"], "xy": xy, "found": tr["found"]}


# ─────────────────────────────── 速度・μ・e の推定 ───────────────────────────────

def puck_velocity_estimate(t, xy, table: dict, *, model: str = "coulomb", t_ref=None, iters: int = 3) -> dict:
    """N 点の位置から速度を最小二乗で: 向き û を固定した等減速模型 p(τ) = p_ref + v_ref τ − ½ μg τ² û(τ = t − t_ref)。

    û は v_ref から取るので 3 回反復(初期値 = 端点の差)。"viscous" は基底 (1 − e^{−kτ})/k で線形、"none" は直線。
    雑音の見積り: 残差から σ_pos、(AᵀA)⁻¹ から v_ref の分散(``sigma_v``、等方)。返り値
    ``{"p_ref","v_ref","speed","u","t_ref","sigma_pos","sigma_v","sigma_p","resid_rms","n","model"}``。N < 3 は ValueError。"""
    tt = np.asarray(t, np.float64).reshape(-1)
    P = np.asarray(xy, np.float64).reshape(-1, 2)
    if tt.size != P.shape[0] or tt.size < 3:
        raise ValueError("need >= 3 samples with matching t")
    k = _decel_params(table, model)
    if t_ref is None:
        t_ref = float(tt[-1])
    tau = tt - t_ref
    if model == "viscous" and k > 0:
        basis = (1.0 - np.exp(-k * tau)) / k
    else:
        basis = tau
    A = np.column_stack([np.ones_like(tau), basis])
    u = P[-1] - P[0]
    u = u / max(np.linalg.norm(u), 1e-15)
    beta = None
    for _ in range(iters if model == "coulomb" else 1):
        Y = P + (0.5 * k * tau * tau)[:, None] * u if model == "coulomb" else P
        beta = np.linalg.lstsq(A, Y, rcond=None)[0]
        v_ref = beta[1]
        nv = np.linalg.norm(v_ref)
        if nv > 1e-15:
            u = v_ref / nv
    Y = P + (0.5 * k * tau * tau)[:, None] * u if model == "coulomb" else P
    R = Y - A @ beta
    dof = max(2 * tt.size - 4, 1)
    s2 = float(np.sum(R * R) / dof)
    cov = s2 * np.linalg.inv(A.T @ A)
    return {"p_ref": beta[0], "v_ref": beta[1], "speed": float(np.linalg.norm(beta[1])), "u": u, "t_ref": float(t_ref),
            "sigma_pos": float(np.sqrt(s2)), "sigma_v": float(np.sqrt(cov[1, 1])), "sigma_p": float(np.sqrt(cov[0, 0])),
            "resid_rms": float(np.sqrt(np.mean(R * R))), "n": int(tt.size), "model": model}


def puck_mu_from_decel(t, xy, g: float = G) -> dict:
    """向きに沿った距離 s(t) に二次式を当て、a = 2c₂ から μ = −a/g(Coulomb の等減速)。``{"mu", "a", "v0", "resid_rms"}``。N < 4 は ValueError。"""
    tt = np.asarray(t, np.float64).reshape(-1)
    P = np.asarray(xy, np.float64).reshape(-1, 2)
    if tt.size != P.shape[0] or tt.size < 4:
        raise ValueError("need >= 4 samples with matching t")
    u = P[-1] - P[0]
    u = u / max(np.linalg.norm(u), 1e-15)
    s = (P - P[0]) @ u
    c = np.polyfit(tt - tt[0], s, 2)
    a = 2.0 * c[0]
    res = s - np.polyval(c, tt - tt[0])
    return {"mu": float(-a / g), "a": float(a), "v0": float(c[1]), "resid_rms": float(np.sqrt(np.mean(res ** 2)))}


def puck_restitution_from_wall(t, xy, table: dict, *, model: str = "coulomb") -> dict:
    """壁で跳ねた軌跡から e(法線)と kₜ(接線): 向きが最も変わるコマで前後に分け、両側を :func:`puck_velocity_estimate` で
    衝突時刻へ外挿。壁は衝突点に最も近い壁。``{"e", "kt", "t_hit", "wall", "n_before", "n_after", "v_in", "v_out"}``。両側 3 点未満は ValueError。"""
    tt = np.asarray(t, np.float64).reshape(-1)
    P = np.asarray(xy, np.float64).reshape(-1, 2)
    if tt.size != P.shape[0] or tt.size < 6:
        raise ValueError("need >= 6 samples (3 each side of the bounce) with matching t")
    d = np.diff(P, axis=0)
    ang = np.arctan2(d[:, 1], d[:, 0])
    dang = np.abs(np.angle(np.exp(1j * np.diff(ang))))
    j = int(np.argmax(dang)) + 1
    if j < 3 or tt.size - j < 3:
        raise ValueError("bounce too close to the ends of the track")
    r = table["puck_radius"]
    walls = {"x+": (0, table["x_half"] - r), "x-": (0, -(table["x_half"] - r)),
             "y+": (1, table["y_half"] - r), "y-": (1, -(table["y_half"] - r))}
    pm = 0.5 * (P[j - 1] + P[j])
    wall = min(walls, key=lambda w: abs(pm[walls[w][0]] - walls[w][1]))
    ax, bound = walls[wall]
    before = puck_velocity_estimate(tt[:j], P[:j], table, model=model, t_ref=tt[j - 1])
    after = puck_velocity_estimate(tt[j:], P[j:], table, model=model, t_ref=tt[j])
    k = _decel_params(table, model)
    s0 = before["speed"]
    u = before["u"]
    need = (bound - before["p_ref"][ax]) / u[ax] if abs(u[ax]) > 1e-15 else None
    tau = _time_to_distance(model, s0, k, max(need, 0.0)) if need is not None else None
    t_hit = tt[j - 1] + (tau if tau is not None else 0.5 * (tt[j] - tt[j - 1]))
    v_in = float(_speed_at(model, s0, k, t_hit - tt[j - 1])) * u
    tau2 = t_hit - tt[j]
    v_out = float(_speed_at(model, after["speed"], k, tau2)) * after["u"]
    n = np.zeros(2)
    n[ax] = -np.sign(bound)
    vn_in, vn_out = float(v_in @ n), float(v_out @ n)
    vt_in = v_in - vn_in * n
    vt_out = v_out - vn_out * n
    e = -vn_out / vn_in if abs(vn_in) > 1e-15 else np.nan
    kt = float(np.linalg.norm(vt_out) / np.linalg.norm(vt_in)) if np.linalg.norm(vt_in) > 1e-12 else np.nan
    return {"e": float(e), "kt": kt, "t_hit": float(t_hit), "wall": wall, "n_before": j, "n_after": int(tt.size - j),
            "v_in": v_in, "v_out": v_out}


# ─────────────────────────────── 5 節リンク ───────────────────────────────

def fivebar_link(*, d: float = 0.30, l1: float = 0.25, l2: float = 0.35, base=(-1.05, 0.0)) -> dict:
    """平面 5 節リンク(2 本の 2 リンク腕の先端を 1 点で繋ぐ): 根元 A₁ = base + (0, −d/2)、A₂ = base + (0, +d/2)、
    近位 l₁・遠位 l₂、前方 = +x。数は **仮定**(IROS 2024 の実機の寸法は原文を読めていない)。返り値 dict(``table`` sort)。"""
    if not (d > 0 and l1 > 0 and l2 > 0):
        raise ValueError("need d, l1, l2 > 0")
    b = _v2(base, "base")
    return {"d": float(d), "l1": float(l1), "l2": float(l2), "base": b,
            "A1": b + np.array([0.0, -d / 2.0]), "A2": b + np.array([0.0, d / 2.0])}


def _circle_intersections(c1, r1, c2, r2):
    """2 円の交点(2 つ、(2,2))。交わらなければ None。"""
    dvec = c2 - c1
    dd = float(np.linalg.norm(dvec))
    if dd < 1e-15 or dd > r1 + r2 + 1e-12 or dd < abs(r1 - r2) - 1e-12:
        return None
    a = (r1 * r1 - r2 * r2 + dd * dd) / (2.0 * dd)
    h2 = r1 * r1 - a * a
    h = np.sqrt(max(h2, 0.0))
    ex = dvec / dd
    ey = np.array([-ex[1], ex[0]])
    m = c1 + a * ex
    return np.array([m + h * ey, m - h * ey])


def fivebar_fk(q, link: dict, *, branch: str = "forward"):
    """順運動学: 関節角 (q₁, q₂)(各腕の近位リンクの x 軸からの角)→ 先端 E。肘 Bᵢ = Aᵢ + l₁(cos qᵢ, sin qᵢ)、
    E = 円(B₁, l₂) ∩ 円(B₂, l₂) の "forward"(x が大きい側)か "back"。返り値 ``{"E", "B1", "B2"}``、交わらなければ ``None``。"""
    _choice("branch", branch, ("forward", "back"))
    q = _v2(q, "q")
    B1 = link["A1"] + link["l1"] * np.array([np.cos(q[0]), np.sin(q[0])])
    B2 = link["A2"] + link["l1"] * np.array([np.cos(q[1]), np.sin(q[1])])
    X = _circle_intersections(B1, link["l2"], B2, link["l2"])
    if X is None:
        return None
    i = int(np.argmax(X[:, 0])) if branch == "forward" else int(np.argmin(X[:, 0]))
    return {"E": X[i], "B1": B1, "B2": B2}


def fivebar_ik(E, link: dict, *, branch: str = "out"):
    """逆運動学: 先端 E → (q₁, q₂)。腕 i の肘 = 円(Aᵢ, l₁) ∩ 円(E, l₂)、"out" は肘が外側(腕 1 は −y 側、腕 2 は +y 側)、
    "in" はその逆。届かなければ ``None``(fail-closed)。FK∘IK = 恒等になる領域が作業域(:func:`fivebar_workspace`)。"""
    _choice("branch", branch, ("out", "in"))
    E = _v2(E, "E")
    qs = []
    for i, A in enumerate((link["A1"], link["A2"])):
        X = _circle_intersections(A, link["l1"], E, link["l2"])
        if X is None:
            return None
        side = -1.0 if i == 0 else 1.0
        if branch == "in":
            side = -side
        j = int(np.argmax(side * X[:, 1]))
        B = X[j]
        qs.append(np.arctan2(B[1] - A[1], B[0] - A[0]))
    return np.array(qs)


def fivebar_workspace(link: dict, *, n: int = 161, tol: float = 1e-9) -> dict:
    """作業域: 格子の各点で IK が解けて FK∘IK が tol で戻る所(枝 out/forward で矛盾しない所だけを「届く」とする)。
    返り値 ``{"xs","ys","mask","area","x_max","x_min"}``(x_max = 届く最前の x)。"""
    if n < 3:
        raise ValueError("n must be >= 3")
    r_max = link["l1"] + link["l2"]
    b = link["base"]
    xs = np.linspace(b[0] - r_max, b[0] + r_max, n)
    ys = np.linspace(b[1] - r_max - link["d"] / 2, b[1] + r_max + link["d"] / 2, n)
    mask = np.zeros((ys.size, xs.size), bool)
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            q = fivebar_ik((x, y), link)
            if q is None:
                continue
            fk = fivebar_fk(q, link)
            if fk is not None and np.linalg.norm(fk["E"] - (x, y)) < tol:
                mask[iy, ix] = True
    cell = (xs[1] - xs[0]) * (ys[1] - ys[0])
    xr = xs[np.any(mask, axis=0)]
    return {"xs": xs, "ys": ys, "mask": mask, "area": float(mask.sum() * cell),
            "x_max": float(xr.max()) if xr.size else np.nan, "x_min": float(xr.min()) if xr.size else np.nan}


def fivebar_reach_interval(link: dict, x_line: float, *, n: int = 801) -> dict:
    """守備線 x = x_line 上で届く y の区間(格子で、FK∘IK 往復つき)。``{"y_lo","y_hi","ok"}``。"""
    if n < 3:
        raise ValueError("n must be >= 3")
    r_max = link["l1"] + link["l2"]
    ys = np.linspace(-r_max - link["d"], r_max + link["d"], n) + link["base"][1]
    ok = np.zeros(ys.size, bool)
    for i, y in enumerate(ys):
        q = fivebar_ik((x_line, y), link)
        if q is None:
            continue
        fk = fivebar_fk(q, link)
        ok[i] = fk is not None and np.linalg.norm(fk["E"] - (x_line, y)) < 1e-9
    yy = ys[ok]
    return {"y_lo": float(yy.min()) if yy.size else np.nan, "y_hi": float(yy.max()) if yy.size else np.nan, "ok": bool(yy.size)}


def striker_plan(crossing, q_now, link: dict, *, omega_max: float = 6.0, t_now: float = 0.0, margin: float = 0.0) -> dict:
    """打点計画(規則): 予測の交点へ IK で関節角を出し、各サーボを一定角速度 ≤ ω_max で動かす。所要 = max|Δq|/ω_max。
    交点の到着より先に着けば feasible。返り値 ``{"feasible","reason","q_target","dq","t_move","t_arrive","t_cross","E"}``、
    reason ∈ {"ok","no_crossing","unreachable","too_late"}。``crossing`` = :func:`puck_crossing_point` の返り値(None 可)。
    ω_max = 6 rad/s の既定は仮定。"""
    if omega_max <= 0:
        raise ValueError("omega_max must be > 0")
    q_now = _v2(q_now, "q_now")
    out = {"feasible": False, "reason": "no_crossing", "q_target": None, "dq": None, "t_move": np.nan, "t_arrive": np.nan,
           "t_cross": np.nan, "E": None}
    if crossing is None:
        return out
    if not isinstance(crossing, dict) or "p" not in crossing or "t" not in crossing:
        raise ValueError("crossing must be None or the dict returned by puck_crossing_point")
    E = _v2(crossing["p"], "crossing p")
    out["t_cross"] = float(crossing["t"])
    out["E"] = E
    q = fivebar_ik(E, link)
    fk = fivebar_fk(q, link) if q is not None else None
    if q is None or fk is None or np.linalg.norm(fk["E"] - E) > 1e-9:
        out["reason"] = "unreachable"
        return out
    dq = np.angle(np.exp(1j * (q - q_now)))
    t_move = float(np.max(np.abs(dq)) / omega_max)
    out.update({"q_target": q, "dq": dq, "t_move": t_move, "t_arrive": t_now + t_move})
    if t_now + t_move + margin > crossing["t"]:
        out["reason"] = "too_late"
        return out
    out.update({"feasible": True, "reason": "ok"})
    return out


def fivebar_trajectory(q_now, plan: dict, t) -> np.ndarray:
    """計画の関節軌道 q(t): t_now から t_move の間は一定角速度、着いたら止まる。(N,2)。"""
    q_now = _v2(q_now, "q_now")
    tt = np.atleast_1d(np.asarray(t, np.float64))
    if plan.get("q_target") is None:
        return np.tile(q_now, (tt.size, 1))
    t0 = plan["t_arrive"] - plan["t_move"]
    frac = np.clip((tt - t0) / max(plan["t_move"], 1e-15), 0.0, 1.0)
    return q_now[None, :] + frac[:, None] * plan["dq"][None, :]


# ─────────────────────────────── MuJoCo ───────────────────────────────

def puck_scene_mjcf(table: dict, *, cam_height: float = 1.5, fovy: float = 50.0, offwidth: int = 1024,
                    offheight: int = 768) -> str:
    """自前の最小 MJCF(Coulomb 版、mujoco 不要): 摩擦のある平面に円柱のパック(自由関節)、4 枚の壁(箱)、真上カメラ。
    Challenge の台は粘性減衰なので、Coulomb の等減速を MuJoCo で確かめるにはこちらを使う。壁の反発は軟接触で e は測る。"""
    if cam_height <= 0 or not (0 < fovy < 180) or offwidth < 8 or offheight < 8:
        raise ValueError("need cam_height > 0, 0 < fovy < 180, offscreen >= 8 px")
    r = table["puck_radius"]
    xh, yh = table["x_half"], table["y_half"]
    th = 0.045
    return """<mujoco model="puck_table_coulomb">
  <option timestep="0.0005" cone="elliptic" impratio="1" gravity="0 0 -%g"/>
  <visual><global offwidth="%d" offheight="%d"/></visual>
  <default><geom condim="3" solref="0.005 1"/></default>
  <worldbody>
    <camera name="top" pos="0 0 %g" quat="1 0 0 0" fovy="%g"/>
    <light pos="0 0 3" dir="0 0 -1" directional="true"/>
    <geom name="surface" type="box" size="%g %g 0.02" pos="0 0 -0.02" rgba="0.95 0.95 0.95 1" friction="%g 0.005 0.0001" priority="1"/>
    <geom name="wall_xp" type="box" size="%g %g 0.02" pos="%g 0 0.02" rgba="0.5 0.5 0.5 1" friction="0 0 0" priority="2"/>
    <geom name="wall_xm" type="box" size="%g %g 0.02" pos="%g 0 0.02" rgba="0.5 0.5 0.5 1" friction="0 0 0" priority="2"/>
    <geom name="wall_yp" type="box" size="%g %g 0.02" pos="0 %g 0.02" rgba="0.5 0.5 0.5 1" friction="0 0 0" priority="2"/>
    <geom name="wall_ym" type="box" size="%g %g 0.02" pos="0 %g 0.02" rgba="0.5 0.5 0.5 1" friction="0 0 0" priority="2"/>
    <body name="puck" pos="0 0 0.01">
      <freejoint name="puck_free"/>
      <geom name="puck" type="cylinder" size="%g 0.01" rgba="0.9 0.1 0.1 1" mass="%g" friction="%g 0.005 0.0001"/>
    </body>
  </worldbody>
</mujoco>
""" % (table["g"], offwidth, offheight, cam_height, fovy, xh + th, yh + th, table["mu"],
       th / 2, yh + th, xh + th / 2, th / 2, yh + th, -(xh + th / 2), xh + th, th / 2, yh + th / 2, xh + th, th / 2,
       -(yh + th / 2), r, table["mass"], table["mu"])


def puck_challenge_mjcf(path: str | None = None, *, cam_height: float = 1.5, fovy: float = 50.0) -> tuple:
    """Robot Air Hockey Challenge の ``table.xml``(MIT、配布物、repo には同梱しない)を読み、真上カメラと大きい offscreen buffer を
    文字列で足す(元ファイルは触らない)。``path`` が None なら環境変数 ``FULLSEYE_AIRHOCKEY_DATA`` の下の ``table.xml``。
    無ければ FileNotFoundError(fail-closed)。rim の STL は同じディレクトリの ``table_rim.stl``。返り値 (xml 文字列, assets dict)。"""
    if path is None:
        root = os.environ.get("FULLSEYE_AIRHOCKEY_DATA", "").strip()
        if not root:
            raise FileNotFoundError("FULLSEYE_AIRHOCKEY_DATA is not set (place table.xml and table_rim.stl of the Challenge there)")
        path = os.path.join(root, "table.xml")
    with open(path, encoding="utf-8") as f:
        xml = f.read()
    cam = '<camera name="top" pos="0 0 %g" quat="1 0 0 0" fovy="%g"/>\n        <light pos="0 0 3"' % (cam_height, fovy)
    xml2 = xml.replace('<light pos="0 0 3"', cam, 1)
    xml2 = xml2.replace('<asset>', '<visual><global offwidth="1024" offheight="768"/></visual>\n    <asset>', 1)
    if xml2.count('name="top"') != 1 or 'offwidth' not in xml2:
        raise ValueError("table.xml did not contain the expected anchors")
    stl = os.path.join(os.path.dirname(path), "table_rim.stl")
    with open(stl, "rb") as f:
        assets = {"table_rim.stl": f.read()}
    return xml2, assets


def puck_mujoco_run(xml: str, assets, p0, v0, *, fps: float, duration: float, render: bool = True, shape=(480, 800),
                    puck_joint: str = "puck_x") -> dict:
    """MuJoCo でパックを打ち出し、コマの時刻の真値(位置・速度)と(任意で)真上のコマを記録する(第 2 実装、mujoco が要る)。

    ``puck_joint`` = "puck_x"(Challenge: slide×2 + hinge)か "puck_free"(自前 :func:`puck_scene_mjcf`: freejoint)。返り値
    ``{"t" (N,), "xy" (N,2), "v" (N,2), "frames" [N] uint8 RGB or None, "dt_sim", "model"}``。mujoco が無ければ ImportError。"""
    import mujoco
    _choice("puck_joint", puck_joint, ("puck_x", "puck_free"))
    m = mujoco.MjModel.from_xml_string(xml, assets or {})
    d = mujoco.MjData(m)
    p0 = _v2(p0, "p0")
    v0 = _v2(v0, "v0")
    d.qpos[0], d.qpos[1] = p0
    d.qvel[0], d.qvel[1] = v0
    mujoco.mj_forward(m, d)
    rend = mujoco.Renderer(m, shape[0], shape[1]) if render else None
    n = int(round(duration * fps))
    T, XY, V, F = [], [], [], []
    dt = m.opt.timestep
    steps_per_frame = int(round(1.0 / (fps * dt)))
    if abs(steps_per_frame * dt * fps - 1.0) > 1e-9:
        raise ValueError("fps must divide the simulation timestep: 1/(fps*dt) = %g" % (1.0 / (fps * dt)))
    for _ in range(n):
        T.append(d.time)
        XY.append(d.qpos[:2].copy())
        V.append(d.qvel[:2].copy())
        if rend is not None:
            rend.update_scene(d, camera="top")
            F.append(rend.render().copy())
        for _ in range(steps_per_frame):
            mujoco.mj_step(m, d)
    if rend is not None:
        rend.close()
    return {"t": np.asarray(T), "xy": np.asarray(XY), "v": np.asarray(V), "frames": F if render else None, "dt_sim": dt,
            "model": m}
