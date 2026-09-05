"""校正ターゲット(caltab)生成・検出とワールド平面マップ(HALCON "Calibration" genuine, numpy).

円マーク格子の校正板を生成・シミュレート・画像から検出し、ワールド平面写像を作る。
image = 2D float64。マーク座標は (row, col)。

座標規約: ``create_caltab`` の ``points`` は **板の中心を原点**にした (y, x) [mm]
(HALCON の caltab と同じく板中心が世界原点)。``sim_caltab`` と ``find_marks_and_pose``
はこの ``points`` をそのまま world (x, y, 0) として使うので、シミュレートに渡した
``pose`` と復元される ``pose`` は同じ座標系で直接比較できる(2026-09-02 以前は
sim 側だけが中心化していて t が R·(30,30,0) だけずれていた)。
``caltab_points`` は生の格子(原点=最初のマーク)を返す低レベル関数のまま。
"""
from __future__ import annotations

import numpy as np


def caltab_points(rows=7, cols=7, spacing=1.0):
    """校正板の理想マーク座標(ワールド, mm; 原点=最初のマーク)を (y, x) で返す(caltab_points)。"""
    r, c = np.mgrid[0:rows, 0:cols]
    x = c.ravel() * spacing; y = r.ravel() * spacing
    return np.column_stack([y, x]).astype(np.float64)


def gen_caltab(rows=7, cols=7, spacing=1.0, radius=0.3, image_size=256):
    """円マーク格子の校正板画像を生成(gen_caltab)。"""
    img = np.zeros((image_size, image_size))
    margin = image_size * 0.1
    step = (image_size - 2 * margin) / max(rows - 1, cols - 1)
    yy, xx = np.mgrid[0:image_size, 0:image_size]
    centers = []
    for i in range(rows):
        for j in range(cols):
            cy = margin + i * step; cx = margin + j * step
            img[(yy - cy) ** 2 + (xx - cx) ** 2 <= (radius * step) ** 2] = 1.0
            centers.append([cy, cx])
    return {"image": img, "centers": np.asarray(centers), "rows": rows, "cols": cols}


def create_caltab(rows=7, cols=7, spacing=1.0):
    """校正板の記述(理想点、板中心が原点)を作る(create_caltab)。"""
    pts = caltab_points(rows, cols, spacing)
    pts = pts - pts.mean(0)
    return {"points": pts, "rows": rows, "cols": cols, "spacing": float(spacing),
            "origin": "center"}


def _ideal_points(caltab):
    return caltab["points"] if isinstance(caltab, dict) and "points" in caltab else caltab_points()


def sim_caltab(caltab, cam_par, pose, image_size=256, mark_radius=3.0):
    """校正板を指定カメラ姿勢で投影した画像をシミュレート(sim_caltab)。
    world = (x, y, 0) with (y, x) = ``caltab["points"]`` そのまま(中心化しない)。"""
    from calib import project_3d_point
    pts = _ideal_points(caltab)
    world = np.column_stack([pts[:, 1], pts[:, 0], np.zeros(len(pts))])
    px = project_3d_point(world, cam_par, pose)
    img = np.zeros((image_size, image_size)); yy, xx = np.mgrid[0:image_size, 0:image_size]
    for row, col in px:
        if 0 <= row < image_size and 0 <= col < image_size:
            img[(yy - row) ** 2 + (xx - col) ** 2 <= mark_radius ** 2] = 1.0
    return {"image": img, "marks": px}


def disp_caltab(caltab):
    """校正板画像を返す(表示用)(disp_caltab)。"""
    return caltab["image"] if isinstance(caltab, dict) and "image" in caltab else caltab


def find_caltab(image, thresh=0.5):
    """画像から校正板の円マーク中心を検出(連結成分の重心)(find_caltab)。"""
    from scipy import ndimage
    m = np.asarray(image, float) > thresh
    lab, n = ndimage.label(m)
    if n == 0:
        return np.zeros((0, 2))
    centers = ndimage.center_of_mass(m, lab, range(1, n + 1))
    return np.asarray(centers)


def find_calib_object(image, thresh=0.5):
    """校正オブジェクト(マーク)を検出(find_calib_object)。find_caltab の別名。"""
    return {"marks": find_caltab(image, thresh)}


