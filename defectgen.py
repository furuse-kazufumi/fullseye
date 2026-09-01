# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""defectgen — 欠陥を**数式で**作る。注釈は生成の副産物として無料で付いてくる。

検査アルゴリズムを試すのに一番足りないのは、いつでも「欠陥のある画像と、その
正解マスク」である。実物を集めるのは高くつき、しかも**稀な欠陥ほど集まらない**
——検査で本当に困るのはそこなのに。

このモジュールは欠陥を撮影物ではなく **確率幾何のモデル**として作る。傷は
ランダムウォーク、孔食は非一様な点過程、割れは分岐する枝、ゆず肌は帯域制限
ノイズ。パラメータを振れば**同じ種類の欠陥を、狙った大きさ・向き・コントラストで
いくらでも**出せる(系統的なエッジケース生成)。そして幾何から描くので
**画素完全なマスクが生成の副産物として必ず付く** — 人手の注釈が要らない。

生成 AI は使わない。理由は 3 つある:

  * **制御できること** — 「幅 30 µm、長さ 2 mm、45°、コントラスト 5%」を指定
    したい。生成モデルに頼むと、出てきた欠陥が本当にその寸法かを別途測る羽目
    になる。
  * **注釈が正確なこと** — 幾何を知っているので、マスクは定義から作れる。
    生成画像に後から注釈を付けると、そこが新しい誤差源になる。
  * **再現できること** — seed で決定的。同じ seed は同じ欠陥を返す。

**honest な限界**: これは *appearance* のモデルであって、材料物理のモデルでは
ない。傷の断面が実物どおりの光り方をする保証はなく、鏡面や透明体では特にずれる
(そこは光輸送の領域で、``visiondesign`` の docstring に書いたとおり本ライブラリの
外)。ここで作れるのは「**この形・この大きさ・このコントラストの特徴を、その
検査系が見つけられるか**」を問うための素材であって、実欠陥の代用ではない。

``visiondesign.image_formation`` と組み合わせると、理想の欠陥画像が「その光学系で
実際に撮れる画像」になる。さらに ``aug_*`` 群を掛ければセンサ雑音まで乗る。
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "defect_scratch", "defect_pits", "defect_crack", "defect_blob",
    "surface_texture", "composite_defect", "defect_stats",
    "MAX_DEFECT_PIXELS",
]

#: 生成できる画像の画素数上限。掃引で回すことを想定しているので、1 枚が大きすぎる
#: と気付かないうちにメモリと時間を食う(小さい入力から巨大な確保、の家系)。
MAX_DEFECT_PIXELS = 1 << 24


def _shape(shape):
    """(H, W) の妥当性検証。"""
    try:
        h, w = (int(shape[0]), int(shape[1]))
    except (TypeError, ValueError, IndexError):
        raise ValueError("shape must be a (height, width) pair, got %r" % (shape,))
    if h < 2 or w < 2:
        raise ValueError("shape must be at least 2x2, got %dx%d" % (h, w))
    if h * w > MAX_DEFECT_PIXELS:
        raise ValueError("shape %dx%d exceeds MAX_DEFECT_PIXELS=%d"
                         % (h, w, MAX_DEFECT_PIXELS))
    return h, w


def _num(value, name, *, lo=None, hi=None, allow_zero=False):
    """数値引数の検証。文字列・bool を明示的に弾く。

    ``float("30")`` は成功するので、未解析の設定値が µm として通り抜ける
    (光学系で実際に踏んだ罠。``thin_lens("50","200")`` が 66.667 mm を返した)。
    """
    if isinstance(value, (str, bytes, bool)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    v = float(value)
    if not np.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if not allow_zero and v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (name, value))
    if allow_zero and v < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))
    if lo is not None and v < lo:
        raise ValueError("%s must be >= %g, got %r" % (name, lo, value))
    if hi is not None and v > hi:
        raise ValueError("%s must be <= %g, got %r" % (name, hi, value))
    return v


