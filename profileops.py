# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""profileops —— 閉じた断面形状(profile)の計測。翼型・羽根・押し出し材・ガスケット。

## この族は何をする道具箱か

**閉じた輪郭を「弦」で正規化して、その断面の性質を数字にする**層です。入力は
``(N, 2)`` の ``(x, y)`` 点列(閉輪郭)、出力は厚み分布・キャンバー線・前縁半径・
後縁隙間、そして**設計形状との偏差**です。

翼型が典型ですが、原理は「細長い閉断面を弦に沿って測る」だけなので、送風ファンの
羽根、羽根車、タービン翼、押し出し材、ガスケット、板金の断面にそのまま使えます。

## なぜこの族を足したか —— 在庫を数えた結果

2026-09-06 に 2-D レジストリを走査したところ、輪郭を扱う op は **97 個**ありました
(``*_xld`` 系の生成・選択・平滑化・モーメント・当てはめ、``convex_hull``、
``distance_transform`` …)。しかし:

* **弦に沿って厚みを測る** op が無い。``get_region_thickness`` は領域の太さで、
  弦方向の分布ではない。
* **キャンバー線**(上面と下面の中線)を出す op が無い。
* **前縁半径**を出す op が無い。``hx_fit_circle_contour`` はあるが、輪郭の
  どの部分を前縁と呼ぶかを決める層が無い。
* **輪郭同士の符号つき偏差**が無い。``hx_dist_ellipse_contour`` は楕円との距離、
  ``distance_transform`` はラスタ。任意の 2 本の輪郭の法線方向のずれは出せない。

つまり「形はいくらでも作れて選べるのに、**断面として測る**層が空いていた」。

## 正しさの確かめ方 —— 閉形式と、既知の欠陥の注入

**NACA 4 桁翼型は閉形式で定義されている**ので、この族の真値は計算できます
(``tests/test_profileops.py``):

=====================  ===========================  ==========================
量                     NACA 4 桁の閉形式            実測(NACA 2412、点数 801)
=====================  ===========================  ==========================
最大厚み               ``t`` (下 2 桁 / 100)        0.12006(x = 0.300)
最大キャンバー         ``m`` (1 桁目 / 100)         0.01882(x = 0.415)★定義差
前縁半径               ``1.1019 t^2`` = 0.01587     0.01594(``frac=0.001``)
後縁隙間               既定係数なら開く             0.00390
=====================  ===========================  ==========================

★ キャンバーが 6 % 低いのは**定義の差**で実装の誤りではありません
(:func:`profile_camber` の表を参照)。対称翼 NACA 0012 では 0.00001 になることを
確かめてあり、**対称翼で 0 にならないかどうか**がこの族の一番効く検査でした ——
実際、後縁が開いていると弦が傾いて 0.001257 のキャンバーが出る、という
バグをそれで見つけています。

さらに **UIUC の実データとも突き合わせてあります** —— 公開されている
``naca2412.dat`` の上面と、閉形式で生成した上面の差は**最大 7.3e-4 翼弦**
(RMS 2.9e-4)。UIUC 側が 35 点の粗い表で丸められていることを考えれば妥当な一致で、
「閉形式が真値として使える」ことの裏づけになります。

**もう一段大事なのが、既知の欠陥を注入して測り返すこと**(:func:`profile_perturb`)。
0.001 翼弦だけ厚くした形を作り、``profile_deviation`` がそれを 0.001 として
返すかを見ます。これをやらない形状検査は、**静かに合格を出します**。

## 位置合わせが偏差を吸収する(この族でいちばん危ない罠)

測った形と設計形を比べる前に位置を合わせますが、**自由に合わせると欠陥が消えます**。
わずかに傾いた測定を「傾き」ではなく「厚みの偏り」として合わせ込む、あるいは
逆に本物の厚み増を「拡大」として吸収してしまう。

:func:`profile_align` は自由度を**明示的に選ばせます**(``"rigid"`` = 回転 + 並進、
``"chord"`` = 弦の両端だけを合わせる、``"none"`` = 合わせない)。既定は
``"chord"`` —— スケールを推定しないので、厚みや大きさの誤差が**吸収されない**。

実測 1: 既知の 0.002 翼弦の**一様な厚み増**は、どの合わせ方でも平均 0.00199 と
して戻ります(3 度の回転と並進を掛けたあとでも同じ)。ここは安心してよい。

実測 2 —— **欠陥が合わせの基準そのものに乗っていると話が変わります**。前縁を
0.003 削った形を比べると:

===============  ==================  ==============  ==================
合わせ方         最悪の偏差          その位置        前縁側の最悪
===============  ==================  ==============  ==================
``"chord"``      -0.00283            **x = 1.000**   -0.00096
``"rigid"``      -0.00166            x = 0.009       -0.00166
``"none"``       -0.00309            x = 0.001       -0.00309
===============  ==================  ==============  ==================

