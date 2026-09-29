"""driveterrain の門: Perlin の定理(格子点 0・周期 256・|v| ≤ 1・解析導関数)/ fBm の β = 2H + 2 / 動径周期図 /
コース距離場(閉形式と |∇d| = 1)/ 地形の高さと勾配の閉形式 / 地形メッシュ / 世界への適用(索引の分割・剛体の持ち上げ)/
路面の材質(水溜り・摩耗)/ 木・歩行者・横断歩道の体積と本数 / 撒き(距離条件)/ 発散定理の体積 / fail-closed。"""
import copy

import numpy as np
import pytest

import drivecourse
import driveworld as DW
import driveterrain as DT


# ─────────────────────────────── 道具 ───────────────────────────────────────

def _loop_course():
    loop = drivecourse.course_loop(40, 15, 8)
    return drivecourse.course_layout(loop["elements"], loop["placements"])


def _segments(course):
    """検算用: コースの全多角形の辺 (M, 2, 2)(閉じ点は落とす)。module の _course_polys とは別に組む。"""
    els = course["elements"] if course.get("kind") == "layout" else [course]
    segs = []
    for e in els:
        P = np.asarray(e["polygon"], float)
        if np.allclose(P[0], P[-1]):
            P = P[:-1]
        segs.append(np.stack([P, np.roll(P, -1, axis=0)], axis=1))
    return np.concatenate(segs, axis=0)


def _brute_distance(course, Q):
    """点ごとに全辺への点-線分距離を素朴なループで取る(独立した真値)。"""
    S = _segments(course)
    out = np.empty(len(Q))
    for i, q in enumerate(Q):
        best = np.inf
        for a, b in S:
            ab = b - a
            t = np.clip(np.dot(q - a, ab) / max(np.dot(ab, ab), 1e-300), 0.0, 1.0)
            best = min(best, float(np.hypot(*(q - (a + t * ab)))))
        out[i] = best
    return out


def _random_xy(n, bounds, seed):
    rng = np.random.default_rng(seed)
    xmin, xmax, ymin, ymax = bounds
    return rng.uniform(xmin, xmax, n), rng.uniform(ymin, ymax, n)


def _fbm_grid(p, n):
    """n×n(dx = 1)の fBm を行ごとに評価する(位相配列 (n, K) を小さく保つ)。"""
    xs = np.arange(n, dtype=float)
    X, Y = np.meshgrid(xs, xs)
    Z = np.empty((n, n))
    for r in range(n):
        Z[r] = DT.fbm_height(X[r], Y[r], p)
    return Z


_BOUNDS = (-40.0, 40.0, -30.0, 30.0)
_TP = dict(seed=1, hurst=0.8, amplitude=2.0, n_waves=64, flat=2.0, blend=10.0, road_amp=0.3)


@pytest.fixture(scope="module")
def course():
    return _loop_course()


@pytest.fixture(scope="module")
def terrain_world(course):
    """コーンを南の直線(y = −15)の路面に置いた世界に地形を掛ける。適用前の頂点も返す。"""
    p = DT.terrain_params(**_TP)
    w = DW.world_build(course, props=[("cone", 0.0, -15.0, 0.0)])
    before = [w["V"][slice(*o["verts"])].copy() for o in w["objects"]]     # 索引で引く(kerb の名前は重複する)
    DT.world_apply_terrain(w, p, step=2.0)
    return w, p, before


@pytest.fixture(scope="module")
def road_view(terrain_world):
    w, p, _ = terrain_world
    K = DW.camera_intrinsics(60, 160, 100)
    pose = DW.camera_pose((-15.0, -15.0, 1.35), (5.0, -15.0, 0.9))
    view = DW.world_camera(w, pose, K, 160, 100)
    return view, pose, K


# ─────────────────────────────── Perlin ─────────────────────────────────────

def test_perlin2_is_zero_at_every_lattice_point():
    for freq in (0.25, 1.0, 3.0):
        i, j = np.meshgrid(np.arange(-6, 7), np.arange(-6, 7))
        v = DT.perlin2(i / freq, j / freq, seed=3, freq=freq)["value"]
        assert np.abs(v).max() < 1e-12


def test_perlin2_is_periodic_with_period_256_lattice():
    freq = 0.5
    x, y = _random_xy(2000, (-20, 20, -20, 20), 1)
    v = DT.perlin2(x, y, seed=5, freq=freq)["value"]
    vx = DT.perlin2(x + 256 / freq, y, seed=5, freq=freq)["value"]
    vy = DT.perlin2(x, y - 256 / freq, seed=5, freq=freq)["value"]
    assert np.abs(vx - v).max() < 1e-10 and np.abs(vy - v).max() < 1e-10