def _stamp(mask, yy, xx, radius):
    """(yy, xx) を中心に半径 *radius* の円盤をマスクへ焼き付ける。

    円盤の重ね合わせで線や領域を描くのは、幅が厳密に ``2*radius`` になり、
    **マスクと見た目が定義から一致する**ため(ラスタ線分だと幅が向きで変わる)。
    """
    h, w = mask.shape
    r = int(np.ceil(radius))
    y0, y1 = max(0, int(yy) - r), min(h, int(yy) + r + 1)
    x0, x1 = max(0, int(xx) - r), min(w, int(xx) + r + 1)
    if y0 >= y1 or x0 >= x1:
        return
    gy, gx = np.mgrid[y0:y1, x0:x1]
    inside = (gy - yy) ** 2 + (gx - xx) ** 2 <= radius * radius
    mask[y0:y1, x0:x1] |= inside


def defect_scratch(shape=(256, 256), length_px=120.0, width_px=3.0,
                   angle_deg=30.0, wander=0.15, contrast=-0.25, seed=0,
                   start=None):
    """引っかき傷 — 向きを持ったランダムウォークで描く 1 本の線状欠陥。

    直線ではなく、指定方向へ進みながら ``wander`` の強さで向きがゆらぐ経路
    (実際の擦り傷が工具の送りに沿いつつ微妙に蛇行するのに倣う)。``wander=0``
    で厳密な直線になる。

    *contrast* は背景 0.5 に対する加算量で、**負なら暗い傷、正なら光る傷**
    (鏡面部品では傷が明るく出るので、符号を選べることが要る)。

    Returns ``(image, mask)``: 画像は float64 [0,1]、マスクは bool。マスクは
    幾何から作るので画素完全で、後付けの注釈による誤差が入らない。

    Raises ValueError: shape が 2x2 未満/上限超過、長さ・幅が非正、
    ``wander`` が負、``contrast`` が [-1,1] の外、seed が整数でない場合。
    """
    h, w = _shape(shape)
    length = _num(length_px, "length_px")
    width = _num(width_px, "width_px")
    _num(wander, "wander", allow_zero=True)
    c = _num(contrast, "contrast", lo=-1.0, hi=1.0, allow_zero=True)
    if isinstance(seed, bool) or int(seed) != seed:
        raise ValueError("seed must be an integer, got %r" % (seed,))
    rng = np.random.default_rng(int(seed))
    theta = np.radians(_num(angle_deg, "angle_deg", allow_zero=True))
    if start is None:
        y, x = h / 2.0, w / 2.0
        y -= 0.5 * length * np.sin(theta)
        x -= 0.5 * length * np.cos(theta)
    else:
        y, x = float(start[0]), float(start[1])

    mask = np.zeros((h, w), bool)
    steps = max(2, int(np.ceil(length)))
    for _ in range(steps):
        _stamp(mask, y, x, width / 2.0)
        theta += rng.normal(0.0, wander) if wander > 0 else 0.0
        y += np.sin(theta)
        x += np.cos(theta)
    img = np.full((h, w), 0.5, np.float64)
    img[mask] += c
    return np.clip(img, 0.0, 1.0), mask


