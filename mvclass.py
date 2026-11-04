# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""mvclass —— 特徴ベクトルの分類器(GMM / k-NN / 既存 MLP・SVM の入口)と語彙の照合。

モデルはどれも dict。``train_class_mlp`` / ``train_class_svm``(``final_genuine2``)の返りは
画素分類にしか渡せなかったので、ベクトルの入口 ``classify_class_mlp`` / ``classify_class_svm``
をここへ足した。GMM の EM は乱数の種を固定できるので結果は決定的。
出典: A. P. Dempster, N. M. Laird, D. B. Rubin, J. R. Stat. Soc. B 39(1), 1-38 (1977);
T. Cover and P. Hart, IEEE Trans. Inf. Theory 13(1), 21-27 (1967);
V. I. Levenshtein, Sov. Phys. Dokl. 10(8), 707-710 (1966)。
"""
from __future__ import annotations

import numpy as np


def _features(features, op):
    X = np.asarray(features, dtype=np.float64)
    if X.size == 0:
        raise ValueError("%s: features are empty — pass at least one row" % op)
    if X.ndim == 1:
        X = X[:, None]
    if X.ndim != 2 or not np.isfinite(X).all():
        raise ValueError("%s: features must be a finite (N, D) array" % op)
    return X


def _labels(features, labels, op):
    X = _features(features, op)
    y = np.asarray(labels).ravel()
    if y.size != X.shape[0]:
        raise ValueError("%s: %d rows but %d labels" % (op, X.shape[0], y.size))
    if np.unique(y).size < 2:
        raise ValueError("%s: need at least 2 classes" % op)
    return X, y


def _log_gauss(X, mean, cov):
    """多変量正規分布の対数密度。共分散が特異なら ValueError。"""
    try:
        L = np.linalg.cholesky(cov)
    except np.linalg.LinAlgError as exc:
        raise ValueError("train_class_gmm: covariance is singular") from exc
    z = np.linalg.solve(L, (X - mean).T)
    return -0.5 * (np.sum(z * z, axis=0) + X.shape[1] * np.log(2.0 * np.pi)) - np.log(np.diag(L)).sum()


def _em(X, n_centers, iterations, tol, reg, rng):
    """1 クラスの点に混合正規分布を EM で当てはめる。"""
    n, d = X.shape
    k = min(int(n_centers), n)
    means = X[rng.choice(n, k, replace=False)].copy()
    base = np.cov(X.T, bias=True).reshape(d, d) + np.eye(d) * reg
    covs = np.stack([base.copy() for _ in range(k)])
    weights = np.full(k, 1.0 / k)
    last = -np.inf
    for _ in range(int(iterations)):
        logp = np.stack([np.log(weights[j]) + _log_gauss(X, means[j], covs[j]) for j in range(k)], axis=1)
        top = logp.max(axis=1, keepdims=True)
        px = np.exp(logp - top)
        total = px.sum(axis=1, keepdims=True)
        resp = px / total
        loglik = float((top[:, 0] + np.log(total[:, 0])).sum())
        nk = resp.sum(axis=0) + 1e-12
        weights = nk / n
        means = (resp.T @ X) / nk[:, None]
        for j in range(k):
            dx = X - means[j]
            covs[j] = (dx * resp[:, j:j + 1]).T @ dx / nk[j] + np.eye(d) * reg
        if abs(loglik - last) <= tol * (1.0 + abs(loglik)):
            break
        last = loglik
    return {"weights": weights, "means": means, "covs": covs}


def train_class_gmm(features, labels, n_centers=1, iterations=100, tol=1e-6, regularize=1e-6, seed=0):
    """クラスごとに混合正規分布を EM で学習する。

    事前確率はクラスの行数の比。``n_centers=1`` は 2 次判別分析と同じ。
    空の入力(``features`` が 0 要素)は ValueError。

    Args:
        features: (N, D) の特徴。
        labels: 長さ N のクラス(2 種類以上)。
        n_centers: クラスあたりの成分数(>= 1)。
        iterations: EM の上限回数(>= 1)。
        tol: 対数尤度の相対変化の収束判定。
        regularize: 共分散の対角に足す値(> 0)。
        seed: 初期中心を選ぶ乱数の種。

    Returns:
        ``classes``、``priors``、``components`` を持つモデルの dict。
    """
    op = "train_class_gmm"
    X, y = _labels(features, labels, op)
    if int(n_centers) < 1 or int(iterations) < 1 or not float(regularize) > 0:
        raise ValueError("%s: n_centers, iterations and regularize must be positive" % op)
    rng = np.random.default_rng(int(seed))
    classes = np.unique(y)
    comps, priors = [], []
    for cls in classes:
        rows = X[y == cls]
        comps.append(_em(rows, n_centers, iterations, float(tol), float(regularize), rng))
        priors.append(rows.shape[0] / X.shape[0])
    return {"classes": classes, "priors": np.array(priors), "components": comps}


def _gmm_model(model, op):
    if not isinstance(model, dict) or "components" not in model or "priors" not in model:
        raise ValueError("%s: model must come from train_class_gmm" % op)
    return model


def evaluate_class_gmm(model, features):
    """各クラスの事後確率と、モデル全体の対数密度を行ごとに返す。

    空の入力(``features`` が 0 要素)は ValueError。

    Args:
        model: :func:`train_class_gmm` の返り。
        features: (N, D) の特徴。

    Returns:
        ``posterior`` (N, K) と ``log_density`` (N,) を持つ dict。
    """
    op = "evaluate_class_gmm"
    m = _gmm_model(model, op)
    X = _features(features, op)
    d = m["components"][0]["means"].shape[1]
    if X.shape[1] != d:
        raise ValueError("%s: features have %d columns, the model %d" % (op, X.shape[1], d))
    per_class = []
    for prior, comp in zip(m["priors"], m["components"]):
        lp = np.stack([np.log(w) + _log_gauss(X, mu, cv)
                       for w, mu, cv in zip(comp["weights"], comp["means"], comp["covs"])], axis=1)
        top = lp.max(axis=1, keepdims=True)
        per_class.append(np.log(prior) + top[:, 0] + np.log(np.exp(lp - top).sum(axis=1)))
    logs = np.stack(per_class, axis=1)
    top = logs.max(axis=1, keepdims=True)
    px = np.exp(logs - top)
    total = px.sum(axis=1, keepdims=True)
    return {"posterior": px / total, "log_density": top[:, 0] + np.log(total[:, 0])}


def classify_class_gmm(model, features):
    """混合正規分布のモデルで事後確率が最大のクラスを行ごとに返す。

    空の入力(``features`` が 0 要素)は ValueError。

    Args:
        model: :func:`train_class_gmm` の返り。
        features: (N, D) の特徴。

    Returns:
        ``labels`` (N,) と ``confidence`` (N,)(選んだクラスの事後確率)を持つ dict。
    """
    ev = evaluate_class_gmm(model, features)
    best = np.argmax(ev["posterior"], axis=1)
    return {"labels": np.asarray(model["classes"])[best],
            "confidence": ev["posterior"][np.arange(best.size), best]}


def train_class_knn(features, labels):
    """k-NN の分類器を作る(特徴を標準化して保持する)。

    標準偏差が 0 の列は 1 で割る(その列は距離に効かない)。
    空の入力(``features`` が 0 要素)は ValueError。

    Args:
        features: (N, D) の特徴。
        labels: 長さ N のクラス(2 種類以上)。

    Returns:
        ``X``、``y``、``mu``、``sd`` を持つモデルの dict。
    """
    X, y = _labels(features, labels, "train_class_knn")
    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd = np.where(sd > 0, sd, 1.0)
    return {"X": (X - mu) / sd, "y": y, "mu": mu, "sd": sd}


def classify_class_knn(model, features, k=5):
    """k 近傍の多数決でクラスを行ごとに返す(同票は距離の和が小さいクラス)。

    空の入力(``features`` が 0 要素)は ValueError。

    Args:
        model: :func:`train_class_knn` の返り。
        features: (N, D) の特徴。
        k: 近傍の数(>= 1、学習行数まで)。

    Returns:
        ``labels`` (N,) と ``confidence`` (N,)(選んだクラスの票の比)を持つ dict。
    """
    op = "classify_class_knn"
    if not isinstance(model, dict) or "X" not in model or "y" not in model:
        raise ValueError("%s: model must come from train_class_knn" % op)
    X = _features(features, op)
    if X.shape[1] != model["X"].shape[1]:
        raise ValueError("%s: features have %d columns, the model %d" % (op, X.shape[1], model["X"].shape[1]))
    q = (X - model["mu"]) / model["sd"]
    n = model["X"].shape[0]
    kk = int(k)
    if kk < 1 or kk > n:
        raise ValueError("%s: k must be in 1..%d" % (op, n))
    from scipy.spatial import cKDTree
    dist, idx = cKDTree(model["X"]).query(q, k=kk)
    if kk == 1:
        dist, idx = dist[:, None], idx[:, None]
    votes = model["y"][idx]
    labels, conf = [], []
    for row, dr in zip(votes, dist):
        vals, counts = np.unique(row, return_counts=True)
        top = vals[counts == counts.max()]
        if top.size > 1:
            sums = [dr[row == v].sum() for v in top]
            pick = top[int(np.argmin(sums))]
        else:
            pick = top[0]
        labels.append(pick)
        conf.append(counts.max() / kk)
    return {"labels": np.array(labels), "confidence": np.array(conf)}


def _trained_scores(model, X, op):
    if not isinstance(model, dict) or "mu" not in model or "sd" not in model:
        raise ValueError("%s: model must come from the matching train_class_ op" % op)
    return (X - model["mu"]) / model["sd"]


def classify_class_mlp(model, features):
    """``train_class_mlp`` の多層パーセプトロンで特徴の行を分類する。

    中間層の活性は学習の入口と同じ tanh で、出力の softmax を確信度にする。
    空の入力(``features`` が 0 要素)は ValueError。

    Args:
        model: ``train_class_mlp`` の返り。
        features: (N, D) の特徴。

    Returns:
        ``labels`` (N,) と ``confidence`` (N,) を持つ dict。
    """
    op = "classify_class_mlp"
    z = _trained_scores(model, _features(features, op), op)
    if "W1" not in model or "W2" not in model:
        raise ValueError("%s: model must come from train_class_mlp" % op)
    hidden = np.tanh(z @ model["W1"] + model["b1"])
    out = hidden @ model["W2"] + model["b2"]
    out = out - out.max(axis=1, keepdims=True)
    prob = np.exp(out)
    prob /= prob.sum(axis=1, keepdims=True)
    best = np.argmax(prob, axis=1)
    return {"labels": np.asarray(model["classes"])[best], "confidence": prob[np.arange(best.size), best]}


def classify_class_svm(model, features):
    """``train_class_svm`` の線形 SVM で特徴の行を分類する(one-vs-rest の最大マージン)。

    空の入力(``features`` が 0 要素)は ValueError。

    Args:
        model: ``train_class_svm`` の返り。
        features: (N, D) の特徴。

    Returns:
        ``labels`` (N,) と ``margin`` (N,)(選んだクラスの判別値)を持つ dict。
    """
    op = "classify_class_svm"
    z = _trained_scores(model, _features(features, op), op)
    if "weights" not in model:
        raise ValueError("%s: model must come from train_class_svm" % op)
    scores = np.stack([z @ w + b for w, b in model["weights"]], axis=1)
    best = np.argmax(scores, axis=1)
    return {"labels": np.asarray(model["classes"])[best], "margin": scores[np.arange(best.size), best]}


def _levenshtein(a, b, limit=None):
    """編集距離(置換・挿入・削除の費用 1)。"""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def create_lexicon(words):
    """照合に使う語の一覧を作る(重複を除き、順を固定する)。

    空の入力(``words`` が 0 要素)は ValueError。

    Args:
        words: 文字列の並び。

    Returns:
        ``words``(ソートした語のリスト)を持つ dict。
    """
    op = "create_lexicon"
    items = [words] if isinstance(words, str) else list(words)
    if not items:
        raise ValueError("%s: words are empty — pass at least one word" % op)
    if not all(isinstance(w, str) and w for w in items):
        raise ValueError("%s: every word must be a non-empty string" % op)
    return {"words": sorted(set(items))}


def _lexicon(lexicon, op):
    if not isinstance(lexicon, dict) or not lexicon.get("words"):
        raise ValueError("%s: lexicon must come from create_lexicon" % op)
    return lexicon["words"]


def lookup_lexicon(lexicon, word):
    """語が一覧にあるかを完全一致で調べ、あれば 1.0、無ければ 0.0 を返す。

    空の入力(``word`` が空文字)は ValueError。

    Args:
        lexicon: :func:`create_lexicon` の返り。
        word: 調べる語。

    Returns:
        一覧にあれば ``1.0``、無ければ ``0.0``。
    """
    op = "lookup_lexicon"
    words = _lexicon(lexicon, op)
    if not isinstance(word, str) or not word:
        raise ValueError("%s: word must be a non-empty string" % op)
    return 1.0 if word in words else 0.0


def suggest_lexicon(lexicon, word):
    """編集距離が最小の語と、その距離を返す(同距離は一覧の順で最初の語)。

    空の入力(``word`` が空文字)は ValueError。

    Args:
        lexicon: :func:`create_lexicon` の返り。
        word: 調べる語。

    Returns:
        ``suggestion``(語)と ``distance``(整数)を持つ dict。
    """
    op = "suggest_lexicon"
    words = _lexicon(lexicon, op)
    if not isinstance(word, str) or not word:
        raise ValueError("%s: word must be a non-empty string" % op)
    costs = [_levenshtein(word, w) for w in words]
    best = int(np.argmin(costs))
    return {"suggestion": words[best], "distance": int(costs[best])}
