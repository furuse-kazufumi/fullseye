"""Spin Image 記述子 + RANSAC 剛体登録(Johnson & Hebert)(workflow 並行探索・実測検証済、初期推定なしの大回転+部分重なり登録)。"""
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


def _estimate_normals(points, k=18, orient_ref=None):
    """局所 PCA で各点法線を推定し、orient_ref(既定=重心)から外向きに符号統一する。

    近傍 k 点の共分散の最小固有ベクトルを面法線とし、法線を「参照点から外向き」に
    そろえる。参照点も点群も剛体変換で一緒に動くため、この符号決定は回転・並進で不変
    (= 2 点群間で法線の向きが整合する)。

    引数:
        points: (N,3) 点群(numpy.ndarray)。
        k: 法線推定に使う近傍点数。
        orient_ref: 符号統一の参照点。None なら点群重心。
    返り値:
        normals: (N,3) 単位法線。
    """
    from scipy.spatial import cKDTree
    P = np.asarray(points, np.float64)
    n = len(P)
    tree = cKDTree(P)
    _, idx = tree.query(P, k=min(k, n))
    normals = np.empty((n, 3), np.float64)
    for i in range(n):
        Q = P[idx[i]] - P[idx[i]].mean(0)
        vals, vecs = np.linalg.eigh(Q.T @ Q)
        normals[i] = vecs[:, 0]                       # 最小固有値 = 面法線
    ref = P.mean(0) if orient_ref is None else np.asarray(orient_ref, np.float64)
    flip = (normals * (P - ref)).sum(1) < 0.0
    normals[flip] *= -1.0
    normals /= (np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12)
    return normals


def _spin_images(points, normals, kp_idx, support_radius,
                 n_alpha=16, n_beta=16, support_angle_cos=0.0):
    """keypoint ごとの Spin Image 記述子(平均引き + L2 正規化した flat ベクトル)。

    各 keypoint p の法線 n を軸とし、支持半径内の点 x について
    β = n·(x-p)(軸方向の符号付き高さ)、α = sqrt(|x-p|^2 - β^2)(軸からの距離)を求め、
    (α, β) の 2D ヒストグラムへ bilinear で「回転(spin)」蓄積する(Johnson & Hebert 1997)。
    範囲は α∈[0, S], β∈[-S, S](S=support_radius)。相関マッチ用に各記述子を
    平均引き→L2 正規化して返す(L2 最近傍 ≈ 正規化相関係数最大)。

    引数:
        points: (N,3) 点群。normals: (N,3) 単位法線。
        kp_idx: keypoint の点インデックス配列。
        support_radius: 支持半径 S。
        n_alpha, n_beta: (α, β) のビン数(記述子次元 = n_alpha*n_beta)。
        support_angle_cos: 支持角しきい値の cos。keypoint 法線との内積が
            これ以上の点のみ蓄積(遮蔽・裏面に頑健)。0 で無効。
    返り値:
        descs: (len(kp_idx), n_beta*n_alpha) 記述子。近傍不足の行はゼロ。
    """
    from scipy.spatial import cKDTree
    P = np.asarray(points, np.float64)
    Nn = np.asarray(normals, np.float64)
    tree = cKDTree(P)
    a_bin = support_radius / n_alpha
    b_bin = 2.0 * support_radius / n_beta
    descs = np.zeros((len(kp_idx), n_beta * n_alpha), np.float64)
    for m, ki in enumerate(kp_idx):
        p, nrm = P[ki], Nn[ki]
        nb = tree.query_ball_point(p, support_radius)
        if len(nb) < 6:
            continue
        d = P[nb] - p
        beta = d @ nrm
        alpha = np.sqrt(np.clip(np.einsum("ij,ij->i", d, d) - beta * beta, 0.0, None))
        if support_angle_cos > 0.0:
            keep = (Nn[nb] @ nrm) >= support_angle_cos
            alpha, beta = alpha[keep], beta[keep]
        inb = (alpha < support_radius) & (np.abs(beta) < support_radius)
        alpha, beta = alpha[inb], beta[inb]
        if len(alpha) < 6:
            continue
        fa = alpha / a_bin                            # 列 = α
        fb = (support_radius - beta) / b_bin          # 行 = β(上端 = +S)
        ia = np.floor(fa).astype(np.int64)
        ib = np.floor(fb).astype(np.int64)
        da, db = fa - ia, fb - ib
        img = np.zeros((n_beta + 1, n_alpha + 1), np.float64)
        np.add.at(img, (ib, ia), (1 - da) * (1 - db))
        np.add.at(img, (ib, ia + 1), da * (1 - db))
        np.add.at(img, (ib + 1, ia), (1 - da) * db)
        np.add.at(img, (ib + 1, ia + 1), da * db)
        v = img[:n_beta, :n_alpha].ravel()
        v -= v.mean()
        nn = np.linalg.norm(v)
        if nn > 1e-9:
            v /= nn
        descs[m] = v
    return descs


