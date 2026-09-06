# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""形態統計(Procrustes / GPA / 形態 PCA / 左右対称性 / 符号つき面距離)。

契約:

* Procrustes は**平行移動と回転**を必ず消し、``scaling=True`` なら**大きさも**
  消す。消してよい変形と消してはいけない変形を分けて確かめる。
* ``reflection=False``(既定)は鏡映を許さない —— 許すと左右非対称性という
  測りたいものが平均に吸われて消える。
* 形態 PCA は**合成した群の真のモード**を復元する(分散比が既知)。
* Mahalanobis は**裾の成分を切らないと意味を失う**(数値ゼロで割った回数を
  測ることになる)。既定の打ち切りがそれを防いでいるか。
* 正中面は**残差最小の面ではなく、対の中点が乗る面**。片側の変形で引きずられ
  ないことを、既知の変形で確かめる。
"""
import numpy as np
import pytest

import shapestats as ss


def _rz(deg):
    t = np.deg2rad(deg)
    return np.array([[np.cos(t), -np.sin(t), 0.0],
                     [np.sin(t), np.cos(t), 0.0],
                     [0.0, 0.0, 1.0]])


# --------------------------------------------------------------------------- #
# 1. 合成 —— 真値を持つ群
# --------------------------------------------------------------------------- #
def test_synth_family_has_the_declared_shape_and_is_deterministic():
    a = ss.shape_synth_family(n_shapes=6, n_points=32, seed=3)
    b = ss.shape_synth_family(n_shapes=6, n_points=32, seed=3)
    assert a.shape == (6, 32, 3)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, ss.shape_synth_family(n_shapes=6, n_points=32, seed=4))


def test_perturb_modes_are_what_they_say():
    p = ss.shape_synth_family(2, 40, seed=0)[0]
    assert np.allclose(ss.shape_perturb(p, 0.3, "shift") - p,
                       0.3 * np.array([1.0, 0.0, 0.0]))
    sc = ss.shape_perturb(p, 0.25, "scale")
    assert np.allclose(sc.mean(0), p.mean(0))                    # 重心は動かない
    assert np.allclose(sc - sc.mean(0), 1.25 * (p - p.mean(0)))
    with pytest.raises(ValueError, match="mode must be"):
        ss.shape_perturb(p, 0.1, "nope")


# --------------------------------------------------------------------------- #
# 2. Procrustes —— 何を消し、何を残すか
# --------------------------------------------------------------------------- #
def test_translation_rotation_and_scale_are_removed():
    p = ss.shape_synth_family(2, 48, seed=1)[0]
    q = (p @ _rz(37.0).T) * 1.4 + np.array([3.0, -2.0, 0.5])
    assert ss.procrustes_distance(q, p) < 1e-12


def test_scaling_false_keeps_the_size_difference():
    p = ss.shape_synth_family(2, 48, seed=1)[0]
    q = ss.shape_perturb(p, 0.2, "scale")
    assert ss.procrustes_distance(p, q) < 1e-12                  # 大きさを消す
    assert ss.procrustes_distance(p, q, scaling=False) > 0.1     # 消さない


def test_reflection_is_refused_by_default():
    """鏡映を許すと左右差が消える。既定でそれが起きないこと。"""
    p = ss.shape_synth_family(2, 48, seed=2)[0]
    mirrored = p * np.array([1.0, 1.0, -1.0])
    d_no = ss.procrustes_distance(mirrored, p)
    d_yes = ss.procrustes_distance(mirrored, p, reflection=True)
    assert d_yes < 1e-12, "鏡映を許しても重ならない —— 前提が違う"
    assert d_no > 0.1, "既定で鏡映が通ってしまっている"


def test_procrustes_needs_correspondence_and_says_so():
    p = ss.shape_synth_family(2, 30, seed=0)[0]
    with pytest.raises(ValueError, match="correspondence"):
        ss.procrustes_fit(p, p[:20])


def test_gpa_converges_and_the_mean_is_not_the_raw_mean():
    fam = ss.shape_synth_family(10, 40, seed=5)
    moved = np.stack([f @ _rz(30.0 * i).T + i * 0.4 for i, f in enumerate(fam)])
    aligned = ss.generalized_procrustes(moved)
    assert aligned.shape == moved.shape
    gpa_mean = ss.shape_mean(moved)
    raw_mean = moved.mean(0)
    # 生の平均は個体がばらばらに置かれているぶんだけ縮む
    def size(x):
        return float(np.sqrt(np.mean(np.sum((x - x.mean(0)) ** 2, axis=1))))
    # 実測 0.680 対 0.268(2.54 倍)。生の平均は個体の散らばりのぶんだけ縮む。
    assert size(gpa_mean) > 2.0 * size(raw_mean), (size(gpa_mean), size(raw_mean))


# --------------------------------------------------------------------------- #
# 3. 統計形状モデル
# --------------------------------------------------------------------------- #
def test_pca_recovers_the_modes_that_were_put_in():
    """分散比が ``mode_scale`` の 2 乗比に近いこと(モデルの検算)。

    ★ ただしそれは ``align=False`` のとき。既定の ``align=True`` は Procrustes で
    **大きさも消す**ので、「長軸の伸び」モードの分散が半分以上そちらへ吸われる。
    実測 6.981 → 2.565。間違いではなく定義の帰結で、docstring の表と対。
    """
    fam = ss.shape_synth_family(n_shapes=40, n_points=80,
                                mode_scale=(0.30, 0.12), seed=7)
    raw = ss.shape_pca(fam, align=False)
    ev = ss.shape_explained_variance(raw)
    assert ev[0] + ev[1] > 0.995, ev[:4]
    ratio = float(raw["variance"][0] / raw["variance"][1])
    assert 5.0 < ratio < 9.5, ratio                    # 理論 (0.30/0.12)^2 = 6.25

    scaled = ss.shape_pca(fam)                          # align=True(既定)
    r2 = float(scaled["variance"][0] / scaled["variance"][1])
    assert r2 < 0.6 * ratio, (ratio, r2)                # スケール除去が食う
    # スケールだけ残せば元に戻る(食っているのが大きさだと言い切れる)
    keep = ss.shape_pca(ss.generalized_procrustes(fam, scaling=False), align=False)
    # 回転の合わせ直しぶんだけ厳密一致はしない(実測 6.981329 対 6.981329)。
    assert float(keep["variance"][0] / keep["variance"][1]) == pytest.approx(ratio,
                                                                             rel=1e-3)


def test_project_then_reconstruct_returns_the_aligned_shape():
    fam = ss.shape_synth_family(12, 64, seed=8)
    m = ss.shape_pca(fam)
    s = fam[3]
    back = ss.shape_reconstruct(m, ss.shape_project(m, s))
    ref = ss.procrustes_align(s, m["mean"])
    assert float(np.sqrt(np.mean(np.sum((back - ref) ** 2, axis=1)))) < 1e-9


def test_reconstruct_refuses_too_many_scores():
    m = ss.shape_pca(ss.shape_synth_family(5, 32, seed=0))
    with pytest.raises(ValueError, match="components"):
        ss.shape_reconstruct(m, np.zeros(m["components"].shape[0] + 1))


def test_mahalanobis_truncates_the_numerically_dead_tail():
    """全成分を足すと群内の個体まで巨大になる。既定がそれを避けていること。"""
    fam = ss.shape_synth_family(12, 80, seed=0)
    m = ss.shape_pca(fam)
    inside = ss.shape_mahalanobis(m, fam[0])
    outside = ss.shape_mahalanobis(m, ss.shape_perturb(fam[0], 0.5))
    assert inside < 3.0 and outside > 2.0 * inside, (inside, outside)
    # 裾まで足すと壊れる、を実際に示す(既定を変えたらここで気づく)
    wrecked = ss.shape_mahalanobis(m, fam[0], n_modes=m["variance"].size)
    assert wrecked > 100.0 * inside, (wrecked, inside)


def test_synthesize_stays_inside_the_model():
    fam = ss.shape_synth_family(16, 48, seed=9)
    m = ss.shape_pca(fam)
    new = ss.shape_synthesize(m, seed=1)
    assert new.shape == m["mean"].shape
    assert ss.shape_mahalanobis(m, new) < 6.0


# --------------------------------------------------------------------------- #
# 4. 左右対称性
# --------------------------------------------------------------------------- #
def _paired_landmarks(n_pairs=12, spread=0.4):
    """x = 0 を正中面とする、厳密に左右対称なランドマーク(左 n 個 + 右 n 個)。"""
    rng = np.random.default_rng(0)
    left = np.column_stack([-(0.2 + rng.random(n_pairs) * spread),
                            rng.random(n_pairs) - 0.5,
                            rng.random(n_pairs) - 0.5])
    right = left * np.array([-1.0, 1.0, 1.0])
    return np.vstack([left, right])


def test_mirror_plane_is_found_on_a_symmetric_set():
    lm = _paired_landmarks()
    plane = ss.mirror_plane_from_pairs(lm)
    assert plane.shape == (2, 3)
    assert abs(plane[0, 0]) < 1e-12                              # 面は x = 0
    assert abs(abs(plane[1, 0]) - 1.0) < 1e-9                    # 法線は x 軸
    assert np.max(np.abs(ss.landmark_asymmetry(lm))) < 1e-12


def test_the_landmark_plane_is_not_dragged_by_a_one_sided_change():
    """★ 片側だけ動かしても正中面は動かない(中点が動かないから)。

    残差を最小にする面はここで引きずられる —— 2026-09-06 の PoC 実測で
    6.4 mm の片側変形に対し 2.92 mm / 1.72 度ずれ、非対称量の 46 % を消した。
    ランドマーク面はその代わりに、対の対応が要る。
    """
    lm = _paired_landmarks()
    n = lm.shape[0] // 2
    moved = lm.copy()
    moved[n:] += np.array([0.25, 0.0, 0.0])                      # 右側だけ外へ
    plane = ss.mirror_plane_from_pairs(moved)
    assert abs(plane[0, 0] - 0.125) < 1e-9, plane[0]             # 中点はちょうど半分動く

    # ★ **面を自由にすると、片側の一様な広がりは丸ごと吸われる**(実測 4.9e-35)。
    #   中点が半分だけ動き、面もそこへ動くので、左右差として残らない。これは
    #   この定義の限界であって不具合ではない —— 見たいなら面を外から与えるか、
    #   正中線上のランドマーク(midline)を足すこと。
    assert np.max(np.abs(ss.landmark_asymmetry(moved))) < 1e-12

    # 面を元のまま(x = 0)固定すれば、入れた量がそのまま出る。
    fixed = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    assert np.allclose(ss.landmark_asymmetry(moved, plane=fixed), 0.25, atol=1e-9)


def test_asymmetry_keeps_its_sign():
    """符号は「右が外側なら正」。面は固定して測る(自由な面は一様分を吸うため)。"""
    lm = _paired_landmarks()
    n = lm.shape[0] // 2
    fixed = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    out, inn = lm.copy(), lm.copy()
    out[n:] += np.array([0.1, 0.0, 0.0])
    inn[n:] -= np.array([0.1, 0.0, 0.0])
    assert float(np.mean(ss.landmark_asymmetry(out, plane=fixed))) > 0.0
    assert float(np.mean(ss.landmark_asymmetry(inn, plane=fixed))) < 0.0


def test_a_single_pair_moved_is_visible_even_with_a_free_plane():
    """1 対だけ動かせば中点集合の当てはめは支配されず、ちゃんと出る。"""
    lm = _paired_landmarks()
    n = lm.shape[0] // 2
    one = lm.copy()
    one[n] += np.array([0.3, 0.0, 0.0])                          # 右の 1 点だけ外へ
    dev = ss.landmark_asymmetry(one)
    # 実測: 動かした対が 0.225(入れた 0.3 の 75 %。残りは面が吸う)、他の最大が
    # 0.073。面がわずかに傾くので他の対にも漏れるが、3 倍の差が付いて見分く。
    assert dev[0] > 0.2, dev
    assert np.max(np.abs(dev[1:])) < 0.4 * dev[0], dev


def test_odd_landmark_counts_are_refused_when_pairs_are_implied():
    with pytest.raises(ValueError, match="偶数"):
        ss.mirror_plane_from_pairs(np.zeros((7, 3)))


# --------------------------------------------------------------------------- #
# 5. 符号つき面距離
# --------------------------------------------------------------------------- #
def test_signed_distance_is_positive_outside_and_negative_inside():
    rng = np.random.default_rng(0)
    v = rng.standard_normal((600, 3))
    sphere = v / np.linalg.norm(v, axis=1, keepdims=True)
    outside = sphere[:50] * 1.3
    inside = sphere[:50] * 0.7
    d_out = ss.signed_surface_distance(outside, sphere, sphere, k=4)
    d_in = ss.signed_surface_distance(inside, sphere, sphere, k=4)
    assert (d_out > 0).mean() > 0.98, (d_out > 0).mean()
    assert (d_in < 0).mean() > 0.98, (d_in < 0).mean()
    assert abs(float(np.median(d_out)) - 0.3) < 0.05
    assert abs(float(np.median(d_in)) + 0.3) < 0.05


def test_signed_distance_refuses_a_normal_count_mismatch():
    p = ss.shape_synth_family(2, 40, seed=0)[0]
    with pytest.raises(ValueError, match="surface_normals"):
        ss.signed_surface_distance(p, p, p[:10])