前縁を削ると前縁の位置そのものが動くので、``"chord"``(前縁と後縁を合わせる)は
**損失を反対の端へ移し**、前縁での落ち込みを 3 分の 1 に見せます。``"rigid"``
(全点の最小二乗)は場所は正しく出しますが、ずれを全体へ散らして半分に見せます。
既に同じ座標系にある(``"none"``)ときだけ、注入した 0.003 がそのまま出ます。

**教訓**: 欠陥が基準に乗る場所(前縁・後縁・取り付け面)を検査するときは、
合わせの自由度をその場所から**外して**取るか、``"none"`` で比べられるよう
測定側の座標系を先に決めること。相似(スケール推定)を提供しないのも同じ理由で、
大きさの誤差そのものを吸収してしまいます。

## 規約(取り違えると静かに間違う)

* 輪郭は ``(N, 2)`` の ``(x, y)``。**行と列ではありません** —— この repo には
  ``(row, col)`` の規約(``keypoints`` / ``fit_transform``)と ``(x, y)`` の規約
  (``pairs`` / ``filled_polygon``)が両方あり、混ぜると転置した形が出ます。
  こちらは ``pairs`` と同じ ``(x, y)``。
* 一筆書きで、**閉じているか、ほぼ閉じている**こと。端点間の隙間が形の広がりの
  20 % を超えると :func:`profile_sides` が拒否します(NACA の開いた後縁は
  0.25 % なので通ります)。**「1 価の関数だから拒否される」ではありません** ——
  点列は閉じれば多角形になり、厚みも面積も出てしまうからです。
* 弦は**最も離れた 2 点**から出発し、**後縁を隙間の中点に取り直して**から
  前縁を決め直します(後縁が開いていると角の片方を拾って弦が傾くため)。
  前縁と後縁の区別は「少し入ったところが太いほう」—— 曲率ではありません
  (後縁の尖りのほうが曲率は大きく出ます)。
* 正規化後は弦長 1、前縁が原点、弦が +x 方向。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "ALIGN_MODES", "PERTURB_KINDS", "NACA_LE_RADIUS_COEFF",
    "profile_synth_naca4", "profile_resample", "profile_chord_frame",
    "profile_normalise", "profile_sides", "profile_thickness", "profile_camber",
    "profile_leading_edge_radius", "profile_trailing_edge_gap",
    "profile_align", "profile_deviation", "profile_perturb",
]

#: 位置合わせの自由度。**相似(スケール推定)は意図的に提供しない** ——
#: 大きさの誤差そのものを吸収してしまい、実測で厚み増の 2 割が消えた。
#:
#: * ``"chord"``(既定) —— 弦の両端(前縁・後縁)だけを合わせる。回転・並進のみ。
#: * ``"rigid"`` —— 全点の最小二乗による回転 + 並進(Umeyama、スケール固定)。
#: * ``"none"`` —— 合わせない(既に同じ座標系にある場合)。
ALIGN_MODES = ("chord", "rigid", "none")

#: 注入できる既知の欠陥。**検出力を測るため**にあるので、量が閉形式で分かるもの
#: だけを置く。
#:
#: * ``"thicken"`` —— 法線方向に一様に厚くする(``amount`` 翼弦)。
#: * ``"le_erosion"`` —— 前縁付近だけを削る(風車翼の前縁侵食)。
#: * ``"waviness"`` —— 弦方向に正弦波のうねりを法線方向へ加える。
#: * ``"twist"`` —— 後縁側を回す(ねじれ)。
PERTURB_KINDS = ("thicken", "le_erosion", "waviness", "twist")

#: NACA 4 桁の前縁半径の閉形式係数。``r_le = 1.1019 * t^2``(``t`` は最大厚み比)。
#: 出典は NACA の翼型定義(Abbott & von Doenhoff, Theory of Wing Sections)。
NACA_LE_RADIUS_COEFF = 1.1019

_EPS = 1e-12


# =========================================================================
# 入力の検証(fail-closed)
# =========================================================================

def _require_closed(a, name, tol=0.2):
    """端点が離れすぎていたら「これは閉じた断面ではない」と断る。

    ★ 当初 docstring に「1 価の関数(MTF 曲線など)は下面が取れないので拒否
    される」と書いたが、**嘘だった** —— 点列を閉じれば多角形になり、面積も
    厚みも出る(実測で指数関数の曲線が素通りした)。実際に効く判定は
    「与えられた並びが**もともと閉じているか**」で、端点間の隙間を弦で割って見る。
    NACA の開いた後縁は 0.25 %、閉じ忘れた曲線は 100 % 前後になる。
    """
    gap = float(np.hypot(*(a[0] - a[-1])))
    span = float(np.max(np.hypot(*(a - a.mean(axis=0)).T))) * 2.0
    if span > _EPS and gap / span > tol:
        raise ValueError(
            f"{name} does not look like a closed section: its first and last points are "
            f"{gap / span:.0%} of the extent apart (an open, single-valued curve such as a "
            "spectrum cannot be measured as a section). Close the contour first")