def test_perlin2_is_bounded_and_derivatives_match_finite_differences():
    x, y = _random_xy(5000, (-50, 50, -50, 50), 2)
    r = DT.perlin2(x, y, seed=7, freq=0.7)
    assert np.abs(r["value"]).max() <= 1.0
    h = 1e-5
    fx = (DT.perlin2(x + h, y, 7, 0.7)["value"] - DT.perlin2(x - h, y, 7, 0.7)["value"]) / (2 * h)
    fy = (DT.perlin2(x, y + h, 7, 0.7)["value"] - DT.perlin2(x, y - h, 7, 0.7)["value"]) / (2 * h)
    assert np.abs(r["dx"] - fx).max() < 1e-6 and np.abs(r["dy"] - fy).max() < 1e-6


def test_perlin2_seeds_and_fail_closed():
    x, y = _random_xy(500, (-10, 10, -10, 10), 3)
    a = DT.perlin2(x, y, seed=0)["value"]
    b = DT.perlin2(x, y, seed=1)["value"]
    assert not np.allclose(a, b) and np.array_equal(a, DT.perlin2(x, y, seed=0)["value"])
    with pytest.raises(ValueError):
        DT.perlin2(x, y, freq=0.0)
    with pytest.raises(ValueError):
        DT.perlin2(x, y, freq=-1.0)
    with pytest.raises(ValueError):
        DT.perlin2(np.array([0.0, np.nan]), np.array([0.0, 0.0]))


# ─────────────────────────────── fBm ────────────────────────────────────────

def test_fbm_params_spectrum_and_rms_normalisation():
    p = DT.fbm_params(seed=2, hurst=0.6, n_waves=256, amplitude=1.7)
    c = p["A"] * p["f"] ** 0.6
    assert np.ptp(c) < 1e-12 * c.mean()                       # A ∝ f^{−H}
    assert abs(np.sum(p["A"] ** 2) / 2 - 1.7 ** 2) < 1e-12    # RMS = amplitude
    assert (p["f"] >= p["f_min"]).all() and (p["f"] <= p["f_max"]).all()
    with pytest.raises(ValueError):
        DT.fbm_params(hurst=0.0)
    with pytest.raises(ValueError):
        DT.fbm_params(hurst=1.0)
    with pytest.raises(ValueError):
        DT.fbm_params(f_min=0.1, f_max=0.1)


def test_fbm_gradient_matches_finite_differences():
    p = DT.fbm_params(seed=4, n_waves=64)
    x, y = _random_xy(400, (-100, 100, -100, 100), 4)
    gx, gy = DT.fbm_gradient(x, y, p)
    h = 1e-5
    fx = (DT.fbm_height(x + h, y, p) - DT.fbm_height(x - h, y, p)) / (2 * h)
    fy = (DT.fbm_height(x, y + h, p) - DT.fbm_height(x, y - h, p)) / (2 * h)
    assert np.abs(gx - fx).max() < 1e-6 and np.abs(gy - fy).max() < 1e-6


def test_spectral_slope_recovers_beta_2h_plus_2():
    # 実測(6 seed): β − (2H+2) の平均 ≈ +0.09(H=0.5)/ +0.14(H=0.8)、sd ≈ 0.05。+0.1 の偏りは有限の帯域と
    # Hanning 窓(周期図の漏れ)から来る(fBm の定理そのものは β = 2H + 2)。1 格子 ≈ 5 s なので 2 枚まで。
    for H in (0.5, 0.8):
        p = DT.fbm_params(seed=0, hurst=H, n_waves=1024, f_min=1 / 400, f_max=1 / 4)
        r = DT.spectral_slope(_fbm_grid(p, 512), 1.0, 1 / 100, 1 / 10, n_bins=64)
        assert abs(r["beta"] - (2 * H + 2)) < 0.25, (H, r)
        assert r["n"] >= 3


