"""HALCON coverage 拡充 tier(``hx_`` prefix)— 未カバーの実 HALCON operator を genuine に実装.

各 op は `data/halcon_operators.json` に実在し **これまで未カバー**だった operator の本物の機能を
自作 numpy で実装する(名前 provenance は halcon_coverage.py が dangling 検出で検証)。契約は
既存 registry と同じ ``fn(v, a, b)``(v=[0,1] の 2D 画像 or 二値 region、a/b=[0,1] の進化ノブ)。

追加(実 HALCON 名 → 機能):
  Regions 生成: gen_circle / gen_ellipse / gen_rectangle2 / gen_checker_region / gen_grid_region
  Filters:      convol_gabor(Gabor フィルタ)
  Image:        fit_surface_first_order / fit_surface_second_order(gray 値の多項式面近似=照明推定)
                cooc_feature_image(GLCM 共起行列テクスチャ特徴)/ full_domain(定義域を全面に)
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _grid(shape):
    h, w = shape
    Y, X = np.mgrid[0:h, 0:w].astype(np.float64)
    return h, w, Y, X


def _norm01(v):
    v = np.asarray(v, dtype=np.float64)
    lo, hi = float(v.min()), float(v.max())
    return (v - lo) / (hi - lo) if hi > lo else np.zeros_like(v)


# ── Regions 生成(fn(v,a,b) -> 二値 region。v.shape を画布に、a/b を幾何パラメータに)──── #
def _gen_circle(v, a, b):
    """円形の region を生成する。HALCON の ``gen_circle``(円を生成する)に相当。

    画布中心 ``(h/2, w/2)`` を中心とする円板を描き、内部を 1・外部を 0 として
    返す。``a`` が半径を ``min(h, w)`` の 10%〜50% の範囲で振る。``b`` は未使用。
    """
    h, w, Y, X = _grid(v.shape)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    r = (0.1 + 0.4 * a) * min(h, w)
    return ((Y - cy) ** 2 + (X - cx) ** 2 <= r * r).astype(np.float64)


def _gen_ellipse(v, a, b):
    """軸並行の楕円 region を生成する。HALCON の ``gen_ellipse``(楕円を生成する)
    に相当(向き固定の近似 —— 本家は回転角パラメータも取る)。

    ``a`` が横半径(画像幅の 10%〜50%)、``b`` が縦半径(画像高さの 10%〜50%)を
    振る。
    """
    h, w, Y, X = _grid(v.shape)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    ra = (0.1 + 0.4 * a) * w / 2 + 1e-6
    rb = (0.1 + 0.4 * b) * h / 2 + 1e-6
    return (((X - cx) / ra) ** 2 + ((Y - cy) / rb) ** 2 <= 1.0).astype(np.float64)


def _gen_rectangle2(v, a, b):
    """任意角度の矩形 region を生成する。HALCON の ``gen_rectangle2``
    (任意方向の矩形を生成する)に相当。

    中心を画布中心に固定し、``b`` が回転角(``b*pi`` ラジアン、0〜180°)、``a``
    が半幅(画像幅の 10%〜50%)と半高さ(連動して画像高さの 6%〜30%)を振る。
    """
    h, w, Y, X = _grid(v.shape)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    th = b * np.pi
    dx, dy = X - cx, Y - cy
    xr = np.cos(th) * dx + np.sin(th) * dy
    yr = -np.sin(th) * dx + np.cos(th) * dy
    hw = (0.1 + 0.4 * a) * w / 2
    hh = (0.06 + 0.24 * a) * h / 2
    return ((np.abs(xr) <= hw) & (np.abs(yr) <= hh)).astype(np.float64)


def _gen_checker_region(v, a, b):
    """市松模様(チェッカーボード)region を生成する。HALCON の
    ``gen_checker_region``(チェッカー領域を生成する)に相当。

    セルサイズを ``a`` で ``min(h, w)`` の 5%〜25% の範囲に振り、
    ``(row//cell + col//cell)`` が偶数のセルを前景(1)とする。``b`` は未使用。
    """
    h, w, Y, X = _grid(v.shape)
    cell = max(2, int((0.05 + 0.2 * a) * min(h, w)))
    return (((X.astype(int) // cell) + (Y.astype(int) // cell)) % 2 == 0).astype(np.float64)


def _gen_grid_region(v, a, b):
    """格子線 region を生成する。HALCON の ``gen_grid_region``(直線または画素から
    region を生成する)の格子パターンに相当する簡略版。

    ``a`` が格子間隔(``min(h, w)`` の 5%〜25%)を振り、行・列インデックスが
    間隔の倍数の画素を前景とする。``b`` は未使用。
    """
    h, w, Y, X = _grid(v.shape)
    step = max(2, int((0.05 + 0.2 * a) * min(h, w)))
    return ((X.astype(int) % step == 0) | (Y.astype(int) % step == 0)).astype(np.float64)


# ── Filters: Gabor ─────────────────────────────────────────────────────────── #
def _convol_gabor(v, a, b):
    """Gabor フィルタ(方位 theta=a*pi、周波数 freq=0.08+0.35b)。応答の大きさを返す。

    向きの規約は core の ``gabor`` と同じ: ``a=0`` (θ=0) が **縦縞**、``a=0.5``
    (θ=90°) が横縞に最も応答する。

    ★正規化(2026-09-02 の修正): **カーネルの L1 ノルムで割る固定スケール**。
    以前は ``_norm01``(その画像の min–max を [0,1] へ引き伸ばす)だったため、
    向きによる応答の大小が潰れるどころか **順序が逆転していた** —— 実測
    (96×96 の横縞、b=0.5): 横縞検出器 (a=0.5) の平均 0.34663 に対し、ほとんど
    反応しないはずの縦縞検出器 (a=0) が 0.58434 と **高く**出ていた(弱い応答ほど
    引き伸ばし率が大きいため)。``|v| <= 1`` なら ``|v * g| <= sum|g|`` なので
    L1 で割れば [0,1] を保ったまま向き・画像を跨いで比較できる。
    """
    theta = a * np.pi
    freq = 0.08 + 0.35 * b
    sigma = 2.2
    r = 4
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1].astype(np.float64)
    xr = xx * np.cos(theta) + yy * np.sin(theta)
    yr = -xx * np.sin(theta) + yy * np.cos(theta)
    envelope = np.exp(-(xr ** 2 + yr ** 2) / (2 * sigma ** 2))
    kernel = envelope * np.cos(2 * np.pi * freq * xr)
    kernel -= kernel.mean()                              # DC 除去(平坦部で 0)
    l1 = float(np.abs(kernel).sum())
    resp = np.abs(ndimage.convolve(np.clip(v, 0, 1), kernel, mode="reflect"))
    return np.clip(resp / l1, 0, 1) if l1 > 1e-12 else np.zeros_like(resp)


# ── Image: gray 値の多項式面近似(照明/背景推定)─────────────────────────────── #
def _fit_surface(v, order):
    h, w, Y, X = _grid(v.shape)
    xn = (X / max(w - 1, 1)) * 2 - 1                     # [-1,1] 正規化で条件数改善
    yn = (Y / max(h - 1, 1)) * 2 - 1
    cols = [np.ones_like(xn), xn, yn]
    if order >= 2:
        cols += [xn * xn, yn * yn, xn * yn]
    A = np.stack([c.ravel() for c in cols], axis=1)
    coef, *_ = np.linalg.lstsq(A, v.ravel(), rcond=None)
    return _norm01((A @ coef).reshape(v.shape))


def _fit_surface_first_order(v, a, b):
    """gray 値を 1 次多項式面(平面)で最小二乗近似する。HALCON の
    ``fit_surface_first_order``(gray 値モーメントを計算し 1 次曲面で近似する)
    に相当。

    座標を [-1, 1] に正規化してから ``[1, x, y]`` を基底に最小二乗回帰し、
    近似面を min-max で [0, 1] に正規化して返す(照明ムラ推定に使う)。
    ``a``, ``b`` は未使用。
    """
    return _fit_surface(v, 1)


def _fit_surface_second_order(v, a, b):
    """gray 値を 2 次多項式面で最小二乗近似する。HALCON の
    ``fit_surface_second_order``(gray 値モーメントを計算し 2 次曲面で近似する)
    に相当。

    基底を ``[1, x, y, x^2, y^2, xy]`` に拡張したこと以外は ``hx_fit_surface1``
    と同じ(座標 [-1,1] 正規化 -> 最小二乗 -> [0,1] 正規化)。曲がった照明ムラや
    緩い凹凸の背景推定に使う。``a``, ``b`` は未使用。
    """
    return _fit_surface(v, 2)


# ── Image: GLCM 共起行列テクスチャ特徴(image -> feature scalar)──────────────── #
def _cooc_feature_image(v, a, b):
    """量子化して距離 d の水平共起行列を作り、Haralick contrast を返す(a=距離, b は角度選択)。

    入力 ``v``([0,1] 画像)を ``int(v*8)`` で 8 階調に量子化し(clip で 0〜7)、距離 ``d`` だけ離れた画素対の
    出現回数を 8×8 の共起行列にして転置を足し(対称化)、総和で割って確率にする。返すのは Haralick の
    contrast ``sum p(i,j)*(i-j)^2`` を最大値 ``(8-1)^2 = 49`` で割った ``np.float64``(値域 [0,1])。

    - ``a`` → 距離 ``d = 1 + int(a*3)``(1〜4 画素)。
    - ``b`` → 方向。``b < 0.5`` で水平(同じ行で ``d`` 列右)、``b >= 0.5`` で垂直(同じ列で ``d`` 行下)。斜め方向は無い。
    - 画像の幅(または高さ)が ``d`` 以下で画素対が 1 つも作れないと総和 0 とみなして 0.0 を返す(例外は出さない)。

    値が大きいほど隣接画素の階調差が大きい(粗い/コントラストの高いテクスチャ)。8 階調のため微妙な濃淡差は同じ
    階調に潰れる。16 階調の ``skimage`` 実装 ``cooc_feature_matrix`` とは階調数・正規化が異なり数値は一致しない。
    前段に ``hx_gabor`` や ``mean_image`` など画像 op、後段は feature として比較・しきい値に使う。
    """
    levels = 8
    q = np.clip((v * levels).astype(int), 0, levels - 1)
    d = 1 + int(a * 3)
    if b < 0.5:                                          # 水平 (0°)
        i, j = q[:, :-d], q[:, d:]
    else:                                                # 垂直 (90°)
        i, j = q[:-d, :], q[d:, :]
    glcm = np.zeros((levels, levels), dtype=np.float64)
    np.add.at(glcm, (i.ravel(), j.ravel()), 1.0)
    glcm += glcm.T
    total = glcm.sum()
    if total <= 0:
        return np.float64(0.0)
    glcm /= total
    li = np.arange(levels)
    contrast = float((glcm * (li[:, None] - li[None, :]) ** 2).sum())
    return np.float64(contrast / (levels - 1) ** 2)     # [0,1] 正規化


# ── Image: 定義域を全面へ(image -> full region)────────────────────────────── #
def _full_domain(v, a, b):
    """画像の定義域を全面に広げる。HALCON の ``full_domain``(画像の定義域を
    最大に拡張する)に相当。

    入力と同じ形状の全 1 の region(=画像全面)を返すだけの op。ROI を絞る他の
    op と対で使い、定義域をリセットするために使う。``a``, ``b`` は未使用。
    """
    return np.ones_like(v, dtype=np.float64)


# ── 第 2 バッチ ─────────────────────────────────────────────────────────────── #
def _disk(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = (xx * xx + yy * yy <= r * r).astype(np.float64)
    return d / d.sum()


def _mean_image_shape(v, a, b):
    """任意マスク(円 disk)による平均平滑化。半径 r を a で可変(矩形 mean と別 op)。

    半径 ``r`` の円板(``xx^2+yy^2 <= r^2`` を満たす画素を 1、総和で割って正規化)を ``ndimage.convolve(mode="reflect")``
    で畳み込む。出力は入力と同形の float 配列で、値域は入力の範囲を出ない(重みの和が 1)。

    - ``a`` → 半径 ``r = 1 + int(a*4)``(1〜5 画素、5 になるのは a=1 のときだけ)。カーネルは ``(2r+1)`` 角の中の円板。
    - ``b`` は未使用。

    矩形窓の ``mean_image`` と違い方向による重みの偏りが少なく、円板半径以下の構造を等方的にぼかす。境界は鏡映で
    延長するので端の暗落ちは起きない。入力検証は無く、NaN が含まれるとそのまま伝播する。
    """
    r = 1 + int(a * 4)
    return ndimage.convolve(v, _disk(r), mode="reflect")


def _close_edges(v, a, b):
    """エッジ振幅画像の隙間を閉じる: しきい値 a で二値化 → morphological closing(半径 b)。

    ``v > a`` で二値化した後、``scipy.ndimage.binary_closing`` を 3×3 全結合(8 近傍)構造要素の ``it`` 回反復
    = ``(2*it+1)`` 角の正方形で 1 回クロージング(膨張→収縮)し、0/1 の float 画像で返す。

    - ``a`` → 二値化しきい値(エッジ振幅画像を想定。a=0 では 0 より大きい画素がすべて前景)。
    - ``b`` → 構造要素の反復回数 ``it = 1 + int(b*3)``(1〜4、正方形の辺は 3〜9 画素)。閉じられる隙間はおおむね
    ``2*it`` 画素以下。

    注意: ``binary_closing`` は画像外を 0 として収縮するため、画像端から ``it`` 画素の帯は必ず 0 になる
    (全面 1 の 20×20 に it=1 を掛けると残るのは 18×18)。端に接するエッジを扱うときは前に余白を付けるか、結果を
    膨張し直す。入力は image(エッジ振幅)で出力も image sort だが中身は二値。``hx_nonmax_dir`` や ``sobel_amp`` の
    後に置き、つながったエッジは ``hx_region_to_label`` や ``hx_detect_edge_segments`` へ渡す。
    """
    from scipy.ndimage import binary_closing, generate_binary_structure, iterate_structure
    edges = v > a
    it = 1 + int(b * 3)
    st = iterate_structure(generate_binary_structure(2, 2), it)
    return binary_closing(edges, structure=st).astype(np.float64)


def _close_edges_length(v, a, b):
    """close_edges に加え、長さ(画素数)が閾値未満の短いエッジ断片を除去する。

    ``v > a`` で二値化 → 3×3(8 近傍)構造要素で 1 回 ``binary_closing`` → ``ndimage.label``(既定の 4 近傍連結)で
    連結成分にし、画素数が ``min_len`` 未満の成分を落として 0/1 の float 画像で返す。

    - ``a`` → 二値化しきい値。
    - ``b`` → 残す最小画素数 ``min_len = 2 + int(b*20)``(2〜22)。
    - 成分が 1 つも無ければクロージング結果をそのまま返す。

    注意: クロージングの構造要素は固定 3×3 で、``hx_close_edges`` のような幅の調整は無い。ラベリングが 4 近傍のため
    斜めにつながる 1 画素幅の線は別成分に分かれ、「長さ」が短く数えられて消えやすい。``binary_closing`` は画像外を
    0 と扱うので端 1 画素の帯は常に 0 になる。「長さ」は成分の画素数であり幾何学的な線長ではない(塊も長いと数える)。
    """
    from scipy.ndimage import binary_closing, generate_binary_structure, label
    edges = binary_closing(v > a, structure=generate_binary_structure(2, 2))
    lab, n = label(edges)
    if n == 0:
        return edges.astype(np.float64)
    sizes = np.bincount(lab.ravel())
    min_len = 2 + int(b * 20)
    keep = np.isin(lab, np.nonzero(sizes >= min_len)[0][1:])   # 0=背景を除く
    return keep.astype(np.float64)


def _expand_region(v, a, b):
    """領域間の隙間を埋める(region -> region): 二値領域を dilation で膨張して連結を促す。

    ``v > 0.5`` を region とみなし、4 近傍の十字構造要素を ``it`` 回反復した菱形(マンハッタン距離 ``it`` 以内)で
    ``binary_dilation`` を 1 回掛け、0/1 の float 配列で返す。

    - ``a`` → 膨張半径 ``it = 1 + int(a*4)``(1〜5 画素)。互いの距離が ``2*it`` 画素以下の領域どうしがつながる。
    - ``b`` は未使用。

    隙間を埋めて連結を促す op で、領域は必ず太る(元の面積には戻らない)。元の大きさを保ちたいときは後段で
    ``hx_erosion1`` を同程度の半径で掛けるか、初めから ``hx_closing`` を使う。画像外は 0 扱い(膨張は端で止まる)。
    空の region は空のまま返る。
    """
    from scipy.ndimage import binary_dilation, generate_binary_structure, iterate_structure
    reg = v > 0.5
    it = 1 + int(a * 4)
    st = iterate_structure(generate_binary_structure(2, 1), it)
    return binary_dilation(reg, structure=st).astype(np.float64)


def _region_to_mean(v, a, b):
    """各連結領域をその平均 gray 値で塗る(image -> image)。閾値 a で前景/背景を分け label 化。

    ``v > a`` を前景とし ``ndimage.label``(4 近傍)で連結成分に分け、各成分の画素を ``ndimage.mean`` で求めた
    成分内の平均 gray 値で塗りつぶす。背景(``v <= a``)は背景画素全体の平均 1 値で塗る(背景が無ければ 0.0)。
    出力は入力と同形の float 画像で、値域は入力の範囲内(正規化しない)。

    - ``a`` → 前景/背景を分けるしきい値。a=0 なら 0 より大きい画素がすべて前景。
    - ``b`` は未使用。

    結果は成分ごとに一定値になるので、後段の ``threshold`` で「平均が明るい部品だけ」を選ぶような使い方ができる。
    4 近傍ラベルなので斜め接触する塊は別々の平均になる。入力の検証は無い。
    """
    from scipy.ndimage import label, mean as ndmean
    fg = v > a
    lab, n = label(fg)
    out = np.full_like(v, float(v[~fg].mean()) if (~fg).any() else 0.0)
    if n > 0:
        means = ndmean(v, labels=lab, index=np.arange(1, n + 1))
        out[fg] = np.asarray(means)[lab[fg] - 1]
    return out


# ── 第 3 バッチ: セグメンテーション/エッジ/周波数フィルタ生成 ─────────────────── #
def _nonmax_suppression_dir(v, a, b):
    """勾配方向に沿った非最大抑制(Canny の NMS 段)。エッジを 1 画素に細線化する。

    Sobel で ``gx``(列方向)・``gy``(行方向)を取り、振幅 ``hypot(gx, gy)`` と方向 ``arctan2(gy, gx) mod 180°`` を
    求める。方向を 45° 刻みの 4 区分に量子化し、各画素をその区分に対応する 2 つの隣接画素と比べて
    ``mag >= 両隣`` の画素だけ残す(それ以外は 0)。残った振幅を min-max で [0,1] に正規化し、``a*0.3`` 未満を 0 に落とす。

    - ``a`` → 弱エッジのしきい値 ``a*0.3``(正規化後の値に対して。a=0 でしきい値なし)。
    - ``b`` は未使用。

    注意点:
    - 隣接比較は ``np.roll`` なので画像端では反対側の画素と比較される(端 1 画素は信用しない)。
    - 比較が ``>=`` のため、同じ振幅が並ぶ理想的なステップエッジは 2 画素幅で残る(1 画素にはならない)。
    - 現状の実装では 45° と 135° の区分で比較する隣接画素の対が入れ替わっており、斜めのエッジは勾配方向でなく
    エッジに沿った方向で比較される。そのため水平・垂直エッジは細線化されるが、斜めエッジはほとんど細線化されない
    (ぼかした対角ステップエッジで 1400 画素前後がそのまま残る実測)。斜めエッジの細線化が要る場合は ``canny`` や
    ``skeleton`` を検討する。

    ``sobel_amp`` のような振幅画像ではなく元の gray 画像を渡す(内部で微分する)。後段は ``hx_close_edges`` /
    ``hx_detect_edge_segments`` / ``threshold``。
    """
    gx = ndimage.sobel(v, axis=1)
    gy = ndimage.sobel(v, axis=0)
    mag = np.hypot(gx, gy)
    ang = (np.rad2deg(np.arctan2(gy, gx)) % 180.0)
    q = (np.round(ang / 45.0).astype(int)) % 4
    shifts = {0: ((0, -1), (0, 1)), 1: ((-1, 1), (1, -1)),
              2: ((-1, 0), (1, 0)), 3: ((-1, -1), (1, 1))}
    out = np.zeros_like(mag)
    for qi, (s1, s2) in shifts.items():
        n1 = np.roll(np.roll(mag, s1[0], 0), s1[1], 1)
        n2 = np.roll(np.roll(mag, s2[0], 0), s2[1], 1)
        keep = (q == qi) & (mag >= n1) & (mag >= n2)
        out[keep] = mag[keep]
    out = _norm01(out)
    out[out < a * 0.3] = 0.0                              # 弱エッジを a で抑制
    return out


def _char_threshold(v, a, b):
    """暗い文字を明るい背景から抽出(region): thresh = mean - k*std(k は a)で下側を選ぶ。

    画像全体の平均 ``mean`` と標準偏差 ``std`` から ``thr = mean - k*std`` を計算し、``v < thr`` の画素を 1 とする
    0/1 の float region を返す。暗い文字が少数派で明るい背景が多数派、という前提の大域しきい値。

    - ``a`` → 係数 ``k = 0.2 + 1.8*a``(0.2〜2.0)。大きいほど厳しく(より暗い画素だけ)、小さいほど多く拾う。
    - ``b`` は未使用。

    濃淡が一様な画像では ``std = 0`` となり ``thr = mean`` で「平均未満」だけが残る。照明ムラがあると 1 本の
    しきい値では片側が欠けるので、前に ``hx_plane_deviation`` で背景を引くか、局所版の ``dyn_threshold`` /
    ``local_threshold`` を使う。明るい文字を取りたい場合は先に画像を反転する(この op は下側しか選ばない)。
    """
    k = 0.2 + 1.8 * a
    thr = float(v.mean()) - k * float(v.std())
    return (v < thr).astype(np.float64)


def _histo_to_thresh(v, a, b):
    """ヒストグラムの谷から閾値を決めて二値化(Otsu の分散基準でなく谷検出=別 op)。

    ``v`` の 64 bin ヒストグラム(範囲 [0,1])を σ=1.5 のガウスで平滑化し、最も高い bin ``p1`` と、``p1`` から 5 bin
    以上離れた中で次に高い bin ``p2`` を取り、その間で最小の bin(谷)の左端の値をしきい値 ``thr`` にして
    ``v > thr`` を 1 とする 0/1 の float region を返す。

    - ``a``, ``b`` は未使用(しきい値は完全に自動)。
    - ``p2`` が見つからない(5 bin 以上離れた bin が無い)ときは ``lo == hi`` となり谷を bin 32、つまり ``thr = 0.5``
    に固定する。

    注意: ``p2`` は「2 番目のモード」ではなく「p1 から 5 bin 以上離れた 2 番目に高い bin」なので、単峰の裾でも選ばれる。
    その場合の谷はピークと裾の間の最小値になり、意図と違う位置で切れる(単峰のガウス雑音画像で大半が前景になる
    実測あり)。双峰性がはっきりした画像向け。分散基準で決めたいときは ``otsu``、局所的なら ``dyn_threshold``。
    """
    hist, edges = np.histogram(v.ravel(), bins=64, range=(0.0, 1.0))
    hs = ndimage.gaussian_filter1d(hist.astype(float), 1.5)
    # 2 つの主ピーク間の最小値(谷)を閾値に
    peaks = np.argsort(hs)[::-1]
    p1 = peaks[0]
    p2 = next((p for p in peaks[1:] if abs(p - p1) > 4), p1)
    lo, hi = sorted((p1, p2))
    valley = lo + int(np.argmin(hs[lo:hi + 1])) if hi > lo else 32
    thr = edges[valley]
    return (v > thr).astype(np.float64)


def _freq_radius(shape):
    h, w = shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    return np.fft.fftshift(np.sqrt(fy ** 2 + fx ** 2))   # 中心=DC の正規化周波数半径


def _gen_lowpass(v, a, b):
    """理想ローパスフィルタ画像(周波数領域の中心円板マスク、遮断半径 a)。

    入力 ``v`` は形を決めるためだけに使い、``np.fft.fftfreq`` で各軸の正規化周波数(-0.5〜0.5)を作って
    ``fftshift`` した半径 ``r = sqrt(fy^2 + fx^2)``(中心=DC、四隅で約 0.707)に対し ``r <= cutoff`` を 1 とする
    0/1 の float 画像(周波数領域マスク)を返す。画像そのものにフィルタを掛けるのではない。

    - ``a`` → 遮断半径 ``cutoff = 0.05 + 0.45*a``(0.05〜0.5。a=1 で軸方向のナイキスト周波数まで通す)。
    - ``b`` は未使用。

    DC が中央に来る配置(``fftshift`` 済)なので、``fft_generic`` / ``fft_image`` のような「中心が低周波」の
    スペクトル画像と画素どうしで掛け合わせる用途に合う。自前で ``np.fft.fft2`` の結果に掛けるときは
    ``ifftshift`` で戻してから使う。兄弟 op に ``hx_gen_highpass``(補集合)/ ``hx_gen_bandpass`` /
    ``hx_gen_bandfilter``(円環)。
    """
    r = _freq_radius(v.shape)
    cutoff = 0.05 + 0.45 * a
    return (r <= cutoff).astype(np.float64)


def _gen_highpass(v, a, b):
    """理想ハイパスフィルタの周波数マスクを生成する。HALCON の ``gen_highpass``
    (理想ハイパスフィルタを生成する)に相当。

    DC を中心に fftshift した正規化周波数半径 ``r`` を計算し、``r > cutoff`` の
    画素を 1 とする(``cutoff = 0.05 + 0.45*a``)。兄弟 op ``hx_gen_lowpass`` /
    ``hx_gen_bandpass`` と半径の計算式を共有する。``b`` は未使用。返り値は
    フィルタそのもの(周波数領域のマスク画像)で、画像に畳み込む前段にあたる。
    """
    r = _freq_radius(v.shape)
    cutoff = 0.05 + 0.45 * a
    return (r > cutoff).astype(np.float64)


def _gen_bandpass(v, a, b):
    """理想バンドパス(周波数領域の円環マスク、内半径 a・帯域幅 b)。

    ``hx_gen_lowpass`` と同じ正規化周波数半径 ``r``(``fftshift`` 済、中心=DC)に対し ``r_lo <= r <= r_hi`` の
    円環を 1 とする 0/1 の float 画像(周波数領域マスク)を返す。入力 ``v`` は形状の取得にのみ使う。

    - ``a`` → 内半径 ``r_lo = 0.05 + 0.4*a``(0.05〜0.45)。
    - ``b`` → 帯域幅 ``r_hi - r_lo = 0.05 + 0.3*b``(0.05〜0.35)。外半径は ``r_lo + 幅`` で最大 0.8 だが、半径が
    約 0.707 を超える周波数は存在しないので、大きな a, b では円環の外側が画像外に出て実質ハイパスになる。

    ``hx_gen_bandfilter`` は「中心半径と半幅」で同じ円環を指定する別パラメータ化。``fft_generic`` などの中心=DC
    スペクトルとの画素積で使う。
    """
    r = _freq_radius(v.shape)
    r_lo = 0.05 + 0.4 * a
    r_hi = r_lo + 0.05 + 0.3 * b
    return ((r >= r_lo) & (r <= r_hi)).astype(np.float64)


# ── 第 4 バッチ: Morphology(任意 SE の region 形態)+ Regions 生成 + 周波数フィルタ ── #
def _disc_bool(r):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    return xx * xx + yy * yy <= r * r


def _se_radius(a):
    return 1 + int(a * 4)


def _erosion1(v, a, b):
    """円板構造要素で region を収縮(erosion)する。HALCON の ``erosion1``
    (region を収縮する)に相当。

    半径 ``r = 1 + int(a*4)`` の円板を構造要素として
    ``scipy.ndimage.binary_erosion`` を呼ぶ。``b`` は未使用。境界の外側画素を
    削り、細い突起やノイズ画素を消す。
    """
    from scipy.ndimage import binary_erosion
    return binary_erosion(v > 0.5, structure=_disc_bool(_se_radius(a))).astype(np.float64)


def _dilation1(v, a, b):
    """円板構造要素で region を膨張(dilation)する。HALCON の ``dilation1``
    (region を膨張する)に相当。

    半径 ``r = 1 + int(a*4)`` の円板構造要素で ``scipy.ndimage.binary_dilation``
    を呼ぶ。``b`` は未使用。隙間を埋めたり領域を太らせたりするのに使う。
    """
    from scipy.ndimage import binary_dilation
    return binary_dilation(v > 0.5, structure=_disc_bool(_se_radius(a))).astype(np.float64)


def _opening(v, a, b):
    """円板構造要素で region をオープニング(収縮→膨張)する。HALCON の
    ``opening``(region をオープンする)に相当。

    半径 ``r = 1 + int(a*4)`` の円板で ``scipy.ndimage.binary_opening`` を呼ぶ。
    ``b`` は未使用。細い突起や小さな孤立点を除去しつつ全体形状を保つ。
    """
    from scipy.ndimage import binary_opening
    return binary_opening(v > 0.5, structure=_disc_bool(_se_radius(a))).astype(np.float64)


def _closing(v, a, b):
    """円板構造要素で region をクロージング(膨張→収縮)する。HALCON の
    ``closing``(region をクローズする)に相当。

    半径 ``r = 1 + int(a*4)`` の円板で ``scipy.ndimage.binary_closing`` を呼ぶ。
    ``b`` は未使用。小さな穴や切れ目を埋めつつ全体形状を保つ。
    """
    from scipy.ndimage import binary_closing
    return binary_closing(v > 0.5, structure=_disc_bool(_se_radius(a))).astype(np.float64)


def _dilation2(v, a, b):
    """参照点つき dilation: 膨張後に参照点オフセット(b で並進)。

    ``v > 0.5`` を region とし、半径 ``r`` の円板構造要素で ``binary_dilation`` した後、結果を列方向に ``sh`` 画素
    ``np.roll`` で平行移動して 0/1 の float 配列で返す。

    - ``a`` → 円板半径 ``r = 1 + int(a*4)``(1〜5 画素)。
    - ``b`` → 列方向のずらし量 ``sh = int((b-0.5)*6)``。値は -3〜3 で、小数点以下は 0 方向に切り捨てるため ``b`` が
    およそ 1/3〜2/3 の範囲では 0(ずらし無し)になる。負で左、正で右。

    行方向のずらしは無い(参照点を横にずらす形だけを再現)。``np.roll`` なので端からはみ出た分は反対側に現れる
    (端に接する region を扱うときは注意)。単純な膨張だけなら ``hx_dilation1``。
    """
    from scipy.ndimage import binary_dilation
    d = binary_dilation(v > 0.5, structure=_disc_bool(_se_radius(a)))
    sh = int((b - 0.5) * 6)
    return np.roll(d, sh, axis=1).astype(np.float64)


def _gen_disc_se(v, a, b):
    """円板構造要素を region として生成(半径 a)。

    入力 ``v`` は画布の形状のためだけに使い、画像中心 ``((h-1)/2, (w-1)/2)`` から半径 ``r`` 以内の画素を 1 とする
    円板を 0/1 の float 配列(region)で返す。

    - ``a`` → 半径 ``r = (0.05 + 0.35*a) * min(h, w)``(短辺の 5%〜40%)。
    - ``b`` は未使用。

    名前は「構造要素」だが、この op が返すのは画像と同じ大きさの region であり、``hx_erosion1`` などが内部で使う
    小さなカーネルではない。中心固定の円 region が欲しいときの生成器として、``hx_gen_circle``(半径 10%〜50%)の
    小径版にあたる。他の region と重ねて ROI を作るのに使う。
    """
    h, w, Y, X = _grid(v.shape)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    r = (0.05 + 0.35 * a) * min(h, w)
    return ((Y - cy) ** 2 + (X - cx) ** 2 <= r * r).astype(np.float64)


def _gen_circle_sector(v, a, b):
    """円のセクタ region(開始角 b*2pi、掃引 a*2pi)。

    画像中心 ``((h-1)/2, (w-1)/2)``・半径 ``r = 0.42*min(h, w)``(固定)の円板のうち、開始角から掃引角ぶんの扇形を
    1 とする 0/1 の float region を返す。角度は ``arctan2(row-cy, col-cx)`` で測る(0 が +列方向。行が下向きに
    増える画像座標では画面上で時計回りに増える)。

    - ``a`` → 掃引角 ``sweep = 0.1 + a*(2*pi - 0.1)``(約 5.7°〜360°。a=1 で完全な円板)。
    - ``b`` → 開始角 ``start = b*2*pi``。

    扇形の判定は ``(ang - start) mod 2*pi <= sweep`` なので 360° をまたいでも途切れない。半径は固定で、変えたいときは
    ``hx_gen_circle`` / ``hx_gen_disc_se`` を重ねる。楕円版は ``hx_gen_ellipse_sector``。入力画像の中身は見ない。
    """
    h, w, Y, X = _grid(v.shape)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    r = 0.42 * min(h, w)
    rad = np.sqrt((Y - cy) ** 2 + (X - cx) ** 2)
    ang = np.arctan2(Y - cy, X - cx) % (2 * np.pi)
    start = b * 2 * np.pi
    sweep = 0.1 + a * (2 * np.pi - 0.1)
    rel = (ang - start) % (2 * np.pi)
    return ((rad <= r) & (rel <= sweep)).astype(np.float64)


def _gen_ellipse_sector(v, a, b):
    """楕円の扇形(セクタ)region を生成する。HALCON の ``gen_ellipse_sector``
    (楕円セクタを生成する)に相当。

    楕円の軸は画像幅の 42%・高さの 30%に固定。``b`` が開始角(``b*2*pi``)、
    ``a`` が掃引角(``0.1 + a*(2*pi-0.1)``)を振る。``hx_gen_circle_sector`` の
    楕円版。
    """
    h, w, Y, X = _grid(v.shape)
    cy, cx = (h - 1) / 2, (w - 1) / 2
    ra, rb = 0.42 * w, 0.30 * h
    inside = ((X - cx) / ra) ** 2 + ((Y - cy) / rb) ** 2 <= 1.0
    ang = np.arctan2(Y - cy, X - cx) % (2 * np.pi)
    rel = (ang - b * 2 * np.pi) % (2 * np.pi)
    return (inside & (rel <= 0.1 + a * (2 * np.pi - 0.1))).astype(np.float64)


def _gen_empty_region(v, a, b):
    """空(全画素 0)の region を生成する。HALCON の ``gen_empty_region``
    (空 region を生成する)に相当。

    入力と同じ形状の全 0 配列を返すだけ。``a``, ``b`` は未使用。初期値や
    プレースホルダとして使う。
    """
    return np.zeros_like(v, dtype=np.float64)


def _clip_region_rel(v, a, b):
    """region をその外接矩形に対し相対的にクリップ(各辺から a の割合を削る)。

    ``v > 0.5`` の region の外接矩形 ``[y0, y1] × [x0, x1]`` を求め、その高さ・幅の ``0.5*a`` ずつを上下左右から
    削った内側の矩形に含まれる画素だけを残して 0/1 の float 配列で返す。

    - ``a`` → 各辺から削る割合 ``my = int((y1-y0)*0.5*a)``、``mx = int((x1-x0)*0.5*a)``。a=0 で無変化、a=1 で
    外接矩形の中心線付近(1 行・1 列程度)しか残らない。
    - ``b`` は未使用。
    - region が空なら空のまま返す。

    削るのは外接矩形に対する相対量なので、region の大きさが違っても「周辺 x% を落とす」意味が保たれる。外接矩形は
    region 全体で 1 つ(成分ごとではない)ため、離れた小成分が並ぶ場合は端の成分がまるごと消えることがある。
    画像基準の中央矩形で切るなら ``hx_rectangle1_domain`` との論理積を使う。
    """
    reg = v > 0.5
    ys, xs = np.nonzero(reg)
    if ys.size == 0:
        return reg.astype(np.float64)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    my = int((y1 - y0) * 0.5 * a)
    mx = int((x1 - x0) * 0.5 * a)
    out = np.zeros_like(reg)
    out[y0 + my:y1 - my + 1, x0 + mx:x1 - mx + 1] = reg[y0 + my:y1 - my + 1, x0 + mx:x1 - mx + 1]
    return out.astype(np.float64)


def _gen_bandfilter(v, a, b):
    """理想バンドフィルタ画像(周波数円環、中心半径 a・幅 b)。gen_bandpass と別 operator。

    ``hx_gen_lowpass`` と同じ ``fftshift`` 済の正規化周波数半径 ``r``(中心=DC)に対し
    ``c - half <= r <= c + half`` の円環を 1 とする 0/1 の float 画像(周波数領域マスク)を返す。入力 ``v`` は
    形状の取得にのみ使う。

    - ``a`` → 円環の中心半径 ``c = 0.05 + 0.4*a``(0.05〜0.45)。
    - ``b`` → 半幅 ``half = 0.03 + 0.15*b``(0.03〜0.18)。内半径 ``c - half`` が負になる組み合わせ(小さい a と
    大きい b)では DC を含む円板になり、実質ローパスになる。

    ``hx_gen_bandpass`` が「内半径と幅」なのに対し、こちらは「中心と半幅」で同じ円環を指定する。特定の空間周波数
    (縞の周期 ``1/c`` 画素)だけを抜き出すマスクを作り、``fft_generic`` などの中心=DC スペクトルと画素積で使う。
    """
    r = _freq_radius(v.shape)
    c = 0.05 + 0.4 * a
    half = 0.03 + 0.15 * b
    return ((r >= c - half) & (r <= c + half)).astype(np.float64)


def _gen_derivative_filter(v, a, b):
    """周波数領域の微分フィルタ。``a`` が微分の階数、``b`` が向き。

    HALCON の ``gen_derivative_filter`` は Derivative(x / y / xx / yy / xy)と
    次数を取るが、ここは長らく ``|f|`` を正規化して返すだけで、**入力の中身も
    つまみも一切見ていなかった** —— 2026-09-02 実測で、同じ形なら
    ``a``/``b`` を変えても、別の絵を渡しても、返りが**バイト一致**だった
    (兄弟の ``hx_gen_lowpass`` / ``hx_gen_highpass`` / ``hx_gen_bandfilter`` は
    つまみで変わるので、この 1 件だけ浮いていた)。

    * ``a`` : 階数 1〜2(``|f|`` か ``|f|^2``)。2 階はラプラシアンに対応する。
    * ``b`` : 向き。0 で x 方向 ``|f_x|``、1 で y 方向 ``|f_y|``、間は等方 ``|f|``
      へ滑らかに混ぜる(0.5 でちょうど等方)。

    返りは周波数領域の**フィルタそのもの**(HALCON の gen_* と同じ約束)なので、
    入力は形を決めるためだけに使う。ただし形だけでなく**つまみでちゃんと変わる**
    ようになったので、進化が階数と向きを選べる。
    """
    h, w = np.asarray(v).shape[:2]
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    t = float(np.clip(b, 0.0, 1.0))
    # 0 -> x のみ / 0.5 -> 等方 / 1 -> y のみ
    wx = min(1.0, 2.0 * (1.0 - t))
    wy = min(1.0, 2.0 * t)
    mag = np.sqrt((wx * fx) ** 2 + (wy * fy) ** 2)
    order = 1.0 + float(np.clip(a, 0.0, 1.0))          # 1..2 階
    return _norm01(np.fft.fftshift(mag ** order))


def _fill_interlace(v, a, b):
    """2 枚のビデオ半画像を補間(奇数行を隣接偶数行の平均で置換=デインターレース)。

    1 枚の画像を奇数行・偶数行の 2 フィールドとみなし、奇数行(``1::2``)を上下の隣接行の平均
    ``0.5*(v[i-1] + v[i+1])`` で置き換える。偶数行はそのまま。出力は入力と同形の float 画像。

    - ``a``, ``b`` は未使用。
    - 上下の行は ``np.roll`` で取るため、高さが偶数のとき最終行(奇数行)の「下」は先頭行になる(端 1 行だけ循環)。

    インターレース映像の櫛状ずれを消す最も単純な線形補間で、奇数フィールドの情報は捨てられる(縦の解像度は
    半分に落ちる)。どちらのフィールドを残すかは選べない(常に偶数行が生き残る)。行方向の縞が疑われるときの
    前処理として、``hx_nonmax_dir`` など微分系 op の前に置く。
    """
    out = v.copy()
    up = np.roll(v, 1, axis=0)
    dn = np.roll(v, -1, axis=0)
    out[1::2, :] = 0.5 * (up[1::2, :] + dn[1::2, :])
    return out


# ── 第 5 バッチ: 高さ場陰影 / 平面偏差 / 直線分検出 ────────────────────────────── #
def _shade_height_field(v, a, b):
    """高さ場 v を Lambertian 陰影で描画(法線×光源)。方位 a・仰角 b の光源。

    ``v`` を高さ場(gray 値 = 高さ、画素間隔 1)とみなし、``np.gradient`` の ``(gy, gx)`` から法線
    ``n = (-gx, -gy, 1) / sqrt(gx^2 + gy^2 + 1)`` を作り、方向 ``l = (cos(el)cos(az), cos(el)sin(az), sin(el))`` の
    平行光との内積 ``n·l`` を 0 で下から clip し、min-max で [0,1] に正規化して返す(Lambertian 陰影)。

    - ``a`` → 光源の方位角 ``az = a*2*pi``(``lx = cos(az)`` が列方向、``ly = sin(az)`` が行方向の成分)。
    - ``b`` → 光源の仰角 ``el = (0.2 + 0.7*b) * pi/2``(約 18°〜81°。1 で真上に近い)。

    注意: 高さのスケール係数が無く、[0,1] の値を数百画素にわたって微分するため勾配はごく小さい。そのままでは
    陰影の差がほとんど無いが、最後の min-max 正規化で見える化している。したがって出力の絶対的な明るさに意味は
    無く、入力が平坦だと全画素 0 になる。深度画像や ``hx_fit_surface2`` で推定した背景面の凹凸を目で確かめる用途向け。
    """
    gy, gx = np.gradient(v)
    nz = np.ones_like(v)
    norm = np.sqrt(gx * gx + gy * gy + 1.0)
    az, el = a * 2 * np.pi, (0.2 + 0.7 * b) * (np.pi / 2)
    lx, ly, lz = np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)
    shade = (-gx * lx - gy * ly + nz * lz) / norm
    return _norm01(np.clip(shade, 0, None))


def _plane_deviation(v, a, b):
    """gray 値の 1 次平面近似からの偏差 |v - plane|(平坦度/欠陥検査)。

    座標を [-1,1] に正規化した基底 ``[1, x, y]`` で gray 値を最小二乗の平面に当て(``hx_fit_surface1`` と同じ
    回帰)、残差の絶対値 ``|v - plane|`` を [0,1] に clip して返す。正規化はしない(純粋な平面なら丸め誤差程度の
    ほぼ 0 画像になる)。

    - ``a``, ``b`` は未使用。

    平面からの偏差が大きい画素=照明の傾きでは説明できない構造(傷・打痕・異物)。出力は符号を捨てているので
    「平面より明るい/暗い」は区別しない。区別が要るなら ``hx_fit_surface1`` の結果と元画像を別途引く。
    1 次面なので緩やかに曲がった背景は残差に出る。その場合は ``hx_fit_surface2`` 側で背景を推定する。
    後段は ``threshold`` で欠陥 region 化、あるいは ``hx_char_threshold`` の前処理として背景差し引き代わりに使える。
    """
    h, w, Y, X = _grid(v.shape)
    xn = (X / max(w - 1, 1)) * 2 - 1
    yn = (Y / max(h - 1, 1)) * 2 - 1
    A = np.stack([np.ones_like(xn).ravel(), xn.ravel(), yn.ravel()], axis=1)
    coef, *_ = np.linalg.lstsq(A, v.ravel(), rcond=None)
    plane = (A @ coef).reshape(v.shape)
    # 直接クリップ(min-max 正規化は純平面の浮動小数ノイズを [0,1] に増幅するため不可)。
    return np.clip(np.abs(v - plane), 0.0, 1.0)


def _detect_edge_segments(v, a, b):
    """直線的なエッジ断片を検出: NMS で細線化 → 連結成分のうち PCA で細長い(直線状)ものを残す。

    ``hx_nonmax_dir(v, a, 0)`` で細線化したエッジ(``> 0``)を 8 近傍で連結成分に分け、各成分の画素座標の共分散
    固有値比 ``λmax/λmin`` が ``min_ratio`` 以上のもの(細長い=直線状)だけを 1 とする 0/1 の float region を返す。

    - ``a`` → 細線化段の弱エッジしきい値(``hx_nonmax_dir`` の ``a`` と同じ。正規化振幅 ``a*0.3`` 未満を捨てる)。
    - ``b`` → 細長さのしきい値 ``min_ratio = 3 + b*12``(3〜15)。大きいほど真っ直ぐな断片だけ残る。
    - 画素数 5 未満の成分は無条件に捨てる。``λmin`` がほぼ 0(完全な直線)なら比を無限大として採用する。

    注意: 直線性の判定は「点群の広がりが 1 軸に偏っているか」であり、曲線でも十分細長ければ通る。細線化段が斜め
    エッジをほとんど細線化しない(``hx_nonmax_dir`` の注記参照)ため、斜めのエッジは幅を持った塊になり固有値比が
    下がって落とされやすい。連結成分単位なので、交差した線は 1 つの成分として比が下がる。後段で線分ごとに扱うなら
    ``hx_region_to_label`` や ``hough_line_trans``。
    """
    from scipy.ndimage import label, generate_binary_structure
    thin = _nonmax_suppression_dir(v, a, 0) > 0
    lab, n = label(thin, structure=generate_binary_structure(2, 2))
    out = np.zeros_like(v)
    min_ratio = 3.0 + b * 12.0                           # 細長さ閾値(長軸/短軸)
    for k in range(1, n + 1):
        ys, xs = np.nonzero(lab == k)
        if ys.size < 5:
            continue
        pts = np.column_stack([ys - ys.mean(), xs - xs.mean()]).astype(float)
        ev = np.linalg.eigvalsh(np.cov(pts.T)) if pts.shape[0] > 1 else np.array([0.0, 0.0])
        ratio = (ev[1] / ev[0]) if ev[0] > 1e-9 else np.inf
        if ratio >= min_ratio:                           # 直線状のみ採用
            out[ys, xs] = 1.0
    return out


# ── 第 6 バッチ: Image ドメイン/ラベル + Segmentation lowlands/plateaus ────────── #
def _gen_image_proto(v, a, b):
    """入力と同サイズの定数グレー画像(値 a)を生成。

    入力 ``v`` と同じ形状で全画素が ``a`` の float64 画像を返す。入力の中身は見ない。

    - ``a`` → 定数値(そのまま。0 で真っ黒、1 で真っ白)。
    - ``b`` は未使用。

    算術 op の相手(オフセット・スケール)や、マスクの補集合を作る土台として使う。全面 1 の region が欲しければ
    ``hx_full_domain`` / ``hx_get_domain``、全面 0 の region は ``hx_gen_empty_region``。
    """
    return np.full_like(v, float(a), dtype=np.float64)


def _get_domain(v, a, b):
    """画像の定義域を region として取得(既定は全面)。

    入力 ``v`` と同じ形状の全 1 の float64 配列(region)を返す。この実装は画像に ROI(定義域)の概念を持たないため、
    定義域は常に画像全面であり、``hx_full_domain`` と同じ結果になる。

    - ``a``, ``b`` は未使用。入力の gray 値も見ない。

    用途は「今の定義域を region として取り出し、他の region 演算の初期値にする」こと。ROI を絞った region が
    欲しいときは ``hx_rectangle1_domain``(中央矩形)か ``threshold`` で作る。
    """
    return np.ones_like(v, dtype=np.float64)


def _region_to_label(v, a, b):
    """しきい値 a で二値化した領域の連結成分をラベル画像に変換(正規化)。

    ``v > a`` を前景として ``ndimage.label``(8 近傍)で連結成分にラベル付けし、ラベル番号 ``1..n`` を ``n`` で割った
    float 画像を返す。背景は 0、成分は ``1/n, 2/n, ..., 1`` の等間隔の値になる。成分が無ければ全 0。

    - ``a`` → 二値化しきい値(region を渡すときは 0.5 にする)。
    - ``b`` は未使用。

    ラベル番号は走査順(左上から)で振られるため、同じ成分でも画像内の他の成分数 ``n`` が変わると値が変わる。
    値で成分を識別する用途にのみ向き、値の大小に意味は無い。成分ごとの統計が欲しければ ``hx_region_to_mean``
    (平均 gray 値で塗る)を使う。ラベル画像から 1 成分だけを取り出すには ``threshold`` 系で値域を切る。
    """
    from scipy.ndimage import label, generate_binary_structure
    lab, n = label(v > a, structure=generate_binary_structure(2, 2))
    return (lab / n).astype(np.float64) if n > 0 else np.zeros_like(v)


def _rectangle1_domain(v, a, b):
    """画像の定義域を軸並行矩形に縮小(中央の a×b の割合)region。

    入力 ``v`` と同じ形状で、画像中央に置いた高さ ``hh``・幅 ``ww`` の軸並行矩形を 1 とする 0/1 の float 配列
    (region)を返す。入力の中身は見ない。

    - ``a`` → 高さの割合 ``hh = int(h * (0.2 + 0.7*a))``(20%〜90%)。
    - ``b`` → 幅の割合 ``ww = int(w * (0.2 + 0.7*b))``(20%〜90%)。
    - 左上は ``((h-hh)//2, (w-ww)//2)`` で、中央からのずれは整数切り捨てぶんだけ。

    画像の周辺(照明落ち・レンズ端)を検査対象から外す ROI を作るのに使う。画像全面が欲しければ ``hx_full_domain``、
    既存 region の周辺を削るなら ``hx_clip_region_rel``。
    """
    h, w = v.shape
    hh, ww = int(h * (0.2 + 0.7 * a)), int(w * (0.2 + 0.7 * b))
    y0, x0 = (h - hh) // 2, (w - ww) // 2
    out = np.zeros_like(v, dtype=np.float64)
    out[y0:y0 + hh, x0:x0 + ww] = 1.0
    return out


def _lowlands(v, a, b):
    """gray 値の窪地(局所最小の平坦域)を検出: 近傍最小と一致する画素 region。

    ``ndimage.minimum_filter``(``size`` 角の正方形窓、鏡映境界)で局所最小 ``mn`` を取り、``v <= mn + 1e-6`` かつ
    ``v < 画像平均`` の画素を 1 とする 0/1 の float region を返す。

    - ``a`` → 窓の一辺 ``size = 3 + int(a*6)``(3〜9 画素)。大きいほど広い範囲で最小である必要があり、点が減る。
    - ``b`` は未使用。

    平坦な窪みは窓内の全画素が最小値に等しいため、領域ごと(1 点ではなく面で)拾われる。逆に画像全体が平坦だと
    ``v < mean`` を満たす画素が無く空になる。「平均より暗い」条件のため、明るい面の中の浅い窪みは拾えない。
    雑音があると小さな極小が大量に出るので、前段に ``hx_mean_shape`` / ``gauss_filter`` を置く。反対の隆起は
    画像を反転して同じ op を掛ける。
    """
    size = 3 + int(a * 6)
    mn = ndimage.minimum_filter(v, size=size, mode="reflect")
    return ((v <= mn + 1e-6) & (v < float(v.mean()))).astype(np.float64)


def _plateaus_center(v, a, b):
    """gray 値の平坦域(勾配~0)の中心を検出: 平坦連結成分の重心画素を marker region に。

    Sobel 勾配振幅 ``gmag`` を求め、``gmag < (0.01 + 0.1*a) * max(gmag)`` の画素を「平坦」として 8 近傍で連結成分に
    分け、各成分の重心(``center_of_mass``)を四捨五入した 1 画素だけを 1 とするマーカー region を返す。

    - ``a`` → 平坦とみなす勾配の上限(最大勾配の 1%〜11%)。大きいほど平坦域が広がりつながる。
    - ``b`` は未使用。
    - 成分が 1 つも無ければ全 0。

    注意: 出力は成分 1 つにつき 1 画素で、成分の面積や形は失われる。重心は非凸な平坦域(環状など)では域外に落ちる
    ことがある。しきい値が最大勾配に対する相対値なので、強いエッジが 1 本あるだけで他の緩い勾配が「平坦」側に入る。
    ウォーターシェッドのマーカーや、成分数を数える用途向け。面としての平坦域が欲しいなら ``hx_lowlands``。
    """
    from scipy.ndimage import label, center_of_mass, generate_binary_structure
    gmag = np.hypot(ndimage.sobel(v, axis=1), ndimage.sobel(v, axis=0))
    flat = gmag < (0.01 + 0.1 * a) * (gmag.max() + 1e-9)
    lab, n = label(flat, structure=generate_binary_structure(2, 2))
    out = np.zeros_like(v, dtype=np.float64)
    if n > 0:
        for cy, cx in center_of_mass(flat, lab, range(1, n + 1)):
            out[int(round(cy)), int(round(cx))] = 1.0
    return out


# ── 第 7 バッチ: region 平行移動 / skeleton 分割 ──────────────────────────────── #
def _move_region(v, a, b):
    """region を平行移動(dy=a, dx=b を中心 0 のオフセットに)。

    np.roll ゆえ**端は循環**(はみ出た region が反対側から現れる)。HALCON の
    move_region は端で消える(クリップ)なので端に触れる移動では挙動が異なる —
    進化 op の特徴量用途では循環で一様性を保つ設計を維持し、差異はここに開示する。
    """
    reg = v > 0.5
    dy = int((a - 0.5) * v.shape[0])
    dx = int((b - 0.5) * v.shape[1])
    return np.roll(np.roll(reg, dy, 0), dx, 1).astype(np.float64)


def _split_skeleton_region(v, a, b):
    """1 画素幅 skeleton を分岐点で分割: 近傍数>=3 の junction を除いて連結成分に分ける。

    ``v > 0.5`` の骨格画素ごとに 8 近傍の骨格画素数 ``nb`` を数え、``nb >= 3`` の画素(分岐点)を取り除いた
    0/1 の float 配列を返す。分岐点を抜くことで骨格が枝ごとの連結成分に分かれる。

    - ``a``, ``b`` は未使用。

    前提は 1 画素幅の骨格(``skeleton`` の出力)。太い線や塊を渡すと内部の画素はすべて ``nb >= 3`` となり
    ほぼ全部が消える。分岐点そのものは出力に含まれない(分岐の位置が要るなら ``junctions_skeleton``)。
    分かれた枝を個別に扱うには後段で ``hx_region_to_label`` を掛ける。分岐点の隣接画素は除かないので、
    多方向が集まる太めの交差では 1 画素の残骸がつながったまま残ることがある。同系の op に ``r2_split_skeleton_lines``。
    """
    from scipy.ndimage import convolve
    sk = (v > 0.5).astype(np.uint8)
    nb = convolve(sk, np.array([[1, 1, 1], [1, 0, 1], [1, 1, 1]]), mode="constant")
    junc = (sk == 1) & (nb >= 3)                         # 分岐点
    return ((sk == 1) & ~junc).astype(np.float64)


# ── 第 8 バッチ: XLD contour(dict {shape,(H,W); cs:[Nx2 (row,col)]})─────────────── #
def _c_cs(v):
    return [np.asarray(c, float) for c in v.get("cs", [])] if isinstance(v, dict) else []


def _c_shape(v):
    return tuple(v.get("shape", (1, 1))) if isinstance(v, dict) else (1, 1)


def _c_mk(shape, cs):
    return {"shape": shape, "cs": [np.asarray(c, float) for c in cs if len(c) > 0]}


def _sort_contours_xld(v, a, b):
    """contour を相対位置(重心 row→col)でソート。

    contour dict(``{"shape": (H, W), "cs": [N×2 の (row, col) 配列, ...]}``)の ``cs`` を、各 contour の点の平均
    (重心)の行、次に列の昇順で並べ替えて返す。点列そのものは変えない。

    - ``a``, ``b`` は未使用。
    - dict 以外や ``cs`` が空なら空の contour 集合を返す(例外は出ない)。点数 0 の contour は出力から落ちる。

    上→下、同じ高さなら左→右の順になるので、文字列や部品列を読み順に並べるのに使う。重心は点の単純平均で、
    点の密度に偏りがあれば幾何学的な中心とずれる。``hx_union_adjacent`` はリスト順に貪欲連結するため、前にこの op を
    置くと連結の結果が安定する。
    """
    cs = _c_cs(v)
    cs.sort(key=lambda c: (float(c[:, 0].mean()), float(c[:, 1].mean())))
    return _c_mk(_c_shape(v), cs)


def _clip_contours_xld(v, a, b):
    """contour を画像ドメイン(中央 margin a/b を残す矩形)にクリップ(範囲外点を除去)。

    contour dict の各 contour について、画像の内側に取った矩形 ``my <= row <= H-1-my``、``mx <= col <= W-1-mx``
    に入る点だけを残し、1 点も残らない contour は捨てて返す。

    - ``a`` → 上下の余白 ``my = a*0.4*H``(0〜高さの 40%)。
    - ``b`` → 左右の余白 ``mx = b*0.4*W``(0〜幅の 40%)。a=b=0 なら画像範囲 ``[0, H-1] × [0, W-1]`` でのクリップ。

    点を間引くだけで contour は分割しないため、矩形外を通って戻ってくる contour は残った点どうしが直接つながった
    形(ジャンプ)になる。分割が要るなら後段で ``hx_split_contours``。中心からの割合で切る類似 op に
    ``hx_crop_contours``(中心基準の幅・高さ指定)。線長で足切りする ``xg_clip_contours`` とは別物。
    """
    h, w = _c_shape(v)
    my, mx = a * 0.4 * h, b * 0.4 * w
    out = []
    for c in _c_cs(v):
        m = (c[:, 0] >= my) & (c[:, 0] <= h - 1 - my) & (c[:, 1] >= mx) & (c[:, 1] <= w - 1 - mx)
        if m.any():
            out.append(c[m])
    return _c_mk((h, w), out)


def _clip_end_points_contours_xld(v, a, b):
    """各 contour の端点を k 個ずつ切り落とす(k は a)。

    contour dict の各 contour から先頭と末尾の ``k`` 点ずつを落とし ``c[k:len-k]`` を返す。

    - ``a`` → 切り落とす点数 ``k = 1 + int(a*5)``(1〜6 点)。
    - ``b`` は未使用。
    - 点数が ``2k+1`` 以下の contour は短くするのではなく丸ごと捨てる。短い contour が多いと出力が空になりうる。

    エッジ抽出の端に出るかぎ状の乱れや、閉じた contour の始点重複を落とすのに使う。単位は「点数」であって画素距離
    ではないので、点の密度(``edges_sub_pix`` は 1 画素刻み)を意識する。閉じた contour に掛けると閉じなくなる
    (``hx_test_closed_xld`` の判定が変わる)。
    """
    k = 1 + int(a * 5)
    out = [c[k:len(c) - k] for c in _c_cs(v) if len(c) > 2 * k + 1]
    return _c_mk(_c_shape(v), out)


def _all_pts(v):
    cs = _c_cs(v)
    return np.concatenate(cs, 0) if cs else np.zeros((0, 2))


def _smallest_circle_xld(v, a, b):
    """全 contour 点の最小包含円(近似=重心中心)の半径を返す(正規化 feature)。

    contour dict の全 contour の点をまとめ、点の平均(重心)を中心として最も遠い点までの距離 ``r`` を求め、
    ``r / max(H, W)`` を ``np.float64`` で返す。真の最小包含円(中心も最適化)ではなく「重心を中心とする包含円」の
    近似で、半径は真値以上になる。

    - ``a``, ``b`` は未使用。
    - 点が 1 つも無ければ 0.0(有効な値 0 と区別できない)。

    複数 contour があっても 1 つの円で包む(contour ごとではない)。正規化は画像の長辺なので、同じ形でも画像サイズが
    変わると値が変わる。円らしさを測りたいなら ``hx_fit_circle_contour``(残差)や ``circularity_xld``。
    region 版の厳密解は ``r2_smallest_circle``。
    """
    p = _all_pts(v)
    if len(p) == 0:
        return np.float64(0.0)
    c = p.mean(0)
    r = float(np.sqrt(((p - c) ** 2).sum(1)).max())
    return np.float64(r / max(_c_shape(v)))


def _smallest_rectangle1_xld(v, a, b):
    """全 contour 点の外接軸並行矩形の面積比を返す(feature)。

    contour dict の全点をまとめ、行方向・列方向それぞれの ``max - min``(外接軸並行矩形の高さ・幅)の積を
    画像面積 ``H*W`` で割った値を ``np.float64`` で返す。

    - ``a``, ``b`` は未使用。
    - 点が無ければ 0.0。1 点だけ、または全点が同一行/列でも幅が 0 になり 0.0(``+1`` の画素補正はしない)。

    全 contour をまとめた 1 つの矩形なので、離れた contour が 2 つあると間の空白も面積に入る。向きを持つ
    最小面積矩形は ``hx_smallest_rect2_xld``、region に対する軸並行外接矩形は ``smallest_rectangle1``。
    """
    p = _all_pts(v)
    if len(p) == 0:
        return np.float64(0.0)
    hw = (p.max(0) - p.min(0))
    h, w = _c_shape(v)
    return np.float64(float(hw[0] * hw[1]) / max(h * w, 1))


def _test_closed_xld(v, a, b):
    """閉じている contour の割合を返す(端点間距離が閾値未満=閉、feature)。

    contour dict の各 contour について、点数が 3 以上かつ始点と終点のユークリッド距離が ``tol`` 以下なら
    「閉じている」と数え、閉じた contour の本数を全 contour 数で割った割合を ``np.float64`` で返す。

    - ``a`` → 許容距離 ``tol = 1 + a*4``(1〜5 画素)。
    - ``b`` は未使用。
    - contour が無ければ 0.0。

    始点=終点を重複させて閉じる ``close_contours_xld`` の出力は距離 0 なので必ず閉と判定される。
    ``hx_clip_end_points`` や ``hx_clip_contours`` で端を落とした後は開いた扱いになる。個々の contour がどれかは
    返さない(割合のみ)。
    """
    cs = _c_cs(v)
    if not cs:
        return np.float64(0.0)
    tol = 1.0 + a * 4.0
    closed = sum(1 for c in cs if len(c) > 2 and np.hypot(*(c[0] - c[-1])) <= tol)
    return np.float64(closed / len(cs))


def _regress_contours_xld(v, a, b):
    """各 contour に回帰直線を当て、平均残差(直線からのズレ)を返す(feature)。小=直線的。

    点数 3 以上の各 contour について、点の重心を通る全最小二乗直線(座標共分散の最小固有ベクトルを法線とする)を
    当て、点から直線までの距離の RMS を求める。全 contour の RMS を平均し ``max(H, W)`` で割って 1 で頭打ちした
    ``np.float64`` を返す。

    - ``a``, ``b`` は未使用。
    - 有効な contour が無ければ 0.0(「完全な直線」と区別できない)。

    小さいほど直線的。直線そのものの傾きや位置は返さない(当てはめ結果が要るなら ``fit_line_contours``)。
    折れ線としての角の数を見たいなら ``hx_split_contours`` で分割してから線分数を数える。点数 2 以下の contour は
    評価から外れる。1 本の contour だけを対象にした同種の指標は ``xg_regress_contours``。
    """
    cs = _c_cs(v)
    res = []
    for c in cs:
        if len(c) < 3:
            continue
        d = c - c.mean(0)
        w_, V = np.linalg.eigh(np.cov(d.T))
        n = V[:, 0]                                       # 最小固有ベクトル=法線
        res.append(float(np.sqrt((( d @ n) ** 2).mean())))
    if not res:
        return np.float64(0.0)
    return np.float64(min(np.mean(res) / max(_c_shape(v)), 1.0))


def _moments_any_xld(v, a, b):
    """全 contour 点の 2 次中心モーメント(広がり)を返す(正規化 feature)。

    contour dict の全点をまとめ、重心からの二乗距離の平均 ``mean((row - mean_row)^2 + (col - mean_col)^2)``
    (2 次中心モーメント ``mu20 + mu02`` を点数で割ったもの)を ``max(H, W)^2`` で割り、1 で頭打ちした
    ``np.float64`` で返す。

    - ``a``, ``b`` は未使用。
    - 点が 2 個未満なら 0.0。

    「点群が重心からどれだけ広がっているか」の等方的な指標で、向きや縦横比は含まない。輪郭の点密度に依存するので、
    同じ図形でも点の刻みが不均一だと値が変わる。向き付きの慣性(長軸・短軸)は ``hx_fit_ellipse_contour`` /
    ``elliptic_axis_xld``、region の 2 次モーメントは ``moments_region_2nd``。
    """
    p = _all_pts(v)
    if len(p) < 2:
        return np.float64(0.0)
    d = p - p.mean(0)
    mu = (d[:, 0] ** 2 + d[:, 1] ** 2).mean()
    return np.float64(min(mu / (max(_c_shape(v)) ** 2), 1.0))


def _cross2d(a, b):
    """2D ベクトルの外積(z 成分のスカラー)。numpy>=2.0 で ``np.cross`` の 2 次元
    入力対応が削除される見込みのため、明示式で代替(数式は等価: a×b の z 成分)。"""
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def _rdp(pts, eps):
    """Ramer-Douglas-Peucker: 支配点の index を返す。"""
    if len(pts) < 3:
        return [0, len(pts) - 1]
    a, b = pts[0], pts[-1]
    ab = b - a
    L = np.hypot(*ab)
    if L < 1e-9:
        d = np.hypot(*(pts - a).T)
    else:
        d = np.abs(_cross2d(np.tile(ab, (len(pts), 1)), pts - a)) / L
    i = int(np.argmax(d))
    if d[i] > eps:
        left = _rdp(pts[:i + 1], eps)
        right = _rdp(pts[i:], eps)
        return left[:-1] + [x + i for x in right]
    return [0, len(pts) - 1]


def _split_contours_xld(v, a, b):
    """各 contour を支配点(RDP)で線分に分割する(許容 eps は a)。

    各 contour(点数 3 以上)に Ramer-Douglas-Peucker を掛けて支配点の index を求め、隣り合う支配点の間の部分列
    ``c[s:e+1]`` を新しい contour として並べる(隣り合う線分は端点を共有する)。点数 2 以下の contour はそのまま通す。

    - ``a`` → 許容距離 ``eps = 0.5 + a*5``(0.5〜5.5 画素)。この距離以内の折れは無視されるので、大きいほど線分が
    長く少なくなる。
    - ``b`` は未使用。

    出力は「線分ごとの contour」であって折れ線の頂点だけではない(元の点は全部残る)。閉じた contour(始点=終点)は
    始点から最も遠い点で最初に分割される。線分の本数が角の数の目安になり、``hx_regress_contours`` を後段に置くと
    各線分の直線性が測れる。
    """
    eps = 0.5 + a * 5.0
    out = []
    for c in _c_cs(v):
        if len(c) < 3:
            out.append(c)
            continue
        idx = _rdp(c, eps)
        for s, e in zip(idx[:-1], idx[1:]):
            if e - s >= 1:
                out.append(c[s:e + 1])
    return _c_mk(_c_shape(v), out)


def _gen_parallel_contour_xld(v, a, b):
    """各 contour の平行(法線オフセット)contour を生成(距離は (a-0.5) で符号つき)。

    各 contour(点数 2 以上)の接線を ``np.gradient(c, axis=0)`` で求め、それを 90° 回した単位法線
    ``(-t_col, t_row) / |t|`` の方向に ``dist`` だけ全点をずらした contour を返す。元の contour は出力に含まれない
    (置き換わる)。

    - ``a`` → 符号つきオフセット ``dist = (a - 0.5) * 10``(-5〜+5 画素。a=0.5 で無変化)。
    - ``b`` は未使用。
    - 接線長が 1e-9 未満の点(重複点)は法線 0 とし動かさない。点数 1 の contour はそのまま。

    法線の向きは contour の進行方向で決まる(左右どちらが正かは点列の向き次第)。曲率半径より大きくずらすと
    自己交差する(``hx_test_self_intersect`` で検出可能)。輪郭を太らせ/痩せさせた形の比較や、計測線を境界から
    一定距離に置くのに使う。
    """
    dist = (a - 0.5) * 10.0
    out = []
    for c in _c_cs(v):
        if len(c) < 2:
            out.append(c)
            continue
        t = np.gradient(c, axis=0)
        nrm = np.column_stack([-t[:, 1], t[:, 0]])
        L = np.hypot(nrm[:, 0], nrm[:, 1])[:, None]
        nrm = nrm / np.where(L < 1e-9, 1.0, L)
        out.append(c + dist * nrm)
    return _c_mk(_c_shape(v), out)


# ── 第 9 バッチ: XLD contour への形状フィット(contour -> feature)──────────────── #
def _fit_circle_contour_xld(v, a, b):
    """Kåsa 代数法で contour 点に円を当て、フィット残差(RMS)を返す(小=円に近い)。

    全 contour の点をまとめ、Kåsa の代数法(``[x, y, 1]·sol = x^2 + y^2`` を最小二乗で解き、中心
    ``(sol0/2, sol1/2)``、半径 ``sqrt(sol2 + cx^2 + cy^2)``)で円を当て、各点の中心からの距離と半径の差の RMS を
    ``max(H, W)`` で割って 1 で頭打ちした ``np.float64`` で返す。円のパラメータ自体は返さない。

    - ``a``, ``b`` は未使用。
    - 点が 3 個未満なら 0.0(完全な円と区別できない)。半径の根号の中が負になれば半径 0 として扱う。

    代数法は幾何学的な距離の最小化ではないので、円弧が短い(角度範囲が狭い)点群や外れ値では半径が偏る。
    ほぼ直線上の点群では最小ノルム解の半径が非常に大きくなり、残差は小さく出る(直線が「大きな円」に見える)。
    円らしさの判定には ``hx_regress_contours`` と併用して直線を除く。包含円の半径は ``hx_smallest_circle_xld``。
    """
    p = _all_pts(v)
    if len(p) < 3:
        return np.float64(0.0)
    x, y = p[:, 1], p[:, 0]
    A = np.column_stack([x, y, np.ones_like(x)])
    bb = x * x + y * y
    sol, *_ = np.linalg.lstsq(A, bb, rcond=None)
    cx, cy = sol[0] / 2, sol[1] / 2
    r = np.sqrt(max(sol[2] + cx * cx + cy * cy, 0))
    res = np.sqrt(((np.hypot(x - cx, y - cy) - r) ** 2).mean())
    return np.float64(min(res / max(_c_shape(v)), 1.0))


def _fit_ellipse_contour_xld(v, a, b):
    """2 次モーメントから楕円を当て、軸比(短/長=真円で 1、細長いほど 0)を返す。

    全 contour の点をまとめて座標共分散行列の固有値 ``λmin, λmax`` を取り、``sqrt(λmin/λmax)``(主軸方向の標準偏差
    の比 = 慣性楕円の短軸/長軸)を ``np.float64`` で返す。

    - ``a``, ``b`` は未使用。
    - 点が 3 個未満、または ``λmax <= 1e-9``(全点一致)なら 0.0。負の固有値は 0 に clip する。

    1 に近いほど等方(真円)、0 に近いほど細長い。楕円境界を当てはめる代数的フィットではなく点群の 2 次モーメント
    なので、点の密度の偏りや欠けた弧では軸比が変わる。楕円の傾き・中心は返さない(``orientation_xld`` /
    ``area_center_xld``)。``cv2.fitEllipse`` 版は ``elliptic_axis_xld``。楕円からの逸脱量は ``hx_dist_ellipse_contour``。
    """
    p = _all_pts(v)
    if len(p) < 3:
        return np.float64(0.0)
    d = p - p.mean(0)
    w_, _ = np.linalg.eigh(np.cov(d.T))
    w_ = np.clip(w_, 0, None)
    return np.float64(np.sqrt(w_[0] / w_[1]) if w_[1] > 1e-9 else 0.0)


def _min_area_rect_ratio(p):
    """角度掃引で最小面積外接矩形を求め、(点の広がり充填率, 面積) を返す。"""
    best = None
    for deg in range(0, 90, 6):
        th = np.radians(deg)
        R = np.array([[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]])
        q = p @ R.T
        area = float((np.ptp(q[:, 0]) + 1e-9) * (np.ptp(q[:, 1]) + 1e-9))
        if best is None or area < best[0]:
            best = (area, np.ptp(q[:, 0]), np.ptp(q[:, 1]))
    return best


def _fit_rectangle2_contour_xld(v, a, b):
    """最小面積外接矩形を当て、そのアスペクト比(短辺/長辺)を返す(feature)。

    全 contour の点をまとめ、0°〜84° を 6° 刻みで回転させたときの軸並行外接矩形の面積が最小になる角度を探し、
    その矩形の短辺/長辺を ``np.float64`` で返す(``hx_smallest_rect2_xld`` と同じ探索)。

    - ``a``, ``b`` は未使用。
    - 点が 3 個未満なら 0.0。長辺が 1e-9 未満(全点一致)でも 0.0。

    角度は 15 通りの離散探索なので、真の最小面積矩形とは最大 3° ずれる(細長い形ほどアスペクト比への影響は小さい)。
    矩形の中心・角度・辺長は返さない。1 に近いほど正方形、0 に近いほど細長い。回転を伴わない外接矩形の面積比は
    ``hx_smallest_rect1_xld``、region 版(回転キャリパー)は ``r2_smallest_rectangle2``。
    """
    p = _all_pts(v)
    if len(p) < 3:
        return np.float64(0.0)
    _, e1, e2 = _min_area_rect_ratio(p)
    lo, hi = sorted((e1, e2))
    return np.float64(lo / hi if hi > 1e-9 else 0.0)


def _smallest_rectangle2_xld(v, a, b):
    """最小面積外接矩形の面積比(矩形面積 / 画像面積)を返す(feature)。

    全 contour の点をまとめ、0°〜84° を 6° 刻みで回転させて軸並行外接矩形の面積を計算し、その最小値を画像面積
    ``H*W`` で割って 1 で頭打ちした ``np.float64`` で返す。

    - ``a``, ``b`` は未使用。
    - 点が 3 個未満なら 0.0。各辺には ``1e-9`` が足してあり、点が同一直線上でも面積は厳密には 0 でなく極小値。

    角度探索が 6° 刻みなので真の最小面積より最大で数 % 大きく出ることがある。全 contour を 1 つの矩形で包むため、
    離れた contour が複数あると間の空白も含む。アスペクト比は ``hx_fit_rectangle2_contour``、軸並行版は
    ``hx_smallest_rect1_xld``。
    """
    p = _all_pts(v)
    if len(p) < 3:
        return np.float64(0.0)
    area, _, _ = _min_area_rect_ratio(p)
    h, w = _c_shape(v)
    return np.float64(min(area / max(h * w, 1), 1.0))


# ── 第 10 バッチ: XLD contour 続き ───────────────────────────────────────────── #
def _crop_contours_xld(v, a, b):
    """contour を中央の a×b 割合の矩形に crop(範囲内の点のみ残す)。

    各 contour の点のうち、画像中心 ``(H/2, W/2)`` からの距離が行方向 ``hh`` 以内かつ列方向 ``ww`` 以内のものだけを
    残し、1 点も残らない contour は捨てて返す。

    - ``a`` → 残す高さの半分 ``hh = (0.3 + 0.6*a) * H/2``(全体の 30%〜90%)。
    - ``b`` → 残す幅の半分 ``ww = (0.3 + 0.6*b) * W/2``(全体の 30%〜90%)。a=b=1 でも周辺 5% は落ちる。

    点を間引くだけで分割しないので、矩形の外を回って戻る contour は残った点どうしがつながる(ジャンプ)。
    矩形外を完全に無視したい場合は後段で ``hx_split_contours``。余白を画像端から指定する版は ``hx_clip_contours``、
    1 つのノブで正方形窓にする版は ``xg_crop_contours``。
    """
    h, w = _c_shape(v)
    hh, ww = (0.3 + 0.6 * a) * h / 2, (0.3 + 0.6 * b) * w / 2
    cy, cx = h / 2, w / 2
    out = []
    for c in _c_cs(v):
        m = (np.abs(c[:, 0] - cy) <= hh) & (np.abs(c[:, 1] - cx) <= ww)
        if m.any():
            out.append(c[m])
    return _c_mk((h, w), out)


def _dist_ellipse_contour_xld(v, a, b):
    """contour 点の当てはめ楕円境界からの平均距離を返す(小=楕円に近い、feature)。

    全 contour の点をまとめ、重心と座標共分散の固有分解から主軸系に移し、半軸を ``2*sqrt(λ)``(各主軸の 2σ)とする
    楕円を当てて、各点の正規化半径 ``rad = sqrt((u/ax0)^2 + (v/ax1)^2)`` と 1 との差 ``|rad - 1|`` の平均を 1 で
    頭打ちした ``np.float64`` で返す。

    - ``a``, ``b`` は未使用。
    - 点が 4 個未満なら 0.0。固有値は ``1e-9`` で下から clip。

    注意: 値は画素距離ではなく楕円の正規化座標での差(無次元)。また半軸 2σ は「一様に塗られた楕円」に合う値で、
    境界だけの点群では ``σ = 半軸/sqrt(2)`` になるため、完全な楕円輪郭でも 0 にならず約 0.29 の下駄が乗る(実測
    0.2938)。比較用の相対指標として使い、絶対値で「楕円かどうか」を切らない。最大値版は ``hx_dist_ellipse_points``、
    軸比は ``hx_fit_ellipse_contour``。
    """
    p = _all_pts(v)
    if len(p) < 4:
        return np.float64(0.0)
    c = p.mean(0)
    d = p - c
    w_, V = np.linalg.eigh(np.cov(d.T))
    w_ = np.clip(w_, 1e-9, None)
    loc = d @ V                                          # 主軸系
    ax = 2 * np.sqrt(w_)                                 # 半軸(≈2σ)
    rad = np.sqrt((loc[:, 0] / ax[0]) ** 2 + (loc[:, 1] / ax[1]) ** 2)
    return np.float64(min(float(np.abs(rad - 1.0).mean()), 1.0))


def _seg_intersect(p1, p2, p3, p4):
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)


def _test_self_intersection_xld(v, a, b):
    """自己交差する contour の割合を返す(feature)。非隣接セグメント対を判定。

    各 contour(点数 4 以上)について、隣接しない線分の全対 ``(i, i+1)`` と ``(j, j+1)``(``j >= i+2``)を
    向き付き面積の符号(ccw 判定)で交差判定し、1 対でも交差する contour の本数を全 contour 数で割った割合を
    ``np.float64`` で返す。始点と終点が一致(距離 1e-6 未満)する閉曲線では、最初の線分と最後の線分の対は隣接扱いで
    除外する。

    - ``a``, ``b`` は未使用。
    - contour が無ければ 0.0。点数 3 以下の contour は交差なしとして数える。

    判定は真に交差する場合のみで、端点が相手の線分上に乗る接触や同一直線上の重なりは検出しない(不等号が厳密)。
    計算量は contour ごとに線分数の 2 乗で、点の多い contour では遅い(``hx_split_contours`` や
    ``smooth_contours_xld`` で点を減らしてから)。``hx_gen_parallel_contour`` で内側にずらした輪郭の破綻検出に使える。
    """
    cs = _c_cs(v)
    if not cs:
        return np.float64(0.0)
    hit = 0
    for c in cs:
        n = len(c)
        if n < 4:
            continue
        closed = np.hypot(*(c[0] - c[-1])) < 1e-6         # 端点一致=閉曲線
        found = False
        for i in range(n - 1):
            for j in range(i + 2, n - 1):
                if closed and i == 0 and j == n - 2:
                    continue                             # 閉曲線のみ端の隣接をスキップ
                if _seg_intersect(c[i], c[i + 1], c[j], c[j + 1]):
                    found = True
                    break
            if found:
                break
        hit += found
    return np.float64(hit / len(cs))


def _union_adjacent_contours_xld(v, a, b):
    """端点が近い(閾値 a)contour を貪欲に連結する。

    contour のリストを走査し、``cs[i]`` の終点と ``cs[j]``(``j > i``)の始点の距離が ``tol`` 以下なら ``cs[j]`` を
    ``cs[i]`` の後ろにつないで 1 本にする。1 回つなぐたびに先頭から走査をやり直し、つなげる対が無くなるまで繰り返す。

    - ``a`` → 許容距離 ``tol = 1 + a*8``(1〜9 画素)。
    - ``b`` は未使用。

    判定は「終点→始点」の向きだけで、始点どうし・終点どうしが近い場合に反転してつなぐことはしない(向きの揃った
    contour 列を想定)。貪欲法なので 3 本以上が候補になるときはリスト順で先に見つかった相手とつながる
    (``hx_sort_contours`` で順序を整えると結果が安定する)。つなぎ目の点は重複せず、隙間は直線で飛ぶ。
    計算量は本数の 2 乗×連結回数。つないだ後の閉じ具合は ``hx_test_closed_xld`` で確認する。
    """
    cs = [c for c in _c_cs(v) if len(c) > 0]
    tol = 1.0 + a * 8.0
    merged = True
    while merged and len(cs) > 1:
        merged = False
        for i in range(len(cs)):
            for j in range(i + 1, len(cs)):
                if np.hypot(*(cs[i][-1] - cs[j][0])) <= tol:
                    cs[i] = np.vstack([cs[i], cs[j]])
                    cs.pop(j)
                    merged = True
                    break
            if merged:
                break
    return _c_mk(_c_shape(v), cs)


def _polar_trans_contour_xld_inv(v, a, b):
    """contour 点を (radius, angle) とみなし直交座標へ逆変換(polar_trans の逆)。

    各 contour の点を ``(row, col) = (半径 rad, 角度)`` とみなし、``ang = col / W * 2*pi`` として
    ``(cy + rad*sin(ang), cx + rad*cos(ang))``(``cy, cx = H/2, W/2``)の直交座標に戻した contour を返す。

    - ``a``, ``b`` は未使用。
    - 半径は行の値をそのまま画素距離として使い、角度は列を画像幅で 0〜2π に写す。

    注意: 順変換 ``polar_trans_contour_xld`` は行を ``r / max(H, W) * H``、列を ``(θ + π) / 2π * W`` として
    出力するため、この op はその厳密な逆にはなっていない。角度に π のずれ(点が中心対称の位置に写る)、非正方画像では
    半径に ``max(H, W)/H`` 倍のずれが出る(往復で半径の 2 倍の誤差が出る実測)。順変換との往復を期待するときは
    この差を織り込むか、この op を「列=角度・行=半径の一般的な極座標表現から直交へ」の変換として単独で使う。
    """
    h, w = _c_shape(v)
    cy, cx = h / 2, w / 2
    out = []
    for c in _c_cs(v):
        rad = c[:, 0]
        ang = c[:, 1] / max(w, 1) * 2 * np.pi
        out.append(np.column_stack([cy + rad * np.sin(ang), cx + rad * np.cos(ang)]))
    return _c_mk((h, w), out)


def _select_xld_point(v, a, b):
    """クエリ点(正規化 a,b)を外接矩形に含む contour のみ選ぶ(filter)。

    正規化座標 ``(a, b)`` のクエリ点 ``(qy, qx) = (a*H, b*W)`` が、contour の外接軸並行矩形
    ``[min row, max row] × [min col, max col]`` に入る contour だけを残して返す。

    - ``a`` → クエリ点の行(0〜1 を高さに写す)。
    - ``b`` → クエリ点の列(0〜1 を幅に写す)。

    判定は外接矩形であって contour の内側(多角形の内外)ではないので、L 字や環状の contour では contour の外の
    点でも選ばれる。厳密な内外判定が要るなら ``contours_to_region`` で region 化して ``hx_test_region_point``。
    点に最も近い contour までの距離は ``hx_distance_pc``。該当が無ければ空の contour 集合。
    """
    h, w = _c_shape(v)
    qy, qx = a * h, b * w
    out = []
    for c in _c_cs(v):
        if c[:, 0].min() <= qy <= c[:, 0].max() and c[:, 1].min() <= qx <= c[:, 1].max():
            out.append(c)
    return _c_mk((h, w), out)


# ── 第 11 バッチ: shape-from-shading の光源推定(3D Reconstruction, image -> feature)── #
def _img_grads(v):
    return ndimage.sobel(v, axis=1), ndimage.sobel(v, axis=0)   # Ex, Ey


def _estimate_tilt_lr(v, a, b):
    """Lee-Rosenfeld: 光源方位角 tilt = atan2(<Ey>, <Ex>)(平均勾配方向)。[0,1] 正規化。

    Sobel 勾配 ``Ex``(列方向)・``Ey``(行方向)を画像全体で平均し、``tilt = arctan2(<Ey>, <Ex>)`` を
    ``(tilt / 2π) mod 1`` で [0,1) に写した ``np.float64`` を返す。Lambertian 面で光源方位(tilt)が平均勾配の方向に
    現れるという Lee-Rosenfeld の推定。

    - ``a``, ``b`` は未使用。
    - 0 が +列方向、0.25 が +行方向(画像では下)、以下その向きに回る。平均勾配がほぼ 0 だと ``arctan2(0, 0) = 0`` で
    0 に落ちる。

    勾配の生の平均を使うので、コントラストの強い部分の方向に引きずられる。表面の反射率や形状がランダムで、照明の
    傾きだけが全体の勾配の偏りを作る、という前提が要る。局所コントラストの影響を抑えた版は ``hx_estimate_tilt_zc``。
    角度値は周期量なので 0 と 1 付近は同じ方向(差を取るときは注意)。
    """
    ex, ey = _img_grads(v)
    tilt = np.arctan2(ey.mean(), ex.mean())
    return np.float64((tilt / (2 * np.pi)) % 1.0)


def _estimate_tilt_zc(v, a, b):
    """Zheng-Chellappa: 正規化勾配の平均方向で tilt を推定(局所コントラスト非依存)。

    Sobel 勾配 ``(Ex, Ey)`` を各画素で振幅 ``hypot(Ex, Ey) + 1e-9`` で割った単位ベクトルにしてから平均し、
    ``tilt = arctan2(<Ey/|E|>, <Ex/|E|>)`` を ``(tilt / 2π) mod 1`` で [0,1) に写した ``np.float64`` を返す
    (Zheng-Chellappa の tilt 推定)。

    - ``a``, ``b`` は未使用。
    - 角度の規約は ``hx_estimate_tilt_lr`` と同じ(0 が +列方向、0.25 が +行方向)。

    各画素の寄与が方向だけになるため、強いエッジや明るい部分に引きずられにくい。反面、勾配がほぼ 0 の平坦部でも
    (``1e-9`` で割った)雑音の方向が等しく 1 票を持つので、平坦な背景が広い画像では推定がぼやける。前段で
    ``gauss_filter`` を掛けて雑音の勾配を減らすと安定する。
    """
    ex, ey = _img_grads(v)
    mag = np.hypot(ex, ey) + 1e-9
    tilt = np.arctan2((ey / mag).mean(), (ex / mag).mean())
    return np.float64((tilt / (2 * np.pi)) % 1.0)


def _estimate_slant(v):
    """slant(光源天頂角)推定: 平均輝度と勾配統計から。Lambertian の <I>=albedo*cos(slant)。"""
    mu = float(np.clip(v.mean(), 0, 1))
    return float(np.arccos(np.clip(mu, 0, 1)))          # cos(slant)=<I>/albedo(albedo~1 近似)


def _estimate_sl_al_lr(v, a, b):
    """Lee-Rosenfeld: 光源の slant を推定(天頂角、0=正面〜pi/2=真横)。[0,1] 正規化。

    画像の平均輝度 ``<I>`` を反射率 1 の Lambertian 面の関係 ``<I> = albedo * cos(slant)`` に当てはめ、
    ``slant = arccos(<I>)`` を ``pi/2`` で割った ``np.float64``(0〜1)で返す。0 が正面光(平均 1.0)、1 が真横
    (平均 0)。

    - ``a``, ``b`` は未使用。
    - 平均は [0,1] に clip してから ``arccos`` に渡すので範囲外にはならない。

    実質「平均輝度が低いほど slant が大きい」という 1 対 1 の写像で、反射率は 1 と仮定している(暗い素材も
    斜光と区別できない)。勾配で補正する版は ``hx_estimate_sl_al_zc``、反射率の代理値は ``hx_estimate_al_am``。
    ``hx_shade_height_field`` の仰角 ``b`` と組み合わせて陰影を再現する際の目安に使う。
    """
    return np.float64(_estimate_slant(v) / (np.pi / 2))


def _estimate_sl_al_zc(v, a, b):
    """Zheng-Chellappa: slant を勾配エネルギーで補正して推定。

    ``hx_estimate_sl_al_lr`` と同じ ``arccos(<I>)`` の slant に、Sobel 勾配振幅の平均 ``e``(1 で頭打ち)による係数
    ``(1 + min(e, 1))`` を掛けて、``pi/2`` で割り 1 で頭打ちした ``np.float64`` を返す。「勾配が強い=斜光=slant 大」
    という向きの補正。

    - ``a``, ``b`` は未使用。

    補正係数は 1〜2 倍で、平均輝度が低く勾配も強い画像では上限 1 に張り付く。勾配振幅はテクスチャや雑音でも
    増えるので、照明以外の要因で slant が過大に出る。前段に ``gauss_filter`` を置くと雑音分の勾配は減る。
    反射率の推定は ``hx_estimate_al_am``、方位は ``hx_estimate_tilt_zc``。
    """
    ex, ey = _img_grads(v)
    e = float(np.hypot(ex, ey).mean())
    sl = _estimate_slant(v) * (1.0 + min(e, 1.0))       # 勾配が強い=斜光=slant 大
    return np.float64(min(sl / (np.pi / 2), 1.0))


def _estimate_al_am(v, a, b):
    """albedo(反射率)と ambient(環境光)の推定: albedo ~ 輝度レンジ、ここでは albedo を返す。

    画像の最大値と最小値の差 ``max(v) - min(v)`` を [0,1] に clip した ``np.float64`` を返す。
    「反射率(albedo)が高いほど陰影の明暗差が大きい」という関係を、輝度のダイナミックレンジで代用した推定。
    ambient(環境光)は計算せず返さない。

    - ``a``, ``b`` は未使用。

    最大・最小の 2 画素だけで決まるため、飽和画素や暗点が 1 つでもあれば 1 に張り付く。雑音に弱いので前段で
    ``hx_mean_shape`` や ``median_rect`` を掛ける。min-max 正規化済みの画像では常に 1 になり意味を持たない。
    slant の推定 ``hx_estimate_sl_al_lr`` は反射率 1 を仮定しており、この値で割って補正する用途が想定される。
    """
    lo, hi = float(v.min()), float(v.max())
    return np.float64(np.clip(hi - lo, 0, 1))           # 反射率の代理=輝度ダイナミックレンジ


# ── 第 12 バッチ: contour 距離/歪み + disparity→depth ───────────────────────────── #
def _add_noise_white_contour_xld(v, a, b):
    """contour 点に白色ガウス雑音を付加(std は a、固定 seed で決定的)。

    各 contour の全点座標 (row, col) に、平均 0・標準偏差 ``std`` のガウス雑音を独立に加えて返す。乱数は
    ``np.random.default_rng(12345)`` を呼ぶたびに作り直すので、同じ入力なら常に同じ雑音が出る(決定的)。

    - ``a`` → 標準偏差 ``std = a*3``(0〜3 画素。a=0 なら無変化)。
    - ``b`` は未使用。

    雑音列は contour の順番と点数に依存するため、前段で点の順序や本数が変わると同じ ``a`` でも雑音の当たり方が
    変わる。ロバスト性の検証(``hx_fit_circle_contour`` の残差がどれだけ増えるか等)や、``smooth_contours_xld`` の
    効果確認に使う。
    """
    rng = np.random.default_rng(12345)
    std = a * 3.0
    out = [c + rng.normal(0, std, c.shape) for c in _c_cs(v)]
    return _c_mk(_c_shape(v), out)


def _change_radial_distortion_contours_xld(v, a, b):
    """contour に放射歪み r' = r(1 + k r^2) を適用(k は (a-0.5) で樽/糸巻き)。

    各 contour の点を画像中心 ``(H/2, W/2)`` からの相対座標 ``d`` にし、正規化半径 ``r = |d| / (max(H, W)/2)`` に
    対して ``d' = d * (1 + k*r^2)`` と伸縮させた contour を返す(放射歪みモデルの 1 次項)。

    - ``a`` → 歪み係数 ``k = (a - 0.5) * 1.5``(-0.75〜+0.75)。``k < 0`` で点が中心に寄る(樽型)、``k > 0`` で
    外へ広がる(糸巻き型)、a=0.5 で無変化。
    - ``b`` は未使用。

    半径は画像長辺の半分で正規化しているので、画像の隅で ``r`` が 1 前後になり、``k = ±0.75`` なら隅の点は
    1.75 倍/0.25 倍まで動く。逆変換は無い(``k`` の符号を反転しても厳密には戻らない)。レンズ歪みの影響を contour
    計測(``hx_fit_circle_contour`` 等)で試す、あるいは合成的にデータを増やす用途。
    """
    h, w = _c_shape(v)
    cy, cx = h / 2, w / 2
    k = (a - 0.5) * 1.5
    scale = max(h, w) / 2
    out = []
    for c in _c_cs(v):
        d = c - [cy, cx]
        r = np.hypot(d[:, 0], d[:, 1]) / scale
        f = 1 + k * r ** 2
        out.append([cy, cx] + d * f[:, None])
    return _c_mk((h, w), out)


def _dist_ellipse_contour_points_xld(v, a, b):
    """contour 各点の当てはめ楕円境界からの最大距離を返す(点別 distance の集約=max、feature)。

    ``hx_dist_ellipse_contour`` と同じ手順(全点をまとめ、重心と共分散の固有分解から半軸 ``2*sqrt(λ)`` の楕円を
    当て、各点の正規化半径 ``rad`` を計算)で、``|rad - 1|`` の平均ではなく最大値を 1 で頭打ちした ``np.float64``
    で返す。

    - ``a``, ``b`` は未使用。
    - 点が 4 個未満なら 0.0。

    最大値なので外れ点 1 つで決まる(雑音に敏感)。値は楕円の正規化座標での差で画素距離ではない。半軸 2σ の
    取り方は境界だけの点群に対して sqrt(2) 倍大きいため、完全な楕円輪郭でも約 0.29 の下駄が乗る点は平均版と同じ。
    平均版は ``hx_dist_ellipse_contour``、外れ点を減らすなら前段に ``smooth_contours_xld``。
    """
    p = _all_pts(v)
    if len(p) < 4:
        return np.float64(0.0)
    c = p.mean(0)
    d = p - c
    w_, V = np.linalg.eigh(np.cov(d.T))
    w_ = np.clip(w_, 1e-9, None)
    loc = d @ V
    ax = 2 * np.sqrt(w_)
    rad = np.sqrt((loc[:, 0] / ax[0]) ** 2 + (loc[:, 1] / ax[1]) ** 2)
    return np.float64(min(float(np.abs(rad - 1.0).max()), 1.0))


def _dist_rectangle2_contour_points_xld(v, a, b):
    """contour 各点の最小面積外接矩形の中心からの正規化距離の平均(feature)。

    全 contour の点をまとめ、点の重心からの各点のユークリッド距離の平均を ``max(H, W)`` で割って 1 で頭打ちした
    ``np.float64`` を返す。

    - ``a``, ``b`` は未使用。
    - 点が 3 個未満なら 0.0。

    注意: 名前は最小面積外接矩形の中心からの距離だが、現実装は矩形を求めず点群の重心を中心にしている。
    点が偏っている場合(弧が欠けた輪郭など)は矩形中心と重心がずれるため、名前どおりの値にはならない。
    実質は「重心からの平均半径」で、``hx_moments_any_xld``(二乗平均)の 1 乗版にあたる。矩形そのものは
    ``hx_smallest_rect2_xld`` / ``hx_fit_rectangle2_contour``。
    """
    p = _all_pts(v)
    if len(p) < 3:
        return np.float64(0.0)
    c = p.mean(0)
    d = np.hypot(*(p - c).T)
    return np.float64(min(float(d.mean()) / max(_c_shape(v)), 1.0))


def _distance_pc(v, a, b):
    """クエリ点(正規化 a,b)から contour までの最小距離を返す(feature)。

    正規化座標 ``(a, b)`` のクエリ点 ``q = (a*H, b*W)`` から、全 contour の頂点までのユークリッド距離の最小値を
    ``max(H, W)`` で割って 1 で頭打ちした ``np.float64`` で返す。

    - ``a`` → クエリ点の行(0〜1)。
    - ``b`` → クエリ点の列(0〜1)。
    - contour の点が無ければ 0.0(点が contour 上にある場合と区別できない)。

    距離は頂点までであって線分までではないので、点の間隔が粗い contour では真の距離より最大で「点間隔の半分」程度
    大きく出る。細かい contour(``edges_sub_pix`` の 1 画素刻み)ではほぼ一致する。region までの距離は
    ``hx_distance_pr``、水平線からの距離は ``hx_distance_sc``、点を含む contour の選択は ``hx_select_xld_point``。
    """
    p = _all_pts(v)
    if len(p) == 0:
        return np.float64(0.0)
    h, w = _c_shape(v)
    q = np.array([a * h, b * w])
    return np.float64(min(float(np.hypot(*(p - q).T).min()) / max(h, w), 1.0))


def _disparity_image_to_xyz(v, a, b):
    """視差画像から深度 Z = f*baseline/disparity を計算(焦点/基線は a,b で可変)。正規化 Z。

    ``v``(0〜1)を視差 ``disp = v*63 + 0.5`` 画素相当に写し、``Z = f * baseline / disp`` を計算して min-max で
    [0,1] に正規化した画像を返す。X, Y は計算しない(Z のみ)。

    - ``a`` → 焦点距離 ``f = 200 + 600*a``。
    - ``b`` → 基線長 ``baseline = 0.05 + 0.15*b``。
    - 視差の下限を 0.5 に置いているのでゼロ除算は起きない。

    注意: ``f * baseline`` は全画素共通の定数倍で、最後の min-max 正規化で打ち消されるため、``a``, ``b`` を変えても
    出力は変わらない(実測で完全一致)。出力は実質「視差の逆数を正規化したもの」で、視差最大(``v = 1``)が 0、
    視差最小(``v = 0``)が 1 になる(近い物ほど暗い)。絶対的な深度が要る用途には使えない。逆数変換で遠方の
    量子化が粗くなるので、``v`` が小さい領域の値は不安定。
    """
    f = 200 + 600 * a
    baseline = 0.05 + 0.15 * b
    disp = v * 63.0 + 0.5                                 # [0,1] を視差[px]相当へ
    z = f * baseline / disp
    return _norm01(z)


# ── 第 13 バッチ: 点/線と region・contour の距離 + 1D エッジ対 ──────────────────── #
def _distance_pr(v, a, b):
    """クエリ点(正規化 a,b)から region までの最小距離(feature)。距離変換で。

    ``v > 0.5`` の region の補集合にユークリッド距離変換(``distance_transform_edt``)を掛け、正規化座標 ``(a, b)``
    の画素での値(その画素から最も近い region 画素までの距離)を ``max(H, W)`` で割って 1 で頭打ちした
    ``np.float64`` で返す。

    - ``a`` → 行 ``min(int(a*H), H-1)``。
    - ``b`` → 列 ``min(int(b*W), W-1)``。
    - region が空なら 1.0(「最大距離」の意味。``hx_distance_pc`` の空=0 とは逆なので注意)。

    クエリ点が region の内側なら 0。距離変換は画像全体に対して計算するので 1 点の問い合わせとしては重いが、
    値は厳密な画素間距離(``hx_distance_pc`` のような頂点近似ではない)。含むかどうかだけなら
    ``hx_test_region_point``。
    """
    reg = v > 0.5
    if not reg.any():
        return np.float64(1.0)
    dt = ndimage.distance_transform_edt(~reg)
    h, w = v.shape
    return np.float64(min(float(dt[min(int(a * h), h - 1), min(int(b * w), w - 1)]) / max(h, w), 1.0))


def _distance_sc(v, a, b):
    """水平線分(行 a*H)から contour までの最小距離(feature)。

    行 ``a*H`` の水平線から、全 contour の頂点までの縦方向の距離 ``|row - a*H|`` の最小値を ``max(H, 1)`` で割って
    1 で頭打ちした ``np.float64`` で返す。列は見ないので、線分は画像の幅いっぱいに伸びる水平線として扱う。

    - ``a`` → 水平線の行位置(0 で最上行、1 で最下行の 1 つ下)。
    - ``b`` は未使用。
    - contour の点が無ければ 0.0(線上に点がある場合と区別できない)。

    距離は頂点までなので、隣接 2 頂点の間で線を横切る contour でも 0 にはならず「近い方の頂点の行差」になる。
    点から contour までの距離は ``hx_distance_pc``、点から region までは ``hx_distance_pr``。
    """
    p = _all_pts(v)
    if len(p) == 0:
        return np.float64(0.0)
    h, w = _c_shape(v)
    return np.float64(min(float(np.abs(p[:, 0] - a * h).min()) / max(h, 1), 1.0))


def _fuzzy_measure_pairs(v, a, b):
    """中央の水平プロファイルでエッジ対(明バーの立上り境界→立下り境界)を数える(1D 計測)。

    レベル閾値の交差で境界を 1 回ずつ取る(np.gradient はステップを 2 画素に滲ませ二重計上
    するため不可)。閾値 lvl は a で可変。返り値は対の数(/10 で正規化した feature)。"""
    row = v[v.shape[0] // 2]
    lvl = 0.2 + 0.6 * a
    hi = row >= lvl
    rises = np.where(~hi[:-1] & hi[1:])[0]               # low->high 境界
    falls = np.where(hi[:-1] & ~hi[1:])[0]               # high->low 境界
    pairs = 0
    fi = 0
    for r in rises:
        while fi < len(falls) and falls[fi] <= r:
            fi += 1
        if fi < len(falls):
            pairs += 1
            fi += 1
    return np.float64(min(pairs / 10.0, 1.0))


# ── 第 14 バッチ: region 点包含判定 ──────────────────────────────────────────── #
def _test_region_point(v, a, b):
    """region が点(正規化 a=行, b=列)を含むか(1/0、test_region_point)。

    ``v > 0.5`` の region が、正規化座標 ``(a, b)`` の画素を含むかを 1.0/0.0 の ``np.float64`` で返す。

    - ``a`` → 行 ``r = min(int(a*h), h-1)``(0 で先頭行、1 で最終行)。
    - ``b`` → 列 ``c = min(int(b*w), w-1)``。

    座標は (行, 列) 順で、切り捨てで画素に丸める。1 画素の判定なので region の縁ぎりぎりでは不安定になる。
    点の周辺で判定したいときは先に ``hx_dilation1`` で region を太らせる。複数点の包含率は
    ``hx_test_region_points``、点から region までの距離は ``hx_distance_pr``。
    """
    reg = v > 0.5
    h, w = v.shape
    r, c = min(int(a * h), h - 1), min(int(b * w), w - 1)
    return np.float64(1.0 if reg[r, c] else 0.0)


def _test_region_points(v, a, b):
    """格子状の複数点のうち region に含まれる割合(test_region_points)。

    ``v > 0.5`` の region を ``step`` 画素おきの格子(``reg[::step, ::step]``、原点は (0,0))でサンプリングし、
    格子点のうち region に入っている割合を ``np.float64``(0〜1)で返す。

    - ``a`` → 格子間隔 ``step = max(2, int((0.1 + 0.3*a) * min(h, w)))``(短辺の 10%〜40%、最小 2 画素)。
    - ``b`` は未使用。
    - 格子点が 0 個なら 0.0。

    格子が細かければ region の面積率の近似になり、粗ければ「代表点がどれだけ region に落ちるか」の粗い指標になる。
    格子の原点は固定なので、region を少しずらすだけで値が飛ぶ。面積率そのものが欲しいなら region の平均値を
    取る方が正確。1 点の判定は ``hx_test_region_point``。
    """
    reg = v > 0.5
    h, w = v.shape
    step = max(2, int((0.1 + 0.3 * a) * min(h, w)))
    pts = reg[::step, ::step]
    return np.float64(float(pts.mean()) if pts.size else 0.0)


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """未カバー実 HALCON operator の genuine 実装 tier を返す。"""
    defs = [
        # (name, halcon 実名, in_sort, out_sort, fn)
        ("hx_gen_circle", "gen_circle", IMAGE, REGION, _gen_circle),
        ("hx_gen_ellipse", "gen_ellipse", IMAGE, REGION, _gen_ellipse),
        ("hx_gen_rectangle2", "gen_rectangle2", IMAGE, REGION, _gen_rectangle2),
        ("hx_gen_checker_region", "gen_checker_region", IMAGE, REGION, _gen_checker_region),
        ("hx_gen_grid_region", "gen_grid_region", IMAGE, REGION, _gen_grid_region),
        ("hx_gabor", "convol_gabor", IMAGE, IMAGE, _convol_gabor),
        ("hx_fit_surface1", "fit_surface_first_order", IMAGE, IMAGE, _fit_surface_first_order),
        ("hx_fit_surface2", "fit_surface_second_order", IMAGE, IMAGE, _fit_surface_second_order),
        ("hx_cooc_feature", "cooc_feature_image", IMAGE, FEATURE, _cooc_feature_image),
        ("hx_full_domain", "full_domain", IMAGE, REGION, _full_domain),
        # 第 2 バッチ
        ("hx_mean_shape", "mean_image_shape", IMAGE, IMAGE, _mean_image_shape),
        ("hx_close_edges", "close_edges", IMAGE, IMAGE, _close_edges),
        ("hx_close_edges_length", "close_edges_length", IMAGE, IMAGE, _close_edges_length),
        ("hx_expand_region", "expand_region", REGION, REGION, _expand_region),
        ("hx_region_to_mean", "region_to_mean", IMAGE, IMAGE, _region_to_mean),
        # 第 3 バッチ
        ("hx_nonmax_dir", "nonmax_suppression_dir", IMAGE, IMAGE, _nonmax_suppression_dir),
        ("hx_char_threshold", "char_threshold", IMAGE, REGION, _char_threshold),
        ("hx_histo_to_thresh", "histo_to_thresh", IMAGE, REGION, _histo_to_thresh),
        ("hx_gen_lowpass", "gen_lowpass", IMAGE, IMAGE, _gen_lowpass),
        ("hx_gen_highpass", "gen_highpass", IMAGE, IMAGE, _gen_highpass),
        ("hx_gen_bandpass", "gen_bandpass", IMAGE, IMAGE, _gen_bandpass),
        # 第 4 バッチ
        ("hx_erosion1", "erosion1", REGION, REGION, _erosion1),
        ("hx_dilation1", "dilation1", REGION, REGION, _dilation1),
        ("hx_opening", "opening", REGION, REGION, _opening),
        ("hx_closing", "closing", REGION, REGION, _closing),
        ("hx_dilation2", "dilation2", REGION, REGION, _dilation2),
        ("hx_gen_disc_se", "gen_disc_se", IMAGE, REGION, _gen_disc_se),
        ("hx_gen_circle_sector", "gen_circle_sector", IMAGE, REGION, _gen_circle_sector),
        ("hx_gen_ellipse_sector", "gen_ellipse_sector", IMAGE, REGION, _gen_ellipse_sector),
        ("hx_gen_empty_region", "gen_empty_region", IMAGE, REGION, _gen_empty_region),
        ("hx_clip_region_rel", "clip_region_rel", REGION, REGION, _clip_region_rel),
        ("hx_gen_bandfilter", "gen_bandfilter", IMAGE, IMAGE, _gen_bandfilter),
        ("hx_gen_derivative_filter", "gen_derivative_filter", IMAGE, IMAGE, _gen_derivative_filter),
        ("hx_fill_interlace", "fill_interlace", IMAGE, IMAGE, _fill_interlace),
        # 第 5 バッチ
        ("hx_shade_height_field", "shade_height_field", IMAGE, IMAGE, _shade_height_field),
        ("hx_plane_deviation", "plane_deviation", IMAGE, IMAGE, _plane_deviation),
        ("hx_detect_edge_segments", "detect_edge_segments", IMAGE, REGION, _detect_edge_segments),
        # 第 6 バッチ
        ("hx_gen_image_proto", "gen_image_proto", IMAGE, IMAGE, _gen_image_proto),
        ("hx_get_domain", "get_domain", IMAGE, REGION, _get_domain),
        ("hx_region_to_label", "region_to_label", IMAGE, IMAGE, _region_to_label),
        ("hx_rectangle1_domain", "rectangle1_domain", IMAGE, REGION, _rectangle1_domain),
        ("hx_lowlands", "lowlands", IMAGE, REGION, _lowlands),
        ("hx_plateaus_center", "plateaus_center", IMAGE, REGION, _plateaus_center),
        # 第 7 バッチ
        ("hx_move_region", "move_region", REGION, REGION, _move_region),
        ("hx_split_skeleton_region", "split_skeleton_region", REGION, REGION, _split_skeleton_region),
        ("hx_test_region_point", "test_region_point", REGION, FEATURE, _test_region_point),
        ("hx_test_region_points", "test_region_points", REGION, FEATURE, _test_region_points),
        # 第 8 バッチ(XLD contour)
        ("hx_sort_contours", "sort_contours_xld", CONTOUR, CONTOUR, _sort_contours_xld),
        ("hx_clip_contours", "clip_contours_xld", CONTOUR, CONTOUR, _clip_contours_xld),
        ("hx_clip_end_points", "clip_end_points_contours_xld", CONTOUR, CONTOUR, _clip_end_points_contours_xld),
        ("hx_smallest_circle_xld", "smallest_circle_xld", CONTOUR, FEATURE, _smallest_circle_xld),
        ("hx_smallest_rect1_xld", "smallest_rectangle1_xld", CONTOUR, FEATURE, _smallest_rectangle1_xld),
        ("hx_test_closed_xld", "test_closed_xld", CONTOUR, FEATURE, _test_closed_xld),
        ("hx_regress_contours", "regress_contours_xld", CONTOUR, FEATURE, _regress_contours_xld),
        ("hx_moments_any_xld", "moments_any_xld", CONTOUR, FEATURE, _moments_any_xld),
        ("hx_split_contours", "split_contours_xld", CONTOUR, CONTOUR, _split_contours_xld),
        ("hx_gen_parallel_contour", "gen_parallel_contour_xld", CONTOUR, CONTOUR, _gen_parallel_contour_xld),
        # 第 9 バッチ(XLD 形状フィット)
        ("hx_fit_circle_contour", "fit_circle_contour_xld", CONTOUR, FEATURE, _fit_circle_contour_xld),
        ("hx_fit_ellipse_contour", "fit_ellipse_contour_xld", CONTOUR, FEATURE, _fit_ellipse_contour_xld),
        ("hx_fit_rectangle2_contour", "fit_rectangle2_contour_xld", CONTOUR, FEATURE, _fit_rectangle2_contour_xld),
        ("hx_smallest_rect2_xld", "smallest_rectangle2_xld", CONTOUR, FEATURE, _smallest_rectangle2_xld),
        # 第 10 バッチ(XLD 続き)
        ("hx_crop_contours", "crop_contours_xld", CONTOUR, CONTOUR, _crop_contours_xld),
        ("hx_dist_ellipse_contour", "dist_ellipse_contour_xld", CONTOUR, FEATURE, _dist_ellipse_contour_xld),
        ("hx_test_self_intersect", "test_self_intersection_xld", CONTOUR, FEATURE, _test_self_intersection_xld),
        ("hx_union_adjacent", "union_adjacent_contours_xld", CONTOUR, CONTOUR, _union_adjacent_contours_xld),
        ("hx_polar_trans_inv", "polar_trans_contour_xld_inv", CONTOUR, CONTOUR, _polar_trans_contour_xld_inv),
        ("hx_select_xld_point", "select_xld_point", CONTOUR, CONTOUR, _select_xld_point),
        # 第 11 バッチ(shape-from-shading 光源推定)
        ("hx_estimate_tilt_lr", "estimate_tilt_lr", IMAGE, FEATURE, _estimate_tilt_lr),
        ("hx_estimate_tilt_zc", "estimate_tilt_zc", IMAGE, FEATURE, _estimate_tilt_zc),
        ("hx_estimate_sl_al_lr", "estimate_sl_al_lr", IMAGE, FEATURE, _estimate_sl_al_lr),
        ("hx_estimate_sl_al_zc", "estimate_sl_al_zc", IMAGE, FEATURE, _estimate_sl_al_zc),
        ("hx_estimate_al_am", "estimate_al_am", IMAGE, FEATURE, _estimate_al_am),
        # 第 12 バッチ
        ("hx_add_noise_contour", "add_noise_white_contour_xld", CONTOUR, CONTOUR, _add_noise_white_contour_xld),
        ("hx_radial_distort_contour", "change_radial_distortion_contours_xld", CONTOUR, CONTOUR, _change_radial_distortion_contours_xld),
        ("hx_dist_ellipse_points", "dist_ellipse_contour_points_xld", CONTOUR, FEATURE, _dist_ellipse_contour_points_xld),
        ("hx_dist_rect2_points", "dist_rectangle2_contour_points_xld", CONTOUR, FEATURE, _dist_rectangle2_contour_points_xld),
        ("hx_distance_pc", "distance_pc", CONTOUR, FEATURE, _distance_pc),
        ("hx_disparity_to_xyz", "disparity_image_to_xyz", IMAGE, IMAGE, _disparity_image_to_xyz),
        # 第 13 バッチ
        ("hx_distance_pr", "distance_pr", REGION, FEATURE, _distance_pr),
        ("hx_distance_sc", "distance_sc", CONTOUR, FEATURE, _distance_sc),
        ("hx_fuzzy_measure_pairs", "fuzzy_measure_pairs", IMAGE, FEATURE, _fuzzy_measure_pairs),
    ]
    return [Op(name, "halcon_ext", halcon, isort, osort, fn)
            for (name, halcon, isort, osort, fn) in defs]