def _contour(c, name="contour", min_pts=8, closed=False):
    a = np.asarray(c, dtype=np.float64)
    if a.ndim != 2 or a.shape[1] != 2:
        raise ValueError(
            f"{name} must be an (N, 2) array of (x, y) points, got shape {a.shape}. "
            "This family uses the (x, y) convention (like `pairs` / filled_polygon), "
            "not (row, col)")
    if a.shape[0] < min_pts:
        raise ValueError(f"{name} needs at least {min_pts} points, got {a.shape[0]}")
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} contains non-finite coordinates")
    if closed:
        _require_closed(a, name)
    return a


def _choice(v, name, allowed):
    if v not in allowed:
        raise ValueError(f"{name} must be one of {allowed}, got {v!r}")
    return v


def _positive(v, name):
    x = float(v)
    if not np.isfinite(x) or x <= 0:
        raise ValueError(f"{name} must be a finite positive number, got {v}")
    return x


# =========================================================================
# 1. 生成 —— 真値は閉形式から
# =========================================================================

def profile_synth_naca4(code="2412", n=161, closed_te=False):
    """NACA 4 桁翼型を閉形式で生成する。返りは ``(N, 2)`` の一筆書き。

    ``code`` は 4 桁(例 ``"2412"`` = キャンバー 2 %、位置 40 %、厚み 12 %)。
    点は前縁を密にするために余弦分布で置く。

    ``closed_te`` は後縁を閉じる係数を使うかどうか。**既定は歴史的な係数**
    (0.1015)で、後縁がわずかに開く。閉じる版は 0.1036。どちらを使ったかで
    後縁付近の計測が変わるので、真値として使うなら固定して書き残すこと。

    Returns:
        ``(2*n-1, 2)``。後縁 → 上面 → 前縁 → 下面 → 後縁 の順(Selig 流)。
    """
    s = str(code).strip()
    if len(s) != 4 or not s.isdigit():
        raise ValueError(f"code must be 4 digits like '2412', got {code!r}")
    npts = int(n)
    if npts < 16:
        raise ValueError(f"n must be >= 16, got {n}")
    m = int(s[0]) / 100.0
    p = int(s[1]) / 10.0
    t = int(s[2:]) / 100.0
    if t <= 0:
        raise ValueError(f"thickness digits must be > 0, got {code!r}")
    a4 = -0.1036 if closed_te else -0.1015
    beta = np.linspace(0.0, np.pi, npts)
    x = 0.5 * (1.0 - np.cos(beta))                       # 前縁を密に
    yt = 5.0 * t * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2
                    + 0.2843 * x ** 3 + a4 * x ** 4)
    if m > 0 and 0 < p < 1:
        yc = np.where(x < p,
                      m / p ** 2 * (2 * p * x - x ** 2),
                      m / (1 - p) ** 2 * ((1 - 2 * p) + 2 * p * x - x ** 2))
        dyc = np.where(x < p,
                       2 * m / p ** 2 * (p - x),
                       2 * m / (1 - p) ** 2 * (p - x))
    else:
        yc = np.zeros_like(x)
        dyc = np.zeros_like(x)
    th = np.arctan(dyc)
    xu, yu = x - yt * np.sin(th), yc + yt * np.cos(th)
    xl, yl = x + yt * np.sin(th), yc - yt * np.cos(th)
    upper = np.column_stack([xu[::-1], yu[::-1]])        # 後縁 → 前縁
    lower = np.column_stack([xl[1:], yl[1:]])            # 前縁 → 後縁
    return np.vstack([upper, lower])


# =========================================================================
# 2. 弦の枠と正規化
# =========================================================================

