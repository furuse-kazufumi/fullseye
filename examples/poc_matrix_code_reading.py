# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""2 値マトリクスコードを読む —— 自分で埋めたビット行列を、撮影を汚してから読み返す。

ここで作るのは **QR 規格そのものではなく、QR と同じ構造を持つ 2 値マトリクス
コード**である。位置検出パターン 3 個 + 分離帯 + タイミングパターン + 位置合わせ
パターン 1 個 + 25x25 のモジュール格子、というレイアウトだけを同型に作り、
データ領域には乱数のビットを置く。誤り訂正符号も、マスク処理も、形式情報も、
文字コードへの復号も入っていない —— 入れていないものを入れたと書かないため、
以下では「符号」と呼ぶ。規格そのものを読むわけではないので、読取率をそのまま
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
2. **ゼロ点を置かないと「読めた」は測れない** —— 全部 0 と答える(BER 0.526)/
   画布を格子に押し込んで固定閾値で切る(0.507)の 2 つを並べる。どちらも
   当てずっぽうの 0.5 に張り付く。読める側は 0.0000 なので、差は疑いようがない。
3. **要因ごとに崖がある** —— ぼけ σ/モジュール 0.4〜0.5、傾き 78 度、雑音 σ 0.3、
   位置検出パターンの遮蔽 2 モジュール、モジュール寸法 1 px。ぼけの崖はナイキスト
   から予想した帯(0.375〜0.68)の下端に来た。
4. **幾何を当てる段と、標本を読む段は別々に壊れ、先に落ちるのはいつも幾何** ——
   真のホモグラフィを渡した場合と自力検出を毎回並べると、ぼけでも雑音でも傾きでも
   定位が先に死ぬ。「読めない」の原因を二値化やぼけに求める前に、ここを分けて測る。
5. **出鱈目を返さない** —— 構造(位置検出/分離帯/タイミング/位置合わせ)は格子数
   だけで決まりデータには依らないので、読む側が自己採点できる。採点が落ちたら
   ビット行列を返さない。真値を覗かずに「読めなかった」と言える唯一の道。

★ この PoC が出した道具の穴(op 本体は直していない):

- **A. 局所しきい値の窓が画素で固定されていて、モジュール寸法に届かない。**
  ``adaptive_gauss_thresh`` / ``local_threshold`` は σ が ``1 + 3a`` で最大 4 px、
  ``sk_sauvola`` / ``var_threshold`` / ``xsk3_threshold_local_median`` は窓が
  ``2*int(6a)+3`` で最大 15 px、``dyn_threshold`` / ``local_max`` /
  ``gray_dilation_rect`` などの順位フィルタ族は ``{3,5,7,9}`` px。**1 モジュール
  8 px までなら十分に効く**(第 5 章 (a) の表でムラ 0.95 でも BER 0.013)。
  問題はその先で、**モジュールが窓より大きくなると静かに壊れる** ——
  ムラ 0.9 のまま寸法だけを振ると ``adaptive_gauss_thresh`` は m=16 px で
  BER 0.14、m=24 px で 0.55(= 当てずっぽう)。窓を 3 モジュールに取った
  手書きの Bernsen はどの寸法でも 0。局所しきい値の窓は**対象の構造寸法で決まる
  量**なのに、つまみが ``[0,1]`` 正規化で画素の上限が固定されているため、
  撮像の解像度を上げただけで「照明ムラに強い op」が効かなくなる。
  例外が上がるわけではなく、BER だけが静かに増える種類の壊れ方である。
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
  とおり、応答の極大はモジュールの角すべてに立つので 309 個出る(欲しいのは 4 個)。
  座標ではなく応答マップを返す仕様(docstring にも明記あり)と合わせて、
  「4 隅を取る」用途には極大抽出と選別を別途書く必要があり、素直な道具に
  ならなかった。本 PoC は結局 1:1:3:1:1 の run 長走査を自前で書いている。

