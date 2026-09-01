# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""visionlab — マシンビジョンの仮想環境。**部品を買う前に、ラインを組む前に。**

検査システムを立ち上げるときに本当に知りたいのは 1 つで、「**この構成で、狙う
欠陥をどこまで見つけられるか**」である。それを答えるのに、普通は部品を買い、
サンプルを集め、ラインを止めて試す。ここではそれを計算で先に済ませる。

一本に繋がる 5 段:

  1. **設計** — カメラ・レンズ・作動距離を決める(``visiondesign.system_geometry``)
  2. **限界** — 分解能・被写界深度・周辺光量の限界を閉形式で出す
     (``visiondesign.resolving_power`` / ``system_feasibility``)
  3. **仮想の部品** — 正常な表面の質感の上に、寸法を指定した欠陥を置く
     (``defectgen``。マスクは幾何から作るので**画素完全**)
  4. **撮像** — その光学系で実際に撮れる画像にする
     (``visiondesign.image_formation`` + 必要なら ``aug_*`` のセンサ雑音)
  5. **検査と判定** — 検査アルゴリズムを通し、**検出率が落ちる欠陥サイズ**を出す
     (:func:`inspection_sweep`)

2 の「限界」と 5 の「実測の検出率」は**別物**である点が肝心で、両方出すのが
この層の意味である。光学の限界は「原理的にそこに情報があるか」しか言わない。
実際に見つかるかは、表面の質感・コントラスト・雑音・アルゴリズムで決まり、
たいてい原理限界よりかなり手前で落ちる。設計をその 2 つの数字で語れると、
「レンズを変えるべきか、アルゴリズムを直すべきか」が分かれる。

