# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""形態統計 —— 形の**群**を比べる層(Procrustes / 統計形状モデル / 対称性)。

この repo には形を**1 つずつ**扱う道具は揃っていた(位置合わせ・SDF・曲率・
メッシュ修復・点群)。足りていなかったのは「**群集平均との差**で語る」層で、
2026-09-06 に左右非対称性の PoC が具体的に列挙した: Procrustes / 一般化
Procrustes(GPA)/ 平均形状 / 形態 PCA / 3-D ランドマークの対応 / 符号つきの
面-面距離。比較形態学(頭蓋・骨・歯)がそれで止まり、工業でも「設計 CAD が
無い部品を、同型の個体群と比べる」ができなかった。

**工業検査との違いは 1 点だけ** —— 設計 CAD が無い。だから基準が
「図面との差」ではなく「**群集平均との差**」「**左右対称性**」「**成長の軸**」に
なる。それ以外は同じパイプライン(抽出 → 位置合わせ → 特徴量化 → 群比較 →
異常検出)に載る。

規約:

* 形は ``(N, 3)`` の点で、**点の並びが対応**していること(ランドマーク、または
  同じ手順で再標本化した頂点)。対応が無い点群を渡しても例外は出ないが、
  返る数はでたらめになる —— 対応の有無はこちらからは見えないので、
  :func:`procrustes_align` は**並び順が意味を持つ**と docstring で宣言する。
* 形の群は ``(K, N, 3)``。K 個体 x N 点。
* 角度は度、距離は入力の単位のまま。

**Procrustes の 3 段階**(どれを取り除くかで意味が変わる):

1. 平行移動を除く(重心を原点へ)—— 位置の違いを捨てる。
2. 回転を除く —— 向きの違いを捨てる。
3. スケールを除く(``scaling=True``)—— **大きさの違いを捨てる**。
   成長や体格差を「形の違い」と数えたくないときはこれ。逆に、大きさ自体が
   形質なら ``scaling=False`` にする。**この選択で結論が変わる**ので既定に
   頼らないこと。

鏡映は既定で**許さない**(``reflection=False``)。許すと左手系の個体が右手系の
平均に重なってしまい、左右非対称性という測りたいものが消える。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "shape_synth_family", "shape_perturb",
    "procrustes_fit", "procrustes_align", "procrustes_distance",
    "generalized_procrustes", "shape_mean",
    "shape_pca", "shape_project", "shape_reconstruct", "shape_mahalanobis",
    "shape_explained_variance", "shape_synthesize",
    "mirror_plane_from_pairs", "landmark_asymmetry", "signed_surface_distance",
]

#: :func:`shape_pca` が返す辞書の必須キー。述語(``shapemodel``)と対。
MODEL_KEYS = ("mean", "components", "variance", "n_points")


