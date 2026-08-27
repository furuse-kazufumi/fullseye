"""Ground-truth tests for silhouette space-carving (visual hull).

すべて閉形式/既知値で検証する:
- 射影は camera 規約(X_cam = R X + t, pixel = K X_cam を w 除算)通りの既知画素に落ちる。
- 凸物体(球・軸整列箱)の visual hull は「真の物体 voxel の上位集合」(recall 1.0)
  かつ十分 tight(IoU が閾値超え)。凸物体は多視点で hull ≈ 物体になるという定理の数値確認。
- 単視点では視錐(奥行きに伸びる錐台)しか制約できず全く tight でないことを honest に確認。

tolerance の根拠は各アサート脇のコメントに明記。近似手法(離散化)の系統誤差のみ許容。
"""
import numpy as np

import visualhull as vh


# --- helpers ---------------------------------------------------------------- #
def _K(f: float, cx: float, cy: float) -> np.ndarray:
    return np.array([[f, 0.0, cx], [0.0, f, cy], [0.0, 0.0, 1.0]])


def _fibonacci_cameras(n: int, dist: float):
    """dist 半径の球面に n 台のカメラを準等間隔配置し原点を見る (Ks, Rs, ts)。

    fibonacci-sphere で全方位(仰角込み)をカバー -> 球/箱の visual hull が top/bottom も
    彫られ tight になる。単一赤道リングだと縦方向が彫れず円柱状になるので仰角分散が要。"""
    K = _K(250.0, 100.0, 100.0)
    Ks, Rs, ts = [], [], []
    ga = np.pi * (3.0 - np.sqrt(5.0))                      # golden angle
    for i in range(n):
        z = 1.0 - 2.0 * (i + 0.5) / n                     # -1..1
        r = np.sqrt(max(0.0, 1.0 - z * z))
        phi = ga * i
        eye = dist * np.array([r * np.cos(phi), r * np.sin(phi), z])
        R, t = vh.look_at(eye, target=(0, 0, 0), up=(0, 0, 1))
        Ks.append(K)
        Rs.append(R)
        ts.append(t)
    return Ks, Rs, ts


def _solid_ball(radius: float, n: int = 48, n_surf: int = 20000) -> np.ndarray:
    """半径 radius の中身の詰まった球点群(内部=格子 + 表面=fibonacci 殻)。

    内部格子だけだと limb 方向の最外サンプルが radius にわずかに届かず、射影シルエットが
    真球より内側に痩せて境界 voxel を取りこぼす。物体の実表面は radius ちょうどなので、
    半径ぴったりの表面殻を明示的に密サンプルして本来の輪郭(limb)まで覆わせる。"""
    g = np.linspace(-radius, radius, n)
    X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
    inner = np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)
    inner = inner[np.linalg.norm(inner, axis=1) <= radius]
    # fibonacci-sphere で単位球面を準等間隔サンプル -> radius 倍した表面殻
    i = np.arange(n_surf) + 0.5
    z = 1.0 - 2.0 * i / n_surf
    r = np.sqrt(np.clip(1.0 - z * z, 0.0, None))
    phi = np.pi * (3.0 - np.sqrt(5.0)) * i
    surf = radius * np.stack([r * np.cos(phi), r * np.sin(phi), z], axis=1)
    return np.vstack([inner, surf])


def _solid_box(hx: float, hy: float, hz: float, n: int = 40) -> np.ndarray:
    """半幅 (hx,hy,hz) の中身の詰まった軸整列箱の点群(格子サンプル)。"""
    X, Y, Z = np.meshgrid(np.linspace(-hx, hx, n),
                          np.linspace(-hy, hy, n),
                          np.linspace(-hz, hz, n), indexing="ij")
    return np.stack([X.ravel(), Y.ravel(), Z.ravel()], axis=1)


def _voxel_centers(bounds, res):
    (xmin, xmax), (ymin, ymax), (zmin, zmax) = bounds
    xs = xmin + (np.arange(res) + 0.5) * (xmax - xmin) / res
    ys = ymin + (np.arange(res) + 0.5) * (ymax - ymin) / res
    zs = zmin + (np.arange(res) + 0.5) * (zmax - zmin) / res
    return np.meshgrid(xs, ys, zs, indexing="ij")   # X, Y, Z each (res,res,res)


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = np.count_nonzero(a & b)
    union = np.count_nonzero(a | b)
    return inter / union if union else 1.0


def _recall(recon: np.ndarray, truth: np.ndarray) -> float:
    tp = np.count_nonzero(recon & truth)
    n = np.count_nonzero(truth)
    return tp / n if n else 1.0


# --- projection ground truth ------------------------------------------------ #
def test_synthesize_projects_to_known_pixel():
    # R=I, t=(0,0,2): X_cam = X + (0,0,2). f=200, cx=cy=64.
    K = _K(200.0, 64.0, 64.0)
    R = np.eye(3)
    t = np.array([0.0, 0.0, 2.0])
    # X=(0.1,0,0) -> X_cam=(0.1,0,2) -> u = 200*0.1/2 + 64 = 74, v = 64
    sil = vh.synthesize_silhouette(np.array([[0.1, 0.0, 0.0]]), K, R, t,
                                   size=(128, 128), fill=False, dilate=0)
    assert sil[64, 74]                               # 閉形式で求めた画素が前景
    assert sil.sum() == 1                            # dilate=0,fill=False で厳密に 1 画素


