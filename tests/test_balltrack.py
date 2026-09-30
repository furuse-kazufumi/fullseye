"""balltrack の門: 投影の整合 / DLT 三角測量 / 軌跡の三角測量 / 等加速度 Kalman / 模様からのスピン / 跳ねの検出 / 検出と追跡 / fail-closed。"""
import numpy as np
import pytest

import ballistics as B
import balltrack as BT
import driveworld as DW
import drivettc as TT

ORANGE = (1.0, 0.55, 0.05)


def _two_cams():
    """640×480・fov 50° のカメラ 2 台(台の両側の斜め上、原点あたりを見る)。"""
    K = DW.camera_intrinsics(50.0, 640, 480)
    P1 = DW.camera_pose((-2.5, 1.5, 1.6), (0.0, 0.0, 0.9))
    P2 = DW.camera_pose((2.5, -1.4, 1.5), (0.0, 0.0, 0.9))
    return K, P1, P2


def _points(n=50, seed=0):
    pts = np.random.default_rng(seed).uniform(-1, 1, (n, 3))
    pts[:, 2] += 0.9
    return pts


def _rodrigues(omega, dt):
    w = np.asarray(omega, np.float64)
    th = np.linalg.norm(w) * dt
    a = w / np.linalg.norm(w)
    Kx = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(th) * Kx + (1 - np.cos(th)) * Kx @ Kx


def _parabola(dt=1 / 200, t_end=1.0):
    t = np.arange(0, t_end, dt)
    return B.flight_vacuum([0, 0, 1], [3, 0.5, 4], t)


def _disc(cx=40.3, cy=60.7, r=6.2, shape=(100, 120)):
    rr, cc = np.mgrid[0:shape[0], 0:shape[1]]
    return np.hypot(cc - cx, rr - cy) < r


# ─────────────────────────────── 投影 ───────────────────────────────────────

def test_reproject_matches_camera_project_and_marks_points_behind():
    """reproject = pose で変換した点に drivettc.camera_project を当てたもの(1e-9)。カメラの背後の点は NaN。pose が 4×4 でなければ ValueError。"""
    K, P1, _ = _two_cams()
    pts = _points()
    uv = BT.reproject(pts, P1, K)
    Pc = (np.column_stack([pts, np.ones(len(pts))]) @ P1.T)[:, :3]
    col, row, depth = TT.camera_project(Pc, K)
    assert (depth > 0).all() and np.isfinite(uv).all()
    assert np.abs(uv[:, 0] - col).max() < 1e-9 and np.abs(uv[:, 1] - row).max() < 1e-9
    behind = np.array([[-5.0, 3.0, 2.0], [-4.0, 2.5, 1.9]])      # 視線の反対側(eye の後ろ)
    uvb = BT.reproject(behind, P1, K)
    assert np.isnan(uvb).all()
    with pytest.raises(ValueError):
        BT.reproject(pts, np.eye(3), K)


# ─────────────────────────────── 三角測量 ─────────────────────────────────────

def test_triangulate_dlt_recovers_exact_points():
    """真の投影 2 視点から 50 点が 1e-9 で戻り、再投影 rms < 1e-9、n_views = 2。"""
    K, P1, P2 = _two_cams()
    pts = _points()
    uv1, uv2 = BT.reproject(pts, P1, K), BT.reproject(pts, P2, K)
    for i in range(len(pts)):
        t = BT.triangulate_dlt([uv1[i], uv2[i]], [P1, P2], [K, K])
        assert np.linalg.norm(t["p"] - pts[i]) < 1e-9 and t["reproj_rms"] < 1e-9 and t["n_views"] == 2


def test_triangulate_dlt_skips_nan_views_and_fails_closed():
    """3 視点のうち 1 つが NaN でも残り 2 視点で解く(n_views 2)。有限の視点が 2 未満なら ValueError。"""
    K, P1, P2 = _two_cams()
    pts = _points(5)
    uv1, uv2 = BT.reproject(pts, P1, K), BT.reproject(pts, P2, K)
    P3 = DW.camera_pose((0.5, 3.0, 2.0), (0.0, 0.0, 0.9))
    t = BT.triangulate_dlt([uv1[0], [np.nan, np.nan], uv2[0]], [P1, P3, P2], [K, K, K])
    assert t["n_views"] == 2 and np.linalg.norm(t["p"] - pts[0]) < 1e-9
    with pytest.raises(ValueError):
        BT.triangulate_dlt([uv1[0], [np.nan, np.nan]], [P1, P2], [K, K])
    with pytest.raises(ValueError):
        BT.triangulate_dlt([uv1[0]], [P1], [K])