def test_radial_periodogram_peaks_at_the_cosine_frequency():
    f0 = 0.05
    xs = np.arange(256, dtype=float)
    Z = np.cos(2 * np.pi * f0 * xs)[None, :] * np.ones((256, 1))
    pg = DT.radial_periodogram(Z, 1.0)
    width = pg["f"][1] - pg["f"][0]
    assert abs(pg["f"][np.argmax(pg["power"])] - f0) <= width
    assert pg["f"].min() > 0                                      # DC は除く
    pg2 = DT.radial_periodogram(Z + 5.0, 1.0)                     # 平均を引くので定数は効かない
    assert np.allclose(pg2["power"], pg["power"], rtol=1e-9, atol=1e-9)
    with pytest.raises(ValueError):
        DT.radial_periodogram(np.zeros((4, 64)), 1.0)
    with pytest.raises(ValueError):
        DT.radial_periodogram(Z, 0.0)


# ─────────────────────────────── 距離場 ─────────────────────────────────────

def test_course_distance_is_closed_form_and_eikonal(course):
    x, y = _random_xy(600, _BOUNDS, 5)
    Q = np.column_stack([x, y])
    r = DT.course_distance(course, Q)
    inside = drivecourse.course_contains(course, Q)
    assert inside.any() and (r["d"][inside] == 0).all()
    assert (r["nx"][inside] == 0).all() and (r["ny"][inside] == 0).all()
    assert np.abs(r["d"][~inside] - _brute_distance(course, Q[~inside])).max() < 1e-9
    assert (r["d"][~inside] > 0).all()
    h = 1e-5
    dx = (DT.course_distance(course, Q + [h, 0])["d"] - DT.course_distance(course, Q - [h, 0])["d"]) / (2 * h)
    dy = (DT.course_distance(course, Q + [0, h])["d"] - DT.course_distance(course, Q - [0, h])["d"]) / (2 * h)
    far = r["d"] > 0.5
    err = np.abs(np.hypot(dx, dy)[far] - 1.0)
    assert np.median(err) < 1e-6 and np.percentile(err, 99) < 1e-4     # 中心軸の近くだけ崩れる
    with pytest.raises(ValueError):
        DT.course_distance(course, [[0.0, np.inf]])


def test_course_distance_normal_equals_gradient(course):
    x, y = _random_xy(600, _BOUNDS, 6)
    Q = np.column_stack([x, y])
    r = DT.course_distance(course, Q)
    h = 1e-5
    dx = (DT.course_distance(course, Q + [h, 0])["d"] - DT.course_distance(course, Q - [h, 0])["d"]) / (2 * h)
    dy = (DT.course_distance(course, Q + [0, h])["d"] - DT.course_distance(course, Q - [0, h])["d"]) / (2 * h)
    far = r["d"] > 0.5
    assert np.percentile(np.abs(r["nx"][far] - dx[far]), 99) < 1e-5
    assert np.percentile(np.abs(r["ny"][far] - dy[far]), 99) < 1e-5
    assert np.abs(np.hypot(r["nx"], r["ny"])[far] - 1).max() < 1e-12


# ─────────────────────────────── 地形 ───────────────────────────────────────

def test_terrain_height_on_road_is_only_the_road_wave(course):
    p0 = DT.terrain_params(**{**_TP, "road_amp": 0.0})
    x, y = _random_xy(2000, _BOUNDS, 7)
    on = drivecourse.course_contains(course, np.column_stack([x, y]))
    assert on.sum() > 50
    assert (DT.terrain_height(x[on], y[on], p0, course) == 0).all()
    p1 = DT.terrain_params(**_TP)
    z = DT.terrain_height(x[on], y[on], p1, course)
    wave = 0.5 * 0.3 * (np.sin(2 * np.pi * x[on] / 160.0) + np.sin(2 * np.pi * y[on] / 110.0 + 1.0))
    assert np.abs(z - wave).max() < 1e-12


def test_terrain_height_far_from_road_is_fbm_plus_road_wave(course):
    p = DT.terrain_params(**_TP)
    x, y = _random_xy(3000, (-80, 80, -70, 70), 8)
    d = DT.course_distance(course, np.column_stack([x, y]))["d"]
    far = d >= p["flat"] + p["blend"]
    assert far.sum() > 100
    z = DT.terrain_height(x[far], y[far], p, course)
    ref = DT.fbm_height(x[far], y[far], p) + DT.terrain_height(x[far], y[far], DT.terrain_params(**{**_TP, "amplitude": 0.0}))
    assert np.array_equal(z, DT.terrain_height(x[far], y[far], p))   # course 無し = w ≡ 1 と同じ
    assert np.abs(z - ref).max() < 1e-12