def _as_shape(a, name="shape"):
    x = np.asarray(a, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != 3:
        raise ValueError("%s must be (N, 3), got %r" % (name, (x.shape,)))
    if x.shape[0] < 1:
        raise ValueError("%s must have at least 1 point" % name)
    if not np.all(np.isfinite(x)):
        raise ValueError("%s has non-finite values" % name)
    return x


def _as_family(a, name="shapes"):
    x = np.asarray(a, dtype=np.float64)
    if x.ndim != 3 or x.shape[2] != 3:
        raise ValueError("%s must be (K, N, 3), got %r" % (name, (x.shape,)))
    if x.shape[0] < 2:
        raise ValueError("%s needs at least 2 shapes (got %d)" % (name, x.shape[0]))
    if not np.all(np.isfinite(x)):
        raise ValueError("%s has non-finite values" % name)
    return x


# --------------------------------------------------------------------------- #
# 1. 合成 —— 真値を持つ形の群を作る                                            #
# --------------------------------------------------------------------------- #
def shape_synth_family(n_shapes: int = 8, n_points: int = 64, n_modes: int = 2,
                       mode_scale=(0.30, 0.12), noise: float = 0.0,
                       seed: int = 0):
    """既知の変形モードを持つ形の群を作る。→ ``(n_shapes, n_points, 3)``。

    基準形は楕円体上の準一様な点で、そこに **正規直交な変形モード**を
    既知の重みで足す。モード 1 は長軸方向の伸び、モード 2 は左右の曲げ。
    :func:`shape_pca` に食わせると、**主成分の分散比が ``mode_scale`` の 2 乗比に
    一致する**はずで、これが統計形状モデルの検算になる。

    ``noise`` は点ごとの等方ガウス雑音の標準偏差(モデルに乗らない成分)。
    """
    k = int(n_shapes)
    n = int(n_points)
    if k < 2 or n < 4:
        raise ValueError("need n_shapes >= 2 and n_points >= 4")
    m = int(n_modes)
    if m < 1 or m > len(mode_scale):
        raise ValueError("n_modes must be 1..%d (mode_scale の長さ)" % len(mode_scale))
    rng = np.random.default_rng(int(seed))

    # 基準形: 黄金角らせんで楕円体上に散らす(決定的、準一様)
    i = np.arange(n, dtype=np.float64) + 0.5
    z = 1.0 - 2.0 * i / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    phi = np.pi * (3.0 - np.sqrt(5.0)) * i
    base = np.column_stack([1.0 * r * np.cos(phi), 0.6 * r * np.sin(phi), 0.4 * z])

    modes = np.zeros((m, n, 3))
    modes[0, :, 0] = base[:, 0]                       # 長軸の伸び縮み
    if m > 1:
        modes[1, :, 1] = base[:, 0] ** 2 - float(np.mean(base[:, 0] ** 2))  # 曲げ
    for j in range(m):                                 # 正規化(重みの意味を揃える)
        nrm = np.linalg.norm(modes[j])
        if nrm > 0:
            modes[j] /= nrm

    w = rng.standard_normal((k, m)) * np.asarray(mode_scale[:m], float)
    out = base[None, :, :] + np.einsum("km,mnc->knc", w, modes)
    if noise:
        out = out + rng.normal(0.0, float(noise), out.shape)
    return out


def shape_perturb(shape, amplitude: float = 0.05, mode: str = "bulge",
                  center=(1.0, 0.0, 0.0), sigma: float = 0.4, seed: int = 0):
    """形に**既知の**変形を 1 つ入れる。→ ``(N, 3)``。

    ``mode``:

    * ``"bulge"``  —— *center* のまわりをガウス重みで外向きに膨らませる。
      片側だけに入れれば左右非対称性の真値になる。
    * ``"shift"``  —— *center* 方向へ一様に平行移動(Procrustes が消す成分)。
    * ``"scale"``  —— 一様拡大(``scaling=True`` の Procrustes が消す成分)。
    * ``"noise"``  —— 等方ガウス雑音(どの手法でも消えない床)。

    「Procrustes が消してくれる変形」と「消してはいけない変形」を分けて試せる
    ように 4 つ置いてある。位置合わせの検算はこの区別が要る。
    """
    p = _as_shape(shape)
    a = float(amplitude)
    c = np.asarray(center, dtype=np.float64).reshape(3)
    if mode == "shift":
        return p + a * c
    if mode == "scale":
        m = p.mean(0)
        return m + (p - m) * (1.0 + a)
    if mode == "noise":
        return p + np.random.default_rng(int(seed)).normal(0.0, a, p.shape)
    if mode != "bulge":
        raise ValueError("mode must be one of bulge / shift / scale / noise, got %r" % mode)
    d = np.linalg.norm(p - c, axis=1)
    w = np.exp(-(d ** 2) / (2.0 * float(sigma) ** 2))
    n = p - p.mean(0)
    nn = np.linalg.norm(n, axis=1, keepdims=True)
    unit = n / np.maximum(nn, 1e-12)
    return p + a * w[:, None] * unit


# --------------------------------------------------------------------------- #
# 2. Procrustes                                                                #
# --------------------------------------------------------------------------- #
def procrustes_fit(source, target, scaling: bool = True, reflection: bool = False):
    """*source* を *target* へ重ねる相似変換。→ ``(4, 4)`` の同次行列。

    **点の並びが対応していること**が前提(i 番目どうしが同じ解剖学的位置)。
    対応が無い点群では例外は出ず、意味の無い変換が返る —— 対応の有無は
    この関数からは見えない。対応が無いなら ICP 系(``registration``)を使う。

    ``scaling=True`` なら大きさの違いも吸収する。``reflection=False``(既定)は
    ``det(R) = +1`` を強制する —— 許すと左手系の個体が右手系の平均に重なり、
    左右非対称性という測りたいものが消える。

    行列は同次座標で ``target ~ source @ M[:3,:3].T + M[:3,3]`` の向き。
    """
    a = _as_shape(source, "source")
    b = _as_shape(target, "target")
    if a.shape != b.shape:
        raise ValueError("source %r and target %r must have the same shape "
                         "(Procrustes needs point-to-point correspondence)"
                         % (a.shape, b.shape))
    ca, cb = a.mean(0), b.mean(0)
    a0, b0 = a - ca, b - cb
    u, s, vt = np.linalg.svd(a0.T @ b0, full_matrices=False)
    d = np.eye(3)
    if not reflection and np.linalg.det(u @ vt) < 0.0:
        d[2, 2] = -1.0                                # 最小特異値の軸を反転
    R = (u @ d @ vt).T                                # source -> target
    scale = 1.0
    if scaling:
        denom = float((a0 ** 2).sum())
        if denom > 0.0:
            scale = float((s * np.diag(d)).sum() / denom)
    M = np.eye(4)
    M[:3, :3] = scale * R
    M[:3, 3] = cb - scale * (R @ ca)
    return M


def procrustes_align(source, target, scaling: bool = True, reflection: bool = False):
    """*source* を *target* に重ねた点。→ ``(N, 3)``(:func:`procrustes_fit` の適用)。

    ``M = procrustes_fit(source, target, scaling, reflection)`` を求め、
    ``source @ M[:3, :3].T + M[:3, 3]`` を返す。変換は重心合わせ + SVD による回転
    (+ 任意でスケール)の相似変換で、**i 番目どうしが対応している**ことが前提。
    対応の無い点群を渡しても例外は出ず、意味の無い配置が返る(その場合は
    ICP 系の登録を使う)。

    - ``source``, ``target``: ``(N, 3)``、同じ ``N``、有限。``N = 1`` でも通る(並進のみ)。
    - ``scaling=True``: 大きさの違いも吸収する。``False`` なら剛体変換。
      ``source`` が全点同一(広がり 0)のときスケールは 1 のまま。
    - ``reflection=False``(既定): ``det(R) = +1`` を強制。``True`` にすると鏡像も
      許す ―― 左右非対称性を測る用途では消えてしまうので通常は既定のまま。
    - 返り値: ``(N, 3)`` float64。残差を数値で欲しいなら ``procrustes_distance``、
      変換行列そのものは ``procrustes_fit``。
    - 失敗: ``ValueError``(形が ``(N, 3)`` でない、``N`` 不一致、非有限)。

    多数の形を同時に揃えるなら ``generalized_procrustes``。
    """
    a = _as_shape(source, "source")
    M = procrustes_fit(a, target, scaling=scaling, reflection=reflection)
    return a @ M[:3, :3].T + M[:3, 3]


def procrustes_distance(source, target, scaling: bool = True,
                        reflection: bool = False, normalize: bool = True):
    """Procrustes 距離 = 重ねたあとの点ごと RMS。→ float。

    ``normalize=True``(既定)は *target* の重心距離 RMS で割った**無次元**の値。
    形どうしを大きさに依らず比べるならこちら。生の距離が要るなら False。
    """
    a = _as_shape(source, "source")
    b = _as_shape(target, "target")
    al = procrustes_align(a, b, scaling=scaling, reflection=reflection)
    rms = float(np.sqrt(np.mean(np.sum((al - b) ** 2, axis=1))))
    if not normalize:
        return rms
    size = float(np.sqrt(np.mean(np.sum((b - b.mean(0)) ** 2, axis=1))))
    return rms / size if size > 0.0 else 0.0


def generalized_procrustes(shapes, max_iter: int = 100, tol: float = 1e-10,
                           scaling: bool = True, reflection: bool = False):
    """一般化 Procrustes(GPA)。全個体を共通の枠へ。→ ``(K, N, 3)``。

    手順は教科書どおり: 1 個体を仮の平均にして全員を合わせ、平均を取り直し、
    その平均を**最初の個体に合わせ直して**枠の漂流を止め、収束まで繰り返す。
    最後の一手が無いと平均が毎回ゆっくり回り、``tol`` に到達しない。

    収束の判定は平均形状の移動量(点ごと RMS)。反復数と収束の可否は
    :func:`shape_mean` ではなくこちらには返らない —— 群を返す関数なので、
    診断が要るときは前後で :func:`procrustes_distance` を測ること。
    """
    x = _as_family(shapes)
    k = x.shape[0]
    ref = x[0]
    cur = x.copy()
    prev_mean = None
    for _ in range(max(1, int(max_iter))):
        for i in range(k):
            cur[i] = procrustes_align(x[i], ref, scaling=scaling, reflection=reflection)
        mean = cur.mean(0)
        # 平均を最初の個体に合わせ直す(枠が漂わないように)
        mean = procrustes_align(mean, x[0], scaling=scaling, reflection=reflection)
        if prev_mean is not None:
            move = float(np.sqrt(np.mean(np.sum((mean - prev_mean) ** 2, axis=1))))
            if move <= float(tol):
                ref = mean
                break
        prev_mean = mean
        ref = mean
    for i in range(k):
        cur[i] = procrustes_align(x[i], ref, scaling=scaling, reflection=reflection)
    return cur


def shape_mean(shapes, max_iter: int = 100, tol: float = 1e-10,
               scaling: bool = True, reflection: bool = False):
    """GPA で揃えたあとの平均形状。→ ``(N, 3)``。

    ★ **生の平均(``shapes.mean(0)``)と混同しないこと**。位置と向きを揃えずに
    平均すると、個体がばらばらに置かれているぶんだけ形が縮む。合わせてから
    平均するのが「平均形状」。
    """
    return generalized_procrustes(shapes, max_iter=max_iter, tol=tol,
                                  scaling=scaling, reflection=reflection).mean(0)


# --------------------------------------------------------------------------- #
# 3. 統計形状モデル                                                            #
# --------------------------------------------------------------------------- #
def shape_pca(shapes, n_components: int = 0, align: bool = True):
    """形態 PCA(統計形状モデル)。→ dict(``shapemodel``)。

    返す辞書: ``mean`` ``(N,3)`` / ``components`` ``(k, N*3)`` / ``variance``
    ``(k,)`` / ``n_points`` / ``total_variance`` / ``aligned`` ``(K,N,3)``。

    ``n_components=0``(既定)は ``min(K-1, N*3)`` 本すべて。
    ``align=True`` なら先に :func:`generalized_procrustes` を掛ける
    (揃えずに PCA を取ると、第 1 主成分が「位置の違い」になって形の話が消える)。

    ★ **分散は標本分散(``K-1`` で割る)**。K が小さいと固有値は系統的に大きく
    出る。個体数が二桁に届かないうちは、固有値そのものより**比**を見ること。

    ★★ **``align=True`` は「大きさの違い」も消すので、大きさに近いモードの分散を
    食う。** :func:`shape_synth_family` は第 1 モードを「長軸の伸び縮み」、第 2 を
    「曲げ」にしてあり、重みの比は 0.30 : 0.12 なので**分散比の真値は 6.25**。
    実測(K=40、N=80、seed=7):

    ==========================  ==========  ======================
    前処理                      分散比      寄与率(第 1 / 第 2)
    ==========================  ==========  ======================
    ``align=False``                  6.981        0.8747 / 0.1253
    GPA(``scaling=False``)          6.981        0.8747 / 0.1253
    ``align=True``(既定)            2.565        0.7188 / 0.2803
    ==========================  ==========  ======================

    伸びは一様拡大とよく似ているので、Procrustes のスケール除去がその半分以上を
    持っていく。**間違いではなく定義の帰結** —— 「大きさを形質に数えるか」を
    先に決めていないと、同じデータから違う主成分が出る。成長や体格差を形の話に
    含めたいなら ``align=False``(または ``generalized_procrustes(scaling=False)``
    を通してから ``align=False``)にすること。
    """
    x = _as_family(shapes)
    if align:
        x = generalized_procrustes(x)
    k, n, _ = x.shape
    mean = x.mean(0)
    flat = (x - mean).reshape(k, -1)
    u, s, vt = np.linalg.svd(flat, full_matrices=False)
    var = (s ** 2) / max(1, k - 1)
    keep = int(n_components) if int(n_components) > 0 else min(k - 1, n * 3)
    keep = max(1, min(keep, vt.shape[0]))
    return {"mean": mean, "components": vt[:keep].copy(), "variance": var[:keep].copy(),
            "n_points": int(n), "total_variance": float(var.sum()),
            "aligned": x}


def _as_model(model):
    if not isinstance(model, dict) or not all(k in model for k in MODEL_KEYS):
        raise ValueError("model must be a dict from shape_pca (keys %s)"
                         % (", ".join(MODEL_KEYS),))
    return model


def shape_project(model, shape, align: bool = True):
    """形をモデルの座標(主成分スコア)へ。→ ``(k,)``。

    ``align=True`` なら先に平均形状へ Procrustes で合わせる。合わせずに投影すると
    位置と向きの違いがスコアに漏れ、**同じ形なのに別の個体に見える**。

    式: ``scores = components @ (shape - mean).ravel()``(``components`` は
    ``(k, N*3)`` の正規直交行、``mean`` は ``(N, 3)``)。``align=True`` のときは
    ``procrustes_align(shape, mean)``(スケール込み・鏡像なし)を先に掛ける。

    - ``model``: ``shape_pca`` の返り値(``mean`` / ``components`` / ``variance`` /
      ``n_points`` を持つ dict)。欠けていれば ``ValueError``。
    - ``shape``: ``(N, 3)``、``N == model["n_points"]``、有限。点の並びは学習に使った
      ランドマークと同じ順であること(対応が違っても例外は出ない)。
    - ``align``: 既定 True。``shape_pca(align=False)`` で作ったモデル(大きさを形質に
      含める)に投影するときは、ここも ``False`` にしないとスケールが消える。
    - 返り値: ``(k,)`` float64。各成分の単位は座標と同じ。``sqrt(variance)`` で割れば
      標準偏差単位(何 σ 外れているか)になる。
    - 失敗: ``ValueError``(モデルの形式、点数の不一致、非有限)。

    逆写像は ``shape_reconstruct``、外れ具合の 1 数値は ``shape_mahalanobis``。
    """
    m = _as_model(model)
    p = _as_shape(shape)
    if p.shape[0] != m["n_points"]:
        raise ValueError("shape has %d points but the model has %d"
                         % (p.shape[0], m["n_points"]))
    if align:
        p = procrustes_align(p, m["mean"])
    return m["components"] @ (p - m["mean"]).reshape(-1)


def shape_reconstruct(model, scores):
    """スコアから形を戻す。→ ``(N, 3)``。

    与えたスコアが本数より少なければ残りは 0(= 平均のまま)として扱う。
    多ければ ``ValueError`` —— 黙って切り捨てると「入れたはずのモードが効かない」
    という追いにくい形になる。
    """
    m = _as_model(model)
    z = np.atleast_1d(np.asarray(scores, dtype=np.float64)).ravel()
    comp = m["components"]
    if z.size > comp.shape[0]:
        raise ValueError("got %d scores but the model has %d components"
                         % (z.size, comp.shape[0]))
    full = np.zeros(comp.shape[0])
    full[:z.size] = z
    return m["mean"] + (full @ comp).reshape(m["n_points"], 3)


def shape_mahalanobis(model, shape, align: bool = True, cumulative: float = 0.99,
                      n_modes: int = 0):
    """モデルから見てその形がどれだけ**異常**か。→ float。

    ``sqrt(sum(score_i^2 / variance_i))`` を**先頭の何本かに限って**足す。

    ★ **全成分を足してはいけない。** K 個体の群から出る主成分は K-1 本だが、
    後ろのほうは分散が数値的なゼロまで落ちる。実測(K=12、N=80、真のモードは
    2 本)の分散: ``3.2e-02, 5.6e-03, 4.0e-05, 6.7e-13, 9.7e-14, 9.9e-17, …,
    1.0e-31``。この裾で割ると値が意味を失う:

    ==========  ===========  ==================
    使う本数    群内の個体   0.5 の膨らみを注入
    ==========  ===========  ==================
    1                 0.428               1.821
    2                 0.885               2.617
    3                 1.035              18.134
    5                 1.373        1393035.060
    11(全部)      46613.636       9.3e+13
    ==========  ===========  ==================

    5 本で群内の個体が 1.37 なのに外れが 100 万、11 本では**群内ですら 46614**。
    「異常度」ではなく「数値ゼロで割った回数」を測っている。

    そこで既定は**累積寄与率 ``cumulative``(0.99)までの成分だけ**を使う。
    上の群では 2 本(0.99895)が選ばれ、群内 0.885 / 外れ 2.617 と素直に並ぶ。
    ``n_modes`` を正の数で与えればその本数に固定する(比較のため本数を揃えたい
    ときに使う)。**どちらを使ったかで値が変わる**ので、報告するときは本数も一緒に。
    """
    m = _as_model(model)
    v = np.asarray(m["variance"], dtype=np.float64)
    if v.size == 0:
        return 0.0
    if int(n_modes) > 0:
        keep = max(1, min(int(n_modes), v.size))
    else:
        total = float(v.sum())
        if total <= 0.0:
            return 0.0
        frac = np.cumsum(v) / total
        keep = int(np.searchsorted(frac, float(cumulative)) + 1)
        keep = max(1, min(keep, v.size))
    z = shape_project(m, shape, align=align)[:keep]
    vv = v[:keep]
    good = vv > 0.0
    if not np.any(good):
        return 0.0
    return float(np.sqrt(np.sum(z[good] ** 2 / vv[good])))


def shape_explained_variance(model):
    """各主成分の寄与率(合計 1)。→ ``(k,)``。

    式: ``variance / total_variance``。分母は ``model["total_variance"]``(``shape_pca``
    が**全**特異値から計算した総分散)で、無ければ ``variance.sum()``。

    - ``model``: ``shape_pca`` の返り値。必須キーが無ければ ``ValueError``。
    - 返り値: ``(k,)`` float64、各要素は ``[0, 1]``。``shape_pca(n_components=0)``
      (全成分)なら合計は 1。**``n_components`` で打ち切ったモデルでは合計が 1 未満**
      になる(切り捨てた成分の分だけ足りない)―― 「上位 k 本でどれだけ説明できるか」
      を読むにはむしろその方が正しい。
    - 総分散が 0(全個体が同じ形)なら全要素 0 を返す(0 除算にしない)。

    ``shape_pca`` の分散は標本分散(``K-1`` で割る)なので、個体数が少ないと
    固有値の絶対値は膨らむが、比であるこの量は影響を受けにくい。累積和
    (``cumsum``)で「99 % に何本要るか」を決め、``shape_mahalanobis`` の ``cumulative``
    や ``shape_synthesize`` の ``n_modes`` に渡す。
    """
    m = _as_model(model)
    v = np.asarray(m["variance"], dtype=np.float64)
    total = float(m.get("total_variance") or v.sum())
    return v / total if total > 0.0 else np.zeros_like(v)


def shape_synthesize(model, sigmas=None, n_modes: int = 3, seed: int = 0):
    """モデルから**もっともらしい新しい形**を 1 つ作る。→ ``(N, 3)``。

    ``sigmas`` を与えればその標準偏差倍のスコア、省けば先頭 ``n_modes`` 本を
    正規乱数で引く。3 標準偏差を超える形は群の中に 1 つも無かった形なので、
    既定では引かない(``sigmas`` で明示すれば作れる)。
    """
    m = _as_model(model)
    v = np.asarray(m["variance"], dtype=np.float64)
    if sigmas is None:
        rng = np.random.default_rng(int(seed))
        k = max(1, min(int(n_modes), v.size))
        z = np.clip(rng.standard_normal(k), -3.0, 3.0) * np.sqrt(v[:k])
    else:
        z = np.atleast_1d(np.asarray(sigmas, dtype=np.float64)).ravel()
        z = z * np.sqrt(v[:z.size])
    return shape_reconstruct(m, z)


# --------------------------------------------------------------------------- #
# 4. 左右対称性(ランドマーク)                                                #
# --------------------------------------------------------------------------- #
def mirror_plane_from_pairs(landmarks, pairs=None, midline=None):
    """左右の対応ランドマークから正中面を出す。→ ``(2, 3)``(1 行目 = 点、2 行目 = 法線)。

    左右の対 ``(i, j)`` の**中点**は、どれも正中面の上に乗る。だからその中点集合に
    平面を当てればよい —— 変形の量に依らず面が決まるのが要点で、残差を最小に
    する面(:func:`symmetry3d.detect_reflection_symmetry`)とは別物である。

    ★ 2026-09-06 の実測: 6.4 mm の片側変形を入れると、**残差最適面は真の正中面
    から 2.92 mm / 1.72 度ずれ、非対称量の 46 % を消した**(利得 0.54)。この
    ランドマーク面なら利得 1.03。**見つけるなら残差最適面、量を言うならこちら**。

    *midline* は正中線上にある(対にならない)ランドマークの添字。与えると
    中点集合に足して面の当てはめを安定させる。

    ``pairs=None`` は**前半と後半を対にする**規約(``i`` と ``i + N//2``)。
    左のランドマークを全部並べてから右を同じ順で並べる、という保存形式が
    形態計測では一般的なので、それに合わせてある。**点数が奇数なら拒否する**
    —— 半分に割れない並びを黙って切り詰めると、対が 1 つずつずれて全部の
    符号が入れ替わる。
    """
    p = _as_shape(landmarks, "landmarks")
    if pairs is None:
        n = p.shape[0]
        if n % 2 != 0 or n < 4:
            raise ValueError("pairs=None は前半/後半の規約なので、ランドマークは "
                             "偶数個(4 以上)必要(got %d)" % n)
        pairs = np.column_stack([np.arange(n // 2), np.arange(n // 2, n)])
    idx = np.asarray(pairs, dtype=np.int64)
    if idx.ndim != 2 or idx.shape[1] != 2 or idx.shape[0] < 2:
        raise ValueError("pairs must be (M, 2) with M >= 2, got %r" % (idx.shape,))
    if idx.min() < 0 or idx.max() >= p.shape[0]:
        raise ValueError("pairs index out of range for %d landmarks" % p.shape[0])
    mids = 0.5 * (p[idx[:, 0]] + p[idx[:, 1]])
    if midline is not None:
        mi = np.asarray(midline, dtype=np.int64).ravel()
        if mi.size:
            if mi.min() < 0 or mi.max() >= p.shape[0]:
                raise ValueError("midline index out of range")
            mids = np.vstack([mids, p[mi]])
    if mids.shape[0] < 3:
        raise ValueError("need >= 3 midline points to fit a plane (got %d)"
                         % mids.shape[0])
    c = mids.mean(0)
    _, _, vt = np.linalg.svd(mids - c, full_matrices=False)
    normal = vt[-1]
    # 法線の向きを「左の対 -> 右の対」に揃える(符号が任意だと符号つき偏差が裏返る)
    lr = (p[idx[:, 1]] - p[idx[:, 0]]).mean(0)
    if float(normal @ lr) < 0.0:
        normal = -normal
    return np.vstack([c, normal / max(float(np.linalg.norm(normal)), 1e-12)])


def landmark_asymmetry(landmarks, pairs=None, plane=None):
    """左右の対ごとの**符号つき**非対称量。→ ``(M,)``。

    各対について、片方を面で鏡映してもう片方と比べ、面の法線方向の差を返す。
    符号は「右が外側なら正」(:func:`mirror_plane_from_pairs` が法線をその向きに
    揃えている)。**絶対値にまとめない** —— 左右どちらが張り出しているかは
    臨床でも検査でも意味が違う。

    ``pairs=None`` / ``plane=None`` はどちらも :func:`mirror_plane_from_pairs`
    と同じ既定(前半/後半の対、その対から出した正中面)。**面を省くと、面自体が
    同じ対から決まる**ので「面を決めた材料で面からのずれを測る」ことになる ——
    それでも左右差は測れる(中点は定義上どちらの側にも寄らない)が、
    別の情報源から面が決まるなら渡したほうが強い。
    """
    p = _as_shape(landmarks, "landmarks")
    if pairs is None:
        n = p.shape[0]
        if n % 2 != 0 or n < 4:
            raise ValueError("pairs=None は前半/後半の規約なので、ランドマークは "
                             "偶数個(4 以上)必要(got %d)" % n)
        pairs = np.column_stack([np.arange(n // 2), np.arange(n // 2, n)])
    idx = np.asarray(pairs, dtype=np.int64)
    if idx.ndim != 2 or idx.shape[1] != 2:
        raise ValueError("pairs must be (M, 2), got %r" % (idx.shape,))
    if plane is None:
        plane = mirror_plane_from_pairs(p, idx)
    pl = np.asarray(plane, dtype=np.float64)
    if pl.shape != (2, 3):
        raise ValueError("plane must be (2, 3): row 0 point, row 1 normal")
    c, n = pl[0], pl[1] / max(float(np.linalg.norm(pl[1])), 1e-12)
    left = p[idx[:, 0]] - c
    right = p[idx[:, 1]] - c
    mirrored = left - 2.0 * (left @ n)[:, None] * n         # 左を鏡映して右側へ
    return (right - mirrored) @ n


# --------------------------------------------------------------------------- #
# 5. 面までの符号つき距離                                                      #
# --------------------------------------------------------------------------- #
def signed_surface_distance(query, surface, surface_normals=None, k: int = 1):
    """問い合わせ点から面までの**符号つき**距離。→ ``(N,)``。

    符号は面の法線から決める(外側が正)。1-D の輪郭には
    ``profileops.profile_deviation`` があるのに 3-D に相当が無かった、というのが
    2026-09-06 に PoC が出した穴。

    法線を省くと :func:`normals_orient.estimate_oriented_normals` で推定する
    —— **向き付き**でなければ符号が点ごとにばらつく(素の PCA 法線は符号が任意で、
    回転すると 4 割が裏返る。``pointcloud.fpfh`` が踏んだのと同じ穴)。

    ``k`` は符号を決めるときに使う最近傍の数。1 だと最近傍 1 点の法線に賭ける
    ことになり、雑音のある面では符号が飛ぶ。2 以上にすると距離で重みを付けた
    平均の向きで決める(距離そのものは最近傍のまま)。
    """
    from scipy.spatial import cKDTree

    q = _as_shape(query, "query")
    s = _as_shape(surface, "surface")
    if surface_normals is None:
        from normals_orient import estimate_oriented_normals
        nrm = estimate_oriented_normals(s, k=min(20, max(3, s.shape[0] - 1)))
    else:
        nrm = _as_shape(surface_normals, "surface_normals")
        if nrm.shape[0] != s.shape[0]:
            raise ValueError("surface_normals has %d rows but surface has %d"
                             % (nrm.shape[0], s.shape[0]))
    kk = max(1, min(int(k), s.shape[0]))
    dist, idx = cKDTree(s).query(q, k=kk)
    if kk == 1:
        dist = dist[:, None]
        idx = idx[:, None]
    w = 1.0 / np.maximum(dist, 1e-12)
    n_avg = np.einsum("qk,qkc->qc", w, nrm[idx]) / w.sum(1)[:, None]
    n_avg /= np.maximum(np.linalg.norm(n_avg, axis=1, keepdims=True), 1e-12)
    sign = np.sign(np.einsum("qc,qc->q", q - s[idx[:, 0]], n_avg))
    sign[sign == 0.0] = 1.0
    return sign * dist[:, 0]