def test_track_triangulate_stitches_partially_overlapping_tracks():
    """カメラ A(コマ 0–7)と B(コマ 4–11)の軌跡 → 両方で見えたコマ 4–7 だけが返り、位置は真値と一致(1e-9)。1 台だけなら空。"""
    K, P1, P2 = _two_cams()
    n = 12
    t = np.arange(n) / 200.0
    pts = B.flight_vacuum([-0.5, 0.1, 1.0], [3.0, 0.4, 2.0], t)
    uv1, uv2 = BT.reproject(pts, P1, K), BT.reproject(pts, P2, K)
    fa, fb = np.arange(0, 8), np.arange(4, 12)
    trA = {"frame": fa, "col": uv1[fa, 0], "row": uv1[fa, 1], "radius": np.full(len(fa), 3.0)}
    trB = {"frame": fb, "col": uv2[fb, 0], "row": uv2[fb, 1], "radius": np.full(len(fb), 3.0)}
    out = BT.track_triangulate([trA, trB], [P1, P2], [K, K], n)
    assert out["frame"].dtype == np.int64 and out["frame"].tolist() == [4, 5, 6, 7]
    assert out["p"].shape == (4, 3) and np.abs(out["p"] - pts[4:8]).max() < 1e-9
    assert out["reproj_rms"].shape == (4,) and out["reproj_rms"].max() < 1e-9
    empty = BT.track_triangulate([trA], [P1], [K], n)
    assert len(empty["frame"]) == 0 and empty["p"].shape == (0, 3)


# ─────────────────────────────── Kalman ─────────────────────────────────────

def test_kalman_ca_converges_on_an_exact_parabola():
    """真空の放物線(200 Hz, 1 s, q 1e-2, r 1e-9): 末尾 20 歩の新息 < 1e-9、加速度の推定 ≈ (0, 0, −9.81)(1e-6)、位置誤差 < 1e-9。
    雑音 1e-3・r 1e-6 でも末尾の位置誤差 < 2e-3。"""
    dt = 1 / 200
    p = _parabola(dt)
    kf = BT.kalman_ca(p, dt, q=1e-2, r=1e-9)
    assert kf["x"].shape == (len(p), 9) and kf["x_pred"].shape == (len(p), 9) and kf["P"].shape == (len(p), 9, 9)
    assert np.abs(kf["innovation"][-20:]).max() < 1e-9
    assert np.allclose(kf["x"][-1, 2::3], (0.0, 0.0, -B.G), atol=1e-6)
    assert np.abs(kf["x"][-1, 0::3] - p[-1]).max() < 1e-9
    noisy = p + np.random.default_rng(1).normal(0, 1e-3, p.shape)
    kf2 = BT.kalman_ca(noisy, dt, q=1e-2, r=1e-6)
    assert np.abs(kf2["x"][-1, 0::3] - p[-1]).max() < 2e-3


def test_kalman_ca_skips_nan_observations_and_keeps_predicting():
    """NaN の観測は飛ばし(そのコマの新息は NaN)、状態は予測で真値に乗り続ける。"""
    dt = 1 / 200
    p = _parabola(dt)
    gap = p.copy()
    gap[50] = np.nan
    gap[120:123] = np.nan
    kf = BT.kalman_ca(gap, dt, q=1e-2, r=1e-9)
    assert np.isnan(kf["innovation"][50]).all() and np.isnan(kf["innovation"][120:123]).all()
    assert np.isfinite(kf["innovation"][49]).all() and np.isfinite(kf["innovation"][123]).all()
    assert np.isfinite(kf["x"]).all() and np.isfinite(kf["P"]).all()
    assert np.abs(kf["x"][50, 0::3] - p[50]).max() < 1e-6
    assert np.abs(kf["x"][122, 0::3] - p[122]).max() < 1e-6
    assert np.abs(kf["x"][-1, 0::3] - p[-1]).max() < 1e-9


