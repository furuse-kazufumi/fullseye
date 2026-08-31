# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""deform3d — 3D 非剛体・変形レジストレーション(点群 in / 点群 out)。

cv2 / HALCON は 2D の変形照合(可変形テンプレート・光学的流れ)は持つが、**3D 点群の
非剛体位置合わせ**は手薄。ここを fullseye の差別化点として埋める。

提供する op:
    - ``tps_fit`` / ``tps_warp``     : 3D Thin-Plate-Spline(TPS)の当てはめと適用。
    - ``register_nonrigid``          : 非剛体 ICP(反復最近傍対応 → TPS 再当てはめ)。
    - ``register_cpd_rigid``         : Coherent Point Drift(CPD)剛体版(EM で軟対応)。

すべて numpy ``(N,3)`` を入出力とする。重い依存(torch 等)は使わず、
``scipy.spatial.cKDTree``(最近傍)と ``numpy.linalg``(線形代数)だけで完結する。

数学メモ(3D TPS):
    変形写像 f(x) = c + A·x + Σ_i w_i·U(‖x − p_i‖) を制御点対応から解く。
    3D の TPS(biharmonic)基底は U(r) = r。制御点 p_i(=移動側)を固定し、
    目標 v_i(=固定側)へ写す係数 (w, a=[c;A]) を鞍点系
        [ K+λI   P ] [ w ]   [ v ]
        [ P^T    0 ] [ a ] = [ 0 ]
    から求める。K_ij = U(‖p_i − p_j‖)、P_i = [1, p_i]。λ は平滑化(0 で厳密内挿)。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "tps_kernel",
    "tps_fit",
    "tps_warp",
    "register_nonrigid",
    "register_cpd_rigid",
]


# --------------------------------------------------------------------------- #
# 入力正規化ヘルパ                                                            #
# --------------------------------------------------------------------------- #
def _as_points(a, name="points"):
    """array-like を float64 の ``(N,3)`` 配列へ正規化する。

    長さ 3 の 1 次元入力は単一点として ``(1,3)`` に昇格する。形状が不正なら
    ``ValueError`` を送出する(型チェックだけで済ませず実際の次元を検証)。
    """
    arr = np.asarray(a, dtype=np.float64)
    if arr.ndim == 1:
        if arr.shape[0] != 3:
            raise ValueError(f"{name} must be a 1D array of length 3, or (N,3) "
                             f"(got: shape={arr.shape})")
        arr = arr.reshape(1, 3)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(f"{name} must have shape (N,3) (got: shape={arr.shape})")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contains non-finite values (NaN/Inf)")
    return arr


def _pairwise_dist(a, b):
    """``a`` (M,3) と ``b`` (N,3) の総当たりユークリッド距離 (M,N) を返す。

    ``scipy.spatial.distance.cdist`` があれば使い、無ければ numpy broadcasting で
    計算する(graceful degradation)。
    """
    try:
        from scipy.spatial.distance import cdist
        return cdist(a, b, metric="euclidean")
    except Exception:  # scipy が無い/失敗 → numpy にフォールバック
        diff = a[:, None, :] - b[None, :, :]
        d2 = np.einsum("mnk,mnk->mn", diff, diff)
        return np.sqrt(np.maximum(d2, 0.0))


# --------------------------------------------------------------------------- #
# Thin-Plate-Spline(3D)                                                      #
# --------------------------------------------------------------------------- #

#: tps_fit の制御点数上限。TPS は (K+4)² の密行列を組んで lstsq する O(K³) なので
#: K は暗黙に「数千まで」の前提がある。上限なしだと点群をそのまま渡した事故で
#: 実質ハングする(連鎖ファザー wave-4 実測: K≈4 万で 12GB/数十分)。上限は
#: fail-closed(黙って間引かず ValueError で subsample を促す)。10,000 で
#: 行列 ~800MB・数十秒が上限になる。
TPS_MAX_CTRL = 10_000

#: tps_warp のチャンク幅(点数)。カーネル評価 (M,K) を M 方向に分割して
#: メモリを チャンク×K に有界化する(結果は一括評価とビット一致)。
_TPS_WARP_CHUNK = 65_536

#: register_cpd_rigid の N×M 上限(密な責務行列を EM 毎反復で組むため)。
#: 25M ペア ≈ 配列 1 本 200MB。同種の暗黙前提を fail-closed で明示する。
CPD_MAX_PAIRS = 25_000_000