def test_synthesize_filters_points_behind_camera():
    K = _K(200.0, 64.0, 64.0)
    R = np.eye(3)
    t = np.array([0.0, 0.0, -2.0])                   # 点は z=-2 (カメラ後方) へ
    sil = vh.synthesize_silhouette(np.array([[0.0, 0.0, 0.0]]), K, R, t,
                                   size=(128, 128), fill=False, dilate=0)
    assert sil.sum() == 0                            # depth<=0 は棄却 -> 空


# --- sphere: superset (recall 1.0) + tight (high IoU) ----------------------- #
def test_sphere_visual_hull_is_superset_and_tight():
    radius = 1.0
    pts = _solid_ball(radius)
    Ks, Rs, ts = _fibonacci_cameras(20, dist=4.0)    # N=20 >= 12, full-sphere coverage
    sils = [vh.synthesize_silhouette(pts, K, R, t, size=(200, 200))
            for K, R, t in zip(Ks, Rs, ts)]

    bounds = ((-1.5, 1.5), (-1.5, 1.5), (-1.5, 1.5))
    res = 24
    recon = vh.visual_hull(sils, Ks, Rs, ts, bounds, res)

    X, Y, Z = _voxel_centers(bounds, res)
    truth = (np.sqrt(X ** 2 + Y ** 2 + Z ** 2) <= radius)

    # recall 1.0: visual hull は連続空間で物体の上位集合。coverage シルエット(fill+1px
    # dilate)で離散化誤差下でも真の球 voxel を 1 つも取りこぼさない。
    assert _recall(recon, truth) == 1.0
    assert np.all(recon[truth])                      # 上位集合(球内 voxel を全包含)

    # tight: 凸物体は多視点で hull ≈ 物体。IoU 閾値 0.6 は honest な下限 —
    # 実際は視点数/解像度で 0.8+ 出るが、(a) hull は N 個の錐の交差で球に外接する
    # 微小な多面体的膨らみ (b) pixel/voxel 各 1 セルの離散化誤差 (c) 保守側 1px dilate、
    # の 3 つで真球からわずかに太る分を見込んで 0.6 に設定。
    assert _iou(recon, truth) > 0.6


# --- box -> box ------------------------------------------------------------- #
def test_box_visual_hull_recovers_box():
    hx, hy, hz = 0.8, 0.6, 0.7
    pts = _solid_box(hx, hy, hz)
    Ks, Rs, ts = _fibonacci_cameras(20, dist=4.0)
    sils = [vh.synthesize_silhouette(pts, K, R, t, size=(200, 200))
            for K, R, t in zip(Ks, Rs, ts)]

    bounds = ((-1.2, 1.2), (-1.2, 1.2), (-1.2, 1.2))
    res = 24
    recon = vh.carve(sils, Ks, Rs, ts, bounds, res)

    X, Y, Z = _voxel_centers(bounds, res)
    truth = (np.abs(X) <= hx) & (np.abs(Y) <= hy) & (np.abs(Z) <= hz)

    assert _recall(recon, truth) == 1.0              # 軸整列箱も上位集合(取りこぼしなし)
    assert np.all(recon[truth])
    # 箱は凸なので hull は箱に外接。0.6 は上と同根拠(角の面取り+離散化+dilate)。
    assert _iou(recon, truth) > 0.6


# --- single view is a frustum, not tight ------------------------------------ #
def test_single_camera_is_not_tight():
    radius = 1.0
    pts = _solid_ball(radius)
    Ks, Rs, ts = _fibonacci_cameras(20, dist=4.0)
    bounds = ((-1.5, 1.5), (-1.5, 1.5), (-1.5, 1.5))
    res = 24

    X, Y, Z = _voxel_centers(bounds, res)
    truth = (np.sqrt(X ** 2 + Y ** 2 + Z ** 2) <= radius)

    # 1 台だけ
    sil0 = vh.synthesize_silhouette(pts, Ks[0], Rs[0], ts[0], size=(200, 200))
    recon1 = vh.visual_hull([sil0], [Ks[0]], [Rs[0]], [ts[0]], bounds, res)

    # 全台
    sils = [vh.synthesize_silhouette(pts, K, R, t, size=(200, 200))
            for K, R, t in zip(Ks, Rs, ts)]
    recon_all = vh.visual_hull(sils, Ks, Rs, ts, bounds, res)

    # 単視点でも物体の上位集合ではある(視錐は物体を含む)-> recall 1.0
    assert _recall(recon1, truth) == 1.0
    # だが奥行き方向に錐台として伸び、全く tight でない: voxel 数が真の球より遥かに多く、
    # 多視点解より緩い。閾値は「錐台 >> 球」を示す保守値。bounds が物体に密着(±1.5)なため
    # 錐台は途中で打ち切られ実測 ~2.6x(open な bounds ならさらに伸びる)。
    n_true = int(truth.sum())
    assert int(recon1.sum()) > 2 * n_true            # 錐台は球体積の 2 倍超に膨れる(実測 ~2.6x)
    assert int(recon1.sum()) > 2 * int(recon_all.sum())  # 多視点解よりずっと緩い(実測 ~2.5x)
    assert _iou(recon1, truth) < 0.4                 # tight でない(多視点は >0.6)
    assert _iou(recon_all, truth) > _iou(recon1, truth)
