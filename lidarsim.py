# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""lidarsim — 回転式 LiDAR を三角形メッシュの世界に撃つ(レイキャスト、numpy のみ)。

Velodyne / Ouster / Hesai のような**回転式(spinning)LiDAR** は、水平に 360° 回りながら
複数のレーザ層(beam)で縦方向を掃く。本モジュールは、その 1 スイープを三角形メッシュの世界
``(V, F)`` に対して**幾何学的に厳密に**(各レイと各三角形の交点を解いて)合成する。
出力は :mod:`spherical_proj` と同じ並びの球面レンジ画像 ``ranges (n_beams, n_az)`` と、
世界座標の反射点、当たった面の番号、面ラベルである。

## 固有価値(既存との棲み分け, honest)

* :mod:`spherical_proj` は「点群 ⇄ レンジ画像」の**整列**であり、世界(面)を知らない。本モジュールは
  **面の世界からレンジ画像を作る**側(合成)で、遮蔽・視野・測距範囲・ノイズを持つ。両者は同じ
  行/列規約を共有し、本モジュールの ``ranges`` を ``spherical_proj.unproject_spherical`` に渡すと
  センサ座標の反射点がそのまま戻る(:func:`lidar_range_image_to_points`)。
* :mod:`render3d` はカメラ(透視投影・ラスタ化)で、視錐台の中しか見えない。ここは全方位の
  **角度格子のレイキャスト**で、水平 360° の巻き(azimuth wrap)を扱う。
* :func:`evis_fullseye_bridge.pseudo_lidar_rays` は水平面内の 2-D スキャン。ここは仰角を持つ 3-D。

## 方法

レイ–三角形交差は Möller–Trumbore(1997)を numpy でベクトル化(両面、裏面カリングなし)。
**加速**: センサ原点から見た各三角形の方位角区間・仰角区間を求め、レイの (beam, 列) 格子に
落として候補だけを検査する。

* 方位角区間 = 3 頂点の方位角を覆う最小の弧。弧が π 以上(xy 射影が原点を含む)、または頂点が
  原点上、または辺が原点を通る三角形は**全方位・全仰角**として保守的に扱う。±π を跨ぐ区間は
  列区間を 2 つに割る(wrap)。
* 仰角区間 = 頂点の仰角の min/max **に加えて、各辺(大円弧)の仰角の極値**を含める。辺がセンサの
  真上/真下近くを通ると頂点の仰角より高い/低い点が辺の途中に出るため(例: 頂点 (±10, 0.2, 1) の辺は
  頂点で 5.7° だが途中で 78.7°)、頂点だけで区間を作ると当たるはずのレイを落とす。大円の最高点
  ``ĥ ∝ ẑ − (ẑ·n̂)n̂`` が短弧の内側にあるかを外積の符号で判定する(閉形式)。
* 候補 (三角形, beam, 列) の組を全部展開して一括で Möller–Trumbore を解き、レイごとに最小距離を
  ``np.minimum.at`` で取る(同距離の場合は面番号の小さい方)。組は ``_PAIR_CHUNK`` ずつ処理して
  メモリを抑える。原点からの平面距離が ``range_max`` を超える三角形は事前に捨てる。

測った速度(2026-09-29, Windows 11, Python 3.11, numpy 2.4.6, 32 beam × 1800 列 = 57,600 レイ、
ウォームアップ後 1 回の wall time):
地面 2,000 三角形(60 m 四方)+ 箱 200(2,400 三角形)= 4,400 三角形で **0.16 s**(41,707 hit)、
地面 2,000 + 箱 1,500(18,000)= 20,000 三角形で **0.80 s**(55,631 hit)。
``tests/test_lidarsim.py::test_scan_speed`` が 10 s 未満を門にする。同じテストファイルで、辺の極値・
wrap・全方位扱いをそれぞれ無効化すると力ずく実装との一致の門が赤になることを確認済み(門は壊して確かめた)。

## フレーム規約

* 世界座標: x = 前/東, y = 左/北, z = 上(右手系)、単位 m、角度 rad(度を受ける引数は ``_deg``)。
* ``T_sensor`` は 4×4 同次行列(world ← sensor)。回転部は正規直交でなければ ``ValueError``。
* センサ座標: x = 前, y = 左, z = 上。beam i(仰角 e_i)・列 j(方位角 a_j)のレイ方向は
  ``(cos e_i cos a_j, cos e_i sin a_j, sin e_i)``。