def tps_kernel(r):
    """3D TPS の放射基底関数 U(r) = r を返す(要素ごと)。

    3 次元の thin-plate(biharmonic)Green 関数は U(r) = r。2D の r²·log r とは
    異なり原点で特異性を持たないため、制御点が一致(r=0)しても安定。
    """
    return np.asarray(r, dtype=np.float64)


def tps_fit(src_ctrl, dst_ctrl, lam=0.0):
    """3D Thin-Plate-Spline を制御点対応から当てはめる。

    移動側の制御点 ``src_ctrl`` を固定側 ``dst_ctrl`` へ写す TPS 係数を、鞍点系
    を最小二乗(``numpy.linalg.lstsq``)で解いて求める。λ=0 なら制御点上で厳密に
    内挿(``tps_warp(model, src_ctrl) == dst_ctrl``)、λ>0 で平滑化する。

    引数:
        src_ctrl: (K,3) 制御点(変形の始点、TPS のカーネル中心 p_i)。
        dst_ctrl: (K,3) 対応する目標点(変形の終点 v_i)。
        lam: 正則化係数 λ≥0。カーネル行列 K の対角へ λ を加える。大きいほど
            変形は滑らか(制御点への当てはめは緩む)。

    返り値:
        model: dict。キーは
            "ctrl" (K,3) カーネル中心 p_i、
            "w"    (K,3) 非線形(曲げ)係数、
            "a"    (4,3) アフィン係数([平行移動; 線形部]、a[0]=c, a[1:4]=Aᵀ)、
            "lam"  使用した λ。

    例外:
        ValueError: 形状不一致、制御点数不足、非有限値。
    """
    p = _as_points(src_ctrl, "src_ctrl")
    v = _as_points(dst_ctrl, "dst_ctrl")
    if p.shape[0] != v.shape[0]:
        raise ValueError(f"src_ctrl and dst_ctrl have mismatched point counts "
                         f"({p.shape[0]} vs {v.shape[0]})")
    n = p.shape[0]
    if n < 4:
        # 3D のアフィン部(4 係数)を決めるには最低 4 点必要。
        raise ValueError(f"3D TPS needs at least 4 control points (got: {n})")
    if n > TPS_MAX_CTRL:
        raise ValueError(
            f"tps_fit got {n} control points; the dense (K+4)^2 system is "
            f"O(K^3) and impractical beyond TPS_MAX_CTRL={TPS_MAX_CTRL}. "
            f"Subsample the correspondences first (e.g. random choice or "
            f"farthest_point_sampling) — TPS needs only a sparse set of "
            f"control points to represent a smooth deformation.")
    if lam < 0:
        raise ValueError(f"lam must be non-negative (got: {lam})")

    # カーネル行列 K (n,n) と多項式部 P (n,4)
    K = tps_kernel(_pairwise_dist(p, p))
    if lam > 0:
        K = K + lam * np.eye(n)
    P = np.hstack([np.ones((n, 1)), p])  # [1, x, y, z]

    # 鞍点系 L (n+4, n+4) と右辺 Y (n+4, 3)
    L = np.zeros((n + 4, n + 4), dtype=np.float64)
    L[:n, :n] = K
    L[:n, n:] = P
    L[n:, :n] = P.T
    Y = np.zeros((n + 4, 3), dtype=np.float64)
    Y[:n, :] = v

    # 数値安定のため最小二乗で解く(鞍点系の階数落ちにも最小ノルム解で対処)。
    params, *_ = np.linalg.lstsq(L, Y, rcond=None)
    w = params[:n, :]      # (n,3)
    a = params[n:, :]      # (4,3)
    return {"ctrl": p, "w": w, "a": a, "lam": float(lam)}


def tps_warp(model, points):
    """TPS モデルで点群を変形する。

    f(x) = [1,x,y,z]·a + Σ_i w_i·U(‖x − p_i‖) を評価する。

    引数:
        model: ``tps_fit`` が返した dict。
        points: (M,3)(または長さ3の1次元)。変形したい点群。

    返り値:
        (M,3) 変形後の点群(入力が1次元なら (3,) を返す)。

    例外:
        ValueError: model の形式不正、または points の形状不正。
    """
    for key in ("ctrl", "w", "a"):
        if key not in model:
            raise ValueError(f"model is missing required key '{key}' (pass the output of tps_fit)")
    ctrl = np.asarray(model["ctrl"], dtype=np.float64)
    w = np.asarray(model["w"], dtype=np.float64)
    a = np.asarray(model["a"], dtype=np.float64)

    was_1d = np.asarray(points).ndim == 1
    x = _as_points(points, "points")

    # (M,K) カーネルを一括で組むと M×K×8 バイト(M=数百万 × K=数千で数百 GB)に
    # なるため、M 方向にチャンクして評価する。数学は同一(行ごとに独立)。
    out = np.empty((x.shape[0], 3), dtype=np.float64)
    for s in range(0, x.shape[0], _TPS_WARP_CHUNK):
        blk = x[s:s + _TPS_WARP_CHUNK]
        U = tps_kernel(_pairwise_dist(blk, ctrl))         # (m,K)
        Phi = np.hstack([np.ones((blk.shape[0], 1)), blk])  # (m,4)
        out[s:s + _TPS_WARP_CHUNK] = Phi @ a + U @ w
    return out[0] if was_1d else out


