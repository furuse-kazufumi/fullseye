"""FPFH 記述子 + RANSAC 剛体登録(Rusu 2009)(workflow 並行探索・実測検証済、初期推定なしの大回転+部分重なり登録)。"""
import numpy as np

try:
    import torch
except ImportError:                       # torch は optional(gpu/threed extra)
    class _TorchMissing:
        def __getattr__(self, name):
            raise ImportError(
                "this operator needs the optional 'torch' backend — "
                "install with: pip install \"fullseye[gpu]\"")
    torch = _TorchMissing()


# ═══════════════════════════════════════════════════════════════════════════
# 疎な feature descriptor マッチング — FPFH(Fast Point Feature Histogram)
#   Rusu 2009 の全パイプライン: 法線推定 → SPFH → FPFH → 記述子NNマッチ → RANSAC。
#   密マッチ(NCC/shape/Hough)と違い「初期推定なし」で大回転+部分重なりを対応付け、
#   剛体姿勢を出す(ICP の前段=coarse init 供給)。dst ≈ src @ R.T + t(ICP 慣習)。
#   ※ np / torch は match3d モジュール先頭で import 済み。scipy は関数内 import。
# ═══════════════════════════════════════════════════════════════════════════
def voxel_downsample(points, voxel_size):
    """voxel グリッドで点群を平均ダウンサンプル(セル内重心)。

    独立サンプリングされた 2 雲は近傍構成が食い違い FPFH の記述子一致率が落ちる。
    共通解像度の格子に載せ直すことで近傍を揃え、対応の正答率を大きく上げる前処理
    (Open3D/PCL の FPFH 位置合わせで標準。本実装でも 0.06→0.2 に改善を実測)。

    引数:
        points (N,3): 点群。voxel_size (float): セル辺長。
    返り値: (M,3) ダウンサンプル点群(M<=N)。
    """
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3 or len(P) == 0:
        # 連鎖ファザー実測(wave-4): 空点群が grp[-1] で生 IndexError 化する
        raise ValueError("voxel_downsample: points must be a non-empty (N, 3) "
                         "array, got %r — an upstream filter may have emptied "
                         "the cloud" % (P.shape,))
    key = np.floor(P / voxel_size).astype(np.int64)
    order = np.lexsort((key[:, 2], key[:, 1], key[:, 0]))
    ks = key[order]; Ps = P[order]
    uniq = np.ones(len(ks), bool)
    uniq[1:] = np.any(ks[1:] != ks[:-1], axis=1)
    grp = np.cumsum(uniq) - 1
    out = np.zeros((grp[-1] + 1, 3)); cnt = np.zeros(grp[-1] + 1)
    np.add.at(out, grp, Ps); np.add.at(cnt, grp, 1.0)
    return out / cnt[:, None]


def estimate_point_normals(points, k=16, orient_ref=None):
    """点群 (N,3) の単位法線を局所 PCA(共分散最小固有ベクトル)で推定。

    orient_ref (3,) を与えるとその参照点から外向き(n·(p-ref)>0)へ符号統一、None なら
    雲の重心基準。この規則は回転・並進同変なので、同一形状を回転した雲では対応法線が
    一致し FPFH の角特徴が回転不変になる。注意: 部分重なりで src/dst の重心がずれると
    境界付近で符号が食い違うため、既知視点があれば orient_ref にそれを渡すのが望ましい。

    引数: points (N,3), k(近傍数), orient_ref(符号統一の参照点 or None)。
    返り値: (N,3) 単位法線。
    """
    from scipy.spatial import cKDTree
    P = np.asarray(points, np.float64)
    if P.ndim != 2 or P.shape[1] != 3 or len(P) < 3:
        # 実測: 1-2 点だと cKDTree.query が欠損近傍を境界外 index で埋め、
        # P[idx] が生 IndexError 化する。法線の局所 PCA は 3 点未満で未定義。
        raise ValueError("estimate_point_normals: points must be an (N, 3) "
                         "array with N >= 3 (got %r) — normals are undefined "
                         "on fewer points" % (P.shape,))
    n = len(P)
    k = max(3, min(k, n - 1))
    tree = cKDTree(P)
    _, idx = tree.query(P, k=k + 1)                # 自身含む
    nb = P[idx]                                     # (N,k+1,3)
    Q = nb - nb.mean(axis=1, keepdims=True)
    cov = np.einsum("nki,nkj->nij", Q, Q) / nb.shape[1]
    _, vec = np.linalg.eigh(cov)                    # 昇順固有値
    normals = vec[:, :, 0]                          # 最小固有値方向=法線
    ref = P.mean(axis=0) if orient_ref is None else np.asarray(orient_ref, np.float64)
    sign = np.sign(np.einsum("ni,ni->n", normals, P - ref))
    sign[sign == 0] = 1.0
    normals = normals * sign[:, None]
    normals /= np.linalg.norm(normals, axis=1, keepdims=True).clip(1e-12)
    return normals