def profile_chord_frame(contour):
    """弦(最も離れた 2 点)を見つける。返りは dict。

    翼型の慣行どおり、**最も離れた 2 点**を前縁・後縁とみなす。どちらが前縁かは
    **その点の近傍の曲率が大きいほう**で決める(前縁は丸く、後縁は尖る)。

    Returns:
        dict: ``le`` / ``te``(座標)、``le_index`` / ``te_index``、
        ``chord``(長さ)、``angle_deg``(弦の向き)。
    """
    c = _contour(contour)
    # 凸包の点だけで総当たりすれば十分(最遠点対は必ず凸包上にある)
    hull = _convex_hull(c)
    d2 = np.sum((hull[:, None, :] - hull[None, :, :]) ** 2, axis=-1)
    i, j = np.unravel_index(int(np.argmax(d2)), d2.shape)
    pa, pb = hull[i], hull[j]
    ia = int(np.argmin(np.sum((c - pa) ** 2, axis=1)))
    ib = int(np.argmin(np.sum((c - pb) ** 2, axis=1)))
    # 前縁 = **少し入ったところが太いほう**(後縁は尖って薄い)。
    # ★ 最初は「曲率が大きいほう」で書いて、NACA 2412 で**後縁を前縁と判定した**。
    #    3 点円の曲率は、上下面がほぼ接する後縁で前縁の丸みより大きく出る ——
    #    「前縁は丸い」という直観が、輪郭上の 3 点で測ると逆転する。
    if _girth_near(c, c[ia], c[ib]) >= _girth_near(c, c[ib], c[ia]):
        le_i, te_i = ia, ib
    else:
        le_i, te_i = ib, ia
    # ★ 後縁が開いていると、最遠 2 点は後縁の**角の片方**を拾って弦が傾く。
    #   隙間の中点に取り直してから、前縁を「その中点から最も遠い点」に決める。
    #   これをやらないと対称翼でもキャンバーが後縁の半隙間ぶん出る(実測 0.001257)。
    te = _trailing_edge_midpoint(c, c[te_i], c[le_i])
    le_i = int(np.argmax(np.sum((c - te) ** 2, axis=1)))
    le = c[le_i]
    te_i = int(np.argmin(np.sum((c - te) ** 2, axis=1)))
    v = te - le
    return {"le": le, "te": te, "le_index": le_i, "te_index": te_i,
            "chord": float(np.hypot(*v)),
            "angle_deg": float(np.degrees(np.arctan2(v[1], v[0])))}


def _trailing_edge_midpoint(c, te_pt, le_pt, band=0.005):
    """後縁の隙間の中点。開いていなければ ``te_pt`` とほぼ同じ点を返す。

    弦方向に後縁から ``band``(弦比)だけ入った帯の中で、弦に垂直な向きの
    最大と最小を平均する。帯に点が 1 つしか無ければそのまま返す。
    """
    axis = te_pt - le_pt
    ln = np.hypot(*axis)
    if ln < _EPS:
        return te_pt
    axis = axis / ln
    perp = np.array([-axis[1], axis[0]])
    rel = c - te_pt
    along = rel @ axis                       # 後縁側が 0、前縁へ向かって負
    sel = along >= -band * ln
    if np.count_nonzero(sel) < 2:
        return te_pt
    across = rel[sel] @ perp
    mid = 0.5 * (float(np.max(across)) + float(np.min(across)))
    # 帯の中で最も後縁寄りの弦方向位置に、中点の横位置を載せる
    return te_pt + mid * perp


def _girth_near(c, end, other, frac=0.05):
    """``end`` から弦方向に ``frac`` だけ入った帯での、弦に垂直な広がり。

    前縁側は断面が太いので大きく、後縁側は尖っているので小さい。**閉形式で
    決まる量ではなく形の性質**なので、比較にだけ使い、値そのものは返さない。
    """
    axis = other - end
    ln = np.hypot(*axis)
    if ln < _EPS:
        return 0.0
    axis = axis / ln
    perp = np.array([-axis[1], axis[0]])
    rel = c - end
    along = rel @ axis
    band = (along >= 0.0) & (along <= frac * ln)
    if not np.any(band):
        return 0.0
    across = rel[band] @ perp
    return float(np.max(across) - np.min(across))


def _cross2(a, b):
    """2 次元の外積(スカラ)。``np.cross`` の 2 次元用法は NumPy 2.0 で非推奨 ——
    テスト 1 回で 29 万件の警告が出たので自前で書く。"""
    return float(a[0] * b[1] - a[1] * b[0])


def _convex_hull(pts):
    """単調鎖法(Andrew monotone chain)。``convex_hull`` op は 3-D 点群向け。"""
    p = pts[np.lexsort((pts[:, 1], pts[:, 0]))]
    if len(p) < 3:
        return p

    def half(seq):
        out = []
        for q in seq:
            while len(out) >= 2 and _cross2(out[-1] - out[-2], q - out[-2]) <= 0:
                out.pop()
            out.append(q)
        return out

    return np.array(half(p)[:-1] + half(p[::-1])[:-1])


