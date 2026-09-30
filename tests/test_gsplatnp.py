"""gsplatnp(numpy の 3DGS)の門: EWA 投影の閉形式・α 合成の式・剛体の同変性・被覆・密度つまみの単調性・誤差つまみの大きさ・fail-closed。"""
import math

import numpy as np
import pytest

import driveworld as DW
import gsplatnp as GS


def _one(mu, cov3, color=(1.0, 0.0, 0.0), opacity=0.05, normal=(0.0, 0.0, 1.0)):
    """ガウシアン 1 個の gs(face 等は描画に使わないので空でよい)。cov3 は世界系の 3×3。"""
    w, E = np.linalg.eigh(np.asarray(cov3, np.float64))
    R = E[:, [2, 1, 0]]                                  # 列 = t1, t2, n(n = 最小の軸)
    if np.linalg.det(R) < 0:
        R[:, 2] *= -1
    ww = w[[2, 1, 0]]
    return {"mu": np.asarray(mu, np.float64)[None], "R": R[None], "cov_t": np.diag(ww[:2])[None], "sigma_n": np.sqrt([ww[2]]),
            "sigma_t": np.sqrt([ww[0]]), "normal": np.asarray(normal, np.float64)[None], "color": np.asarray(color, np.float64)[None],
            "opacity": np.array([opacity]), "label": np.array([7])}


def _cam(eye=(0.0, -1.0, 0.3), target=(0.0, 0.0, 0.0), W=160, H=120, fov=40.0):
    return DW.camera_pose(eye, target), DW.camera_intrinsics(fov, W, H), W, H


def test_ewa_second_moments_match_the_closed_form():
    """1 個のガウシアンの α 像の平均と 2 次モーメント = 投影した中心と Σ' = J W Σ Wᵀ Jᵀ + 0.3 I(× α の切り捨て c = 2 ln(255 o) による
    縮み f = 1 − (c/2) e^{−c/2} / (1 − e^{−c/2})、o は Mip-Splatting の補正後)。Σ' は別の実装(driveworld.world_project_points で 3-D の標本 40 万点を写した共分散)とも照合。"""
    pose, K, W, H = _cam()
    A = np.array([[0.004, 0.001, 0.0], [0.001, 0.002, 0.0005], [0.0, 0.0005, 0.001]]) * 0.25
    mu = np.array([0.02, 0.05, -0.01])
    o = 0.05
    r = GS.gs_render(_one(mu, A, opacity=o), pose, K, W, H, ambient=1.0)
    al = r["alpha"]
    yy, xx = np.mgrid[0:H, 0:W]
    m = al.sum()
    cx, cy = (al * xx).sum() / m, (al * yy).sum() / m
    col, row, _ = DW.world_project_points(mu[None], pose, K)
    assert abs(cx - col[0]) < 0.02 and abs(cy - row[0]) < 0.02, (cx, cy, col, row)
    S_img = np.array([[(al * (xx - cx) ** 2).sum(), (al * (xx - cx) * (yy - cy)).sum()],
                      [(al * (xx - cx) * (yy - cy)).sum(), (al * (yy - cy) ** 2).sum()]]) / m
    rng = np.random.default_rng(0)
    P = rng.multivariate_normal(mu, A * 1e-4, 400000)          # 小さく縮めて写す = 線形化(J)の数値微分
    c2, r2, _ = DW.world_project_points(P, pose, K)
    S_mc = np.cov(np.vstack([c2, r2])) * 1e4 + 0.3 * np.eye(2)
    comp = math.sqrt(np.linalg.det(S_mc - 0.3 * np.eye(2)) / np.linalg.det(S_mc))   # Mip-Splatting の不透明度の補正
    c = 2.0 * math.log(255.0 * o * comp)
    f = 1.0 - (c / 2.0) * math.exp(-c / 2.0) / (1.0 - math.exp(-c / 2.0))
    assert np.max(np.abs(S_img - f * S_mc)) < 0.02 * np.max(np.abs(S_mc)), (S_img, f * S_mc)
    assert np.linalg.eigvalsh(S_mc).min() > 4.0                 # 探針が画素より十分大きい(離散化の誤差を門に入れない)


