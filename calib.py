"""カメラ校正/投影/ハンドアイ(HALCON "Calibration" chapter の genuine 実装, numpy).

投影・平面ホモグラフィ(image<->world plane)・Zhang 内部校正・Tsai-Lenz ハンドアイ。
実センサ handle でなく純粋な多視点幾何を本物で実装。
cam_par = {"fx","fy","cx","cy"}(またはピンホール 3x3 K)。pose = 4x4 剛体変換。
"""
from __future__ import annotations

import numpy as np


# ── 入口の検査(fail-closed、2026-10-23 に台帳 opscalib へ載せる便で追加)────────── #
# 非有限・空・形の合わない入力は ValueError で拒否する。以前は NaN の点が NaN の画素に、
# 欠けた鍵が KeyError に、視線と平行な点が inf になって黙って下流へ流れていた。
def _finite_array(a, name, op, cols=None, min_rows=1):
    """有限な float64 配列 ``(N, cols)``(``cols`` 指定時)を返す。空・非有限・形違いは拒否。"""
    if isinstance(a, (str, bytes)):
        raise ValueError("%s: %s is a string — expected an array of numbers" % (op, name))
    try:
        arr = np.asarray(a, dtype=np.float64)
    except (TypeError, ValueError) as e:
        raise ValueError("%s: %s is not numeric (%s)" % (op, name, e)) from None
    if cols is not None:
        if arr.size % cols:
            raise ValueError("%s: %s has %d values, not a multiple of %d (expected (N, %d))"
                             % (op, name, arr.size, cols, cols))
        arr = arr.reshape(-1, cols)
    if arr.size == 0 or (arr.ndim >= 1 and len(arr) < min_rows):
        raise ValueError("%s: %s is empty or has fewer than %d row(s) — nothing to compute on"
                         % (op, name, min_rows))
    if not np.isfinite(arr).all():
        raise ValueError("%s: %s has %d non-finite value(s) — refused rather than propagated"
                         % (op, name, int((~np.isfinite(arr)).sum())))
    return arr


def _finite_scalar(v, name, op, positive=False):
    """有限な実数(``positive`` なら正)を返す。bool・文字列・NaN・Inf は拒否。"""
    if isinstance(v, (bool, np.bool_, str, bytes)) or np.ndim(v) != 0:
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v))
    try:
        f = float(v)
    except (TypeError, ValueError):
        raise ValueError("%s: %s must be a real number, got %r" % (op, name, v)) from None
    if not np.isfinite(f) or (positive and f <= 0.0):
        raise ValueError("%s: %s must be a %sfinite number, got %r"
                         % (op, name, "positive " if positive else "", v))
    return f


def _shape2(shape, op):
    """``(H, W)`` の正の整数 2 つを返す。"""
    try:
        h, w = shape
    except (TypeError, ValueError):
        raise ValueError("%s: shape must be (H, W), got %r" % (op, shape)) from None
    out = []
    for v in (h, w):
        if isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, np.integer)) or int(v) < 1:
            raise ValueError("%s: shape must be two positive integers, got %r" % (op, shape))
        out.append(int(v))
    return tuple(out)


def _pose_matrix(pose, op, name="pose"):
    """有限な 4x4(または 3x4)の剛体変換を 4x4 で返す。"""
    P = _finite_array(pose, name, op)
    if P.shape == (3, 4):
        P = np.vstack([P, [0.0, 0.0, 0.0, 1.0]])
    if P.shape != (4, 4):
        raise ValueError("%s: %s must be a 4x4 (or 3x4) transform, got shape %r"
                         % (op, name, P.shape))
    return P


def _checked_div(num, den, op, what):
    """同次座標の割り算。分母 0(視線・地平線上の点)で inf を返さず拒否する。"""
    with np.errstate(divide="ignore", invalid="ignore"):
        out = num / den
    bad = ~np.isfinite(out)
    if bad.any():
        n = int(bad.any(axis=-1).sum()) if bad.ndim > 1 else int(bad.sum())
        raise ValueError("%s: %d point(s) have a zero homogeneous coordinate (%s) — "
                         "their image is at infinity" % (op, n, what))
    return out


