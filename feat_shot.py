"""SHOT 記述子 + ISS keypoint + RANSAC 登録(Tombari 2010)(workflow 並行探索・実測検証済、初期推定なしの大回転+部分重なり登録)。"""
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

from match3d import icp_point2point_3d


def estimate_normals(points, k=16, device="cpu"):
    """各点の法線を局所共分散の最小固有ベクトルで推定し、Tombari 局所符号則で
    近傍質量から離れる向き(局所外向き)へ統一する。回転共変かつ部分重なりに
    安定(大域重心に依存しない局所則のため)。返り値 (N,3) 単位法線。"""
    from scipy.spatial import cKDTree
    pts = np.asarray(points, np.float64)
    n = len(pts)
    tree = cKDTree(pts)
    _, idx = tree.query(pts, k=min(k, n))
    normals = np.zeros((n, 3), np.float64)
    for i in range(n):
        nb = pts[idx[i]]
        q = nb - nb.mean(0)
        vals, vecs = np.linalg.eigh(q.T @ q)
        nrm = vecs[:, 0]                        # 最小固有値 = 法線
        d = nb - pts[i]
        if np.sum(d @ nrm >= 0) > len(d) / 2.0:  # 近傍質量から離れる向きへ
            nrm = -nrm
        normals[i] = nrm
    normals /= (np.linalg.norm(normals, axis=1, keepdims=True) + 1e-12)
    return normals


def iss_keypoints(points, radius, nms_radius=None, gamma21=0.99, gamma32=0.99,
                  max_kp=400, min_neighbors=8):
    """ISS(Intrinsic Shape Signatures、3D Harris 相当)キーポイント検出。
    局所共分散の最小固有値 λ3 を saliency とし、固有値が distinct(向きが
    well-defined)な点のみ候補にして NMS で疎に選ぶ。回転不変。返り値=点 index 配列。"""
    from scipy.spatial import cKDTree
    pts = np.asarray(points, np.float64)
    n = len(pts)
    tree = cKDTree(pts)
    if nms_radius is None:
        nms_radius = 0.6 * radius
    saliency = np.full(n, -1.0)
    for i in range(n):
        nb_idx = tree.query_ball_point(pts[i], radius)
        if len(nb_idx) < min_neighbors:
            continue
        q = pts[nb_idx] - pts[i]
        vals = np.linalg.eigvalsh((q.T @ q) / len(nb_idx))[::-1]  # λ1>=λ2>=λ3
        l1, l2, l3 = vals
        if l1 <= 1e-12:
            continue
        if (l2 / l1) < gamma21 and (l3 / l2) < gamma32:
            saliency[i] = l3
    cand = np.where(saliency > 0)[0]
    cand = cand[np.argsort(saliency[cand])[::-1]]
    accepted, acc_pts = [], []
    for i in cand:
        if acc_pts:
            if np.linalg.norm(np.asarray(acc_pts) - pts[i], axis=1).min() < nms_radius:
                continue
        accepted.append(i)
        acc_pts.append(pts[i])
        if len(accepted) >= max_kp:
            break
    return np.asarray(accepted, dtype=np.int64)


def _compute_lrf(pts, tree, center, radius):
    """Tombari の局所参照フレーム(LRF)。距離重み付き共分散の固有ベクトルを
    符号曖昧性解消(各軸を近傍ベクトルの投影多数派へ)して右手系化。列=[x,y,z]。"""
    nb_idx = tree.query_ball_point(center, radius)
    if len(nb_idx) < 5:
        return None
    d = pts[nb_idx] - center
    dist = np.linalg.norm(d, axis=1)
    w = np.clip(radius - dist, 0, None)         # 距離重み(近いほど大)
    wsum = w.sum()
    if wsum <= 1e-12:
        return None
    cov = (d * w[:, None]).T @ d / wsum
    vals, vecs = np.linalg.eigh(cov)            # 昇順
    x_ax, z_ax = vecs[:, 2], vecs[:, 0]         # 最大 / 最小 固有値
    if np.sum(d @ x_ax >= 0) < len(d) / 2.0:    # 符号 = 近傍多数派に一致(Tombari)
        x_ax = -x_ax
    if np.sum(d @ z_ax >= 0) < len(d) / 2.0:
        z_ax = -z_ax
    y_ax = np.cross(z_ax, x_ax)
    ny = np.linalg.norm(y_ax)
    if ny < 1e-9:
        return None
    y_ax /= ny
    x_ax = np.cross(y_ax, z_ax)                 # 直交正規化を保証
    return np.stack([x_ax, y_ax, z_ax], axis=1)


