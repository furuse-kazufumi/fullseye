"""balltrack — 映像から球を測る op 族(卓球・けん玉の PoC 系列、17 巡目): 検出(サブピクセル重心)・追跡(等速予測の対応づけ)・
Kalman(等加速度)・多カメラ三角測量(DLT)・跳ねの検出・模様からのスピン。

先駆者(ロボット卓球の視覚: 多カメラ高速追跡 → 三角測量 → 抗力 + マグヌスの軌道予測 → スピン推定)と同じ計測を numpy だけで組み、
:mod:`ballistics` と :mod:`ballworld` の真値で採点する。門 = 真値の投影を検出すると誤差 < 0.2 px、真の対応で三角測量すると 1e-9 m、
放物線の真値を Kalman(等加速度)に通すと収束後の残差 → 0、既知の回転で回した模様の向きから ω が 1e-9 で戻る。

規約: 画素は (col, row)、画素中心は整数座標(render3d / driveworld と同じ)。カメラは render3d の規約(world → camera 4×4、
カメラは −Z を向く、深度 = −Z_c、col = fx·X/depth + cx、row = cy − fy·Y/depth)。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "ball_detect", "ball_track", "kalman_ca", "triangulate_dlt", "track_triangulate", "bounce_detect",
    "marker_direction", "spin_from_markers", "reproject",
]


def _img(image) -> np.ndarray:
    a = np.asarray(image, np.float64)
    if a.ndim == 3:
        a = a.mean(axis=2)
    if a.ndim != 2 or a.size == 0 or not np.all(np.isfinite(a)):
        raise ValueError("image must be a finite (H, W) or (H, W, 3) array")
    return a


# ─────────────────────────────── 検出 ───────────────────────────────

def ball_detect(image, *, mode: str = "bright", thresh=None, color=None, color_tol: float = 0.25,
                radius_range=(1.5, 80.0), max_candidates: int = 8) -> list:
    """画像から球の候補を出す: しきい値 → 連結成分 → 明るさ重みのサブピクセル重心・等価半径・充填率。

    ``mode`` = "bright"(明るい塊、``thresh`` 既定 = 平均 + 2σ)/ "dark"(暗い塊)/ "color"(``color`` (3,) との RGB 距離 < color_tol)/
    "chroma"(明るさで正規化した色の距離 < color_tol: 陰影に強い)。
    返り値 = ``[{"col", "row", "radius", "area", "fill", "score"}, …]``(score 降順、fill = 面積 / 外接円の面積で球らしさ)。
    半径が ``radius_range`` の外の塊は捨てる。"""
    from scipy import ndimage
    img = np.asarray(image, np.float64)
    if mode in ("color", "chroma"):
        if img.ndim != 3 or color is None:
            raise ValueError("mode='color'/'chroma' needs an (H, W, 3) image and color")
        c = np.asarray(color, np.float64).reshape(3)
        if mode == "chroma":                                     # 明るさ(陰影)を除いた色: c/|c| の距離
            nrm = np.linalg.norm(img, axis=2, keepdims=True)
            dist = np.sqrt(np.sum((img / np.maximum(nrm, 1e-9) - c / np.linalg.norm(c)) ** 2, axis=2))
            dist[nrm[..., 0] < 0.05] = np.inf
        else:
            dist = np.sqrt(np.sum((img - c) ** 2, axis=2))
        mask = dist < color_tol
        weight = np.clip(1.0 - dist / color_tol, 0.0, 1.0)
    else:
        g = _img(img)
        if thresh is None:
            thresh = g.mean() + 2.0 * g.std()
        if mode == "bright":
            mask = g > thresh
            weight = np.clip(g - thresh, 0.0, None)
        elif mode == "dark":
            mask = g < thresh
            weight = np.clip(thresh - g, 0.0, None)
        else:
            raise ValueError("mode must be 'bright', 'dark', 'color' or 'chroma'")
    lab, n = ndimage.label(mask)
    out = []
    if n == 0:
        return out
    rr, cc = np.mgrid[0:mask.shape[0], 0:mask.shape[1]].astype(np.float64)
    rmin, rmax = radius_range
    for k in range(1, n + 1):
        m = lab == k
        area = int(m.sum())
        r_eq = np.sqrt(area / np.pi)
        if not (rmin <= r_eq <= rmax):
            continue
        w = weight[m]
        if w.sum() <= 0:
            w = np.ones(area)
        col = float(np.sum(w * cc[m]) / w.sum())
        row = float(np.sum(w * rr[m]) / w.sum())
        rad = np.hypot(cc[m] - col, rr[m] - row).max() + 0.5
        fill = float(area / (np.pi * rad * rad))
        out.append({"col": col, "row": row, "radius": float(r_eq), "area": area, "fill": fill,
                    "score": float(fill * np.sqrt(area))})
    out.sort(key=lambda d: -d["score"])
    return out[:max_candidates]


# ─────────────────────────────── 追跡 ───────────────────────────────

def ball_track(detections, *, max_jump: float = 40.0, min_score: float = 0.0) -> dict:
    """コマごとの候補列 ``detections[k] = ball_detect(frame_k)`` を 1 本の軌跡に繋ぐ(等速予測に最も近い候補、``max_jump`` px 以内)。

    返り値 ``{"frame" (N,), "col" (N,), "row" (N,), "radius" (N,), "found" (K,) bool}``(見つからないコマは飛ばす)。"""
    if not isinstance(detections, (list, tuple)):
        raise ValueError("detections must be a list of per-frame candidate lists")
    fr, cs, rs, rad = [], [], [], []
    found = np.zeros(len(detections), bool)
    pred = None
    for k, cands in enumerate(detections):
        cands = [c for c in cands if c.get("score", 1.0) >= min_score]
        if not cands:
            continue
        if pred is None:
            best = cands[0]
        else:
            d = [np.hypot(c["col"] - pred[0], c["row"] - pred[1]) for c in cands]
            j = int(np.argmin(d))
            if d[j] > max_jump:
                continue
            best = cands[j]
        fr.append(k)
        cs.append(best["col"])
        rs.append(best["row"])
        rad.append(best["radius"])
        found[k] = True
        if len(fr) >= 2 and fr[-1] - fr[-2] > 0:
            dk = fr[-1] - fr[-2]
            pred = (cs[-1] + (cs[-1] - cs[-2]) / dk, rs[-1] + (rs[-1] - rs[-2]) / dk)
        else:
            pred = (cs[-1], rs[-1])
    return {"frame": np.asarray(fr, np.int64), "col": np.asarray(cs), "row": np.asarray(rs), "radius": np.asarray(rad),
            "found": found}


def kalman_ca(z, dt: float, *, q: float = 1.0, r: float = 1.0, x0=None, P0: float = 1e3) -> dict:
    """等加速度モデルの Kalman フィルタ(位置の観測 (N, D)、状態 = 位置・速度・加速度 × D)。

    返り値 ``{"x" (N, 3D) 更新後, "x_pred" (N, 3D) 予測, "P" (N, 3D, 3D), "innovation" (N, D)}``。
    ``q`` = 加速度の変化の分散(白色ジャーク)、``r`` = 観測の分散。放物線の真値を入れると(モデルが厳密なので)収束後の
    新息 → 0、r → 0 で更新後の位置 = 観測(門)。NaN の観測は予測だけ(欠測)。"""
    Z = np.asarray(z, np.float64)
    if Z.ndim != 2 or Z.shape[0] < 1 or dt <= 0 or q < 0 or r < 0:
        raise ValueError("z must be (N, D), dt > 0, q ≥ 0, r ≥ 0")
    N, D = Z.shape
    F1 = np.array([[1.0, dt, 0.5 * dt * dt], [0.0, 1.0, dt], [0.0, 0.0, 1.0]])
    G1 = np.array([dt ** 3 / 6.0, dt * dt / 2.0, dt])
    Q1 = q * np.outer(G1, G1)
    F = np.kron(np.eye(D), F1)
    Q = np.kron(np.eye(D), Q1)
    H = np.kron(np.eye(D), np.array([[1.0, 0.0, 0.0]]))
    R = r * np.eye(D)
    n = 3 * D
    if x0 is None:
        x = np.zeros(n)
        first = Z[0] if np.all(np.isfinite(Z[0])) else np.zeros(D)
        x[0::3] = first
    else:
        x = np.asarray(x0, np.float64).reshape(n)
    P = P0 * np.eye(n)
    X = np.empty((N, n))
    Xp = np.empty((N, n))
    Ps = np.empty((N, n, n))
    inn = np.full((N, D), np.nan)
    for k in range(N):
        if k > 0:
            x = F @ x
            P = F @ P @ F.T + Q
        Xp[k] = x
        zk = Z[k]
        if np.all(np.isfinite(zk)):
            y = zk - H @ x
            S = H @ P @ H.T + R
            K = P @ H.T @ np.linalg.inv(S) if r > 0 else P @ H.T @ np.linalg.pinv(S)
            x = x + K @ y
            P = (np.eye(n) - K @ H) @ P
            inn[k] = y
        X[k] = x
        Ps[k] = P
    return {"x": X, "x_pred": Xp, "P": Ps, "innovation": inn}


# ─────────────────────────────── 三角測量 ───────────────────────────────

def _projection_matrix(pose, K) -> np.ndarray:
    """render3d 規約(カメラは −Z を向く、row は下向き)の 3×4 射影行列: (col·d, row·d, d) = M [X Y Z 1]、d = 深度。"""
    T = np.asarray(pose, np.float64)
    K = np.asarray(K, np.float64)
    if T.shape != (4, 4) or K.shape != (3, 3):
        raise ValueError("pose must be 4×4, K 3×3")
    flip = np.diag([1.0, -1.0, -1.0])            # X 右, Y 上 → (x, −y, depth = −Z)
    Kc = np.array([[K[0, 0], 0.0, K[0, 2]], [0.0, K[1, 1], K[1, 2]], [0.0, 0.0, 1.0]])
    return Kc @ flip @ T[:3, :]


def reproject(points, pose, K) -> np.ndarray:
    """世界点 (N, 3) → (N, 2) の (col, row)(深度 ≤ 0 は NaN)。"""
    P = np.asarray(points, np.float64).reshape(-1, 3)
    M = _projection_matrix(pose, K)
    h = np.column_stack([P, np.ones(len(P))]) @ M.T
    d = h[:, 2]
    with np.errstate(divide="ignore", invalid="ignore"):
        uv = h[:, :2] / d[:, None]
    uv[d <= 0] = np.nan
    return uv


def triangulate_dlt(uvs, poses, Ks) -> dict:
    """1 点の多視点三角測量(線形 DLT、SVD): ``uvs`` (C, 2)、``poses`` (C, 4, 4)、``Ks`` (C, 3, 3)。
    返り値 ``{"p" (3,), "reproj_rms" px, "n_views"}``。NaN の視点は飛ばす。2 視点未満なら ValueError。"""
    U = np.asarray(uvs, np.float64).reshape(-1, 2)
    rows = []
    Ms = []
    for uv, pose, K in zip(U, poses, Ks):
        if not np.all(np.isfinite(uv)):
            continue
        M = _projection_matrix(pose, K)
        Ms.append((uv, M))
        rows.append(uv[0] * M[2] - M[0])
        rows.append(uv[1] * M[2] - M[1])
    if len(Ms) < 2:
        raise ValueError("need at least 2 finite views")
    A = np.asarray(rows)
    _, _, Vt = np.linalg.svd(A)
    X = Vt[-1]
    if abs(X[3]) < 1e-15:
        raise ValueError("triangulation degenerate (point at infinity)")
    p = X[:3] / X[3]
    err = []
    for uv, M in Ms:
        h = M @ np.r_[p, 1.0]
        err.append(np.hypot(*(h[:2] / h[2] - uv)))
    return {"p": p, "reproj_rms": float(np.sqrt(np.mean(np.square(err)))), "n_views": len(Ms)}


def track_triangulate(tracks, poses, Ks, n_frames: int) -> dict:
    """カメラごとの軌跡(:func:`ball_track` の返り値)を三角測量して 3-D の軌跡に: ``{"frame", "p" (N, 3), "reproj_rms" (N,)}``
    (2 視点以上で見えたコマだけ)。"""
    C = len(tracks)
    uv = np.full((n_frames, C, 2), np.nan)
    for c, tr in enumerate(tracks):
        uv[tr["frame"], c, 0] = tr["col"]
        uv[tr["frame"], c, 1] = tr["row"]
    fr, P, E = [], [], []
    for k in range(n_frames):
        if np.count_nonzero(np.all(np.isfinite(uv[k]), axis=1)) < 2:
            continue
        t = triangulate_dlt(uv[k], poses, Ks)
        fr.append(k)
        P.append(t["p"])
        E.append(t["reproj_rms"])
    return {"frame": np.asarray(fr, np.int64), "p": np.asarray(P).reshape(-1, 3), "reproj_rms": np.asarray(E)}


# ─────────────────────────────── 跳ねの検出 ───────────────────────────────

def bounce_detect(t, z, *, min_gap: int = 2) -> dict:
    """高さの列 z(t) から接触の候補を出す: 下向きの速度が上向きに変わる局所最小(前後 ``min_gap`` 標本で最小)。
    返り値 ``{"index" (M,), "t" (M,), "z" (M,)}``。"""
    t = np.asarray(t, np.float64).reshape(-1)
    z = np.asarray(z, np.float64).reshape(-1)
    if t.size != z.size or t.size < 3:
        raise ValueError("need ≥ 3 samples with matching t")
    idx = []
    for i in range(1, z.size - 1):
        lo, hi = max(0, i - min_gap), min(z.size, i + min_gap + 1)
        if z[i] <= z[lo:hi].min() and z[i - 1] > z[i] and z[i + 1] > z[i]:
            idx.append(i)
    idx = np.asarray(idx, np.int64)
    return {"index": idx, "t": t[idx], "z": z[idx]}


# ─────────────────────────────── 模様からのスピン ───────────────────────────────

def marker_direction(marker_uv, center_uv, radius_px, K=None) -> np.ndarray:
    """像の中の模様の位置 (col, row) → 球面上の向き(カメラ系の単位ベクトル、前半球: x 右、y 上、z 手前)。

    ``K`` (3, 3) を渡すと**透視で厳密に**解く: 球の角半径 α = atan(半径 px / f) から中心までの距離(半径 1 として 1/sin α)と
    中心の視線を出し、模様の画素の視線を球面と交差させ、交点の法線を返す。★K が無い形は円板を正射影とみなし、中心を通る
    視線を z とする系で答える —— 球が光軸から外れていると系ごと回り、球が動く映像では視線の変化がそのまま見かけの回転になる
    (0.6 m 先を 6 m/s で横切る球は 1 ms で視線が 0.01 rad 回り、1 コマの回転 0.15 rad に 7 % 上乗せされた。2026-09-30、
    PoC ㉔ の近接カメラ)。K が無ければ従来どおり。"""
    m = np.asarray(marker_uv, np.float64).reshape(2)
    c = np.asarray(center_uv, np.float64).reshape(2)
    if radius_px <= 0:
        raise ValueError("radius_px must be positive")
    x = (m[0] - c[0]) / radius_px
    y = -(m[1] - c[1]) / radius_px
    rr = x * x + y * y
    if rr > 1.0 + 1e-9:
        raise ValueError("marker lies outside the ball's disc")
    if K is None:
        return np.array([x, y, np.sqrt(max(0.0, 1.0 - rr))])
    Km = np.asarray(K, np.float64).reshape(3, 3)
    f = 0.5 * (Km[0, 0] + Km[1, 1])
    alpha = np.arctan(radius_px / f)
    rc = np.linalg.solve(Km, np.array([c[0], c[1], 1.0]))
    C = rc / np.linalg.norm(rc) / np.sin(alpha)                        # 中心(カメラ系 x 右・y 下・z 前、球の半径 = 1)
    rm = np.linalg.solve(Km, np.array([m[0], m[1], 1.0]))
    rm /= np.linalg.norm(rm)
    b = float(rm @ C)
    disc = b * b - (float(C @ C) - 1.0)
    tt = b - np.sqrt(max(0.0, disc))                                   # 手前の交点(外れたら接点へ寄せる)
    n = tt * rm - C
    n /= np.linalg.norm(n)
    return np.array([n[0], -n[1], -n[2]])                              # この関数の系(x 右、y 上、z 手前)へ


def spin_from_markers(dirs0, dirs1, dt: float) -> dict:
    """模様の向きの組(前 (M, 3)、後 (M, 3)、単位ベクトル)から角速度ベクトル ω [rad/s] を出す。

    M ≥ 2 なら Kabsch(SVD)で回転 R を当て、回転角 θ と軸から ω = θ/dt·軸(既知の ω で回した向きを入れると 1e-9 で戻る = 門)。
    M = 1 なら d₀ → d₁ の最小回転(軸 = d₀ × d₁)を返す("full" = False): 模様の向きまわりの成分は原理的に決まらず、
    コマ間の回転角が大きいと ω の直交成分の近似としても外れる(模様は ω の軸まわりの小円を描くので、最小回転の大円と違う)。
    正直に: 1 つの模様で ω を出したいなら dt を小さく(回転角 ≪ 1 rad)、それでも軸まわりの成分は別の模様が要る。
    返り値 ``{"omega", "angle", "axis", "R", "full", "rms"}``。"""
    D0 = np.asarray(dirs0, np.float64).reshape(-1, 3)
    D1 = np.asarray(dirs1, np.float64).reshape(-1, 3)
    if D0.shape != D1.shape or len(D0) < 1 or dt <= 0:
        raise ValueError("dirs must be (M, 3) pairs, dt > 0")
    D0 = D0 / np.linalg.norm(D0, axis=1, keepdims=True)
    D1 = D1 / np.linalg.norm(D1, axis=1, keepdims=True)
    if len(D0) == 1:
        a, b = D0[0], D1[0]
        ax = np.cross(a, b)
        s = np.linalg.norm(ax)
        c = float(np.clip(a @ b, -1.0, 1.0))
        ang = float(np.arctan2(s, c))
        axis = ax / s if s > 1e-15 else np.array([0.0, 0.0, 1.0])
        Kx = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
        R = np.eye(3) + np.sin(ang) * Kx + (1 - np.cos(ang)) * Kx @ Kx
        return {"omega": axis * ang / dt, "angle": ang, "axis": axis, "R": R, "full": False, "rms": 0.0}
    Hm = D0.T @ D1
    U, _, Vt = np.linalg.svd(Hm)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1.0, 1.0, d]) @ U.T
    ang = float(np.arccos(np.clip((np.trace(R) - 1.0) / 2.0, -1.0, 1.0)))
    if ang < 1e-12:
        axis = np.array([0.0, 0.0, 1.0])
    else:
        w = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
        axis = w / np.linalg.norm(w)
    rms = float(np.sqrt(np.mean(np.sum((D0 @ R.T - D1) ** 2, axis=1))))
    return {"omega": axis * ang / dt, "angle": ang, "axis": axis, "R": R, "full": True, "rms": rms}