def defect_pits(shape=(256, 256), count=25, radius_px=4.0, radius_sigma=0.4,
                contrast=-0.3, clustering=0.0, seed=0):
    """孔食・打痕 — 点過程で置いた円形のくぼみ群。

    ``clustering=0`` なら一様分布(完全にランダムな配置)。値を上げると
    **既に置いた孔の近くに寄る**(腐食が起点から広がる様子に倣う)。半径は
    平均 ``radius_px``・相対ばらつき ``radius_sigma`` の対数正規で振れるので、
    「同じ大きさの丸が並ぶ」不自然さにならない。

    Returns ``(image, mask)``。

    Raises ValueError: count が非負整数でない、半径が非正、``clustering`` が
    [0,1] の外、``contrast`` が [-1,1] の外の場合。
    """
    h, w = _shape(shape)
    if isinstance(count, bool) or int(count) != count or int(count) < 0:
        raise ValueError("count must be a non-negative integer, got %r" % (count,))
    r_mean = _num(radius_px, "radius_px")
    r_sigma = _num(radius_sigma, "radius_sigma", allow_zero=True)
    clus = _num(clustering, "clustering", lo=0.0, hi=1.0, allow_zero=True)
    c = _num(contrast, "contrast", lo=-1.0, hi=1.0, allow_zero=True)
    rng = np.random.default_rng(int(seed))

    mask = np.zeros((h, w), bool)
    placed = []
    for _ in range(int(count)):
        if placed and rng.random() < clus:
            py, px = placed[int(rng.integers(len(placed)))]
            # 親の近傍(半径の数倍)に子を置く = 起点から広がる腐食
            y = float(np.clip(py + rng.normal(0, 4 * r_mean), 0, h - 1))
            x = float(np.clip(px + rng.normal(0, 4 * r_mean), 0, w - 1))
        else:
            y, x = float(rng.uniform(0, h - 1)), float(rng.uniform(0, w - 1))
        r = float(r_mean * np.exp(rng.normal(0.0, r_sigma))) if r_sigma > 0 else r_mean
        _stamp(mask, y, x, max(0.5, r))
        placed.append((y, x))
    img = np.full((h, w), 0.5, np.float64)
    img[mask] += c
    return np.clip(img, 0.0, 1.0), mask


def defect_crack(shape=(256, 256), length_px=90.0, width_px=2.0, angle_deg=90.0,
                 branch_prob=0.12, wander=0.25, contrast=-0.35, seed=0,
                 max_branches=8):
    """割れ — 枝分かれする線状欠陥。傷との違いは**分岐する**こと。

    主枝を伸ばしながら確率 ``branch_prob`` で子枝を出し、子枝は親より短く細く
    なる(実際の亀裂が先端で分岐し細くなるのに倣う)。分岐の総数は
    ``max_branches`` で頭打ちにする — 上限が無いと指数的に増えて、小さな入力から
    大きな計算になる。

    Returns ``(image, mask)``。

    Raises ValueError: ``branch_prob`` が [0,1] の外、``max_branches`` が負、
    その他 :func:`defect_scratch` と同じ検証に反する場合。
    """
    h, w = _shape(shape)
    length = _num(length_px, "length_px")
    width = _num(width_px, "width_px")
    bp = _num(branch_prob, "branch_prob", lo=0.0, hi=1.0, allow_zero=True)
    wan = _num(wander, "wander", allow_zero=True)
    c = _num(contrast, "contrast", lo=-1.0, hi=1.0, allow_zero=True)
    if isinstance(max_branches, bool) or int(max_branches) != max_branches \
            or int(max_branches) < 0:
        raise ValueError("max_branches must be a non-negative integer, got %r"
                         % (max_branches,))
    rng = np.random.default_rng(int(seed))
    mask = np.zeros((h, w), bool)
    theta0 = np.radians(_num(angle_deg, "angle_deg", allow_zero=True))
    # (y, x, theta, 残り長さ, 幅)
    todo = [(h / 2.0 - 0.5 * length * np.sin(theta0),
             w / 2.0 - 0.5 * length * np.cos(theta0), theta0, length, width)]
    branches = 0
    while todo:
        y, x, theta, remain, wid = todo.pop()
        for _ in range(max(2, int(np.ceil(remain)))):
            _stamp(mask, y, x, wid / 2.0)
            theta += rng.normal(0.0, wan) if wan > 0 else 0.0
            y += np.sin(theta)
            x += np.cos(theta)
            if not (0 <= y < h and 0 <= x < w):
                break
            if branches < max_branches and bp > 0 and rng.random() < bp / remain:
                branches += 1
                # 子枝は親の 40〜70% の長さ、幅は 60〜80%(先端ほど細い)
                todo.append((y, x, theta + rng.choice([-1, 1]) * rng.uniform(0.4, 1.0),
                             remain * rng.uniform(0.4, 0.7),
                             max(1.0, wid * rng.uniform(0.6, 0.8))))
    img = np.full((h, w), 0.5, np.float64)
    img[mask] += c
    return np.clip(img, 0.0, 1.0), mask


