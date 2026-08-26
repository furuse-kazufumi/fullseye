"""descriptors3d — 点群の大域形状記述子(統計ベース shape distribution)。

点群(numpy 配列 (N,3))から、**平行移動・回転・スケールに不変**な大域記述子
(ヒストグラム)を計算する。3D 形状検索(retrieval)・分類(classification)向けの
コンパクトなシグネチャで、numpy in / numpy out・scipy(任意)のみ。

match3d.sh_descriptor(球面調和 = 周波数空間の帯域エネルギー)とは**別系統**:
こちらは Osada 2002 "Shape Distributions" 流の**統計記述子**。voxel を必要とせず、
点群のペア/トリプルを乱択して幾何量の分布を測るだけなので、
- メッシュ化・voxel 化・法線推定が不要(生の点群でよい)、
- 大域統計なので部分欠損・ノイズにゆるやかに頑健、
- SH のような固定 grid 解像度・torch 依存がない、
という特徴を持つ。

提供する関数:
    d2_distribution(points, bins, samples, seed)  ランダム 2 点対の距離分布(D2)
    a3_distribution(points, bins, samples, seed)  ランダム 3 点のなす角分布(A3)
    extent_signature(points)                      PCA 主軸に沿った広がり比(3,)
    describe(points, bins, seed)                  上記を連結した大域記述子
    shape_distance(desc_a, desc_b, metric)        記述子間距離(小 = 同形状)

不変性の根拠:
    D2 — 距離は回転・平行移動で不変。さらに**平均距離で割って正規化**するので
         スケールにも不変(Osada は max やモデル体積で正規化するが、平均は外れ値に
         強い)。固定レンジ [0, _D2_MAX] のヒストグラムにして shape 間で比較可能に。
    A3 — 角度は回転・平行移動・スケールすべてに不変。レンジは [0, π] 固定。
    extent — 共分散の固有値は回転で不変。固有値の比(= 主軸に沿った広がりの比)を
         とれば絶対スケールが消え、正規化して (3,) ベクトルにする。

軸規約: points[:, 0], [:, 1], [:, 2] = (x, y, z)。順序は結果に影響しない(全指標が
座標軸の取り方に不変)。
"""
from __future__ import annotations

import numpy as np

# D2 の正規化距離ヒストグラムの上限。距離を平均距離で割った値の範囲。
# 一様な線分(最も細長い形状)の pairwise 距離は 平均 = L/3、最大 = L なので
# 正規化最大 = 3.0。これを上限にすれば棒の端点対まで最終 bin に収まる。
# コンパクト形状(球 ~1.9 / 立方体 ~2.6)は上限に余裕を残す。
_D2_MAX = 3.0
_EPS = 1e-12


# --------------------------------------------------------------------------- #
# 入力検証                                                                     #
# --------------------------------------------------------------------------- #
def _check_points(points, min_points: int, name: str = "points") -> np.ndarray:
    """(N,3) の実数点群であることを検証し、float64 の連続配列にして返す。

    点数不足・次元違い・非有限値を明示的な ValueError で弾く(黙って NaN を
    下流に流さない)。
    """
    arr = np.asarray(points, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 3:
        raise ValueError(
            f"{name} は (N,3) の点群である必要があります: shape={arr.shape}"
        )
    n = arr.shape[0]
    if n < min_points:
        raise ValueError(
            f"{name} の点数が不足しています: N={n}(この指標には最低 {min_points} 点が必要)"
        )
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} に NaN/Inf が含まれています。前処理で除去してください")
    return np.ascontiguousarray(arr)