# --------------------------------------------------------------------------- #
# 非剛体 ICP(TPS ベース)                                                     #
# --------------------------------------------------------------------------- #
def register_nonrigid(src, dst, iters=20, lam=1.0, k_smooth=None):
    """非剛体 ICP で ``src`` を ``dst`` へ寄せる。

    各反復で「現在の変形後 src」から ``dst`` への最近傍対応を張り直し、その対応を
    制御点対応(制御中心 = 元の src)として TPS を正則化つきで再当てはめし、src を
    変形する。対応が既知でなくとも滑らかな非線形変形を回復できる。

    実装上の要点(頑健性):
        - **スケール不変**: λ は dst の重心まわり RMS 半径に対する相対値として扱う
          (内部で λ_eff = λ·scale)。座標が 100 倍でも同じ λ が同じ挙動を与える。
        - **発散ガード**: 対応が曖昧だと単純な NN 反復は正のフィードバックで発散し得る。
          反復ごとの対応 RMS を監視し、**最良反復**(最小 RMS)の変形とモデルを返す。
          これにより悪い λ でも「初期より悪い」結果を返さない。
        - λ が大きいほど剛(変形が小さい)。既定 λ=1.0 は保守的(ほぼ剛)なので、
          大きな非線形変形を回復させたい場合は λ を小さく(例 0.01〜0.05)する。

    引数:
        src: (N,3) 移動側点群。
        dst: (M,3) 固定側(参照)点群。
        iters: 最大反復回数。
        lam: TPS 正則化 λ(スケール相対)。大きいほど変形が滑らか(外れ対応に頑健、
            当てはめは緩い)。小さいほど密着(細かい変形を回復)。
        k_smooth: None なら最近傍1点を目標にする(ハード対応)。整数を与えると
            ``dst`` 側の k 近傍の平均を目標にして対応を平滑化する(ノイズに頑健)。

    返り値:
        warped_src: (N,3) 最良反復での変形後 src。
        model: 対応する TPS モデル(制御中心 = 元 src、原座標系でそのまま
            ``tps_warp`` に渡せる)。1回も当てはめできなければ None。
        info: dict。"rms"(最良の対応 RMS)、"rms_init"(初期=恒等時の対応 RMS)、
              "rms_history"(list)、"iters"(実反復数)、"best_iter"、"converged"(bool)。

    例外:
        ValueError: 形状不正、点数不足、k_smooth 不正。
    """
    from scipy.spatial import cKDTree

    S0 = _as_points(src, "src")
    D = _as_points(dst, "dst")
    if S0.shape[0] < 4:
        raise ValueError(f"src needs at least 4 points (TPS control points) (got: {S0.shape[0]})")
    if D.shape[0] < 1:
        raise ValueError("dst is empty")
    if iters < 1:
        raise ValueError(f"iters must be >= 1 (got: {iters})")
    if k_smooth is not None:
        if not isinstance(k_smooth, (int, np.integer)) or k_smooth < 1:
            raise ValueError(f"k_smooth must be a positive integer or None (got: {k_smooth})")
        k_smooth = int(min(k_smooth, D.shape[0]))

    # スケール(dst の重心まわり RMS 半径)→ λ をスケール相対に。
    scale = float(np.sqrt(np.mean(np.sum((D - D.mean(axis=0)) ** 2, axis=1))))
    scale = max(scale, 1e-12)
    lam_eff = lam * scale

    tree = cKDTree(D)

    def _targets(moved):
        """変形後 src 各点に対する dst 側の目標点(ハード or k平均)を返す。"""
        if k_smooth is None or k_smooth == 1:
            _, idx = tree.query(moved, k=1)
            return D[idx]
        _, idx = tree.query(moved, k=k_smooth)
        return D[idx].mean(axis=1)  # idx:(N,k) → k 近傍平均

    warped = S0.copy()
    rms_history = []
    converged = False
    used = 0

    # 初期(恒等)の対応 RMS
    tgt0 = _targets(warped)
    rms_init = float(np.sqrt(np.mean(np.sum((warped - tgt0) ** 2, axis=1))))

    best_rms = np.inf
    best_warped = warped.copy()
    best_model = None
    best_iter = 0
    prev_rms = np.inf

    for it in range(iters):
        used = it + 1
        targets = _targets(warped)

        # 制御中心は「元の src」、目標は現在の最近傍。これで写像 src→dst を学習。
        model = tps_fit(S0, targets, lam=lam_eff)
        warped = tps_warp(model, S0)

        rms = float(np.sqrt(np.mean(np.sum((warped - targets) ** 2, axis=1))))
        rms_history.append(rms)

        # 発散ガード: 最良反復を保持。
        if rms < best_rms:
            best_rms = rms
            best_warped = warped.copy()
            best_model = model
            best_iter = used

        # 収束: 相対改善が十分小さくなったら打ち切り。
        if prev_rms < np.inf:
            rel = abs(prev_rms - rms) / max(prev_rms, 1e-12)
            if rel < 1e-5:
                converged = True
                break
        prev_rms = rms

    info = {
        "rms": float(best_rms),
        "rms_init": rms_init,
        "rms_history": rms_history,
        "iters": used,
        "best_iter": best_iter,
        "converged": converged,
    }
    return best_warped, best_model, info