def defect_blob(shape=(256, 256), radius_px=20.0, roughness=0.35, contrast=0.25,
                seed=0, centre=None, harmonics=6):
    """しみ・付着物・異物 — 輪郭が波打つ塊状の欠陥。

    半径を角度の関数として少数の調和成分で揺らす(``harmonics`` 個)。
    ``roughness=0`` なら真円。円と違って**輪郭が滑らかなまま不規則**になるので、
    円形度で弾くような素朴な検査を通り抜ける素材になる。

    Returns ``(image, mask)``。

    Raises ValueError: 半径が非正、``roughness`` が負、``harmonics`` が正整数で
    ない場合。
    """
    h, w = _shape(shape)
    r0 = _num(radius_px, "radius_px")
    rough = _num(roughness, "roughness", allow_zero=True)
    c = _num(contrast, "contrast", lo=-1.0, hi=1.0, allow_zero=True)
    if isinstance(harmonics, bool) or int(harmonics) != harmonics or int(harmonics) < 1:
        raise ValueError("harmonics must be a positive integer, got %r" % (harmonics,))
    rng = np.random.default_rng(int(seed))
    cy, cx = (h / 2.0, w / 2.0) if centre is None else (float(centre[0]), float(centre[1]))
    amps = rng.normal(0.0, rough, int(harmonics)) / (1 + np.arange(int(harmonics)))
    phases = rng.uniform(0, 2 * np.pi, int(harmonics))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    ang = np.arctan2(yy - cy, xx - cx)
    rad = np.hypot(yy - cy, xx - cx)
    boundary = r0 * (1.0 + sum(a * np.cos((k + 1) * ang + p)
                               for k, (a, p) in enumerate(zip(amps, phases))))
    mask = rad <= np.maximum(boundary, 0.5)
    img = np.full((h, w), 0.5, np.float64)
    img[mask] += c
    return np.clip(img, 0.0, 1.0), mask


def surface_texture(shape=(256, 256), kind="orange_peel", strength=0.05,
                    scale_px=8.0, seed=0):
    """欠陥ではない背景 — 正常な表面の見た目。

    これが無いと、平坦な背景に欠陥だけが乗った非現実的に簡単な画像になり、
    検査アルゴリズムを甘く評価してしまう。``kind``:

      * ``"orange_peel"`` — 帯域制限ノイズ(塗装のゆず肌)
      * ``"brushed"`` — 一方向に強く相関したノイズ(ヘアライン仕上げ)
      * ``"grain"`` — 白色に近い細かいノイズ(鋳肌・粗い機械加工面)

    Returns 背景画像 float64 [0,1](平均 0.5)。マスクは返さない — 正常面には
    注釈すべきものが無いため。

    Raises ValueError: 未知の ``kind``、``strength`` が [0,1] の外、
    ``scale_px`` が非正の場合。
    """
    h, w = _shape(shape)
    s = _num(strength, "strength", lo=0.0, hi=1.0, allow_zero=True)
    scale = _num(scale_px, "scale_px")
    if kind not in ("orange_peel", "brushed", "grain"):
        raise ValueError("kind must be one of 'orange_peel', 'brushed', 'grain', "
                         "got %r" % (kind,))
    from scipy import ndimage
    rng = np.random.default_rng(int(seed))
    n = rng.standard_normal((h, w))
    if kind == "orange_peel":
        tex = ndimage.gaussian_filter(n, sigma=scale)
    elif kind == "brushed":
        tex = ndimage.gaussian_filter(n, sigma=(scale * 4.0, scale * 0.25))
    else:                                                  # grain
        tex = ndimage.gaussian_filter(n, sigma=max(0.5, scale * 0.1))
    sd = float(tex.std())
    if sd <= 0.0:
        return np.full((h, w), 0.5, np.float64)            # 定数 = 揺らぎ無し
    return np.clip(0.5 + s * tex / sd, 0.0, 1.0)