def _K(cam_par, op="camera"):
    """``cam_par``({"fx","fy","cx","cy"} または 3x3 K)→ 有限な 3x3 K。"""
    if isinstance(cam_par, dict):
        missing = [k for k in ("fx", "fy", "cx", "cy") if k not in cam_par]
        if missing:
            raise ValueError("%s: cam_par is missing %s (expected keys fx, fy, cx, cy)"
                             % (op, ", ".join(missing)))
        fx = _finite_scalar(cam_par["fx"], "cam_par['fx']", op, positive=True)
        fy = _finite_scalar(cam_par["fy"], "cam_par['fy']", op, positive=True)
        cx = _finite_scalar(cam_par["cx"], "cam_par['cx']", op)
        cy = _finite_scalar(cam_par["cy"], "cam_par['cy']", op)
        return np.array([[fx, 0, cx], [0, fy, cy], [0, 0, 1.0]])
    K = _finite_array(cam_par, "cam_par", op)
    if K.shape != (3, 3):
        raise ValueError("%s: cam_par must be a dict {fx, fy, cx, cy} or a 3x3 K, got shape %r"
                         % (op, K.shape))
    return K


def project_3d_point(points_3d, cam_par, pose=None):
    """3D 点をカメラへ透視投影し画素 (row, col) を返す(project_3d_point)。"""
    op = "project_3d_point"
    P = _finite_array(points_3d, "points_3d", op, cols=3)
    K = _K(cam_par, op)
    if pose is not None:
        pose = _pose_matrix(pose, op)
        P = (P @ pose[:3, :3].T) + pose[:3, 3]
    uvw = P @ K.T
    uv = _checked_div(uvw[:, :2], uvw[:, 2:3], op, "z = 0 in the camera frame")
    return np.column_stack([uv[:, 1], uv[:, 0]])          # (row=y, col=x)


def project_point_hom_mat3d(points_3d, hom_mat3d):
    """4x4 or 3x4 射影行列 P=K[R|t] で 3D 点を投影し画素 (row, col) を返す(project_point_hom_mat3d)。

    ``project_3d_point`` と同じ (row, col) 規約
    (2026-09-02 以前は (x, y) を返しており兄弟 API と食い違っていた)。"""
    op = "project_point_hom_mat3d"
    P = _finite_array(points_3d, "points_3d", op, cols=3)
    Hm = _pose_matrix(hom_mat3d, op, "hom_mat3d")[:3]
    out = (np.column_stack([P, np.ones(len(P))]) @ Hm.T)
    uv = _checked_div(out[:, :2], out[:, 2:3], op, "w = 0")
    return np.column_stack([uv[:, 1], uv[:, 0]])


def project_hom_point_hom_mat3d(points_hom, hom_mat3d):
    """同次 3D 点 (4,) を 3x4/4x4 射影行列で投影し画素 (row, col) を返す(project_hom_point_hom_mat3d)。"""
    op = "project_hom_point_hom_mat3d"
    P = _finite_array(points_hom, "points_hom", op, cols=4)
    Hm = _pose_matrix(hom_mat3d, op, "hom_mat3d")[:3]
    out = P @ Hm.T
    uv = _checked_div(out[:, :2], out[:, 2:3], op, "w = 0")
    return np.column_stack([uv[:, 1], uv[:, 0]])


def _homography_dlt(src, dst):
    """4+ 点対応から DLT でホモグラフィ H (dst = H src) を推定。"""
    src = np.asarray(src, float).reshape(-1, 2); dst = np.asarray(dst, float).reshape(-1, 2)
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        A.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    A = np.asarray(A)
    _, _, Vt = np.linalg.svd(A, full_matrices=A.shape[0] < A.shape[1])
    H = Vt[-1].reshape(3, 3)
    return H / H[2, 2]


def vector_to_hom_mat2d(src_points, dst_points):
    """点対応から 2D ホモグラフィを推定(vector_to_hom_mat2d)。"""
    return _homography_dlt(src_points, dst_points)


def image_to_world_plane(image_points, homography):
    """画像点を平面ホモグラフィで world 平面(z=0)へ写す(image_to_world_plane)。

    規約に依らず ``homography`` を点に **そのまま** 適用する: H を (x=col, y=row)
    で推定したなら点も (col, row) で渡す(``camera_calibration`` の
    ``homographies`` は (x,y)→(col,row) なので、その逆行列をこの向きで使う)。"""
    op = "image_to_world_plane"
    p = _finite_array(image_points, "image_points", op, cols=2)
    H = _finite_array(homography, "homography", op)
    if H.shape != (3, 3):
        raise ValueError("%s: homography must be 3x3, got shape %r" % (op, H.shape))
    h = np.column_stack([p, np.ones(len(p))]) @ H.T
    return _checked_div(h[:, :2], h[:, 2:3], op, "the point maps to the horizon")