def _accumulate_bin(v, n):
    """ビン中心 0.5,1.5,.. に値 1 を線形分配(境界 clamp)。戻り [(idx,w),(idx,w)]。"""
    b = v - 0.5
    i0 = int(np.floor(b))
    frac = b - i0
    lo = min(max(i0, 0), n - 1)
    hi = min(max(i0 + 1, 0), n - 1)
    return [(lo, 1.0 - frac), (hi, frac)]


def shot_descriptor(points, normals, kp_idx, tree, radius,
                    n_azim=8, n_elev=2, n_rad=2, n_cos=11):
    """SHOT 記述子(Tombari 2010)。各キーポイントに LRF を張り、球状支持を
    径2×仰角2×方位8=32 空間セルに分割、各セルで「LRF z 軸と近傍点法線の
    cos角」を n_cos=11 ビンのヒストグラムに quadrilinear 補間で蓄積 → 32×11=352
    次元を L2 正規化。返り値 (Kp,352)。LRF 不能な点は零ベクトル。"""
    pts = np.asarray(points, np.float64)
    Kp = len(kp_idx)
    dim = n_azim * n_elev * n_rad * n_cos
    desc = np.zeros((Kp, dim), np.float64)
    for ki, kp in enumerate(kp_idx):
        lrf = _compute_lrf(pts, tree, pts[kp], radius)
        if lrf is None:
            continue
        z_ax = lrf[:, 2]
        nb_idx = [j for j in tree.query_ball_point(pts[kp], radius) if j != kp]
        if len(nb_idx) < 5:
            continue
        d = pts[nb_idx] - pts[kp]
        q = d @ lrf                              # LRF 座標 [qx,qy,qz]
        r = np.linalg.norm(q, axis=1)
        cosd = np.clip(normals[nb_idx] @ z_ax, -1.0, 1.0)
        for m in range(len(nb_idx)):
            rm = r[m]
            if rm < 1e-9 or rm > radius:
                continue
            qx, qy, qz = q[m]
            v_rad = (rm / radius) * n_rad
            v_elev = (np.arccos(np.clip(qz / rm, -1.0, 1.0)) / np.pi) * n_elev
            az = np.arctan2(qy, qx) % (2 * np.pi)
            v_az = (az / (2 * np.pi)) * n_azim
            v_cos = ((cosd[m] + 1.0) / 2.0) * n_cos
            rad_c = _accumulate_bin(v_rad, n_rad)
            elev_c = _accumulate_bin(v_elev, n_elev)
            cos_c = _accumulate_bin(v_cos, n_cos)
            ba = v_az - 0.5                       # 方位は円環補間(wrap)
            a0 = int(np.floor(ba))
            fa = ba - a0
            az_c = [(a0 % n_azim, 1.0 - fa), ((a0 + 1) % n_azim, fa)]
            for ri, rw in rad_c:
                for ei, ew in elev_c:
                    for ai, aw in az_c:
                        base = ((ri * n_elev + ei) * n_azim + ai) * n_cos
                        for ci, cw in cos_c:
                            w = rw * ew * aw * cw
                            if w > 0:
                                desc[ki, base + ci] += w
        nrm = np.linalg.norm(desc[ki])
        if nrm > 1e-9:
            desc[ki] /= nrm
    return desc


def match_descriptors(desc_s, desc_d, ratio=0.9, mutual=True):
    """記述子マッチング。src→dst で最近傍2点を取り Lowe 比率テスト
    (d1/d2<ratio)、mutual=True なら相互最近傍チェックで誤対応を抑制。
    返り値 (P,2) の [src局所index, dst局所index]。"""
    from scipy.spatial import cKDTree
    valid_s = np.where(np.linalg.norm(desc_s, axis=1) > 1e-6)[0]
    valid_d = np.where(np.linalg.norm(desc_d, axis=1) > 1e-6)[0]
    if len(valid_s) == 0 or len(valid_d) < 2:
        return np.zeros((0, 2), np.int64)
    Ds, Dd = desc_s[valid_s], desc_d[valid_d]
    tree_d = cKDTree(Dd)
    dist, idx = tree_d.query(Ds, k=2)
    if mutual:
        tree_s = cKDTree(Ds)
        _, idx_ds = tree_s.query(Dd, k=1)
    pairs = []
    for a in range(len(valid_s)):
        d1, d2 = dist[a, 0], dist[a, 1]
        if d2 < 1e-12 or (d1 / d2) > ratio:
            continue
        b = idx[a, 0]
        if mutual and idx_ds[b] != a:
            continue
        pairs.append((valid_s[a], valid_d[b]))
    return np.asarray(pairs, np.int64)