def profile_normalise(contour):
    """弦長 1・前縁が原点・弦が +x になるよう回転と並進で正規化する。

    **スケールは弦長でしか変えない**(形を歪めない)。返りは正規化した輪郭。

    手順: ``profile_chord_frame`` で前縁 ``le``・後縁 ``te``(開いた後縁は隙間の
    中点)・弦長 ``chord``・弦の向き ``angle_deg`` を求め、
    ``((contour - le) @ R(-angle).T) / chord`` を返す。回転・並進・一様スケールの
    相似変換だけで、点の数と順序は保つ(再標本化しない)。

    - ``contour``: ``(N, 2)`` の **(x, y)**、8 点以上、有限。``(row, col)`` を渡すと
      弦は見つかるが上下が入れ替わる(例外は出ない)。閉じているかはここでは
      検査しない(``profile_sides`` 以降が検査する)。
    - 返り値: ``(N, 2)`` float64。前縁が ``(0, 0)``、後縁が ``(1, 0)`` 付近、
      ``x`` は ``[0, 1]`` の弦比。``y`` の符号(上面が正か負か)は入力の周回方向
      で決まり、反転はしない。
    - 失敗: ``ValueError``(形、点数不足、非有限、弦長が 0 = 全点一致)。

    前縁・後縁の判定は「最遠点対のうち、少し内側で断面が太いほう = 前縁」なので、
    前後で太さが同じ対称な断面(楕円など)では前後が入れ替わることがある。
    ``profile_sides`` / ``profile_thickness`` / ``profile_camber`` は内部でこれを呼ぶ。
    """
    c = _contour(contour)
    fr = profile_chord_frame(c)
    ch = fr["chord"]
    if ch < _EPS:
        raise ValueError("chord length is zero; the contour degenerates to a point")
    a = np.radians(-fr["angle_deg"])
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    return ((c - fr["le"]) @ rot.T) / ch


def profile_resample(contour, n=200, kind="arclength"):
    """輪郭を等間隔に取り直す。``kind`` は ``"arclength"`` のみ(現状)。

    点の密度が場所で違うと、厚みやキャンバーの当てはめが密なところに引きずられる。
    比較する 2 本は**同じ取り方**で取り直してから比べること。
    """
    c = _contour(contour)
    if kind != "arclength":
        raise ValueError(f"kind must be 'arclength', got {kind!r}")
    m = int(n)
    if m < 8:
        raise ValueError(f"n must be >= 8, got {n}")
    closed = np.vstack([c, c[:1]]) if np.hypot(*(c[0] - c[-1])) > _EPS else c
    seg = np.hypot(*np.diff(closed, axis=0).T)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    if s[-1] < _EPS:
        raise ValueError("contour has zero length")
    target = np.linspace(0.0, s[-1], m + 1)[:-1]
    return np.column_stack([np.interp(target, s, closed[:, 0]),
                            np.interp(target, s, closed[:, 1])])


# =========================================================================
# 3. 断面としての計測
# =========================================================================

def profile_sides(contour, n=101, normalise=True):
    """上面・下面を弦方向の関数として取り出す。返りは dict。

    弦を ``n`` 等分し、各位置で輪郭と交わる上下の点を線形補間で拾う。

    **開いた曲線はここで拒否される** —— 1 価の関数(MTF 曲線のような)を渡すと
    下面が取れないので、「これは閉じた断面ではない」と明示して落とす。型ではなく
    検証で守っている(``pairs`` は関数データにも閉輪郭にも使われる語彙なので、
    型を分けると既存の輪郭生成 op から繋がらなくなる)。

    Returns:
        dict: ``x``(``(n,)``)、``upper`` / ``lower``(``(n,)``)、``normalised``。
    """
    _contour(contour, closed=True)                # 断面であることを先に確かめる
    c = profile_normalise(contour) if normalise else _contour(contour)
    m = int(n)
    if m < 5:
        raise ValueError(f"n must be >= 5, got {n}")
    xs = np.linspace(0.0, 1.0, m)
    up = np.full(m, np.nan)
    lo = np.full(m, np.nan)
    seg = np.vstack([c, c[:1]])
    x0, y0 = seg[:-1, 0], seg[:-1, 1]
    x1, y1 = seg[1:, 0], seg[1:, 1]
    for k, xv in enumerate(xs):
        hit = ((x0 <= xv) & (xv <= x1)) | ((x1 <= xv) & (xv <= x0))
        if not np.any(hit):
            continue
        dx = x1[hit] - x0[hit]
        tt = np.where(np.abs(dx) < _EPS, 0.0, (xv - x0[hit]) / np.where(np.abs(dx) < _EPS, 1.0, dx))
        ys = y0[hit] + tt * (y1[hit] - y0[hit])
        up[k], lo[k] = float(np.max(ys)), float(np.min(ys))
    inner = slice(1, -1)
    if not np.any(np.isfinite(up[inner]) & np.isfinite(lo[inner])):
        raise ValueError(
            "no chordwise station has both an upper and a lower surface — this is not a "
            "closed profile (an open, single-valued curve such as a spectrum cannot be "
            "measured as a section)")
    if np.nanmax(up[inner] - lo[inner]) < _EPS:
        raise ValueError("upper and lower surfaces coincide; the contour has no thickness")
    return {"x": xs, "upper": up, "lower": lo, "normalised": bool(normalise)}


def profile_thickness(contour, n=101):
    """厚み分布 ``t(x)``。返りは ``(n, 2)`` の ``(x, t)``。

    ``pairs`` として返すので、``pairs_to_signal`` や ``plot_series`` へそのまま
    渡せる。最大厚みとその位置は :func:`profile_thickness_stats` ではなく
    返り値から取る(``t`` の最大 = 最大厚み比)。
    """
    s = profile_sides(contour, n)
    t = s["upper"] - s["lower"]
    return np.column_stack([s["x"], np.where(np.isfinite(t), t, 0.0)])


