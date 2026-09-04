"""metalfinish(加工された金属表面)の単体テスト。

契約:
  * 接線場は仕上げごとに**幾何が違う**(一方向 / 同心円 / 放射 / 交差 / 無方向)。
    同心円は半径に直交し、放射は半径に平行 —— そこを内積で機械検証する。
  * 粗さ場は `random` だけ等方(αx == αy)、他は異方性(αx > αy)。
  * 加工痕は法線を**筋に直交する向き**へ傾ける。`random` では何もしない。
  * ブラストは方向統計を持たない = ハイライトが伸びずに広がる(異方性より低いピーク)。
  * 陰影は材質の色を引き継ぐ(金は R>G>B、銀はほぼ中性)。
  * 引数検査は fail-closed。
"""
import numpy as np
import pytest

import metalfinish as MF


def _hemisphere(n=96):
    y, x = np.mgrid[-1:1:n * 1j, -1:1:n * 1j]
    r2 = x * x + y * y
    m = r2 < 1.0
    z = np.sqrt(np.maximum(1.0 - r2, 0.0))
    return np.stack([x, y, z], -1) * m[..., None], m


# --------------------------------------------------------------------------- #
# 接線場                                                                        #
# --------------------------------------------------------------------------- #
def test_tangent_fields_have_the_right_geometry():
    h = w = 64
    for kind in MF.FINISHES:
        t = MF.tangent_field((h, w), kind)
        assert t.shape == (h, w, 3)
        assert np.allclose(np.linalg.norm(t, axis=-1), 1.0, atol=1e-12)
        assert np.allclose(t[..., 2], 0.0)                 # 面内

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    r = np.stack([xx - (w - 1) / 2.0, yy - (h - 1) / 2.0], -1)
    r = r / np.maximum(np.linalg.norm(r, axis=-1, keepdims=True), 1e-9)
    inner = np.s_[8:-8, 8:-8]                              # 中心の特異点を避ける

    circ = MF.tangent_field((h, w), "circular")[..., :2]
    assert np.abs((circ * r).sum(-1))[inner].max() < 1e-9  # 半径に直交
    rad = MF.tangent_field((h, w), "radial")[..., :2]
    assert np.abs(np.abs((rad * r).sum(-1)) - 1.0)[inner].max() < 1e-9   # 半径に平行

    lin = MF.tangent_field((h, w), "linear", angle_deg=30.0)
    assert np.allclose(lin[0, 0, :2], [np.cos(np.radians(30.0)), np.sin(np.radians(30.0))])
    assert np.allclose(lin - lin[0, 0], 0.0)               # 一方向 = 定ベクトル

    rnd = MF.tangent_field((h, w), "random")
    assert float(np.std(np.arctan2(rnd[..., 1], rnd[..., 0]))) > 0.5    # 向きが散る


def test_tangent_field_rejects_bad_input():
    with pytest.raises(ValueError, match="unknown finish"):
        MF.tangent_field((8, 8), "sandblasted-ish")
    with pytest.raises(ValueError):
        MF.tangent_field((0, 8), "linear")
    with pytest.raises(ValueError):
        MF.tangent_field((8, 8), "circular", center=(1.0, 2.0, 3.0))


# --------------------------------------------------------------------------- #
# 粗さ場                                                                        #
# --------------------------------------------------------------------------- #
def test_roughness_is_isotropic_only_for_random():
    for kind in MF.FINISHES:
        a = MF.roughness_field((32, 32), kind)
        assert a.shape == (32, 32, 2) and np.all(a > 0.0)
        ax, ay = a[..., 0].mean(), a[..., 1].mean()
        if kind == "random":
            assert ax == pytest.approx(ay, rel=1e-12)      # 無方向仕上げ
        else:
            assert ax > 2.0 * ay, (kind, ax, ay)           # 筋がある