# --------------------------------------------------------------------------- #
# Coherent Point Drift(剛体)                                                 #
# --------------------------------------------------------------------------- #
def register_cpd_rigid(src, dst, iters=50, w=0.0, tol=1e-8):
    """Coherent Point Drift(CPD)剛体版で回転+並進を EM 推定する。

    ``src``(移動側 Y, M点)を ``dst``(固定側 X, N点)へ剛体変換で合わせる。CPD は
    dst を、src を中心に置いた等方ガウス混合の重心と見なし、E ステップで軟対応
    (posterior)を、M ステップで最尤の剛体変換と分散を更新する。ICP と違い対応を
    ハードに決めないため、初期ずれ・部分的外れ値に頑健。スケールは 1 固定(純剛体)。

    参考: Myronenko & Song, "Point Set Registration: Coherent Point Drift", 2010。

    引数:
        src: (M,3) 移動側点群。
        dst: (N,3) 固定側点群。
        iters: 最大 EM 反復回数。
        w: 外れ値(一様分布)混合比 0≤w<1。0 で外れ無し。
        tol: 分散 σ² の相対変化がこの値未満で収束打ち切り。

    返り値:
        R: (3,3) 回転(``dst ≈ src @ R.T + t``)。
        t: (3,) 並進。
        info: dict。"sigma2"(最終分散)、"iters"、"converged"、"rmse"
              (変換後 src の最近傍 RMSE)。

    例外:
        ValueError: 形状不正、点数不足、w 範囲外。
    """
    from scipy.spatial import cKDTree

    Y = _as_points(src, "src")   # 移動側 (M,3)
    X = _as_points(dst, "dst")   # 固定側 (N,3)
    if not (0.0 <= w < 1.0):
        raise ValueError(f"w must satisfy 0<=w<1 (got: {w})")
    if Y.shape[0] < 1 or X.shape[0] < 1:
        raise ValueError("src / dst is empty")
    if iters < 1:
        raise ValueError(f"iters must be >= 1 (got: {iters})")

    M, D = Y.shape
    N = X.shape[0]
    if N * M > CPD_MAX_PAIRS:
        raise ValueError(
            f"register_cpd_rigid got {N} x {M} points; CPD builds a dense "
            f"(N,M) responsibility matrix every EM iteration, impractical "
            f"beyond N*M={CPD_MAX_PAIRS:,} (~{CPD_MAX_PAIRS * 8 // 2**20} MB "
            f"per array). Subsample both clouds first (CPD needs shape, not "
            f"density).")

    R = np.eye(D, dtype=np.float64)
    t = np.zeros(D, dtype=np.float64)

    # 初期分散 σ² = (1/(D N M)) Σ_{m,n} ‖x_n − y_m‖²
    sigma2 = _pairwise_dist(X, Y).__pow__(2).sum() / (D * N * M)
    sigma2 = max(float(sigma2), 1e-12)

    converged = False
    used = 0
    # Myronenko & Song (2010) の外れ値定数。E ステップ分母に加える一様項は
    #   c = (2πσ²)^(D/2) · (w/(1-w)) · (M/N)
    # で、(2πσ²)^(D/2) は σ² 依存のため下のループ内で毎回掛ける。ここでは
    # σ² 非依存の係数 (w/(1-w))·(M/N) のみを保持する。以前は (2π)^(D/2) を
    # 二重に含めており、外れ値オッズが (2π)^(D/2)≈15.75 倍(D=3)に化けて
    # w の意味(外れ値割合)が壊れていた。
    c_const = (w / max(1.0 - w, 1e-12)) * (M / N)

    for it in range(iters):
        used = it + 1

        # --- E ステップ: posterior P (M,N) -------------------------------- #
        TY = Y @ R.T + t                       # 変換後の移動側 (M,3)
        d2 = _pairwise_dist(X, TY) ** 2        # (N,M): ‖x_n − T(y_m)‖²
        P = np.exp(-d2.T / (2.0 * sigma2))     # (M,N)
        denom = P.sum(axis=0, keepdims=True) + c_const * (2.0 * np.pi * sigma2) ** (D / 2.0)
        denom = np.maximum(denom, 1e-300)
        P = P / denom                          # 列(=各 x_n)で正規化

        # --- M ステップ: 剛体変換の最尤更新 ------------------------------ #
        P1 = P.sum(axis=1)        # (M,) 各 y_m の総重み
        Pt1 = P.sum(axis=0)       # (N,) 各 x_n の総重み
        Np = P.sum()
        if Np < 1e-12:
            break

        mu_x = (X.T @ Pt1) / Np   # (3,)
        mu_y = (Y.T @ P1) / Np    # (3,)
        Xh = X - mu_x
        Yh = Y - mu_y

        A = Xh.T @ P.T @ Yh       # (3,3)
        U, _S, Vt = np.linalg.svd(A)
        C = np.eye(D)
        C[-1, -1] = np.linalg.det(U @ Vt)
        R = U @ C @ Vt
        t = mu_x - R @ mu_y

        # σ² 更新
        trAtR = np.trace(A.T @ R)
        trXhPX = float(np.sum(Pt1 * np.sum(Xh ** 2, axis=1)))
        new_sigma2 = (trXhPX - trAtR) / (Np * D)
        new_sigma2 = max(float(new_sigma2), 1e-12)

        if abs(new_sigma2 - sigma2) / max(sigma2, 1e-12) < tol:
            sigma2 = new_sigma2
            converged = True
            break
        sigma2 = new_sigma2

    # 変換後 src の最近傍 RMSE(品質指標)
    TY = Y @ R.T + t
    dmin, _ = cKDTree(X).query(TY, k=1)
    rmse = float(np.sqrt(np.mean(dmin ** 2)))

    info = {"sigma2": float(sigma2), "iters": used,
            "converged": converged, "rmse": rmse}
    return R, t, info