def profile_camber(contour, n=101):
    """キャンバー線(上下面の中線)。返りは ``(n, 2)`` の ``(x, yc)``。

    ★**定義の差を承知で使うこと**。ここが返すのは「弦の各位置での上下面の中点」
    で、NACA が翼型を**作るときに使う**キャンバー線(厚みを法線方向に載せる前の
    中心線)とは厳密には別物です。加えて弦の取り方も違う —— 幾何的な弦は
    「後縁の中点から最も遠い点」を前縁とするので、キャンバーのある翼では
    生成座標の原点からわずかにずれ、弦が 0.1 度ほど傾きます。

    実測(閉形式の最大キャンバー比 対 本 op の返り):

    ==========  ==========  ==========  ==========
    翼型        閉形式      実測        比
    ==========  ==========  ==========  ==========
    NACA 0012   0.0000      0.00001     ——
    NACA 2412   0.0200      0.01882     0.94
    NACA 4412   0.0400      0.03786     0.95
    ==========  ==========  ==========  ==========

    **対称翼で 0 になること**は確認済み(0.00001)。有翼で 5-6 % 低く出るのは
    上の定義差で、実装の誤りではありません。設計値と比べるときは、同じ定義で
    測った基準形状(``profile_synth_naca4`` の出力)と比べること ——
    :func:`profile_deviation` はまさにそれをします。
    """
    s = profile_sides(contour, n)
    yc = 0.5 * (s["upper"] + s["lower"])
    return np.column_stack([s["x"], np.where(np.isfinite(yc), yc, 0.0)])


def profile_leading_edge_radius(contour, frac=0.001, n_fit=24):
    """前縁半径(翼弦比)。前縁近傍の点に円を当てはめる。

    ``frac`` は前縁から弦方向にどこまでを「前縁付近」とみなすか。**この値で
    答えが変わる**。鼻先は円だが、少し離れると円ではないので、窓を広げると
    系統的に**過大**になる。NACA 4 桁の閉形式 ``1.1019 * t^2`` と突き合わせた
    実測(点数 4001 で生成):

    ==========  ==========  ==========  ==========  ==========
    frac        NACA 0012   NACA 2412   NACA 0021   NACA 0008
    ==========  ==========  ==========  ==========  ==========
    閉形式      0.01587     0.01587     0.04859     0.00705
    0.001       0.01590     0.01594     0.04780     0.00730
    0.005       0.01708     0.01716     0.04801     0.00870
    0.01        0.01872     0.01880     0.04897     0.01042
    0.03        0.02517     0.02526     0.05412     0.01688
    ==========  ==========  ==========  ==========  ==========

    ★ 既定は **0.001**。最初 0.03 を既定にしていて、閉形式の **1.6 倍**の値を
    返していた(「1 % 以内」と docstring に書いたのは確かめる前の推測だった)。
    厚い翼(0021)ほど鈍いので窓の影響が小さく、薄い翼(0008)ほど敏感。

    実データのように点が疎な輪郭では、この窓に点が 5 つ入らないことがある ——
    そのときは自動で等弧長に取り直してから当てはめる。
    """
    c = profile_normalise(contour)
    f = _positive(frac, "frac")
    near = c[c[:, 0] <= f]
    if len(near) < 5:
        c = profile_resample(c, max(int(n_fit / max(f, 1e-3)), 200))
        near = c[c[:, 0] <= f]
    if len(near) < 5:
        raise ValueError(
            f"only {len(near)} points within frac={f} of the leading edge; "
            "resample the contour or widen frac")
    return float(_fit_circle(near)[2])


def _fit_circle(p):
    """代数的な円当てはめ(Kasa)。返りは ``(cx, cy, r)``。"""
    x, y = p[:, 0], p[:, 1]
    A = np.column_stack([x, y, np.ones_like(x)])
    b = x ** 2 + y ** 2
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    cx, cy = sol[0] / 2.0, sol[1] / 2.0
    r = np.sqrt(max(sol[2] + cx ** 2 + cy ** 2, 0.0))
    return cx, cy, r


