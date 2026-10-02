"""HALCON 風の分類器: 学習する側(train_class_mlp / train_class_svm)を facade に載せた門。

2026-10-02: 分類する側(classify_image_class_mlp/svm)だけが ``fs.vision`` から呼べ、モデルを作る手段が
公開経路に無かった(名前の無い非公開関数 136 本の棚卸しで発見)。入口と消費を同じ経路に揃える。
正直に: HALCON の train_class_* はハンドル型 API で、ここは小規模な numpy 実装(パリティではない、
OP_DISPOSITION は out_of_scope_model のまま)。
"""
import warnings

import numpy as np
import pytest

import final_genuine2 as FG


_CENTRES = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, 0.9]])   # 三角形(一直線に並べると OvR 線形 SVM は原理的に苦手)


def _blobs(k=2, n=60, seed=0, sep=4.0):
    rng = np.random.default_rng(seed)
    X = np.concatenate([rng.normal(sep * _CENTRES[c], 0.15 * sep, (n, 2)) for c in range(k)])
    y = np.repeat(np.arange(k), n)
    return X, y


def _acc(train, classify, X, y):
    return (classify(X.reshape(1, -1, X.shape[1]), train(X, y)).ravel() == y).mean()


def _vision():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import fullseye as fs
    return fs.vision


def test_train_ops_are_reachable_from_the_facade():
    v = _vision()
    assert v.tools.train_class_mlp is not None
    assert v.tools.train_class_svm is not None


@pytest.mark.parametrize("k", [2, 3])
def test_mlp_trains_a_model_that_the_public_classifier_consumes(k):
    """学習 → classify_image_class_mlp(公開済み)の往復で、分離した塊を当てる。"""
    X, y = _blobs(k)
    model = FG.train_class_mlp(X, y)
    # 特徴画像 = 1 行 × N 画素 × 2 チャネル
    pred = FG.classify_image_class_mlp(X.reshape(1, -1, 2), model).ravel()
    assert (pred == y).mean() >= 0.98


@pytest.mark.parametrize("k", [2, 3])
def test_svm_separates_blobs(k):
    X, y = _blobs(k)
    assert _acc(FG.train_class_svm, FG.classify_image_class_svm, X, y) >= 0.98


@pytest.mark.parametrize("pair", [(FG.train_class_mlp, FG.classify_image_class_mlp),
                                  (FG.train_class_svm, FG.classify_image_class_svm)],
                         ids=["mlp", "svm"])
def test_prediction_is_invariant_to_the_feature_scale(pair):
    """標準化の不変性: 特徴を 0.01 倍〜100 倍にしても予測は 1 画素も変わらない。

    2026-10-02 の回帰: 標準化が無かった頃、3 クラスで MLP は尺度 4 以上で 0.69、SVM は 0.04 / 400 で
    0.33〜0.75 まで落ちていた。
    """
    train, classify = pair
    X, y = _blobs(3)
    base = classify(X.reshape(1, -1, 2), train(X, y)).ravel()
    for s in (0.01, 0.1, 10.0, 100.0):
        Xs = X * s + 3.0 * s
        got = classify(Xs.reshape(1, -1, 2), train(Xs, y)).ravel()
        assert np.array_equal(got, base), s


def test_a_model_without_standardisation_still_classifies():
    """mu / sd を持たない古いモデル dict は従来どおり生の特徴で分類する。"""
    X, y = _blobs(2, sep=1.0)
    m = FG.train_class_mlp(X, y)
    raw = {k: v for k, v in m.items() if k not in ("mu", "sd")}
    Xn = (X - m["mu"]) / m["sd"]
    a = FG.classify_image_class_mlp(X.reshape(1, -1, 2), m)
    b = FG.classify_image_class_mlp(Xn.reshape(1, -1, 2), raw)
    assert np.array_equal(a, b)


def test_mlp_is_deterministic_for_a_fixed_seed():
    X, y = _blobs(2)
    a = FG.train_class_mlp(X, y)
    b = FG.train_class_mlp(X, y)
    assert all(np.array_equal(a[k], b[k]) for k in ("W1", "b1", "W2", "b2"))


def test_mlp_agrees_with_sklearn_on_separable_data():
    """第 2 実装: sklearn の MLPClassifier と、分離可能な 3 クラスで予測が揃う。"""
    sk = pytest.importorskip("sklearn.neural_network")
    X, y = _blobs(3)
    ours = FG.classify_image_class_mlp(X.reshape(1, -1, 2), FG.train_class_mlp(X, y)).ravel()
    ref = sk.MLPClassifier(hidden_layer_sizes=(8,), max_iter=2000, random_state=0).fit(X, y).predict(X)
    assert (ours == ref).mean() >= 0.98


def test_svm_labels_are_the_original_class_values():
    """クラス値が 0..K-1 でなくても(例: 7 と 11)元の値を返す。"""
    X, y = _blobs(2)
    y2 = np.where(y == 0, 7, 11)
    model = FG.train_class_svm(X, y2)
    pred = FG.classify_image_class_svm(X.reshape(1, -1, 2), model).ravel()
    assert set(np.unique(pred)) <= {7, 11}
    assert (pred == y2).mean() >= 0.98