def test_kalman_ca_fails_closed():
    """(N,) の観測・dt ≤ 0・q < 0・r < 0 は ValueError。"""
    dt = 1 / 200
    p = _parabola(dt, 0.2)
    with pytest.raises(ValueError):
        BT.kalman_ca(p[:, 0], dt)
    with pytest.raises(ValueError):
        BT.kalman_ca(p, 0.0)
    with pytest.raises(ValueError):
        BT.kalman_ca(p, dt, q=-1.0)
    with pytest.raises(ValueError):
        BT.kalman_ca(p, dt, r=-1.0)


def test_kalman_ca_with_zero_observation_noise_tracks_observation():
    """r = 0(pinv の経路)でも落ちず、更新後の位置 = 観測。"""
    dt = 1 / 200
    t = np.arange(0, 0.5, dt)
    p = B.flight_vacuum([0.2, -0.1, 1], [2, 1, 3], t)
    kf = BT.kalman_ca(p, dt, q=1e-2, r=0.0)
    assert np.isfinite(kf["x"]).all()
    assert np.abs(kf["x"][:, 0::3] - p).max() < 1e-9


# ─────────────────────────────── スピン ─────────────────────────────────────

def test_spin_from_markers_recovers_known_omega():
    """既知の ω(dt 1/200)で回した 3 つの模様 → ω が 1e-9 で戻り full=True・rms < 1e-12。2 つでも厳密。形が合わなければ ValueError。"""
    w = np.array([50.0, -120.0, 300.0])
    dt = 1 / 200
    R = _rodrigues(w, dt)
    d0 = np.random.default_rng(2).normal(size=(3, 3))
    d0 /= np.linalg.norm(d0, axis=1, keepdims=True)
    d1 = d0 @ R.T
    s = BT.spin_from_markers(d0, d1, dt)
    assert s["full"] and np.abs(s["omega"] - w).max() < 1e-9 and s["rms"] < 1e-12
    assert abs(s["angle"] - np.linalg.norm(w) * dt) < 1e-9 and np.allclose(s["axis"], w / np.linalg.norm(w), atol=1e-9)
    assert np.abs(s["R"] - R).max() < 1e-9
    s2 = BT.spin_from_markers(d0[:2], d1[:2], dt)
    assert s2["full"] and np.abs(s2["omega"] - w).max() < 1e-9
    with pytest.raises(ValueError):
        BT.spin_from_markers(d0, d1[:2], dt)
    with pytest.raises(ValueError):
        BT.spin_from_markers(d0, d1, 0.0)


def test_spin_from_single_marker_is_the_minimal_rotation():
    """1 つの模様は full=False で、返る R は d₀ を d₁ に写し(1e-12)、ω は d₀ に直交。
    ω ⊥ d₀ なら模様は大円を描き最小回転 = 真の回転なので、dt = 1/2000 で ω の相対誤差 < 1e-9(実測 ~2e-16、仕様の 1 % より遥かに良い)。
    ω が d₀ に直交しないと軸まわりの成分は原理的に決まらない(相対誤差が大きい)。"""
    w = np.array([50.0, -120.0, 300.0])
    dt = 1 / 200
    d0 = np.random.default_rng(2).normal(size=3)
    d0 /= np.linalg.norm(d0)
    d1 = _rodrigues(w, dt) @ d0
    s1 = BT.spin_from_markers(d0[None], d1[None], dt)
    assert not s1["full"] and s1["rms"] == 0.0
    assert np.abs(s1["R"] @ d0 - d1).max() < 1e-12
    assert abs(s1["omega"] @ d0) < 1e-9
    assert np.linalg.norm(s1["omega"] - w) / np.linalg.norm(w) > 1e-3     # 一般の向きでは戻らない(正直な限界)
    perp = np.cross(w, [1.0, 0.0, 0.0])
    perp /= np.linalg.norm(perp)
    dts = 1 / 2000
    ss = BT.spin_from_markers(perp[None], (_rodrigues(w, dts) @ perp)[None], dts)
    assert np.linalg.norm(ss["omega"] - w) / np.linalg.norm(w) < 1e-9