def _fpfh_pair_features(P, Nn, I, J):
    """順序対 (I,J) の Darboux 角特徴 (α, φ, θ) を返す。剛体不変(内積のみ)。

    source 選択(PCL 準拠): 連結線とより整合する法線を持つ側を source に固定し、
    Darboux 枠 u=n_s, v=u×d̂, w=u×v で α=v·n_t, φ=u·d̂, θ=atan2(w·n_t, u·n_t)。
    """
    pi, pj = P[I], P[J]
    ni, nj = Nn[I], Nn[J]
    dvec = pj - pi
    dist = np.linalg.norm(dvec, axis=1).clip(1e-12)
    unit = dvec / dist[:, None]
    a_i = np.einsum("ni,ni->n", ni, unit)
    a_j = -np.einsum("ni,ni->n", nj, unit)
    swap = np.abs(a_i) < np.abs(a_j)                # 大きい|dot|の側を source
    n_s = np.where(swap[:, None], nj, ni)
    n_t = np.where(swap[:, None], ni, nj)
    unit_s = np.where(swap[:, None], -unit, unit)   # source→target 方向
    u = n_s
    v = np.cross(u, unit_s)
    v /= np.linalg.norm(v, axis=1, keepdims=True).clip(1e-12)
    w = np.cross(u, v)
    alpha = np.einsum("ni,ni->n", v, n_t)           # ∈[-1,1]
    phi = np.einsum("ni,ni->n", u, unit_s)          # ∈[-1,1]
    theta = np.arctan2(np.einsum("ni,ni->n", w, n_t),
                       np.einsum("ni,ni->n", u, n_t))  # ∈[-π,π]
    return alpha, phi, theta


def compute_fpfh(points, normals, k=60, n_bins=11):
    """FPFH 記述子 (N, 3*n_bins) を計算(Rusu 2009)。

    1) SPFH: 各点 p と近傍 k 点の対に (α,φ,θ) を求め、各特徴を n_bins ビンでヒストグラム化。
    2) FPFH(p) = SPFH(p) + (1/k)Σ_j (1/d_pj) SPFH(j): 近傍 SPFH を距離重みで合成。
    3 サブヒストグラムを各々 L1 正規化して連結(既定 33 次元)。角特徴は剛体不変。

    引数: points (N,3), normals (N,3), k(FPFH 近傍数), n_bins(1特徴あたりのビン数)。
    返り値: (N, 3*n_bins) の記述子行列。
    """
    from scipy.spatial import cKDTree
    P = np.asarray(points, np.float64)
    Nn = np.asarray(normals, np.float64)
    n = len(P)
    k = max(3, min(k, n - 1))
    tree = cKDTree(P)
    dists, idx = tree.query(P, k=k + 1)             # 自身含む
    idx = idx[:, 1:]                                 # 自身除去 (N,k)
    dists = dists[:, 1:].clip(1e-12)
    kk = idx.shape[1]

    I = np.repeat(np.arange(n), kk)
    J = idx.reshape(-1)
    alpha, phi, theta = _fpfh_pair_features(P, Nn, I, J)

    def _bin(x, lo, hi):
        b = np.floor((x - lo) / (hi - lo) * n_bins).astype(np.int64)
        return np.clip(b, 0, n_bins - 1)
    ba = _bin(alpha, -1.0, 1.0)
    bp = _bin(phi, -1.0, 1.0)
    bt = _bin(theta, -np.pi, np.pi)

    spfh = np.zeros((n, 3 * n_bins), np.float64)     # SPFH(anchor=I 別に集計)
    np.add.at(spfh, (I, ba), 1.0)
    np.add.at(spfh, (I, n_bins + bp), 1.0)
    np.add.at(spfh, (I, 2 * n_bins + bt), 1.0)
    for s in range(3):                               # サブごと L1 正規化
        seg = spfh[:, s * n_bins:(s + 1) * n_bins]
        seg /= seg.sum(axis=1, keepdims=True).clip(1e-12)

    wgt = 1.0 / dists                                # 距離重み (N,k)
    weighted = (wgt[:, :, None] * spfh[idx]).sum(axis=1) / kk
    fpfh = spfh + weighted                           # FPFH = SPFH + 近傍合成
    for s in range(3):
        seg = fpfh[:, s * n_bins:(s + 1) * n_bins]
        seg /= seg.sum(axis=1, keepdims=True).clip(1e-12)
    return fpfh