def _kabsch_rigid(A, B, device="cpu"):
    """R@A_i + t ~= B_i を満たす剛体 (R,t) を SVD(Kabsch)で解く。torch 出力。"""
    dev = torch.device(device)
    At = torch.as_tensor(np.asarray(A), dtype=torch.float64, device=dev)
    Bt = torch.as_tensor(np.asarray(B), dtype=torch.float64, device=dev)
    cA, cB = At.mean(0), Bt.mean(0)
    H = (At - cA).T @ (Bt - cB)
    U, S, Vt = torch.linalg.svd(H)
    V = Vt.T
    d = torch.sign(torch.det(V @ U.T))
    D = torch.diag(torch.tensor([1.0, 1.0, float(d)], dtype=torch.float64, device=dev))
    R = V @ D @ U.T
    t = cB - R @ cA
    return R, t


def register_spin(src, dst, device="cpu", n_keypoints=220, normal_k=18,
                  support_radius=None, n_alpha=16, n_beta=16,
                  support_angle_deg=60.0, lowe_ratio=0.85,
                  ransac_iters=4000, inlier_thr=None, min_inliers=8,
                  seed=0):
    """Spin Image 記述子 + RANSAC による初期推定なし疎特徴剛体位置合わせ。

    2 点群 ``src`` (N,3), ``dst`` (M,3) を、初期姿勢の事前情報なしに位置合わせする。
    各点の法線(局所 PCA、重心から外向きに符号統一 = 剛体変換で不変)を軸として近傍点を
    (α=軸からの距離, β=軸方向の高さ) の 2D ヒストグラムへ「回転(spin)」蓄積した
    Spin Image 記述子(Johnson & Hebert 1997)を keypoint ごとに作り、記述子空間の
    最近傍でマッチ(Lowe ratio test で選別)、RANSAC(3 点最小標本 + Kabsch)で
    外れ値に頑健な剛体変換を推定する。密マッチ(NCC/位相相関/Hough)や PCA 主軸整列と
    違い、**大回転 + 部分重なり**でも局所特徴の対応から姿勢を復元できるため、ICP の
    前段(coarse init 供給)に使える。返す姿勢は ``dst ~= src @ R.T + t``
    (= ``R @ src_i + t``)の規約に従う(``icp_point2point_3d`` と同一)。

    引数:
        src: (N,3) 移動側点群(numpy.ndarray か torch.Tensor)。
        dst: (M,3) 固定側(参照)点群。
        device: torch デバイス("cpu" 等)。SVD/最終姿勢をこの上で解く。
        n_keypoints: 各点群から抽出する keypoint 数(等間隔サブサンプル)。
        normal_k: 法線推定に使う近傍点数(局所 PCA)。
        support_radius: Spin Image の支持半径。None なら各点群個別の bbox 対角(大きい方)
            の 0.30 倍(未知並進で汚れないよう和集合でなく個別に測る)。
        n_alpha, n_beta: Spin Image の (α, β) ビン数(記述子は n_alpha*n_beta 次元)。
        support_angle_deg: 支持角しきい値(度)。keypoint 法線とこの角度以内の法線を持つ
            支持点のみ蓄積(遮蔽・裏面に頑健)。>=90 で無効。
        lowe_ratio: Lowe 比率テストしきい値(d1 < ratio*d2 の対応のみ採用)。
        ransac_iters: RANSAC 反復数。
        inlier_thr: RANSAC のインライア距離しきい値。None なら bbox 対角の 0.04 倍。
        min_inliers: 有効姿勢とみなす最小インライア数(``ok`` 判定)。
        seed: RANSAC 乱数シード。
    返り値:
        R: (3,3) torch.Tensor。dst ~= src @ R.T + t を満たす回転。
        t: (3,) torch.Tensor。並進。
        info: dict。"n_matches"(ratio test 通過対応数), "inliers"(RANSAC最終),
              "inlier_ratio", "rmse"(インライア上 RMSE), "support_radius",
              "inlier_thr", "ok"(min_inliers 以上か)。

    注意:
        - 記述子は法線符号に依存する。重心から外向きの符号統一は、法線が概ね放射状で
          n·(p-重心) の符号が安定な形状(lumpy な閉曲面等)で有効。薄板・管状など
          n·(p-重心)≈0 の領域が多い形状では 2 雲間で符号が反転しうる。
        - 平面・球など曲率が空間的に一様な部位は記述子が縮退し ratio test で対応が消える
          (無特徴形状には不向き)。overlap が概ね 60% を切ると成功率が急落し、失敗時は
          幾何整合だが誤りの解に RANSAC がロックして壊滅的な誤差になりうる(``ok`` /
          ``inlier_ratio`` ゲートの併用を推奨)。
    """
    from scipy.spatial import cKDTree
    dev = torch.device(device)

    def _np(a):
        if isinstance(a, torch.Tensor):
            return a.detach().cpu().numpy().astype(np.float64)
        return np.asarray(a, np.float64)

    try:
        S, D = _np(src), _np(dst)
    except (TypeError, ValueError) as e:
        # 連鎖ファザー wave-4 兄弟一掃: dict 等の非数値プール産物が np.asarray で
        # 生 TypeError 化する穴(register_fpfh と同クラス)。fail-closed に拒否。
        raise ValueError("register_spin: src/dst must be numeric (N, 3) point "
                         "arrays (got %s / %s)"
                         % (type(src).__name__, type(dst).__name__)) from e
    if S.ndim != 2 or S.shape[1] != 3 or D.ndim != 2 or D.shape[1] != 3:
        raise ValueError("register_spin: src/dst must be (N, 3) point arrays, "
                         "got %r / %r" % (S.shape, D.shape))
    if len(S) < 3 or len(D) < 3:
        raise ValueError("register_spin: need at least 3 points on each side "
                         "(got %d / %d) — a rigid pose is undefined below that; "
                         "an upstream filter may have emptied the cloud"
                         % (len(S), len(D)))
    rng = np.random.default_rng(seed)

    # スケール自動決定: 各点群個別の bbox 対角の大きい方(未知並進に汚されない)
    diag = max(float(np.linalg.norm(S.max(0) - S.min(0))),
               float(np.linalg.norm(D.max(0) - D.min(0))))
    if support_radius is None:
        support_radius = 0.30 * diag
    if inlier_thr is None:
        inlier_thr = 0.04 * diag

    eye = torch.eye(3, dtype=torch.float64, device=dev)
    zero = torch.zeros(3, dtype=torch.float64, device=dev)
    info = {"n_matches": 0, "inliers": 0, "inlier_ratio": 0.0, "rmse": float("inf"),
            "support_radius": support_radius, "inlier_thr": inlier_thr, "ok": False}

    # 法線(各点群それぞれの重心から外向き)
    ns = _estimate_normals(S, k=normal_k)
    nd = _estimate_normals(D, k=normal_k)

    # keypoint(等間隔サブサンプル)
    ks = np.linspace(0, len(S) - 1, min(n_keypoints, len(S))).astype(np.int64)
    kd = np.linspace(0, len(D) - 1, min(n_keypoints, len(D))).astype(np.int64)

    sa_cos = float(np.cos(np.deg2rad(support_angle_deg))) if support_angle_deg < 90 else 0.0
    ds = _spin_images(S, ns, ks, support_radius, n_alpha, n_beta, sa_cos)
    dd = _spin_images(D, nd, kd, support_radius, n_alpha, n_beta, sa_cos)

    vs = np.linalg.norm(ds, axis=1) > 1e-6
    vd = np.linalg.norm(dd, axis=1) > 1e-6
    ks_v, ds_v = ks[vs], ds[vs]
    kd_v, dd_v = kd[vd], dd[vd]
    if len(ds_v) < 3 or len(dd_v) < 3:
        return eye, zero, info

    # 記述子空間の最近傍マッチ + Lowe ratio test
    dtree = cKDTree(dd_v)
    dist, nbr = dtree.query(ds_v, k=2)
    src_pts, dst_pts = [], []
    for i in range(len(ds_v)):
        d1, d2 = dist[i, 0], dist[i, 1]
        if d2 > 1e-9 and d1 < lowe_ratio * d2:
            src_pts.append(S[ks_v[i]])
            dst_pts.append(D[kd_v[nbr[i, 0]]])
    src_pts = np.asarray(src_pts, np.float64)
    dst_pts = np.asarray(dst_pts, np.float64)
    info["n_matches"] = len(src_pts)
    if len(src_pts) < 3:
        return eye, zero, info

    # RANSAC(3 点最小標本 + Kabsch、共線標本は棄却)
    best_inl, best_mask = -1, None
    nP = len(src_pts)
    for _ in range(ransac_iters):
        s = rng.choice(nP, 3, replace=False)
        A3, B3 = src_pts[s], dst_pts[s]
        if np.linalg.norm(np.cross(A3[1] - A3[0], A3[2] - A3[0])) < 1e-6 * diag * diag:
            continue
        R3, t3 = _kabsch_rigid(A3, B3, device=device)
        Rn, tn = R3.cpu().numpy(), t3.cpu().numpy()
        err = np.linalg.norm(src_pts @ Rn.T + tn - dst_pts, axis=1)
        mask = err < inlier_thr
        inl = int(mask.sum())
        if inl > best_inl:
            best_inl, best_mask = inl, mask

    if best_mask is None or best_inl < 3:
        return eye, zero, info

    # 全インライアで最終 Kabsch 再推定
    R, t = _kabsch_rigid(src_pts[best_mask], dst_pts[best_mask], device=device)
    Rn, tn = R.cpu().numpy(), t.cpu().numpy()
    resid = np.linalg.norm(src_pts[best_mask] @ Rn.T + tn - dst_pts[best_mask], axis=1)
    info.update(inliers=int(best_inl), inlier_ratio=best_inl / max(nP, 1),
                rmse=float(np.sqrt((resid ** 2).mean())),
                ok=int(best_inl) >= min_inliers)
    return R, t, info