def test_alpha_compositing_is_front_to_back_and_order_free():
    """同じ画素に重なる 2 個: 中心の色 = c1 α1 + c2 α2 (1 − α1) + sky (1 − α1)(1 − α2)(1 = 手前)。配列の順を入れ替えても同じ像。"""
    pose, K, W, H = _cam()
    A = np.eye(3) * 1e-4
    g1 = _one([0.0, -0.2, 0.0], A, color=(1.0, 0.0, 0.0), opacity=0.6)
    eye = np.array([0.0, -1.0, 0.3])
    g2 = _one(eye + 1.4 * (np.array([0.0, -0.2, 0.0]) - eye) + [0.004, 0.0, 0.0], A * 4, color=(0.0, 0.0, 1.0), opacity=0.7)   # 同じ視線の奥
    both = {k: np.concatenate([g1[k], g2[k]]) for k in g1}
    swap = {k: np.concatenate([g2[k], g1[k]]) for k in g1}
    sky = np.array([0.2, 0.9, 0.3])
    ra = GS.gs_render(both, pose, K, W, H, ambient=1.0, sky=sky)
    rb = GS.gs_render(swap, pose, K, W, H, ambient=1.0, sky=sky)
    assert np.array_equal(ra["color"], rb["color"]) and np.array_equal(ra["alpha"], rb["alpha"])
    col, row, dep = DW.world_project_points(np.vstack([g1["mu"], g2["mu"]]), pose, K)
    assert dep[0] < dep[1]
    # 各ガウシアン単独の α をその画素で出して式と照合
    px, py = int(round(col[0])), int(round(row[0]))
    al = []
    for g in (g1, g2):
        rr = GS.gs_render(g, pose, K, W, H, ambient=1.0, sky=sky)
        al.append(rr["alpha"][py, px])
    a1, a2 = al
    expect = np.array([1.0, 0.0, 0.0]) * a1 + np.array([0.0, 0.0, 1.0]) * a2 * (1 - a1) + sky * (1 - a1) * (1 - a2)
    assert a1 > 0.5 and a2 > 0.05
    assert np.allclose(ra["color"][py, px], expect, atol=1e-9)


def _quad_world(size=0.2, color=(0.8, 0.5, 0.2)):
    w = DW._empty_world()
    V = np.array([[-size, -size, 0.0], [size, -size, 0.0], [size, size, 0.0], [-size, size, 0.0]])
    DW.world_add(w, V, np.array([[0, 1, 2], [0, 2, 3]]), 5, color, name="quad")
    return w


def test_rigid_motion_moves_the_splats_with_the_world():
    """世界の頂点を剛体変換 (Q, t) で動かして gs_update → μ' = Q μ + t、向き R' = Q R(誤差つきでも)。作り直しと同じ個数・同じ face。"""
    w = _quad_world()
    gs = GS.gs_from_world(w, spacing=0.01, pos_noise=0.002, seed=3)
    mu0, R0 = gs["mu"].copy(), gs["R"].copy()
    th = 0.7
    Q = np.array([[math.cos(th), -math.sin(th), 0], [math.sin(th), math.cos(th), 0], [0, 0, 1.0]]) @ \
        np.array([[1, 0, 0], [0, math.cos(0.4), -math.sin(0.4)], [0, math.sin(0.4), math.cos(0.4)]])
    t = np.array([0.3, -0.1, 0.5])
    w["V"] = w["V"] @ Q.T + t
    GS.gs_update(gs, w)
    assert np.allclose(gs["mu"], mu0 @ Q.T + t, atol=1e-12)
    assert np.allclose(gs["R"], np.einsum("ij,njk->nik", Q, R0), atol=1e-12)


def test_dense_splats_cover_the_surface_and_match_the_mesh_render():
    """平らな板を密(間隔 5 mm)に: 板の内側の画素の 99 % 以上で α ≥ 0.95、色の差の中央値 < 0.02(メッシュの描画 driveworld.world_camera と)。"""
    w = _quad_world()
    gs = GS.gs_from_world(w, spacing=0.005)
    pose, K, W, H = _cam(eye=(0.0, -0.5, 0.5), W=200, H=150)
    r = GS.gs_render(gs, pose, K, W, H)
    m = DW.world_camera(w, pose, K, W, H)
    inside = m["label"] == 5
    er = inside.copy()
    for _ in range(3):                                           # 縁の 3 画素は除く(ガウシアンは縁で滲む)
        er[1:-1, 1:-1] &= er[:-2, 1:-1] & er[2:, 1:-1] & er[1:-1, :-2] & er[1:-1, 2:]
    assert er.sum() > 3000
    assert (r["alpha"][er] >= 0.95).mean() > 0.99
    assert np.median(np.abs(r["color"][er] - m["color"][er]).max(axis=1)) < 0.02
    assert (r["label"][er] == 5).mean() > 0.99