def test_marker_direction_maps_disc_to_front_hemisphere():
    """円板の中心 → (0, 0, 1)、縁 → z = 0(単位ベクトル)、円板の外・半径 ≤ 0 は ValueError。"""
    c = (100.0, 80.0)
    assert np.allclose(BT.marker_direction(c, c, 10.0), (0, 0, 1))
    rim = BT.marker_direction((110.0, 80.0), c, 10.0)
    assert np.allclose(rim, (1, 0, 0), atol=1e-12)
    up = BT.marker_direction((100.0, 70.0), c, 10.0)                  # 行は下向きなので上の縁は +y
    assert np.allclose(up, (0, 1, 0), atol=1e-12)
    mid = BT.marker_direction((105.0, 84.0), c, 10.0)
    assert abs(np.linalg.norm(mid) - 1.0) < 1e-12 and mid[2] > 0
    with pytest.raises(ValueError):
        BT.marker_direction((111.0, 80.0), c, 10.0)
    with pytest.raises(ValueError):
        BT.marker_direction(c, c, 0.0)



def test_marker_direction_view_ray_correction():
    """K を渡すと透視で厳密に解く: 光軸上の球の中心の模様は (0, 0, 1)、光軸から外れた球でも真の向きと 1e-9 で一致し、
    正射影の形(K なし)は外れる(2026-09-30)。"""
    K = np.array([[800.0, 0, 320.0], [0, 800.0, 240.0], [0, 0, 1.0]])
    c = (320.0, 240.0)
    assert np.allclose(BT.marker_direction(c, c, 10.0, K), (0, 0, 1), atol=1e-12)
    r = 0.02
    C = np.array([0.25, -0.12, 0.6])                                   # カメラ系(x 右、y 下、z 前)、光軸から 24° 外れた球
    worst_plain, worst_k = 0.0, 0.0
    toward = -C / np.linalg.norm(C)
    rng = np.random.default_rng(3)
    for _ in range(40):
        n = toward + 0.5 * rng.normal(size=3)
        n /= np.linalg.norm(n)
        if n @ toward < 0.3:
            continue
        uv = lambda X: (K @ (X / X[2]))[:2]                             # noqa: E731
        cu = uv(C)
        rad = 800.0 * r / np.sqrt(C @ C - r * r)
        mu = uv(C + r * n)
        truth = np.array([n[0], -n[1], -n[2]])                          # この関数の系(x 右、y 上、z 手前)
        try:
            dp = BT.marker_direction(mu, cu, rad)
            dk = BT.marker_direction(mu, cu, rad, K)
        except ValueError:
            continue
        worst_plain = max(worst_plain, np.arccos(np.clip(dp @ truth, -1, 1)))
        worst_k = max(worst_k, float(np.linalg.norm(dk - truth)))           # arccos は 1 の近くで √ε しか分解できない
    assert worst_k < 1e-9 and worst_plain > 0.1, (worst_plain, worst_k)

# ─────────────────────────────── 跳ね ───────────────────────────────────────

def test_bounce_detect_finds_simulated_contacts():
    """真空(rho 0)・e 0.85 の落下を 200 Hz で標本化 → 最初の 3 接触が模擬の接触時刻から 1 コマ(5 ms)以内。標本が足りなければ ValueError。"""
    bp = B.ball_params(rho=0)
    sim = B.flight_simulate([0, 0, 0.5], [1, 0, 0], [0, 0, 0], bp, B.impact_params(0.85, 0.2), 1.5, 1e-3)
    t = np.arange(0, 1.5, 1 / 200)
    z = np.interp(t, sim["t"], sim["p"][:, 2])
    bd = BT.bounce_detect(t, z)
    truth = np.array([c["t"] for c in sim["contacts"]])
    assert len(truth) >= 3 and len(bd["t"]) >= 3
    assert np.abs(bd["t"][:3] - truth[:3]).max() < 5e-3 + 1e-12
    assert bd["index"].dtype == np.int64 and np.allclose(bd["z"], z[bd["index"]])
    assert (bd["z"][:3] < 0.5).all()
    with pytest.raises(ValueError):
        BT.bounce_detect([0.0, 1.0], [1.0, 0.0])
    with pytest.raises(ValueError):
        BT.bounce_detect(t, z[:-1])


