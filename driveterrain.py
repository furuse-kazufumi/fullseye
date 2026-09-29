"""driveterrain — 教習所の世界を広げる: 閉形式の地形と路面の材質、手続き的な木・歩行者・横断歩道(16 巡目)。

世界は「生成した時に真値を持つ」。地形は乱数位相の正弦の和(fBm のスペクトル合成、Saupe 1988: E 次元の
fBm はパワースペクトル ∝ f^{−β}、β = 2H + E)で、高さも勾配も閉形式。路面の粒・摩耗した白線・水溜り・染みは
Perlin(2002)の勾配雑音を世界座標で評価する(格子点で 0、周期 256、解析的な導関数)。コースへの距離場は
点-線分距離の閉形式で、道の外では |∇d| = 1(eikonal)。木・歩行者は箱と回転体で作り体積の閉形式が門になる。

規約: 世界座標は driveworld と同じ(x, y 水平、z 上)。高さ場 z = h(x, y) は ``terrain_height`` で、
コース(走れる多角形)の周り ``flat`` [m] は平ら(z = 路面のうねり ``road_amp`` だけ)で、そこから ``blend`` [m]
かけて smoothstep で起伏に繋がる。既存の world_build の出力に :func:`world_apply_terrain` で後から掛ける。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "perlin2", "fbm_params", "fbm_height", "fbm_gradient", "radial_periodogram", "spectral_slope",
    "course_distance", "terrain_params", "terrain_height", "terrain_gradient", "terrain_mesh",
    "world_apply_terrain", "world_materials", "material_params",
    "tree_mesh", "pedestrian_mesh", "crosswalk_mesh", "add_mesh_object", "scatter_offroad", "mesh_signed_volume",
    "TERRAIN_LABELS",
]

#: driveworld.LABELS に足すラベル(10 以降)。
TERRAIN_LABELS = {10: "terrain", 11: "puddle", 12: "crosswalk", 13: "tree"}

_ROAD_COLOR = (0.40, 0.41, 0.43)
_GRASS_COLOR = (0.36, 0.48, 0.25)
_LINE_COLOR = (0.95, 0.95, 0.92)


def _xy(x, y):
    x = np.asarray(x, np.float64)
    y = np.asarray(y, np.float64)
    if x.shape != y.shape:
        x, y = np.broadcast_arrays(x, y)
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y))):
        raise ValueError("x, y must be finite")
    return x, y


# ─────────────────────────────── Perlin の勾配雑音 ───────────────────────────────

_GRAD8 = np.array([[np.cos(k * np.pi / 4), np.sin(k * np.pi / 4)] for k in range(8)])


def _perm(seed: int) -> np.ndarray:
    rng = np.random.default_rng(int(seed))
    p = rng.permutation(256)
    return np.concatenate([p, p])


def perlin2(x, y, seed: int = 0, freq: float = 1.0) -> dict:
    """Perlin(2002, improved noise)の 2 次元勾配雑音を世界座標 (x, y) で評価する。

    格子は ``freq`` [周期/m] の間隔、勾配は 8 方向の単位ベクトル、補間は quintic fade ``6t⁵−15t⁴+10t³``。
    返り値 ``{"value", "dx", "dy"}``(導関数は解析的、``d/dx`` は世界座標あたり)。定理: 格子点で値 0、
    周期 256 格子、|value| ≤ 1。"""
    x, y = _xy(x, y)
    if not np.isfinite(freq) or freq <= 0:
        raise ValueError("freq must be positive")
    P = _perm(seed)
    X = x * freq
    Y = y * freq
    i0 = np.floor(X).astype(np.int64)
    j0 = np.floor(Y).astype(np.int64)
    fx = X - i0
    fy = Y - j0
    ia = i0 & 255
    ja = j0 & 255

    def grad(di, dj):
        h = P[P[(ia + di) & 255] + ((ja + dj) & 255)] & 7
        return _GRAD8[h]

    g00, g10, g01, g11 = grad(0, 0), grad(1, 0), grad(0, 1), grad(1, 1)
    d00 = g00[..., 0] * fx + g00[..., 1] * fy
    d10 = g10[..., 0] * (fx - 1) + g10[..., 1] * fy
    d01 = g01[..., 0] * fx + g01[..., 1] * (fy - 1)
    d11 = g11[..., 0] * (fx - 1) + g11[..., 1] * (fy - 1)
    u = fx * fx * fx * (fx * (fx * 6 - 15) + 10)
    v = fy * fy * fy * (fy * (fy * 6 - 15) + 10)
    du = 30 * fx * fx * (fx * (fx - 2) + 1)
    dv = 30 * fy * fy * (fy * (fy - 2) + 1)
    a = d00 + u * (d10 - d00)
    b = d01 + u * (d11 - d01)
    n = a + v * (b - a)
    dadx = g00[..., 0] + u * (g10[..., 0] - g00[..., 0]) + du * (d10 - d00)
    dbdx = g01[..., 0] + u * (g11[..., 0] - g01[..., 0]) + du * (d11 - d01)
    dady = g00[..., 1] + u * (g10[..., 1] - g00[..., 1])
    dbdy = g01[..., 1] + u * (g11[..., 1] - g01[..., 1])
    dndx = dadx + v * (dbdx - dadx)
    dndy = dady + v * (dbdy - dady) + dv * (b - a)
    return {"value": n, "dx": dndx * freq, "dy": dndy * freq}


# ─────────────────────────────── fBm のスペクトル合成 ───────────────────────────────

def fbm_params(seed: int = 0, hurst: float = 0.8, n_waves: int = 128, f_min: float = 1 / 200.0,
               f_max: float = 1 / 8.0, amplitude: float = 1.0) -> dict:
    """乱数位相の正弦の和で fBm 面を作るための表(Saupe 1988 のスペクトル合成の連続版)。

    周波数は [f_min, f_max] に対数一様、向きは一様、位相は一様、振幅 ∝ f^{−H}。対数一様に撒いた波は
    2 次元周波数面の密度が ∝ f^{−2} なので、パワースペクトルは ∝ A(f)² f^{−2} = f^{−(2H+2)}、
    つまり β = 2H + E(E = 2)。振幅は RMS が ``amplitude`` になるよう正規化する。"""
    if not (0 < hurst < 1):
        raise ValueError("hurst must be in (0, 1)")
    if n_waves < 1 or not (0 < f_min < f_max):
        raise ValueError("need n_waves ≥ 1 and 0 < f_min < f_max")
    if not np.isfinite(amplitude) or amplitude < 0:
        raise ValueError("amplitude must be ≥ 0")
    rng = np.random.default_rng(int(seed))
    f = np.exp(rng.uniform(np.log(f_min), np.log(f_max), n_waves))
    th = rng.uniform(0, 2 * np.pi, n_waves)
    ph = rng.uniform(0, 2 * np.pi, n_waves)
    A = f ** (-hurst)
    rms = np.sqrt(np.sum(A * A) / 2.0)
    A = A * (amplitude / rms if rms > 0 else 0.0)
    return {"f": f, "theta": th, "phi": ph, "A": A, "hurst": float(hurst), "amplitude": float(amplitude),
            "f_min": float(f_min), "f_max": float(f_max), "seed": int(seed)}


_FBM_CHUNK = 16384          # 点 × 波の一時配列を 16384 × K に抑える(512² × 1024 波を一括にすると 2 GB)


def _fbm_phase(x, y, p):
    c = np.cos(p["theta"])
    s = np.sin(p["theta"])
    # (n, K)
    return 2 * np.pi * p["f"] * (x[:, None] * c + y[:, None] * s) + p["phi"]


def _fbm_eval(x, y, p, grad: bool):
    xf, yf = x.ravel(), y.ravel()
    h = np.empty(xf.shape)
    gx = np.empty(xf.shape) if grad else None
    gy = np.empty(xf.shape) if grad else None
    for s in range(0, xf.size, _FBM_CHUNK):
        ph = _fbm_phase(xf[s:s + _FBM_CHUNK], yf[s:s + _FBM_CHUNK], p)
        if grad:
            w = -p["A"] * 2 * np.pi * p["f"] * np.sin(ph)
            gx[s:s + _FBM_CHUNK] = np.sum(w * np.cos(p["theta"]), axis=-1)
            gy[s:s + _FBM_CHUNK] = np.sum(w * np.sin(p["theta"]), axis=-1)
        else:
            h[s:s + _FBM_CHUNK] = np.sum(p["A"] * np.cos(ph), axis=-1)
    if grad:
        return gx.reshape(x.shape), gy.reshape(x.shape)
    return h.reshape(x.shape)


def fbm_height(x, y, p: dict) -> np.ndarray:
    """fBm の高さの閉形式: h(x, y) = Σ_k A_k cos(2π f_k (x cosθ_k + y sinθ_k) + φ_k)(表は :func:`fbm_params`)。"""
    x, y = _xy(x, y)
    return _fbm_eval(x, y, p, False)


def fbm_gradient(x, y, p: dict):
    """(∂h/∂x, ∂h/∂y) の閉形式。"""
    x, y = _xy(x, y)
    return _fbm_eval(x, y, p, True)


def radial_periodogram(field, dx: float, n_bins: int = 48) -> dict:
    """格子上の高さ場 (H, W) の周期図を動径方向に平均する: ``{"f", "power", "count"}``(f は周期/m)。

    平均であって環の積分ではない(積分すると f を 1 つ掛けた傾きになる)。DC は除く。"""
    Z = np.asarray(field, np.float64)
    if Z.ndim != 2 or min(Z.shape) < 8:
        raise ValueError("field must be (H, W) with H, W ≥ 8")
    if not np.isfinite(dx) or dx <= 0:
        raise ValueError("dx must be positive")
    Z = Z - Z.mean()
    win = np.hanning(Z.shape[0])[:, None] * np.hanning(Z.shape[1])[None, :]
    F = np.fft.fftshift(np.fft.fft2(Z * win))
    P = np.abs(F) ** 2
    fy = np.fft.fftshift(np.fft.fftfreq(Z.shape[0], d=dx))
    fx = np.fft.fftshift(np.fft.fftfreq(Z.shape[1], d=dx))
    R = np.hypot(fx[None, :], fy[:, None])
    fmax = min(fx.max(), fy.max())
    edges = np.linspace(0, fmax, n_bins + 1)
    idx = np.digitize(R.ravel(), edges) - 1
    ok = (idx >= 1) & (idx < n_bins)
    cnt = np.bincount(idx[ok], minlength=n_bins)
    pw = np.bincount(idx[ok], weights=P.ravel()[ok], minlength=n_bins)
    keep = cnt > 0
    fc = 0.5 * (edges[:-1] + edges[1:])
    return {"f": fc[keep], "power": pw[keep] / cnt[keep], "count": cnt[keep]}


def spectral_slope(field, dx: float, f_lo: float, f_hi: float, n_bins: int = 48) -> dict:
    """動径周期図の log–log 直線当てはめ: ``{"beta", "intercept", "n"}``(power ∝ f^{−beta})。

    定理: fBm 面(H)なら β = 2H + 2(Saupe 1988)。"""
    pg = radial_periodogram(field, dx, n_bins)
    m = (pg["f"] >= f_lo) & (pg["f"] <= f_hi) & (pg["power"] > 0)
    if np.count_nonzero(m) < 3:
        raise ValueError("fewer than 3 periodogram bins in [f_lo, f_hi]")
    lf = np.log(pg["f"][m])
    lp = np.log(pg["power"][m])
    slope, icpt = np.polyfit(lf, lp, 1)
    return {"beta": float(-slope), "intercept": float(icpt), "n": int(np.count_nonzero(m))}


# ─────────────────────────────── コースへの距離場 ───────────────────────────────

_CHUNK = 4096


def _course_polys(course) -> list:
    if not isinstance(course, dict):
        raise ValueError("course must be a dict from course_* / course_layout")
    if course.get("kind") == "layout":
        els = course.get("elements") or []
    else:
        els = [course]
    out = []
    for e in els:
        P = np.asarray(e["polygon"], np.float64)
        if np.allclose(P[0], P[-1]):
            P = P[:-1]
        out.append(P)
    if not out:
        raise ValueError("course has no polygon")
    return out


def course_distance(course, xy) -> dict:
    """点 (N, 2) からコース(走れる多角形の和)への距離と、最寄り点から外へ向く単位ベクトル。

    ``{"d" (N,), "nx" (N,), "ny" (N,)}``。内側は d = 0、n = 0。外側の d は最寄りの辺への点-線分距離の閉形式で、
    中心軸(最寄り点が 2 つある所)を除いて |∇d| = 1(eikonal)。"""
    import drivecourse
    Q = np.asarray(xy, np.float64).reshape(-1, 2)
    if not np.all(np.isfinite(Q)):
        raise ValueError("xy must be finite")
    segs = []
    for P in _course_polys(course):
        segs.append(np.stack([P, np.roll(P, -1, axis=0)], axis=1))
    S = np.concatenate(segs, axis=0)          # (M, 2, 2)
    a = S[:, 0]
    ab = S[:, 1] - S[:, 0]
    L2 = np.maximum(np.sum(ab * ab, axis=1), 1e-300)
    d = np.zeros(len(Q))
    nx = np.zeros(len(Q))
    ny = np.zeros(len(Q))
    for s in range(0, len(Q), _CHUNK):
        q = Q[s:s + _CHUNK]
        t = np.clip(((q[:, None, :] - a[None]) * ab[None]).sum(-1) / L2[None], 0.0, 1.0)   # (n, M)
        c = a[None] + t[..., None] * ab[None]                                              # (n, M, 2)
        v = q[:, None, :] - c
        dd = np.hypot(v[..., 0], v[..., 1])
        k = np.argmin(dd, axis=1)
        r = np.arange(len(q))
        dm = dd[r, k]
        vm = v[r, k]
        d[s:s + len(q)] = dm
        nrm = np.where(dm > 0, dm, 1.0)
        nx[s:s + len(q)] = vm[:, 0] / nrm
        ny[s:s + len(q)] = vm[:, 1] / nrm
    inside = drivecourse.course_contains(course, Q)
    d[inside] = 0.0
    nx[inside] = 0.0
    ny[inside] = 0.0
    return {"d": d, "nx": nx, "ny": ny}


# ─────────────────────────────── 地形 ───────────────────────────────

def terrain_params(seed: int = 0, hurst: float = 0.8, amplitude: float = 2.0, f_min: float = 1 / 120.0,
                   f_max: float = 1 / 6.0, n_waves: int = 128, flat: float = 2.0, blend: float = 10.0,
                   road_amp: float = 0.0, road_len=(160.0, 110.0), road_phase=(0.0, 1.0)) -> dict:
    """地形の表: fBm の起伏(道から ``flat`` m は 0、そこから ``blend`` m で smoothstep)+ 路面のうねり
    ``road_amp·½[sin(2πx/L₁+φ₁) + sin(2πy/L₂+φ₂)]``(道にも掛かる、勾配の上限 = road_amp·π/min(L))。"""
    if flat < 0 or blend <= 0:
        raise ValueError("need flat ≥ 0 and blend > 0")
    if not np.isfinite(road_amp) or road_amp < 0:
        raise ValueError("road_amp must be ≥ 0")
    L1, L2 = float(road_len[0]), float(road_len[1])
    if L1 <= 0 or L2 <= 0:
        raise ValueError("road_len must be positive")
    p = fbm_params(seed, hurst, n_waves, f_min, f_max, amplitude)
    p.update({"flat": float(flat), "blend": float(blend), "road_amp": float(road_amp), "road_len": (L1, L2),
              "road_phase": (float(road_phase[0]), float(road_phase[1]))})
    return p


def _road_wave(x, y, p):
    L1, L2 = p["road_len"]
    p1, p2 = p["road_phase"]
    a = 0.5 * p["road_amp"]
    z = a * (np.sin(2 * np.pi * x / L1 + p1) + np.sin(2 * np.pi * y / L2 + p2))
    zx = a * 2 * np.pi / L1 * np.cos(2 * np.pi * x / L1 + p1)
    zy = a * 2 * np.pi / L2 * np.cos(2 * np.pi * y / L2 + p2)
    return z, zx, zy


def _blend(d, p):
    t = np.clip((d - p["flat"]) / p["blend"], 0.0, 1.0)
    return t * t * (3 - 2 * t), 6 * t * (1 - t) / p["blend"]


def terrain_height(x, y, p: dict, course=None) -> np.ndarray:
    """z = fbm(x, y)·w(d(x, y)) + うねり(x, y)。course が無ければ w = 1(起伏だけ)。"""
    x, y = _xy(x, y)
    h = fbm_height(x, y, p)
    if course is not None:
        dist = course_distance(course, np.column_stack([x.ravel(), y.ravel()]))
        w, _ = _blend(dist["d"].reshape(x.shape), p)
        h = h * w
    return h + _road_wave(x, y, p)[0]


def terrain_gradient(x, y, p: dict, course=None):
    """(∂z/∂x, ∂z/∂y) の閉形式: ∇(h·w) = w∇h + h·w′(d)·∇d、∇d = 最寄り点から外へ向く単位ベクトル。"""
    x, y = _xy(x, y)
    hx, hy = fbm_gradient(x, y, p)
    if course is not None:
        h = fbm_height(x, y, p)
        dist = course_distance(course, np.column_stack([x.ravel(), y.ravel()]))
        w, dw = _blend(dist["d"].reshape(x.shape), p)
        gx = dist["nx"].reshape(x.shape)
        gy = dist["ny"].reshape(x.shape)
        hx = w * hx + h * dw * gx
        hy = w * hy + h * dw * gy
    _, rx, ry = _road_wave(x, y, p)
    return hx + rx, hy + ry


def terrain_mesh(p: dict, course, bounds, step: float = 2.0) -> dict:
    """(xmin, xmax, ymin, ymax) を step の升に割り z = terrain_height の格子メッシュ。

    ``{"V", "F", "face_label" (0 = 道の内側、10 = 地形), "face_color"}``。面のラベルは重心の内外判定。"""
    import drivecourse
    xmin, xmax, ymin, ymax = (float(v) for v in bounds)
    if not (xmax > xmin and ymax > ymin) or step <= 0:
        raise ValueError("bad bounds or step")
    nx = max(1, int(np.ceil((xmax - xmin) / step)))
    ny = max(1, int(np.ceil((ymax - ymin) / step)))
    xs = np.linspace(xmin, xmax, nx + 1)
    ys = np.linspace(ymin, ymax, ny + 1)
    X, Y = np.meshgrid(xs, ys)
    Z = terrain_height(X, Y, p, course)
    V = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])
    i = np.arange(ny)[:, None] * (nx + 1) + np.arange(nx)[None, :]
    a, b, c, d = i.ravel(), (i + 1).ravel(), (i + nx + 2).ravel(), (i + nx + 1).ravel()
    F = np.vstack([np.column_stack([a, b, c]), np.column_stack([a, c, d])]).astype(np.int64)
    cen = V[F].mean(axis=1)[:, :2]
    inside = drivecourse.course_contains(course, cen)
    label = np.where(inside, 0, 10).astype(np.int64)
    color = np.where(inside[:, None], np.asarray(_ROAD_COLOR), np.asarray(_GRASS_COLOR))
    return {"V": V, "F": F, "face_label": label, "face_color": color}


def world_apply_terrain(world: dict, p: dict, step: float = 2.0) -> dict:
    """world_build の出力(平らな世界)に地形を掛ける(その場で書き換え、同じ dict を返す)。

    路面の升(objects[0] "ground")を terrain_mesh に置き換え、姿勢を持つ物体(資産・木・歩行者)は姿勢の
    (x, y) の高さだけ剛体で持ち上げ、持たない物体(縁石・白線・停止線・レール・坂)は頂点ごとに持ち上げる。
    ``world["terrain"] = p`` を記録する。"""
    if not world.get("objects") or world["objects"][0].get("name") != "ground":
        raise ValueError("world must come from world_build (objects[0] is the ground)")
    course = world["course"]
    g = world["objects"][0]
    v0, v1 = g["verts"]
    f0, f1 = g["faces"]
    tm = terrain_mesh(p, course, world["bounds"], step)
    # 頂点・面を差し替える(索引をずらす)
    dv = len(tm["V"]) - (v1 - v0)
    df = len(tm["F"]) - (f1 - f0)
    V = np.vstack([world["V"][:v0], tm["V"], world["V"][v1:]])
    F_rest = world["F"][f1:] + dv
    F = np.vstack([world["F"][:f0], tm["F"] + v0, F_rest])
    world["V"], world["F"] = V, F
    world["face_label"] = np.concatenate([world["face_label"][:f0], tm["face_label"], world["face_label"][f1:]])
    world["face_color"] = np.vstack([world["face_color"][:f0], tm["face_color"], world["face_color"][f1:]])
    g["verts"] = (v0, v0 + len(tm["V"]))
    g["faces"] = (f0, f0 + len(tm["F"]))
    for obj in world["objects"][1:]:
        a, b = obj["verts"]
        obj["verts"] = (a + dv, b + dv)
        a, b = obj["faces"]
        obj["faces"] = (a + df, b + df)
        a, b = obj["verts"]
        if obj.get("pose") is not None:
            x, y = obj["pose"][0], obj["pose"][1]
            dz = float(terrain_height(np.array([x]), np.array([y]), p, course)[0])
            world["V"][a:b, 2] += dz
            obj["z"] = float(obj.get("z", 0.0)) + dz
        else:
            xy = world["V"][a:b, :2]
            world["V"][a:b, 2] += terrain_height(xy[:, 0], xy[:, 1], p, course)
    world["terrain"] = p
    return world


# ─────────────────────────────── 路面の材質(画素ごと、世界座標で) ───────────────────────────────

def material_params(seed: int = 0, grain: float = 0.05, puddle_level: float = 0.55, puddle_freq: float = 0.6,
                    stain_level: float = 0.6, stain_freq: float = 0.9, wear: float = 0.6, wear_freq: float = 2.0,
                    grass_var: float = 0.10, sky=(0.62, 0.75, 0.92)) -> dict:
    """材質の表。puddle = Perlin(puddle_freq) > puddle_level の所(道の内側だけ、ラベル 11、色 = 写り込み refl·空 + (1−refl)·陰影つきの路面)、
    stain = 同様に暗い染み(ラベルは道のまま、真値の場 "stain" に残る)、wear = 白線の摩耗率 clip(wear·(Perlin(wear_freq)·0.5+0.5)·2, 0, 1)。"""
    for k, v in (("grain", grain), ("puddle_freq", puddle_freq), ("stain_freq", stain_freq), ("wear_freq", wear_freq)):
        if not np.isfinite(v) or v < 0:
            raise ValueError("%s must be ≥ 0" % k)
    if not (0 <= wear <= 1):
        raise ValueError("wear must be in [0, 1]")
    return {"seed": int(seed), "grain": float(grain), "puddle_level": float(puddle_level),
            "puddle_freq": float(puddle_freq), "stain_level": float(stain_level), "stain_freq": float(stain_freq),
            "wear": float(wear), "wear_freq": float(wear_freq), "grass_var": float(grass_var),
            "sky": tuple(float(v) for v in sky)}


def _world_points(view: dict, pose, K) -> np.ndarray:
    """描画結果の深度から画素の世界座標 (H, W, 3) を戻す(NaN = 空)。"""
    import drivettc
    Pc = drivettc.camera_backproject(view["depth"], K)
    T = np.linalg.inv(np.asarray(pose, np.float64))
    Pw = Pc @ T[:3, :3].T + T[:3, 3]
    return Pw


def world_materials(world: dict, view: dict, pose, K, m: dict) -> dict:
    """描画結果 ``view``(world_camera、"shade" を含む)に路面の材質を画素ごとに掛ける。

    路面(ラベル 0)と地形(10)の画素は世界座標で材質を評価し直す: アスファルトの粒(Perlin 8 周期/m)、草の色むら、
    染み(暗い斑、ラベルは 0 のまま)、水溜り(空の写り込み、ラベル 11)。白線・横断歩道(9・12)は摩耗率 wear で
    路面の色に混ぜる(ラベルは不変、真値 "wear" に残る)。水溜りの写り込みの強さ(0.1〜0.9、Perlin 1.5 周期/m)は真値 "refl"。
    返り値 = ``{"color", "label", "puddle", "refl", "stain", "wear", "xyz"}``。"""
    import drivecourse
    if "shade" not in view:
        raise ValueError("view must come from world_camera(..., shade=True)")
    color = np.array(view["color"], np.float64, copy=True)
    label = np.array(view["label"], np.int64, copy=True)
    shade = np.asarray(view["shade"], np.float64)
    H, W = label.shape
    Pw = _world_points(view, pose, K)
    X, Y = Pw[..., 0], Pw[..., 1]
    ok = np.isfinite(X)
    puddle = np.zeros((H, W), bool)
    refl = np.zeros((H, W))
    stain = np.zeros((H, W))
    wear = np.zeros((H, W))
    ground = ok & ((label == 0) | (label == 10))
    if np.any(ground):
        xs, ys = X[ground], Y[ground]
        inside = drivecourse.course_contains(world["course"], np.column_stack([xs, ys]))
        g = perlin2(xs, ys, m["seed"] + 1, 8.0)["value"]
        base = np.where(inside[:, None], np.asarray(_ROAD_COLOR), np.asarray(_GRASS_COLOR))
        gv = perlin2(xs, ys, m["seed"] + 2, 0.25)["value"]
        base = base * (1.0 + m["grain"] * g[:, None] + np.where(inside, 0.0, m["grass_var"] * gv)[:, None])
        st = perlin2(xs, ys, m["seed"] + 3, m["stain_freq"])["value"]
        s_amt = np.clip((st - m["stain_level"]) / max(1e-9, 1 - m["stain_level"]), 0, 1) * inside
        base = base * (1.0 - 0.55 * s_amt)[:, None]
        pd = perlin2(xs, ys, m["seed"] + 4, m["puddle_freq"])["value"]
        is_p = (pd > m["puddle_level"]) & inside
        sky = np.asarray(m["sky"])
        col = base * shade[ground][:, None]
        rf = np.clip(0.5 + 0.6 * perlin2(xs[is_p], ys[is_p], m["seed"] + 6, 1.5)["value"], 0.1, 0.9)
        col[is_p] = rf[:, None] * sky + (1 - rf)[:, None] * col[is_p]  # 写り込み rf(空)+ 濡れた底(陰影つき)。鏡面の幾何ではない
        rfl = np.zeros(np.count_nonzero(ground))
        rfl[is_p] = rf
        refl[ground] = rfl
        color[ground] = np.clip(col, 0, 1)
        lab = np.where(inside, 0, 10)
        lab[is_p] = 11
        label[ground] = lab
        pm = np.zeros(np.count_nonzero(ground), bool)
        pm[is_p] = True
        puddle[ground] = pm
        stain[ground] = s_amt
    lines = ok & ((label == 9) | (label == 12))
    if np.any(lines):
        xs, ys = X[lines], Y[lines]
        wv = perlin2(xs, ys, m["seed"] + 5, m["wear_freq"])["value"]
        w = np.clip(m["wear"] * (wv * 0.5 + 0.5) * 2.0, 0, 1)
        g = perlin2(xs, ys, m["seed"] + 1, 8.0)["value"]
        road = np.asarray(_ROAD_COLOR) * (1.0 + m["grain"] * g[:, None])
        col = (np.asarray(_LINE_COLOR) * (1 - w)[:, None] + road * w[:, None]) * shade[lines][:, None]
        color[lines] = np.clip(col, 0, 1)
        wear[lines] = w
    return {"color": color, "label": label, "puddle": puddle, "refl": refl, "stain": stain, "wear": wear, "xyz": Pw}


# ─────────────────────────────── 手続き的な物体 ───────────────────────────────

def _prism(poly_xy: np.ndarray, z0: float, z1: float):
    """多角形 (n, 2) を z0..z1 に押し出した閉じたメッシュ(側面 + 上下の扇)。"""
    n = len(poly_xy)
    Vb = np.column_stack([poly_xy, np.full(n, z0)])
    Vt = np.column_stack([poly_xy, np.full(n, z1)])
    V = np.vstack([Vb, Vt, [[*poly_xy.mean(0), z0]], [[*poly_xy.mean(0), z1]]])
    cb, ct = 2 * n, 2 * n + 1
    F = []
    for i in range(n):
        j = (i + 1) % n
        F += [[i, j, n + j], [i, n + j, n + i], [cb, j, i], [ct, n + i, n + j]]
    return V, np.asarray(F, np.int64)


def _revolve(profile_rz: np.ndarray, n: int):
    """輪郭 (r_k, z_k)(下から上、r ≥ 0、両端は r = 0 でよい)を z 軸まわりに n 分割で回した閉じたメッシュ。"""
    ang = np.arange(n) * 2 * np.pi / n
    rings = []
    V = []
    for r, z in profile_rz:
        if r <= 0:
            rings.append([len(V)])
            V.append([0.0, 0.0, z])
        else:
            rings.append(list(range(len(V), len(V) + n)))
            V += [[r * np.cos(a), r * np.sin(a), z] for a in ang]
    F = []
    for k in range(len(rings) - 1):
        A, B = rings[k], rings[k + 1]
        for i in range(n):
            j = (i + 1) % n
            a0, a1 = A[i % len(A)], A[j % len(A)]
            b0, b1 = B[i % len(B)], B[j % len(B)]
            if len(A) == 1:
                F.append([a0, b1, b0])            # 底の扇は外向き(−z)
            elif len(B) == 1:
                F.append([a0, a1, b0])
            else:
                F += [[a0, a1, b1], [a0, b1, b0]]
    return np.asarray(V, np.float64), np.asarray(F, np.int64)


def mesh_signed_volume(V, F) -> float:
    """閉じたメッシュの符号つき体積(発散定理: Σ v₀·(v₁×v₂)/6、外向きで正)。"""
    V = np.asarray(V, np.float64)
    F = np.asarray(F, np.int64)
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(np.sum(np.einsum("ij,ij->i", a, np.cross(b, c))) / 6.0)


def tree_mesh(height: float = 6.0, trunk_radius: float = 0.15, crown_radius: float = 1.8, kind: str = "broadleaf",
              n: int = 8, color=None) -> dict:
    """手続き的な木: 幹 = 正 n 角柱(高さ 0.35·height)、樹冠 = 円錐(conifer)か回転楕円体(broadleaf、上下 0.65·height)。

    返り値 ``{"V", "F", "color" (M,3), "label" (13), "dims", "volume"}``。``volume`` は閉形式: 幹 = ½ n r² sin(2π/n)·h_t、
    円錐 = ⅓·½ n R² sin(2π/n)·h_c(多角形の底面なので厳密)、楕円体は内接なので mesh_signed_volume ≤ 4/3·π R² (h_c/2)。"""
    if height <= 0 or trunk_radius <= 0 or crown_radius <= 0 or n < 3:
        raise ValueError("bad tree dims")
    if kind not in ("broadleaf", "conifer"):
        raise ValueError("kind must be 'broadleaf' or 'conifer'")
    ht = 0.35 * height
    hc = height - ht
    ang = np.arange(n) * 2 * np.pi / n
    poly = trunk_radius * np.column_stack([np.cos(ang), np.sin(ang)])
    Vt, Ft = _prism(poly, 0.0, ht)
    apoly = 0.5 * n * np.sin(2 * np.pi / n)
    if kind == "conifer":
        Vc, Fc = _revolve(np.array([[0.0, ht * 0.95], [crown_radius, ht * 0.95], [0.0, height]]), n)
        vol_c = apoly * crown_radius ** 2 * (height - ht * 0.95) / 3.0
        exact = True
    else:
        m = 10
        t = np.linspace(-np.pi / 2, np.pi / 2, m + 2)
        prof = np.column_stack([crown_radius * np.cos(t), ht + hc / 2 + hc / 2 * np.sin(t)])
        prof[0, 0] = prof[-1, 0] = 0.0
        Vc, Fc = _revolve(prof, n)
        vol_c = 4.0 / 3.0 * np.pi * crown_radius ** 2 * (hc / 2)
        exact = False
    V = np.vstack([Vt, Vc])
    F = np.vstack([Ft, Fc + len(Vt)])
    trunk_col = np.array([0.36, 0.25, 0.15])
    crown_col = np.array(color if color is not None else ([0.13, 0.42, 0.16] if kind == "conifer" else [0.22, 0.55, 0.20]))
    C = np.vstack([np.tile(trunk_col, (len(Ft), 1)), np.tile(crown_col, (len(Fc), 1))])
    return {"V": V, "F": F, "color": C, "label": 13, "dims": (2 * crown_radius, 2 * crown_radius, height),
            "volume": {"trunk": apoly * trunk_radius ** 2 * ht, "crown": vol_c, "crown_exact": exact}}


def pedestrian_mesh(height: float = 1.7, color=None, stride: float = 0.0) -> dict:
    """手続き的な歩行者: 脚 2 本(箱)、胴(箱)、頭(回転体)。原点 = 足元中心、+x が前。``stride`` [m] で脚を前後に開く。

    返り値 ``{"V", "F", "color", "label" (7), "dims", "volume"}``(体積は箱の閉形式 + 頭は内接 ≤ 球)。"""
    if height <= 0:
        raise ValueError("height must be positive")
    h = float(height)
    leg_h, torso_h, head_r = 0.47 * h, 0.35 * h, 0.065 * h
    leg_w, leg_d = 0.09 * h, 0.09 * h
    torso_w, torso_d = 0.24 * h, 0.12 * h
    parts = []

    def box(x0, x1, y0, y1, z0, z1):
        poly = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
        return _prism(poly, z0, z1)

    s = float(stride) / 2
    parts.append(box(-leg_d / 2 + s, leg_d / 2 + s, -torso_w / 2, -torso_w / 2 + leg_w, 0.0, leg_h))
    parts.append(box(-leg_d / 2 - s, leg_d / 2 - s, torso_w / 2 - leg_w, torso_w / 2, 0.0, leg_h))
    parts.append(box(-torso_d / 2, torso_d / 2, -torso_w / 2, torso_w / 2, leg_h, leg_h + torso_h))
    m = 8
    t = np.linspace(-np.pi / 2, np.pi / 2, m + 2)
    zc = leg_h + torso_h + head_r * 1.05
    prof = np.column_stack([head_r * np.cos(t), zc + head_r * np.sin(t)])
    prof[0, 0] = prof[-1, 0] = 0.0
    parts.append(_revolve(prof, 10))
    V = np.zeros((0, 3))
    F = np.zeros((0, 3), np.int64)
    C = []
    cols = [np.array([0.20, 0.22, 0.40])] * 2 + [np.array(color if color is not None else [0.80, 0.25, 0.20]),
                                               np.array([0.85, 0.70, 0.58])]
    for (v, f), c in zip(parts, cols):
        F = np.vstack([F, f + len(V)])
        V = np.vstack([V, v])
        C.append(np.tile(c, (len(f), 1)))
    vol_box = 2 * leg_d * leg_w * leg_h + torso_d * torso_w * torso_h
    return {"V": V, "F": F, "color": np.vstack(C), "label": 7, "dims": (torso_d, torso_w, zc + head_r),
            "volume": {"boxes": vol_box, "head_max": 4.0 / 3.0 * np.pi * head_r ** 3}}


def crosswalk_mesh(a, b, length: float = 4.0, stripe: float = 0.45, gap: float = 0.45, z: float = 0.006) -> dict:
    """横断歩道(ゼブラ): 道を横切る線分 a→b に沿って幅 ``stripe``・間隔 ``gap`` の縞を、a→b に直交する向きに
    ``length`` だけ伸ばす(a→b の左手側)。``{"V", "F", "color", "label" (12), "n_stripes", "area"}``。"""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    d = b - a
    L = float(np.hypot(*d))
    if L <= 0 or length <= 0 or stripe <= 0 or gap < 0:
        raise ValueError("bad crosswalk geometry")
    u = d / L
    nrm = np.array([-u[1], u[0]]) * length
    V, F = [], []
    s = 0.0
    k = 0
    while s + stripe <= L + 1e-9:
        p0 = a + u * s
        p1 = a + u * (s + stripe)
        i = len(V)
        V += [[*p0, z], [*p1, z], [*(p1 + nrm), z], [*(p0 + nrm), z]]
        F += [[i, i + 1, i + 2], [i, i + 2, i + 3]]
        s += stripe + gap
        k += 1
    if k == 0:
        raise ValueError("segment shorter than one stripe")
    F = np.asarray(F, np.int64)
    return {"V": np.asarray(V, np.float64), "F": F, "color": np.tile(np.asarray(_LINE_COLOR), (len(F), 1)),
            "label": 12, "n_stripes": k, "area": k * stripe * length}


def add_mesh_object(world: dict, mesh: dict, x: float, y: float, yaw: float, *, name: str = "", z: float = 0.0) -> int:
    """手続き的なメッシュ(tree_mesh / pedestrian_mesh …、原点 = 底面中心)を姿勢に置いて世界に足す。

    資産と同じ ``pose``/``dims`` を持たせるので :func:`driveworld.world_move` で動かせる。"""
    import driveworld
    V = driveworld.place_mesh(np.asarray(mesh["V"], np.float64), float(x), float(y), float(yaw), float(z))
    i = driveworld.world_add(world, V, mesh["F"], int(mesh["label"]), mesh["color"], name=name or "mesh",
                             pose=(x, y, yaw), extra={"dims": tuple(float(v) for v in mesh["dims"]), "z": float(z)})
    return i


def scatter_offroad(course, bounds, n: int = 60, r_min: float = 4.0, margin: float = 3.0, seed: int = 0,
                    max_tries: int = 20000) -> np.ndarray:
    """道の外に物を撒く(dart throwing): 各点はコースから ``margin`` 以上、互いに ``r_min`` 以上離れる。

    返り値 (n', 3) = (x, y, yaw)。``max_tries`` で n に届かなければあるだけ返す(n' ≤ n)。"""
    if n < 0 or r_min <= 0 or margin < 0:
        raise ValueError("bad scatter parameters")
    rng = np.random.default_rng(int(seed))
    xmin, xmax, ymin, ymax = (float(v) for v in bounds)
    pts = []
    tries = 0
    while len(pts) < n and tries < max_tries:
        m = 256
        q = np.column_stack([rng.uniform(xmin, xmax, m), rng.uniform(ymin, ymax, m)])
        tries += m
        d = course_distance(course, q)["d"]
        for k in np.nonzero(d >= margin)[0]:
            if len(pts) >= n:
                break
            if pts:
                P = np.asarray(pts)[:, :2]
                if np.min(np.hypot(P[:, 0] - q[k, 0], P[:, 1] - q[k, 1])) < r_min:
                    continue
            pts.append([q[k, 0], q[k, 1], rng.uniform(0, 2 * np.pi)])
    return np.asarray(pts, np.float64).reshape(-1, 3)