def test_terrain_gradient_matches_finite_differences(course):
    p = DT.terrain_params(**_TP)
    x, y = _random_xy(600, _BOUNDS, 9)
    gx, gy = DT.terrain_gradient(x, y, p, course)
    h = 1e-5
    fx = (DT.terrain_height(x + h, y, p, course) - DT.terrain_height(x - h, y, p, course)) / (2 * h)
    fy = (DT.terrain_height(x, y + h, p, course) - DT.terrain_height(x, y - h, p, course)) / (2 * h)
    assert np.percentile(np.abs(gx - fx), 99) < 1e-6 and np.percentile(np.abs(gy - fy), 99) < 1e-6
    gx0, gy0 = DT.terrain_gradient(x, y, p)                       # course 無し
    fx0 = (DT.terrain_height(x + h, y, p) - DT.terrain_height(x - h, y, p)) / (2 * h)
    assert np.abs(gx0 - fx0).max() < 1e-6


def test_terrain_params_fails_closed():
    with pytest.raises(ValueError):
        DT.terrain_params(flat=-0.1)
    with pytest.raises(ValueError):
        DT.terrain_params(blend=0.0)
    with pytest.raises(ValueError):
        DT.terrain_params(road_amp=-1.0)
    with pytest.raises(ValueError):
        DT.terrain_params(road_len=(0.0, 10.0))


def test_terrain_mesh_heights_and_face_labels(course):
    p = DT.terrain_params(**_TP)
    m = DT.terrain_mesh(p, course, _BOUNDS, step=4.0)
    V, F = m["V"], m["F"]
    assert F.max() < len(V) and len(F) == len(m["face_label"]) == len(m["face_color"])
    assert np.array_equal(V[:, 2], DT.terrain_height(V[:, 0], V[:, 1], p, course))
    cen = V[F].mean(axis=1)[:, :2]
    inside = drivecourse.course_contains(course, cen)
    assert inside.any() and (~inside).any()
    assert (m["face_label"][inside] == 0).all() and (m["face_label"][~inside] == 10).all()
    with pytest.raises(ValueError):
        DT.terrain_mesh(p, course, (0, 0, 0, 1), 1.0)
    with pytest.raises(ValueError):
        DT.terrain_mesh(p, course, _BOUNDS, 0.0)


# ─────────────────────────────── 世界への適用 ───────────────────────────────

def test_world_apply_terrain_partitions_indices_and_lifts_objects(terrain_world):
    w, p, before = terrain_world
    objs = w["objects"]
    assert objs[0]["name"] == "ground" and w["terrain"] is p
    # (a) 頂点・面の範囲が V / F を分割し、各物体の面は自分の頂点だけを指す
    vr = sorted(o["verts"] for o in objs)
    fr = sorted(o["faces"] for o in objs)
    assert vr[0][0] == 0 and vr[-1][1] == len(w["V"]) and all(a[1] == b[0] for a, b in zip(vr, vr[1:]))
    assert fr[0][0] == 0 and fr[-1][1] == len(w["F"]) and all(a[1] == b[0] for a, b in zip(fr, fr[1:]))
    for o in objs:
        f = w["F"][slice(*o["faces"])]
        if len(f):
            assert f.min() >= o["verts"][0] and f.max() < o["verts"][1], o["name"]
    assert len(w["F"]) == len(w["face_label"]) == len(w["face_color"])
    # (b) コーンは姿勢の高さだけ剛体で持ち上がる
    ic = [k for k, o in enumerate(objs) if o["name"] == "cone"][0]
    cone = objs[ic]
    V0 = before[ic]
    V1 = w["V"][slice(*cone["verts"])]
    dz = V1[:, 2] - V0[:, 2]
    zc = float(DT.terrain_height(np.array([0.0]), np.array([-15.0]), p, w["course"])[0])
    assert abs(zc) > 1e-3 and np.abs(dz - zc).max() < 1e-12 and np.array_equal(V1[:, :2], V0[:, :2])
    assert abs(cone["z"] - zc) < 1e-12
    # (c) 縁石は頂点ごとに持ち上がる
    n_kerb = 0
    for k, o in enumerate(objs):
        if o["name"].startswith("kerb"):
            n_kerb += 1
            Vb = before[k]
            Va = w["V"][slice(*o["verts"])]
            assert np.array_equal(Va[:, :2], Vb[:, :2])
            assert np.abs((Va[:, 2] - Vb[:, 2]) - DT.terrain_height(Vb[:, 0], Vb[:, 1], p, w["course"])).max() < 1e-12
    assert n_kerb == 4                                                 # 直線 2 + 半円 2
    # (e) ground でない先頭は拒否
    with pytest.raises(ValueError):
        DT.world_apply_terrain({"objects": [{"name": "cone"}], "V": w["V"], "F": w["F"]}, p)


