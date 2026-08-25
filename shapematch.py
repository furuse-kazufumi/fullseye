"""形状ベースマッチング(HALCON "Matching" chapter の genuine core, numpy).

Steger 流の勾配方向マッチング: モデル=テンプレートのエッジ点の正規化勾配ベクトル、
スコア=対応位置での勾配方向の一致(内積平均)。輝度変化に頑健。
コントラスト反転を許すかは ``metric``(HALCON と同名)で選ぶ —— 既定の
``"use_polarity"`` は許さない。**点ごとに絶対値を取る "ignore_local_polarity" を
既定にしていた頃は、向きが乱数でも E[|cos|] = 2/pi = 0.637 の下駄が残り、
雑音の強い画像で min_score が何も棄却できなかった**(実測、docs/HIGHSPEED_VISION.md)。
handle でなく軽量 dict。画像/テンプレートは [0,1] の 2D float64。
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage


def _grad_field(img):
    gx = ndimage.sobel(img, axis=1)
    gy = ndimage.sobel(img, axis=0)
    mag = np.hypot(gx, gy)
    return gx, gy, mag


def create_shape_model(template, min_grad: float = 0.1,
                       metric: str = "use_polarity") -> dict:
    """テンプレートのエッジ点(|grad|>min_grad)の正規化勾配ベクトルをモデル化(create_shape_model)。

    ``metric`` は HALCON の同名パラメータ:

    - ``"use_polarity"``(既定、HALCON も既定) —— 勾配の **符号つき** cos を平均。
      向きが揃っていないと点が加点されないので、明暗が反転した物体は一致しない。
    - ``"ignore_global_polarity"`` —— 符号つきで足してから絶対値。物体全体の
      明暗が反転していても一致する(部分ごとの反転は許さない)。
    - ``"ignore_local_polarity"`` —— 点ごとに絶対値。**最も緩く、偽陽性が出やすい**
      (HALCON の説明も同じ警告をしている)。
    """
    t = np.asarray(template, dtype=np.float64)
    gx, gy, mag = _grad_field(t)
    thr = min_grad * (mag.max() + 1e-9)
    ys, xs = np.nonzero(mag > thr)
    if len(ys) == 0:
        ys, xs = np.array([t.shape[0] // 2]), np.array([t.shape[1] // 2])
    n = np.hypot(gx[ys, xs], gy[ys, xs]) + 1e-9
    return {"shape": t.shape, "pts": np.column_stack([ys, xs]),
            "grad": np.column_stack([gy[ys, xs] / n, gx[ys, xs] / n]),
            # 各階層でモデルを作り直すためにテンプレートを保持する。
            # **ピラミッドを作るのは画像であってモデルではない**(一次資料で確認、
            # docs/HIGHSPEED_VISION.md「ピラミッドの正体」)ので、粗い階層のモデルは
            # 縮小したテンプレートから抽出し直す。モデル点を間引くのとは別物。
            "template": t.copy(), "min_grad": float(min_grad),
            # **MinContrast**(HALCON の同名パラメータ)。これが無いと、勾配が
            # 雑音しかない場所でも m で割った時点で単位ベクトルに化けるので、
            # |cos| の平均が 2/pi = 0.637 に張り付く。実測でも純雑音の画像で
            # 最良スコアが 0.73-0.75 出ており、**既定の min_score=0.5 では
            # 何も棄却できなかった**。閾値未満の点は 0 点として数える。
            "min_contrast": float(thr), "metric": str(metric)}


def create_generic_shape_model(template, min_grad: float = 0.1,
                               metric: str = "use_polarity") -> dict:
    """汎用形状モデル(create_generic_shape_model、create_shape_model と同核)。"""
    return create_shape_model(template, min_grad, metric)


def create_aniso_shape_model(template, min_grad: float = 0.1,
                             metric: str = "use_polarity") -> dict:
    """異方性スケール形状モデル(create_aniso_shape_model、モデル自体は同一、find で異方 scale 探索)。"""
    m = create_shape_model(template, min_grad, metric)
    m["aniso"] = True
    return m


def _score_at(model, gy_img, gx_img, mag_img, r0, c0):
    pts = model["pts"]
    ys = pts[:, 0] - model["shape"][0] // 2 + r0
    xs = pts[:, 1] - model["shape"][1] // 2 + c0
    H, W = mag_img.shape
    ok = (ys >= 0) & (ys < H) & (xs >= 0) & (xs < W)
    if ok.sum() < 3:
        return 0.0
    ys, xs = ys[ok], xs[ok]
    m = mag_img[ys, xs]
    md = m + 1e-9
    ig = np.column_stack([gy_img[ys, xs] / md, gx_img[ys, xs] / md])
    dots = (ig * model["grad"][ok]).sum(1)               # 符号つき方向一致
    mc = float(model.get("min_contrast", 0.0))
    if mc > 0.0:
        dots = np.where(m >= mc, dots, 0.0)              # 低コントラスト点は 0 点
    # **画像外へ出た点も 0 点**として全点数で割る。見えている点だけの平均だと、
    # 端で model が半分はみ出た位置が数点の平均で高得点になった(実測)。
    n = len(pts)
    metric = model.get("metric", "use_polarity")
    if metric == "ignore_local_polarity":
        # 点ごとに絶対値を取る。**これが雑音の下駄の正体**。向きが乱数でも
        # E[|cos|] = 2/pi = 0.637 が残るので、雑音の強い画像では min_score が
        # 何も棄却できない(実測: 雑音 sd 0.15 で 0.57、sd 0.30 で 0.65)。
        return float(np.abs(dots).sum() / n)
    if metric == "ignore_global_polarity":
        # 符号つきで足してから絶対値。乱数なら和は 0 のまわりに散るだけなので
        # 下駄は履かない(標準偏差 1/sqrt(n) 相当)。
        return float(abs(dots.sum()) / n)
    # use_polarity(既定)。負は一致していないので 0 で止める。
    return float(max(0.0, dots.sum() / n))


def pyr_down(a):
    """平滑化してから 1/2 に間引く。**平滑化を省くと細い構造が丸ごと消える**
    (実測: 1 px の線で上位残存 0.33。docs/HIGHSPEED_VISION.md)。"""
    return ndimage.gaussian_filter(np.asarray(a, dtype=np.float64), 1.0)[::2, ::2]


def build_model_pyramid(model, num_levels=None, min_pts: int = 12) -> list:
    """階層ごとにテンプレートを縮小し、**その階層でモデルを作り直す**。

    num_levels=None なら自動で決める。打ち切りの基準は **粗い階層で残るモデル点数**。
    実測では「細さ」そのものではなくこの点数が効いていた
    (1 px の細線でもテンプレートが長ければ点は十分残る。
     壊れたのは点数が 9 まで落ちた小さいモデルのほうだった)。
    """
    t = model.get("template")
    if t is None:
        return [model]
    # **防御**: dict(model) で複製して pts/shape だけ差し替える呼び出しが在る
    # (find_scaled_shape_model 等)。その場合 template は元のままで shape と
    # 食い違うので、作り直すと誤った結果になる。食い違いを見たら平坦探索へ落とす。
    if tuple(t.shape) != tuple(model["shape"]):
        return [model]
    mg = model.get("min_grad", 0.1)
    mt = model.get("metric", "use_polarity")
    out = [model]
    cur = t
    while num_levels is None or len(out) < num_levels:
        nxt = pyr_down(cur)
        if min(nxt.shape) < 6:
            break
        m = create_shape_model(nxt, mg, mt)
        if len(m["pts"]) < min_pts:
            break
        out.append(m)
        cur = nxt
        if len(out) >= 6:
            break
    return out


def image_pyramid(image, n_levels: int) -> list:
    """画像を n_levels 段に縮小して返す(先頭が原寸)。

    **scale を何通り試しても画像階層は 1 回作れば足りる。**
    find_aniso_shape_model は scale を 9 通り見るので、毎回作り直すと
    探索本体より縮小のほうが高くつく。
    """
    pyr = [np.asarray(image, dtype=np.float64)]
    for _ in range(max(0, int(n_levels) - 1)):
        pyr.append(pyr_down(pyr[-1]))
    return pyr


def _scan_flat(model, field, step: int):
    """1 階層を全走査して最良の (score, row, col) を返す。"""
    gx, gy, mag = field
    H, W = mag.shape
    h, w = model["shape"]
    best = (-1.0, -1, -1)
    for r0 in range(h // 2, H - h // 2, step):
        for c0 in range(w // 2, W - w // 2, step):
            s = _score_at(model, gy, gx, mag, r0, c0)
            if s > best[0]:
                best = (s, r0, c0)
    return best


def _search_with_pyramid(models, pyr, fields, n_cand: int = 12):
    """モデル階層と画像階層を突き合わせ、最良の (score, row, col) を返す。

    models[i] は pyr[i] と同じ解像度。最粗階層を全走査して候補を n_cand 個残し、
    階層を下りながら近傍 5x5 だけ精密化する。**画像階層は呼び出し側の持ち物**
    なので、scale を変えて何度呼んでも縮小はやり直さない。
    """
    top = len(models) - 1
    mh, mw = models[top]["shape"]
    gxT, gyT, magT = fields[top]
    Ht, Wt = pyr[top].shape
    cand = []
    for r0 in range(mh // 2, max(mh // 2 + 1, Ht - mh // 2)):
        for c0 in range(mw // 2, max(mw // 2 + 1, Wt - mw // 2)):
            cand.append((_score_at(models[top], gyT, gxT, magT, r0, c0), r0, c0))
    if not cand:
        return None
    cand.sort(key=lambda z: -z[0])
    cand = cand[:n_cand]

    for L in range(top - 1, -1, -1):
        gxL, gyL, magL = fields[L]
        HL, WL = pyr[L].shape
        mhL, mwL = models[L]["shape"]
        nxt = []
        for _, r0, c0 in cand:
            for dr in (-2, -1, 0, 1, 2):
                for dc in (-2, -1, 0, 1, 2):
                    r, c = r0 * 2 + dr, c0 * 2 + dc
                    if not (mhL // 2 <= r < HL - mhL // 2
                            and mwL // 2 <= c < WL - mwL // 2):
                        continue
                    nxt.append((_score_at(models[L], gyL, gxL, magL, r, c), r, c))
        if not nxt:
            return None
        nxt.sort(key=lambda z: -z[0])
        cand = nxt[:n_cand]
    return cand[0]


def find_shape_model(model, image, min_score: float = 0.5, step: int = 2,
                     num_levels="auto", n_cand: int = 12, angles=None,
                     device: str = "cpu") -> dict:
    """モデルを画像中で探索し最良一致(行/列/角度/スコア)を返す(find_shape_model)。

    ``num_levels="auto"`` で **粗密探索(ピラミッドサーチ)** を使う。
    ``num_levels=0`` で従来どおりの平坦な全走査。

    ``angles`` に角度の並び(度、例 ``range(-30, 31, 10)``)を渡すと **回転も探索**する。
    HALCON の find_shape_model は Angle を返すが、この一族は角度 0 固定だった。回転は
    テンプレートを回してモデルを作り直す(点も勾配も一緒に回る)ことで各角度もピラミッドに
    乗る。``angles=None``(既定)は従来どおり角度 0 のみ(後方互換)。
    """
    img = np.asarray(image, dtype=np.float64)

    # 角度探索: テンプレートを各角度に回して掃引(scale と同じ機構)。
    if angles is not None and model.get("template") is not None:
        combos = [(float(a), 1.0, 1.0) for a in angles]
        b = _search_transforms(model, img, combos, min_score, step, n_cand,
                               device=device)
        if b is None:
            return {"row": -1, "col": -1, "column": -1, "angle": 0.0,
                    "score": 0.0, "found": False, "levels": 1}
        score, r, c, ang, _sr, _sc, lv = b
        return {"row": int(r), "col": int(c), "column": int(c),
                "angle": float(ang), "score": float(score),
                "found": score >= min_score, "levels": lv}

    if num_levels == 0 or model.get("template") is None:
        sc, r, c = _scan_flat(model, _grad_field(img), step)
        return {"row": r, "col": c, "column": c, "angle": 0.0,
                "score": sc, "found": sc >= min_score, "levels": 1}

    nl = None if num_levels == "auto" else int(num_levels)
    models = build_model_pyramid(model, nl)
    if len(models) == 1:
        return find_shape_model(model, image, min_score, step, num_levels=0)

    pyr = image_pyramid(img, len(models))
    fields = [_grad_field(a) for a in pyr]
    hit = _search_with_pyramid(models, pyr, fields, n_cand)
    if hit is None:
        return find_shape_model(model, image, min_score, step, num_levels=0)

    sc, r, c = hit
    # "col" と "column" の両方を返す。この家族は片方しか返しておらず、
    # find_local_deformable_model が rigid.get("column") を読んで **常に None**
    # を得ていた(実測で発覚)。HALCON の名前は Column なので両方載せる。
    return {"row": int(r), "col": int(c), "column": int(c), "angle": 0.0,
            "score": float(sc), "found": sc >= min_score, "levels": len(models)}


def zoom_model(model, scale_row: float, scale_col: float = None):
    """**テンプレートを拡大縮小してから、その解像度でモデルを作り直す**。

    以前この一族は ``model["pts"] * s`` と点の座標だけ伸縮した dict を組んでいた。
    それだと 3 つが同時に起きる:

    1. ``template`` を持たないのでピラミッドに乗れず、必ず平坦な全走査へ落ちる
    2. 勾配方向が元の解像度のまま。**異方 scale では法線の向きは実際に変わる**
       (座標を A で写すと法線は A^-T で写る)のに、変わらないままだった
    3. 縮めても点数が減らないので、小さい scale でも速くならない

    テンプレート側を zoom すれば HALCON の作り方(scale ごとにモデルを作る)と
    一致し、3 つとも消える。縮めすぎて意味を失う scale では None を返す。
    """
    if scale_col is None:
        scale_col = scale_row
    sr, sc = float(scale_row), float(scale_col)
    t = model.get("template")
    if t is None:
        # template を持たないモデル。従来どおり点だけ伸縮する(ピラミッドには乗らない)。
        pts = model["pts"] * np.array([sr, sc])
        return {"shape": (int(model["shape"][0] * sr), int(model["shape"][1] * sc)),
                "pts": pts.astype(int), "grad": model["grad"],
                "min_contrast": model.get("min_contrast", 0.0),
                "metric": model.get("metric", "use_polarity"),
                "scale_row": sr, "scale_col": sc}
    if abs(sr - 1.0) < 1e-9 and abs(sc - 1.0) < 1e-9:
        out = dict(model)
    else:
        z = ndimage.zoom(np.asarray(t, dtype=np.float64), (sr, sc), order=1)
        if min(z.shape) < 6:
            return None                      # 縮めすぎ。この scale は捨てる
        out = create_shape_model(z, model.get("min_grad", 0.1),
                                 model.get("metric", "use_polarity"))
    out["scale_row"], out["scale_col"] = sr, sc
    return out


def create_scaled_shape_model(template, min_grad: float = 0.1,
                              metric: str = "use_polarity") -> dict:
    """等方スケール形状モデル(create_scaled_shape_model)。"""
    m = create_shape_model(template, min_grad, metric)
    m["scaled"] = True
    return m


def rotate_model(model, angle_deg: float):
    """**テンプレートを回してから、その向きでモデルを作り直す**(create_shape_model)。

    zoom_model と同じ思想。回転で変わるのは点の座標だけではない —— **エッジの
    法線(勾配)も一緒に回る**。点だけ回して元の勾配を流用すると 45 度で
    score 0.688、テンプレを回して作り直すと 0.961(実測)。回転行列 R は直交だから
    R^-T = R で、法線も点と同じ R で回る(異方 scale の A^-T が R では A に一致する)。

    ``ndimage.rotate(reshape=False)`` で外形サイズは保つ。角度 0 は素通し。
    """
    a = float(angle_deg)
    t = model.get("template")
    if t is None or abs(a) < 1e-9:
        out = dict(model)
        out["angle"] = a
        return out
    tr = ndimage.rotate(np.asarray(t, dtype=np.float64), a, reshape=False)
    out = create_shape_model(tr, model.get("min_grad", 0.1),
                             model.get("metric", "use_polarity"))
    out["angle"] = a
    return out


def transform_model(model, angle: float = 0.0, scale_row: float = 1.0,
                    scale_col: float = 1.0):
    """回転 + スケールをまとめてテンプレートに施し、モデルを作り直す。

    順序は **回転 -> スケール**。テンプレートを一度だけ変換して作り直すので、
    点も勾配も正しく一緒に動く(zoom_model / rotate_model と同核)。
    縮めすぎた場合は None。
    """
    m = rotate_model(model, angle)
    if abs(scale_row - 1.0) > 1e-9 or abs(scale_col - 1.0) > 1e-9:
        m = zoom_model(m, scale_row, scale_col)
        if m is None:
            return None
        m["angle"] = float(angle)
    return m


def _transform_pyramids(model, combos):
    """(angle, sr, sc) ごとに **変換したテンプレートからモデル階層を作る**。

    返り値は [((angle, sr, sc), [models...]), ...]。潰れた変換は落とす。
    """
    per = []
    for (ang, sr, sc) in combos:
        tm = transform_model(model, ang, sr, sc)
        if tm is None:
            continue
        per.append(((ang, sr, sc), build_model_pyramid(tm)))
    return per


def _search_transforms_gpu(model, image, combos, device):
    """GPU で使えるなら (score, row, col, angle, sr, sc, 1) を返す。無理なら None。

    無理な条件(→ CPU にフォールバック): device が cuda でない / torch/GPU 不在 /
    テンプレート無し(点だけのモデルは変換を作り直せない) / metric が
    ``ignore_local_polarity``(点ごと abs は conv で表現できない)。
    """
    if device != "cuda":
        return None
    try:
        import shapematch_gpu as _g
    except Exception:
        return None
    if not _g.gpu_available():
        return None
    if model.get("template") is None:
        return None
    if model.get("metric", "use_polarity") == "ignore_local_polarity":
        return None
    b = _g.search_transforms(model, image, combos,
                             build_transform=transform_model, device="cuda")
    if b is None:
        return None
    score, r, c, ang, sr, sc = b
    return (score, r, c, ang, sr, sc, 1)   # GPU は全解像度なので levels=1


def _search_transforms(model, image, combos, min_score=0.5, step=2, n_cand=12,
                       device="cpu"):
    """(angle, sr, sc) を掃引して最良の (score, row, col, angle, sr, sc, levels)。

    **画像階層は必要な深さぶん 1 回だけ作り、全変換で使い回す。**
    変換ごとに縮小し直すと、探索より縮小のほうが高くつく(実測、scale で 3 割)。

    ``device="cuda"`` なら全変換を conv2d のバッチとして GPU で同時評価する
    (実測 34-88x、位置は CPU と一致)。GPU が使えない条件では静かに CPU へ戻る。
    """
    gpu = _search_transforms_gpu(model, image, combos, device)
    if gpu is not None:
        return gpu
    img = np.asarray(image, dtype=np.float64)
    per = _transform_pyramids(model, combos)
    if not per:
        return None
    depth = max(len(m) for _, m in per)
    pyr = image_pyramid(img, depth)
    fields = [_grad_field(a) for a in pyr]
    best = None
    for (ang, sr, sc), models in per:
        if len(models) == 1:
            hit = _scan_flat(models[0], fields[0], step)
        else:
            hit = _search_with_pyramid(models, pyr, fields, n_cand)
        if hit is None or hit[1] < 0:
            continue
        if best is None or hit[0] > best[0]:
            best = (hit[0], hit[1], hit[2], ang, sr, sc, len(models))
    return best


def _search_scales(model, image, combos, min_score=0.5, step=2, n_cand=12,
                   device="cpu"):
    """scale のみ掃引(後方互換)。内部は _search_transforms(angle=0)。

    返り値は従来どおり (score, row, col, scale_row, scale_col, levels)。
    """
    b = _search_transforms(model, image, [(0.0, sr, sc) for sr, sc in combos],
                           min_score, step, n_cand, device=device)
    if b is None:
        return None
    score, r, c, _ang, sr, sc, lv = b
    return (score, r, c, sr, sc, lv)


def find_scaled_shape_model(model, image, scales=(0.8, 1.0, 1.25),
                            min_score: float = 0.5, step: int = 2,
                            n_cand: int = 12, device: str = "cpu") -> dict:
    """スケールを変えながら最良一致を探索(find_scaled_shape_model)。

    scale ごとに **テンプレートを zoom してモデルを作り直す** ので、各 scale も
    ピラミッドサーチに乗る(以前は点だけ伸縮していたため必ず平坦走査だった)。
    ``device="cuda"`` で全 scale を GPU の conv2d バッチとして同時評価。
    """
    b = _search_scales(model, image, [(s, s) for s in scales], min_score, step,
                       n_cand, device=device)
    if b is None:
        return {"row": -1, "col": -1, "column": -1, "score": 0.0,
                "found": False, "scale": 1.0, "levels": 1}
    score, r, c, sr, _sc, lv = b
    return {"row": int(r), "col": int(c), "column": int(c), "score": float(score),
            "found": score >= min_score, "scale": sr, "levels": lv}


# ── 多インスタンス検出 / XLD 由来モデル / パラメータ決定・アクセサ ────────────── #
def _nms_from_map(score_map, min_score, max_matches, min_distance):
    """スコア地図から非最大抑制で上位を拾う。返り値は [(score, r, c), ...]。"""
    H, W = score_map.shape
    sm = score_map.copy()
    out = []
    for _ in range(int(max_matches)):
        idx = np.unravel_index(np.argmax(sm), sm.shape)
        s = float(sm[idx])
        if s < min_score:
            break
        out.append((s, int(idx[0]), int(idx[1])))
        r0 = max(0, idx[0] - min_distance); r1 = min(H, idx[0] + min_distance + 1)
        c0 = max(0, idx[1] - min_distance); c1 = min(W, idx[1] + min_distance + 1)
        sm[r0:r1, c0:c1] = -1.0
    return out


def _scan_level(model, field, step=1):
    """1 階層を全走査してスコア地図を返す(中心規約)。"""
    gx, gy, mag = field
    H, W = mag.shape
    mh, mw = model["shape"]
    score_map = np.full((H, W), -1.0)
    # **_score_at は (r0,c0) を中心として解釈する。** ここは以前 range(0, H-mh)
    # と左上規約で走査していたため 2 つ壊れていた(実測):
    #   (a) 右下の帯 [H-mh, H-mh//2) を一度も見ない -> 端の物体を丸ごと取り逃す
    #   (b) 上/左では model の半分が画像外に出て、見えている数点だけの平均が
    #       0.73 と出る -> min_score 0.5 を平気で超える偽陽性
    # 中心の有効範囲だけを走査すれば、model は常に全部画像内に入り両方消える。
    for r0 in range(mh // 2, H - mh // 2, step):
        for c0 in range(mw // 2, W - mw // 2, step):
            score_map[r0, c0] = _score_at(model, gy, gx, mag, r0, c0)
    return score_map


def _find_shape_models_gpu(model, image, min_score, max_matches, min_distance,
                           device):
    """GPU で使えるなら {"matches":..., "num":..., "levels":1} を返す。無理なら None。

    スコアマップ(重い)を GPU の conv2d で 1 発で作り、NMS(安い)は CPU の
    ``_nms_from_map`` を使い回す。ピラミッドの粗密は要らない —— conv が密で速く、
    全解像度のマップをそのまま NMS にかけられる。フォールバック条件は
    _search_transforms_gpu と同じ(cuda/GPU/template/metric)。
    """
    if device != "cuda":
        return None
    try:
        import shapematch_gpu as _g
    except Exception:
        return None
    if not _g.gpu_available():
        return None
    if model.get("template") is None:
        return None
    if model.get("metric", "use_polarity") == "ignore_local_polarity":
        return None
    sm = _g.score_maps([model], image, metric=model.get("metric", "use_polarity"),
                       mc=float(model.get("min_contrast", 0.0)),
                       device="cuda")[0]
    # CPU の _scan_level と同じ中心規約: model が全部画像内に入る内部だけを残し、
    # 端の部分被覆(偽陽性)を番兵 -1 で弾く。
    h, w = model["shape"]
    hh, ww = h // 2, w // 2
    guarded = np.full_like(sm, -1.0)
    guarded[hh:sm.shape[0] - hh, ww:sm.shape[1] - ww] = \
        sm[hh:sm.shape[0] - hh, ww:sm.shape[1] - ww]
    hits = _nms_from_map(guarded, min_score, max_matches, min_distance)
    return {"matches": [{"row": r, "column": c, "col": c, "score": s}
                        for s, r, c in hits], "num": len(hits), "levels": 1}


def find_shape_models(model, image, min_score=0.5, step=2, max_matches=10,
                      min_distance=5, num_levels="auto", n_cand=None,
                      device="cpu"):
    """複数インスタンスを非最大抑制つきで検出(find_shape_models)。

    ``num_levels="auto"`` で **粗密探索**。最粗階層を全走査して NMS で候補を
    拾い、各候補を独立に階層を下りて精密化する。単一インスタンス版と違い
    候補は 1 個に絞らない —— 絞ると 2 個目以降が消えるため。
    ``num_levels=0`` で従来どおりの平坦な全走査。

    ``device="cuda"`` で **スコアマップを GPU の conv2d で作り**、NMS は CPU で
    行う(GPU が使えない条件では静かに CPU の粗密探索へ戻る)。
    """
    gpu = _find_shape_models_gpu(model, image, min_score, max_matches,
                                 min_distance, device)
    if gpu is not None:
        return gpu
    img = np.asarray(image, np.float64)
    use_pyr = num_levels != 0 and model.get("template") is not None
    models = build_model_pyramid(
        model, None if num_levels == "auto" else int(num_levels)) if use_pyr else [model]

    if len(models) == 1:
        sm = _scan_level(model, _grad_field(img), step)
        hits = _nms_from_map(sm, min_score, max_matches, min_distance)
        return {"matches": [{"row": r, "column": c, "col": c, "score": s}
                            for s, r, c in hits], "num": len(hits), "levels": 1}

    pyr = image_pyramid(img, len(models))
    fields = [_grad_field(a) for a in pyr]
    top = len(models) - 1

    # 最粗階層: 全走査 -> NMS。**候補は多めに残す**。粗い階層の順位は当てにせず、
    # 「真の上位が候補集合に残るか」だけを頼りにする(docs/HIGHSPEED_VISION.md
    # の関門の結論。粗い階層の rho は 0.6 前後しかないが上位残存は 1.00)。
    k = int(n_cand) if n_cand else max(4 * int(max_matches), 20)
    md_top = max(1, int(min_distance) >> top)
    # 走査しなかった位置は -1 の番兵。0.0 を下限にして番兵だけ弾く
    # (実スコアは 0 以上なので、これで候補を減らしすぎることはない)。
    coarse = _nms_from_map(_scan_level(models[top], fields[top]), 0.0, k, md_top)

    # 各候補を独立に下ろす。単一版のように上位 n_cand で足切りすると、
    # 2 個目以降のインスタンスがここで消える。
    cand = [(s, r, c) for s, r, c in coarse]
    for L in range(top - 1, -1, -1):
        HL, WL = pyr[L].shape
        mhL, mwL = models[L]["shape"]
        gxL, gyL, magL = fields[L]
        nxt = []
        for _, r0, c0 in cand:
            b = None
            for dr in (-2, -1, 0, 1, 2):
                for dc in (-2, -1, 0, 1, 2):
                    r, c = r0 * 2 + dr, c0 * 2 + dc
                    if not (mhL // 2 <= r < HL - mhL // 2
                            and mwL // 2 <= c < WL - mwL // 2):
                        continue
                    v = _score_at(models[L], gyL, gxL, magL, r, c)
                    if b is None or v > b[0]:
                        b = (v, r, c)
            if b is not None:
                nxt.append(b)
        if not nxt:
            return find_shape_models(model, image, min_score, step, max_matches,
                                     min_distance, num_levels=0)
        cand = nxt

    # 原寸での最終 NMS。階層を下りた先で候補どうしが同じ場所へ寄ることがある。
    cand.sort(key=lambda z: -z[0])
    matches, taken = [], []
    for s, r, c in cand:
        if s < min_score:
            break
        if any(abs(r - rr) <= min_distance and abs(c - cc) <= min_distance
               for rr, cc in taken):
            continue
        taken.append((r, c))
        matches.append({"row": int(r), "column": int(c), "col": int(c),
                        "score": float(s)})
        if len(matches) >= int(max_matches):
            break
    return {"matches": matches, "num": len(matches), "levels": len(models)}


def find_ncc_models(model, image, min_score=0.5, max_matches=10, min_distance=5):
    """NCC モデルの複数インスタンス検出(find_ncc_models)。"""
    from matching import _ncc_map
    t = np.asarray(model["template"], np.float64)
    nccm = _ncc_map(t, np.asarray(image, np.float64))
    # find_ncc_model と同じく **中心** を返す(_ncc_map の添字は左上)。
    oh, ow = t.shape[0] // 2, t.shape[1] // 2
    H, W = nccm.shape; matches = []; sm = nccm.copy()
    for _ in range(int(max_matches)):
        idx = np.unravel_index(np.argmax(sm), sm.shape)
        if sm[idx] < min_score:
            break
        matches.append({"row": int(idx[0]) + oh, "column": int(idx[1]) + ow,
                        "col": int(idx[1]) + ow, "row_tl": int(idx[0]),
                        "col_tl": int(idx[1]), "score": float(sm[idx])})
        r0 = max(0, idx[0] - min_distance); r1 = min(H, idx[0] + min_distance + 1)
        c0 = max(0, idx[1] - min_distance); c1 = min(W, idx[1] + min_distance + 1)
        sm[r0:r1, c0:c1] = -1.0
    return {"matches": matches, "num": len(matches)}


def find_scaled_shape_models(model, image, scales=(0.8, 1.0, 1.25), min_score=0.5,
                             max_matches=10, step=2):
    """スケール探索つき複数インスタンス検出(find_scaled_shape_models)。"""
    # **scale は最良スコアで選ぶ。件数では選ばない。**
    # 以前は res["num"] > best["num"] で選んでいたので、合っていない scale が
    # 偽陽性を 1 件多く出しただけで勝ってしまった(実測: 真の scale 1.0 に対し
    # 0.8 が選ばれ、スコアも 0.80 に落ちた)。
    best = {"matches": [], "num": 0, "scale": 1.0, "score": -1.0}
    for s in scales:
        # **テンプレートを zoom してモデルを作り直す**(点だけ伸縮しない)。
        # これで各 scale もピラミッドに乗る。
        scaled = zoom_model(model, s)
        if scaled is None:
            continue
        res = find_shape_models(scaled, image, min_score, step=step,
                                max_matches=max_matches)
        top = max((m["score"] for m in res["matches"]), default=-1.0)
        if top > best["score"]:
            best = {**res, "scale": s, "score": top}
    return best


def _contour_to_template(contour):
    """XLD 輪郭(dict {shape, cs})をエッジ強度テンプレート画像へラスタライズ。"""
    H, W = contour["shape"]
    t = np.zeros((H, W))
    for a in contour["cs"]:
        rr = np.clip(a[:, 0].round().astype(int), 0, H - 1)
        cc = np.clip(a[:, 1].round().astype(int), 0, W - 1)
        t[rr, cc] = 1.0
    from scipy.ndimage import gaussian_filter
    return gaussian_filter(t, 1.0)


def create_shape_model_xld(contour, min_grad=0.1):
    """XLD 輪郭から形状モデルを作る(create_shape_model_xld)。"""
    return create_shape_model(_contour_to_template(contour), min_grad)


def create_scaled_shape_model_xld(contour, min_grad=0.1):
    """XLD 輪郭からスケール対応形状モデル(create_scaled_shape_model_xld)。"""
    from shapematch import create_scaled_shape_model
    return create_scaled_shape_model(_contour_to_template(contour), min_grad)


def create_aniso_shape_model_xld(contour, min_grad=0.1):
    """XLD 輪郭から異方性スケール形状モデル(create_aniso_shape_model_xld)。"""
    return create_aniso_shape_model(_contour_to_template(contour), min_grad)


def determine_shape_model_params(template):
    """テンプレートから推奨 min_grad/コントラストを自動決定(determine_shape_model_params)。"""
    t = np.asarray(template, np.float64)
    gx, gy, mag = _grad_field(t)
    return {"min_contrast": float(np.percentile(mag, 75) / (mag.max() + 1e-9)),
            "num_levels": int(max(1, np.log2(min(t.shape)) - 2))}


def get_shape_model_contours(model):
    """形状モデルのエッジ点を輪郭として返す(get_shape_model_contours)。"""
    return {"shape": model["shape"], "cs": [model["pts"].astype(float)]}


def get_shape_model_origin(model):
    """形状モデルの原点(重心)を返す(get_shape_model_origin)。"""
    c = model["pts"].mean(0)
    return {"row": float(c[0]), "column": float(c[1])}


def set_shape_model_origin(model, row, col):
    """形状モデルの参照原点を設定(set_shape_model_origin)。"""
    model = dict(model); model["origin"] = (float(row), float(col))
    return model


def create_cam_pose_look_at_point(cam_pos, look_at, up=(0, 0, 1)):
    """カメラ位置と注視点から look-at 姿勢(4x4)を構築(create_cam_pose_look_at_point)。"""
    cam_pos = np.asarray(cam_pos, float); look_at = np.asarray(look_at, float)
    up = np.asarray(up, float)
    z = look_at - cam_pos; z = z / (np.linalg.norm(z) + 1e-12)   # 前方
    x = np.cross(up, z); x = x / (np.linalg.norm(x) + 1e-12)     # 右
    y = np.cross(z, x)                                           # 下
    R = np.column_stack([x, y, z])
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = cam_pos
    return T


# ── matching: generic/aniso/local-deformable/descriptor/params ────────────────── #
def find_generic_shape_model(model, image, min_score=0.5, step=2):
    """汎用形状モデル検出(find_generic_shape_model)。find_shape_model の別名。"""
    return find_shape_model(model, image, min_score, step)


def find_aniso_shape_model(model, image, min_score=0.5,
                           scale_r=(0.9, 1.0, 1.1), scale_c=(0.9, 1.0, 1.1),
                           device: str = "cpu"):
    """行/列独立スケール(異方性)での形状モデル検出(find_aniso_shape_model)。"""
    combos = [(sr, sc) for sr in scale_r for sc in scale_c]
    # 行と列を別々に zoom したテンプレートからモデルを作り直す。**異方 scale では
    # エッジ法線の向きが実際に変わる** ので、点だけ伸縮して勾配を流用するのは
    # 近似ですらない(細長く潰した円の法線は元の円の法線と違う向きを向く)。
    b = _search_scales(model, image, combos, min_score, device=device)
    # 見つからない時も **同じ鍵** を返す。以前は {"found": False} だけだったので
    # 呼び出し側の res["row"] が KeyError で落ちた。
    if b is None:
        return {"row": -1, "col": -1, "column": -1, "score": 0.0,
                "found": False, "scale_row": 1.0, "scale_col": 1.0}
    score, r, c, sr, sc, lv = b
    return {"row": int(r), "col": int(c), "column": int(c), "score": float(score),
            "found": score >= min_score, "scale_row": sr, "scale_col": sc,
            "levels": lv}


def find_aniso_shape_models(model, image, min_score=0.5, max_matches=10,
                            scale_r=(0.9, 1.0, 1.1), scale_c=(0.9, 1.0, 1.1)):
    """異方性スケールでの複数インスタンス検出(find_aniso_shape_models)。

    **以前は scale を一切見ずに find_shape_models を素通ししていた**(名前が
    嘘をついていた)。scale ごとに zoom したモデルで検出し、最良スコアの
    scale を採る。
    """
    best = {"matches": [], "num": 0, "scale_row": 1.0, "scale_col": 1.0,
            "score": -1.0}
    for sr in scale_r:
        for sc in scale_c:
            zm = zoom_model(model, sr, sc)
            if zm is None:
                continue
            res = find_shape_models(zm, image, min_score, max_matches=max_matches)
            top = max((m["score"] for m in res["matches"]), default=-1.0)
            if top > best["score"]:
                best = {**res, "scale_row": sr, "scale_col": sc, "score": top}
    return best


def inspect_shape_model(model):
    """形状モデルのエッジ点数・広がり・原点を点検用に返す(inspect_shape_model)。"""
    pts = model["pts"]
    return {"num_points": len(pts), "extent": pts.max(0) - pts.min(0),
            "centroid": pts.mean(0).tolist(), "shape": model["shape"]}


def determine_ncc_model_params(template):
    """NCC モデルの推奨パラメータ(コントラスト/レベル数)を決定(determine_ncc_model_params)。"""
    t = np.asarray(template, float)
    return {"num_levels": int(max(1, np.log2(min(t.shape)) - 2)),
            "contrast": float(t.std())}


def determine_deformable_model_params(template):
    """変形モデルの推奨パラメータを決定(determine_deformable_model_params)。"""
    return determine_shape_model_params(template)


def adapt_shape_model_high_noise(template, min_grad=0.25, smooth=2.0):
    """高ノイズ向けに平滑化を強めた形状モデルを作る(adapt_shape_model_high_noise)。"""
    from scipy.ndimage import gaussian_filter
    return create_shape_model(gaussian_filter(np.asarray(template, float), smooth), min_grad)


def create_local_deformable_model(template, min_grad=0.1):
    """局所変形マッチング用モデル(テンプレート保持)(create_local_deformable_model)。"""
    t = np.asarray(template, float)
    return {"template": t, "shape": t.shape, "edge": create_shape_model(t, min_grad)}


def create_local_deformable_model_xld(contour, min_grad=0.1):
    """XLD 由来の局所変形モデル(create_local_deformable_model_xld)。"""
    return create_local_deformable_model(_contour_to_template(contour), min_grad)


def find_local_deformable_model(model, image, min_score=0.5):
    """剛体位置を粗く合わせた後、オプティカルフローで局所変形を推定
    (find_local_deformable_model)。変形ベクトル場を返す。"""
    rigid = find_shape_model(model["edge"], image, min_score)
    from filters_flow import optical_flow_mg
    t = model["template"]; H, W = t.shape
    # find_shape_model は "col" を返す。ここは "column" を読んでいたので既定値 0 に
    # 落ち、**常に画像の左端 [0:W] を切り出してフローを取っていた**(実測)。
    col = rigid.get("col", rigid.get("column", 0)) or 0
    r0 = int(rigid.get("row", 0)) - H // 2; c0 = int(col) - W // 2
    r0 = max(0, min(r0, image.shape[0] - H)); c0 = max(0, min(c0, image.shape[1] - W))
    patch = np.asarray(image, float)[r0:r0 + H, c0:c0 + W]
    flow = optical_flow_mg(t, patch, iterations=100)
    return {"row": rigid.get("row"), "column": int(col), "col": int(col),
            "score": rigid.get("score", 0.0), "deformation": flow}


def create_planar_uncalib_deformable_model(template, min_grad=0.1):
    """平面(未校正)変形モデル(create_planar_uncalib_deformable_model)。"""
    return create_local_deformable_model(template, min_grad)


def find_planar_uncalib_deformable_model(model, image, min_score=0.5):
    """平面未校正変形モデルの検出(find_planar_uncalib_deformable_model)。"""
    return find_local_deformable_model(model, image, min_score)


def create_planar_calib_deformable_model(template, cam_par, min_grad=0.1):
    """平面(校正済)変形モデル(create_planar_calib_deformable_model)。"""
    m = create_local_deformable_model(template, min_grad); m["cam_par"] = cam_par
    return m


def find_planar_calib_deformable_model(model, image, min_score=0.5):
    """平面校正済変形モデルの検出(find_planar_calib_deformable_model)。"""
    return find_local_deformable_model(model, image, min_score)


def create_planar_uncalib_deformable_model_xld(contour, min_grad=0.1):
    """XLD 由来の平面未校正変形モデル(create_planar_uncalib_deformable_model_xld)。"""
    return create_local_deformable_model(_contour_to_template(contour), min_grad)


def create_planar_calib_deformable_model_xld(contour, cam_par, min_grad=0.1):
    """XLD 由来の平面校正済変形モデル(create_planar_calib_deformable_model_xld)。"""
    m = create_local_deformable_model(_contour_to_template(contour), min_grad)
    m["cam_par"] = cam_par
    return m