def _kabsch(P, Q, device="cpu"):
    """対応既知の剛体姿勢(Kabsch/SVD)。dst Q ≈ P @ R.T + t を満たす R,t
    (icp_point2point_3d と同規約)を返す。"""
    Pt = torch.as_tensor(P, dtype=torch.float64, device=device)
    Qt = torch.as_tensor(Q, dtype=torch.float64, device=device)
    cP, cQ = Pt.mean(0), Qt.mean(0)
    H = (Pt - cP).T @ (Qt - cQ)
    U, S, Vt = torch.linalg.svd(H)
    V = Vt.T
    d = torch.sign(torch.det(V @ U.T))
    D = torch.diag(torch.tensor([1.0, 1.0, float(d)], dtype=torch.float64, device=device))
    R = V @ D @ U.T
    t = cQ - R @ cP
    return R.cpu().numpy(), t.cpu().numpy()


def ransac_rigid(src_pts, dst_pts, pairs, inlier_thr, iters=2000, seed=0,
                 device="cpu"):
    """3 点最小サンプル + Kabsch の RANSAC で外れ対応に頑健な剛体姿勢を推定。
    退化(共線)サンプルを棄却し、最良インライア集合で再推定。
    返り値 (R, t, inliers(bool), S, D) or None。"""
    rng = np.random.default_rng(seed)
    S = src_pts[pairs[:, 0]]
    D = dst_pts[pairs[:, 1]]
    m = len(pairs)
    if m < 3:
        return None
    best_inliers, best_count = None, 0
    for _ in range(iters):
        sel = rng.choice(m, 3, replace=False)
        P3, Q3 = S[sel], D[sel]
        if np.linalg.norm(np.cross(P3[1] - P3[0], P3[2] - P3[0])) < 1e-6:
            continue                             # 共線サンプルは退化
        R, t = _kabsch(P3, Q3, device)
        err = np.linalg.norm(S @ R.T + t - D, axis=1)
        inl = err < inlier_thr
        c = int(inl.sum())
        if c > best_count:
            best_count, best_inliers = c, inl
    if best_inliers is None or best_count < 3:
        return None
    R, t = _kabsch(S[best_inliers], D[best_inliers], device)
    return R, t, best_inliers, S, D