* ``ranges`` の並びは :mod:`spherical_proj` と同一: **行 0 = 上端の仰角(v_max)**、行の中心仰角
  ``e_i = v_max − (i + 0.5)(v_max − v_min)/n_beams``。**列 0 = 方位角 −π(後方)**、中央列 = 0(前方 +x)、
  列は反時計回りに増え、列の中心方位角 ``a_j = −π + (j + 0.5)·2π/n_az``
  (``spherical_proj.unproject_spherical`` のビン中心と同一)。
* ``points`` は世界座標。センサ座標に戻すのは :func:`lidar_points_sensor_frame`。

## 限界(self_reported)

* **単一リターン**(最も近い面だけ)。半透明・複数エコー・last return はない。
* **ビームの広がりなし**(レイは幅ゼロ)。実機の footprint による端の混合(mixed pixel)は出ない。
* **強度・材質モデルなし**(反射率・入射角依存の欠測・黒体の無返答はない)。全ての面は必ず返す。
* **運動歪みなし**(1 スイープは剛体・瞬時)。ego-motion の deskew は対象外。
* **方位角は等間隔・仰角も等間隔**(実機の非等間隔ビーム配置は表現しない。``elevations`` を書き換えて
  使う場合は ``lidar_range_image_to_points`` の逆投影は合わなくなる)。
* ``range_min`` 未満 / ``range_max`` 超の**最近接**は「無返答(0)」にする(奥の面に抜けはしない: 近すぎる
  面は物理的にビームを塞ぐと見なす)。ノイズは無ノイズの距離で判定した後に足す(ノイズが返答の有無を
  変えることはない)。
* 三角形の辺・頂点上にちょうど乗るレイは両側の三角形に「当たる」扱い(許容 1e-9)にして穴を防ぐ。

## 参考文献