# ── 対応づけ(ホモグラフィ誘導)────────────────────────────────────────────── #
def _dlt_normalized(src, dst):
    """Hartley 正規化つき DLT: dst ~ H src(両方 (x, y))。"""
    src = np.asarray(src, float); dst = np.asarray(dst, float)

    def norm_T(p):
        c = p.mean(0)
        s = np.sqrt(2.0) / (np.mean(np.linalg.norm(p - c, axis=1)) + 1e-12)
        return np.array([[s, 0, -s * c[0]], [0, s, -s * c[1]], [0, 0, 1.0]])
    Ts, Td = norm_T(src), norm_T(dst)
    sh = np.column_stack([src, np.ones(len(src))]) @ Ts.T
    dh = np.column_stack([dst, np.ones(len(dst))]) @ Td.T
    A = []
    for (x, y, _), (u, v, _) in zip(sh, dh):
        A.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        A.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _, _, Vt = np.linalg.svd(np.asarray(A))
    Hn = Vt[-1].reshape(3, 3)
    H = np.linalg.inv(Td) @ Hn @ Ts
    return H / H[2, 2]


def _apply_h(H, p):
    h = np.column_stack([p, np.ones(len(p))]) @ H.T
    return h[:, :2] / h[:, 2:3]


def _corners(p):
    """(N,2) 点集合の 4 隅(左上/右上/左下/右下 = a+b, a-b の極値)の index。"""
    s, d = p[:, 0] + p[:, 1], p[:, 0] - p[:, 1]
    return np.array([int(np.argmin(s)), int(np.argmin(d)), int(np.argmax(d)), int(np.argmax(s))])


def _assign(proj, marks, max_dist):
    """投影理想点 → 最近傍マーク(距離 < max_dist、1 対 1)。(ideal_idx, mark_idx) を返す。"""
    dmat = np.linalg.norm(proj[:, None, :] - marks[None, :, :], axis=2)
    pairs = []
    used = set()
    order = np.argsort(dmat, axis=None)
    for flat in order:
        i, j = divmod(int(flat), dmat.shape[1])
        if dmat[i, j] > max_dist:
            break
        if j in used or any(i == a for a, _ in pairs):
            continue
        pairs.append((i, j)); used.add(j)
    if not pairs:
        return np.zeros(0, int), np.zeros(0, int)
    pairs.sort()
    a = np.array(pairs)
    return a[:, 0], a[:, 1]


def find_marks_and_pose(image, cam_par, caltab, thresh=0.5, max_reproj_rms=3.0):
    """マーク検出 + 校正板の姿勢推定(平面ホモグラフィ → pose)(find_marks_and_pose)。

    対応づけは行優先ソートではなく **ホモグラフィ誘導**: 検出マークと理想格子の 4 隅
    (row±col の極値)から初期 H を作り、理想点を投影して最近傍マークを 1 対 1 に
    割り当て、全対応で H を再推定(2 反復)。板の面内回転が ±45° 未満なら傾き
    (rx, ry)の大きさに関係なく正しく対応する(2026-09-02 以前は少しの傾きで
    行が交錯し、深度が数百 mm ずれても無警告だった)。

    fail-closed: マークが 4 個未満/対応が 4 組未満/再投影 RMS が
    ``max_reproj_rms`` [px] を超えるときは ``ValueError``(``None`` で無効化可)。
    戻り値: ``marks`` (M,2) 対応づいた検出マーク(``ideal_index`` の順)、``pose`` 4x4、
    ``homography`` (x,y)→(col,row)、``reproj_rms`` [px]、``residuals`` (M,)、``n_marks``。
    world は ``caltab["points"]`` の (y, x) をそのまま (x, y, 0) とする。
    """
    from calib import _K
    from transforms import proj_hom_mat2d_to_pose
    marks = find_caltab(image, thresh)
    ideal = _ideal_points(caltab)
    K = _K(cam_par)
    if len(marks) < 4 or len(ideal) < 4:
        raise ValueError(f"find_marks_and_pose: need >= 4 marks (detected {len(marks)}, "
                         f"ideal {len(ideal)})")
    world_xy = ideal[:, ::-1]                               # (y,x) -> (x,y)
    marks_xy = marks[:, ::-1]                               # (row,col) -> (x,y)
    ci, cm = _corners(ideal), _corners(marks)
    if len(set(cm.tolist())) < 4:
        raise ValueError("find_marks_and_pose: could not identify 4 distinct plate corners")
    H = _dlt_normalized(world_xy[ci], marks_xy[cm])
    ii = jj = None
    for _ in range(3):
        proj = _apply_h(H, world_xy)
        # 格子ピッチ(画素)= 投影理想点の最近傍距離の中央値
        dd = np.linalg.norm(proj[:, None] - proj[None, :], axis=2)
        np.fill_diagonal(dd, np.inf)
        pitch = float(np.median(dd.min(1)))
        ii, jj = _assign(proj, marks_xy, 0.45 * pitch)
        if len(ii) < 4:
            raise ValueError(f"find_marks_and_pose: only {len(ii)} ideal/detected correspondences "
                             "within half a pitch — plate not found or rotated beyond ±45°")
        H = _dlt_normalized(world_xy[ii], marks_xy[jj])
    pose = proj_hom_mat2d_to_pose(H, K)
    if pose[2, 3] < 0:                                      # 板はカメラの前にある
        pose = proj_hom_mat2d_to_pose(-H, K)
    # ホモグラフィ分解は初期値。再投影誤差を姿勢 6 自由度で非線形最小化して仕上げる。
    world3 = np.column_stack([world_xy[ii], np.zeros(len(ii))])
    pose, residuals = _refine_pose(world3, marks[jj], K, pose)
    rms = float(np.sqrt(np.mean(residuals ** 2)))
    # ★このゲートが**捕まえないもの**: 一枚の平面ターゲットに対する内部パラメータの
    # 誤り(特に fx/fy の比)。平面 1 枚の homography は内部パラメータに 2 つしか
    # 拘束を与えない(Zhang 2000)ので、誤った fy はここで解いている姿勢 6 自由度に
    # ほとんど吸収され、残差はしきい値の下に留まりうる。
    # 実測 2026-09-05: fy を 500 → 300 と誤らせても Linux/scipy 1.18 では RMS 0.90 px
    # (正しい K なら 0.14 px)。同じ入力が Windows/旧 scipy では 6.39 px になり、
    # **最適化の収束先の違いだけで「検出できたりできなかったり」する**。
    # 内部パラメータを検証したいなら、視点を 3 枚以上取るか非平面のターゲットを使う。
    # ここが効くのは「姿勢では吸収できない」不整合(対応付けの誤り、非平面の板)。
    if max_reproj_rms is not None and rms > max_reproj_rms:
        raise ValueError(f"find_marks_and_pose: pose reprojection RMS {rms:.2f} px > "
                         f"{max_reproj_rms} px — correspondence or calibration is wrong")
    return {"marks": marks[jj], "ideal_index": ii, "pose": pose, "homography": H,
            "reproj_rms": rms, "residuals": residuals, "n_marks": int(len(marks))}