def test_patchiness_creates_variation_and_stays_positive():
    flat = MF.roughness_field((64, 64), "linear", patchiness=0.0)
    var = MF.roughness_field((64, 64), "linear", patchiness=0.6, seed=3)
    assert float(np.std(flat)) == pytest.approx(np.std(flat[..., 0]) + 0.0, abs=1.0)
    assert float(np.std(var[..., 0])) > float(np.std(flat[..., 0]))
    assert np.all(var > 0.0)
    with pytest.raises(ValueError):
        MF.roughness_field((8, 8), "linear", patchiness=1.5)
    with pytest.raises(ValueError):
        MF.roughness_field((8, 8), "linear", scale=0.0)


# --------------------------------------------------------------------------- #
# 加工痕                                                                        #
# --------------------------------------------------------------------------- #
def test_micro_normals_tilt_across_the_grooves_and_stay_unit():
    N, m = _hemisphere()
    out = MF.micro_normals(N, "linear", pitch_px=8.0, depth=0.08)
    assert np.allclose(np.linalg.norm(out[m], axis=-1), 1.0, atol=1e-12)
    assert float(np.abs(out - N)[m].max()) > 0.01          # 何かは変えている
    # 筋方向(x)には周期構造が乗らず、直交方向(y)に乗る
    diff = np.abs(out - N).sum(-1)
    var_along = float(np.var(diff[m.shape[0] // 2, 20:-20]))
    assert var_along > 0.0
    flat = MF.micro_normals(N, "linear", depth=0.0)
    assert np.allclose(flat, N * m[..., None])             # depth=0 は無加工
    same = MF.micro_normals(N, "random", depth=0.5)
    assert np.allclose(same, N * m[..., None])             # random は方向を持たない


def test_blast_spreads_instead_of_elongating():
    """★ ブラスト面と異方性面の見分け: 方向統計が無いのでハイライトが伸びない。"""
    N, m = _hemisphere()
    lin = MF.finish_shade(N, "linear", "al")
    rnd = MF.finish_shade(N, "random", "al")
    assert float(lin.max()) > 2.0 * float(rnd.max())       # 筋つきの方がピークが高い
    b = MF.blast_normals(N, grain=0.05, seed=1)
    assert np.allclose(np.linalg.norm(b[m], axis=-1), 1.0, atol=1e-12)
    assert float(np.abs(b - N)[m].max()) > 0.01
    assert np.allclose(MF.blast_normals(N, grain=0.0), N * m[..., None])
    with pytest.raises(ValueError):
        MF.blast_normals(N, cell_px=0.0)


# --------------------------------------------------------------------------- #
# 陰影(材質 × 仕上げ)                                                          #
# --------------------------------------------------------------------------- #
def test_finish_shade_keeps_the_metal_colour():
    N, m = _hemisphere()
    au = MF.finish_shade(N, "linear", "au")
    ag = MF.finish_shade(N, "linear", "ag")
    pa = au.reshape(-1, 3)[au.sum(-1).argmax()]
    pg = ag.reshape(-1, 3)[ag.sum(-1).argmax()]
    assert pa[0] > pa[1] > pa[2], pa                       # 金は R>G>B
    assert float(np.ptp(pg / max(pg.max(), 1e-12))) < 0.12, pg   # 銀はほぼ中性
    assert np.all(au >= 0.0) and np.isfinite(au).all()
    assert np.allclose(au[~m], 0.0)                        # 背景は 0


def test_finish_shade_differs_between_finishes():
    N, _ = _hemisphere()
    imgs = {k: MF.finish_shade(N, k, "al") for k in MF.FINISHES}
    keys = list(imgs)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = imgs[keys[i]], imgs[keys[j]]
            assert float(np.abs(a - b).max()) > 1e-6, (keys[i], keys[j])


def test_catalog_orders_roughness():
    cat = MF.finish_catalog()
    assert set(cat) == set(MF.FINISHES)
    assert cat["linear"]["alpha_y"] < cat["crosshatch"]["alpha_y"] < cat["random"]["alpha_y"]
    cat["linear"]["alpha_x"] = 999.0                       # 返りは複製(表を壊せない)
    assert MF.finish_catalog()["linear"]["alpha_x"] != 999.0