def profile_trailing_edge_gap(contour, n=201):
    """後縁の開き(翼弦比)。上面と下面の後縁端の距離。

    NACA 4 桁の既定係数(-0.1015)は後縁を**わずかに開く**ので、0 にならないのが
    正しい。閉じる係数(-0.1036)なら 0 に近づく。

    手順: ``profile_sides(contour, n)``(弦長 1 に正規化し、弦を ``n`` 等分した各
    位置で上面・下面を線形補間)を取り、**``x = 1`` 側から見て上下両方が取れた
    最初の位置**の ``upper - lower`` を返す。単位は弦長比(無次元)。

    - ``contour``: ``(N, 2)`` の **(x, y)**、8 点以上、有限、**閉じた断面**であること
      (端点間の隙間が全体の 20 % を超えると「閉じていない」として ``ValueError``)。
    - ``n``: 弦の分割数、5 以上(既定 201)。**粗いと後縁から手前の位置で測る**ことに
      なり、テーパした後縁では実際の隙間より大きく出る。細かいほど後縁に寄る。
    - 返り値: float(弦長比)。閉じた後縁で ≈ 0、NACA 2412 の既定係数で 0.0025 程度。
      符号は上面の ``y`` が下面より大きい限り正。
    - 失敗: ``ValueError``(形、閉じていない、上下が取れる位置が 1 つも無い、
      上下面が一致して厚み 0)。

    ``profile_thickness`` の末尾の値と同じ量を「後縁の 1 点だけ」で返すもの。
    ``profile_synth_naca4(closed_te=True)`` で作った真値と比べれば検算になる。
    """
    s = profile_sides(contour, n)
    for k in range(len(s["x"]) - 1, -1, -1):
        if np.isfinite(s["upper"][k]) and np.isfinite(s["lower"][k]):
            return float(s["upper"][k] - s["lower"][k])
    raise ValueError("no chordwise station has both surfaces near the trailing edge")


# =========================================================================
# 4. 比べる —— 位置合わせと偏差
# =========================================================================

def profile_align(measured, reference, mode="chord"):
    """測った輪郭を設計輪郭へ合わせる。返りは ``(aligned, info)``。

    ``mode`` は :data:`ALIGN_MODES`。**相似(スケール推定)は提供しない** ——
    大きさの誤差そのものを吸収してしまうため(モジュール docstring の実測表)。

    Returns:
        ``(aligned (N, 2), info)``。``info`` は ``mode`` / ``angle_deg`` /
        ``translation`` / ``scale``(常に 1.0。**推定していないことの明示**)。
    """
    m = _contour(measured, "measured")
    r = _contour(reference, "reference")
    _choice(mode, "mode", ALIGN_MODES)
    if mode == "none":
        return m.copy(), {"mode": mode, "angle_deg": 0.0,
                          "translation": np.zeros(2), "scale": 1.0}
    if mode == "chord":
        fm, fr = profile_chord_frame(m), profile_chord_frame(r)
        a = np.radians(fr["angle_deg"] - fm["angle_deg"])
        rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
        out = (m - fm["le"]) @ rot.T + fr["le"]
        return out, {"mode": mode, "angle_deg": float(np.degrees(a)),
                     "translation": fr["le"] - fm["le"], "scale": 1.0}
    # rigid: 対応は最近傍でなく**弧長のパラメータ**で取る(点数が違ってよい)
    k = max(len(m), len(r), 64)
    mm, rr = profile_resample(m, k), profile_resample(r, k)
    mm = _roll_to_leading_edge(mm)
    rr = _roll_to_leading_edge(rr)
    cm, cr = mm.mean(axis=0), rr.mean(axis=0)
    H = (mm - cm).T @ (rr - cr)
    u, _, vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(vt.T @ u.T))
    rot = vt.T @ np.diag([1.0, d]) @ u.T
    out = (m - cm) @ rot.T + cr
    return out, {"mode": mode,
                 "angle_deg": float(np.degrees(np.arctan2(rot[1, 0], rot[0, 0]))),
                 "translation": cr - cm, "scale": 1.0}


def _roll_to_leading_edge(c):
    i = profile_chord_frame(c)["le_index"]
    return np.roll(c, -i, axis=0)


def profile_deviation(measured, reference, n=200, align="chord", oversample=8):
    """設計形状からの**符号つき法線方向のずれ**。返りは dict。

    正が「太い側(外向き)」、負が「痩せた側」。設計輪郭の外向き法線を基準にする。

    Args:
        measured / reference: ``(N, 2)`` の閉輪郭。
        n: 比較に使う等弧長の点数(両方を取り直す)。
        align: :data:`ALIGN_MODES`。
        oversample: 相手側を基準の何倍の密度で取り直すか(既定 8)。
            折れ線が弧を切る分だけ偏差に床ができるので、**相手側は細かく**取る。
    Returns:
        dict: ``points``(基準側の点、``(n, 2)``)、``deviation``(``(n,)``)、
        ``max`` / ``min`` / ``rms`` / ``mean``、``align``。
    """
    ref = profile_resample(_contour(reference, "reference"), n)
    # ★ 合わせる前に**同じ取り方で取り直す**。弦の枠(とくに後縁の中点)は点の
    #   置き方にわずかに依存するので、生の輪郭と取り直した輪郭を突き合わせると、
    #   同一の形でも 0.02 度の回転と 7.8e-4 の並進が入る —— それがそのまま
    #   偏差の床(実測 rms 6.05e-4)になっていた。比べるものは同じ土俵に載せる。
    mea_in = profile_resample(_contour(measured, "measured"), n)
    mea, info = profile_align(mea_in, ref, align)
    # 相手側は**細かく**取り直す。基準点から折れ線への距離は、折れ線が弦で
    # 弧を切る分(サジッタ)だけ内側に出る —— 曲率の大きい前縁で効く。
    # 実測: 同じ形どうしで n=400 のとき床が 6.05e-4、8 倍に取ると 1.0e-5。
    mea = profile_resample(mea, oversample * n)
    nrm = _outward_normals(ref)
    # ★ 点対点ではなく**点対折れ線**で測る。等弧長に取り直しても両者の位相は
    #   一致しないので、対応を番号で取ると位相のずれがそのまま偏差になる
    #   (実測: 同じ形を自分と比べて rms 6.05e-4 —— 検出したい欠陥と同じ桁)。
    dev = _signed_distance_to_polyline(ref, nrm, mea)
    return {"points": ref, "deviation": dev, "normals": nrm,
            "max": float(np.max(dev)), "min": float(np.min(dev)),
            "rms": float(np.sqrt(np.mean(dev ** 2))), "mean": float(np.mean(dev)),
            "align": info}