def _match_fpfh_descriptors(fs, fd, mutual=True, ratio=0.95):
    """記述子最近傍マッチ。mutual(相互最近傍)+ ratio test(Lowe)で対応を絞る。"""
    from scipy.spatial import cKDTree
    td = cKDTree(fd)
    kq = 2 if ratio else 1
    dd, ii = td.query(fs, k=kq)
    if ratio:
        d1 = dd[:, 0]; d2 = dd[:, 1].clip(1e-12)
        keep = (d1 / d2) < ratio
        nn_s2d = ii[:, 0]
    else:
        keep = np.ones(len(fs), dtype=bool)
        nn_s2d = ii if ii.ndim == 1 else ii[:, 0]
    if mutual:
        ts = cKDTree(fs)
        _, nn_d2s = ts.query(fd, k=1)
        keep &= (nn_d2s[nn_s2d] == np.arange(len(fs)))
    src_idx = np.where(keep)[0]
    return src_idx, nn_s2d[src_idx]


def _kabsch_rigid(Pm, Qm):
    """対応点 Pm→Qm の剛体 (R,t)。Qm ≈ Pm@R.T + t を満たす(反射補正込み SVD)。"""
    pc = Pm.mean(0); qc = Qm.mean(0)
    H = (Pm - pc).T @ (Qm - qc)
    U, _, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    R = Vt.T @ np.diag([1.0, 1.0, d]) @ U.T
    return R, qc - R @ pc