def test_coarser_spacing_departs_further_from_the_mesh():
    """密度のつまみ: 間隔 3 → 6 → 12 → 24 mm で、メッシュの描画との平均の色差が単調に増える(曲がった面 = 球)。"""
    w = DW._empty_world()
    import render3d  # noqa: F401  (world_camera が使う)
    # 球(経緯の格子)
    nu, nv = 48, 24
    th = np.linspace(0, np.pi, nv + 1)
    ph = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    V = np.array([[0.05 * math.sin(a) * math.cos(b), 0.05 * math.sin(a) * math.sin(b), 0.05 * math.cos(a)] for a in th for b in ph])
    F = []
    for i in range(nv):
        for j in range(nu):
            a, b = i * nu + j, i * nu + (j + 1) % nu
            c, d = a + nu, b + nu
            F += [[a, c, b], [b, c, d]]
    DW.world_add(w, V, np.array(F), 3, (0.9, 0.4, 0.1), name="ball")
    pose, K, W, H = _cam(eye=(0.0, -0.3, 0.1), W=160, H=160, fov=30.0)
    m = DW.world_camera(w, pose, K, W, H)
    errs = []
    for sp in (0.003, 0.006, 0.012, 0.024):
        r = GS.gs_render(GS.gs_from_world(w, spacing=sp), pose, K, W, H)
        errs.append(float(np.abs(r["color"] - m["color"]).mean()))
    assert all(a < b for a, b in zip(errs, errs[1:])), errs


def test_position_and_colour_noise_have_the_asked_size_and_stay_fixed():
    """位置の誤差: |μ − μ(誤差なし)| の二乗平均 = √3 · pos_noise(±5 %)。同じ seed なら同じ誤差、gs_update をまたいでも変わらない。
    色の誤差: 色の差の標準偏差 ≈ color_noise(切り詰めの無い中間の色で ±5 %)。"""
    w = _quad_world(color=(0.5, 0.5, 0.5))
    a = GS.gs_from_world(w, spacing=0.004, seed=1)
    b = GS.gs_from_world(w, spacing=0.004, pos_noise=0.003, color_noise=0.05, seed=1)
    d = np.linalg.norm(b["mu"] - a["mu"], axis=1)
    assert abs(math.sqrt((d ** 2).mean()) / (math.sqrt(3) * 0.003) - 1) < 0.05
    assert abs((b["color"] - a["color"]).std() / 0.05 - 1) < 0.05
    mu = b["mu"].copy()
    GS.gs_update(b, w)
    assert np.array_equal(b["mu"], mu)
    c = GS.gs_from_world(w, spacing=0.004, pos_noise=0.003, color_noise=0.05, seed=1)
    assert np.array_equal(c["mu"], b["mu"]) and np.array_equal(c["color"], b["color"])


def test_thin_parts_get_smaller_denser_splats():
    """曲率の上限: 太さ 3 mm の糸(円柱)のガウシアンは σ ≤ 0.5 · 半径 + 余裕、太さ 60 mm の円柱は間隔どおり(σ = 1.0 · spacing)。"""
    def cyl(r, L=0.3, n=12):
        a = np.linspace(0, 2 * np.pi, n, endpoint=False)
        V = np.vstack([np.column_stack([r * np.cos(a), r * np.sin(a), np.zeros(n)]), np.column_stack([r * np.cos(a), r * np.sin(a), np.full(n, L)])])
        F = []
        for j in range(n):
            k = (j + 1) % n
            F += [[j, k, n + j], [k, n + k, n + j]]
        return V, np.array(F)
    w = DW._empty_world()
    V, F = cyl(0.0015)
    DW.world_add(w, V, F, 1, (0.1, 0.1, 0.1), name="string")
    V, F = cyl(0.03)
    DW.world_add(w, V + [0.2, 0, 0], F, 2, (0.8, 0.6, 0.3), name="stick")
    gs = GS.gs_from_world(w, spacing=0.004)
    s_str = gs["sigma_t"][gs["obj"] == 0]
    s_stk = gs["sigma_t"][gs["obj"] == 1]
    # 12 角形の円柱: 隣の面の角 30°、重心の差の辺に垂直な成分 ≈ 弦の半分 × 2 → R ≈ r 程度(0.6〜1.1 r)
    assert 0.5 * 0.6 * 0.0015 <= s_str.max() <= 0.5 * 1.1 * 0.0015, s_str.max()
    assert np.allclose(s_stk, 1.0 * 0.004, rtol=2e-3)                # 個数の切り上げで僅かに密