def _rotvec_to_mat(v):
    from calib import _axis_to_rot
    return _axis_to_rot(np.asarray(v, float))


def _mat_to_rotvec(R):
    from calib import _rot_to_axis
    return _rot_to_axis(np.asarray(R, float))


def _refine_pose(world3, marks_rc, K, pose0):
    """world (N,3) ↔ 画素 (row,col) の再投影誤差を (回転ベクトル, t) の 6 自由度で
    最小化(Levenberg-Marquardt, scipy)。(pose 4x4, 各点の残差ノルム) を返す。"""
    from scipy.optimize import least_squares
    from calib import project_3d_point
    p0 = np.concatenate([_mat_to_rotvec(pose0[:3, :3]), pose0[:3, 3]])

    def make_pose(p):
        T = np.eye(4); T[:3, :3] = _rotvec_to_mat(p[:3]); T[:3, 3] = p[3:]
        return T

    def resid(p):
        return (project_3d_point(world3, K, make_pose(p)) - marks_rc).ravel()
    sol = least_squares(resid, p0, method="lm", xtol=1e-12, ftol=1e-12, max_nfev=200)
    pose = make_pose(sol.x)
    r = resid(sol.x).reshape(-1, 2)
    return pose, np.linalg.norm(r, axis=1)


def gen_image_to_world_plane_map(cam_par, pose, shape, scale=1.0):
    """画像→ワールド平面(z=0)の写像テーブルを生成(gen_image_to_world_plane_map)。"""
    from calib import image_points_to_world_plane
    H, W = shape
    rr, cc = np.mgrid[0:H, 0:W]
    px = np.column_stack([rr.ravel(), cc.ravel()])
    world = image_points_to_world_plane(cam_par, pose, px, scale)
    return {"x_map": world[:, 1].reshape(H, W), "y_map": world[:, 0].reshape(H, W)}


def binocular_calibration(object_points, image_points_left, image_points_right):
    """左右カメラを Zhang で個別校正しステレオ相対姿勢を推定(binocular_calibration)。
    引数規約は ``calib.camera_calibration`` と同じ(object (x,y) / image (row,col))。"""
    from calib import camera_calibration
    cl = camera_calibration(object_points, image_points_left)
    cr = camera_calibration(object_points, image_points_right)
    return {"left": cl, "right": cr,
            "note": "相対姿勢は各視点の外部パラメータ差から算出(簡易)"}
