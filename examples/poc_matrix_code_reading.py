# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""2 値マトリクスコードを読む —— 自分で埋めたビット行列を、撮影を汚してから読み返す。

ここで作るのは **QR 規格そのものではなく、QR と同じ構造を持つ 2 値マトリクス
コード**である。位置検出パターン 3 個 + 分離帯 + タイミングパターン + 位置合わせ
パターン 1 個 + 25x25 のモジュール格子、というレイアウトだけを同型に作り、
データ領域には乱数のビットを置く。誤り訂正符号も、マスク処理も、形式情報も、
文字コードへの復号も入っていない —— 入れていないものを入れたと書かないため、
以下では「符号」と呼ぶ。規格の QR を読むわけではないので、読取率をそのまま
規格準拠リーダの性能として引用してはいけない。

EXTEND: 実際の QR を読むなら、**エンコーダとデコーダは別ライブラリに任せる**
(生成は ``qrcode``、復号は ``pyzbar`` / ``zxing-cpp`` 等。どれもこのリポジトリの
依存には入れていない)。ここで作ったのは前段だけで、そこは**そのまま流用できる**:
二値化 -> 位置検出パターンの 1:1:3:1:1 走査 -> 4 点ホモグラフィ -> モジュール
中心のサンプリング、までを通すと N x N のビット行列が出る。それを外部デコーダの
「ビット行列入力」に渡せばよい(``zxing-cpp`` は画像入力しか受けないので、その
場合はここで推定したホモグラフィで**正対に戻した画像**を渡す形になる)。
規格を相手にするときに本 PoC が持っていない前提が 3 つ増える: (a) 版(格子数)は
既知ではなくタイミングパターンの本数から数える、(b) マスクパターン 8 種の解除と
形式情報の BCH 復号が要る、(c) Reed-Solomon 誤り訂正があるので **BER がそのまま
読取失敗率にはならない**(訂正能力以下の誤りは 0 になり、超えると一気に全滅する)。
本 PoC の BER は「訂正符号に渡す前の生の誤り率」であり、そこが分かれ目になる。

この PoC が示すこと:

1. **真値が完璧に取れる** —— ビット行列を先に決めて画像を合成するので、読み返した
   結果との比較に推定が一切入らない。ビット誤り率(BER)はそのまま数えられる。
2. **ゼロ点を置かないと「読めた」は測れない** —— 全部 0 と答える / 大域固定閾値で
   切って格子に押し込むだけ、の 2 つを並べる。どちらも BER 0.5 付近に落ちる。
3. **要因ごとに崖がある** —— ぼけ・傾き・照明ムラ・雑音・遮蔽・モジュール寸法を
   1 本ずつ振る。ぼけの崖はナイキストから予想した位置とほぼ一致する。
4. **幾何を当てる段と、標本を読む段は別々に壊れる** —— 真のホモグラフィを渡した
   場合と自力検出の場合を毎回並べる。壊れているのがどちらかが分かれる。

★ この PoC が出した道具の穴(op 本体は直していない):

- **A. 局所しきい値の窓が 1 モジュールより小さい。** ``adaptive_gauss_thresh`` と
  ``local_threshold`` は σ が ``1 + 3a`` で最大 4 px、``sk_sauvola`` /
  ``var_threshold`` / ``xsk3_threshold_local_median`` は窓が ``2*int(6a)+3`` で
  最大 15 px、``dyn_threshold`` / ``local_max`` / ``gray_dilation_rect`` などの
  順位フィルタ族は ``{3,5,7,9}`` px。**1 モジュール 8 px の符号では、どれも
  「1 モジュール内の平均」しか見ない** —— 局所しきい値の要点は数モジュール分の
  背景を平均することなので、つまみが物理量(モジュール寸法)に届かない。
  照明ムラの表で、この 3 族が全滅して手書きの Bernsen(窓 3 モジュール)だけが
  読めるのはそのため。つまみが ``[0,1]`` 正規化なので**画素で指定する道が無い**。
- **B. 任意のホモグラフィで画像を warp する op が無い。** ``projective_trans_image``
  は「上 2 隅を内側に寄せる台形 1 パターン」に固定されていて、3x3 行列を渡せない
  (``backends_auto`` の ``kind="projective"``)。カメラ姿勢から作った H で撮影像を
  合成する、という一番普通の使い方ができないので、本 PoC は逆写像を自前で書いた。
  ``affine_warp`` も同様につまみ 2 個で、行列を受け取らない。
- **C. ``calib`` の平面幾何がファサードから見えない。** ``vector_to_hom_mat2d`` /
  ``image_to_world_plane`` / ``projective_trans_pixel`` は ``fullseye`` 直下にも
  ``fullseye.ledger`` にも出ておらず、``import calib`` / ``import transforms`` と
  内部モジュールを直接叩くしかない。しかも ``image_to_world_plane`` は名前に
  反して「渡した H を点にそのまま適用する」だけなので、本 PoC ではモジュール
  座標 -> 画像座標という **逆向き** に使っている(docstring はそう書いてあるが、
  名前だけ見ると必ず取り違える)。
- **D. Harris の ``corner_response`` は符号の定位には使えない。** 第 9 章で実測する
  とおり、応答の極大はモジュールの角すべてに立つので数百個出る。座標ではなく応答
  マップを返す仕様(docstring にも明記あり)と合わせて、「4 隅を取る」用途には
  極大抽出と選別を別途書く必要があり、素直な道具にはならなかった。