* T. Möller, B. Trumbore, "Fast, Minimum Storage Ray/Triangle Intersection", J. Graphics Tools 2(1), 1997.
* A. Williams et al., "An Efficient and Robust Ray–Box Intersection Algorithm", J. Graphics Tools 10(1), 2005(slab 法)。
"""
from __future__ import annotations

import math

import numpy as np

import spherical_proj

__all__ = [
    "lidar_spec",
    "lidar_scan",
    "lidar_points_sensor_frame",
    "lidar_range_image_to_points",
    "ray_plane_range",
    "ray_box_ranges",
]

_TWO_PI = 2.0 * math.pi
_DET_EPS = 1e-12          # 平行レイ / 退化三角形
_BARY_EPS = 1e-9          # 重心座標の許容(辺の上のレイを両側に含めて穴を防ぐ)
_ORIGIN_EPS = 1e-12       # センサ原点上の頂点
_PAIR_CHUNK = 1 << 20     # 一括処理する (三角形, レイ) 組の数
_Z_HAT = np.array([0.0, 0.0, 1.0])


# ---- 検査(fail-closed) --------------------------------------------------------------------------
def _finite_points(P, what: str) -> np.ndarray:
    A = np.asarray(P, np.float64)
    if A.ndim != 2 or A.shape[1] != 3:
        raise ValueError("lidarsim: %s must be (N, 3), got %r" % (what, (A.shape,)))
    bad = ~np.isfinite(A)
    if bad.any():
        row = int(np.flatnonzero(bad.any(axis=1))[0])
        raise ValueError("lidarsim: %s contain %d non-finite value(s) (first at index %d)"
                         % (what, int(bad.sum()), row))
    return A


def _mesh_arrays(V, F) -> tuple[np.ndarray, np.ndarray]:
    """``(V, F)`` を float64 (N,3) / int64 (M,3) に整形し検査(:mod:`render3d` と同じ流儀)。"""
    Vv = _finite_points(V, "vertices")
    if Vv.shape[0] == 0:
        raise ValueError("lidarsim: mesh has no vertices")
    Ff = np.asarray(F)
    if Ff.size == 0:
        raise ValueError("lidarsim: mesh has no faces")
    if Ff.ndim != 2 or Ff.shape[1] != 3:
        raise ValueError("lidarsim: faces must be (M, 3) triangles, got %r" % (Ff.shape,))
    if not np.issubdtype(Ff.dtype, np.integer):
        if not np.all(np.mod(Ff, 1) == 0):
            raise ValueError("lidarsim: faces must be integer indices")
    Ff = Ff.astype(np.int64)
    lo, hi = int(Ff.min()), int(Ff.max())
    if lo < 0 or hi >= Vv.shape[0]:
        raise ValueError("lidarsim: face index %d out of range for %d vertices"
                         % (hi if hi >= Vv.shape[0] else lo, Vv.shape[0]))
    return Vv, Ff


def _check_pose(T) -> np.ndarray:
    P = np.asarray(T, np.float64)
    if P.shape != (4, 4):
        raise ValueError("lidarsim: T_sensor must be a 4x4 matrix, got %r" % (P.shape,))
    if not np.isfinite(P).all():
        raise ValueError("lidarsim: T_sensor contains non-finite values")
    R = P[:3, :3]
    if not np.allclose(R @ R.T, np.eye(3), atol=1e-6) or float(np.linalg.det(R)) < 0.0:
        raise ValueError("lidarsim: T_sensor rotation is not a proper orthonormal matrix")
    if not np.allclose(P[3], [0.0, 0.0, 0.0, 1.0], atol=1e-9):
        raise ValueError("lidarsim: T_sensor last row must be [0, 0, 0, 1]")
    return P


def _check_spec(spec) -> dict:
    need = ("n_beams", "n_az", "v_fov_deg", "range_min", "range_max", "noise_std",
            "elevations", "azimuths")
    if not isinstance(spec, dict) or any(k not in spec for k in need):
        raise ValueError("lidarsim: spec must come from lidar_spec() (missing keys)")
    nb, na = int(spec["n_beams"]), int(spec["n_az"])
    if nb < 1 or na < 1:
        raise ValueError("lidarsim: spec has non-positive resolution")
    el = np.asarray(spec["elevations"], np.float64)
    az = np.asarray(spec["azimuths"], np.float64)
    if el.shape != (nb,) or az.shape != (na,):
        raise ValueError("lidarsim: spec elevations/azimuths do not match n_beams/n_az")
    return spec


# ---- 仕様 -------------------------------------------------------------------------------------------
def lidar_spec(n_beams: int = 32, v_fov_deg=(-25.0, 15.0), azimuth_res_deg: float = 0.2,
               range_max: float = 60.0, range_min: float = 0.5, noise_std: float = 0.0) -> dict:
    """回転式 LiDAR の仕様 dict を作る(既定は 32 beam・仰角 −25…+15°・方位 0.2° = 1800 列)。

    - ``n_beams``: レーザ層の数(≥ 1)。仰角帯 ``v_fov_deg=(v_min, v_max)`` [度] を等分し、行 0 が
      上端 ``v_max`` 側(:mod:`spherical_proj` と同じ)。``v_min < v_max``、いずれも [−90, 90] の中。
    - ``azimuth_res_deg``: 方位角の刻み [度](> 0)。360° を割り切る値でなければ ``ValueError``
      (等間隔の 1 周が前提。0.2 → 1800 列、0.1 → 3600 列)。
    - ``range_min`` / ``range_max`` [m]: 測距範囲(``0 ≤ range_min < range_max < ∞``)。外の最近接は無返答。
    - ``noise_std`` [m]: range 方向のガウスノイズの標準偏差(≥ 0、0 = 完全決定的)。

    返り値の dict: ``n_beams, n_az, v_fov_deg, azimuth_res_deg, range_min, range_max, noise_std,
    elevations (n_beams,) [rad, 行 0 = 上端], azimuths (n_az,) [rad, 列 0 = −π 側の中心]``。
    """
    nb = int(n_beams)
    if nb < 1:
        raise ValueError("lidarsim: n_beams must be >= 1, got %r" % (n_beams,))
    v_min, v_max = float(v_fov_deg[0]), float(v_fov_deg[1])
    if not (math.isfinite(v_min) and math.isfinite(v_max)) or not (v_min < v_max):
        raise ValueError("lidarsim: v_fov_deg must be (v_min, v_max) with v_min < v_max, got %r"
                         % (v_fov_deg,))
    if v_min < -90.0 or v_max > 90.0:
        raise ValueError("lidarsim: v_fov_deg must lie within [-90, 90], got %r" % (v_fov_deg,))
    res = float(azimuth_res_deg)
    if not math.isfinite(res) or res <= 0.0 or res > 360.0:
        raise ValueError("lidarsim: azimuth_res_deg must be in (0, 360], got %r" % (azimuth_res_deg,))
    na_f = 360.0 / res
    na = int(round(na_f))
    if na < 1 or abs(na_f - na) > 1e-6:
        raise ValueError("lidarsim: azimuth_res_deg=%r does not divide 360 deg into an integer "
                         "number of columns (uniform spacing required)" % (azimuth_res_deg,))
    r_min, r_max = float(range_min), float(range_max)
    if not (math.isfinite(r_min) and math.isfinite(r_max)) or r_min < 0.0 or not (r_max > r_min):
        raise ValueError("lidarsim: need 0 <= range_min < range_max (finite), got %r, %r"
                         % (range_min, range_max))
    sd = float(noise_std)
    if not math.isfinite(sd) or sd < 0.0:
        raise ValueError("lidarsim: noise_std must be finite and >= 0, got %r" % (noise_std,))

    v_min_r, v_max_r = math.radians(v_min), math.radians(v_max)
    i = np.arange(nb, dtype=np.float64)
    elevations = v_max_r - (i + 0.5) * (v_max_r - v_min_r) / nb
    j = np.arange(na, dtype=np.float64)
    azimuths = (j + 0.5) / na * _TWO_PI - np.pi
    return {
        "n_beams": nb, "n_az": na, "v_fov_deg": (v_min, v_max), "azimuth_res_deg": res,
        "range_min": r_min, "range_max": r_max, "noise_std": sd,
        "elevations": elevations, "azimuths": azimuths,
    }


def _ray_dirs(spec) -> np.ndarray:
    """センサ座標のレイ方向 (n_beams, n_az, 3)(単位ベクトル)。"""
    e = np.asarray(spec["elevations"], np.float64)[:, None]
    a = np.asarray(spec["azimuths"], np.float64)[None, :]
    ce = np.cos(e)
    shape = (e.shape[0], a.shape[1])
    return np.stack([ce * np.cos(a), ce * np.sin(a), np.broadcast_to(np.sin(e), shape)], axis=2)


# ---- 加速: 三角形の角度区間 → (beam, 列) のビン ---------------------------------------------------
def _edge_elevation_extrema(u1: np.ndarray, u2: np.ndarray):
    """単位方向 u1→u2 の短弧(大円)上の仰角の最大/最小、および辺が原点を通る(反対方向)フラグ。

    大円の最高点 ĥ ∝ ẑ − (ẑ·n̂)n̂(n̂ = u1×u2 の単位化)が短弧の内側にあるとき、その仰角
    asin(|ẑ − (ẑ·n̂)n̂|) が弧の最大。最低点は −ĥ。内側判定は (u1×ĥ)·n̂ ≥ 0 かつ (ĥ×u2)·n̂ ≥ 0。
    """
    n = np.cross(u1, u2)
    nn = np.linalg.norm(n, axis=1)
    ok = nn > 1e-12
    nh = n / np.where(ok, nn, 1.0)[:, None]
    h = _Z_HAT[None, :] - nh[:, 2:3] * nh
    hz = np.linalg.norm(h, axis=1)
    okh = ok & (hz > 1e-12)
    hh = h / np.where(okh, hz, 1.0)[:, None]
    el_top = np.arcsin(np.clip(hz, -1.0, 1.0))

    s1 = np.einsum("ij,ij->i", np.cross(u1, hh), nh)
    s2 = np.einsum("ij,ij->i", np.cross(hh, u2), nh)
    top = okh & (s1 >= -1e-12) & (s2 >= -1e-12)
    s1m = np.einsum("ij,ij->i", np.cross(u1, -hh), nh)
    s2m = np.einsum("ij,ij->i", np.cross(-hh, u2), nh)
    bot = okh & (s1m >= -1e-12) & (s2m >= -1e-12)
    anti = (~ok) & (np.einsum("ij,ij->i", u1, u2) < 0.0)
    return top, bot, el_top, anti


def _triangle_bins(Vs: np.ndarray, F: np.ndarray, spec) -> tuple:
    """各三角形の候補 (beam 行区間, 列区間) エントリを作る。

    返り値 ``(tri, r0, r1, c0, c1)``(各 (E,) int)。wrap を跨ぐ三角形は 2 エントリ。
    視野外・退化・``range_max`` より遠い平面の三角形はエントリなし。
    """
    nb, na = int(spec["n_beams"]), int(spec["n_az"])
    v_min, v_max = (math.radians(float(x)) for x in spec["v_fov_deg"])
    de = (v_max - v_min) / nb
    da = _TWO_PI / na
    r_max = float(spec["range_max"])

    P = Vs[F]                                            # (M, 3, 3)
    M = P.shape[0]
    # 退化三角形(面積 0)と、原点からの平面距離が range_max を超えるものは捨てる。
    e1 = P[:, 1] - P[:, 0]
    e2 = P[:, 2] - P[:, 0]
    nrm = np.cross(e1, e2)
    nlen = np.linalg.norm(nrm, axis=1)
    alive = nlen > _DET_EPS
    with np.errstate(invalid="ignore", divide="ignore"):
        plane_dist = np.abs(np.einsum("ij,ij->i", nrm, P[:, 0])) / np.where(alive, nlen, 1.0)
    alive &= plane_dist <= r_max

    r = np.linalg.norm(P, axis=2)                        # (M, 3)
    degenerate = (r < _ORIGIN_EPS).any(axis=1)
    U = P / np.where(r > 0.0, r, 1.0)[:, :, None]

    # 方位角の最小被覆弧
    az = np.arctan2(P[:, :, 1], P[:, :, 0])              # (M, 3) in (-π, π]
    a_sorted = np.sort(az, axis=1)
    gaps = np.concatenate([np.diff(a_sorted, axis=1),
                           (a_sorted[:, 0] + _TWO_PI - a_sorted[:, 2])[:, None]], axis=1)
    kmax = np.argmax(gaps, axis=1)
    idx = np.arange(M)
    span = _TWO_PI - gaps[idx, kmax]
    start = a_sorted[idx, (kmax + 1) % 3]
    full = degenerate | (span >= math.pi - 1e-9)

    # 仰角区間(頂点 + 辺の極値)
    el_v = np.arcsin(np.clip(U[:, :, 2], -1.0, 1.0))
    emin = el_v.min(axis=1)
    emax = el_v.max(axis=1)
    for a, b in ((0, 1), (1, 2), (2, 0)):
        top, bot, el_top, anti = _edge_elevation_extrema(U[:, a], U[:, b])
        emax = np.where(top, np.maximum(emax, el_top), emax)
        emin = np.where(bot, np.minimum(emin, -el_top), emin)
        full |= anti

    # 行区間(保守的に floor / ceil で 1 セルずつ広げる)
    r0f = np.floor((v_max - emax) / de - 0.5)
    r1f = np.ceil((v_max - emin) / de - 0.5)
    in_fov = (r1f >= 0) & (r0f <= nb - 1)
    r0 = np.clip(r0f, 0, nb - 1).astype(np.int64)
    r1 = np.clip(r1f, 0, nb - 1).astype(np.int64)
    r0 = np.where(full, 0, r0)
    r1 = np.where(full, nb - 1, r1)
    keep = alive & (in_fov | full)

    # 列区間(wrap を跨げば 2 エントリ)
    c0f = np.floor((start + math.pi) / da - 0.5)
    c1f = np.ceil((start + span + math.pi) / da - 0.5)
    all_cols = full | (c1f - c0f + 1 >= na)
    c0 = c0f.astype(np.int64)
    c1 = c1f.astype(np.int64)

    tri_list, r0_list, r1_list, c0_list, c1_list = [], [], [], [], []

    sel = keep & all_cols
    tri_list.append(idx[sel]); r0_list.append(r0[sel]); r1_list.append(r1[sel])
    c0_list.append(np.zeros(int(sel.sum()), np.int64)); c1_list.append(np.full(int(sel.sum()), na - 1, np.int64))

    part = keep & ~all_cols
    neg = part & (c0 < 0)
    over = part & (c1 >= na) & ~neg
    plain = part & ~neg & ~over

    tri_list.append(idx[plain]); r0_list.append(r0[plain]); r1_list.append(r1[plain])
    c0_list.append(c0[plain]); c1_list.append(c1[plain])

    for m, lo_a, hi_a, lo_b, hi_b in (
        (neg, c0 + na, np.full(M, na - 1), np.zeros(M, np.int64), c1),
        (over, c0, np.full(M, na - 1), np.zeros(M, np.int64), c1 - na),
    ):
        for lo, hi in ((lo_a, hi_a), (lo_b, hi_b)):
            tri_list.append(idx[m]); r0_list.append(r0[m]); r1_list.append(r1[m])
            c0_list.append(np.clip(lo[m], 0, na - 1)); c1_list.append(np.clip(hi[m], 0, na - 1))

    tri = np.concatenate(tri_list)
    return (tri, np.concatenate(r0_list), np.concatenate(r1_list),
            np.concatenate(c0_list), np.concatenate(c1_list))


# ---- Möller–Trumbore(ベクトル化) --------------------------------------------------------------------
def _moller_trumbore(D: np.ndarray, v0: np.ndarray, v1: np.ndarray, v2: np.ndarray):
    """原点から方向 D のレイと三角形 (v0, v1, v2) の交差(両面)。``(hit (K,) bool, t (K,))``。"""
    e1 = v1 - v0
    e2 = v2 - v0
    pvec = np.cross(D, e2)
    det = np.einsum("ij,ij->i", e1, pvec)
    ok = np.abs(det) > _DET_EPS
    inv = 1.0 / np.where(ok, det, 1.0)
    tvec = -v0
    u = np.einsum("ij,ij->i", tvec, pvec) * inv
    ok &= (u >= -_BARY_EPS) & (u <= 1.0 + _BARY_EPS)
    qvec = np.cross(tvec, e1)
    v = np.einsum("ij,ij->i", D, qvec) * inv
    ok &= (v >= -_BARY_EPS) & (u + v <= 1.0 + _BARY_EPS)
    t = np.einsum("ij,ij->i", e2, qvec) * inv
    ok &= t > 0.0
    return ok, t


# ---- スキャン ---------------------------------------------------------------------------------------
def lidar_scan(V, F, spec, T_sensor, *, labels=None, seed: int = 0) -> dict:
    """メッシュ世界 ``(V, F)`` に姿勢 ``T_sensor``(world ← sensor)の LiDAR を 1 スイープ撃つ。

    - ``V`` (N,3) float / ``F`` (M,3) int: 三角形メッシュ(空・非 (N,3)・非有限・範囲外の面番号は
      ``ValueError``)。
    - ``spec``: :func:`lidar_spec` の dict。
    - ``T_sensor``: 4×4 同次行列(world ← sensor)。センサ座標は x=前, y=左, z=上。
    - ``labels``: 面ごとの int ラベル (M,) または None(None なら当たったセルのラベルは 0)。
    - ``seed``: ノイズの乱数種(``noise_std == 0`` なら乱数を一切引かず、ビット単位で決定的)。

    返り値の dict:
    ``points`` (K,3) **世界座標**の反射点(行優先: beam 0 の列 0 から)/ ``ranges`` (n_beams, n_az)
    [m](0 = 無返答)/ ``hit_face`` (n_beams, n_az) int(−1 = 無し)/ ``labels`` (n_beams, n_az) int
    (−1 = 無し)/ ``beam`` (K,) int / ``col`` (K,) int / ``n_hits`` int。
    最近接の面が ``range_min`` 未満または ``range_max`` 超なら無返答(奥の面へ抜けない)。ノイズは
    無ノイズ距離で返答の有無を決めた後、``ranges`` と ``points`` に足す。
    """
    Vv, Ff = _mesh_arrays(V, F)
    spec = _check_spec(spec)
    T = _check_pose(T_sensor)
    if labels is not None:
        lab = np.asarray(labels)
        if lab.ndim != 1 or lab.shape[0] != Ff.shape[0]:
            raise ValueError("lidarsim: labels must be (M,) with M = number of faces %d, got %r"
                             % (Ff.shape[0], (lab.shape,)))
        lab = lab.astype(np.int64)
    else:
        lab = None

    nb, na = int(spec["n_beams"]), int(spec["n_az"])
    R = T[:3, :3]
    t_w = T[:3, 3]
    Vs = (Vv - t_w[None, :]) @ R                        # world → sensor: Rᵀ (p − t)

    dirs = _ray_dirs(spec).reshape(-1, 3)               # (nb*na, 3)
    tri, r0, r1, c0, c1 = _triangle_bins(Vs, Ff, spec)
    P = Vs[Ff]

    best = np.full(nb * na, np.inf, dtype=np.float64)
    hit_ray, hit_t, hit_tri = [], [], []
    if tri.size:
        width = c1 - c0 + 1
        count = (r1 - r0 + 1) * width
        cum = np.concatenate([[0], np.cumsum(count)])
        total = int(cum[-1])
        for s in range(0, total, _PAIR_CHUNK):
            p = np.arange(s, min(s + _PAIR_CHUNK, total), dtype=np.int64)
            k = np.searchsorted(cum, p, side="right") - 1
            off = p - cum[k]
            row = r0[k] + off // width[k]
            col = c0[k] + off % width[k]
            ray = row * na + col
            tk = tri[k]
            Pk = P[tk]
            ok, tt = _moller_trumbore(dirs[ray], Pk[:, 0], Pk[:, 1], Pk[:, 2])
            if ok.any():
                hit_ray.append(ray[ok]); hit_t.append(tt[ok]); hit_tri.append(tk[ok])

    ranges = np.zeros(nb * na, dtype=np.float64)
    hit_face = np.full(nb * na, -1, dtype=np.int64)
    if hit_ray:
        ray_all = np.concatenate(hit_ray)
        t_all = np.concatenate(hit_t)
        tri_all = np.concatenate(hit_tri)
        np.minimum.at(best, ray_all, t_all)
        nearest = t_all == best[ray_all]
        face_best = np.full(nb * na, np.iinfo(np.int64).max, dtype=np.int64)
        np.minimum.at(face_best, ray_all[nearest], tri_all[nearest])
        valid = np.isfinite(best) & (best >= float(spec["range_min"])) & (best <= float(spec["range_max"]))
        ranges[valid] = best[valid]
        hit_face[valid] = face_best[valid]

    valid = ranges > 0.0
    flat_idx = np.flatnonzero(valid)
    sd = float(spec["noise_std"])
    if sd > 0.0 and flat_idx.size:
        rng = np.random.default_rng(int(seed))
        ranges[flat_idx] = ranges[flat_idx] + rng.normal(0.0, sd, size=flat_idx.size)

    beam = flat_idx // na
    col = flat_idx % na
    pts_s = dirs[flat_idx] * ranges[flat_idx][:, None]
    points = pts_s @ R.T + t_w[None, :]                  # sensor → world

    lab_img = np.full(nb * na, -1, dtype=np.int64)
    if flat_idx.size:
        lab_img[flat_idx] = 0 if lab is None else lab[hit_face[flat_idx]]

    return {
        "points": points,
        "ranges": ranges.reshape(nb, na),
        "hit_face": hit_face.reshape(nb, na),
        "labels": lab_img.reshape(nb, na),
        "beam": beam.astype(np.int64),
        "col": col.astype(np.int64),
        "n_hits": int(flat_idx.size),
    }


def lidar_points_sensor_frame(scan: dict, T_sensor) -> np.ndarray:
    """:func:`lidar_scan` の世界座標 ``points`` をセンサ座標 (K,3) に戻す(``Rᵀ (p − t)``)。"""
    if not isinstance(scan, dict) or "points" not in scan:
        raise ValueError("lidarsim: scan must be the dict returned by lidar_scan()")
    T = _check_pose(T_sensor)
    P = np.asarray(scan["points"], np.float64)
    if P.size == 0:
        return np.zeros((0, 3), np.float64)
    P = _finite_points(P, "scan points")
    return (P - T[:3, 3][None, :]) @ T[:3, :3]


def lidar_range_image_to_points(ranges, spec) -> np.ndarray:
    """レンジ画像 (n_beams, n_az) → センサ座標の点 (K,3)。``spherical_proj.unproject_spherical`` に委譲。

    ``spec`` の ``v_fov_deg`` をそのまま渡す(自前の逆投影は書かない: 行/列規約の正本は spherical_proj)。
    形が ``spec`` の (n_beams, n_az) と違えば ``ValueError``。
    """
    spec = _check_spec(spec)
    Rimg = np.asarray(ranges, np.float64)
    if Rimg.shape != (int(spec["n_beams"]), int(spec["n_az"])):
        raise ValueError("lidarsim: ranges must be (n_beams, n_az) = %r, got %r"
                         % ((int(spec["n_beams"]), int(spec["n_az"])), (Rimg.shape,)))
    return spherical_proj.unproject_spherical(Rimg, v_fov=spec["v_fov_deg"])


# ---- 閉形式の第 2 実装 -------------------------------------------------------------------------------
def _origin_dirs(origin, dirs):
    O = np.asarray(origin, np.float64)
    if O.shape != (3,) or not np.isfinite(O).all():
        raise ValueError("lidarsim: origin must be a finite (3,) vector")
    D = np.asarray(dirs, np.float64)
    if D.ndim < 1 or D.shape[-1] != 3 or not np.isfinite(D).all():
        raise ValueError("lidarsim: dirs must be (..., 3) finite")
    return O, D


def ray_plane_range(origin, dirs, plane) -> np.ndarray:
    """原点 ``origin`` から方向 ``dirs (...,3)`` のレイが平面 ``ax+by+cz+d=0`` に当たるまでの距離。

    閉形式 ``t = −(n·O + d)/(n·D)``、距離は ``t·‖D‖``。前方(t > 0)に当たらない・平行なら ``inf``。
    法線がゼロなら ``ValueError``。
    """
    O, D = _origin_dirs(origin, dirs)
    pl = np.asarray(plane, np.float64)
    if pl.shape != (4,) or not np.isfinite(pl).all() or np.linalg.norm(pl[:3]) < 1e-15:
        raise ValueError("lidarsim: plane must be finite (a, b, c, d) with a nonzero normal")
    n, d = pl[:3], pl[3]
    denom = D @ n
    num = -(O @ n + d)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(np.abs(denom) > 1e-300, num / denom, np.inf)
    out = np.where(t > 0.0, t * np.linalg.norm(D, axis=-1), np.inf)
    return np.asarray(out, np.float64)


def ray_box_ranges(origin, dirs, box) -> np.ndarray:
    """原点 ``origin`` から方向 ``dirs (...,3)`` のレイが軸平行箱に入るまでの距離(slab 法)。

    ``box = (xmin, ymin, zmin, xmax, ymax, zmax)``。外れは ``inf``。原点が箱の内側なら前方で最初に
    当たる面(出口)までの距離。距離は ``t·‖D‖``。``min < max`` でない箱は ``ValueError``。
    """
    O, D = _origin_dirs(origin, dirs)
    b = np.asarray(box, np.float64)
    if b.shape != (6,) or not np.isfinite(b).all() or not np.all(b[:3] < b[3:]):
        raise ValueError("lidarsim: box must be finite (xmin, ymin, zmin, xmax, ymax, zmax) with min < max")
    lo, hi = b[:3], b[3:]
    t_near = np.full(D.shape[:-1], -np.inf)
    t_far = np.full(D.shape[:-1], np.inf)
    miss = np.zeros(D.shape[:-1], dtype=bool)
    for k in range(3):
        dk = D[..., k]
        par = dk == 0.0
        inside = (O[k] >= lo[k]) & (O[k] <= hi[k])
        miss |= par & ~inside
        with np.errstate(divide="ignore", invalid="ignore"):
            t1 = (lo[k] - O[k]) / dk
            t2 = (hi[k] - O[k]) / dk
        tmin = np.where(par, -np.inf, np.minimum(t1, t2))
        tmax = np.where(par, np.inf, np.maximum(t1, t2))
        t_near = np.maximum(t_near, tmin)
        t_far = np.minimum(t_far, tmax)
    hit = ~miss & (t_far >= t_near) & (t_far >= 0.0)
    t = np.where(t_near >= 0.0, t_near, t_far)
    out = np.where(hit, t * np.linalg.norm(D, axis=-1), np.inf)
    return np.asarray(out, np.float64)
