"""poc_surface_defect_classifiers の門を小さく回す: 描画が意味のある像であること、閉形式の参照と
Fullseye の分類器が一致すること、未知の欠陥を拒否できること、ラベルを入れ替えると偶然の正解率に落ちること。

The full PoC (5 seeds, 650 patches each, scikit-learn second implementation when installed) runs in
``test_poc_scripts_run.py``; these are the cheap pieces that pin its building blocks.
"""
import numpy as np
import pytest

from examples import poc_surface_defect_classifiers as P

L = P.L


@pytest.fixture(scope="module")
def one_seed():
    return P.run_seed(11)


def test_render_is_meaningful_and_only_the_stain_changes_colour():
    rng = np.random.default_rng(0)
    for kind in P.CLASSES + (P.UNKNOWN,):
        img, mask, lay = P.render_patch(kind, 0.8, rng)
        assert img.shape == (P.SIZE, P.SIZE, 3) and np.isfinite(img).all()
        assert 0.0 <= img.min() and img.max() <= 1.0 and np.ptp(img) > 0.2
        assert mask.any() == (kind == "stain")
        assert np.isnan(lay) == (kind != "scratch")
        c = P.chroma(img)
        if kind == "stain":
            assert c[mask].mean() - c[~mask].mean() > 0.05
        else:                                  # 高さの欠陥は陰影だけ: 色度は金属のまま
            assert abs(np.median(c) - np.median(P.chroma(P.render_patch("normal", 0.0, rng)[0]))) < 0.01


def test_render_rejects_an_unknown_kind():
    with pytest.raises(ValueError):
        P.render_patch("crack", 0.5, np.random.default_rng(0))


def test_gmm_one_centre_equals_closed_form_qda_and_knn_equals_brute_force(one_seed):
    r = one_seed
    X, y = r["X"], r["labels"]
    Xtr, ytr, Xte = X[r["tr"]], y[r["tr"]], X[r["te"]]
    assert np.mean(r["pred"]["gmm1"] == P.qda_reference(Xtr, ytr, Xte)) >= 0.995
    assert np.mean(r["pred"]["knn"] == P.knn_reference(Xtr, ytr, Xte)) >= 0.99
    pix = r["pix"]
    assert np.allclose(pix["inv"] @ pix["cov"], np.eye(3), atol=1e-8)


def test_classifiers_are_far_above_chance_but_not_perfect(one_seed):
    r = one_seed
    for name, p in r["pred"].items():
        acc = float(np.mean(p == r["yte"]))
        assert 0.75 < acc < 1.0, (name, acc)
    assert r["perm_acc"] < 0.25 + 3 * np.sqrt(0.25 * 0.75 / len(r["yte"]))


def test_second_implementation_is_within_the_binomial_tolerance(one_seed):
    r = one_seed
    refs = r["sk"] if r["sk"] is not None else {"mlp": r["logreg"], "svm": r["logreg"]}
    for name in ("gmm1", "gmm2", "mlp", "svm", "knn"):
        if name not in refs:
            continue
        d, tol, _, worst = P.compare(r["pred"][name], refs[name], r["yte"])
        assert d <= tol and worst <= 1.0, (name, d, tol, worst)


def test_gmm_rejects_the_defect_it_never_saw(one_seed):
    r = one_seed
    assert r["reject_unknown"] >= 0.8
    assert r["reject_known"] <= P.REJECT_Q + 3 * np.sqrt(P.REJECT_Q * (1 - P.REJECT_Q) / len(r["yte"]))


def test_stain_pixels_lut_beats_the_min_max_box(one_seed):
    r = one_seed
    assert r["lut_iou"] > 0.6 and r["lut_fp"] < 0.01
    assert r["lut_iou"] > r["sup_iou"] > 0.5
    assert r["uns_z"] > r["uns_raw"]


def test_binom_tol_is_finite_at_perfect_accuracy():
    assert 0.0 < P.binom_tol(1.0, 45) < 0.2
    assert P.binom_tol(0.5, 100) > P.binom_tol(0.9, 100)