if __name__ == "__main__":
    # 構造格子に滑らかな曲げを既知変形として掛け、回復を確認。
    g = np.linspace(0.1, 0.9, 6)
    gx, gy, gz = np.meshgrid(g, g, g, indexing="ij")
    src = np.stack([gx.ravel(), gy.ravel(), gz.ravel()], axis=1)
    warp = src + 0.08 * np.stack(
        [np.sin(np.pi * src[:, 1]),
         0.5 * np.sin(np.pi * src[:, 2]),
         0.3 * np.sin(np.pi * src[:, 0])], axis=1)
    init_true = float(np.sqrt(np.mean(np.sum((src - warp) ** 2, axis=1))))
    w_src, model, info = register_nonrigid(src, warp, iters=40, lam=0.02)
    final_true = float(np.sqrt(np.mean(np.sum((w_src - warp) ** 2, axis=1))))
    print("nonrigid true RMS:", round(init_true, 5), "->", round(final_true, 5),
          f"({init_true / max(final_true, 1e-12):.0f}x)  iters", info["iters"])
    R0 = np.array([[np.cos(0.3), -np.sin(0.3), 0], [np.sin(0.3), np.cos(0.3), 0], [0, 0, 1]])
    dst = src @ R0.T + np.array([0.2, -0.1, 0.05])
    R, t, cinfo = register_cpd_rigid(src, dst, iters=80)
    print("cpd rmse:", round(cinfo["rmse"], 6), "iters", cinfo["iters"])