def _normalized_hist(values: np.ndarray, bins: int, lo: float, hi: float) -> np.ndarray:
    """[lo, hi] 固定レンジで正規化ヒストグラム(総和 1)を作る。

    レンジ外の値はクリップして端 bin に寄せる(np.histogram の range は範囲外を
    捨ててしまい総和が形状ごとに変わるため、ここでは事前にクリップして質量を保存)。
    空入力・全ゼロは一様分布にフォールバックして NaN を出さない。
    """
    if bins < 1:
        raise ValueError(f"bins は 1 以上である必要があります: bins={bins}")
    v = np.asarray(values, dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return np.full(bins, 1.0 / bins)
    # hi ちょうどの値が最終 bin に入るよう、上端をわずかに内側へクリップ。
    v = np.clip(v, lo, np.nextafter(hi, lo))
    counts, _ = np.histogram(v, bins=bins, range=(lo, hi))
    total = counts.sum()
    if total <= 0:
        return np.full(bins, 1.0 / bins)
    return counts.astype(np.float64) / float(total)


# --------------------------------------------------------------------------- #
# 1. D2 — ランダム 2 点対の距離分布                                            #
# --------------------------------------------------------------------------- #
def d2_distribution(points, bins: int = 64, samples: int = 100_000, seed: int = 0) -> np.ndarray:
    """ランダムな 2 点対のユークリッド距離分布(Osada 2002 の D2)。

    N 点から `samples` 組の相異なる点対 (i, j) を乱択し、その距離を集計する。
    距離は**平均距離で割って正規化**するため、回転・平行移動・**スケール**に不変。
    固定レンジ [0, _D2_MAX] の正規化ヒストグラム (bins,) を返す(総和 1)。

    Parameters
    ----------
    points : array_like, shape (N, 3)
        点群。N >= 2 が必要。
    bins : int
        ヒストグラムの bin 数。
    samples : int
        乱択する点対の数。多いほど分散が下がる(サンプリング誤差 ~ 1/sqrt(samples))。
    seed : int
        乱数シード。同 seed・同点群なら決定論的に同一。

    Returns
    -------
    np.ndarray, shape (bins,)
        正規化距離ヒストグラム。
    """
    p = _check_points(points, min_points=2)
    n = p.shape[0]
    if samples < 1:
        raise ValueError(f"samples は 1 以上である必要があります: samples={samples}")
    rng = np.random.default_rng(seed)
    i = rng.integers(0, n, size=samples)
    # j != i を保証: i に [1, n-1] のオフセットを足して mod n。
    off = rng.integers(1, n, size=samples)
    j = (i + off) % n
    diff = p[i] - p[j]
    dist = np.sqrt(np.einsum("ij,ij->i", diff, diff))
    mean = float(dist.mean())
    if mean < _EPS:
        # 全点がほぼ同一座標(退化)。正規化不能なので bin0 に全質量。
        norm = np.zeros_like(dist)
    else:
        norm = dist / mean
    return _normalized_hist(norm, bins, 0.0, _D2_MAX)


# --------------------------------------------------------------------------- #
# 2. A3 — ランダム 3 点のなす角分布                                            #
# --------------------------------------------------------------------------- #
def a3_distribution(points, bins: int = 64, samples: int = 100_000, seed: int = 0) -> np.ndarray:
    """ランダムな 3 点 (A, B, C) が頂点 B で作る角の分布(Osada 2002 の A3)。

    角度は回転・平行移動・スケールのすべてに不変(スケールしても角は変わらない)ため、
    D2 と相補的な**無次元**の形状特徴になる。レンジ [0, π] 固定の正規化ヒストグラム
    (bins,) を返す(総和 1)。空間的に重なった点(ゼロ長ベクトル)は角が未定義なので
    除外する。

    Parameters
    ----------
    points : array_like, shape (N, 3)
        点群。N >= 3 が必要。
    bins, samples, seed :
        d2_distribution と同義。

    Returns
    -------
    np.ndarray, shape (bins,)
        正規化角度ヒストグラム(ラジアン、[0, π])。
    """
    p = _check_points(points, min_points=3)
    n = p.shape[0]
    if samples < 1:
        raise ValueError(f"samples は 1 以上である必要があります: samples={samples}")
    rng = np.random.default_rng(seed)
    b = rng.integers(0, n, size=samples)                 # 頂点
    a = (b + rng.integers(1, n, size=samples)) % n       # b != a
    c = (b + rng.integers(1, n, size=samples)) % n       # b != c
    # a == c を解消(相異なる 3 点にする)。n >= 3 なので必ず可能。
    clash = a == c
    c[clash] = (c[clash] + 1) % n
    ci = c == b
    c[ci] = (c[ci] + 1) % n

    u = p[a] - p[b]
    w = p[c] - p[b]
    nu = np.sqrt(np.einsum("ij,ij->i", u, u))
    nw = np.sqrt(np.einsum("ij,ij->i", w, w))
    valid = (nu > _EPS) & (nw > _EPS)
    if not np.any(valid):
        return np.full(bins, 1.0 / bins)
    cos = np.einsum("ij,ij->i", u[valid], w[valid]) / (nu[valid] * nw[valid])
    cos = np.clip(cos, -1.0, 1.0)
    ang = np.arccos(cos)
    return _normalized_hist(ang, bins, 0.0, float(np.pi))


# --------------------------------------------------------------------------- #
# 3. extent — PCA 主軸に沿った広がり比                                         #
# --------------------------------------------------------------------------- #
def extent_signature(points) -> np.ndarray:
    """PCA 主軸(共分散の固有ベクトル)方向の広がりの比を返す。

    共分散行列の固有値は回転に不変。ここでは固有値の平方根(= 各主軸方向の標準偏差、
    長さの次元)を降順に並べ、総和 1 に正規化して (3,) ベクトルにする。これにより
    絶対スケールが消え、**回転・平行移動・スケールに不変**な「形の細長さ」指標になる。

    - 等方的な形状(球・立方体)→ 3 成分がほぼ等値 [~0.33, ~0.33, ~0.33]
    - 細長い棒 → 1 成分が突出 [~0.9, ~0.05, ~0.05]

    Parameters
    ----------
    points : array_like, shape (N, 3)
        点群。N >= 3 が必要(共分散を意味のある形で作るため)。

    Returns
    -------
    np.ndarray, shape (3,)
        降順・総和 1 に正規化した広がりベクトル。
    """
    p = _check_points(points, min_points=3)
    centered = p - p.mean(axis=0, keepdims=True)
    # rowvar=False: 各列が変数(x,y,z)。3x3 共分散。
    cov = np.cov(centered, rowvar=False)
    cov = np.atleast_2d(cov)
    # 対称行列 → eigvalsh(実固有値・昇順)。数値誤差の微小負値は 0 にクランプ。
    eig = np.linalg.eigvalsh(cov)
    eig = np.clip(eig, 0.0, None)
    std = np.sqrt(eig)
    std = np.sort(std)[::-1]  # 降順
    total = float(std.sum())
    if total < _EPS:
        # 全点が同一点(広がりゼロ)。等方フォールバック。
        return np.full(3, 1.0 / 3.0)
    return (std / total).astype(np.float64)


# --------------------------------------------------------------------------- #
# 4. describe — 連結記述子                                                     #
# --------------------------------------------------------------------------- #
def describe(points, bins: int = 64, seed: int = 0) -> np.ndarray:
    """D2 + A3 + extent を連結した大域形状記述子を返す。

    長さ 2*bins + 3 の 1 次元 float64 ベクトル。並びは [d2(bins), a3(bins), extent(3)]。
    各部分ブロックはそれぞれ総和 1 に正規化済みなので、L1 距離での比較時に 3 指標が
    おおよそ等しい重みで効く。

    Parameters
    ----------
    points : array_like, shape (N, 3)
        点群。N >= 3 が必要。
    bins : int
        D2 / A3 それぞれの bin 数。
    seed : int
        D2 / A3 の乱択シード(両者に同一 seed を渡す)。

    Returns
    -------
    np.ndarray, shape (2*bins + 3,)
    """
    d2 = d2_distribution(points, bins=bins, seed=seed)
    a3 = a3_distribution(points, bins=bins, seed=seed)
    ext = extent_signature(points)
    return np.concatenate([d2, a3, ext]).astype(np.float64)


# --------------------------------------------------------------------------- #
# 5. shape_distance — 記述子間距離                                             #
# --------------------------------------------------------------------------- #
def shape_distance(desc_a, desc_b, metric: str = "l1") -> float:
    """2 つの記述子間の距離。小さいほど同形状。

    Parameters
    ----------
    desc_a, desc_b : array_like
        describe() などが返す同じ長さのベクトル。
    metric : {"l1", "jsd"}
        - "l1" : L1(マンハッタン)距離。連結記述子(部分分布の並び)に素直で既定。
        - "jsd": Jensen-Shannon 距離(全体を 1 つの分布とみなし総和 1 に正規化してから
                 JS ダイバージェンスの平方根)。0〜1 に収まる有界指標。

    Returns
    -------
    float
        非負の距離。
    """
    a = np.asarray(desc_a, dtype=np.float64).ravel()
    b = np.asarray(desc_b, dtype=np.float64).ravel()
    if a.shape != b.shape:
        raise ValueError(f"記述子の長さが一致しません: {a.shape} vs {b.shape}")
    if a.size == 0:
        raise ValueError("記述子が空です")
    if not (np.all(np.isfinite(a)) and np.all(np.isfinite(b))):
        raise ValueError("記述子に NaN/Inf が含まれています")

    metric = metric.lower()
    if metric == "l1":
        return float(np.abs(a - b).sum())
    if metric == "jsd":
        pa = a / (a.sum() + _EPS)
        pb = b / (b.sum() + _EPS)
        m = 0.5 * (pa + pb)

        def _kl(x, y):
            mask = x > 0
            return float(np.sum(x[mask] * np.log2(x[mask] / (y[mask] + _EPS))))

        js = 0.5 * _kl(pa, m) + 0.5 * _kl(pb, m)
        js = max(js, 0.0)  # 数値誤差でわずかに負になるのを防ぐ
        return float(np.sqrt(js))
    raise ValueError(f"未知の metric です: {metric!r}('l1' か 'jsd')")
