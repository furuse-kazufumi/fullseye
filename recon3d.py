"""recon3d — 点群(point cloud)から**直接**の表面再構成(surface reconstruction)。

差別化点: match3d.py の marching cubes は **voxel 入力**(すでに密度場がある前提)なのに対し、
ここは **生の点群 (N,3) から直接** メッシュ/境界を起こす。橋渡しは 2 系統:

1. ``poisson_lite`` — スクリーンド Poisson(screened Poisson)の**軽量近似**。点群を voxel 格子へ
   splat し、占有(occupancy)か、法線があれば向き付き点からの内外指標(winding number、
   Barill+2018)をガウス平滑して等値面場を作り、marching cubes で等値面メッシュ化する。
   厳密な Poisson 方程式(Kazhdan+2013)は解かない(重い線形系)ため、あくまで近似である。
2. ``alpha_shape_*`` — alpha shapes(Edelsbrunner+1983)。Delaunay 四面体分割の外接球半径が
   1/alpha 未満の四面体だけ残す(alpha-complex)ことで、凸包を「削って」実形状の境界を得る。
   テンプレート不要・穴/凹みを表現でき、疎な点群の**境界抽出**に向く。

いずれも numpy in / numpy out。scipy(spatial/ndimage/signal)と skimage.measure に依存。
エラー処理は省略しない(点数不足・縮退・薄い占有を明示メッセージで graceful に扱う)。
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.signal import fftconvolve
from scipy.spatial import Delaunay, cKDTree
from skimage.measure import marching_cubes


# ═══════════════════════════════════════════════════════════════════════════
# 共通ヘルパ: 点群 → voxel 格子座標(padding つき、等値面が境界で切れないように)
# ═══════════════════════════════════════════════════════════════════════════
def _as_points(points):
    """入力を (N,3) float64 に正規化。形が違えば明示エラー。"""
    P = np.asarray(points, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"points は (N,3) の点群が必要です(受領: shape={P.shape})")
    if not np.isfinite(P).all():
        raise ValueError("points に NaN/Inf が含まれています")
    return P


def _grid_coords(P, size, pad_vox):
    """点群 (N,3) を [pad_vox, size-1-pad_vox]³ の連続格子座標へ写す。

    padding を挟むことで、平滑された等値面が格子端で切れず閉じる。縮退軸(span≈0)は
    定数座標に落とし、ゼロ割を避ける。返り値 (gp(N,3), lo(3,), span(3,), inner)。
    span は**元の**幅(逆写像に使う。縮退軸は 0 のまま=座標を lo に固定)。
    """
    lo = P.min(0)
    hi = P.max(0)
    span = hi - lo                                  # 元の幅(逆写像用、縮退軸は 0)
    span_safe = np.where(span > 1e-12, span, 1.0)   # 正規化用(ゼロ割回避)
    inner = (size - 1) - 2 * pad_vox
    if inner <= 0:
        raise ValueError(
            f"size={size} が pad_vox={pad_vox}(≈3σ)に対して小さすぎます。"
            "size を大きく、または sigma を小さくしてください。")
    gp = pad_vox + (P - lo) / span_safe * inner
    return gp, lo, span, inner


# ═══════════════════════════════════════════════════════════════════════════
# 1. poisson_lite: 点群 → 等値面メッシュ(スクリーンド Poisson の軽量近似)
# ═══════════════════════════════════════════════════════════════════════════
def _winding_indicator(gp, normals, size, sigma, idx):
    """向き付き点(oriented points)→ 内外指標場 [0,1]。generalized winding number の格子版。

    winding number w(x) = (1/4π) Σ_i n_i·(p_i − x)/|p_i − x|³ は、閉じた向き付き曲面の
    **内側で ≈1、外側で ≈0** を返す(Barill+2018 "Fast Winding Numbers")。これは畳み込み
    w = Σ_ch (splat(n_ch) ∗ K_ch) で書ける(K(u) = −u/|u|³)。表面のみサンプルされた点群でも
    内部を正しく埋められる(占有 splat では内部が空になり内外を分けられない)ためここで使う。

    軽量近似ゆえ: 単位法線を面積重みなしで splat するので内側の値は 1 ちょうどではなく
    サンプル密度依存の定数になる。よって winding 場をパーセンタイルで [0,1] へ正規化してから
    iso 抜きする。fftconvolve 'same' の偶数格子パリティで最大 ~0.5voxel の等値面ずれが乗り得る。
    """
    n = np.asarray(normals, dtype=np.float64)
    if n.shape != gp.shape:
        raise ValueError(
            f"normals は points と同形 (N,3) が必要です(points={gp.shape}, normals={n.shape})")
    if not np.isfinite(n).all():
        raise ValueError("normals に NaN/Inf が含まれています")
    nn = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)   # 単位化

    # 法線を最近傍 voxel へ splat(3 チャンネルのベクトル場)
    S = [np.zeros((size, size, size), dtype=np.float64) for _ in range(3)]
    ijk = (idx[:, 0], idx[:, 1], idx[:, 2])
    for c in range(3):
        np.add.at(S[c], ijk, nn[:, c])

    # winding カーネル K(u) = −u/|u|³(中心=原点は特異点 → 0)
    c0 = size // 2
    ax = np.arange(size) - c0
    vz, vy, vx = np.meshgrid(ax, ax, ax, indexing="ij")
    r3 = np.power((vz * vz + vy * vy + vx * vx).astype(np.float64), 1.5)
    r3[c0, c0, c0] = np.inf
    Kz, Ky, Kx = -vz / r3, -vy / r3, -vx / r3

    w = (fftconvolve(S[0], Kz, mode="same")
         + fftconvolve(S[1], Ky, mode="same")
         + fftconvolve(S[2], Kx, mode="same")) / (4.0 * np.pi)
    w = gaussian_filter(w, sigma)

    lo_ref = np.percentile(w, 5.0)
    hi_ref = np.percentile(w, 95.0)
    if hi_ref - lo_ref < 1e-12:
        raise ValueError("法線指標場が縮退しています(有効な内外差がありません)")
    field = np.clip((w - lo_ref) / (hi_ref - lo_ref), 0.0, 1.0)

    # 自動向き付け: 格子中心(通常は物体内部)が端(通常は外部)より高くなるよう反転
    if field[c0, c0, c0] < field[0, 0, 0]:
        field = 1.0 - field
    return field


def poisson_lite(points, size=64, sigma=1.0, iso=0.5, normals=None):
    """点群 (N,3) → (vertices(V,3), faces(F,3)) の表面メッシュ(スクリーンド Poisson 軽量近似)。

    点群を size³ の voxel 格子へ splat し、等値面場を作って marching cubes で三角形メッシュ化する。
    出力頂点は入力点群と同じ**世界座標**(bbox から逆写像)。bounds は点群 bbox(+σ 依存の padding)。

    2 モード:
      * ``normals is None``: **占有(occupancy)** をガウス平滑した密度場を [0,1] 正規化し、
        ``iso``(既定 0.5 = 密度ピークの中腹)で等値面抜き。表面のみの点群では等値面が薄い殻に
        沿って通るため、頂点は表面近傍に載る(内外の充填はしない)。
      * ``normals`` 指定: 向き付き点の **winding number** で内外指標場を作りガウス平滑、``iso``
        (既定 0.5)で表面抜き。表面のみサンプルでも内部を埋めて閉曲面を得られる。

    Parameters
    ----------
    points : array_like (N,3)
        入力点群。
    size : int
        voxel 格子の一辺(既定 64)。大きいほど精細だが O(size³)。
    sigma : float
        ガウス平滑の標準偏差(voxel 単位、既定 1.0)。padding は ⌈3σ⌉+2 voxel を自動確保。
    iso : float
        等値面レベル。正規化場 [0,1] 上の値(既定 0.5)。
    normals : array_like (N,3) or None
        点法線。与えると winding number モード、None なら占有モード。

    Returns
    -------
    vertices : numpy.ndarray (V,3) float64
        世界座標の頂点。
    faces : numpy.ndarray (F,3) int64
        三角形の頂点インデックス(vertices を参照)。

    Raises
    ------
    ValueError
        点数不足(<4)、size が小さすぎる、占有/指標場が薄く iso が場の値域外、など。
    """
    P = _as_points(points)
    if len(P) < 4:
        raise ValueError(f"点群が少なすぎます(表面再構成には >=4 点、受領 {len(P)})")
    if size < 8:
        raise ValueError(f"size={size} が小さすぎます(>=8 推奨)")
    if sigma <= 0:
        raise ValueError("sigma は正である必要があります")

    pad_vox = int(np.ceil(3.0 * sigma)) + 2
    gp, lo, span, inner = _grid_coords(P, size, pad_vox)
    idx = np.clip(np.rint(gp).astype(np.int64), 0, size - 1)      # 最近傍 voxel

    if normals is None:
        grid = np.zeros((size, size, size), dtype=np.float64)
        np.add.at(grid, (idx[:, 0], idx[:, 1], idx[:, 2]), 1.0)   # 占有 splat
        grid = gaussian_filter(grid, sigma)
        mx = float(grid.max())
        if mx <= 0.0:
            raise ValueError("占有場が空です(点が格子に載っていません)")
        field = grid / mx
    else:
        field = _winding_indicator(gp, normals, size, sigma, idx)

    level = float(iso)
    fmin, fmax = float(field.min()), float(field.max())
    if not (fmin < level < fmax):
        raise ValueError(
            f"iso={level} が等値面場の値域 ({fmin:.4g}, {fmax:.4g}) の外です。"
            "占有/指標が薄い、または iso が不適切です。iso を値域内に調整してください。")

    try:
        verts, faces, _, _ = marching_cubes(field, level=level)
    except (RuntimeError, ValueError) as e:              # 等値面が見つからない等
        raise ValueError(f"marching cubes による等値面抽出に失敗: {e}")

    # 格子座標 → 世界座標(縮退軸は span=0 で lo に固定)
    world = lo[None, :] + (verts - pad_vox) / inner * span[None, :]
    return world.astype(np.float64), faces.astype(np.int64)


# ═══════════════════════════════════════════════════════════════════════════
# 2-3. alpha shapes: Delaunay 四面体分割 → 外接球半径で剪定 → 境界三角形
# ═══════════════════════════════════════════════════════════════════════════
def _circumradii(P, simplices):
    """各四面体の外接球半径(circumradius)。中心は等距離条件の 3x3 線形系で解く。

    2·(p_i − p_0)·c = |p_i|² − |p_0|²(i=1,2,3)を解いて中心 c、R=|c − p_0|。
    退化(共面 → 係数行列が特異)四面体は R=+∞ とし、alpha 剪定で自然に除外する。
    返り値 R(M,)。
    """
    T = P[simplices]                                    # (M,4,3)
    p0 = T[:, 0]
    A = 2.0 * (T[:, 1:] - p0[:, None, :])               # (M,3,3)
    rhs = (T[:, 1:] ** 2).sum(2) - (p0 ** 2).sum(1)[:, None]   # (M,3)
    det = np.linalg.det(A)
    R = np.full(len(T), np.inf, dtype=np.float64)
    good = np.abs(det) > 1e-12
    if good.any():
        centers = np.linalg.solve(A[good], rhs[good])   # バッチ 3x3 solve
        R[good] = np.linalg.norm(centers - p0[good], axis=1)
    return R


def _alpha_boundary_faces(P, alpha):
    """alpha-complex の**境界三角形**(ちょうど 1 個の残存四面体に属す面)を points index で返す。

    Delaunay 四面体のうち外接球半径 < 1/alpha を残し、その 4 面を数え上げて出現回数 1 の面
    (= 内部で共有されない外皮)を境界とする。返り値 (B,3) の頂点 index(points を参照)。
    """
    if alpha <= 0:
        raise ValueError("alpha は正である必要があります(1/alpha が半径しきい値)")
    if len(P) < 4:
        raise ValueError(f"Delaunay 四面体分割には >=4 点必要です(受領 {len(P)})")
    try:
        tri = Delaunay(P)
    except Exception as e:                              # 共面/共線などの縮退
        raise ValueError(f"Delaunay 分割に失敗しました(縮退した点群?): {e}")

    simp = tri.simplices                                # (M,4)
    if len(simp) == 0:
        return np.zeros((0, 3), dtype=np.int64)

    R = _circumradii(P, simp)
    keep = np.isfinite(R) & (R < 1.0 / alpha)
    kept = simp[keep]
    if len(kept) == 0:                                  # alpha 大きすぎて全除外
        return np.zeros((0, 3), dtype=np.int64)

    faces = np.concatenate([kept[:, [0, 1, 2]], kept[:, [0, 1, 3]],
                            kept[:, [0, 2, 3]], kept[:, [1, 2, 3]]], axis=0)
    fs = np.sort(faces, axis=1)                         # 面を正準化して数える
    uniq, counts = np.unique(fs, axis=0, return_counts=True)
    return uniq[counts == 1].astype(np.int64)          # 出現 1 回 = 境界面


def alpha_shape_boundary(points, alpha):
    """alpha shapes による**境界点インデックス**を返す(点群 → 境界点)。

    Delaunay 四面体分割の外接球半径 < 1/alpha の四面体の表面三角形(境界面)を集め、その頂点
    集合を境界点とする。中実(表面+内部)の点群から表面殻の点だけを抜き出す用途に向く。
    alpha を大きくすると許す半径 1/alpha が小さくなり、より密着した(細部を拾う)境界になる。

    Parameters
    ----------
    points : array_like (N,3)
    alpha : float
        正の実数。半径しきい値は 1/alpha。``estimate_alpha`` で目安を得られる。

    Returns
    -------
    boundary_point_indices : numpy.ndarray (K,) int64
        points に対する境界点の index(昇順・重複なし)。境界が無ければ空配列。
    """
    P = _as_points(points)
    boundary = _alpha_boundary_faces(P, alpha)
    if len(boundary) == 0:
        return np.zeros((0,), dtype=np.int64)
    return np.unique(boundary).astype(np.int64)


def alpha_shape_mesh(points, alpha):
    """alpha shapes による**表面三角形メッシュ**(点群 → (vertices, faces))。

    ``alpha_shape_boundary`` と同じ境界三角形を、使用頂点だけに詰め直したメッシュとして返す。
    voxel を介さず点群から直接張る表面。凹み/穴を保持できるのが marching cubes 系との差別化。

    Parameters
    ----------
    points : array_like (N,3)
    alpha : float
        正の実数(半径しきい値 1/alpha)。

    Returns
    -------
    vertices : numpy.ndarray (V,3) float64
        境界に使われた入力点(詰め直し済み)。
    faces : numpy.ndarray (F,3) int64
        vertices を参照する三角形インデックス。境界が無ければ (0,3)/(0,3)。
    """
    P = _as_points(points)
    boundary = _alpha_boundary_faces(P, alpha)
    if len(boundary) == 0:
        return np.zeros((0, 3), dtype=np.float64), np.zeros((0, 3), dtype=np.int64)
    used = np.unique(boundary)
    remap = -np.ones(len(P), dtype=np.int64)
    remap[used] = np.arange(len(used))
    verts = P[used]
    faces = remap[boundary]
    return verts.astype(np.float64), faces.astype(np.int64)


# ═══════════════════════════════════════════════════════════════════════════
# 4. estimate_alpha: 最近傍距離中央値ベースの推奨 alpha
# ═══════════════════════════════════════════════════════════════════════════
def estimate_alpha(points):
    """点群のスケールから推奨 alpha を返す(最近傍距離の中央値ベース)。

    各点の最近傍距離の中央値 ``m`` を求め、半径しきい値 1/alpha ≈ 2m(隣接間隔の約 2 倍まで
    許す)となるよう ``alpha = 1/(2m)`` を返す。これで表面付近の素性の良い四面体は残しつつ、
    大きく間延びした四面体(=凹み・外側)を切り落とせる。重複点は最近傍 0 になるため正の距離のみ使う。

    Parameters
    ----------
    points : array_like (N,3)

    Returns
    -------
    alpha : float
        正の有限値。
    """
    P = _as_points(points)
    if len(P) < 2:
        raise ValueError(f"最近傍距離の推定には >=2 点必要です(受領 {len(P)})")
    tree = cKDTree(P)
    d, _ = tree.query(P, k=2)                           # (N,2): 自分自身と最近傍
    nn = d[:, 1]
    nn = nn[nn > 0]                                     # 重複点(距離 0)を除外
    if len(nn) == 0:
        raise ValueError("有効な最近傍距離がありません(点が全て重複している可能性)")
    med = float(np.median(nn))
    return 1.0 / (2.0 * med)
