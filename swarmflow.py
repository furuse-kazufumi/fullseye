# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""swarmflow — 流体のように流れる群れが、見えない障害物を「速度場の乱れ」だけで察知する(学習なし、2026-10-05)。

群れのロボットを SPH(平滑化粒子流体力学)の粒子として動かすと、群れ全体が一つの流体のように振る舞い、障害物に当たった
一部の個体の減速が圧力として上流へ伝わる。上から撮った映像で個体の速度場を測れば、障害物そのものは見えなくても、
自由流からの速度の欠け方で**衝突点(よどみ点)と障害物の位置・半径**が読める。題材の背景は群れロボットの流体模倣制御
(doi:10.1109/iros58592.2024.10801800 と、その発展の 2025 年の論文誌)。本文は使っていない —— 式はすべて下の閉形式から。

外から来るもの(閉形式の真値):
  * **SPH の 3 次スプライン核**(M4、Monaghan 1992)。正規化の定数は 1 次元 2/(3h)、2 次元 10/(7π h²)、3 次元 1/(π h³)。
    恒等式 ∫ W dV = 1 が門になる(数値の求積で、どの次元でも 1)。
  * **円柱まわりのポテンシャル流**: 複素速度 u − i v = U (1 − R²/(z − z_c)²)。よどみ点は z_c − R(上流の衝突点)と z_c + R、
    表面の速さは 2U |sin θ|、中心線の上では u = U (1 − R²/(x − x_c)²)。
  * **なぜ群れの流れがポテンシャル流に近づくか(導出)**: 個体が自由流の速さ U へ時定数 τ で戻ろうとする(抵抗 (U − v)/τ)とき、
    U τ ≪ R なら移流の項は抵抗に比べて小さく、定常では v' = −τ ∇p/ρ(Darcy の流れ)。弱圧縮(音速 c ≫ U)で ∇·v ≈ 0 なら
    ∇²p = 0 —— **Hele-Shaw / Darcy の流れは円柱のまわりで厳密にポテンシャル流**。滑る壁(法線の速度だけ 0)とも整合する。
  * **中心線の欠損の直線化(導出)**: 欠損 d(x) = 1 − u/U = R²/(x − x_c)² だから 1/√d = (x_c − x)/R は x の 1 次式。傾きが
    −1/R、x 切片が x_c。上流だけの点で引けるので「当たる前に」分かる。
  * **Ritter のダム崩壊解**(浅水方程式、乾いた床): 先端の速さ 2√(g h₀)、後ろへ走る膨張波の頭 −√(g h₀)、扇の中で
    h = (2√(g h₀) − x/t)²/(9g)、u = (2/3)(x/t + √(g h₀))、ダムの位置で h = 4h₀/9。群れのゲートを開けたときの広がりに当たる。

numpy 層(台帳 ``swarmflow``、opsdrive): :func:`sph_kernel` 核と勾配 / :func:`sph_density_pressure` 密度と圧力 /
  :func:`swarm_simulate` 障害物のある流路を流れる群れ(SPH、周期境界)/ :func:`swarm_render_overhead` 俯瞰映像の 1 コマ /
  :func:`swarm_field_from_tracks` 個体の検出(blob2d)と追跡から格子の速度場 / :func:`swarm_field_from_piv` 相互相関の PIV
  (pivops)で速度場 / :func:`potential_flow_cylinder` 円柱まわりの閉形式 / :func:`velocity_deficit_map` 自由流からの欠損 /
  :func:`stagnation_from_centerline` 中心線の直線化でよどみ点・中心・半径 / :func:`obstacle_fit_doublet` 二重湧き出しの
  当てはめ(2 次元の最小二乗)と「障害物あり」の判定 / :func:`ritter_dam_break` 閉形式 / :func:`sph_dam_break_1d` SPH の浅水。