# ─────────────────────────────── 検出 ───────────────────────────────────────

def test_ball_detect_subpixel_centre_on_synthetic_disc():
    """明るい円板 (40.3, 60.7)・半径 6.2: 中心 0.15 px・半径 0.5 px 以内、fill > 0.7。反転画像の "dark" も同じ。radius_range の外なら捨てる。"""
    m = _disc()
    img = m.astype(np.float64)
    d = BT.ball_detect(img, mode="bright", thresh=0.5)
    assert len(d) == 1
    assert np.hypot(d[0]["col"] - 40.3, d[0]["row"] - 60.7) < 0.15 and abs(d[0]["radius"] - 6.2) < 0.5
    assert d[0]["fill"] > 0.7 and d[0]["area"] == int(m.sum())
    dk = BT.ball_detect(1.0 - img, mode="dark", thresh=0.5)
    assert np.hypot(dk[0]["col"] - d[0]["col"], dk[0]["row"] - d[0]["row"]) < 1e-9 and dk[0]["radius"] == d[0]["radius"]
    assert BT.ball_detect(img, mode="bright", thresh=0.5, radius_range=(10.0, 80.0)) == []
    assert BT.ball_detect(img, mode="bright", thresh=0.5, radius_range=(1.5, 5.0)) == []
    auto = BT.ball_detect(img, mode="bright")                            # thresh 既定 = 平均 + 2σ でも同じ塊
    assert len(auto) == 1 and auto[0]["area"] == d[0]["area"]


def test_ball_detect_chroma_is_robust_to_shading():
    """陰影(0.5–1.0 の勾配)をかけた橙の円板は "chroma" が 0.3 px で当てる(狭い許容の "color" は外しうるので採点しない)。"""
    m = _disc()
    rgb = np.zeros((100, 120, 3))
    rr, cc = np.mgrid[0:100, 0:120]
    grad = 0.5 + 0.5 * (cc - (40.3 - 6.2)) / 12.4                       # 左端 0.5 → 右端 1.0 の陰影
    rgb[m] = np.array(ORANGE) * grad[m][:, None]
    dc = BT.ball_detect(rgb, mode="chroma", color=ORANGE, color_tol=0.12)
    assert len(dc) == 1 and np.hypot(dc[0]["col"] - 40.3, dc[0]["row"] - 60.7) < 0.3
    assert abs(dc[0]["radius"] - 6.2) < 0.5 and dc[0]["area"] == int(m.sum())
    dcol = BT.ball_detect(rgb, mode="color", color=ORANGE, color_tol=0.12)
    assert isinstance(dcol, list)                                        # 陰影で外しうる(採点しない)
    wide = BT.ball_detect(rgb, mode="color", color=ORANGE, color_tol=0.7)
    assert len(wide) == 1 and wide[0]["area"] == int(m.sum())          # 広い許容なら塊は拾うが…
    bias = np.hypot(wide[0]["col"] - 40.3, wide[0]["row"] - 60.7)
    assert bias > 0.5 and wide[0]["col"] > 40.3                          # …重みが明るさに引かれ中心が明るい側へ偏る(実測 1.14 px)
    assert np.hypot(dc[0]["col"] - 40.3, dc[0]["row"] - 60.7) < bias     # chroma はその偏りを持たない


def test_ball_detect_fails_closed():
    """未知の mode、(H, W) に色モード、color 無しの色モード、非有限の画素は ValueError。何も無い画像は []。"""
    img = _disc().astype(np.float64)
    with pytest.raises(ValueError):
        BT.ball_detect(img, mode="magenta")
    with pytest.raises(ValueError):
        BT.ball_detect(img, mode="chroma", color=ORANGE)
    with pytest.raises(ValueError):
        BT.ball_detect(np.zeros((10, 10, 3)), mode="color")
    bad = img.copy()
    bad[0, 0] = np.nan
    with pytest.raises(ValueError):
        BT.ball_detect(bad, mode="bright", thresh=0.5)
    assert BT.ball_detect(np.zeros((50, 60)), mode="bright", thresh=0.5) == []
    assert BT.ball_detect(np.zeros((50, 60, 3)), mode="chroma", color=ORANGE) == []   # 暗い画素は色が決まらず捨てる