def image_points_to_world_plane(cam_par, pose, image_points, scale=1.0):
    """カメラ内部/外部から画素を world 平面 z=0 へ逆投影(image_points_to_world_plane)。"""
    op = "image_points_to_world_plane"
    K = _K(cam_par, op); pose = _pose_matrix(pose, op)
    sc = _finite_scalar(scale, "scale", op, positive=True)
    R = pose[:3, :3]; t = pose[:3, 3]
    ray_transform = R.T @ np.linalg.inv(K)
    o = -R.T @ t
    p = _finite_array(image_points, "image_points", op, cols=2)
    rays = np.column_stack((p[:, 1], p[:, 0], np.ones(len(p)))) @ ray_transform.T
    lam = _checked_div(-o[2], rays[:, 2], op, "the viewing ray is parallel to the z = 0 plane")
    return (o[None, :2] + lam[:, None] * rays[:, :2]) * sc


def contour_to_world_plane_xld(contour, homography):
    """XLD 輪郭(dict {cs:[Nx2]})を world 平面へ写す(contour_to_world_plane_xld)。"""
    op = "contour_to_world_plane_xld"
    if not isinstance(contour, dict) or not contour.get("cs"):
        raise ValueError("%s: contour must be an XLD dict with a non-empty 'cs' list of (N, 2) "
                         "arrays, got %r" % (op, type(contour).__name__))
    out = {"shape": contour.get("shape"), "cs": []}
    for arr in contour["cs"]:
        out["cs"].append(image_to_world_plane(arr, homography))
    return out


def gen_radial_distortion_map(cam_par, kappa, shape):
    """半径歪みの逆マップ(row_map, col_map)を生成(gen_radial_distortion_map)。"""
    op = "gen_radial_distortion_map"
    K = _K(cam_par, op); H, W = _shape2(shape, op)
    kappa = _finite_scalar(kappa, "kappa", op)
    cx = K[0, 2]; cy = K[1, 2]
    rr, cc = np.mgrid[0:H, 0:W].astype(float)
    x = cc - cx; y = rr - cy
    r2 = x * x + y * y
    f = 1 + kappa * r2
    return {"row_map": cy + y * f, "col_map": cx + x * f}


# ── Zhang の平面校正(内部行列推定)────────────────────────────────────────────── #
def _vij(H, i, j):
    return np.array([H[0, i] * H[0, j],
                     H[0, i] * H[1, j] + H[1, i] * H[0, j],
                     H[1, i] * H[1, j],
                     H[2, i] * H[0, j] + H[0, i] * H[2, j],
                     H[2, i] * H[1, j] + H[1, i] * H[2, j],
                     H[2, i] * H[2, j]])