規約: 長さは m、速さは m/s、時間は s。自由流は +x 向き。速度場は dict(``x`` (W,) 昇順、``y`` (H,) **行の順 = 降順**、``u``・
``v`` (H, W)、``valid`` (H, W) bool —— 測れない格子は NaN で ``valid`` が False)。画像は列 = +x、行 = −y、画素の中心が整数、
画像の中心 ((W − 1)/2, (H − 1)/2) が世界の ``center``。
"""
from __future__ import annotations

import math

import numpy as np

__all__ = [
    "sph_kernel", "sph_density_pressure", "swarm_simulate", "swarm_render_overhead", "swarm_field_from_tracks",
    "swarm_field_from_piv", "potential_flow_cylinder", "velocity_deficit_map", "stagnation_from_centerline",
    "obstacle_fit_doublet", "ritter_dam_break", "sph_dam_break_1d",
]

_SIGMA = {1: 2.0 / 3.0, 2: 10.0 / (7.0 * math.pi), 3: 1.0 / math.pi}


# ======================================================================================================================
# 0. 検査の小道具
def _pos(x, name: str, op: str, allow_zero: bool = False) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, x)) from None
    if not math.isfinite(v) or v < 0.0 or (v == 0.0 and not allow_zero):
        raise ValueError("%s: %s must be finite and %s 0, got %r" % (op, name, ">=" if allow_zero else ">", x))
    return v


def _num(x, name: str, op: str) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a number, got %r" % (op, name, x)) from None
    if not math.isfinite(v):
        raise ValueError("%s: %s must be finite, got %r" % (op, name, x))
    return v


def _pts(p, name: str, op: str, min_n: int = 1) -> np.ndarray:
    a = np.asarray(p, np.float64)
    if a.ndim != 2 or a.shape[1] != 2 or len(a) < min_n:
        raise ValueError("%s: %s must be an (N, 2) array with N >= %d, got shape %r" % (op, name, min_n, a.shape))
    if not np.all(np.isfinite(a)):
        raise ValueError("%s: %s has non-finite values" % (op, name))
    return a


def _img(a, name: str, op: str, min_side: int = 8) -> np.ndarray:
    z = np.asarray(a, np.float64)
    if z.ndim != 2 or min(z.shape) < min_side:
        raise ValueError("%s: %s must be a 2-D array with sides >= %d, got shape %r" % (op, name, min_side, z.shape))
    if not np.all(np.isfinite(z)):
        raise ValueError("%s: %s has non-finite values" % (op, name))
    return z


def _frames(frames, op: str) -> list[np.ndarray]:
    try:
        fr = [_img(f, "frames[%d]" % i, op) for i, f in enumerate(frames)]
    except TypeError:
        raise ValueError("%s: frames must be a sequence of 2-D images" % op) from None
    if len(fr) < 2:
        raise ValueError("%s: need at least 2 frames, got %d" % (op, len(fr)))
    if any(f.shape != fr[0].shape for f in fr):
        raise ValueError("%s: all frames must have the same shape" % op)
    return fr


def _center(center, op: str) -> tuple[float, float]:
    try:
        cx, cy = float(center[0]), float(center[1])
    except (TypeError, ValueError, IndexError):
        raise ValueError("%s: center must be (x, y), got %r" % (op, center)) from None
    if not (math.isfinite(cx) and math.isfinite(cy)):
        raise ValueError("%s: center must be finite, got %r" % (op, center))
    return cx, cy


def _cyl(cylinder, op: str) -> tuple[float, float, float]:
    try:
        xc, yc, r = (float(cylinder[0]), float(cylinder[1]), float(cylinder[2]))
    except (TypeError, ValueError, IndexError):
        raise ValueError("%s: cylinder must be (xc, yc, R), got %r" % (op, cylinder)) from None
    if not (math.isfinite(xc) and math.isfinite(yc)) or not (math.isfinite(r) and r > 0.0):
        raise ValueError("%s: cylinder must be finite with R > 0, got %r" % (op, cylinder))
    return xc, yc, r


def _field(field, op: str) -> dict:
    """速度場の dict を検査して (x, y, u, v, valid) の配列にそろえる(NaN の格子は valid = False に落とす)。"""
    if not isinstance(field, dict):
        raise ValueError("%s: field must be a dict with x, y, u, v (and optionally valid), got %r" % (op, type(field)))
    try:
        x = np.asarray(field["x"], np.float64)
        y = np.asarray(field["y"], np.float64)
        u = np.asarray(field["u"], np.float64)
        v = np.asarray(field["v"], np.float64)
    except KeyError as exc:
        raise ValueError("%s: field is missing key %s" % (op, exc)) from None
    if x.ndim != 1 or y.ndim != 1 or u.shape != (y.size, x.size) or v.shape != u.shape:
        raise ValueError("%s: field needs x (W,), y (H,), u and v (H, W); got %r %r %r %r" % (op, x.shape, y.shape, u.shape, v.shape))
    if x.size < 3 or y.size < 3 or not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise ValueError("%s: field axes must be finite with at least 3 nodes each" % op)
    valid = np.asarray(field.get("valid", np.ones(u.shape, bool)), bool)
    if valid.shape != u.shape:
        raise ValueError("%s: field valid must have shape %r" % (op, u.shape))
    valid = valid & np.isfinite(u) & np.isfinite(v)
    return {"x": x, "y": y, "u": u, "v": v, "valid": valid}


def _pix_to_world(rows, cols, shape, res, center):
    h, w = shape
    return center[0] + (np.asarray(cols) - (w - 1) / 2.0) * res, center[1] + ((h - 1) / 2.0 - np.asarray(rows)) * res


def _world_to_pix(x, y, shape, res, center):
    h, w = shape
    return (h - 1) / 2.0 - (np.asarray(y) - center[1]) / res, (w - 1) / 2.0 + (np.asarray(x) - center[0]) / res


# ======================================================================================================================
# 1. SPH の核と密度・圧力
def sph_kernel(r, h: float, dim: int = 2, derivative: bool = False) -> np.ndarray:
    """3 次スプライン核 W(r, h)(M4、台の半径 2h)。``derivative=True`` で dW/dr(r の向きの微分、0 以下)。

    W = σ_d [1 − 1.5 q² + 0.75 q³] (0 ≤ q < 1)、σ_d · 0.25 (2 − q)³(1 ≤ q < 2)、0(q ≥ 2)、q = r/h。
    σ_1 = 2/(3h)、σ_2 = 10/(7π h²)、σ_3 = 1/(π h³)。この定数で ∫ W dV = 1(恒等式。門で数値の求積と照らす)。

    Args:
        r: 距離の配列(0 以上、形は任意)。
        h: 平滑化の長さ(> 0)。
        dim: 1、2、3。
        derivative: True で dW/dr を返す。
    Returns:
        r と同じ形の配列。
    Raises:
        ValueError: h ≤ 0、dim が 1〜3 でない、r に負・非有限がある。
    """
    op = "sph_kernel"
    hh = _pos(h, "h", op)
    if dim not in _SIGMA:
        raise ValueError("%s: dim must be 1, 2 or 3, got %r" % (op, dim))
    rr = np.asarray(r, np.float64)
    if not np.all(np.isfinite(rr)) or np.any(rr < 0.0):
        raise ValueError("%s: r must be finite and >= 0" % op)
    s = _SIGMA[dim] / hh ** dim
    q = rr / hh
    q1 = q < 1.0
    q2 = (q >= 1.0) & (q < 2.0)
    out = np.zeros_like(q)
    if derivative:
        out[q1] = s / hh * (-3.0 * q[q1] + 2.25 * q[q1] ** 2)
        out[q2] = s / hh * (-0.75 * (2.0 - q[q2]) ** 2)
    else:
        out[q1] = s * (1.0 - 1.5 * q[q1] ** 2 + 0.75 * q[q1] ** 3)
        out[q2] = s * 0.25 * (2.0 - q[q2]) ** 3
    return out


def _pairs(pos: np.ndarray, radius: float, box=None):
    """半径 radius 以内の点の組 (i, j)(i < j)と変位 r_ij = x_i − x_j(周期境界なら最小像)。"""
    from scipy.spatial import cKDTree
    if box is None:
        tree = cKDTree(pos)
        ij = tree.query_pairs(radius, output_type="ndarray")
        d = pos[ij[:, 0]] - pos[ij[:, 1]] if len(ij) else np.zeros((0, 2))
    else:
        L = np.asarray(box, np.float64)
        p = np.mod(pos, L)
        tree = cKDTree(p, boxsize=L)
        ij = tree.query_pairs(radius, output_type="ndarray")
        d = p[ij[:, 0]] - p[ij[:, 1]] if len(ij) else np.zeros((0, 2))
        d -= L * np.round(d / L)
    return ij, d


def sph_density_pressure(points, h: float, mass: float = 1.0, rho0: float = 1.0, c: float = 10.0, box=None) -> dict:
    """点の集まりの SPH 密度 ρ_i = Σ_j m W(|x_i − x_j|, h)(自分を含む)と、弱圧縮の状態方程式 p = c² (ρ − ρ₀)。

    格子の間隔 Δ で m = ρ₀ Δ² に置けば、内側の点の ρ は ρ₀ に近い(h = 1.3Δ で 0.3 % 以内 —— 門で数える)。

    Args:
        points: (N, 2) の位置 [m]。
        h: 平滑化の長さ [m]。
        mass: 1 点の質量(群れでは 1 = 個体数の密度)。
        rho0: 静止の密度。
        c: 音速 [m/s] (圧力の硬さ)。
        box: 周期境界の箱 (Lx, Ly) か None。
    Returns:
        dict: ``rho`` (N,)、``p`` (N,)、``n_neighbors`` (N,)(台の中の他の点の数)。
    """
    op = "sph_density_pressure"
    p = _pts(points, "points", op)
    hh, m, r0, cc = _pos(h, "h", op), _pos(mass, "mass", op), _pos(rho0, "rho0", op), _pos(c, "c", op)
    if box is not None:
        box = (_pos(box[0], "box[0]", op), _pos(box[1], "box[1]", op))
    ij, d = _pairs(p, 2.0 * hh, box)
    n = len(p)
    rho = np.full(n, m * sph_kernel(0.0, hh)[()])
    nn = np.zeros(n, np.int64)
    if len(ij):
        w = m * sph_kernel(np.hypot(d[:, 0], d[:, 1]), hh)
        rho += np.bincount(ij[:, 0], w, n) + np.bincount(ij[:, 1], w, n)
        nn += np.bincount(ij[:, 0], minlength=n) + np.bincount(ij[:, 1], minlength=n)
    return {"rho": rho, "p": cc * cc * (rho - r0), "n_neighbors": nn}


# ======================================================================================================================
# 2. 群れの模擬
def swarm_simulate(obstacle=None, speed: float = 1.0, box=(8.0, 5.0), spacing: float = 0.15, h_factor: float = 1.3,
                   tau: float = 0.1, c: float = 10.0, alpha: float = 0.5, t_warm: float = 2.0, n_frames: int = 20,
                   frame_dt: float = 0.06, noise: float = 0.0, seed: int = 0) -> dict:
    """障害物のある周期の流路を流れる群れ(SPH の弱圧縮流体として動く個体)。障害物は個体には「ぶつかる壁」として効くだけ。

    個体 i の加速度 = (U e_x − v_i)/τ(自由流の速さへ戻る)− Σ_j m (p_i/ρ_i² + p_j/ρ_j²) ∇W_ij(圧力 = 押し合い)
    − Σ_j m Π_ij ∇W_ij(Monaghan の人工粘性、近づく組だけ)+ 揺らぎ(標準偏差 ``noise`` [m/s²] の白色)。
    壁: 円の内側に入った個体は表面へ戻し、内向きの速度だけ消す(滑る壁)。周期境界(x も y も)。積分は symplectic Euler、
    刻みは CFL 0.25 h/(c + U)。U τ ≪ R・c ≫ U のとき定常の流れは円柱まわりのポテンシャル流に近い(module docstring の導出)。

    Args:
        obstacle: (xc, yc, R) [m] か None(障害物なし)。
        speed: 自由流の速さ U [m/s]。
        box: 流路の大きさ (Lx, Ly) [m]、中心が原点。
        spacing: 初期の格子の間隔 [m] (個体の間隔)。
        h_factor: h = h_factor × spacing。
        tau: 速さへ戻る時定数 [s]。
        c: 音速 [m/s] (押し合いの硬さ)。
        alpha: 人工粘性の係数。
        t_warm: 記録の前に流す時間 [s] (定常に近づける)。
        n_frames: 記録するコマ数(≥ 2)。
        frame_dt: コマの間隔 [s]。
        noise: 加速度の揺らぎ [m/s²]。
        seed: 乱数の種。
    Returns:
        dict: ``frames`` (T, N, 2) 位置 [m] (箱の中へ折り返し済み)、``velocities`` (T, N, 2)、``t`` (T,)、``box``、
        ``obstacle``、``h``、``dt``、``rho0``、``density_range``(記録の間の ρ/ρ₀ の 1〜99 % 点)、``n_agents``、
        ``t_total``(流した時間)、``t_wake_reenters``(障害物の後ろの空洞が箱の右端から左端へ回り込み始める時刻
        (Lx/2 − x_c − R)/U。これより長く流すと、上流の端に空洞の個体が入ってきて自由流が汚れる)。

    ★障害物の後ろには個体の入らない空洞が長く伸びる(押し合いの圧力は引っ張らないほど弱く、抵抗で U に戻るだけなので
    横から埋まらない)。俯瞰の映像では障害物の所の「穴」と空洞そのものが見える —— 速度だけで推定するという主張は、
    推定がこの穴を使わない(速度場の欠測として捨てる)という意味で、映像に障害物の手がかりが無いという意味ではない。
    """
    op = "swarm_simulate"
    U = _pos(speed, "speed", op)
    Lx, Ly = _pos(box[0], "box[0]", op), _pos(box[1], "box[1]", op)
    sp = _pos(spacing, "spacing", op)
    hh = _pos(h_factor, "h_factor", op) * sp
    ta, cc = _pos(tau, "tau", op), _pos(c, "c", op)
    al = _pos(alpha, "alpha", op, allow_zero=True)
    tw = _pos(t_warm, "t_warm", op, allow_zero=True)
    fd = _pos(frame_dt, "frame_dt", op)
    nz = _pos(noise, "noise", op, allow_zero=True)
    nf = int(n_frames)
    if nf < 2:
        raise ValueError("%s: n_frames must be >= 2, got %r" % (op, n_frames))
    if Lx < 8 * hh or Ly < 8 * hh:
        raise ValueError("%s: box %r is too small for h = %g (need >= 8h each side)" % (op, box, hh))
    obs = None if obstacle is None else _cyl(obstacle, op)
    rng = np.random.default_rng(int(seed))
    nx, ny = int(round(Lx / sp)), int(round(Ly / sp))
    gx, gy = np.meshgrid((np.arange(nx) + 0.5) * Lx / nx - Lx / 2, (np.arange(ny) + 0.5) * Ly / ny - Ly / 2)
    pos = np.column_stack([gx.ravel(), gy.ravel()]) + rng.normal(0.0, 0.05 * sp, (nx * ny, 2))
    L = np.array([Lx, Ly])
    m = 1.0
    rho0 = float(np.median(sph_density_pressure(pos + L / 2, hh, m, 1.0, cc, box=(Lx, Ly))["rho"]))
    if obs is not None:
        keep = np.hypot(pos[:, 0] - obs[0], pos[:, 1] - obs[1]) > obs[2] + 0.3 * sp
        pos = pos[keep]
    n = len(pos)
    vel = np.zeros((n, 2))
    vel[:, 0] = U
    dt = 0.25 * hh / (cc + U)
    n_rec = max(1, int(round(fd / dt)))
    dt = fd / n_rec
    n_warm = int(math.ceil(tw / dt))
    total = n_warm + (nf - 1) * n_rec
    frames, vels, ts, rhos = [], [], [], []
    target = np.array([U, 0.0])
    for step in range(total + 1):
        ij, d = _pairs(pos + L / 2, 2.0 * hh, (Lx, Ly))
        r = np.hypot(d[:, 0], d[:, 1])
        w = m * sph_kernel(r, hh)
        rho = np.full(n, m * sph_kernel(0.0, hh)[()]) + np.bincount(ij[:, 0], w, n) + np.bincount(ij[:, 1], w, n)
        p = cc * cc * (rho - rho0)
        dw = sph_kernel(r, hh, derivative=True)
        rs = np.where(r > 1e-12, r, 1e-12)
        e = d / rs[:, None]
        i0, j0 = ij[:, 0], ij[:, 1]
        coef = m * (p[i0] / rho[i0] ** 2 + p[j0] / rho[j0] ** 2)
        if al > 0:
            vij = vel[i0] - vel[j0]
            vr = np.sum(vij * d, axis=1)
            mu = hh * vr / (r * r + 0.01 * hh * hh)
            pi_ij = np.where(vr < 0.0, -al * cc * mu / (0.5 * (rho[i0] + rho[j0])), 0.0)
            coef = coef + m * pi_ij
        f = (coef * dw)[:, None] * e            # 粒子 i への −∇ の向きは −coef dW e、j へは +
        acc = (target - vel) / ta
        acc[:, 0] -= np.bincount(i0, f[:, 0], n) - np.bincount(j0, f[:, 0], n)
        acc[:, 1] -= np.bincount(i0, f[:, 1], n) - np.bincount(j0, f[:, 1], n)
        if step >= n_warm and (step - n_warm) % n_rec == 0:
            frames.append(pos.copy())
            vels.append(vel.copy())
            ts.append((step - n_warm) * dt)
            rhos.append(rho / rho0)
        if step == total:
            break
        if nz > 0:
            acc += rng.normal(0.0, nz, acc.shape)
        vel = vel + acc * dt
        pos = pos + vel * dt
        pos = np.mod(pos + L / 2, L) - L / 2
        if obs is not None:
            dx, dy = pos[:, 0] - obs[0], pos[:, 1] - obs[1]
            dist = np.hypot(dx, dy)
            ins = dist < obs[2]
            if np.any(ins):
                dd = np.where(dist[ins] > 1e-12, dist[ins], 1e-12)
                nrm = np.column_stack([dx[ins] / dd, dy[ins] / dd])
                pos[ins] = np.column_stack([obs[0], obs[1]]) + obs[2] * nrm
                vn = np.sum(vel[ins] * nrm, axis=1)
                vel[ins] -= np.minimum(vn, 0.0)[:, None] * nrm
    rr = np.concatenate(rhos)
    return {"frames": np.array(frames), "velocities": np.array(vels), "t": np.array(ts), "box": (Lx, Ly), "obstacle": obs,
            "h": hh, "dt": dt, "rho0": rho0, "density_range": (float(np.percentile(rr, 1)), float(np.percentile(rr, 99))),
            "n_agents": n, "speed": U, "t_total": total * dt,
            "t_wake_reenters": (math.inf if obs is None else (Lx / 2 - obs[0] - obs[2]) / U)}


# ======================================================================================================================
# 3. 俯瞰映像
def swarm_render_overhead(points, shape, res: float, center=(0.0, 0.0), diameter_px: float = 3.0, intensity: float = 1.0,
                          background: float = 0.0) -> np.ndarray:
    """個体の位置 → 上から見た 1 コマ(ガウスの輝点、直径 = 標準偏差の 2 倍 = PIV の慣行、pivops と同じ)。

    Args:
        points: (N, 2) の位置 [m] (空でもよい = 背景だけ)。
        shape: (H, W) [px]。
        res: 画素の大きさ [m/px]。
        center: 画像の中心の世界座標 [m]。
        diameter_px: 輝点の直径 [px]。
        intensity: 輝点の明るさ。
        background: 一様な下駄。
    Returns:
        (H, W) float64。
    """
    op = "swarm_render_overhead"
    try:
        H, W = int(shape[0]), int(shape[1])
    except (TypeError, ValueError, IndexError):
        raise ValueError("%s: shape must be (H, W), got %r" % (op, shape)) from None
    if H < 8 or W < 8:
        raise ValueError("%s: shape must be at least (8, 8), got %r" % (op, shape))
    rs = _pos(res, "res", op)
    ctr = _center(center, op)
    dpx = _pos(diameter_px, "diameter_px", op)
    amp = _pos(intensity, "intensity", op)
    bg = _num(background, "background", op)
    img = np.zeros((H, W))
    p = np.asarray(points, np.float64)
    if p.size:
        p = _pts(p, "points", op)
        rows, cols = _world_to_pix(p[:, 0], p[:, 1], (H, W), rs, ctr)
        sig = dpx / 2.0
        k = int(math.ceil(3.0 * sig))
        r0, c0 = np.floor(rows).astype(np.int64), np.floor(cols).astype(np.int64)
        off = np.arange(-k, k + 2)
        for orow in off:
            rr = r0 + orow
            wr = np.exp(-((rr - rows) ** 2) / (2 * sig * sig))
            okr = (rr >= 0) & (rr < H)
            for ocol in off:
                cc_ = c0 + ocol
                ok = okr & (cc_ >= 0) & (cc_ < W)
                if np.any(ok):
                    wv = wr[ok] * np.exp(-((cc_[ok] - cols[ok]) ** 2) / (2 * sig * sig))
                    np.add.at(img, (rr[ok], cc_[ok]), amp * wv)
    return img + bg


# ======================================================================================================================
# 4. 速度場を測る(個体の追跡 / PIV)
def _detect(img: np.ndarray, thr_frac: float):
    """blob2d で輝点を切り、明るさの重心(副画素)を返す。大きすぎる塊(個体が重なった)は捨てる。"""
    import blob2d
    t = img.min() + thr_frac * (img.max() - img.min())
    lab = blob2d.blob_label(img > t, connectivity=8)
    n = int(lab.max())
    if n == 0:
        return np.zeros((0, 2)), 0
    L = lab.ravel()
    area = np.bincount(L, minlength=n + 1)[1:].astype(np.float64)   # blob_features の 19 項目は要らない(周長・凸包が重い)
    w = np.maximum(img - t, 0.0).ravel()
    rr, cc = np.indices(img.shape)
    sw = np.bincount(L, w, n + 1)[1:]
    sr = np.bincount(L, w * rr.ravel(), n + 1)[1:]
    sc = np.bincount(L, w * cc.ravel(), n + 1)[1:]
    ok = (sw > 0) & (area <= 2.5 * np.median(area))
    return np.column_stack([sr[ok] / sw[ok], sc[ok] / sw[ok]]), int((~ok).sum())


def _grid_axes(shape, res, center, step):
    H, W = shape
    x0, y_top = _pix_to_world(0, 0, shape, res, center)
    x1, y_bot = _pix_to_world(H - 1, W - 1, shape, res, center)
    xs = np.arange(x0 + step / 2, x1, step)
    ys = np.arange(y_top - step / 2, y_bot, -step)
    return xs, ys


def _shepard(pts: np.ndarray, vals: np.ndarray, xs: np.ndarray, ys: np.ndarray, h: float, min_count: int):
    """点の値を SPH 核の重みの平均(Shepard)で格子へ。台の中の点が min_count 未満の格子は NaN。"""
    from scipy.spatial import cKDTree
    gx, gy = np.meshgrid(xs, ys)
    g = np.column_stack([gx.ravel(), gy.ravel()])
    out = np.full((len(g), vals.shape[1]), np.nan)
    cnt = np.zeros(len(g), np.int64)
    if len(pts):
        sm = cKDTree(g).sparse_distance_matrix(cKDTree(pts), 2.0 * h, output_type="ndarray")
        if len(sm):
            gi, pj, dist = sm["i"], sm["j"], sm["v"]
            w = sph_kernel(dist, h)
            sw = np.bincount(gi, w, len(g))
            cnt = np.bincount(gi, minlength=len(g))
            ok = (cnt >= min_count) & (sw > 0)
            for k in range(vals.shape[1]):
                s = np.bincount(gi, w * vals[pj, k], len(g))
                out[ok, k] = s[ok] / sw[ok]
    return out.reshape(len(ys), len(xs), vals.shape[1]), cnt.reshape(len(ys), len(xs))


def swarm_field_from_tracks(frames, res: float, frame_dt: float, center=(0.0, 0.0), grid_step=None, h=None,
                            threshold: float = 0.3, max_disp_px=None, min_count: int = 3, outlier_k: int = 12,
                            outlier_threshold: float = 3.0) -> dict:
    """俯瞰のコマ列 → 個体を検出(blob2d の連結成分 + 明るさの重心)→ 隣のコマと相互最近傍でつなぐ → 速度を SPH 核で格子へ。

    つなぐ条件: A の点の最近傍が B の点で、その B の点の最近傍も A の点(相互)、かつ移動が ``max_disp_px`` 以下
    (既定 = 検出した点どうしの最近傍の間隔の中央値の 0.45 倍。1 コマの移動がこれを超えると取り違える = 追跡の限界)。
    全部のコマの組の速度を一つの集団にして平均する(定常の流れの前提)。取り違えた組は速度が桁で外れる(実測: 一様に
    撒いた 1300 個で 2 % の組が 1〜3 m/s ずれ、格子の rms 誤差が U の 16 % になった)ので、格子へ移す前に**正規化した
    中央値の検査**(PIV の慣行、近い ``outlier_k`` 個の速度の中央値からのずれ / その近傍のずれの中央値 > ``outlier_threshold``)
    で捨てる。

    Args:
        frames: 同じ大きさの (H, W) のコマの列(2 枚以上)。
        res: 画素の大きさ [m/px]。
        frame_dt: コマの間隔 [s]。
        center: 画像の中心の世界座標 [m]。
        grid_step: 格子の間隔 [m] (既定 = 個体の間隔の推定値)。
        h: 格子へ移す核の h [m] (既定 = grid_step)。
        threshold: 2 値化のしきい値(最小〜最大の割合)。
        max_disp_px: 1 コマの移動の上限 [px]。
        min_count: 格子の台の中に要る速度の数。
        outlier_k: 中央値の検査に使う近傍の数(0 で検査しない)。
        outlier_threshold: 検査のしきい値。
    Returns:
        速度場の dict(module の規約)+ ``points`` (M, 2)・``point_velocity`` (M, 2)(つないだ組の中点と速度)、
        ``n_detected``(コマごと)、``n_linked``、``n_outliers``(中央値の検査で捨てた組)、``n_rejected_blobs``、
        ``spacing``(個体の間隔の推定 [m])。
    """
    op = "swarm_field_from_tracks"
    fr = _frames(frames, op)
    rs, fd = _pos(res, "res", op), _pos(frame_dt, "frame_dt", op)
    ctr = _center(center, op)
    th = _num(threshold, "threshold", op)
    if not 0.0 < th < 1.0:
        raise ValueError("%s: threshold must be in (0, 1), got %r" % (op, threshold))
    from scipy.spatial import cKDTree
    dets, n_rej = [], 0
    for f in fr:
        p, nr = _detect(f, th)
        dets.append(p)
        n_rej += nr
    allnn = []
    for p in dets:
        if len(p) >= 2:
            dd, _ = cKDTree(p).query(p, k=2)
            allnn.append(dd[:, 1])
    if not allnn:
        raise ValueError("%s: fewer than 2 agents detected in every frame" % op)
    sp_px = float(np.median(np.concatenate(allnn)))
    md = 0.45 * sp_px if max_disp_px is None else _pos(max_disp_px, "max_disp_px", op)
    mids, vels = [], []
    for a, b in zip(dets[:-1], dets[1:]):
        if len(a) == 0 or len(b) == 0:
            continue
        da, ia = cKDTree(b).query(a)
        _, ib = cKDTree(a).query(b)
        mutual = (ib[ia] == np.arange(len(a))) & (da <= md)
        pa, pb = a[mutual], b[ia[mutual]]
        xa, ya = _pix_to_world(pa[:, 0], pa[:, 1], fr[0].shape, rs, ctr)
        xb, yb = _pix_to_world(pb[:, 0], pb[:, 1], fr[0].shape, rs, ctr)
        mids.append(np.column_stack([(xa + xb) / 2, (ya + yb) / 2]))
        vels.append(np.column_stack([(xb - xa) / fd, (yb - ya) / fd]))
    mid = np.concatenate(mids) if mids else np.zeros((0, 2))
    vel = np.concatenate(vels) if vels else np.zeros((0, 2))
    n_out = 0
    ko = int(outlier_k)
    if ko > 0 and len(mid) > ko + 1:
        _, nb = cKDTree(mid).query(mid, k=ko + 1)
        nb = nb[:, 1:]
        med = np.median(vel[nb], axis=1)
        res_nb = np.median(np.hypot(*(vel[nb] - med[:, None, :]).transpose(2, 0, 1)), axis=1)
        eps = 0.1 * (rs / fd)                   # 0.1 px/コマ(PIV の慣行の ε)
        r_n = np.hypot(*(vel - med).T) / (res_nb + eps)
        good = r_n <= _pos(outlier_threshold, "outlier_threshold", op)
        n_out = int((~good).sum())
        mid, vel = mid[good], vel[good]
    spacing = sp_px * rs
    gs = spacing if grid_step is None else _pos(grid_step, "grid_step", op)
    hh = gs if h is None else _pos(h, "h", op)
    xs, ys = _grid_axes(fr[0].shape, rs, ctr, gs)
    g, cnt = _shepard(mid, vel, xs, ys, hh, int(min_count))
    u, v = g[..., 0], g[..., 1]
    return {"x": xs, "y": ys, "u": u, "v": v, "valid": np.isfinite(u), "count": cnt, "points": mid, "point_velocity": vel,
            "n_detected": [len(p) for p in dets], "n_linked": int(len(mid)) + n_out, "n_outliers": n_out, "n_rejected_blobs": n_rej, "spacing": spacing}


def swarm_field_from_piv(frames, res: float, frame_dt: float, center=(0.0, 0.0), window: int = 24, overlap: float = 0.5,
                         min_peak_ratio: float = 1.1, outlier_threshold=3.0) -> dict:
    """俯瞰のコマ列 → 隣どうしの相互相関の PIV(pivops.piv_cross_correlate)→ 全部の組の平均 → 世界の速度場。

    個体を一つずつ見分けない(重なっても使える)代わりに、窓(``window`` px)より細かい乱れは均される。峰の比が
    ``min_peak_ratio`` 未満の窓は欠測(NaN)。★群れは格子のように並びやすく(押し合いで間隔がそろう)、相関の峰が
    隣の格子の位置にも立つので峰の比が 1 に近い。実測(間隔 7.5 px、窓 24): しきい値 0 だと取り違えた窓が混ざり個体の
    速度との rms が U の 13.7 %、1.1 で 1.9 %(測れた窓 85 %)、1.3 では測れた窓が 18 % に減る —— 既定は 1.1。
    さらに組ごとに正規化した中央値の検査(pivops.piv_outlier_mask、しきい値 ``outlier_threshold``、None で掛けない)で
    外れた窓を欠測にしてから平均する。pivops の注意どおり、急な勾配(障害物の肩)を外れと呼ばないよう慣行の 2 より緩い 3。pivops の成分 (dy, dx) [px/コマ] を u = dx·res/Δt、v = −dy·res/Δt に直す。

    Returns:
        速度場の dict + ``valid_fraction``(窓のうち測れた割合)、``n_pairs``。
    """
    op = "swarm_field_from_piv"
    fr = _frames(frames, op)
    rs, fd = _pos(res, "res", op), _pos(frame_dt, "frame_dt", op)
    ctr = _center(center, op)
    mpr = _pos(min_peak_ratio, "min_peak_ratio", op, allow_zero=True)
    import warnings

    import pivops
    acc, info = [], None
    for a, b in zip(fr[:-1], fr[1:]):
        flow, info = pivops.piv_cross_correlate(a, b, window=int(window), overlap=float(overlap))
        bad = ~(np.asarray(info["peak_ratio"]) >= mpr)
        flow = flow.copy()
        flow[:, bad] = np.nan
        if outlier_threshold is not None:
            with warnings.catch_warnings():                 # 欠測に囲まれた窓の nanmedian の警告(結果は欠測のまま)
                warnings.simplefilter("ignore", RuntimeWarning)
                out_m = pivops.piv_outlier_mask(flow, threshold=_pos(outlier_threshold, "outlier_threshold", op))
            flow[:, out_m] = np.nan
        acc.append(flow)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        mean = np.nanmean(np.array(acc), axis=0)
    xs, _ = _pix_to_world(np.zeros_like(info["cols"]), info["cols"], fr[0].shape, rs, ctr)
    _, ys = _pix_to_world(info["rows"], np.zeros_like(info["rows"]), fr[0].shape, rs, ctr)
    u = mean[1] * rs / fd
    v = -mean[0] * rs / fd
    valid = np.isfinite(u) & np.isfinite(v)
    return {"x": np.asarray(xs, np.float64), "y": np.asarray(ys, np.float64), "u": u, "v": v, "valid": valid,
            "valid_fraction": float(valid.mean()), "n_pairs": len(acc)}


# ======================================================================================================================
# 5. 閉形式の流れと、欠損・よどみ点・障害物の推定
def potential_flow_cylinder(x, y, cylinder, speed: float = 1.0, grid: bool = False) -> dict:
    """円柱まわりのポテンシャル流(閉形式)。u − i v = U (1 − R²/(z − z_c)²)、円の内側は NaN。

    ``grid=True`` なら ``x``・``y`` を格子の軸(1 次元、行 = y の順)とみなし、速度場の dict(module の規約)を返す。
    既定の ``grid=False`` は要素ごと(同じ形に broadcast)に ``u``・``v``・``inside`` を返す —— 軸か点の列かを形で
    推し量らない(同じ長さの 1 次元の x と y はどちらにも読めて、点の列が黙って格子になる)。どちらにも ``stagnation``(上流の衝突点
    (x_c − R, y_c))と ``rear_stagnation`` と ``surface_speed_max``(= 2U)を付ける。
    """
    op = "potential_flow_cylinder"
    xc, yc, R = _cyl(cylinder, op)
    U = _pos(speed, "speed", op)
    xa, ya = np.asarray(x, np.float64), np.asarray(y, np.float64)
    if not (np.all(np.isfinite(xa)) and np.all(np.isfinite(ya))):
        raise ValueError("%s: x and y must be finite" % op)
    if grid and (xa.ndim != 1 or ya.ndim != 1):
        raise ValueError("%s: grid=True needs 1-D x and y axes, got shapes %r and %r" % (op, xa.shape, ya.shape))
    X, Y = np.meshgrid(xa, ya) if grid else np.broadcast_arrays(xa, ya)
    z = (X - xc) + 1j * (Y - yc)
    inside = np.abs(z) < R
    with np.errstate(divide="ignore", invalid="ignore"):
        w = U * (1.0 - R * R / (z * z))
    u, v = np.real(w), -np.imag(w)
    u = np.where(inside, np.nan, u)
    v = np.where(inside, np.nan, v)
    out = {"u": u, "v": v, "inside": inside, "stagnation": (xc - R, yc), "rear_stagnation": (xc + R, yc),
           "surface_speed_max": 2.0 * U}
    if grid:
        out.update({"x": xa, "y": ya, "valid": ~inside})
    return out


def _free_stream(f: dict, frac: float = 0.15) -> float:
    """上流の端(x の小さい側 frac)の有効な格子の u の中央値。"""
    x = f["x"]
    cut = x.min() + frac * (x.max() - x.min())
    sel = f["valid"] & (x[None, :] <= cut)
    if sel.sum() < 3:
        sel = f["valid"]
    if sel.sum() == 0:
        raise ValueError("free stream: the field has no valid cell")
    return float(np.median(f["u"][sel]))


def velocity_deficit_map(field, speed=None) -> dict:
    """速度場 → 自由流からの欠損 1 − u/U、横の振れ v/U、速さの欠損 1 − |v|/U。U は与えるか、上流の端 15 % の u の中央値。

    Returns:
        dict: ``deficit``・``deflection``・``speed_deficit`` (H, W)(測れない格子は NaN)、``speed``(使った U)、``x``・``y``。
    """
    op = "velocity_deficit_map"
    f = _field(field, op)
    U = _free_stream(f) if speed is None else _pos(speed, "speed", op)
    if not U > 0:
        raise ValueError("%s: estimated free-stream speed %r is not positive (is the flow along +x?)" % (op, U))
    nan = ~f["valid"]
    d = np.where(nan, np.nan, 1.0 - f["u"] / U)
    s = np.where(nan, np.nan, f["v"] / U)
    sd = np.where(nan, np.nan, 1.0 - np.hypot(f["u"], f["v"]) / U)
    return {"deficit": d, "deflection": s, "speed_deficit": sd, "speed": U, "x": f["x"], "y": f["y"]}


def _nanmean3(d: np.ndarray) -> np.ndarray:
    """3 × 3 の近傍の NaN を除いた平均(雑音の 1 格子の跳ねで上流の衝突点を取り違えないため)。"""
    z = np.where(np.isfinite(d), d, 0.0)
    n = np.isfinite(d).astype(np.float64)
    zp, npad = np.pad(z, 1), np.pad(n, 1)
    s = sum(zp[i:i + d.shape[0], j:j + d.shape[1]] for i in range(3) for j in range(3))
    c = sum(npad[i:i + d.shape[0], j:j + d.shape[1]] for i in range(3) for j in range(3))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(c > 0, s / c, np.nan)


def stagnation_from_centerline(field, speed=None, d_range=(0.04, 0.6), min_points: int = 4, n_iter: int = 80) -> dict:
    """中心線の欠損を直線化して、上流の衝突点(よどみ点)・障害物の中心・半径を読む(実装 1、上流の点だけ)。

    1. 欠損(3 × 3 の平均)が ``d_range`` の上限を超える格子のうち、最も上流のものを「衝突点のそば」とする。
    2. その少し上流の列(4 列)で、欠損が最大の行を放物線で副格子に求め、平均を中心線 y_c とする
       (上流の欠損 R²(Δx² − Δy²)/(Δx² + Δy²)² は Δy = 0 で最大)。
    3. y_c の高さで欠損を行の間の 1 次補間で取り、衝突点のそばより上流で ``d_range`` の中にある格子で
       1/√d = (x_c − x)/R を重みつき最小二乗で引く(速さの雑音 σ_d は 1/√d では σ_d/(2d^{3/2}) に増えるので、
       重み d^{3/2} —— 欠損の小さい遠くの点は雑音で暴れる): R = −1/傾き、x_c = 切片 × R。よどみ点 = (x_c − R, y_c)。
    4. ``speed`` を与えないときは、上流の端の u を閉形式で割り戻して U を推定し直し、3 を繰り返す(U の変化が 1e-9 未満になるか ``n_iter`` 回まで。収束は 1 次で、R = 0.6・端までの距離 3 の場で約 30 回)。
       上流の端も 1/r² で欠けているので(R = 0.6、距離 3 で 4 %)、端の中央値をそのまま U にすると直線が曲がる。

    Returns:
        dict: ``stagnation`` (x, y)、``center`` (x, y)、``radius``、``n_used``、``rms_residual``(1/√d の当てはめの残差)、
        ``speed``、``ok``(点が足りて傾きが負なら True)。
    """
    op = "stagnation_from_centerline"
    f = _field(field, op)
    lo, hi = float(d_range[0]), float(d_range[1])
    if not 0.0 < lo < hi < 1.0:
        raise ValueError("%s: d_range must satisfy 0 < lo < hi < 1, got %r" % (op, d_range))
    fix_u = speed is not None
    U = _pos(speed, "speed", op) if fix_u else _free_stream(f)
    x, y = f["x"], f["y"]
    out = {"stagnation": (math.nan, math.nan), "center": (math.nan, math.nan), "radius": math.nan, "n_used": 0,
           "rms_residual": math.nan, "speed": U, "ok": False}
    for it in range(max(1, int(n_iter))):
        d = np.where(f["valid"], 1.0 - f["u"] / U, np.nan)
        ds = _nanmean3(d)
        strong = np.isfinite(d) & (d > hi) & (ds > hi)
        if not strong.any():
            return out
        cols = np.where(strong.any(axis=0))[0]
        js = int(cols[0])
        i_s = int(np.argmax(np.where(strong[:, js], ds[:, js], -np.inf)))
        ycs = []
        for j in range(max(0, js - 4), js):
            col = np.where(np.isfinite(ds[:, j]), ds[:, j], -np.inf)
            i0 = int(np.argmax(col[max(0, i_s - 6): i_s + 7])) + max(0, i_s - 6)
            yv = float(y[i0])
            if 0 < i0 < len(y) - 1 and np.all(np.isfinite(col[i0 - 1:i0 + 2])):
                a_, b_, c_ = col[i0 - 1], col[i0], col[i0 + 1]
                den = a_ - 2 * b_ + c_
                if den < 0:
                    yv = float(y[i0] + 0.5 * (a_ - c_) / den * (y[1] - y[0]))
            ycs.append(yv)
        yc = float(np.mean(ycs)) if ycs else float(y[i_s])
        fi = (yc - y[0]) / (y[1] - y[0])
        i0 = int(np.clip(math.floor(fi), 0, len(y) - 2))
        tfr = fi - i0
        row = (1 - tfr) * d[i0] + tfr * d[i0 + 1]
        sel = (np.arange(len(x)) < js) & np.isfinite(row) & (row > lo) & (row < hi)
        out["n_used"] = int(sel.sum())
        if sel.sum() < int(min_points):
            return out
        xs, zs = x[sel], 1.0 / np.sqrt(row[sel])
        A = np.column_stack([xs, np.ones_like(xs)])
        sw = row[sel] ** 1.5                     # σ(1/√d) = σ_d / (2 d^{3/2}) → 重み 1/σ ∝ d^{3/2}
        (k, b0), *_ = np.linalg.lstsq(A * sw[:, None], zs * sw, rcond=None)
        if not k < 0:
            return out
        R = -1.0 / k
        xc = b0 * R
        out.update({"stagnation": (xc - R, yc), "center": (xc, yc), "radius": float(R),
                    "rms_residual": float(np.sqrt(np.mean((A @ np.array([k, b0]) - zs) ** 2))), "ok": True, "speed": U})
        if fix_u:
            break
        # 上流の端の u を閉形式の 1 − R²/(z − z_c)² で割り戻して U を推定し直す
        cut = x.min() + 0.15 * (x.max() - x.min())
        X, Y = np.meshgrid(x, y)
        m_ = f["valid"] & (X <= cut)
        if m_.sum() < 3:
            break
        z = (X[m_] - xc) + 1j * (Y[m_] - yc)
        U_new = float(np.median(f["u"][m_] / np.real(1.0 - R * R / (z * z))))
        if not (math.isfinite(U_new) and U_new > 0):
            break
        done = abs(U_new - U) < 1e-9 * U
        U = U_new
        out["n_iter"] = it + 1
        if done:
            break
    return out


def obstacle_fit_doublet(field, speed=None, upstream_only: bool = False, exclude_margin: float = 1.25,
                         min_explained: float = 0.5, min_radius=None) -> dict:
    """速度場に円柱まわりのポテンシャル流 u − i v = U (1 − R²/(z − z_c)²) を当てはめる(実装 2、2 次元の非線形最小二乗)。

    未知数は (x_c, y_c, R², U)。出発点は 2 つ: :func:`stagnation_from_centerline` と、格子の節点を中心の候補にした
    粗い探索(U を固定すると模型は R² について 1 次なので閉形式で解ける)。説明できる割合の大きい方を採る。円の
    ``exclude_margin`` 倍より内側の格子は使わない(格子へ移す核が壁をまたいで速さを均すため)—— 推定し直して 3 回回す。
    ``upstream_only`` なら衝突点より上流(x < x_c − R)の格子だけで当てはめる(「当たる前に」分かるか)。

    判定: 一様流だけの模型(u, v が定数)の残差 RSS₀ に対して、円柱の模型で減った割合 1 − RSS₁/RSS₀(**乱れのうち
    円柱で説明できる割合**)が ``min_explained`` 以上、半径が ``min_radius``(既定 = 格子の間隔 2 つ)以上、中心が場の中
    —— の 3 つで ``detected``。否定の判定(障害物なし)はこの割合が小さいことで出る。
    ★半径の下限は解像の限界: :func:`swarm_field_from_tracks` の格子は個体の間隔 s ごとなので、既定では R < 2s の障害物を
    「ある」と言わない。拒否が正当なことは実測で確かめた(一様に撒いた粒子、R = 0.6 m: R/s ≈ 5 で中心・半径とも 2 % 以内、
    R/s ≈ 2.5 で 5 % 以内、R/s ≈ 1.2 で半径が 48 % 小さく出る)。

    Returns:
        dict: ``center``・``radius``・``speed``・``stagnation``・``explained``・``detected``・``n_used``・``rms_residual``
        (m/s)・``rms_null``(m/s)。
    """
    op = "obstacle_fit_doublet"
    f = _field(field, op)
    em = _pos(exclude_margin, "exclude_margin", op)
    me = _num(min_explained, "min_explained", op)
    from scipy.optimize import least_squares
    x, y = f["x"], f["y"]
    X, Y = np.meshgrid(x, y)
    step = float(min(abs(x[1] - x[0]), abs(y[1] - y[0])))
    rmin = 2.0 * step if min_radius is None else _pos(min_radius, "min_radius", op)
    U0 = _free_stream(f) if speed is None else _pos(speed, "speed", op)
    fix_u = speed is not None
    vX, vY, vu, vv = X[f["valid"]], Y[f["valid"]], f["u"][f["valid"]], f["v"][f["valid"]]
    if len(vX) < 10:
        raise ValueError("%s: need at least 10 valid cells, got %d" % (op, len(vX)))
    starts = []
    st = stagnation_from_centerline(f, U0)
    if st["ok"] and np.isfinite(st["radius"]):
        starts.append((st["center"][0], st["center"][1], st["radius"]))
    # 粗い探索(大域): 格子の全節点を中心の候補にし、U を固定すると模型は A = R² について 1 次なので A を閉形式で解き、
    # 残差の平均が最小の候補を出発点にする(1 つの出発点だと局所解に落ちる —— 個体 300 で中心が 1.2R ずれた実測)
    e_all = ((vu - U0) - 1j * vv) / (-U0)            # = A / (z − z_c)²
    cx = x[::2] if x.size > 40 else x
    cy = y[::2] if y.size > 40 else y
    best = (np.inf, None)
    for yc_ in cy:
        for xc_ in cx:
            z = (vX - xc_) + 1j * (vY - yc_)
            ok = np.abs(z) > 3.0 * step
            if upstream_only:
                ok &= vX < xc_
            if ok.sum() < 8:
                continue
            g = 1.0 / (z[ok] * z[ok])
            A = max(float(np.real(np.sum(np.conj(g) * e_all[ok])) / np.sum(np.abs(g) ** 2)), 0.0)
            cost = float(np.mean(np.abs(e_all[ok] - A * g) ** 2))
            if cost < best[0]:
                best = (cost, (float(xc_), float(yc_), math.sqrt(A) if A > 0 else step))
    if best[1] is not None:
        starts.append(best[1])
    if not starts:
        dm = velocity_deficit_map(f, U0)["deficit"]
        k = int(np.nanargmax(np.where(np.isfinite(dm), dm, -np.inf)))
        starts.append((float(X.ravel()[k]) + 2 * step, float(Y.ravel()[k]), 2 * step))

    def model(prm, xx, yy):
        xc, yc, a2 = prm[0], prm[1], prm[2]
        U = U0 if fix_u else prm[3]
        z = (xx - xc) + 1j * (yy - yc)
        w = U * (1.0 - a2 / (z * z))
        return np.real(w), -np.imag(w)

    lo = [x.min() - 0.5 * (x.max() - x.min()), y.min() - 0.5 * abs(y.max() - y.min()), 0.0] + ([] if fix_u else [1e-9])
    hi = [x.max() + 0.5 * (x.max() - x.min()), y.max() + 0.5 * abs(y.max() - y.min()),
          (x.max() - x.min()) ** 2] + ([] if fix_u else [np.inf])

    def refine(start):
        r0 = float(np.clip(start[2], step, 0.5 * (x.max() - x.min())))
        prm = np.array([start[0], start[1], r0 * r0] + ([] if fix_u else [U0]))
        used = np.zeros(len(vX), bool)
        for _ in range(3):
            rc = math.sqrt(max(prm[2], 0.0))
            used = np.hypot(vX - prm[0], vY - prm[1]) > em * rc
            if upstream_only:
                used &= vX < prm[0] - rc
            if used.sum() < 8:
                return None
            xx, yy, uu, vvv = vX[used], vY[used], vu[used], vv[used]

            def resid(p, xx=xx, yy=yy, uu=uu, vvv=vvv):
                mu, mv = model(p, xx, yy)
                return np.concatenate([mu - uu, mv - vvv])

            p0 = np.clip(prm, np.array(lo) + 1e-12, np.array(hi) - 1e-12)
            prm = least_squares(resid, p0, bounds=(lo, hi), x_scale="jac", max_nfev=200).x
        xx, yy, uu, vvv = vX[used], vY[used], vu[used], vv[used]
        mu, mv = model(prm, xx, yy)
        rss1 = float(np.sum((mu - uu) ** 2 + (mv - vvv) ** 2))
        rss0 = float(np.sum((uu - uu.mean()) ** 2 + (vvv - vvv.mean()) ** 2))
        expl = 1.0 - rss1 / rss0 if rss0 > 0 else 0.0
        return expl, prm, used, rss1, rss0

    results = [r_ for r_ in (refine(s_) for s_ in starts) if r_ is not None]
    if not results:
        return {"center": (math.nan, math.nan), "radius": math.nan, "speed": U0, "stagnation": (math.nan, math.nan),
                "explained": 0.0, "detected": False, "n_used": 0, "rms_residual": math.nan, "rms_null": math.nan,
                "min_radius": rmin, "n_starts": len(starts)}
    expl, prm, used, rss1, rss0 = max(results, key=lambda r_: r_[0])
    R = math.sqrt(max(prm[2], 0.0))
    U = U0 if fix_u else float(prm[3])
    inside = (x.min() <= prm[0] <= x.max()) and (min(y) <= prm[1] <= max(y))
    det = bool(expl >= me and R >= rmin and inside)
    n = max(int(used.sum()), 1)
    return {"center": (float(prm[0]), float(prm[1])), "radius": R, "speed": U, "stagnation": (float(prm[0]) - R, float(prm[1])),
            "explained": float(expl), "detected": det, "n_used": int(used.sum()), "rms_residual": math.sqrt(rss1 / (2 * n)),
            "rms_null": math.sqrt(rss0 / (2 * n)), "min_radius": rmin, "n_starts": len(starts)}


# ======================================================================================================================
# 6. ゲートを開けた群れの広がり(ダム崩壊)
def ritter_dam_break(x, t: float, h0: float, g: float = 9.81, particle_mass=None) -> dict:
    """Ritter のダム崩壊解(浅水方程式、乾いた床、ダムは x = 0、水は x < 0)。

    c₀ = √(g h₀)。x ≤ −c₀ t: h = h₀、u = 0 / −c₀ t < x < 2c₀ t: h = (2c₀ − x/t)²/(9g)、u = (2/3)(x/t + c₀) / x ≥ 2c₀ t: h = 0。

    先端の近くは h ∝ (x_f − x)² で水がほとんど無い。先端から δ までの水の量は ∫₀^δ (s/t)²/(9g) ds = δ³/(27 g t²)(導出)。
    粒子 1 個の量 m(1 次元の SPH なら h₀Δx)を与えると、**最も前の粒子の居場所**(先端から量 m/2 の所)
    x_f − (27 g t² m/2)^{1/3} を ``lead_particle`` に返す —— 粒子法の先端は Ritter の先端より必ず遅れて見え、その遅れは
    この式で読める(粒子を細かくすると m^{1/3} でしか縮まない)。

    Returns:
        dict: ``h``・``u``(x と同じ形)、``front`` = 2c₀ t、``rarefaction_head`` = −c₀ t、``c0``、``lead_particle``(m を与えたとき)。
    """
    op = "ritter_dam_break"
    tt, hh, gg = _pos(t, "t", op), _pos(h0, "h0", op), _pos(g, "g", op)
    xa = np.asarray(x, np.float64)
    if not np.all(np.isfinite(xa)):
        raise ValueError("%s: x must be finite" % op)
    c0 = math.sqrt(gg * hh)
    s = xa / tt
    h = np.where(s <= -c0, hh, np.where(s >= 2 * c0, 0.0, (2 * c0 - s) ** 2 / (9 * gg)))
    u = np.where((s > -c0) & (s < 2 * c0), (2.0 / 3.0) * (s + c0), 0.0)
    out = {"h": h, "u": u, "front": 2 * c0 * tt, "rarefaction_head": -c0 * tt, "c0": c0}
    if particle_mass is not None:
        mm = _pos(particle_mass, "particle_mass", op)
        out["lead_particle"] = 2 * c0 * tt - (27.0 * gg * tt * tt * mm / 2.0) ** (1.0 / 3.0)
    return out


def sph_dam_break_1d(h0: float = 0.1, length: float = 1.0, n_particles: int = 400, t_end: float = 0.2, g: float = 9.81,
                     kappa: float = 1.3, alpha: float = 0.3, n_out: int = 5) -> dict:
    """1 次元 SPH の浅水方程式でダム崩壊(乾いた床)を解く(群れのゲートを開けたときの広がりの模型)。

    水深 h_i = Σ_j m_j W(x_i − x_j, ℓ_ij)(1 次元の核、m = h₀ Δx)、加速度 du_i/dt = −g Σ_j m_j ∂W_ij/∂x_i(= −g ∂h/∂x、
    運動量を保存する対称形)+ Monaghan の人工粘性。平滑化の長さは粒子ごとに ℓ_i = κ m/h_i(先端の薄い所で広がる)、
    組には平均 ℓ_ij。左の壁(x = −length)は鏡像の粒子。真値は :func:`ritter_dam_break`(門で照らす)。

    Returns:
        dict: ``t`` (K,)、``x`` (K, N)、``h`` (K, N)、``u`` (K, N)(各時刻の粒子)、``front`` (K,)(最も前の粒子)、
        ``mass``(全質量、保存)、``c0``。
    """
    op = "sph_dam_break_1d"
    H0, Lw, te, gg = _pos(h0, "h0", op), _pos(length, "length", op), _pos(t_end, "t_end", op), _pos(g, "g", op)
    kp, al = _pos(kappa, "kappa", op), _pos(alpha, "alpha", op, allow_zero=True)
    N = int(n_particles)
    if N < 20:
        raise ValueError("%s: n_particles must be >= 20, got %r" % (op, n_particles))
    c0 = math.sqrt(gg * H0)
    if te * c0 > 0.9 * Lw:
        raise ValueError("%s: t_end = %g lets the rarefaction reach the wall (t_end must be < 0.9 length/c0 = %g)"
                         % (op, te, 0.9 * Lw / c0))
    dx = Lw / N
    x = -Lw + (np.arange(N) + 0.5) * dx
    u = np.zeros(N)
    m = H0 * dx
    ell = np.full(N, kp * dx)
    lmax = 40.0 * kp * dx
    t_out = np.linspace(0.0, te, int(n_out) + 1)[1:]
    rec = {"t": [], "x": [], "h": [], "u": []}

    from scipy.spatial import cKDTree

    def state(xp, up, el):
        """鏡像の粒子(左の壁)を足し、水深 h と ℓ = κ m/h を 2 回反復でそろえる。組と差分も返す。"""
        nm = min(int(np.searchsorted(xp, -Lw + 2 * lmax)) + 1, len(xp))   # 粒子が少ないと鏡像の幅が全体を超える(chain_fuzz で踏んだ)
        xg = np.concatenate([-2 * Lw - xp[:nm][::-1], xp])
        ug = np.concatenate([-up[:nm][::-1], up])
        ij = cKDTree(xg[:, None]).query_pairs(2 * lmax, output_type="ndarray")
        dxx = xg[ij[:, 0]] - xg[ij[:, 1]]
        ng = len(xg)
        for _ in range(2):
            eg = np.concatenate([el[:nm][::-1], el])
            lij = 0.5 * (eg[ij[:, 0]] + eg[ij[:, 1]])
            w = m * sph_kernel(np.abs(dxx) / lij, 1.0, dim=1) / lij
            hg = m * sph_kernel(0.0, 1.0, dim=1)[()] / eg + np.bincount(ij[:, 0], w, ng) + np.bincount(ij[:, 1], w, ng)
            el = np.minimum(kp * m / hg[nm:], lmax)
        return nm, xg, ug, ij, dxx, lij, hg, el

    t = 0.0
    k_out = 0
    while k_out < len(t_out):
        nm, xg, ug, ij, dxx, lij, hg, ell = state(x, u, ell)
        h = hg[nm:]
        ng = len(xg)
        dwr = sph_kernel(np.abs(dxx) / lij, 1.0, dim=1, derivative=True) / (lij * lij)
        grad = m * dwr * np.sign(dxx)              # m ∂W_ij/∂x_i
        cg = np.sqrt(gg * hg)
        vr = (ug[ij[:, 0]] - ug[ij[:, 1]]) * dxx
        mu = lij * vr / (dxx * dxx + 0.01 * lij * lij)
        hbar = 0.5 * (hg[ij[:, 0]] + hg[ij[:, 1]])
        cbar = 0.5 * (cg[ij[:, 0]] + cg[ij[:, 1]])
        pi_ij = np.where(vr < 0.0, -al * cbar * mu / hbar, 0.0)
        fi = (gg + pi_ij) * grad
        acc = -(np.bincount(ij[:, 0], fi, ng) - np.bincount(ij[:, 1], fi, ng))[nm:]
        dt = 0.2 * float(np.min(ell / (np.sqrt(gg * h) + np.abs(u) + 1e-12)))
        hit = t + dt >= t_out[k_out]
        if hit:
            dt = t_out[k_out] - t
        u = u + acc * dt
        x = x + u * dt
        order = np.argsort(x, kind="stable")
        x, u, ell = x[order], u[order], ell[order]
        t += dt
        if hit:
            nm, _, _, _, _, _, hg, ell = state(x, u, ell)
            rec["t"].append(t)
            rec["x"].append(x.copy())
            rec["u"].append(u.copy())
            rec["h"].append(hg[nm:].copy())
            k_out += 1
    xs = np.array(rec["x"])
    return {"t": np.array(rec["t"]), "x": xs, "h": np.array(rec["h"]), "u": np.array(rec["u"]), "front": xs.max(axis=1),
            "mass": m * N, "c0": c0}