def composite_defect(background, defect_image, mask):
    """正常面の上に欠陥を合成する。**マスクの内側だけ**を置き換える。

    欠陥生成器は背景 0.5 の上に描くので、その差分だけを背景へ移す。こうすると
    表面の質感が欠陥の外で保たれ、かつマスクが合成後も正確なままになる。

    Returns 合成画像 float64 [0,1]。

    Raises ValueError: 3 つの形が一致しない、非有限、mask が bool でない場合。
    """
    bg = np.asarray(background, np.float64)
    df = np.asarray(defect_image, np.float64)
    mk = np.asarray(mask)
    if bg.shape != df.shape or bg.shape != mk.shape:
        raise ValueError("background %r, defect_image %r and mask %r must share "
                         "one shape" % (bg.shape, df.shape, mk.shape))
    if mk.dtype != bool:
        raise ValueError("mask must be a boolean array, got dtype %r" % (mk.dtype,))
    if not (np.isfinite(bg).all() and np.isfinite(df).all()):
        raise ValueError("background/defect_image contain non-finite value(s)")
    out = bg.copy()
    out[mk] = np.clip(bg[mk] + (df[mk] - 0.5), 0.0, 1.0)
    return out


def defect_stats(mask, um_per_pixel=None):
    """作った欠陥を**測り返す** — 注文どおりの大きさになっているかの確認。

    生成器のパラメータは「意図」であって、丸めや画像端での切れで実際の寸法は
    ずれうる。掃引でデータセットを作るときは、意図ではなく**実測値**を注釈に
    書くべきなので、ここで測る。``um_per_pixel`` を渡すと物理単位も併記する
    (``visiondesign.system_geometry`` の出力をそのまま渡せる)。

    Returns 面積・外接箱・長軸/短軸(二次モーメントから)・充填率の table。

    Raises ValueError: mask が bool の 2-D でない場合。
    """
    mk = np.asarray(mask)
    if mk.dtype != bool or mk.ndim != 2:
        raise ValueError("mask must be a 2-D boolean array, got %r %r"
                         % (mk.ndim, mk.dtype))
    ys, xs = np.nonzero(mk)
    if ys.size == 0:
        return {"area_px": 0, "empty": True}
    h = int(ys.max() - ys.min() + 1)
    w = int(xs.max() - xs.min() + 1)
    y0, x0 = ys.mean(), xs.mean()
    cov = np.cov(np.stack([ys - y0, xs - x0])) if ys.size > 1 else np.zeros((2, 2))
    ev = np.linalg.eigvalsh(np.atleast_2d(cov))
    major = float(4.0 * np.sqrt(max(ev[-1], 0.0)))         # 2 標準偏差 x2
    minor = float(4.0 * np.sqrt(max(ev[0], 0.0)))
    out = {
        "area_px": int(ys.size), "empty": False,
        "bbox_h_px": h, "bbox_w_px": w,
        "major_axis_px": major, "minor_axis_px": minor,
        "fill_ratio": float(ys.size) / float(h * w),
    }
    if um_per_pixel is not None:
        s = _num(um_per_pixel, "um_per_pixel")
        out.update({"major_axis_um": major * s, "minor_axis_um": minor * s,
                    "area_um2": float(ys.size) * s * s})
    return out