**honest な限界**: 光輸送のシミュレーションではない(経路追跡も大域照明も測定
BRDF も無い)。鏡面・透明体はまさにそこが効く領域なので、この環境の予測は
そういう部品では外れる。欠陥は *appearance* のモデルであって材料物理ではない。
つまりここで出る検出率は **その仮定のもとでの上限の目安**であって、実機の保証
ではない。実機で測るまでは、設計の当たりを付ける道具として使うこと。
"""
from __future__ import annotations

import numpy as np

import defectgen
import visiondesign

__all__ = ["VisionSystem", "render_part", "inspection_sweep", "detection_report"]


class VisionSystem:
    """カメラ+レンズ+作動距離の 1 つの構成。**単位を持ち歩く器**。

    単位の取り違えはこの手の計算で最も多い誤りなので、値は必ず単位つきの名前で
    保持し、``geometry()`` / ``limits()`` は ``visiondesign`` に委譲する
    (式を二重に持たない)。
    """

    def __init__(self, focal_mm=50.0, working_distance_mm=300.0,
                 pixel_pitch_um=3.45, width_px=1024, height_px=1024,
                 f_number=5.6, wavelength_um=0.55, depth_tolerance_mm=1.0):
        # ★``float("50")`` は成功するので、``float()`` を通すだけでは文字列が
        # ミリメートルとして通り抜ける。``visiondesign`` 側は弾くが、ここで先に
        # float 化してしまうと **その検証に届く前に数値になってしまう**
        # (敵対的検証で実測: VisionSystem(focal_mm="50") が通った)。
        # 器の側でも同じ規律を持つ。
        def _n(value, name):
            if isinstance(value, (str, bytes, bool)):
                raise ValueError("%s must be a number, got %r" % (name, value))
            return float(value)

        self.focal_mm = _n(focal_mm, "focal_mm")
        self.working_distance_mm = _n(working_distance_mm, "working_distance_mm")
        self.pixel_pitch_um = _n(pixel_pitch_um, "pixel_pitch_um")
        for nm, v in (("width_px", width_px), ("height_px", height_px)):
            if isinstance(v, (str, bytes, bool)) or int(v) != v:
                raise ValueError("%s must be an integer, got %r" % (nm, v))
        self.width_px = int(width_px)
        self.height_px = int(height_px)
        self.f_number = _n(f_number, "f_number")
        self.wavelength_um = _n(wavelength_um, "wavelength_um")
        self.depth_tolerance_mm = _n(depth_tolerance_mm, "depth_tolerance_mm")
        # 残る妥当性(正値・焦点距離との関係)は visiondesign の検証に一本化する
        self._geo = visiondesign.system_geometry(
            self.focal_mm, self.working_distance_mm, self.pixel_pitch_um,
            self.width_px, self.height_px)

    def geometry(self):
        """視野・倍率・µm/画素。"""
        return dict(self._geo)

    def limits(self, defect_um):
        """この欠陥サイズに対する実現可能性(判定と理由)。"""
        return visiondesign.system_feasibility(
            defect_um, self.focal_mm, self.working_distance_mm,
            self.pixel_pitch_um, self.f_number, self.width_px, self.height_px,
            self.wavelength_um, self.depth_tolerance_mm)

    def um_per_pixel(self):
        return float(self._geo["um_per_pixel"])

    def px_for_um(self, size_um):
        """物理寸法 [µm] → 画素数。**設計と生成を繋ぐ唯一の換算点**。"""
        return float(size_um) / self.um_per_pixel()

    def capture(self, ideal_image, defocus_px=0.0, exposure=1.0, vignetting=True):
        """理想画像 → この系で実際に撮れる画像。"""
        return visiondesign.image_formation(
            ideal_image, f_number=self.f_number,
            pixel_pitch_um=self.pixel_pitch_um, wavelength_um=self.wavelength_um,
            defocus_px=defocus_px, vignetting=vignetting, exposure=exposure)

    def __repr__(self):
        g = self._geo
        return ("VisionSystem(f=%gmm, WD=%gmm, f/%g, %gum/px, FOV %.1fx%.1fmm)"
                % (self.focal_mm, self.working_distance_mm, self.f_number,
                   round(g["um_per_pixel"], 2), g["fov_w_mm"], g["fov_h_mm"]))


#: 欠陥の種類 → 生成器。物理寸法から画素寸法への換算は :func:`render_part` が行う。
_DEFECT_KINDS = {
    "scratch": defectgen.defect_scratch,
    "crack": defectgen.defect_crack,
    "pits": defectgen.defect_pits,
    "blob": defectgen.defect_blob,
}


def render_part(system, defect_um=100.0, kind="scratch", texture="orange_peel",
                texture_strength=0.06, contrast=-0.25, tile_px=256,
                defocus_px=0.0, seed=0):
    """仮想の部品を 1 枚撮る。→ ``(captured_image, mask, meta)``。

    *defect_um* は **物理寸法**で指定する(画素数ではない)。系の µm/画素で
    画素寸法へ換算するので、**同じ 100 µm の傷が、系を変えれば別の画素数になる**
    — それがこの環境で確かめたいことそのものである。

    マスクは撮像前の幾何から作る。撮像でぼけても**正解は動かない**ので、検出率
    を測る基準として使える。

    Raises ValueError: 未知の *kind*、換算後の欠陥が 1 画素未満、その他は
    ``defectgen`` / ``visiondesign`` の検証に従う。
    """
    if kind not in _DEFECT_KINDS:
        raise ValueError("kind must be one of %s, got %r"
                         % (sorted(_DEFECT_KINDS), kind))
    size_px = system.px_for_um(defect_um)
    if size_px < 1.0:
        raise ValueError(
            "a %g um defect is %.3f pixels at %.2f um/pixel — below one pixel it "
            "cannot be rendered, let alone detected; this is the design telling "
            "you the answer already" % (defect_um, size_px, system.um_per_pixel()))
    h = w = int(tile_px)
    bg = defectgen.surface_texture((h, w), texture, strength=texture_strength,
                                   seed=seed + 1000)
    if kind == "pits":
        ideal, mask = defectgen.defect_pits(
            (h, w), count=12, radius_px=max(0.5, size_px / 2.0),
            contrast=contrast, seed=seed)
    elif kind == "blob":
        ideal, mask = defectgen.defect_blob(
            (h, w), radius_px=max(0.5, size_px / 2.0), contrast=contrast, seed=seed)
    else:                                              # scratch / crack
        ideal, mask = _DEFECT_KINDS[kind](
            (h, w), length_px=min(size_px * 4.0, w * 0.8),
            width_px=max(1.0, size_px), contrast=contrast, seed=seed)
    composed = defectgen.composite_defect(bg, ideal, mask)
    captured = system.capture(composed, defocus_px=defocus_px)
    meta = {
        "defect_um": float(defect_um), "defect_px": size_px,
        "um_per_pixel": system.um_per_pixel(), "kind": kind,
        "measured": defectgen.defect_stats(mask, um_per_pixel=system.um_per_pixel()),
    }
    return captured, mask, meta


def _default_detector(image, background_sigma=2.5):
    """基準の検査アルゴリズム — 局所平均からの外れを拾うだけの素朴な検出器。

    わざと素朴にしてある。ここで良い数字を出すことが目的ではなく、**設計の善し悪し
    を比べる物差し**が要るだけだからである。実際の検査器を評価したいなら
    :func:`inspection_sweep` に自分の関数を渡す。
    """
    from scipy import ndimage
    img = np.asarray(image, np.float64)
    local = ndimage.uniform_filter(img, size=15)
    resid = img - local
    sd = float(resid.std())
    if sd <= 0.0:
        return np.zeros(img.shape, bool)               # 完全に平坦 = 検出なし
    return np.abs(resid) > background_sigma * sd


def inspection_sweep(system, defect_um_grid, kind="scratch", detector=None,
                     seeds=5, contrast=-0.25, texture_strength=0.06,
                     defocus_px=0.0, tile_px=256, min_iou=0.1):
    """欠陥サイズを掃引し、**実測の検出率**を出す。

    各サイズにつき *seeds* 枚を生成して検査器にかけ、正解マスクとの IoU が
    *min_iou* 以上なら検出とみなす。検出率と、光学の原理限界を並べて返すので、
    **「原理的には見えるが実際には見つからない」領域が数字で見える**。

    *detector* は ``image -> bool マスク`` の関数。省略すると素朴な基準検出器を
    使う(:func:`_default_detector`)。進化で得たパイプラインを渡すこともできる。

    Returns ``{"table": [...], "detection_limit_um": ..., "optical_limit_um": ...}``。
    ``detection_limit_um`` は検出率が 0.5 以上になる最小サイズで、どのサイズでも
    届かなければ ``None``(それも答えなので例外にしない)。

    Raises ValueError: グリッドが空/非正、*seeds* が正整数でない場合。
    """
    grid = np.atleast_1d(np.asarray(defect_um_grid, dtype=np.float64))
    if grid.ndim != 1 or grid.size == 0:
        raise ValueError("defect_um_grid must be a non-empty 1-D sequence")
    if not np.isfinite(grid).all() or (grid <= 0).any():
        raise ValueError("defect_um_grid must be positive and finite")
    if isinstance(seeds, bool) or int(seeds) != seeds or int(seeds) < 1:
        raise ValueError("seeds must be a positive integer, got %r" % (seeds,))
    det = _default_detector if detector is None else detector

    rows = []
    for size in np.sort(grid):
        hits, ious, skipped = 0, [], 0
        for s in range(int(seeds)):
            try:
                img, mask, _ = render_part(system, float(size), kind=kind,
                                           texture_strength=texture_strength,
                                           contrast=contrast, tile_px=tile_px,
                                           defocus_px=defocus_px, seed=s)
            except ValueError:
                # 1 画素未満などで描けないサイズ。**黙って 0 件に混ぜない**
                skipped += 1
                continue
            pred = np.asarray(det(img))
            if pred.shape != mask.shape or pred.dtype != bool:
                pred = np.asarray(pred).astype(bool).reshape(mask.shape)
            inter = float(np.sum(pred & mask))
            union = float(np.sum(pred | mask))
            iou = inter / union if union > 0 else 0.0
            ious.append(iou)
            hits += int(iou >= min_iou)
        evaluated = int(seeds) - skipped
        rows.append({
            "defect_um": float(size),
            "defect_px": system.px_for_um(size),
            "detection_rate": (hits / evaluated) if evaluated else None,
            "mean_iou": (float(np.mean(ious)) if ious else None),
            "evaluated": evaluated, "unrenderable": skipped,
            "optical_verdict": system.limits(float(size))["verdict"],
        })
    detected = [r["defect_um"] for r in rows
                if r["detection_rate"] is not None and r["detection_rate"] >= 0.5]
    optical = visiondesign.detectability_limit(
        grid, system.focal_mm, system.working_distance_mm, system.pixel_pitch_um,
        system.f_number, system.width_px, system.height_px, system.wavelength_um,
        system.depth_tolerance_mm)
    return {
        "table": rows,
        "detection_limit_um": (min(detected) if detected else None),
        "optical_limit_um": optical["limit_um"],
        "limited_by": optical["limited_by"],
        "system": repr(system),
    }


def detection_report(sweep):
    """掃引の結果を人が読む文章にする。**都合の良い要約をしない**。

    光学の限界と実測の検出限界を並べ、両者が離れているときはそれを名指しする
    — 離れているなら直すべきはレンズではなくアルゴリズム(または照明)だからで、
    そこを取り違えると高い部品を買って解決しない。
    """
    lines = [sweep["system"]]
    opt, det = sweep["optical_limit_um"], sweep["detection_limit_um"]
    lines.append("optical limit  : %s (%s-limited)"
                 % ("%.1f um" % opt if opt else "not reached on this grid",
                    sweep["limited_by"]))
    lines.append("detection limit: %s"
                 % ("%.1f um" % det if det else "not reached on this grid"))
    if opt and det:
        ratio = det / opt
        lines.append("gap            : detection needs %.1fx the optical limit"
                     % ratio)
        if ratio > 2.0:
            lines.append("  -> the optics already carry the information; the gap "
                         "is contrast/noise/algorithm, not the lens.")
        else:
            lines.append("  -> detection is close to the optical limit; to do "
                         "better, change the optics (magnification or aperture).")
    elif opt and not det:
        lines.append("  -> resolvable in principle but never detected: look at "
                     "contrast, illumination and the detector, not the lens.")
    for r in sweep["table"]:
        rate = "n/a" if r["detection_rate"] is None else "%.0f%%" % (100 * r["detection_rate"])
        note = "" if not r["unrenderable"] else "  (%d unrenderable)" % r["unrenderable"]
        lines.append("  %8.1f um (%5.1f px)  detected %4s  iou %s  optics: %s%s"
                     % (r["defect_um"], r["defect_px"], rate,
                        "n/a" if r["mean_iou"] is None else "%.2f" % r["mean_iou"],
                        r["optical_verdict"], note))
    return "\n".join(lines)