def register_shot(src, dst, radius=None, normal_k=16, ratio=0.9,
                  ransac_iters=2000, inlier_thr=None, refine_icp=True,
                  max_kp=400, device="cpu", seed=0):
    """SHOT 記述子による疎特徴マッチング + RANSAC 剛体姿勢推定(全パイプライン)。

    初期推定なしに、大回転・部分重なりの 2 点群を対応付けて剛体変換
    (回転 R + 並進 t)を返す。密マッチ(NCC/Hough/PCA)と異なり、ISS
    キーポイントごとに局所参照フレーム(LRF)を張り、球状分割セルの
    法線角度ヒストグラム(SHOT)で記述 → Lowe 比率テスト + 相互最近傍で
    マッチ → RANSAC で外れ値に頑健に姿勢推定する。得た姿勢は ICP の
    粗初期値(coarse init)供給にも使える。

    LRF の符号曖昧性: 距離重み付き共分散の固有ベクトルは符号が定まらない
    ため、各軸(x=最大, z=最小 固有値)を近傍ベクトル (p_i-p) の投影多数派
    へ合わせ(Tombari の符号則)、y=z×x で右手系を構成する。点法線も同則で
    近傍質量から離れる向き(局所外向き)に統一するため回転に共変で部分
    重なりにも安定。両点群に同一則を適用することで記述子の repeatability を担保。

    引数:
        src, dst: (N,3)/(M,3) 点群(numpy か torch)。src を dst へ合わせる。
        radius: SHOT 支持半径。None なら各点群自身の bbox 対角(小さい方)の 0.15 倍
            (結合 bbox は並進で対角が水増しされスケールが狂うため使わない)。
        normal_k: 法線推定の knn 数。
        ratio: Lowe 比率テスト閾値(小さいほど厳格)。
        ransac_iters: RANSAC 反復数。
        inlier_thr: RANSAC インライア距離。None なら bbox 対角の 0.03 倍。
        refine_icp: True なら得た姿勢を初期値に Trimmed ICP(icp_point2point_3d)で精緻化。
        max_kp: キーポイント上限。
        device: torch デバイス("cpu" 等)。SVD/ICP をこの上で解く。
        seed: RANSAC 乱数種。

    返り値:
        R: (3,3) numpy。dst ≈ src @ R.T + t を満たす回転(icp と同規約)。
        t: (3,) numpy。並進。
        info: dict。"n_kp_src","n_kp_dst","n_matches","n_inliers","inlier_ratio",
              "icp_rmse"(refine_icp 時),"ok"(True=推定成功; インライア<4 は
              信頼不可として False + 単位変換を返す)。
    """
    from scipy.spatial import cKDTree
    src = np.asarray(src.cpu().numpy() if isinstance(src, torch.Tensor) else src, np.float64)
    dst = np.asarray(dst.cpu().numpy() if isinstance(dst, torch.Tensor) else dst, np.float64)

    # スケールは各点群自身の広がりから(並進不変)。結合 bbox は GT 並進で
    # 対角が水増しされ radius/閾値が狂うため使わない。
    diag = min(np.linalg.norm(src.max(0) - src.min(0)),
               np.linalg.norm(dst.max(0) - dst.min(0)))
    if radius is None:
        radius = 0.15 * diag
    if inlier_thr is None:
        inlier_thr = 0.03 * diag

    ns = estimate_normals(src, k=normal_k, device=device)
    nd = estimate_normals(dst, k=normal_k, device=device)
    # saliency は支持半径より局所(コーナー多数抽出)、NMS も小さめで密に採用
    sal_r, nms_r = 0.6 * radius, 0.3 * radius
    kp_s = iss_keypoints(src, sal_r, nms_radius=nms_r, max_kp=max_kp)
    kp_d = iss_keypoints(dst, sal_r, nms_radius=nms_r, max_kp=max_kp)

    info = {"n_kp_src": int(len(kp_s)), "n_kp_dst": int(len(kp_d)),
            "n_matches": 0, "n_inliers": 0, "inlier_ratio": 0.0, "ok": False}
    if len(kp_s) < 3 or len(kp_d) < 3:
        return np.eye(3), np.zeros(3), info

    tree_s, tree_d = cKDTree(src), cKDTree(dst)
    desc_s = shot_descriptor(src, ns, kp_s, tree_s, radius)
    desc_d = shot_descriptor(dst, nd, kp_d, tree_d, radius)

    pairs_local = match_descriptors(desc_s, desc_d, ratio=ratio, mutual=True)
    info["n_matches"] = int(len(pairs_local))
    if len(pairs_local) < 3:
        return np.eye(3), np.zeros(3), info

    pairs = np.stack([kp_s[pairs_local[:, 0]], kp_d[pairs_local[:, 1]]], axis=1)
    res = ransac_rigid(src, dst, pairs, inlier_thr, iters=ransac_iters,
                       seed=seed, device=device)
    if res is None:
        return np.eye(3), np.zeros(3), info
    R, t, inliers, _, _ = res
    info["n_inliers"] = int(inliers.sum())
    info["inlier_ratio"] = float(inliers.sum() / max(len(pairs), 1))
    # インライアが最小サンプル数(3)ちょうど = 追加支持なし = 信頼不可
    info["ok"] = int(inliers.sum()) >= 4
    if not info["ok"]:
        return np.eye(3), np.zeros(3), info

    if refine_icp:
        Ri, ti, icp_info = icp_point2point_3d(
            src, dst, iters=60, init_R=R, init_t=t,
            trim_ratio=0.6, max_corr_dist=3 * inlier_thr, device=device)
        R = Ri.cpu().numpy() if isinstance(Ri, torch.Tensor) else np.asarray(Ri)
        t = ti.cpu().numpy() if isinstance(ti, torch.Tensor) else np.asarray(ti)
        info["icp_rmse"] = float(icp_info.get("rmse", float("nan")))
    return R, t, info