def test_ball_track_associates_by_constant_velocity_and_rejects_jumps():
    """等速予測に近い候補を選び(得点順でない)、空のコマは found=False で飛ばし、max_jump を超える候補だけのコマは捨てる。frame は int64。"""
    def c(col, row, score=1.0):
        return {"col": float(col), "row": float(row), "radius": 3.0, "score": score}
    true = [(10.0 + 5.0 * k, 20.0 + 2.0 * k) for k in range(6)]
    decoy = [(60.0, 5.0) for _ in range(6)]                            # 動かない・得点は高い偽の候補
    det = [[c(*decoy[k], score=9.0), c(*true[k])] for k in range(6)]
    det[0] = [c(*true[0], score=2.0), c(*decoy[0], score=1.0)]         # 最初のコマは先頭(得点順)の候補 = 真
    det[3] = []                                                        # 欠測
    det[5] = [c(200.0, 200.0, score=9.0)]                              # 大きな跳び → 捨てる
    tr = BT.ball_track(det, max_jump=40.0)
    assert tr["frame"].dtype == np.int64 and tr["frame"].tolist() == [0, 1, 2, 4]
    assert tr["found"].tolist() == [True, True, True, False, True, False]
    assert np.allclose(tr["col"], [true[k][0] for k in (0, 1, 2, 4)]) and np.allclose(tr["row"], [true[k][1] for k in (0, 1, 2, 4)])
    assert np.allclose(tr["radius"], 3.0)
    lo = BT.ball_track(det, max_jump=40.0, min_score=5.0)              # 得点で真の候補を落とすと偽の候補だけ
    assert lo["frame"].tolist() == [1, 2, 4] and np.allclose(lo["col"], 60.0)
    with pytest.raises(ValueError):
        BT.ball_track("not a list")
    # try_track と同じ流れ: 実画像の検出を繋ぐ
    d = BT.ball_detect(_disc().astype(np.float64), mode="bright", thresh=0.5)
    tr2 = BT.ball_track([d, d, [], d])
    assert tr2["frame"].tolist() == [0, 1, 3] and tr2["found"].tolist() == [True, True, False, True]


def test_spin_from_marker_sequence_recovers_omega_and_beats_single_pairs():
    """模様の列(雑音つき)から ω を読む: 2 段目(4 コマ離れた組)は 1 段目(隣同士)より誤差が小さい。見えないコマ(None)は飛ばす。"""
    rng = np.random.default_rng(5)
    w = np.array([0.0, 150.0, 20.0])
    dt = 1e-3
    marks = rng.normal(size=(14, 3))
    marks /= np.linalg.norm(marks, axis=1, keepdims=True)
    R = np.eye(3)
    dirs = []
    for k in range(20):
        if k:
            R = _rodrigues(w, dt) @ R
        d = marks @ R.T
        d = d[d[:, 2] > 0.2] + rng.normal(0, 0.01, (int((d[:, 2] > 0.2).sum()), 3))     # 手前の半球だけ見える + 位置の雑音
        dirs.append(d if k != 7 else None)
    r = BT.spin_from_marker_sequence(dirs, dt)
    e2 = np.linalg.norm(r["omega"] - w) / np.linalg.norm(w)
    e1 = np.linalg.norm(r["omega_stage1"] - w) / np.linalg.norm(w)
    assert r["n_pairs"] >= 10 and e2 < 0.03 and e2 < e1
    with pytest.raises(ValueError):
        BT.spin_from_marker_sequence(dirs, 0.0)
    empty = BT.spin_from_marker_sequence([None, None, None], dt)
    assert empty["n_pairs"] == 0 and np.all(np.isnan(empty["omega"]))