def test_world_move_after_terrain_keeps_the_cone_rigid(terrain_world):
    w = copy.deepcopy(terrain_world[0])                            # 共有の世界を汚さない(往復は 1e-16 ずれる)
    i = [k for k, o in enumerate(w["objects"]) if o["name"] == "cone"][0]
    o = w["objects"][i]
    V = w["V"][slice(*o["verts"])]
    span = np.ptp(V[:, 2])
    z_keep = o["z"]
    DW.world_move(w, i, 5.0, -15.0, 0.0, z=z_keep)
    V2 = w["V"][slice(*o["verts"])]
    assert abs(np.ptp(V2[:, 2]) - span) < 1e-9 and abs(V2[:, 2].min() - z_keep) < 1e-9
    DW.world_move(w, i, 0.0, -15.0, 0.0, z=z_keep)
    assert np.allclose(w["V"][slice(*o["verts"])], V, atol=1e-9)


# ─────────────────────────────── 材質 ───────────────────────────────────────

def test_world_materials_labels_puddles_and_ground_heights(terrain_world, road_view):
    w, p, _ = terrain_world
    view, pose, K = road_view
    mat = DT.world_materials(w, view, pose, K, DT.material_params(seed=0))
    H, W = view["label"].shape
    assert mat["color"].shape == (H, W, 3) and mat["label"].shape == (H, W) and mat["xyz"].shape == (H, W, 3)
    assert mat["puddle"].shape == mat["stain"].shape == mat["wear"].shape == (H, W)
    assert set(np.unique(mat["label"]).tolist()) <= ({-1} | set(DW.LABELS) | set(DT.TERRAIN_LABELS))
    pud = mat["label"] == 11
    assert mat["puddle"][pud].all() and not mat["puddle"][~pud].any()
    if pud.any():
        assert drivecourse.course_contains(w["course"], mat["xyz"][pud][:, :2]).all()
    ground = np.isin(mat["label"], (0, 10, 11))
    assert ground.sum() > 1000
    xyz = mat["xyz"][ground]
    err = np.abs(xyz[:, 2] - DT.terrain_height(xyz[:, 0], xyz[:, 1], p, w["course"]))
    assert np.median(err) < 0.01 and np.percentile(err, 99) < 0.15     # 升の弦の誤差(step 2.0)
    assert (mat["label"] == 10).any() and (mat["label"] == 0).any()
    with pytest.raises(ValueError):
        DT.world_materials(w, {k: v for k, v in view.items() if k != "shade"}, pose, K, DT.material_params())
    with pytest.raises(ValueError):
        DT.material_params(wear=1.5)


def test_world_materials_wear_mixes_line_colour(terrain_world, road_view):
    w, _, _ = terrain_world
    view, pose, K = road_view
    lines = view["label"] == 9
    assert lines.sum() > 10
    m0 = DT.world_materials(w, view, pose, K, DT.material_params(wear=0.0))
    ref = np.asarray(DT._LINE_COLOR)[None, :] * view["shade"][lines][:, None]
    assert np.abs(m0["color"][lines] - ref).max() < 1e-9 and (m0["wear"] == 0).all()
    assert np.array_equal(m0["label"][lines], view["label"][lines])
    m1 = DT.world_materials(w, view, pose, K, DT.material_params(wear=1.0))
    wl = m1["wear"][lines]
    assert (wl >= 0).all() and (wl <= 1).all() and wl.mean() > 0.5
    assert (m1["wear"][~lines] == 0).all()


# ─────────────────────────────── 手続き的な物体 ─────────────────────────────

def test_tree_mesh_volume_is_closed_form_for_conifer_and_bounded_for_broadleaf():
    c = DT.tree_mesh(height=6.0, trunk_radius=0.2, crown_radius=1.5, kind="conifer", n=10)
    assert c["volume"]["crown_exact"] and c["label"] == 13
    assert abs(DT.mesh_signed_volume(c["V"], c["F"]) - (c["volume"]["trunk"] + c["volume"]["crown"])) < 1e-9
    assert len(c["color"]) == len(c["F"]) and c["dims"] == (3.0, 3.0, 6.0)
    b = DT.tree_mesh(kind="broadleaf")
    bound = b["volume"]["trunk"] + b["volume"]["crown"]
    vol = DT.mesh_signed_volume(b["V"], b["F"])
    assert not b["volume"]["crown_exact"] and 0.8 * bound <= vol <= bound and b["label"] == 13
    with pytest.raises(ValueError):
        DT.tree_mesh(kind="palm")
    with pytest.raises(ValueError):
        DT.tree_mesh(height=-1.0)
    with pytest.raises(ValueError):
        DT.tree_mesh(n=2)