★ 道具の穴ではなく**私の間違い**だったもの(同じ罠にかかる人が居るはずなので残す):

- **重心を取る窓は円板でなく正方形にする。** 4 回対称なパターンの中心は、円板の
  重心としては不動点だが **反発する** 不動点だった(外周の輪を斜めに切り落とす
  ため)。実測で 1 反復ごとに約 1 px ずつ逃げ、6 反復で 7 px ずれた。分離帯の
  内側に収まる正方窓にすると、パターン全体をちょうど含んで隣を含まないので、
  中心は**引き込む**不動点になる。
- **3 個の位置検出パターンの三角形に「二等辺」を要求してはいけない。** 傾けて
  撮ると上辺だけが cos(傾き) で縮むので、二等辺なのは正対のときだけ。要求すると
  40 度で偶然それらしい別の 3 点が勝ち、全滅した。直角だけを条件にする。
- **中心 3 点ではホモグラフィの 8 自由度に足りない。** 位置検出パターンの外側
  4 隅を取って 12 組にしたら、45 度以上が通るようになった(72 度まで BER 0)。

数字はすべて末尾の実行結果と同じもので、この機械(Windows / py -3.11 / numpy)で
実測した値である。所要は全体で約 7 秒。
"""
from __future__ import annotations

import math
import time

import numpy as np
from scipy import ndimage

import examplefig as figs
import fullseye as fs
import calib          # 平面ホモグラフィ(ファサードには出ていない。穴 C)

N_MODULES = 25        # 25x25。規格の版 2 と同じ格子数だが規格そのものではない
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
    # 規格にこの分離帯は無い —— 中心を重心で出すために本 PoC で足した。
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


def find_finders(dark, n, step=1):
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
        clusters.append((sel.sum(), pts[sel, :2].mean(0), pts[sel, 2].mean(), mx, my,
                         int(wx.sum()), int(wy.sum())))
    clusters.sort(key=lambda c: -c[0])
    # **横走査と縦走査の両方**で当たった塊だけを候補にする。本物の位置検出パターンは
    # 核の 3 モジュール分の行と列の両方から当たるので、片方向だけの当たり(データ部が
    # たまたま 1:1:3:1:1 に見えた場所)はここでほぼ落ちる。
    cand = [c for c in clusters if c[5] >= 2 and c[6] >= 2][:8]
    if len(cand) < 3:
        return None

    # 3 点の選び方: 直角**だけ**を条件にする。二等辺は条件にしてはいけない ——
    # 傾けて撮ると上辺だけが cos(傾き) で縮むので、45 度で辺の比が 0.71 になり、
    # 二等辺を要求すると偶然それらしい**別の 3 点**が勝ってしまう(実測で 40 度
    # 以上が全滅した)。角度が 90 度から離れないことと、2 辺の比が極端でないこと、
    # それに辺がモジュール寸法より十分長いことだけを見る。
    m_all = float(np.median([c[2] for c in cand]))
    best, best_key = None, None
    for i in range(len(cand)):
        for j in range(i + 1, len(cand)):
            for k in range(j + 1, len(cand)):
                trio = (i, j, k)
                p = np.array([cand[i][1], cand[j][1], cand[k][1]])
                hits = cand[i][0] + cand[j][0] + cand[k][0]
                for a in range(3):
                    b_, c_ = [t for t in range(3) if t != a]
                    v1 = p[b_] - p[a]
                    v2 = p[c_] - p[a]
                    l1 = float(np.linalg.norm(v1)); l2 = float(np.linalg.norm(v2))
                    if min(l1, l2) < 6.0 * m_all:
                        continue
                    if not 0.2 <= l1 / l2 <= 5.0:
                        continue
                    err = abs(float(v1 @ v2)) / (l1 * l2)      # |cos| = 直角からのずれ
                    if err > 0.25:
                        continue
                    key = (-hits, err)
                    if best_key is None or key < best_key:
                        best_key, best = key, (trio, a)
    if best is None:
        return None
    trio, a = best
    # 走査の当たりは「核の 3 行」に偏るので、矩形窓の重心で中心へ寄せ直す。
    # 窓の幅は**その塊自身の**モジュール推定から取る —— 傾けると同じ画像の中で
    # 手前と奥でモジュール寸法が変わるので、全体の中央値を使うと奥側の窓が
    # 広すぎて隣のデータを片側だけ拾い、中心が 13 px ずれた(55 度で実測)。
    ref, mm = [], []
    for t in trio:
        q = cand[t][1]
        mx = cand[t][3] if np.isfinite(cand[t][3]) else m_all
        my = cand[t][4] if np.isfinite(cand[t][4]) else m_all
        r = _refine_center(dark, q[1], q[0], 3.9 * mx, 3.9 * my)
        ref.append(np.array([q[0], q[1]]) if r is None else np.array([r[1], r[0]]))
        mm.append((mx, my))
    p = np.array(ref); mm = np.array(mm)
    tl, mtl = p[a], mm[a]
    idx = [t for t in range(3) if t != a]
    v1 = np.array([p[idx[0]][1] - tl[1], p[idx[0]][0] - tl[0]])   # (x, y)
    v2 = np.array([p[idx[1]][1] - tl[1], p[idx[1]][0] - tl[0]])
    if v1[0] * v2[1] - v1[1] * v2[0] > 0:                         # y 下向きの外積
        i_tr, i_bl = idx[0], idx[1]
    else:
        i_tr, i_bl = idx[1], idx[0]
    centers = np.array([tl, p[i_tr], p[i_bl]])                    # (row, col) x 3
    mxy = np.array([mtl, mm[i_tr], mm[i_bl]])                     # (m_x, m_y) x 3
    return centers, mxy


def finder_quad(dark, cx, cy, hx, hy):
    """位置検出パターンの**外側 4 隅**を (x, y) で返す(TL, TR, BR, BL の順)。

    中心 1 点だけだと 3 点しか対応が取れず、透視を含む 8 自由度のホモグラフィには
    足りない。4 隅まで拾えば 1 個の位置検出パターンから 4 点、3 個で 12 点になり、
    位置合わせパターンに頼らずに済む。外側の輪は 7x7 の正方形なので、窓の中の
    暗画素について ``x+y`` と ``x-y`` の最小・最大を取れば 4 隅の画素が出る
    (面内回転が無いのが前提。回転を入れるなら凸包から取り直すこと)。
    隅の画素の**外側の角**を返すので、対応するモジュール座標は 7x7 の角そのもの。
    """
    h, w = dark.shape
    r0 = int(max(0, math.floor(cy - hy))); r1 = int(min(h, math.ceil(cy + hy)))
    c0 = int(max(0, math.floor(cx - hx))); c1 = int(min(w, math.ceil(cx + hx)))
    if r1 - r0 < 3 or c1 - c0 < 3:
        return None
    sub = dark[r0:r1, c0:c1] > 0.5
    if sub.sum() < 8:
        return None
    yy, xx = np.mgrid[r0:r1, c0:c1]
    ys = yy[sub].astype(float); xs = xx[sub].astype(float)
    ssum = xs + ys; sdif = xs - ys
    i_tl = int(np.argmin(ssum)); i_br = int(np.argmax(ssum))
    i_tr = int(np.argmax(sdif)); i_bl = int(np.argmin(sdif))
    return np.array([[xs[i_tl], ys[i_tl]],                 # 画素の左上の角
                     [xs[i_tr] + 1.0, ys[i_tr]],           # 右上
                     [xs[i_br] + 1.0, ys[i_br] + 1.0],     # 右下
                     [xs[i_bl], ys[i_bl] + 1.0]])          # 左下


def estimate_homography(dark, n, step=1):
    """二値像から モジュール座標 -> 画像座標 のホモグラフィを推定する。

    与える前提は格子数 ``n`` だけ(規格に従うならタイミングパターンの本数から
    数える所)。モジュール寸法は位置検出パターンの間隔から自分で出す。
    対応点は 3 個の位置検出パターンの外側 4 隅 = 12 点で、DLT に流す。
    """
    got = find_finders(dark, n, step)
    if got is None:
        return None, "位置検出パターンを取れず"
    f, mxy = got
    m_x = float(np.linalg.norm(f[1] - f[0])) / (n - 7)     # 上辺 = 横のモジュール寸法
    m_y = float(np.linalg.norm(f[2] - f[0])) / (n - 7)     # 左辺 = 縦のモジュール寸法
    if not (np.isfinite(m_x) and np.isfinite(m_y)) or min(m_x, m_y) < 0.5:
        return None, "モジュール寸法が出ず"
    # 位置検出パターンの左上のモジュール座標(TL / TR / BL)
    origins = [(0.0, 0.0), (n - 7.0, 0.0), (0.0, n - 7.0)]
    src, dst = [], []
    for (ou, ov), c, (mx, my) in zip(origins, f, mxy):
        quad = finder_quad(dark, c[1], c[0], 3.9 * mx, 3.9 * my)
        if quad is None:
            return None, "位置検出パターンの隅を取れず"
        src.extend([[ou, ov], [ou + 7, ov], [ou + 7, ov + 7], [ou, ov + 7]])
        dst.extend(quad.tolist())
    H = calib.vector_to_hom_mat2d(np.array(src), np.array(dst))
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
    print("  規格そのものではない。誤り訂正・マスク・形式情報は入れていない。")

    print("\n=== 2. 理想像とゼロ点 ===")
    img0, H0 = capture(bits, module_px=8)
    b_known, _ = read(img0, n, 8, H_true=H0)
    b_det, _ = detect(img0, 8)
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
    print(f"  {'sigma/m':>9}{'sigma [px]':>12}{'BER 既知':>10}"
          f"{'BER 既知 (雑音 0.02)':>21}{'BER 検出 (雑音 0.02)':>21}")
    blur_rows = []
    for br in (0.0, 0.15, 0.30, 0.40, 0.45, 0.50, 0.60, 0.75, 1.00):
        im, H = capture(bits, module_px=8, blur_ratio=br)
        bk, _ = read(im, n, 8, H_true=H)
        im2, H2 = capture(bits, module_px=8, blur_ratio=br, noise=0.02, seed=7)
        bk2, _ = read(im2, n, 8, H_true=H2)
        bd2, why2 = detect(im2, 8)
        det = f"{ber(bits, bd2):.4f}" if bd2 is not None else f"読めず({why2})"
        print(f"  {br:>9.2f}{br * 8:>12.1f}{ber(bits, bk):>10.4f}"
              f"{ber(bits, bk2):>21.4f}{det:>21}")
        blur_rows.append((br, ber(bits, bk2),
                          ber(bits, bd2) if bd2 is not None else float("nan")))
        if br == 0.50 and figs.enabled():
            # 崖のちょうど上。ビット行列は 25x25 と小さいので 8 倍に拡大して
            # 撮影像と並べる(拡大は表示のためだけで、読み取りは元寸で行った)。
            big = np.ones((8, 8))
            figs.save_grid(
                "symbol_and_errors",
                [np.kron(bits.astype(float), big), im2,
                 np.kron(bk2.astype(float), big),
                 np.kron((bits ^ bk2).astype(float), big)],
                ["真のビット行列", "撮影像(sigma/m 0.50、雑音 0.02)",
                 "読み返したビット行列", "誤ったモジュール(BER %.4f)" % ber(bits, bk2)],
                title="崖のすぐ上で何が起きているか",
                caption="誤りは黒白が隣り合う所に集まる —— 隣のモジュールが"
                        "中心画素へ染み出すため。構造(3 隅・タイミング)は無傷。")
    print("  崖は sigma/m = 0.4 と 0.5 の間(0.40 で BER 0.003、0.50 で 0.066、")
    print("  0.60 で 0.29)。予想した帯 0.375〜0.68 のちょうど下端に来た。")
    print("  雑音 0.02 の有無で崖はほとんど動かない —— 効いているのはコントラストの")
    print("  低下ではなく、**隣のモジュールが中心画素に染み出すこと**の方。")
    print("  定位はもう一段手前で落ちる: 標本化がまだ BER 0.07 の 0.50 では読めるが、")
    print("  0.60 では 1:1:3:1:1 の比が崩れて位置検出パターンが見つからない。")
    # 自力検出の線は「読めた点」で途切れる。途切れる場所そのものが崖。
    br_ax = np.array([r[0] for r in blur_rows])
    det_ok = np.array([np.isfinite(r[2]) for r in blur_rows])
    figs.save_plot("blur_cliff",
                   [("幾何既知(標本化だけ)", br_ax, np.array([r[1] for r in blur_rows])),
                    ("自力検出(幾何 + 標本化)", br_ax[det_ok],
                     np.array([r[2] for r in blur_rows])[det_ok])],
                   xlabel="sigma / m", ylabel="BER",
                   title="ぼけの崖 —— 先に落ちるのは幾何のほう",
                   caption="自力検出の線は sigma/m 0.50 で途切れる(位置検出パターンが"
                           "見つからない)。標本化はそこでまだ BER 0.07。")

    print("\n=== 4. 透視ひずみ —— 傾けると横のモジュールが縮む ===")
    print(f"  {'傾き [度]':>10}{'横の縮み':>10}{'実効モジュール [px]':>20}"
          f"{'BER 既知':>10}{'BER 検出':>26}")
    for tilt in (0.0, 30.0, 45.0, 55.0, 65.0, 72.0, 78.0, 80.0, 84.0):
        im, H = capture(bits, module_px=8, tilt_deg=tilt, noise=0.01, seed=3)
        bk, _ = read(im, n, 8, H_true=H)
        bd, why = detect(im, 8)
        q = _apply_h(H, [[0, 0], [n, 0], [n, n], [0, n]])
        wide = 0.5 * (np.linalg.norm(q[1] - q[0]) + np.linalg.norm(q[2] - q[3])) / n
        det = f"{ber(bits, bd):.4f}" if bd is not None else f"読めず({why})"
        print(f"  {tilt:>10.0f}{math.cos(math.radians(tilt)):>10.3f}{wide:>20.2f}"
              f"{ber(bits, bk):>10.4f}{det:>26}")
    print("  自力検出は 72 度(横 2.4 px)まで BER 0 で通り、78 度で落ちる。")
    print("  幾何が既知なら 80 度まで持つので、限界を決めているのは標本化ではなく定位。")
    print("  ★ ここは実装を 2 回書き直して初めて出た数字で、間違え方が 2 つあった:")
    print("     (a) 3 個の中心の三角形に**二等辺**を要求すると 40 度で全滅する ——")
    print("     傾けると上辺だけが cos で縮むので、二等辺なのは正対のときだけ。")
    print("     直角だけを条件にし、当たりの多い塊を優先すると 72 度まで伸びた。")
    print("     (b) 中心 3 点では対応が 3 組しか無く 8 自由度に足りない。位置検出")
    print("     パターンの**外側 4 隅**を取って 12 組にしたら 45 度以上が通った。")

    print("\n=== 5. 照明ムラ —— 大域と局所はどこで分かれるか ===")
    modes = ("otsu", "adaptive_gauss", "sauvola", "illuminate+otsu", "bernsen(3mod)")
    print("  奥へ向かって明るさが 1.0 -> 1-ムラ幅 に落ちる乗算ムラ。幾何は既知。")
    print("  窓: adaptive_gauss = sigma 4 px(op の上限)、sauvola = 15 px(上限)、")
    print("  illuminate = sigma 15 px(上限)、bernsen = 3 モジュール(手書き)。")
    print("  (a) 1 モジュール 8 px でムラ幅を振る")
    print(f"  {'ムラ幅':>8}" + "".join(f"{m:>17}" for m in modes))
    for illum in (0.0, 0.2, 0.4, 0.6, 0.8, 0.95):
        im, H = capture(bits, module_px=8, illum=illum, noise=0.01, seed=5)
        row = f"  {illum:>8.2f}"
        for m in modes:
            b, _ = read(im, n, 8, mode=m, H_true=H)
            row += f"{ber(bits, b):>17.4f}"
        print(row)
    print("  8 px なら局所しきい値の 3 つはムラ 0.95 でも耐える。大域 otsu は 0.8 から")
    print("  崩れ始める(奥の紙が手前の墨より暗くなり、1 本の線では分けられない)。")
    print("  (b) ムラ幅 0.9 に固定して**モジュール寸法**を振る ★ここが道具の穴 A")
    print(f"  {'m [px]':>8}" + "".join(f"{m:>17}" for m in modes))
    ms_px, ber_by_mode = [], {md: [] for md in modes}
    for m in (4, 6, 8, 12, 16, 24):
        im, H = capture(bits, module_px=m, illum=0.9, noise=0.01, seed=5)
        row = f"  {m:>8d}"
        ms_px.append(m)
        for md in modes:
            b, _ = read(im, n, m, mode=md, H_true=H)
            ber_by_mode[md].append(ber(bits, b))
            row += f"{ber(bits, b):>17.4f}"
        print(row)
    # 窓が画素固定の op は右へ行くほど崩れ、窓をモジュール寸法で決めた bernsen は
    # 平らなまま —— 穴 A はこの 1 枚に全部写る。
    figs.save_plot("threshold_window",
                   [(md, np.array(ms_px, float), np.array(ber_by_mode[md]))
                    for md in modes],
                   xlabel="1 モジュール [px]", ylabel="BER",
                   title="局所しきい値の窓は画素で固定されている(穴 A)",
                   caption="照明ムラ 0.9 固定。解像度を上げるだけで"
                           "「ムラに強い op」が当てずっぽう(0.5)へ落ちる。")
    print("  ★ 窓が画素で固定されている 2 つは、モジュールが窓より大きくなった所で")
    print("     崩れる: adaptive_gauss(sigma 4 px)は m=16 で BER 0.14、m=24 で 0.55。")
    print("     sauvola(窓 15 px)は m=16 で 0.20。窓 = 3 モジュールの bernsen は")
    print("     どの寸法でも 0。**局所しきい値の窓はモジュール寸法で決まる量**なのに、")
    print("     op のつまみは [0,1] 正規化で画素の上限が固定されているため届かない。")
    print("     つまり「照明ムラに強い op」ではなく「モジュールが 12 px 以下のときだけ")
    print("     照明ムラに強い op」だった。撮像の解像度を上げると静かに壊れる。")

    print("\n=== 6. 雑音 ===")
    print("  幾何は 1 モジュール 8 px、ぼけ無し。3 種の種で平均(検出は成功分だけ平均)。")
    print(f"  {'sigma':>8}{'SN':>8}{'BER 既知':>10}{'BER 検出':>10}{'定位成功':>10}")
    for nz in (0.0, 0.05, 0.10, 0.20, 0.25, 0.30, 0.45):
        es, ed, okc = [], [], 0
        for s in (11, 12, 13):
            im, H = capture(bits, module_px=8, noise=nz, seed=s)
            bk, _ = read(im, n, 8, H_true=H)
            bd, _ = detect(im, 8)
            es.append(ber(bits, bk))
            if bd is not None:
                ed.append(ber(bits, bd)); okc += 1
        sn = float("inf") if nz == 0 else 1.0 / nz
        det = f"{np.mean(ed):.4f}" if ed else "読めず"
        print(f"  {nz:>8.2f}{sn:>8.1f}{np.mean(es):>10.4f}{det:>10}{okc:>7}/3")
    print("  標本化(既知)はモジュール中心の 1 画素しか見ないので雑音にそのまま負け、")
    print("  sigma 0.20(SN 5)で BER 0.008、0.30(SN 3.3)で 0.05 まで上がる。")
    print("  定位は sigma 0.25 と 0.30 の間で全滅する —— 二値化した run 長がちぎれて")
    print("  1:1:3:1:1 に見えなくなるため。ここでも先に落ちるのは幾何の方。")
    print("  1 画素ではなくモジュール中央の数画素を平均すれば標本化側は伸びるはずで、")
    print("  それをしていないのは「1 画素で読む」を素の基準として置いているから。")

    print("\n=== 7. 部分遮蔽 —— どこを隠したかで壊れ方が違う ===")
    print("  白い光沢で一辺 k モジュールの正方形を覆う。幾何既知の BER と自力検出の可否。")
    print(f"  {'一辺 [mod]':>11}{'覆う割合':>10}{'中央 BER':>10}{'中央 検出':>11}"
          f"{'隅 BER':>9}{'隅 検出':>20}")
    for k in (0, 1, 2, 4, 6, 8, 10):
        rows = []
        for at in ("center", "finder"):
            im, H = capture(bits, module_px=8, occl_mod=k, occl_at=at, noise=0.01, seed=9)
            bk, _ = read(im, n, 8, H_true=H)
            bd, why = detect(im, 8)
            rows.append((ber(bits, bk), "ok" if bd is not None else why))
        print(f"  {k:>11d}{k * k / (n * n):>10.3f}{rows[0][0]:>10.4f}{rows[0][1]:>11}"
              f"{rows[1][0]:>9.4f}{rows[1][1]:>20}")
    print("  中央(データ部)を覆っても定位は生きたまま、誤りは覆った暗モジュール分")
    print("  だけに留まる —— 一辺 10 モジュール(全体の 16 %)で BER 0.10。")
    print("  位置検出パターンの中心は**一辺 2 モジュールで致命的**。覆う面積は全体の")
    print("  0.6 % しかないのに符号ごと読めなくなる。誤り訂正はビットを救う仕組みで、")
    print("  幾何を救う仕組みではない。汚れやすい面に貼るなら、まず 3 隅を守ること。")

    print("\n=== 8. モジュール寸法 —— 何画素あれば読めるか(現場で一番効く数字)===")
    print("  ゆるい条件 = ぼけ sigma/m 0.25 + 雑音 0.02、きつい条件 = 0.40 + 0.05。")
    print("  どちらも 3 種の種で平均。成功は自力検出が構造の自己採点を通った回数。")
    print(f"  {'m [px]':>8}{'画布 [px]':>11}{'ゆるい 既知':>13}{'ゆるい 検出':>13}"
          f"{'成功':>7}{'きつい 既知':>13}{'きつい 検出':>13}{'成功':>7}{'復号 [ms]':>11}")
    for m in (1, 2, 3, 4, 5, 6, 8, 12):
        out, ts = [], []
        for br, nz in ((0.25, 0.02), (0.40, 0.05)):
            es, ed, okc = [], [], 0
            for sd in (21, 22, 23):
                im, H = capture(bits, module_px=m, blur_ratio=br, noise=nz, seed=sd)
                bk, _ = read(im, n, m, H_true=H)
                t0 = time.perf_counter()
                bd, _ = detect(im, m)
                ts.append(1e3 * (time.perf_counter() - t0))
                es.append(ber(bits, bk))
                if bd is not None:
                    ed.append(ber(bits, bd)); okc += 1
            out.append((float(np.mean(es)), float(np.mean(ed)) if ed else float("nan"), okc))
        ed0 = f"{out[0][1]:.4f}" if out[0][2] else "読めず"
        ed1 = f"{out[1][1]:.4f}" if out[1][2] else "読めず"
        print(f"  {m:>8d}{(n + 2 * QUIET) * m:>11d}{out[0][0]:>13.4f}{ed0:>13}"
              f"{out[0][2]:>5}/3{out[1][0]:>13.4f}{ed1:>13}{out[1][2]:>5}/3"
              f"{np.mean(ts):>11.1f}")
    print("  **1 モジュール 2 px あれば自力で読める**。1 px では位置検出パターンの")
    print("  細い run が 1 px しか無く 1:1:3:1:1 の比を判定できないので定位が立たない")
    print("  (幾何を渡せば 1 px でもほぼ読めるので、限界は標本化ではなく定位にある)。")
    print("  m=2 の「既知」がきつい条件だけ悪いのは合成側の都合で、モジュール中心が")
    print("  ちょうど画素境界に乗るため —— 偶数寸法では標本点を半画素ずらすとよい。")
    print("  実務の目安は、ぼけと雑音の余裕を見て **4〜6 px/モジュール**。")

    print("\n=== 9. Harris の corner_response は符号の定位に使えるか(使えない)===")
    im, H = capture(bits, module_px=8, noise=0.01, seed=31)
    resp = fs.op.corner_response(im, a=0.2)
    peak = (resp == ndimage.maximum_filter(resp, size=5)) & (resp > 0.55)
    cnt = int(ndimage.label(peak)[1])
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
    # 穴 A の実測: 窓が画素で固定された局所しきい値は、モジュールが窓より大きい所で
    # 崩れる。8 px では耐え、24 px では崩れる —— これが「静かに壊れる」の中身。
    im8, H8 = capture(bits, module_px=8, illum=0.9, noise=0.01, seed=5)
    e8 = ber(bits, read(im8, n, 8, mode="adaptive_gauss", H_true=H8)[0])
    im24, H24 = capture(bits, module_px=24, illum=0.9, noise=0.01, seed=5)
    e24 = ber(bits, read(im24, n, 24, mode="adaptive_gauss", H_true=H24)[0])
    assert e8 < 0.05, f"m=8 で adaptive_gauss が読めない BER={e8}(前提が変わった)"
    assert e24 > 0.20, f"m=24 で adaptive_gauss が崩れない BER={e24}(穴 A の再確認を)"
    assert ber(bits, read(im24, n, 24, mode="bernsen(3mod)", H_true=H24)[0]) < 0.02, \
        "モジュール寸法で窓を決めた側まで m=24 で崩れた"
    # 遮蔽: 位置検出パターンの中心を一辺 2 モジュール隠すと定位が死ぬ
    im, H = capture(bits, module_px=8, occl_mod=2, occl_at="finder", noise=0.01, seed=9)
    assert detect(im, 8)[0] is None, "位置検出パターンの中心を潰しても定位できた"
    im, H = capture(bits, module_px=8, occl_mod=10, occl_at="center", noise=0.01, seed=9)
    assert detect(im, 8)[0] is not None, "データ部を覆っただけで定位が死んだ"
    # モジュール寸法の下限
    im, H = capture(bits, module_px=6, blur_ratio=0.25, noise=0.02, seed=21)
    assert ber(bits, detect(im, 6)[0]) == 0.0, "1 モジュール 6 px で読めない"
    im, H = capture(bits, module_px=1, blur_ratio=0.25, noise=0.02, seed=21)
    assert detect(im, 1)[0] is None, "1 モジュール 1 px で定位できた(合成を疑う)"
    # 構造の真値そのもの
    assert bits[3, 3] == 1 and bits[0, 0] == 1 and bits[1, 1] == 0, "位置検出パターンが違う"
    assert bits[7, 0] == 0 and bits[0, 7] == 0, "分離帯が明でない"
    assert np.all(bits[6, 8:16] == np.array([1, 0, 1, 0, 1, 0, 1, 0])), "タイミングが交番でない"
    print("\nPASS")


if __name__ == "__main__":
    main()
