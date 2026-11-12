"""poc_caltab_chain_truth の門を小さく回す: 描画が推定と独立であること、量子化の床が理論どおりであること、
検出の対応づけが全点そろうこと、雑音で検出のずれが増えること。

The full PoC (8 views, 24 seeds x 4 noise levels) runs in ``test_poc_scripts_run.py``; these are the
cheap pieces that pin the chain's building blocks.
"""
import numpy as np
import pytest

from examples import poc_caltab_chain_truth as P


@pytest.fixture(scope="module")
def one_view():
    plate, xy = P.board()
    pose = P.poses()[2]
    img = P.render_view(xy, pose, supersample=3)
    return plate, xy, pose, img, P.true_pixels(xy, pose)


def test_board_is_centred_and_complete():
    plate, xy = P.board()
    assert xy.shape == (P.ROWS * P.COLS, 2)
    assert np.allclose(xy.mean(0), 0.0)
    assert np.isclose(np.ptp(xy[:, 0]), (P.COLS - 1) * P.SPACING)


def test_render_is_meaningful(one_view):
    _, _, _, img, _ = one_view
    assert img.shape == P.SHAPE and np.isfinite(img).all()
    assert img.min() >= 0.0 and img.max() <= 1.0 and np.ptp(img) > 0.5
    # 明るい(マーク)画素の面積 ≈ 63 個の円の像の面積(ρ ~ 6 px)
    frac = float((img > 0.5).mean())
    assert 0.003 < frac < 0.05


def test_detection_matches_projected_centres_at_the_quantisation_floor(one_view):
    plate, _, pose, img, truth = one_view
    found = P.detect(img, plate)
    err = np.linalg.norm(found - truth, axis=1)
    rho = P.MARK_RADIUS * np.sqrt(P.K_TRUE[0, 0] * P.K_TRUE[1, 1]) / pose[2, 3]
    pred = 1.0 / np.sqrt(6 * np.pi * rho)
    rms = float(np.sqrt(np.mean(err ** 2)))
    assert 0.7 < rms / pred < 1.4, (rms, pred)
    assert err.max() < 4 * pred


def test_render_does_not_share_the_estimator_formula(one_view):
    """描いた像から検出した点は、歪みなしの投影から数 px ずれ、歪みありの真値には床の内で合う
    —— 描画は歪みを本当に通っている(検出が歪みなしの式の写しではない)。"""
    plate, xy, pose, img, truth = one_view
    X = np.column_stack([xy, np.zeros(len(xy))])
    import fullseye as fs
    uv, _ = fs.project_points(X, P.K_TRUE, pose[:3, :3], pose[:3, 3])
    pinhole = uv[:, ::-1]
    found = P.detect(img, plate)
    assert np.linalg.norm(found - pinhole, axis=1).max() > 3.0
    assert np.linalg.norm(found - truth, axis=1).max() < 0.4


def test_noise_increases_detection_deviation(one_view):
    plate, _, _, img, _ = one_view
    f0 = P.detect(img, plate)
    devs = []
    for s in (0.02, 0.2):
        d = [np.sqrt(np.mean((P.detect(P.noisy(img, s, k), plate) - f0) ** 2)) for k in range(4)]
        devs.append(float(np.mean(d)))
    assert devs[1] > 1.5 * devs[0] > 0.0


def test_detect_rejects_a_blank_image():
    plate, _ = P.board()
    with pytest.raises((AssertionError, ValueError)):
        P.detect(np.zeros(P.SHAPE), plate)


def test_eccentricity_is_far_below_the_quantisation_floor():
    plate, xy = P.board()
    pose = P.poses()[2]
    truth = P.true_pixels(xy, pose)
    ecc = P.mark_eccentricity(xy, [pose], [truth])
    rho = P.MARK_RADIUS * np.sqrt(P.K_TRUE[0, 0] * P.K_TRUE[1, 1]) / pose[2, 3]
    assert ecc.max() < 0.03 and np.sqrt(np.mean(ecc ** 2)) < 0.25 / np.sqrt(6 * np.pi * rho)


def test_grey_centroid_is_much_closer_than_the_binary_centroid(one_view):
    plate, _, _, img, truth = one_view
    g = P.grey_centroids(img, truth)
    b = P.detect(img, plate)
    assert np.sqrt(np.mean((g - truth) ** 2)) < 0.5 * np.sqrt(np.mean((b - truth) ** 2))


def test_cached_rays_give_the_same_image_as_a_fresh_computation(one_view):
    _, xy, pose, img, _ = one_view
    P._RAYS.clear()
    assert np.array_equal(P.render_view(xy, pose, supersample=3), img)


def test_judge_flags_a_wrong_calibration():
    plate, xy = P.board()
    Ps = P.poses()
    truths = [P.true_pixels(xy, p) for p in Ps]
    good = P.calibrate(xy, truths)                          # 完全な点は真値に戻る
    j = P.judge(good, Ps)
    assert max(abs(v) for v in j["dp"].values()) < 1e-6 and j["rot"].max() < 1e-5
    shifted = P.calibrate(xy, [t * 1.002 + 0.0 for t in truths])   # 全点を 0.2 % 拡大(原点まわり): fx が動く
    assert abs(shifted["fx"] - P.K_TRUE[0, 0]) > 0.5