def test_pedestrian_mesh_volume_head_and_stride():
    m = DT.pedestrian_mesh(height=1.7)
    extra = DT.mesh_signed_volume(m["V"], m["F"]) - m["volume"]["boxes"]
    assert 0 < extra <= m["volume"]["head_max"] and m["label"] == 7
    assert abs(m["dims"][2] - 1.7) < 0.05 * 1.7 and abs(m["V"][:, 2].max() - m["dims"][2]) < 1e-12
    assert abs(m["V"][:, 2].min()) < 1e-12 and len(m["color"]) == len(m["F"])
    s = DT.pedestrian_mesh(height=1.7, stride=0.5)
    n_leg = 10                                                     # 箱 1 つ = 頂点 4 + 4 + 中心 2
    dx = s["V"][:, 0] - m["V"][:, 0]
    assert np.allclose(dx[:n_leg], 0.25) and np.allclose(dx[n_leg:2 * n_leg], -0.25)
    assert np.allclose(dx[2 * n_leg:], 0.0)
    with pytest.raises(ValueError):
        DT.pedestrian_mesh(height=0.0)


def test_crosswalk_mesh_counts_stripes_and_area():
    for L, stripe, gap in ((7.0, 0.45, 0.45), (4.0, 0.5, 0.3), (2.0, 0.6, 0.0)):
        m = DT.crosswalk_mesh((1.0, 2.0), (1.0, 2.0 + L), length=3.0, stripe=stripe, gap=gap)
        n = int(np.floor((L + 1e-9 + gap) / (stripe + gap)))
        assert m["n_stripes"] == n and abs(m["area"] - n * stripe * 3.0) < 1e-12
        assert len(m["F"]) == 2 * n and len(m["V"]) == 4 * n and m["label"] == 12
        assert np.ptp(m["V"][:, 2]) == 0 and len(m["color"]) == len(m["F"])
    with pytest.raises(ValueError):
        DT.crosswalk_mesh((0, 0), (0.3, 0), stripe=0.45)


def test_add_mesh_object_can_be_moved(course):
    w = DW.world_build(course)
    nv, nf = len(w["V"]), len(w["F"])
    t = DT.tree_mesh()
    i = DT.add_mesh_object(w, t, 0.0, 25.0, 0.3, name="tree")
    o = w["objects"][i]
    assert o["pose"] == (0.0, 25.0, 0.3) and "dims" in o and len(w["V"]) == nv + len(t["V"])
    assert len(w["F"]) == nf + len(t["F"]) and (w["face_label"][slice(*o["faces"])] == 13).all()
    DW.world_move(w, i, 5.0, 26.0, 1.0)
    assert len(w["V"]) == nv + len(t["V"]) and o["pose"] == (5.0, 26.0, 1.0)
    fresh = DW.place_mesh(t["V"], 5.0, 26.0, 1.0)
    assert np.allclose(w["V"][slice(*o["verts"])], fresh, atol=1e-9)


def test_scatter_offroad_respects_margin_and_spacing(course):
    P = DT.scatter_offroad(course, _BOUNDS, n=30, r_min=4.0, margin=3.0, seed=1)
    assert P.shape[1] == 3 and 0 < len(P) <= 30
    assert (DT.course_distance(course, P[:, :2])["d"] >= 3.0).all()
    D = np.hypot(P[:, None, 0] - P[None, :, 0], P[:, None, 1] - P[None, :, 1])
    np.fill_diagonal(D, np.inf)
    assert D.min() >= 4.0
    assert np.array_equal(P, DT.scatter_offroad(course, _BOUNDS, n=30, r_min=4.0, margin=3.0, seed=1))
    assert DT.scatter_offroad(course, _BOUNDS, n=0).shape == (0, 3)
    with pytest.raises(ValueError):
        DT.scatter_offroad(course, _BOUNDS, r_min=0.0)


def test_mesh_volume_of_unit_cube_is_plus_one():
    V, F = DT._prism(np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]), 0.0, 1.0)
    assert abs(DT.mesh_signed_volume(V, F) - 1.0) < 1e-12
    assert abs(DT.mesh_signed_volume(V, F[:, ::-1]) + 1.0) < 1e-12        # 裏返すと符号が変わる