def camera_calibration(object_points, image_points_list):
    """Zhang 法で平面ターゲット多視点から内部行列 K を推定(camera_calibration)。

    ``object_points``: (N,2) 平面ターゲット座標 **(x, y)**(z=0 平面、ワールド単位)。
    ``image_points_list``: 各視点の (N,2) 画素対応。**(row, col)** — このモジュールの
    他 API(``project_3d_point`` の戻り値、``image_points_to_world_plane`` の入力)と
    同じ規約。内部で (x=col, y=row) に並べ替えてから解くので、``fx``/``cx`` は
    col 軸、``fy``/``cy`` は row 軸の値になる(2026-09-02 以前は (x,y) として
    扱っており fx↔fy, cx↔cy が入れ替わっていた)。

    fail-closed: 視点が 3 未満、すべての視点が正面平行(回転不足)で解が定まらない、
    または K が非有限/非正になる場合は ``ValueError``(NaN を返さない)。戻り値の
    ``homographies`` は (x,y)→(x=col,y=row) の 3x3、``reproj_rms`` は各視点の
    ホモグラフィ再投影 RMS [px](対応づけの健全性チェックに使う)。

    ``orientation_rank_ratio`` は視点の向きが内部パラメータをどれだけ拘束して
    いるか(``sv[-2]/sv[0]``、大きいほど良い)。**再投影誤差は配置の良し悪しを
    映さない** —— 2026-09-06 の実測で、同じ 10 視点・同じ雑音 0.05 px で板の
    傾きだけを 32 度から 2 度に変えると、再投影 RMS は 0.0690 と 0.0688 で
    比 1.00 倍のまま、fx の誤差は 0.026 % から **7.33 %(281 倍)**になった。
    この比のほうは 129 倍動く。ただし**歪み補正前の点では意味を持たない**
    (下の門の注記を見よ)。
    """
    obj = _finite_array(object_points, "object_points", "camera_calibration", cols=2)
    views = [np.asarray(ip, float).reshape(-1, 2) for ip in image_points_list]
    if len(views) < 3:
        raise ValueError(f"camera_calibration needs >= 3 views (got {len(views)}); "
                         "Zhang's method solves 5 intrinsics from 2 constraints per view")
    for k, ip in enumerate(views):
        if len(ip) != len(obj) or len(ip) < 4:
            raise ValueError(f"view {k}: {len(ip)} image points vs {len(obj)} object points "
                             "(need equal counts, >= 4)")
        if not np.all(np.isfinite(ip)):
            raise ValueError(f"view {k}: non-finite image points")
    Hs, reproj = [], []
    for ip in views:
        xy = ip[:, ::-1]                                   # (row,col) -> (x=col, y=row)
        H = _homography_dlt(obj, xy)
        Hs.append(H)
        pr = image_to_world_plane(obj, H)                  # obj -> pixels (x,y)
        reproj.append(float(np.sqrt(np.mean(np.sum((pr - xy) ** 2, axis=1)))))
    V = []
    for H in Hs:
        V.append(_vij(H, 0, 1))
        V.append(_vij(H, 0, 0) - _vij(H, 1, 1))
    V = np.asarray(V)
    _, sv, Vt = np.linalg.svd(V, full_matrices=V.shape[0] < V.shape[1])
    # 正面平行ばかりの視点では零空間が 2 次元以上になり b が定まらない(Zhang 1999 §3.3)。
    #
    # ★ この門が**実カメラでは発火しない**ことを 2026-09-06 に実測した。歪みの
    #   無い合成では設計どおり働く(傾き 0 度で比 3.8e-14、0.05 度で 8.6e-10、
    #   どちらも拒否)。ところが現実的な樽型歪み k1=-0.18 を入れると、平面
    #   ホモグラフィのモデルがそもそも合わなくなり、比が**傾きに関係なく
    #   1.9e-06 前後に張り付く**(0 度 1.916e-06 / 0.05 度 1.935e-06 /
    #   0.2 度 2.005e-06)。
    #   ★ 条件は 2 つ揃ったときだけ: **歪みがある**ことと、**視点間で板が横に
    #   動く**こと。どちらか片方なら門は設計どおり鳴る(切り分けは
    #   tests/test_calib.py の 3 本)。そして実際の校正セッションは、板を手で
    #   動かして撮るのだから必ず両方が揃う。
    #   しきい値を上げれば済む話でもない —— 歪みありでは
    #   完全退化 1.92e-06 と傾き 2 度 4.42e-06 の差が 2.3 倍しかなく、
    #   分ける線が引けない。よって:
    #     * しきい値はそのまま(歪み補正済みの点なら正しく効く)
    #     * 比そのものを ``orientation_rank_ratio`` として**返す**
    #     * 実際に止めている後段の門に「板を傾けよ」を言わせる(下)
    #   直せない代わりに、判断材料を利用者に渡す。
    rank_ratio = float(sv[-2] / sv[0]) if sv[0] > 0.0 else 0.0
    if rank_ratio <= 1e-8:
        raise ValueError("degenerate calibration views: the plane orientations do not "
                         "constrain the intrinsics (all views fronto-parallel or only "
                         "rotated about the optical axis) — tilt the target between views")
    b = Vt[-1]
    B = np.array([[b[0], b[1], b[3]], [b[1], b[2], b[4]], [b[3], b[4], b[5]]])
    den = B[0, 0] * B[1, 1] - B[0, 1] ** 2
    with np.errstate(all="ignore"):
        cy = (B[0, 1] * B[0, 2] - B[0, 0] * B[1, 2]) / den
        lam = B[2, 2] - (B[0, 2] ** 2 + cy * (B[0, 1] * B[0, 2] - B[0, 0] * B[1, 2])) / B[0, 0]
        fx = np.sqrt(lam / B[0, 0])
        fy = np.sqrt(lam * B[0, 0] / den)
        skew = -B[0, 1] * fx * fx * fy / lam
        cx = skew * cy / fy - B[0, 2] * fx * fx / lam
    out = np.array([fx, fy, cx, cy, skew], float)
    if not np.all(np.isfinite(out)) or fx <= 0 or fy <= 0:
        raise ValueError("camera_calibration produced a non-finite or non-positive K "
                         f"(fx={fx}, fy={fy}, cx={cx}, cy={cy}); check the point "
                         "correspondences ((x,y) object / (row,col) image) and view "
                         "geometry — **the usual cause is that the target is not tilted "
                         "enough between views**, which the degeneracy check above cannot "
                         f"see once lens distortion is present (rank ratio {rank_ratio:.2e}; "
                         "distortion pins it near 2e-06 whatever the tilt)")
    return {"fx": float(fx), "fy": float(fy), "cx": float(cx), "cy": float(cy),
            "skew": float(skew), "homographies": Hs, "reproj_rms": reproj,
            # 視点の向きが内部パラメータをどれだけ拘束しているか(大きいほど良い)。
            # **歪み補正前の点では意味を持たない** —— 上の注記の実測を見よ。
            "orientation_rank_ratio": rank_ratio}