def _signed_distance_to_polyline(points, normals, poly):
    """各 ``points`` から閉じた折れ線 ``poly`` への最短距離(法線の向きで符号)。

    線分ごとに射影して最近点を求め、その変位を基準側の外向き法線へ投影する。
    番号の対応を使わないので、**点の並びや位相に依らない**。
    """
    seg0 = poly
    seg1 = np.roll(poly, -1, axis=0)
    d = seg1 - seg0                                   # (m, 2)
    ll = np.einsum("ij,ij->i", d, d)
    ll = np.where(ll < _EPS, 1.0, ll)
    rel = points[:, None, :] - seg0[None, :, :]       # (n, m, 2)
    t = np.clip(np.einsum("nmj,mj->nm", rel, d) / ll, 0.0, 1.0)
    close = seg0[None, :, :] + t[:, :, None] * d[None, :, :]
    diff = close - points[:, None, :]
    dist2 = np.einsum("nmj,nmj->nm", diff, diff)
    k = np.argmin(dist2, axis=1)
    best = diff[np.arange(len(points)), k]
    return np.einsum("ij,ij->i", best, normals)


def _outward_normals(c):
    """閉輪郭の外向き単位法線。巻き方向を面積の符号で判定して揃える。"""
    nxt = np.roll(c, -1, axis=0)
    prv = np.roll(c, 1, axis=0)
    tan = nxt - prv
    ln = np.hypot(tan[:, 0], tan[:, 1])
    ln = np.where(ln < _EPS, 1.0, ln)
    nrm = np.column_stack([tan[:, 1], -tan[:, 0]]) / ln[:, None]
    area = 0.5 * np.sum(c[:, 0] * nxt[:, 1] - nxt[:, 0] * c[:, 1])
    return nrm if area > 0 else -nrm


# =========================================================================
# 5. 既知の欠陥を注入する —— 検出力を測るため
# =========================================================================

def profile_perturb(contour, kind="thicken", amount=0.001, extent=0.1, cycles=6.0):
    """既知の量の欠陥を入れた輪郭を返す。:data:`PERTURB_KINDS`。

    **これが無い形状検査は、静かに合格を出す**。0.001 翼弦の厚み増を入れて、
    検出器がそれを 0.001 として返すかを確かめるために使う。

    Args:
        contour: 元の輪郭。
        kind: 欠陥の種類。
        amount: 大きさ(翼弦比)。``"twist"`` だけは度。
        extent: ``"le_erosion"`` が及ぶ弦方向の範囲。
        cycles: ``"waviness"`` の波数。
    """
    c = _contour(contour)
    _choice(kind, "kind", PERTURB_KINDS)
    amt = float(amount)
    nrm = _outward_normals(c)
    if kind == "thicken":
        return c + amt * nrm
    fr = profile_chord_frame(c)
    a = np.radians(-fr["angle_deg"])
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    loc = ((c - fr["le"]) @ rot.T) / max(fr["chord"], _EPS)      # 正規化座標
    s = np.clip(loc[:, 0], 0.0, 1.0)
    if kind == "le_erosion":
        ex = _positive(extent, "extent")
        w = np.clip(1.0 - s / ex, 0.0, 1.0)
        return c - amt * w[:, None] * nrm
    if kind == "waviness":
        w = np.sin(2.0 * np.pi * float(cycles) * s)
        return c + amt * w[:, None] * nrm
    # twist: 後縁側ほど大きく回す
    ang = np.radians(amt) * s
    ca, sa = np.cos(ang), np.sin(ang)
    rel = c - fr["le"]
    return fr["le"] + np.column_stack([ca * rel[:, 0] - sa * rel[:, 1],
                                       sa * rel[:, 0] + ca * rel[:, 1]])
