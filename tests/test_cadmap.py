# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""cadmap の閉形式グラウンドトゥルース試験。

ここで確かめるのは「例外が出ないこと」ではなく **「黙って間違った数を返さない
こと」**。真値はすべて解析的に分かるものだけを使う:

  1. 往復可逆性 — 面上の既知の点を投影 → その画素から逆引き → **同じ face_id と
     同じ重心座標**(機械精度)。
  2. 面積 — 既知の平面パッチの面積が解析値と一致し、**斜めから見ても**面上の実
     面積として出る(画素数ベースの素朴な値は 1/cosθ だけ間違う)。
  3. 遮蔽 — 手前の面に隠れた面は選ばれない。隠れている点は ``occluded`` で
     区別される。
  4. 当たらない画素・裏面・退化・型混入の fail-closed。
"""
from __future__ import annotations

import numpy as np
import pytest

import cadmap
import camera


# --------------------------------------------------------------------------- #
# 合成ジオメトリ(すべて閉形式)                                                #
# --------------------------------------------------------------------------- #
def _box(center=(0.0, 0.0, 0.0), size=(1.0, 1.0, 1.0)):
    """外向き巻き(外から見て反時計回り)の直方体 (V, F)。12 三角形。"""
    c = np.asarray(center, float)
    h = np.asarray(size, float) / 2.0
    V = np.array([[-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
                  [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float) * h + c
    F = np.array([
        [0, 2, 1], [0, 3, 2],        # -z
        [4, 5, 6], [4, 6, 7],        # +z
        [0, 1, 5], [0, 5, 4],        # -y
        [3, 7, 6], [3, 6, 2],        # +y
        [0, 4, 7], [0, 7, 3],        # -x
        [1, 2, 6], [1, 6, 5],        # +x
    ], np.int64)
    return V, F


def _quad_patch(tilt_deg=0.0, z=6.0, half=(2.0, 1.5)):
    """カメラ(原点、+Z 向き)に向いた平面パッチ。x 軸まわりに *tilt_deg* 傾ける。

    返りは ``(V, F, area)``。``area`` は解析的な実面積 ``4*half[0]*half[1]``
    (回転は面積を変えない)。法線がカメラを向くように巻いてある。"""
    a, b = float(half[0]), float(half[1])
    P = np.array([[-a, -b, 0.0], [a, -b, 0.0], [a, b, 0.0], [-a, b, 0.0]])
    th = np.deg2rad(float(tilt_deg))
    Rx = np.array([[1.0, 0.0, 0.0],
                   [0.0, np.cos(th), -np.sin(th)],
                   [0.0, np.sin(th), np.cos(th)]])
    V = P @ Rx.T + np.array([0.0, 0.0, z])
    # 巻きは (B-A)x(C-A) が -Z 側(= カメラ側)を向くように
    F = np.array([[0, 2, 1], [0, 3, 2]], np.int64)
    return V, F, 4.0 * a * b


def _K(f=400.0, w=256, h=256):
    return camera.intrinsic_matrix(f, f, (w - 1) / 2.0, (h - 1) / 2.0)


IDENTITY_POSE = (np.eye(3), np.zeros(3))


# --------------------------------------------------------------------------- #
# 1. 往復可逆性 — 厳密な真値                                                    #
# --------------------------------------------------------------------------- #
def test_roundtrip_face_and_barycentric_exact():
    """面上の既知の点 → 投影 → 逆引きで **同じ face_id・同じ重心座標**。"""
    V, F = _box(size=(2.0, 1.5, 1.2))
    K = _K()
    R, t = np.eye(3), np.array([0.3, -0.2, 7.0])
    rng = np.random.default_rng(7)

    vis = cadmap.cad_visible_faces((V, F), K=K, R=R, t=t, width=256, height=256)
    assert vis.size >= 2

    face_ids, barys, pts = [], [], []
    for fid in vis:
        for _ in range(20):
            w = rng.dirichlet(np.ones(3))
            face_ids.append(int(fid))
            barys.append(w)
            pts.append((V[F[fid]] * w[:, None]).sum(0))
    face_ids = np.asarray(face_ids, np.int64)
    barys = np.asarray(barys)
    pts = np.asarray(pts)

    fwd = cadmap.cad_surface_to_pixel((V, F), pts, K=K, R=R, t=t,
                                      image_size=(256, 256))
    keep = fwd["visible"]
    assert keep.sum() >= 40, "可視な標本が足りない"

    back = cadmap.cad_pixel_to_surface((V, F), fwd["uv"][keep], K=K, R=R, t=t,
                                       image_size=(256, 256))
    assert back["hit"].all()
    assert np.array_equal(back["face_id"], face_ids[keep])
    bary_err = float(np.abs(back["bary"] - barys[keep]).max())
    point_err = float(np.abs(back["point"] - pts[keep]).max())
    assert bary_err < 1e-9, bary_err
    assert point_err < 1e-9, point_err


def test_roundtrip_barycentric_reconstructs_point_exactly():
    """返る重心座標と face_id から 3-D 点を組み直すと ``point`` と厳密一致。"""
    V, F = _box()
    uv = np.stack(np.meshgrid(np.arange(40.0, 220.0, 7.0),
                              np.arange(40.0, 220.0, 7.0)), -1).reshape(-1, 2)
    rec = cadmap.cad_pixel_to_surface((V, F), uv, K=_K(), R=np.eye(3),
                                      t=np.array([0.0, 0.0, 5.0]),
                                      image_size=(256, 256))
    h = rec["hit"]
    assert h.sum() > 100
    tri = V[F[rec["face_id"][h]]]
    rebuilt = np.einsum("mkj,mk->mj", tri, rec["bary"][h])
    assert np.abs(rebuilt - rec["point"][h]).max() == 0.0


def test_depth_is_camera_z_not_range():
    """``depth`` はカメラ座標 Z。視線距離と取り違えていないことを直接確かめる。"""
    V, F, _ = _quad_patch(tilt_deg=0.0, z=6.0, half=(3.0, 3.0))
    K = _K()
    uv = np.array([[127.5, 127.5], [200.0, 127.5]])
    rec = cadmap.cad_pixel_to_surface((V, F), uv, K=K, R=np.eye(3),
                                      t=np.zeros(3), image_size=(256, 256))
    assert rec["hit"].all()
    assert np.allclose(rec["depth"], 6.0)             # 平面なので Z は一定
    rng = np.linalg.norm(rec["point"], axis=1)
    assert rng[1] > rng[0] + 1e-3                     # 視線距離は端で伸びる


# --------------------------------------------------------------------------- #
# 2. 面積 — 斜めから見ても面上の実面積                                          #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tilt", [0.0, 30.0, 60.0])
def test_patch_area_matches_analytic_and_beats_naive(tilt):
    """既知パッチの面積が解析値と一致し、傾き無視の素朴値は 1/cosθ だけ外れる。"""
    W = H = 512
    V, F, area_true = _quad_patch(tilt_deg=tilt, z=6.0, half=(1.6, 1.2))
    K = _K(f=900.0, w=W, h=H)
    R, t = np.eye(3), np.zeros(3)
    rec = cadmap.cad_pixel_to_surface(
        (V, F), np.stack(np.meshgrid(np.arange(W, dtype=float),
                                     np.arange(H, dtype=float)), -1).reshape(-1, 2),
        K=K, R=R, t=t, image_size=(W, H))
    labels = rec["hit"].reshape(H, W).astype(np.int32)
    assert labels.sum() > 5000

    tbl = cadmap.cad_defect_to_cad((V, F), labels, K=K, R=R, t=t)
    assert len(tbl) == 1
    rel = abs(tbl[0]["area"] - area_true) / area_true
    assert rel < 0.02, (tilt, tbl[0]["area"], area_true, rel)
    # 素朴値(傾き無視)は cos(tilt) 倍だけ小さい
    naive_rel = tbl[0]["area_naive"] / area_true
    assert abs(naive_rel - np.cos(np.deg2rad(tilt))) < 0.02, (tilt, naive_rel)


def test_area_element_matches_exact_pixel_quad():
    """1 画素の面積要素が、画素 4 隅の光線が平面に切る四辺形の**厳密面積**と一致。"""
    V, F, _ = _quad_patch(tilt_deg=55.0, z=7.0, half=(4.0, 4.0))
    K = _K(f=600.0, w=256, h=256)
    R, t = np.eye(3), np.zeros(3)
    for u, v in [(128.0, 128.0), (90.0, 160.0), (170.0, 100.0)]:
        lab = np.zeros((256, 256), np.int32)
        lab[int(v), int(u)] = 1
        got = cadmap.cad_defect_to_cad((V, F), lab, K=K, R=R, t=t)[0]["area"]
        corners = np.array([[u - .5, v - .5], [u + .5, v - .5],
                            [u + .5, v + .5], [u - .5, v + .5]])
        P = cadmap.cad_pixel_to_surface((V, F), corners, K=K, R=R, t=t,
                                        image_size=(256, 256))["point"]
        exact = 0.5 * (np.linalg.norm(np.cross(P[1] - P[0], P[2] - P[0]))
                       + np.linalg.norm(np.cross(P[0] - P[2], P[3] - P[2])))
        assert abs(got - exact) / exact < 1e-3, (u, v, got, exact)


# --------------------------------------------------------------------------- #
# 3. 遮蔽                                                                      #
# --------------------------------------------------------------------------- #
def test_occluder_wins_and_hidden_face_is_not_returned():
    """手前の板が奥の板を隠す。奥の面 ID は返らない。"""
    Vf, Ff, _ = _quad_patch(0.0, z=4.0, half=(1.0, 1.0))
    Vb, Fb, _ = _quad_patch(0.0, z=9.0, half=(3.0, 3.0))
    V = np.vstack([Vf, Vb])
    F = np.vstack([Ff, Fb + len(Vf)])
    K = _K()
    rec = cadmap.cad_pixel_to_surface((V, F), np.array([[127.5, 127.5]]), K=K,
                                      R=np.eye(3), t=np.zeros(3),
                                      image_size=(256, 256))
    assert rec["hit"][0]
    assert rec["face_id"][0] in (0, 1)                # 手前の板
    assert np.isclose(rec["depth"][0], 4.0)


def test_hidden_point_is_flagged_not_silently_visible():
    """隠れている点を頼まれたら、黙って手前の面の画素を「見えている」と言わない。"""
    Vf, Ff, _ = _quad_patch(0.0, z=4.0, half=(1.0, 1.0))
    Vb, Fb, _ = _quad_patch(0.0, z=9.0, half=(3.0, 3.0))
    V = np.vstack([Vf, Vb])
    F = np.vstack([Ff, Fb + len(Vf)])
    K = _K()
    hidden = np.array([[0.0, 0.0, 9.0]])              # 奥の板の中心 = 隠れている
    edge = np.array([[2.5, 0.0, 9.0]])                # 奥の板の端 = 見えている
    out = cadmap.cad_surface_to_pixel((V, F), np.vstack([hidden, edge]), K=K,
                                      R=np.eye(3), t=np.zeros(3),
                                      image_size=(256, 256))
    assert out["occluded"][0] and not out["visible"][0]
    assert out["occluder_face"][0] in (0, 1)
    assert out["in_front"][0] and out["in_image"][0]   # 投影自体は正当
    assert out["visible"][1] and out["occluder_face"][1] == -1


def test_visible_faces_excludes_back_of_box():
    """閉じた箱では、カメラを向いていない面と裏の面が ``cad_visible_faces`` に入らない。"""
    V, F = _box(size=(2.0, 2.0, 2.0))
    K = _K()
    vis = set(cadmap.cad_visible_faces((V, F), K=K, R=np.eye(3),
                                       t=np.array([0.0, 0.0, 8.0]),
                                       width=192, height=192).tolist())
    assert {0, 1} <= vis                               # -z 面(カメラ側)
    assert vis.isdisjoint({2, 3})                      # +z 面(裏)


def test_point_behind_camera_is_flagged():
    V, F = _box()
    out = cadmap.cad_surface_to_pixel((V, F), np.array([[0.0, 0.0, -3.0]]),
                                      K=_K(), R=np.eye(3), t=np.zeros(3),
                                      image_size=(256, 256))
    assert not out["in_front"][0] and not out["visible"][0]


# --------------------------------------------------------------------------- #
# 4. 当たらない / 裏面 / 縁 / 退化                                              #
# --------------------------------------------------------------------------- #
def test_miss_returns_minus_one_never_the_nearest_face():
    """当たらない画素に**最寄りの面**を返さない。"""
    V, F, _ = _quad_patch(0.0, z=6.0, half=(0.3, 0.3))
    rec = cadmap.cad_pixel_to_surface((V, F), np.array([[5.0, 5.0], [250.0, 250.0]]),
                                      K=_K(), R=np.eye(3), t=np.zeros(3),
                                      image_size=(256, 256))
    assert not rec["hit"].any()
    assert (rec["face_id"] == -1).all()
    assert np.isnan(rec["bary"]).all() and np.isnan(rec["point"]).all()
    assert np.isnan(rec["depth"]).all()


def test_backfacing_patch_is_not_hit():
    """法線がカメラを向いていない面は当たりにしない(``cull_backfaces=False`` で当たる)。"""
    V, F, _ = _quad_patch(0.0, z=6.0, half=(2.0, 2.0))
    Fflip = F[:, ::-1].copy()                          # 巻きを反転 = 裏向き
    uv = np.array([[127.5, 127.5]])
    assert not cadmap.cad_pixel_to_surface((V, Fflip), uv, K=_K(), R=np.eye(3),
                                           t=np.zeros(3),
                                           image_size=(256, 256))["hit"][0]
    assert cadmap.cad_pixel_to_surface((V, Fflip), uv, K=_K(), R=np.eye(3),
                                       t=np.zeros(3), image_size=(256, 256),
                                       cull_backfaces=False)["hit"][0]


def test_shared_edge_point_belongs_to_exactly_one_face_deterministically():
    """共有辺のちょうど上を通る光線が、どちらの面にも属さない状態にならない。"""
    V, F, _ = _quad_patch(0.0, z=6.0, half=(2.0, 2.0))
    K = _K()
    # 対角 (V0 -> V2) 上の点を厳密に作り、その画素へ撃つ
    for s in (0.25, 0.5, 0.75):
        X = (1.0 - s) * V[0] + s * V[2]
        uv, _ = camera.project_points(X[None], K, np.eye(3), np.zeros(3))
        rec = cadmap.cad_pixel_to_surface((V, F), uv, K=K, R=np.eye(3),
                                          t=np.zeros(3), image_size=(256, 256))
        assert rec["hit"][0], s
        assert np.abs(rec["point"][0] - X).max() < 1e-9
        assert float(rec["bary"][0].min()) > -1e-9
        # 決定論: 同じ問い合わせは同じ面を返す
        again = cadmap.cad_pixel_to_surface((V, F), uv, K=K, R=np.eye(3),
                                            t=np.zeros(3), image_size=(256, 256))
        assert again["face_id"][0] == rec["face_id"][0]


def test_vertex_point_hits():
    """頂点ちょうどを通る光線も当たりになる(重心座標は 1 成分が 1)。"""
    V, F, _ = _quad_patch(0.0, z=6.0, half=(2.0, 2.0))
    K = _K()
    uv, _ = camera.project_points(V[2][None], K, np.eye(3), np.zeros(3))
    rec = cadmap.cad_pixel_to_surface((V, F), uv, K=K, R=np.eye(3),
                                      t=np.zeros(3), image_size=(256, 256))
    assert rec["hit"][0]
    assert np.abs(rec["point"][0] - V[2]).max() < 1e-9


def test_degenerate_zero_area_triangle_never_hits():
    V = np.array([[-1.0, 0.0, 5.0], [1.0, 0.0, 5.0], [0.0, 0.0, 5.0]])
    F = np.array([[0, 1, 2]], np.int64)
    uv = np.stack(np.meshgrid(np.arange(0.0, 256.0, 3.0),
                              np.arange(0.0, 256.0, 3.0)), -1).reshape(-1, 2)
    rec = cadmap.cad_pixel_to_surface((V, F), uv, K=_K(), R=np.eye(3),
                                      t=np.zeros(3), image_size=(256, 256),
                                      cull_backfaces=False)
    assert not rec["hit"].any()


def test_empty_faces_refused():
    with pytest.raises(ValueError):
        cadmap.cad_pixel_to_surface((np.zeros((3, 3)), np.zeros((0, 3), int)),
                                    np.zeros((1, 2)))


def test_camera_inside_the_mesh_sees_nothing_with_culling():
    """カメラが箱の中にいると、外向き法線の面はすべて裏を向く = 当たり 0。"""
    V, F = _box(size=(4.0, 4.0, 4.0))
    uv = np.stack(np.meshgrid(np.arange(0.0, 64.0, 2.0),
                              np.arange(0.0, 64.0, 2.0)), -1).reshape(-1, 2)
    inside = cadmap.cad_pixel_to_surface((V, F), uv, K=_K(f=60.0, w=64, h=64),
                                         R=np.eye(3), t=np.zeros(3),
                                         image_size=(64, 64))
    assert not inside["hit"].any()
    off = cadmap.cad_pixel_to_surface((V, F), uv, K=_K(f=60.0, w=64, h=64),
                                      R=np.eye(3), t=np.zeros(3),
                                      image_size=(64, 64), cull_backfaces=False)
    assert off["hit"].any()


def test_inverted_winding_inverts_which_faces_are_visible():
    """巻きを全部反転すると、**近い面が消えて遠い面が見える**。

    裏面判定は巻きに依存するという文書化済みの仮定を、そのまま数値に出す
    (「巻きが混在した mesh では cull_backfaces=False にすること」の根拠)。"""
    V, F = _box()
    kw = dict(K=_K(f=60.0, w=48, h=48), R=np.eye(3),
              t=np.array([0.0, 0.0, 5.0]), width=48, height=48)
    ok = set(cadmap.cad_visible_faces((V, F), **kw).tolist())
    flipped = set(cadmap.cad_visible_faces((V, F[:, ::-1].copy()), **kw).tolist())
    assert {0, 1} <= ok and ok.isdisjoint({2, 3})        # 正しい巻き: 近い面
    assert {2, 3} <= flipped and flipped.isdisjoint({0, 1})   # 反転: 遠い面


# --------------------------------------------------------------------------- #
# 5. 型・単位・資源の fail-closed                                               #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", [
    np.array([["1", "2"]]),                            # str
    np.array([[True, False]]),                         # bool
    np.array([[1 + 2j, 3 + 0j]]),                      # complex
])
def test_string_bool_complex_pixels_refused(bad):
    """``float("50")`` が成功するので、dtype で明示的に落とす。"""
    V, F = _box()
    with pytest.raises(ValueError):
        cadmap.cad_pixel_to_surface((V, F), bad)


def test_string_vertices_refused():
    with pytest.raises(ValueError):
        cadmap.cad_pixel_to_surface((np.array([["0", "0", "0"], ["1", "0", "0"],
                                               ["0", "1", "0"]]),
                                     np.array([[0, 1, 2]])), np.zeros((1, 2)))


@pytest.mark.parametrize("bad", ["64", True, 3 + 1j, 64.5])
def test_bad_width_refused(bad):
    V, F = _box()
    with pytest.raises(ValueError):
        cadmap.cad_visible_faces((V, F), width=bad)


def test_non_rotation_R_refused():
    V, F = _box()
    with pytest.raises(ValueError):
        cadmap.cad_pixel_to_surface((V, F), np.zeros((1, 2)), K=_K(),
                                    R=np.diag([1.0, 1.0, 2.0]), t=np.zeros(3))


def test_K_with_wrong_last_row_refused():
    V, F = _box()
    K = _K()
    K[2] = [0.0, 0.0, 2.0]
    with pytest.raises(ValueError):
        cadmap.cad_pixel_to_surface((V, F), np.zeros((1, 2)), K=K, R=np.eye(3),
                                    t=np.zeros(3))


def test_ray_face_budget_is_enforced_before_allocation(monkeypatch):
    """上限は **float64 昇格の前**に効く: 小さい入力から巨大な確保をさせない。"""
    V, F = _box()
    monkeypatch.setattr(cadmap, "MAX_RAY_FACE_TESTS", 10)
    with pytest.raises(ValueError, match="exceeds"):
        cadmap.cad_pixel_to_surface((V, F), np.zeros((100, 2)), K=_K(),
                                    R=np.eye(3), t=np.zeros(3))
    with pytest.raises(ValueError, match="exceeds"):
        cadmap.cad_visible_faces((V, F), K=_K(), R=np.eye(3), t=np.zeros(3),
                                 width=64, height=64)


def test_chunking_gives_the_same_answer(monkeypatch):
    """チャンク分割は結果を変えない(境界で face_id が入れ替わらない)。"""
    V, F = _box()
    uv = np.stack(np.meshgrid(np.arange(0.0, 128.0, 3.0),
                              np.arange(0.0, 128.0, 3.0)), -1).reshape(-1, 2)
    kw = dict(K=_K(f=200.0, w=128, h=128), R=np.eye(3),
              t=np.array([0.0, 0.0, 6.0]), image_size=(128, 128))
    ref = cadmap.cad_pixel_to_surface((V, F), uv, **kw)
    monkeypatch.setattr(cadmap, "RAY_CHUNK_TESTS", 24)
    small = cadmap.cad_pixel_to_surface((V, F), uv, **kw)
    assert np.array_equal(ref["face_id"], small["face_id"])
    assert np.array_equal(np.nan_to_num(ref["bary"]), np.nan_to_num(small["bary"]))


def test_float_labels_with_fractions_refused():
    V, F = _box()
    lab = np.zeros((16, 16))
    lab[4, 4] = 1.5
    with pytest.raises(ValueError):
        cadmap.cad_defect_to_cad((V, F), lab)


def test_1d_labels_refused():
    V, F = _box()
    with pytest.raises(ValueError):
        cadmap.cad_defect_to_cad((V, F), np.zeros(16, np.int32))


def test_bad_mesh_shape_refused():
    with pytest.raises(ValueError):
        cadmap.cad_pixel_to_surface(np.zeros((4, 3)), np.zeros((1, 2)))


# --------------------------------------------------------------------------- #
# 6. 欠陥表の中身                                                              #
# --------------------------------------------------------------------------- #
def test_defect_table_keeps_regions_that_miss_the_cad():
    """CAD の外に載った領域を**表から消さない**(消すと欠陥が静かに無かったことになる)。"""
    V, F, _ = _quad_patch(0.0, z=6.0, half=(0.4, 0.4))
    K = _K(f=400.0, w=128, h=128)
    lab = np.zeros((128, 128), np.int32)
    lab[60:68, 60:68] = 1                              # パッチの上
    lab[4:10, 4:10] = 2                                # 完全に外
    tbl = cadmap.cad_defect_to_cad((V, F), lab, K=K, R=np.eye(3), t=np.zeros(3))
    by = {r["label"]: r for r in tbl}
    assert set(by) == {1, 2}
    assert by[1]["n_hit"] > 0 and by[1]["area"] > 0.0
    assert by[2]["n_hit"] == 0 and by[2]["area"] == 0.0
    assert by[2]["hit_fraction"] == 0.0
    assert np.isnan(by[2]["centroid"]).all()
    assert by[2]["face_ids"].size == 0


def test_defect_centroid_is_on_the_surface():
    """面積重み重心が、実際に面の上(平面 z = const)に載る。"""
    V, F, _ = _quad_patch(0.0, z=6.0, half=(2.0, 2.0))
    K = _K(f=400.0, w=256, h=256)
    lab = np.zeros((256, 256), np.int32)
    lab[100:150, 110:160] = 1
    r = cadmap.cad_defect_to_cad((V, F), lab, K=K, R=np.eye(3), t=np.zeros(3))[0]
    assert abs(r["centroid"][2] - 6.0) < 1e-9
    assert r["hit_fraction"] == 1.0
    assert np.isclose(r["face_areas"].sum(), r["area"])


def test_defect_face_split_across_two_triangles():
    """対角をまたぐ領域は 2 つの面に分かれ、面ごとの面積の和が総面積に一致する。"""
    V, F, _ = _quad_patch(0.0, z=6.0, half=(2.0, 2.0))
    K = _K(f=400.0, w=256, h=256)
    lab = np.zeros((256, 256), np.int32)
    lab[100:156, 100:156] = 1
    r = cadmap.cad_defect_to_cad((V, F), lab, K=K, R=np.eye(3), t=np.zeros(3))[0]
    assert r["face_ids"].size == 2
    assert np.isclose(r["face_areas"].sum(), r["area"])


def test_bool_mask_is_accepted_as_labels():
    V, F, _ = _quad_patch(0.0, z=6.0, half=(2.0, 2.0))
    mask = np.zeros((128, 128), bool)
    mask[50:70, 50:70] = True
    tbl = cadmap.cad_defect_to_cad((V, F), mask, K=_K(f=200.0, w=128, h=128),
                                   R=np.eye(3), t=np.zeros(3))
    assert len(tbl) == 1 and tbl[0]["label"] == 1 and tbl[0]["area"] > 0.0


def test_camera_used_is_reported():
    """既定カメラに落ちたときも、実際に使われた K/R/t が返る。"""
    V, F = _box()
    rec = cadmap.cad_pixel_to_surface((V, F), np.array([[10.0, 10.0]]))
    cam = rec["camera"]
    assert cam["K"].shape == (3, 3) and cam["t"].shape == (3,)
    again = cadmap.cad_pixel_to_surface((V, F), np.array([[10.0, 10.0]]),
                                        K=cam["K"], R=cam["R"], t=cam["t"],
                                        image_size=(cam["width"], cam["height"]))
    assert again["face_id"][0] == rec["face_id"][0]


# --------------------------------------------------------------------------- #
# 7. 台帳                                                                      #
# --------------------------------------------------------------------------- #
def test_ledger_is_complete_and_wired():
    import opscadmap
    assert opscadmap.missing() == []
    assert set(opscadmap.list_ops()) == set(cadmap.__all__) - {
        "MAX_RAY_FACE_TESTS", "RAY_CHUNK_TESTS", "DEFAULT_IMAGE_SIZE"}
    for name in opscadmap.list_ops():
        meta = opscadmap.info(name)
        assert meta["doc"] and meta["func"] is not None
        assert meta["out"] in ("table", "indices")


def test_ledger_declared_types_match_actual_returns():
    """宣言 out 型が実際の返りと合っている(chain_fuzz の TYPEMISS 相当)。"""
    import opscadmap
    import sys
    sys.path.insert(0, "tools")
    from chain_fuzz import TYPE_CHECKS

    V, F = _box()
    K, R, t = _K(f=64.0, w=64, h=64), np.eye(3), np.array([0.0, 0.0, 5.0])
    calls = {
        "cad_pixel_to_surface": ((V, F), np.array([[32.0, 32.0], [1.0, 1.0]])),
        "cad_surface_to_pixel": ((V, F), V[:4].copy()),
        "cad_defect_to_cad": ((V, F), np.ones((64, 64), np.int32)),
        "cad_visible_faces": ((V, F),),
    }
    for name, args in calls.items():
        kw = dict(K=K, R=R, t=t)
        if name in ("cad_pixel_to_surface", "cad_surface_to_pixel"):
            kw["image_size"] = (64, 64)
        if name == "cad_visible_faces":
            kw.update(width=64, height=64)
        out = opscadmap.call(name, *args, **kw)
        declared = opscadmap.info(name)["out"]
        assert TYPE_CHECKS[declared](out), (name, declared, type(out))


# --------------------------------------------------------------------------- #
# 8. 単位非依存(実バグの回帰試験)                                             #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("scale", [1e-6, 1e-3, 1.0, 1e3, 1e6])
def test_result_is_scale_invariant(scale):
    """mesh を um でも km でも表しても**同じ結果**になる。

    回帰試験。行列式のしきい値を絶対値 1e-12 で持っていたとき、1 辺 1 um の
    mesh(``|e1||e2| ~ 1e-12``)で**例外も出さずに全画素 miss**になり、
    「欠陥は CAD の外にある」という嘘の表を返していた。m 単位の試験では
    見えないので、単位を振る試験でしか捕まらない。"""
    V, F = _box(size=(2.0 * scale, 1.5 * scale, 1.2 * scale))
    K = _K()
    R, t = np.eye(3), np.array([0.0, 0.0, 7.0 * scale])
    vis = cadmap.cad_visible_faces((V, F), K=K, R=R, t=t, width=128, height=128)
    assert vis.size >= 2, scale

    rng = np.random.default_rng(11)
    w = rng.dirichlet(np.ones(3), size=vis.size)
    pts = np.einsum("mkj,mk->mj", V[F[vis]], w)
    fwd = cadmap.cad_surface_to_pixel((V, F), pts, K=K, R=R, t=t,
                                      image_size=(256, 256))
    keep = fwd["visible"]
    assert keep.any(), scale
    back = cadmap.cad_pixel_to_surface((V, F), fwd["uv"][keep], K=K, R=R, t=t,
                                       image_size=(256, 256))
    assert np.array_equal(back["face_id"], vis[keep])
    assert np.abs(back["bary"] - w[keep]).max() < 1e-9
    rel = np.abs(back["point"] - pts[keep]).max() / max(np.abs(pts[keep]).max(), 1e-300)
    assert rel < 1e-12, (scale, rel)


def test_coplanar_duplicate_faces_pick_the_lowest_index_deterministically():
    """厳密に重なった 2 面(z-fighting)でも、返る face は決定論的に最小 index。"""
    V, F, _ = _quad_patch(0.0, z=6.0, half=(2.0, 2.0))
    V2 = np.vstack([V, V])
    F2 = np.vstack([F, F + len(V)])                    # 完全に同一の面を複製
    uv = np.array([[100.0, 130.0], [150.0, 120.0]])
    a = cadmap.cad_pixel_to_surface((V2, F2), uv, K=_K(), R=np.eye(3),
                                    t=np.zeros(3), image_size=(256, 256))
    b = cadmap.cad_pixel_to_surface((V2, F2), uv, K=_K(), R=np.eye(3),
                                    t=np.zeros(3), image_size=(256, 256))
    assert np.array_equal(a["face_id"], b["face_id"])
    assert (a["face_id"] < 2).all()                    # 複製ではなく元の面