def test_fail_closed():
    w = _quad_world()
    for kw in ({"spacing": 0.0}, {"spacing": -1.0}, {"max_per_object": 0}, {"pos_noise": -0.1}, {"color_noise": -0.1},
               {"sigma_ratio": 0.0}, {"opacity": 0.0}, {"opacity": 1.5}, {"curv_ratio": 0.0}):
        with pytest.raises(ValueError):
            GS.gs_from_world(w, **kw)
    gs = GS.gs_from_world(w, spacing=0.01)
    pose, K, W, H = _cam()
    with pytest.raises(ValueError):
        GS.gs_render(gs, pose, K, 0, H)
    with pytest.raises(ValueError):
        GS.gs_render(gs, pose, K, W, H, max_pairs=10)
    empty = DW._empty_world()
    with pytest.raises(ValueError):
        GS.gs_from_world(empty)
    w2 = _quad_world()
    w2["F"] = w2["F"][:1]
    with pytest.raises(ValueError):
        GS.gs_update(GS.gs_from_world(_quad_world(), spacing=0.005), w2)


def test_render_fn_follows_the_world_and_counts_calls():
    """gs_render_fn: 世界の頂点を動かすと描画も動く(板を 5 cm 動かす → α の重心が投影どおりに動く)。呼んだ回数を数える。"""
    w = _quad_world(size=0.05)
    gs = GS.gs_from_world(w, spacing=0.004)
    pose, K, W, H = _cam()
    cam = {"pose": pose, "K": K, "width": W, "height": H}
    fn = GS.gs_render_fn(gs, ambient=1.0)
    img0 = fn(w, cam)
    w["V"] = w["V"] + [0.05, 0.0, 0.0]
    img1 = fn(w, cam)
    assert fn.n_calls == 2 and fn.n_pairs > 0
    sky = np.array([0.62, 0.75, 0.92])
    def cx(img):
        m = np.abs(img - sky).max(axis=2) > 0.1
        return np.nonzero(m)[1].mean()
    c0, _, _ = DW.world_project_points(np.array([[0.0, 0.0, 0.0]]), pose, K)
    c1, _, _ = DW.world_project_points(np.array([[0.05, 0.0, 0.0]]), pose, K)
    assert abs((cx(img1) - cx(img0)) - (c1[0] - c0[0])) < 0.5
    with pytest.raises(ValueError):
        GS.gs_render_fn({})


def test_mip_compensation_keeps_the_alpha_integral_of_a_subpixel_splat():
    """Mip-Splatting の補正: 画素より細いガウシアン(σ' ≈ 0.2 px)でも α の総和 = o · 2π √det(Σ'₀)(足し込み前の共分散)が保たれる
    (補正なしだと 0.3 px² を足したぶん膨らむ: 比 √(det(Σ'₀ + 0.3 I) / det Σ'₀) 倍)。"""
    pose, K, W, H = _cam(W=64, H=48)
    mu = np.array([0.0, 0.0, 0.0])
    A = np.eye(3) * (0.0024 ** 2)
    o = 0.5
    ra = GS.gs_render(_one(mu, A, opacity=o), pose, K, W, H, ambient=1.0)
    rb = GS.gs_render(_one(mu, A, opacity=o), pose, K, W, H, ambient=1.0, antialias=False)
    rng = np.random.default_rng(0)
    P = rng.multivariate_normal(mu, A, 200000)
    c2, r2, _ = DW.world_project_points(P, pose, K)
    S0 = np.cov(np.vstack([c2, r2]))
    assert np.sqrt(np.linalg.eigvalsh(S0).max()) < 0.3                  # 画素より細い
    grow = math.sqrt(np.linalg.det(S0 + 0.3 * np.eye(2)) / np.linalg.det(S0))

    def kept(peak):                                                   # α < 1/255 を捨てたぶん: 質量の 1 − e^{−c/2}、c = 2 ln(255 · peak)
        return 1.0 - 1.0 / (255.0 * peak)
    want = o * 2 * math.pi * math.sqrt(np.linalg.det(S0)) * kept(o / grow)
    assert abs(ra["alpha"].sum() / want - 1) < 0.03, (ra["alpha"].sum(), want)
    want_b = o * 2 * math.pi * math.sqrt(np.linalg.det(S0)) * grow * kept(o)
    assert abs(rb["alpha"].sum() / want_b - 1) < 0.03 and grow > 3, (rb["alpha"].sum(), want_b)