数字はすべて末尾の実行結果と同じもので、この機械(Windows / py -3.11 / numpy)で
実測した値である。
"""
from __future__ import annotations

import math
import time

import numpy as np
from scipy import ndimage

import fullseye as fs
import calib          # 平面ホモグラフィ(ファサードには出ていない。穴 C)

N_MODULES = 25        # 25x25 = QR の版 2 と同じ格子数。規格そのものではない
QUIET = 4             # 余白(明)のモジュール数


# ============================================================================ #
# 符号の合成(真値)
# ============================================================================ #
def build_symbol(n=N_MODULES, seed=0):
    """N x N のビット行列を作る。1 = 暗モジュール。

    戻り値 ``(bits, functional, struct)``。``functional`` が True の場所は構造
    (位置検出/分離帯/タイミング/位置合わせ)で、残りがデータ領域(乱数)。
    ``struct`` は構造だけを載せた行列で、**格子数だけで決まりデータには依らない**
    —— つまり読む側も知っている情報なので、定位が合っているかの自己採点に使える
    (真値を覗くことにはならない)。
    """
    rng = np.random.default_rng(seed)
    bits = np.zeros((n, n), np.uint8)
    functional = np.zeros((n, n), bool)

    def finder(r, c):
        for dr in range(7):
            for dc in range(7):
                edge = dr in (0, 6) or dc in (0, 6)
                core = 2 <= dr <= 4 and 2 <= dc <= 4
                bits[r + dr, c + dc] = 1 if (edge or core) else 0
        functional[r:r + 7, c:c + 7] = True

    for r, c in ((0, 0), (0, n - 7), (n - 7, 0)):
        finder(r, c)
    # 分離帯: 位置検出パターンの外周 1 モジュールを明にする
    for r, c in ((0, 0), (0, n - 7), (n - 7, 0)):
        for rr in range(max(0, r - 1), min(n, r + 8)):
            for cc in range(max(0, c - 1), min(n, c + 8)):
                if not (r <= rr < r + 7 and c <= cc < c + 7):
                    bits[rr, cc] = 0
                    functional[rr, cc] = True
    # タイミング: 6 行目と 6 列目が明暗の交番
    for i in range(n):
        if not functional[6, i]:
            bits[6, i] = 1 if i % 2 == 0 else 0
            functional[6, i] = True
        if not functional[i, 6]:
            bits[i, 6] = 1 if i % 2 == 0 else 0
            functional[i, 6] = True
    # 位置合わせパターン(5x5、中心 (n-7, n-7))+ その外周 1 モジュールの分離帯。
    # 規格の QR にこの分離帯は無い —— 中心を重心で出すために本 PoC で足した。
    ar = ac = n - 7
    for dr in range(-3, 4):
        for dc in range(-3, 4):
            ring = max(abs(dr), abs(dc))
            bits[ar + dr, ac + dc] = 1 if ring in (0, 2) else 0
            functional[ar + dr, ac + dc] = True

    struct = bits.copy()                       # 構造だけ(データを載せる前)
    data = rng.integers(0, 2, size=(n, n)).astype(np.uint8)
    bits = np.where(functional, bits, data).astype(np.uint8)
    return bits, functional, struct


def _apply_h(H, pts):
    """(N,2) の (x, y) に 3x3 ホモグラフィを適用する。"""
    p = np.asarray(pts, float).reshape(-1, 2)
    h = np.column_stack([p, np.ones(len(p))]) @ np.asarray(H, float).T
    return h[:, :2] / h[:, 2:3]


def ground_truth_homography(n, module_px, quiet, tilt_deg):
    """モジュール座標 (u, v) -> 画像座標 (x, y) の真のホモグラフィと画布の一辺。

    平面を鉛直軸まわりに ``tilt_deg`` 回してピンホールで撮る。焦点距離は作動距離と
    同じ(対角約 53 度)。撮った四角形は毎回、縦の伸びが ``module_px`` になるよう
    正規化して画布中央に置く —— こうすると **傾けたぶんだけ横のモジュールが縮む**
    という、現場で効く量がそのまま表に出る。
    """
    canvas = (n + 2 * quiet) * module_px
    A = np.array([[1.0, 0, -n / 2], [0, 1.0, -n / 2], [0, 0, 1.0]])   # 中心を原点へ
    th = math.radians(tilt_deg)
    R = np.array([[math.cos(th), 0, math.sin(th)],
                  [0, 1.0, 0],
                  [-math.sin(th), 0, math.cos(th)]])
    d = 4.0 * n
    K = np.array([[d, 0, 0], [0, d, 0], [0, 0, 1.0]])
    H0 = K @ np.column_stack([R[:, 0], R[:, 1], np.array([0, 0, d])]) @ A
    q = _apply_h(H0, [[0, 0], [n, 0], [n, n], [0, n]])
    w = q[:, 0].max() - q[:, 0].min()
    h = q[:, 1].max() - q[:, 1].min()
    sc = (n * module_px) / max(w, h)
    cx = 0.5 * (q[:, 0].max() + q[:, 0].min())
    cy = 0.5 * (q[:, 1].max() + q[:, 1].min())
    S = np.array([[sc, 0, canvas / 2 - sc * cx], [0, sc, canvas / 2 - sc * cy], [0, 0, 1.0]])
    return S @ H0, canvas


def render(bits, H, canvas, ss=3):
    """ホモグラフィ H で符号を画布へ焼く。明 = 1.0、暗 = 0.0。ss x ss の過標本化。"""
    n = bits.shape[0]
    Hinv = np.linalg.inv(H)
    yy, xx = np.mgrid[0:canvas, 0:canvas].astype(np.float64)
    acc = np.zeros((canvas, canvas))
    offs = (np.arange(ss) + 0.5) / ss - 0.5
    for dy in offs:
        for dx in offs:
            p = np.stack([(xx + 0.5 + dx).ravel(), (yy + 0.5 + dy).ravel()], 1)
            uv = _apply_h(Hinv, p)
            iu = np.floor(uv[:, 0]).astype(np.int64)
            iv = np.floor(uv[:, 1]).astype(np.int64)
            inside = (iu >= 0) & (iu < n) & (iv >= 0) & (iv < n)
            dark = np.zeros(len(p))
            dark[inside] = bits[iv[inside], iu[inside]]
            acc += (1.0 - dark).reshape(canvas, canvas)
    return acc / (ss * ss)


def capture(bits, module_px=8, quiet=QUIET, tilt_deg=0.0, blur_ratio=0.0,
            noise=0.0, illum=0.0, occl_mod=0.0, occl_at="center", seed=1):
    """撮影の劣化を順に掛ける: 反射率 -> 照明ムラ -> 光学のぼけ -> センサ雑音。

    ``blur_ratio`` は 1 モジュール寸法に対するガウス σ の比。``noise`` は輝度の
    標準偏差(明暗のコントラストが 1.0 なので、そのまま SN の逆数)。``occl_mod``
    は遮蔽の一辺(モジュール数)で、白い光沢で覆う。
    """
    rng = np.random.default_rng(seed)
    n = bits.shape[0]
    H, canvas = ground_truth_homography(n, module_px, quiet, tilt_deg)
    img = render(bits, H, canvas)

    if occl_mod > 0:
        half = 0.5 * occl_mod
        uv = {"center": (n / 2, n / 2), "finder": (3.5, 3.5)}[occl_at]
        box = _apply_h(H, [[uv[0] - half, uv[1] - half], [uv[0] + half, uv[1] - half],
                           [uv[0] + half, uv[1] + half], [uv[0] - half, uv[1] + half]])
        r0 = int(max(0, np.floor(box[:, 1].min()))); r1 = int(min(canvas, np.ceil(box[:, 1].max())))
        c0 = int(max(0, np.floor(box[:, 0].min()))); c1 = int(min(canvas, np.ceil(box[:, 0].max())))
        img[r0:r1, c0:c1] = 1.0

    if illum > 0:                      # 対角の乗算ムラ。手前 1.0 -> 奥 1-illum
        yy, xx = np.mgrid[0:canvas, 0:canvas].astype(np.float64)
        t = (xx + yy) / (2.0 * (canvas - 1))
        img = img * (1.0 - illum * t)

    if blur_ratio > 0:
        img = ndimage.gaussian_filter(img, blur_ratio * module_px)
    if noise > 0:
        img = img + rng.normal(0.0, noise, img.shape)
    return np.clip(img, 0.0, 1.0), H


# ============================================================================ #
# 二値化(暗 = 1 のマスクを返す)
# ============================================================================ #
def binarize(img, mode, module_px):
    if mode == "otsu":                              # 大域(fullseye op)
        return 1.0 - fs.op.otsu(img)
    if mode == "adaptive_gauss":                    # 局所ガウス σ = 4 px(上限)
        return 1.0 - fs.op.adaptive_gauss_thresh(img, a=1.0, b=0.45)
    if mode == "sauvola":                           # 局所窓 15 px(上限)
        return 1.0 - fs.op.sk_sauvola(img, a=1.0)
    if mode == "illuminate+otsu":                   # 低周波を抜いてから大域
        return 1.0 - fs.op.otsu(fs.op.illuminate(img, a=1.0, b=1.0))
    if mode == "bernsen(3mod)":                     # 手書き: 窓 = 3 モジュール
        k = int(3 * module_px) | 1
        hi = ndimage.maximum_filter(img, size=k)
        lo = ndimage.minimum_filter(img, size=k)
        thr = 0.5 * (hi + lo)
        dark = (img < thr).astype(np.float64)
        dark[(hi - lo) < 0.15] = 0.0                # 局所コントラストが無い所は背景
        return dark
    raise ValueError(mode)


# ============================================================================ #
# 位置検出パターンの走査(1:1:3:1:1)
# ============================================================================ #
def _runs(line):
    idx = np.flatnonzero(np.diff(line)) + 1
    starts = np.concatenate(([0], idx))
    lens = np.diff(np.concatenate((starts, [len(line)])))
    return starts, lens, line[starts]


def _scan(dark, step):
    """行(または転置して列)を走査し (沿った位置, 横切る位置, モジュール推定) を返す。"""
    hits = []
    for i in range(0, dark.shape[0], step):
        s, l, v = _runs(dark[i])
        for k in range(len(l) - 4):
            if v[k] != 1:
                continue
            r = l[k:k + 5].astype(float)
            m = (r[0] + r[1] + r[2] / 3.0 + r[3] + r[4]) / 5.0
            if m < 0.7:
                continue
            exp = np.array([m, m, 3 * m, m, m])
            if np.all(np.abs(r - exp) <= 0.62 * exp):
                hits.append((float(i), s[k + 2] + r[2] / 2.0, m))
    return hits


def _refine_center(dark, cx, cy, hx, hy=None, iters=6):
    """(cx, cy) を中心とする ``2*hx`` x ``2*hy`` の**矩形**窓の暗画素重心へ寄せる。

    円板ではなく正方形にするのが要点だった。位置検出パターンも位置合わせパターンも
    まわり 1 モジュールが明の分離帯なので、``half`` をパターンの半幅と分離帯の間
    (位置検出なら 3.5〜4.5 モジュール、位置合わせなら 2.5〜3.5)に取れば、
    窓は**パターン全体をちょうど含み、隣のデータは 1 画素も含まない**。すると
    重心はパターンの中心そのもので、少しずれた所から始めても中心へ引き込まれる。
    円板にすると外周の輪を斜めに切り落とすため、中心は不動点ではあっても
    **反発する不動点**になり、実測で 1 反復ごとに 1 px ずつ逃げた(6 反復で 7 px)。

    傾けて撮ると横のモジュールだけが縮むので、窓も縦横で別の幅を取る
    (``hx`` は横走査から、``hy`` は縦走査から出したモジュール寸法に比例させる)。
    正方形のまま横を広く取ると、隣のデータを片側だけ拾って中心がずれた。

    画素 ``i`` の幾何座標は ``i + 0.5``。指標の平均に 0.5 を足して返す。
    """
    hy = hx if hy is None else hy
    h, w = dark.shape
    for _ in range(iters):
        r0 = int(max(0, math.floor(cy - hy))); r1 = int(min(h, math.ceil(cy + hy)))
        c0 = int(max(0, math.floor(cx - hx))); c1 = int(min(w, math.ceil(cx + hx)))
        if r1 - r0 < 2 or c1 - c0 < 2:
            return None
        sub = dark[r0:r1, c0:c1] > 0.5
        if sub.sum() < 4:
            return None
        yy, xx = np.mgrid[r0:r1, c0:c1]
        nx, ny = float(xx[sub].mean()) + 0.5, float(yy[sub].mean()) + 0.5
        moved = abs(nx - cx) + abs(ny - cy)
        cx, cy = nx, ny
        if moved < 1e-3:
            break
    return cx, cy


def find_finders(dark, step=1):
    """位置検出パターンの中心 3 点を (row, col) で返す。見つからなければ None。"""
    rows = [(y, x, m, 1.0, 0.0) for y, x, m in _scan(dark, step)]      # 横走査 -> m_x
    cols = [(x, y, m, 0.0, 1.0) for y, x, m in _scan(dark.T, step)]    # 縦走査 -> m_y
    pts = np.array([list(t) for t in rows + cols])
    if len(pts) < 3:
        return None
    rad = 1.5 * float(np.median(pts[:, 2]))
    used = np.zeros(len(pts), bool)
    clusters = []
    for i in range(len(pts)):
        if used[i]:
            continue
        d = np.hypot(pts[:, 0] - pts[i, 0], pts[:, 1] - pts[i, 1])
        sel = (~used) & (d < rad)
        used |= sel
        wx, wy = pts[sel, 3], pts[sel, 4]
        mx = float((pts[sel, 2] * wx).sum() / wx.sum()) if wx.sum() else float("nan")
        my = float((pts[sel, 2] * wy).sum() / wy.sum()) if wy.sum() else float("nan")
        clusters.append((sel.sum(), pts[sel, :2].mean(0), pts[sel, 2].mean(), mx, my))
    clusters.sort(key=lambda c: -c[0])
    cand = [c for c in clusters if c[0] >= 2][:8]
    if len(cand) < 3:
        return None

    best, best_err = None, 1e9
    for i in range(len(cand)):
        for j in range(i + 1, len(cand)):
            for k in range(j + 1, len(cand)):
                p = np.array([cand[i][1], cand[j][1], cand[k][1]])
                d = np.array([np.linalg.norm(p[1] - p[2]),
                              np.linalg.norm(p[0] - p[2]),
                              np.linalg.norm(p[0] - p[1])])
                order = np.argsort(d)
                a, b, c = d[order]
                if c <= 1e-9:
                    continue
                err = abs(a - b) / c + abs(c - math.sqrt(2) * a) / c
                if err < best_err:
                    best_err, best = err, (p, order)
    if best is None or best_err > 0.30:
        return None
    p, order = best
    # 走査の当たりは「核の 3 行」に偏るので、矩形窓の重心で中心へ寄せ直す
    mxs = [c[3] for c in cand if np.isfinite(c[3])]
    mys = [c[4] for c in cand if np.isfinite(c[4])]
    m_all = float(np.median([c[2] for c in cand]))
    m_x = float(np.median(mxs)) if mxs else m_all
    m_y = float(np.median(mys)) if mys else m_all
    ref = []
    for q in p:
        r = _refine_center(dark, q[1], q[0], 4.0 * m_x, 4.0 * m_y)
        ref.append(np.array([q[0], q[1]]) if r is None else np.array([r[1], r[0]]))
    p = np.array(ref)
    tl = p[int(np.argmax([np.linalg.norm(p[1] - p[2]),
                          np.linalg.norm(p[0] - p[2]),
                          np.linalg.norm(p[0] - p[1])]))]
    rest = [q for q in p if not np.allclose(q, tl)]
    if len(rest) != 2:
        return None
    v1 = np.array([rest[0][1] - tl[1], rest[0][0] - tl[0]])     # (x, y)
    v2 = np.array([rest[1][1] - tl[1], rest[1][0] - tl[0]])
    if v1[0] * v2[1] - v1[1] * v2[0] > 0:                        # y 下向きの外積
        tr, bl = rest[0], rest[1]
    else:
        tr, bl = rest[1], rest[0]
    return np.array([tl, tr, bl])                                # (row, col) x 3


def find_alignment(dark, finders, n, m_x, m_y):
    """3 点のアフィン推定から位置合わせパターンを探し、重心で中心を出す。"""
    src = np.array([[3.5, 3.5], [n - 3.5, 3.5], [3.5, n - 3.5]])          # (u, v)
    dst = np.array([[f[1], f[0]] for f in finders])                        # (x, y)
    M = np.linalg.solve(np.column_stack([src, np.ones(3)]), dst)           # 3x2
    pred = np.array([n - 6.5, n - 6.5, 1.0]) @ M
    # アフィン予測は透視ぶんだけ外れる。分離帯の内側に収まる正方窓で引き込む
    got = _refine_center(dark, pred[0], pred[1], 3.0 * m_x, 3.0 * m_y, iters=8)
    if got is None:
        return None
    return np.array([got[0], got[1]])                                      # (x, y)


def estimate_homography(dark, n, step=1):
    """二値像から モジュール座標 -> 画像座標 のホモグラフィを推定する。

    与える前提は格子数 ``n`` だけ(規格の QR ならタイミングパターンの本数から
    数える所)。モジュール寸法は位置検出パターンの間隔から自分で出す。
    """
    f = find_finders(dark, step)
    if f is None:
        return None, "位置検出パターンを取れず"
    m_x = float(np.linalg.norm(f[1] - f[0])) / (n - 7)     # 上辺 = 横のモジュール寸法
    m_y = float(np.linalg.norm(f[2] - f[0])) / (n - 7)     # 左辺 = 縦のモジュール寸法
    if not (np.isfinite(m_x) and np.isfinite(m_y)) or min(m_x, m_y) < 0.5:
        return None, "モジュール寸法が出ず"
    al = find_alignment(dark, f, n, m_x, m_y)
    if al is None:
        return None, "位置合わせパターンを取れず"
    src = np.array([[3.5, 3.5], [n - 3.5, 3.5], [3.5, n - 3.5], [n - 6.5, n - 6.5]])
    dst = np.array([[f[0][1], f[0][0]], [f[1][1], f[1][0]], [f[2][1], f[2][0]], al])
    H = calib.vector_to_hom_mat2d(src, dst)
    if not np.all(np.isfinite(H)):
        return None, "ホモグラフィが発散"
    return H, "ok"


def sample_modules(dark, H, n):
    """モジュール中心を H で画像へ写して標本化する。1 = 暗。"""
    v, u = np.mgrid[0:n, 0:n]
    pts = np.stack([(u + 0.5).ravel(), (v + 0.5).ravel()], 1)
    # image_to_world_plane は「渡した H を点にそのまま適用する」op(穴 C)
    img_pts = calib.image_to_world_plane(pts, H)
    c = np.floor(img_pts[:, 0]).astype(np.int64)     # 幾何座標 x の画素指標 = floor(x)
    r = np.floor(img_pts[:, 1]).astype(np.int64)
    ok = (r >= 0) & (r < dark.shape[0]) & (c >= 0) & (c < dark.shape[1])
    out = np.zeros(n * n)
    out[ok] = dark[r[ok], c[ok]]
    return (out.reshape(n, n) > 0.5).astype(np.uint8)


def struct_score(read_bits, functional, struct):
    """読んだ行列が「構造どおりか」を自己採点する(データ部は見ない)。

    格子数だけで決まる構造(位置検出/分離帯/タイミング/位置合わせ)は読む側も
    知っているので、真値を覗かずに定位の当否を判定できる。実際の復号器も同じ
    ことをしていて、これが無いと**定位が外れたときに自信満々の出鱈目**が返る。
    """
    return float(np.mean(read_bits[functional] == struct[functional]))


def read(img, n, module_px, mode="otsu", H_true=None, step=1,
         functional=None, struct=None, min_struct=0.85):
    """画像 -> ビット行列。``H_true`` を渡すと幾何は既知(標本化だけを測る)。

    自力検出のときは構造の自己採点が ``min_struct`` 未満なら **None を返して
    落ちる** —— 出鱈目を返すより読めなかったと言う方が下流には親切。
    """
    dark = binarize(img, mode, module_px)
    if H_true is not None:
        return sample_modules(dark, H_true, n), "既知"
    H, why = estimate_homography(dark, n, step)
    if H is None:
        return None, why
    got = sample_modules(dark, H, n)
    if functional is not None:
        sc = struct_score(got, functional, struct)
        if sc < min_struct:
            return None, f"構造 {sc:.2f}"
    return got, "ok"


def ber(bits_true, bits_read):
    if bits_read is None:
        return 1.0
    return float(np.mean(bits_true != bits_read))


# ============================================================================ #
def main():
    bits, functional, struct = build_symbol()
    n = N_MODULES

    def detect(im, m):
        """自力検出で読む(構造の自己採点つき)。"""
        return read(im, n, m, functional=functional, struct=struct)

    dark_frac = float(bits.mean())

    print("=== 1. 符号 —— 真値は自分で埋めたビット行列そのもの ===")
    print(f"  格子 {n}x{n} = {n * n} モジュール / 構造 {int(functional.sum())} "
          f"(位置検出 3 + 分離帯 + タイミング + 位置合わせ 1)/ "
          f"データ {int((~functional).sum())}")
    print(f"  暗モジュールの割合 {dark_frac:.4f}(= 全部 0 と答えたときの BER)")
    print("  QR 規格そのものではない。誤り訂正・マスク・形式情報は入れていない。")

    print("\n=== 2. 理想像とゼロ点 ===")
    img0, H0 = capture(bits, module_px=8)
    b_known, _ = read(img0, n, 8, H_true=H0)
    b_det, why = detect(img0, 8)
    naive = (ndimage.zoom(img0, n / img0.shape[0], order=1)[:n, :n] < 0.5).astype(np.uint8)
    print(f"  {'読み方':<26}{'BER':>10}{'正解モジュール':>14}")
    for label, b in (("幾何既知 + 大域 otsu", b_known),
                     ("自力検出 + 大域 otsu", b_det),
                     ("ゼロ点: 全部 0", np.zeros_like(bits)),
                     ("ゼロ点: 画布を格子に押込", naive)):
        e = ber(bits, b)
        print(f"  {label:<26}{e:>10.4f}{n * n * (1 - e):>13.0f}/{n * n}")
    print("  ゼロ点: 乱数で当てずっぽうなら BER 0.5。上の 2 つのゼロ点はそこに張り付く。")
    print("  幾何を当てる段が仕事をしていることは、この差でしか言えない。")

    print("\n=== 3. ぼけ —— 崖はナイキストから予想した所に来るか ===")
    print("  最小周期は 2 モジュール(= 空間周波数 1/(2m) cyc/px)。ガウスの MTF は")
    print("  exp(-2 pi^2 sigma^2 f^2) なので、そこの明暗比が 50 % になるのは")
    print(f"  sigma/m = {math.sqrt(4 * math.log(2) / (2 * math.pi ** 2)):.3f}、"
          f"10 % は {math.sqrt(4 * math.log(10) / (2 * math.pi ** 2)):.3f}。")
    print(f"  {'sigma/m':>9}{'sigma [px]':>12}{'BER 既知':>10}{'BER 検出':>10}"
          f"{'BER 既知 (雑音 0.02)':>21}{'検出':>8}")
    for br in (0.0, 0.15, 0.30, 0.40, 0.50, 0.60, 0.75, 1.00):
        im, H = capture(bits, module_px=8, blur_ratio=br)
        bk, _ = read(im, n, 8, H_true=H)
        bd, why = detect(im, 8)
        im2, H2 = capture(bits, module_px=8, blur_ratio=br, noise=0.02, seed=7)
        bk2, _ = read(im2, n, 8, H_true=H2)
        bd2, why2 = read(im2, n, 8)
        print(f"  {br:>9.2f}{br * 8:>12.1f}{ber(bits, bk):>10.4f}{ber(bits, bd):>10.4f}"
              f"{ber(bits, bk2):>21.4f}{('ok' if bd2 is not None else 'x'):>8}")
    print("  雑音が無ければ標本化は 0.6 まで持つ(中心画素の値がまだ自分のビット側に")
    print("  ある)。雑音 0.02 を入れると 0.5 付近で崩れ、予想の 0.375〜0.68 に入る。")

    print("\n=== 4. 透視ひずみ —— 傾けると横のモジュールが縮む ===")
    print(f"  {'傾き [度]':>10}{'横の縮み':>10}{'実効モジュール [px]':>20}"
          f"{'BER 既知':>10}{'BER 検出':>10}")
    for tilt in (0.0, 15.0, 30.0, 45.0, 55.0, 65.0, 72.0):
        im, H = capture(bits, module_px=8, tilt_deg=tilt, noise=0.01, seed=3)
        bk, _ = read(im, n, 8, H_true=H)
        bd, why = detect(im, 8)
        q = _apply_h(H, [[0, 0], [n, 0], [n, n], [0, n]])
        wide = 0.5 * (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / n
        print(f"  {tilt:>10.0f}{math.cos(math.radians(tilt)):>10.3f}{wide:>20.2f}"
              f"{ber(bits, bk):>10.4f}"
              f"{(f'{ber(bits, bd):.4f}' if bd is not None else why):>10}")
    print("  幾何が既知なら 72 度(横 2.6 px)でも読める。崩れるのは自力検出の方で、")
    print("  1:1:3:1:1 の走査が斜めに切ると比が崩れるのが先に効く。")

    print("\n=== 5. 照明ムラ —— 大域と局所はどこで分かれるか ===")
    modes = ("otsu", "adaptive_gauss", "sauvola", "illuminate+otsu", "bernsen(3mod)")
    print("  1 モジュール 8 px。窓の大きさ: adaptive_gauss = sigma 4 px(上限)、")
    print("  sauvola = 15 px(上限)、illuminate = sigma 15 px、bernsen = 24 px。")
    print(f"  {'ムラ幅':>8}" + "".join(f"{m:>17}" for m in modes))
    for illum in (0.0, 0.2, 0.4, 0.6, 0.8, 0.95):
        im, H = capture(bits, module_px=8, illum=illum, noise=0.01, seed=5)
        row = f"  {illum:>8.2f}"
        for m in modes:
            b, _ = read(im, n, 8, mode=m, H_true=H)
            row += f"{ber(bits, b):>17.4f}"
        print(row)
    print("  大域 otsu はムラ 0.6 で崩れる(暗い側の紙が明るい側の墨より暗くなる)。")
    print("  ★ 窓が 1 モジュール(8 px)より小さい 2 族は**ムラ 0 でも読めない** ——")
    print("     局所平均が自分自身とほぼ同じになり、しきい値が信号を追いかけるため。")
    print("     読めるのは窓が数モジュールある側だけ。これが道具の穴 A。")

    print("\n=== 6. 雑音 ===")
    print(f"  {'sigma':>8}{'SN':>8}{'BER 既知':>10}{'BER 検出':>10}{'検出の可否':>12}")
    for nz in (0.0, 0.05, 0.10, 0.20, 0.30, 0.45):
        es, ed, okc = [], [], 0
        for s in (11, 12, 13):
            im, H = capture(bits, module_px=8, noise=nz, seed=s)
            bk, _ = read(im, n, 8, H_true=H)
            bd, _ = detect(im, 8)
            es.append(ber(bits, bk)); ed.append(ber(bits, bd)); okc += bd is not None
        sn = float("inf") if nz == 0 else 1.0 / nz
        print(f"  {nz:>8.2f}{sn:>8.1f}{np.mean(es):>10.4f}{np.mean(ed):>10.4f}"
              f"{okc:>9}/3")
    print("  3 回の平均。標本化(既知)は 1 画素しか見ないので雑音にそのまま負け、")
    print("  sigma 0.3(SN 3.3)で BER が数 % に乗る。定位の方が先には壊れない。")

    print("\n=== 7. 部分遮蔽 —— どこを隠したかで壊れ方が違う ===")
    print(f"  {'一辺 [mod]':>11}{'覆う割合':>10}{'中央 BER':>10}{'中央 検出':>11}"
          f"{'隅 BER':>9}{'隅 検出':>11}")
    for k in (0, 2, 4, 6, 8, 10):
        rows = []
        for at in ("center", "finder"):
            im, H = capture(bits, module_px=8, occl_mod=k, occl_at=at, noise=0.01, seed=9)
            bk, _ = read(im, n, 8, H_true=H)
            bd, why = detect(im, 8)
            rows.append((ber(bits, bk), "ok" if bd is not None else why[:9]))
        print(f"  {k:>11d}{k * k / (n * n):>10.3f}{rows[0][0]:>10.4f}{rows[0][1]:>11}"
              f"{rows[1][0]:>9.4f}{rows[1][1]:>11}")
    print("  中央を隠すと誤りは覆った暗モジュールぶんだけ(遮蔽 = 白なので約半分)で、")
    print("  定位は生きる。位置検出パターンを隠すと**一辺 4 モジュールで定位が死ぬ**")
    print("  —— 誤り訂正があっても幾何が出ないので符号全体が読めない。")

    print("\n=== 8. モジュール寸法 —— 何画素あれば読めるか(現場で一番効く数字)===")
    print("  ぼけ sigma/m = 0.25、雑音 0.02。3 種の種で平均。")
    print(f"  {'m [px]':>8}{'画布 [px]':>11}{'BER 既知':>10}{'BER 検出':>10}"
          f"{'定位成功':>10}{'復号 [ms]':>11}")
    for m in (2, 3, 4, 5, 6, 8, 12):
        es, ed, okc, ts = [], [], 0, []
        for s in (21, 22, 23):
            im, H = capture(bits, module_px=m, blur_ratio=0.25, noise=0.02, seed=s)
            bk, _ = read(im, n, m, H_true=H)
            t0 = time.perf_counter()
            bd, _ = detect(im, m)
            ts.append(1e3 * (time.perf_counter() - t0))
            es.append(ber(bits, bk)); ed.append(ber(bits, bd)); okc += bd is not None
        print(f"  {m:>8d}{(n + 2 * QUIET) * m:>11d}{np.mean(es):>10.4f}"
              f"{np.mean(ed):>10.4f}{okc:>7}/3{np.mean(ts):>11.1f}")
    print("  1 モジュール 4 px で自力検出が通り、5 px 以上で BER 0。3 px 以下は")
    print("  1:1:3:1:1 の細い方の run が 3 px しか無く、ぼけと雑音で比が崩れる。")

    print("\n=== 9. Harris の corner_response は符号の定位に使えるか(使えない)===")
    im, H = capture(bits, module_px=8, noise=0.01, seed=31)
    resp = fs.op.corner_response(im, a=0.2)
    peak = (resp == ndimage.maximum_filter(resp, size=5)) & (resp > 0.55)
    lab, cnt = ndimage.label(peak)
    print(f"  応答の極大 {cnt} 個(画布 {im.shape[0]}x{im.shape[1]}、符号の角は 4 個)")
    print("  モジュールの角すべてに立つので、4 隅を選び出す段が別に要る。応答マップ")
    print("  しか返さない仕様(docstring にも明記)と合わせ、定位には向かない。穴 D。")

    print("\n=== 10. 速度(この機械での実測)===")
    for m in (8, 16):
        im, H = capture(bits, module_px=m, blur_ratio=0.2, noise=0.02, seed=41)
        side = im.shape[0]
        t0 = time.perf_counter(); binarize(im, "otsu", m)
        t_bin = 1e3 * (time.perf_counter() - t0)
        d = binarize(im, "otsu", m)
        t0 = time.perf_counter(); estimate_homography(d, n)
        t_loc = 1e3 * (time.perf_counter() - t0)
        t0 = time.perf_counter(); detect(im, m)
        t_all = 1e3 * (time.perf_counter() - t0)
        print(f"  m={m:>2} ({side}x{side})  二値化 {t_bin:>6.1f} ms / "
              f"定位 {t_loc:>7.1f} ms / 全体 {t_all:>7.1f} ms")
    print("  定位が支配的。1:1:3:1:1 の走査を全行・全列で Python の輪に回しており、")
    print("  画布の一辺に比例して行数が増えるぶん、そこだけ素直に効いてくる。")

    # ---- 自己検査(速さは assert しない)------------------------------------- #
    img0, H0 = capture(bits, module_px=8)
    bk, _ = read(img0, n, 8, H_true=H0)
    assert ber(bits, bk) == 0.0, "理想像を幾何既知で読んで BER が 0 でない"
    bd, why = detect(img0, 8)
    assert bd is not None and ber(bits, bd) == 0.0, f"理想像の自力検出が失敗: {why}"
    # ゼロ点はランダム推測の線に張り付く
    assert ber(bits, np.zeros_like(bits)) > 0.35, "全部 0 のゼロ点が甘すぎる"
    naive = (ndimage.zoom(img0, n / img0.shape[0], order=1)[:n, :n] < 0.5).astype(np.uint8)
    assert ber(bits, naive) > 0.30, "格子押込のゼロ点が甘すぎる(幾何段が不要になる)"
    # ぼけの崖は予想の帯(0.375〜0.68)に入る
    im, H = capture(bits, module_px=8, blur_ratio=0.15, noise=0.02, seed=7)
    assert ber(bits, read(im, n, 8, H_true=H)[0]) == 0.0, "sigma/m=0.15 で読めない"
    im, H = capture(bits, module_px=8, blur_ratio=1.0, noise=0.02, seed=7)
    assert ber(bits, read(im, n, 8, H_true=H)[0]) > 0.05, "sigma/m=1.0 で崩れていない"
    # 傾き: 幾何が既知なら深い角度でも標本化は生きる
    im, H = capture(bits, module_px=8, tilt_deg=55.0, noise=0.01, seed=3)
    assert ber(bits, read(im, n, 8, H_true=H)[0]) == 0.0, "傾き 55 度で標本化が壊れた"
    # 照明ムラ: 大域は死に、モジュール寸法の窓を持つ局所だけ生きる
    im, H = capture(bits, module_px=8, illum=0.95, noise=0.01, seed=5)
    e_glob = ber(bits, read(im, n, 8, mode="otsu", H_true=H)[0])
    e_loc = ber(bits, read(im, n, 8, mode="bernsen(3mod)", H_true=H)[0])
    assert e_glob > 0.05, "強いムラで大域しきい値が生き残った(ムラの入れ方を疑う)"
    assert e_loc < 0.02, f"モジュール寸法の局所しきい値が読めない BER={e_loc}"
    # 穴 A の実測: 窓が 1 モジュールより小さい局所しきい値はムラ 0 でも読めない
    im, H = capture(bits, module_px=8, noise=0.0)
    assert ber(bits, read(im, n, 8, mode="adaptive_gauss", H_true=H)[0]) > 0.05, \
        "sigma 4 px の局所しきい値が 8 px モジュールを読めてしまった(穴 A の再確認を)"
    # 遮蔽: 位置検出パターンを一辺 6 モジュール隠すと定位が死ぬ
    im, H = capture(bits, module_px=8, occl_mod=6, occl_at="finder", noise=0.01, seed=9)
    assert detect(im, 8)[0] is None, "位置検出パターンを潰しても定位できた"
    # モジュール寸法の下限
    im, H = capture(bits, module_px=6, blur_ratio=0.25, noise=0.02, seed=21)
    assert ber(bits, detect(im, 6)[0]) == 0.0, "1 モジュール 6 px で読めない"
    im, H = capture(bits, module_px=2, blur_ratio=0.25, noise=0.02, seed=21)
    b2, _ = detect(im, 2)
    assert b2 is None or ber(bits, b2) > 0.0, "1 モジュール 2 px で完璧に読めた(合成を疑う)"
    # 構造の真値そのもの
    assert bits[3, 3] == 1 and bits[0, 0] == 1 and bits[1, 1] == 0, "位置検出パターンが違う"
    assert bits[7, 0] == 0 and bits[0, 7] == 0, "分離帯が明でない"
    assert np.all(bits[6, 8:16] == np.array([1, 0, 1, 0, 1, 0, 1, 0])), "タイミングが交番でない"
    print("\nPASS")


if __name__ == "__main__":
    main()