def calibrate_cameras(object_points, image_points_list):
    """Zhang 法カメラ校正(calibrate_cameras)。camera_calibration の別名。"""
    return camera_calibration(object_points, image_points_list)


# ── Tsai-Lenz ハンドアイ校正(AX = XB)──────────────────────────────────────────── #
def _rot_to_axis(R):
    """回転行列から回転ベクトル(軸*角)を返す。"""
    ang = np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))
    if ang < 1e-9:
        return np.zeros(3)
    ax = np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return ax / (2 * np.sin(ang)) * ang


def _axis_to_rot(v):
    ang = np.linalg.norm(v)
    if ang < 1e-12:
        return np.eye(3)
    ax = v / ang
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + np.sin(ang) * K + (1 - np.cos(ang)) * (K @ K)


def hand_eye_calibration(poses_a, poses_b):
    """一連の運動対から AX=XB を解き X(4x4)を推定(hand_eye_calibration)。

    fail-closed: 姿勢が 3 未満・組の数が合わない・非有限・相対運動の回転軸が 1 方向にしか
    散っていない(X の回転が決まらない)ときは ``ValueError``。

    poses_a/poses_b: 4x4 剛体変換のリスト。隣接運動から相対運動を構成。"""
    op = "hand_eye_calibration"
    A = [_pose_matrix(p, op, "poses_a[%d]" % i) for i, p in enumerate(poses_a)]
    B = [_pose_matrix(p, op, "poses_b[%d]" % i) for i, p in enumerate(poses_b)]
    if len(A) != len(B):
        raise ValueError("%s: poses_a and poses_b must pair up, got %d and %d poses"
                         % (op, len(A), len(B)))
    if len(A) < 3:
        raise ValueError("%s: needs >= 3 poses (>= 2 relative motions with different rotation "
                         "axes) to fix the rotation, got %d" % (op, len(A)))
    # 回転: 相対運動の回転軸から最小二乗で Rx を解く(修正 Rodrigues)
    Msum = np.zeros((3, 3)); bsum = np.zeros(3)
    rels = []
    for i in range(len(A) - 1):
        Ma = np.linalg.inv(A[i]) @ A[i + 1]
        Mb = np.linalg.inv(B[i]) @ B[i + 1]
        rels.append((Ma, Mb))
        alpha = _rot_to_axis(Ma[:3, :3]); beta = _rot_to_axis(Mb[:3, :3])
        # Park-Martin/Procrustes: Rx beta ~= alpha なので M = sum(alpha beta^T)
        Msum += np.outer(alpha, beta)
    U, S, Vt = np.linalg.svd(Msum)
    # 回転軸が 1 方向にしか散っていないと Procrustes の行列がランク落ちし、
    # 軸まわりの回転が決まらない(それでも行列は返る = 静かな誤り)。手前で拒む。
    if S[0] <= 0.0 or S[1] <= 1e-9 * S[0]:
        raise ValueError("%s: the relative motions rotate about a single axis (or not at all) — "
                         "the rotation of X is not determined; move about >= 2 different axes"
                         % op)
    d = np.sign(np.linalg.det(U @ Vt))
    Rx = U @ np.diag([1, 1, d]) @ Vt
    # 並進: (Ra - I) tx = Rx tb - ta
    Ct = []; dt = []
    for Ma, Mb in rels:
        Ct.append(Ma[:3, :3] - np.eye(3))
        dt.append(Rx @ Mb[:3, 3] - Ma[:3, 3])
    tx, *_ = np.linalg.lstsq(np.vstack(Ct), np.concatenate(dt), rcond=None)
    X = np.eye(4); X[:3, :3] = Rx; X[:3, 3] = tx
    return X


def calibrate_hand_eye(poses_a, poses_b):
    """ハンドアイ校正(calibrate_hand_eye)。hand_eye_calibration の別名。"""
    return hand_eye_calibration(poses_a, poses_b)