def register_fpfh(src, dst, src_normals=None, dst_normals=None,
                  voxel_size=None, normal_k=16, feature_k=60, n_bins=11,
                  ransac_iters=8000, inlier_thr=None, edge_sim=0.9,
                  mutual=True, ratio=0.95, seed=0, device="cpu"):
    """FPFH 記述子 + RANSAC で **初期推定なし** の剛体位置合わせ (R,t) を推定する。

    2D の Harris/SIFT に相当する疎 feature マッチの 3D 版。両雲を FPFH 記述子で表し、
    記述子空間の最近傍で対応を張り(相互最近傍 + Lowe ratio でフィルタ)、RANSAC で
    外れ値に頑健な剛体姿勢を解く。密マッチ(NCC/Hough)や PCA と違い、大回転(50-70°)
    +並進+部分重なりでも初期推定なしに姿勢を出せるのが価値。得た (R,t) は ICP の初期値
    (coarse init)として渡すと表面精度まで締められる(dst ≈ src @ R.T + t の ICP 慣習)。

    パイプライン:
        1) voxel ダウンサンプル(独立サンプリング 2 雲の近傍を共通解像度へ揃える。
           FPFH の対応正答率を大きく左右する必須前処理)。
        2) 法線推定(局所 PCA)。src_normals/dst_normals を渡せばそれを使う。
        3) FPFH 記述子(SPFH→距離重み合成)。
        4) 記述子 NN マッチ(mutual + ratio)。
        5) RANSAC: 3 点サンプル → edge-length 整合プレフィルタ → Kabsch → **全点フィットネス**
           (src 全点を変換し dst 最近傍が閾値内に入る割合)で採点。対応(~100点)だけの
           採点は誤姿勢に固着しやすいため、全点フィットネスで頑健化する。
        6) 最良姿勢の対応インライアで再フィット。

    引数:
        src (N,3), dst (M,3): 位置合わせする 2 点群(numpy/torch)。
        src_normals, dst_normals ((N,3)/(M,3) or None): 事前法線。None なら内部推定
            (ただし voxel_size>0 のときは座標が変わるため常に再推定)。
        voxel_size (float or None): ダウンサンプル辺長。None で dst 解像度×2.5 を自動採用。
            0/None で無効化(生点群のまま。独立サンプリングでは非推奨)。
        normal_k (int): 法線推定の近傍数。
        feature_k (int): FPFH の近傍数(大きいほど記述子が安定・識別的。60 前後を推奨)。
        n_bins (int): 1 特徴あたりのヒストグラムビン数(記述子次元 = 3*n_bins)。
        ransac_iters (int): RANSAC 反復数。
        inlier_thr (float or None): インライア距離閾値。None で(ダウンサンプル後)解像度×3。
        edge_sim (float): 三つ組の辺長比の許容(0<edge_sim<=1、1 に近いほど厳格)。
        mutual (bool): 相互最近傍フィルタ。ratio (float or None): Lowe ratio。
        seed (int): RANSAC 乱数種(restart 時に変える)。device (str): 返り値テンソルの device。

    返り値:
        R (3,3) torch.Tensor(device 上), t (3,) torch.Tensor,
        info dict: {"n_corr"(対応数), "inliers"(インライア数), "inlier_ratio",
                    "fitness"(全点フィットネス=restart 選択の指標), "rmse"(インライア RMSE),
                    "inlier_thr", "src_corr","dst_corr"(対応 index)}。

    注意(honest): FPFH は coarse registration であり、独立サンプリング+ノイズ+部分重なり
    の難条件では回転誤差が数度残る(実測: 62°回転・重なり~64%・ノイズ0.5×解像度で
    RANSAC 後 中央値 ~4.4°、~90% が <8°、残り ~10% は 8-9° の境界。ICP で締めると 100%
    が <8°・中央値 ~0.5°)。ノイズが点間隔(解像度)並み以上になると法線・角特徴が
    崩れ記述子が識別力を失う(実測: ノイズ≥1.0×解像度で成功率が低下)。RANSAC は乱択
    なので実運用では数回 restart し info["fitness"] 最大の結果を採るとよい。
    """
    from scipy.spatial import cKDTree
    rng = np.random.default_rng(seed)
    try:
        Ps = np.asarray(src, np.float64)
        Pd = np.asarray(dst, np.float64)
    except (TypeError, ValueError) as e:
        raise ValueError("register_fpfh: src/dst must be numeric (N, 3) point "
                         "arrays (got %s / %s)"
                         % (type(src).__name__, type(dst).__name__)) from e
    if Ps.ndim != 2 or Ps.shape[1] != 3 or Pd.ndim != 2 or Pd.shape[1] != 3:
        raise ValueError("register_fpfh: src/dst must be (N, 3) point arrays, "
                         "got %r / %r" % (Ps.shape, Pd.shape))
    if len(Ps) < 3 or len(Pd) < 3:
        # 連鎖ファザー実測(wave-4): 空点群(radius_outlier_removal 等が全点除去
        # した産物)が voxel_downsample の grp[-1] / KDTree 添字で生 IndexError 化。
        raise ValueError("register_fpfh: need at least 3 points on each side "
                         "(got %d / %d) — a rigid pose is undefined below that; "
                         "an upstream filter may have emptied the cloud"
                         % (len(Ps), len(Pd)))

    res = float(np.median(cKDTree(Pd).query(Pd, k=2)[0][:, -1]))   # dst 解像度
    if voxel_size is None:
        voxel_size = 2.5 * res
    if voxel_size and voxel_size > 0:
        Ps = voxel_downsample(Ps, voxel_size)
        Pd = voxel_downsample(Pd, voxel_size)
        src_normals = dst_normals = None                          # 座標が変わる→再推定
        res = float(np.median(cKDTree(Pd).query(Pd, k=2)[0][:, -1]))

    if src_normals is None:
        src_normals = estimate_point_normals(Ps, k=normal_k)
    if dst_normals is None:
        dst_normals = estimate_point_normals(Pd, k=normal_k)

    fs = compute_fpfh(Ps, src_normals, k=feature_k, n_bins=n_bins)
    fd = compute_fpfh(Pd, dst_normals, k=feature_k, n_bins=n_bins)

    src_idx, dst_idx = _match_fpfh_descriptors(fs, fd, mutual=mutual, ratio=ratio)
    n_corr = len(src_idx)
    dev = torch.device(device)
    if n_corr < 3:
        return (torch.eye(3, dtype=torch.float64, device=dev),
                torch.zeros(3, dtype=torch.float64, device=dev),
                {"n_corr": n_corr, "inliers": 0, "inlier_ratio": 0.0,
                 "fitness": 0.0, "rmse": float("inf"), "inlier_thr": inlier_thr,
                 "src_corr": src_idx, "dst_corr": dst_idx})

    A = Ps[src_idx]; B = Pd[dst_idx]
    if inlier_thr is None:
        inlier_thr = 3.0 * res

    dst_tree = cKDTree(Pd)                                          # 全点フィットネス用
    ver = Ps[rng.choice(len(Ps), min(300, len(Ps)), replace=False)]

    def _full_fitness(R, t):
        d, _ = dst_tree.query(ver @ R.T + t, k=1)
        return float((d < inlier_thr).mean())

    best_score = -1.0; best_inl = 3
    best_R = np.eye(3); best_t = np.zeros(3); best_mask = None
    idx_all = np.arange(n_corr)
    for _ in range(ransac_iters):
        s = rng.choice(idx_all, size=3, replace=False)
        a, b = A[s], B[s]
        da = np.array([np.linalg.norm(a[0]-a[1]), np.linalg.norm(a[1]-a[2]),
                       np.linalg.norm(a[0]-a[2])])
        db = np.array([np.linalg.norm(b[0]-b[1]), np.linalg.norm(b[1]-b[2]),
                       np.linalg.norm(b[0]-b[2])])
        if np.any(da < 1e-9) or np.any(db < 1e-9):
            continue
        r = da / db                                                # edge-length 整合
        if np.min(r) < edge_sim or np.max(r) > 1.0 / edge_sim:
            continue
        R, t = _kabsch_rigid(a, b)
        mask = np.linalg.norm(A @ R.T + t - B, axis=1) < inlier_thr
        ninl = int(mask.sum())
        if ninl < best_inl:                                        # 最小支持ゲート
            continue
        score = _full_fitness(R, t)
        if score > best_score:
            best_score = score
            best_inl = max(4, ninl // 2)
            best_R, best_t, best_mask = R, t, mask

    for _ in range(2):                                             # インライア再フィット
        if best_mask is None or best_mask.sum() < 3:
            break
        R, t = _kabsch_rigid(A[best_mask], B[best_mask])
        mask = np.linalg.norm(A @ R.T + t - B, axis=1) < inlier_thr
        if mask.sum() >= 3:
            best_R, best_t, best_mask = R, t, mask

    rmse = float(np.sqrt(np.mean(np.linalg.norm(
        A[best_mask] @ best_R.T + best_t - B[best_mask], axis=1) ** 2))) \
        if best_mask is not None and best_mask.sum() > 0 else float("inf")
    info = {"n_corr": n_corr,
            "inliers": int(best_mask.sum()) if best_mask is not None else 0,
            "inlier_ratio": float(best_mask.mean()) if best_mask is not None else 0.0,
            "fitness": best_score, "rmse": rmse, "inlier_thr": inlier_thr,
            "src_corr": src_idx, "dst_corr": dst_idx}
    return (torch.as_tensor(best_R, dtype=torch.float64, device=dev),
            torch.as_tensor(best_t, dtype=torch.float64, device=dev), info)
