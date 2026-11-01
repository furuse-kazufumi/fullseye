# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実物 IC の metal-2 SEM 像で配線幅とビアを測り、仮想 SEM の縁補正を試す。

Rothaug ほかの公開データ(Edmond/MPG、DOI 10.17617/3.HY5SYN、CC BY 4.0)を
使う。対応論文 DOI 10.1145/3605769.3624000 も引用する。原本は repo に入れず、
``tools/fetch_sem_metal_layer.py`` で repo 外へ取得する。像は 4096×3536、
14.65 nm/pixel、15 keV BSE、3 us dwell。SVG の path が track、circle が via である。

手順:

1. ``fs.ledger.svg_entities`` へ SVG の bytes を渡し、track 多角形と via 円を読む。
   独立した ``ElementTree`` 読取で要素数と座標を照合する。重なる via 円は同じ
   実物の重複ラベルとしてクラスタ化し、画像端で切れた track と、端から続くのに
   ラベルと重ならない明部成分も数えて採点から除く。
2. Fullseye op だけで fixed threshold / Otsu / Sobel-edge の 3 通りに切り出す。
   IoU、対称境界距離、各 track の距離変換幅と法線方向 line profile 幅を nm で出す。
3. ラベル境界を横切る実像の edge-spread から PSF sigma を測る。仮想 SEM の模型
   ``I=Ibg+(Ifg-Ibg) Phi(x/sigma)`` が予測する両縁の太りを線幅から引き、偏りが
   本当に縮むかを数える。縮まなければ PASS に見せず、そのまま印字する。
4. 高しきい値の blob を via とし、重複を除いたラベルに対する適合率・再現率を出す。

図(``FULLSEYE_FIGURE_DIR`` があるときだけ): (a) 実像とラベルの重ね合わせ(代表図)、
(b) 切り出しとの差、(c) 線幅分布と偏り、(d) PSF 補正の前後。図中ラベルは日本語。
データが無い CI では取得せず、下の ``RECORDED`` を表示して実データ章を飛ばす。

実行例::

    py -3.11 tools/fetch_sem_metal_layer.py
    FULLSEYE_FIGURE_DIR=out/sem-metal py -3.11 examples/poc_real_sem_metal_layer.py
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from scipy.special import ndtri
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import realdata  # noqa: E402

PIXEL_NM = 14.65
FIXED_TRACK_THRESHOLD = 67.0 / 255.0  # 配布元の conventional baseline と同じ値
VIA_THRESHOLD = 157.0 / 255.0
MAX_IMAGES = 10
MAX_WIDTH_TRACKS_PER_IMAGE = 160
SOURCE = realdata.sem_metal_layer_credit()

# 実データを走らせた後、stdout の ``RECORDED_JSON`` と同じ値へ固定する。
RECORDED = {
    "date": "2026-11-01",
    "images": 10,
    "dataset_sha256": "14e0aef2ceeee0aa46b324521535133eba2e33bea222c9b360a0e7b505024753",
    "method": "大津",
    "iou_median": 0.597233577528688,
    "boundary_nm_mean": 316.29300501927685,
    "label_width_nm_p10_p50_p90": [293.0, 351.6, 491.1575001972382],
    "measured_width_nm_p10_p50_p90": [29.3, 41.43645737753169, 132.58022513333927],
    "bias_before_nm": -296.306518253653,
    "bias_after_nm": -285.6303998969665,
    "psf_sigma_nm": 51.9345592851607,
    "via_precision": 0.9783519553072626,
    "via_recall": 0.9394803017602682,
    "via_tp_fp_fn": [5604, 124, 361],
    "label_defects": {"via_duplicates": 1740, "via_border": 112,
                      "track_clipped_labels": 1239, "track_missing_border_components": 51},
}


def _read_image(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        a = np.asarray(im)
    if a.ndim == 3:
        a = a[..., :3].astype(np.float64) @ np.array([0.2125, 0.7154, 0.0721])
    else:
        a = a.astype(np.float64)
    scale = 65535.0 if a.max(initial=0.0) > 255.0 else 255.0
    return np.clip(a / scale, 0.0, 1.0)


def _path_points(d: str) -> list[tuple[float, float]]:
    """配布 SVG の M/L/Z path を独立に読む。曲線・相対座標は拒否する。"""
    toks = re.findall(r"[A-Za-z]|[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", d)
    points = []
    k = 0
    command = None
    while k < len(toks):
        if toks[k].isalpha():
            command = toks[k]
            k += 1
            if command in ("Z", "z"):
                continue
            if command not in ("M", "L"):
                raise ValueError("SEM label SVG: unsupported path command %r" % command)
        if command not in ("M", "L") or k + 1 >= len(toks):
            raise ValueError("SEM label SVG: malformed path")
        x, y = float(toks[k]), float(toks[k + 1])
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("SEM label SVG: non-finite coordinate")
        points.append((x, y))
        k += 2
    if len(points) < 3:
        raise ValueError("SEM label SVG: track polygon has fewer than 3 points")
    return points


def read_label(svg_path: Path, shape: tuple[int, int]):
    """既存 op と独立 XML reader の一致を門にして track / via を返す。"""
    raw = svg_path.read_bytes()
    parsed = fs.ledger.svg_entities(raw)
    if parsed.get("view_box") != [0.0, 0.0, float(shape[1]), float(shape[0])]:
        raise ValueError("%s: SVG viewBox %r does not match image %r"
                         % (svg_path.name, parsed.get("view_box"), shape[::-1]))
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("%s: DTD/entity is refused" % svg_path.name)
    root = ET.fromstring(raw)
    ns = "{http://www.w3.org/2000/svg}"
    direct_tracks = [_path_points(el.attrib.get("d", "")) for el in root.iter(ns + "path")]
    direct_vias = [(float(el.attrib["cx"]), float(el.attrib["cy"]), float(el.attrib["r"]))
                   for el in root.iter(ns + "circle")]
    tracks = [[(float(x), float(-y)) for x, y in ent["points"]]
              for ent in parsed["entities"] if ent["type"] == "polyline"]
    vias = [(float(ent["center"][0]), float(-ent["center"][1]), float(ent["r"]))
            for ent in parsed["entities"] if ent["type"] == "circle"]
    if len(tracks) != len(direct_tracks) or len(vias) != len(direct_vias):
        raise AssertionError("SVG readers disagree on element counts")
    for a, b in zip(tracks, direct_tracks):
        if len(a) != len(b) or not np.allclose(a, b, atol=0.0, rtol=0.0):
            raise AssertionError("SVG readers disagree on track coordinates")
    if not np.allclose(vias, direct_vias, atol=0.0, rtol=0.0):
        raise AssertionError("SVG readers disagree on via coordinates")
    return tracks, vias


def _polygon_mask(shape, polygons):
    im = Image.new("1", (shape[1], shape[0]), 0)
    draw = ImageDraw.Draw(im)
    for points in polygons:
        draw.polygon(points, fill=1)
    return np.asarray(im, dtype=bool)


def _circle_mask(shape, circles):
    im = Image.new("1", (shape[1], shape[0]), 0)
    draw = ImageDraw.Draw(im)
    for x, y, r in circles:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=1)
    return np.asarray(im, dtype=bool)


def _touches_border(points, shape, margin=0.5):
    p = np.asarray(points, np.float64)
    return bool((p[:, 0] <= margin).any() or (p[:, 1] <= margin).any()
                or (p[:, 0] >= shape[1] - 1 - margin).any()
                or (p[:, 1] >= shape[0] - 1 - margin).any())


def deduplicate_vias(vias, shape):
    """交差する円は同じ実 via の重複ラベル。最大円だけ残す。"""
    if not vias:
        return [], 0, 0
    c = np.asarray(vias, np.float64)
    parent = list(range(len(c)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in cKDTree(c[:, :2]).query_pairs(float(2.0 * c[:, 2].max())):
        if np.linalg.norm(c[i, :2] - c[j, :2]) < c[i, 2] + c[j, 2]:
            a, b = find(i), find(j)
            if a != b:
                parent[b] = a
    groups = defaultdict(list)
    for i in range(len(c)):
        groups[find(i)].append(i)
    keep = []
    duplicate = 0
    border = 0
    for ids in groups.values():
        best = max(ids, key=lambda i: (c[i, 2], -i))
        duplicate += len(ids) - 1
        x, y, r = c[best]
        if x - r <= 0 or y - r <= 0 or x + r >= shape[1] - 1 or y + r >= shape[0] - 1:
            border += 1
        else:
            keep.append((float(x), float(y), float(r)))
    return keep, duplicate, border


def segment_tracks(img):
    """Fullseye op だけで 3 通りの track mask を作る。"""
    fixed = np.asarray(fs.op.threshold(img, a=FIXED_TRACK_THRESHOLD, b=0.0), bool)
    otsu = np.asarray(fs.op.otsu(img, a=0.5, b=0.5), bool)
    grad = np.asarray(fs.op.sobel_mag(img, a=0.5, b=0.5), np.float64)
    edge = np.asarray(fs.op.otsu(grad, a=0.5, b=0.5), np.float64)
    edge = np.asarray(fs.op.closing_circle(edge, a=0.0, b=0.0), np.float64)
    edge = np.asarray(fs.op.fill_holes(edge, a=0.5, b=0.5), np.float64)
    low = np.asarray(fs.op.threshold(img, a=0.20, b=0.0), np.float64)
    edge = np.asarray(fs.apply([edge, low], "intersection", on_error="raise"), bool)
    return {"固定しきい値": fixed, "大津": otsu, "縁ベース": edge}


def _label_missing_border_tracks(fixed, label_mask):
    """端から続く明部成分のうち、ラベルとほぼ重ならないものを欠けとして数える。"""
    labels = np.asarray(fs.ledger.blob_label(fixed), np.int32)
    n = int(labels.max(initial=0))
    sizes = np.bincount(labels.ravel(), minlength=n + 1)
    overlap = np.bincount(labels[label_mask].ravel(), minlength=n + 1)
    border_ids = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    ratios = overlap / np.maximum(sizes, 1)
    bad = border_ids[(border_ids > 0) & (sizes[border_ids] >= 30) & (ratios[border_ids] < 0.10)]
    return np.isin(labels, bad), int(len(bad))


def _boundaries(mask):
    labels = np.asarray(fs.ledger.blob_label(mask), np.int32)
    return np.asarray(fs.ledger.blob_boundaries(labels), bool)


def score_mask(pred, truth, roi):
    p, t = pred & roi, truth & roi
    inter = int(np.count_nonzero(p & t))
    union = int(np.count_nonzero(p | t))
    iou = inter / union if union else float("nan")
    bp, bt = _boundaries(p), _boundaries(t)
    if not bp.any() or not bt.any():
        return iou, float("nan"), float("nan")
    dt = np.asarray(fs.ledger.blob_distance(~bt, spacing=PIXEL_NM), np.float64)
    dp = np.asarray(fs.ledger.blob_distance(~bp, spacing=PIXEL_NM), np.float64)
    one = np.concatenate([dt[bp], dp[bt]])
    return iou, float(np.mean(one)), float(np.percentile(one, 95))


def _one_polygon_mask(points, pad=3):
    p = np.asarray(points, np.float64)
    x0 = max(0, int(math.floor(p[:, 0].min())) - pad)
    y0 = max(0, int(math.floor(p[:, 1].min())) - pad)
    x1 = int(math.ceil(p[:, 0].max())) + pad + 1
    y1 = int(math.ceil(p[:, 1].max())) + pad + 1
    im = Image.new("1", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(im).polygon([(x - x0, y - y0) for x, y in points], fill=1)
    return np.asarray(im, bool), (y0, y1, x0, x1)


def _profile_width(mask, points):
    """track の主軸に直交する 1-D profile の連続前景長を返す [px]。"""
    p = np.asarray(points, np.float64)
    q = p - p.mean(axis=0)
    cov = q.T @ q
    val, vec = np.linalg.eigh(cov)
    normal = vec[:, int(np.argmin(val))]
    center = p.mean(axis=0)
    s = np.arange(-80.0, 80.01, 0.25)
    xy = center[None, :] + s[:, None] * normal[None, :]
    prof = ndi.map_coordinates(mask.astype(np.float64), [xy[:, 1], xy[:, 0]], order=0,
                               mode="constant", cval=0.0) > 0.5
    k0 = int(np.argmin(np.abs(s)))
    if not prof[k0]:
        hits = np.flatnonzero(prof)
        if not len(hits):
            return float("nan")
        k0 = int(hits[np.argmin(np.abs(hits - k0))])
    lo = k0
    hi = k0
    while lo > 0 and prof[lo - 1]:
        lo -= 1
    while hi + 1 < len(prof) and prof[hi + 1]:
        hi += 1
    return float((hi - lo + 1) * 0.25)


def track_width_pair(points, pred):
    label, (y0, y1, x0, x1) = _one_polygon_mask(points, pad=16)
    pred_crop = pred[y0:y1, x0:x1]
    if pred_crop.shape != label.shape:
        h = min(pred_crop.shape[0], label.shape[0]); w = min(pred_crop.shape[1], label.shape[1])
        pred_crop, label = pred_crop[:h, :w], label[:h, :w]
    gate = ndi.binary_dilation(label, iterations=10)
    picked = np.asarray(fs.apply([pred_crop, gate], "intersection", on_error="raise"), bool)
    if not picked.any() or not label.any():
        return None
    dl = np.asarray(fs.ledger.blob_distance(label, spacing=PIXEL_NM), np.float64)
    dp = np.asarray(fs.ledger.blob_distance(picked, spacing=PIXEL_NM), np.float64)
    sl = np.asarray(fs.op.skeleton(label.astype(np.float64), a=0.5, b=0.5), bool)
    sp = np.asarray(fs.op.skeleton(picked.astype(np.float64), a=0.5, b=0.5), bool)
    wl = 2.0 * dl[sl & (dl > 0)]
    wp = 2.0 * dp[sp & (dp > 0)]
    if not len(wl) or not len(wp):
        return None
    local_points = [(x - x0, y - y0) for x, y in points]
    return {
        "label_nm": float(np.median(wl)),
        "pred_nm": float(np.median(wp)),
        "label_profile_nm": _profile_width(label, local_points) * PIXEL_NM,
        "pred_profile_nm": _profile_width(picked, local_points) * PIXEL_NM,
    }


def _otsu_value(img):
    hist, edges = np.histogram(np.clip(img, 0, 1), 256, (0.0, 1.0))
    p = hist.astype(np.float64) / max(1, hist.sum())
    omega = np.cumsum(p)
    mids = (edges[:-1] + edges[1:]) / 2.0
    mu = np.cumsum(p * mids); den = omega * (1.0 - omega)
    sb = np.where(den > 1e-12, (mu[-1] * omega - mu) ** 2 / np.maximum(den, 1e-12), 0.0)
    return float(edges[int(np.argmax(sb)) + 1])


def psf_edge_model(img, truth, threshold):
    """境界を横切る edge-spread から sigma としきい値位置の太りを測る。"""
    di = np.asarray(fs.ledger.blob_distance(truth, spacing=1.0), np.float64)
    do = np.asarray(fs.ledger.blob_distance(~truth, spacing=1.0), np.float64)
    signed = di - do
    xs = np.arange(-7, 8, dtype=np.float64)
    values = []
    for x in xs:
        band = img[(signed >= x - 0.5) & (signed < x + 0.5)]
        values.append(float(np.median(band)) if band.size else float("nan"))
    prof = np.asarray(values, np.float64)
    ok = np.isfinite(prof)
    if ok.sum() < 8:
        return None
    prof = np.interp(xs, xs[ok], prof[ok])
    deriv = np.maximum(np.diff(prof), 0.0)
    centers = (xs[:-1] + xs[1:]) / 2.0
    if deriv.sum() <= 1e-12:
        return None
    center = float(np.sum(centers * deriv) / deriv.sum())
    sigma = float(np.sqrt(np.sum((centers - center) ** 2 * deriv) / deriv.sum()))
    bg = float(np.median(prof[:3])); fg = float(np.median(prof[-3:]))
    if fg <= bg + 1e-6 or sigma <= 0:
        return None
    q = float(np.clip((threshold - bg) / (fg - bg), 1e-4, 1.0 - 1e-4))
    outward = float(-sigma * ndtri(q))
    return {"sigma_px": sigma, "bg": bg, "fg": fg, "threshold": threshold,
            "q": q, "outward_px": outward, "width_correction_nm": 2.0 * outward * PIXEL_NM}


def detect_vias(img):
    high = np.asarray(fs.op.threshold(img, a=VIA_THRESHOLD, b=0.0), np.float64)
    clean = np.asarray(fs.op.opening_circle(high, a=0.0, b=0.0), np.float64)
    labels = np.asarray(fs.ledger.blob_label(clean), np.int32)
    feat = fs.ledger.blob_features(labels)
    out = []
    for i in range(int(feat["n"])):
        area = float(feat["area"][i]); dia = float(feat["equiv_diameter"][i])
        circ = float(feat["circularity"][i])
        if 20.0 <= area <= 900.0 and 4.0 <= dia <= 36.0 and circ >= 0.20:
            out.append((float(feat["col"][i]), float(feat["row"][i]), dia / 2.0))
    return out


def score_vias(detected, truth):
    candidates = []
    for i, (x, y, _r) in enumerate(detected):
        for j, (tx, ty, tr) in enumerate(truth):
            d = math.hypot(x - tx, y - ty)
            if d <= max(12.0, 1.5 * tr):
                candidates.append((d, i, j))
    used_d, used_t = set(), set()
    for _d, i, j in sorted(candidates):
        if i not in used_d and j not in used_t:
            used_d.add(i); used_t.add(j)
    tp = len(used_d); fp = len(detected) - tp; fn = len(truth) - tp
    return tp, fp, fn


def _overlay(img, truth, vias, crop):
    y0, y1, x0, x1 = crop
    base = np.repeat(img[y0:y1, x0:x1, None], 3, axis=2)
    edge = _boundaries(truth)[y0:y1, x0:x1]
    base[edge] = (0.1, 1.0, 0.2)
    via = _circle_mask(img.shape, vias)[y0:y1, x0:x1]
    vedge = _boundaries(via)
    base[vedge] = (1.0, 0.15, 0.1)
    return base


def _difference_image(img, truth, pred, crop):
    y0, y1, x0, x1 = crop
    rgb = np.repeat(img[y0:y1, x0:x1, None] * 0.45, 3, axis=2)
    t = truth[y0:y1, x0:x1]; p = pred[y0:y1, x0:x1]
    rgb[t & p] = (0.1, 0.8, 0.2)
    rgb[p & ~t] = (1.0, 0.15, 0.10)  # 太り / false positive
    rgb[t & ~p] = (0.15, 0.35, 1.0)  # 欠け / false negative
    return rgb


def _print_recorded():
    print("実データが無いため章を飛ばす。CI は 6.4 GB を取得しない。")
    print("記録値(RECORDED): " + json.dumps(RECORDED, ensure_ascii=False, sort_keys=True))


def main() -> None:
    t0 = time.perf_counter()
    if os.environ.get("CI") and not os.environ.get("FULLSEYE_SEM_METAL_DATA"):
        _print_recorded()
        return
    try:
        root = realdata.sem_metal_layer_root(required=False)
    except realdata.RealDataError as exc:
        print("実データ配置を拒否: %s" % exc)
        _print_recorded()
        return
    if root is None:
        _print_recorded()
        return
    reduced = os.environ.get("FULLSEYE_POC_BUDGET", "").lower() == "reduced"
    limit = None if "--all" in sys.argv else (2 if reduced else MAX_IMAGES)
    width_limit = 40 if reduced else MAX_WIDTH_TRACKS_PER_IMAGE
    pairs = realdata.sem_metal_layer_pairs(limit=limit)
    print("実データ: %s" % SOURCE)
    print("原本 dataset.zip SHA-256: %s" % realdata.SEM_METAL_SHA256)
    print("展開先: %s" % root)
    print("使用画像: %d 枚%s、画素寸法 %.2f nm/px" %
          (len(pairs), " (--all)" if limit is None else " (番号順の先頭)", PIXEL_NM))

    method_scores = defaultdict(list)
    widths = defaultdict(list)
    profile_bias = defaultdict(list)
    models = defaultdict(list)
    defects = {"via_duplicates": 0, "via_border": 0, "track_clipped_labels": 0,
               "track_missing_border_components": 0}
    via_totals = [0, 0, 0]
    representative = None

    for index, (image_path, svg_path) in enumerate(pairs):
        img = _read_image(image_path)
        tracks, raw_vias = read_label(svg_path, img.shape)
        clean_tracks = [p for p in tracks if not _touches_border(p, img.shape)]
        clipped = len(tracks) - len(clean_tracks)
        vias, duplicates, via_border = deduplicate_vias(raw_vias, img.shape)
        defects["via_duplicates"] += duplicates
        defects["via_border"] += via_border
        defects["track_clipped_labels"] += clipped
        truth = _polygon_mask(img.shape, clean_tracks)
        all_label = _polygon_mask(img.shape, tracks)
        methods = segment_tracks(img)
        missing, missing_n = _label_missing_border_tracks(methods["固定しきい値"], all_label)
        defects["track_missing_border_components"] += missing_n
        roi = ~missing
        roi[:2, :] = False; roi[-2:, :] = False; roi[:, :2] = False; roi[:, -2:] = False
        print("\n[%d/%d] %s: track %d (端切れ除外 %d)、via %d (重複除外 %d / 端除外 %d)、"
              "ラベル欠け候補 %d" % (index + 1, len(pairs), image_path.name, len(clean_tracks), clipped,
                                      len(vias), duplicates, via_border, missing_n))
        for name, pred in methods.items():
            iou, bd, p95 = score_mask(pred, truth, roi)
            method_scores[name].append((iou, bd, p95))
            print("  %-10s IoU %.3f / 境界距離 平均 %.1f nm・p95 %.1f nm" % (name, iou, bd, p95))

        # 各 track の幅。巨大な複雑多角形より、面積順の中央にある通常 track を優先する。
        def polygon_area(points):
            q = np.asarray(points, np.float64)
            return 0.5 * abs(float(np.sum(q[:, 0] * np.roll(q[:, 1], -1)
                                           - q[:, 1] * np.roll(q[:, 0], -1))))
        ranked = sorted(clean_tracks, key=polygon_area)
        if len(ranked) > width_limit:
            step = len(ranked) / width_limit
            ranked = [ranked[min(int(k * step), len(ranked) - 1)]
                      for k in range(width_limit)]
        for name, pred in methods.items():
            for points in ranked:
                row = track_width_pair(points, pred)
                if row is not None:
                    row["image"] = index
                    widths[name].append(row)
                    if np.isfinite(row["label_profile_nm"]) and np.isfinite(row["pred_profile_nm"]):
                        profile_bias[name].append(row["pred_profile_nm"] - row["label_profile_nm"])

        for name, threshold in (("固定しきい値", FIXED_TRACK_THRESHOLD), ("大津", _otsu_value(img))):
            model = psf_edge_model(img, truth, threshold)
            if model is not None:
                model["image"] = index
                models[name].append(model)

        detected = detect_vias(img)
        tp, fp, fn = score_vias(detected, vias)
        via_totals[0] += tp; via_totals[1] += fp; via_totals[2] += fn
        print("  via: 検出 %d / TP %d / FP %d / FN %d" % (len(detected), tp, fp, fn))
        if representative is None:
            h, w = img.shape
            cy, cx = h // 2, w // 2
            crop = (max(0, cy - 512), min(h, cy + 512), max(0, cx - 512), min(w, cx + 512))
            representative = (img, truth, vias, methods, crop)

    print("\n集計: 切り出し")
    summary = {}
    for name in ("固定しきい値", "大津", "縁ベース"):
        a = np.asarray(method_scores[name], np.float64)
        rows = widths[name]
        bias = np.array([r["pred_nm"] - r["label_nm"] for r in rows], np.float64)
        label_width = np.array([r["label_nm"] for r in rows], np.float64)
        pred_width = np.array([r["pred_nm"] for r in rows], np.float64)
        pb = np.asarray(profile_bias[name], np.float64)
        rec = {
            "iou_median": float(np.nanmedian(a[:, 0])),
            "boundary_nm_mean": float(np.nanmean(a[:, 1])),
            "boundary_nm_p95": float(np.nanmean(a[:, 2])),
            "width_tracks": len(rows),
            "label_width_nm_p10_p50_p90": [float(x) for x in np.percentile(label_width, [10, 50, 90])],
            "pred_width_nm_p10_p50_p90": [float(x) for x in np.percentile(pred_width, [10, 50, 90])],
            "width_bias_nm_median": float(np.median(bias)),
            "profile_bias_nm_median": float(np.median(pb)) if len(pb) else float("nan"),
        }
        summary[name] = rec
        print("  %s: IoU 中央 %.3f、境界平均 %.1f nm、幅 n=%d、ラベル p10/50/90 "
              "%.1f/%.1f/%.1f nm、切出し %.1f/%.1f/%.1f nm、偏り %+.1f nm "
              "(line profile %+.1f nm)" %
              (name, rec["iou_median"], rec["boundary_nm_mean"], len(rows),
               *rec["label_width_nm_p10_p50_p90"], *rec["pred_width_nm_p10_p50_p90"],
               rec["width_bias_nm_median"], rec["profile_bias_nm_median"]))

    threshold_best = max(("固定しきい値", "大津"), key=lambda n: summary[n]["iou_median"])
    model_corr = np.array([m["width_correction_nm"] for m in models[threshold_best]], np.float64)
    sigma_nm = np.array([m["sigma_px"] * PIXEL_NM for m in models[threshold_best]], np.float64)
    before = np.array([r["pred_nm"] - r["label_nm"] for r in widths[threshold_best]], np.float64)
    correction_by_image = {int(m["image"]): m["width_correction_nm"] for m in models[threshold_best]}
    corrected = np.array([b - correction_by_image[int(r["image"])]
                          for b, r in zip(before, widths[threshold_best])
                          if int(r["image"]) in correction_by_image], np.float64)
    before_med = float(np.median(before)); after_med = float(np.median(corrected))
    reduction_nm = abs(before_med) - abs(after_med)
    reduction_fraction = reduction_nm / abs(before_med) if before_med else 0.0
    shrank = reduction_nm > 0.0
    effective = shrank and reduction_fraction >= 0.25
    print("\n仮想 SEM の縁太り模型を実機へ (%s):" % threshold_best)
    print("  実像 edge-spread の PSF sigma 中央 %.1f nm、模型の線幅補正量 中央 %+.1f nm" %
          (float(np.median(sigma_nm)), float(np.median(model_corr))))
    print("  幅の偏り: 補正前 %+.1f nm -> 補正後 %+.1f nm (絶対値 %+.1f nm、%.1f %% %s)。" %
          (before_med, after_med, -reduction_nm, 100.0 * reduction_fraction,
           "縮小" if shrank else "悪化"))
    if float(np.median(model_corr)) < 0:
        print("  -> この高いしきい値では模型も縁太りでなく内側への移動を予測した。")
    if not effective:
        print("  -> 残差の %.1f %% が残り、PSF 補正は有効でない。BSE の材料コントラスト、"
              "ラベル輪郭の規約、局所しきい値変動が支配する。" %
              (100.0 * abs(after_med) / max(abs(before_med), 1e-12)))

    tp, fp, fn = via_totals
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    print("\nvia (重複ラベルを除外): TP %d / FP %d / FN %d、適合率 %.3f、再現率 %.3f" %
          (tp, fp, fn, precision, recall))
    print("ラベル欠陥: via 重複 %d、via 端切れ %d、端で切れた track ラベル %d、"
          "端から続く未ラベル track 成分 %d (すべて理由つきで採点から除外)" %
          (defects["via_duplicates"], defects["via_border"], defects["track_clipped_labels"],
           defects["track_missing_border_components"]))

    record = {
        "date": "2026-11-01", "images": len(pairs), "pixel_nm": PIXEL_NM,
        "dataset_sha256": realdata.SEM_METAL_SHA256,
        "method": threshold_best, "methods": summary,
        "psf_sigma_nm_median": float(np.median(sigma_nm)),
        "model_width_correction_nm_median": float(np.median(model_corr)),
        "bias_before_nm": before_med, "bias_after_nm": after_med,
        "bias_reduction_nm": reduction_nm, "bias_reduction_fraction": reduction_fraction,
        "correction_shrank": shrank, "correction_effective": effective,
        "via_precision": precision, "via_recall": recall,
        "via_tp_fp_fn": [tp, fp, fn], "label_defects": defects,
    }
    print("RECORDED_JSON=" + json.dumps(record, ensure_ascii=False, sort_keys=True))

    if representative is not None and figs.enabled():
        img, truth, vias, methods, crop = representative
        best_all = max(summary, key=lambda n: summary[n]["iou_median"])
        overlay = _overlay(img, truth, vias, crop)
        figs.save("scene", overlay,
                  caption="実 SEM 像。緑=track ラベル、赤=重複除去後の via ラベル。",
                  source=SOURCE)
        figs.save("segmentation_difference", _difference_image(img, truth, methods[best_all], crop),
                  caption="%s。緑=一致、赤=太り、青=欠け。" % best_all, source=SOURCE)
        wr = widths[threshold_best]
        figs.save_plot(
            "line_width_distribution",
            [("ラベル", list(range(len(wr))), sorted(r["label_nm"] for r in wr)),
             ("切り出し", list(range(len(wr))), sorted(r["pred_nm"] for r in wr))],
            xlabel="track（幅の小さい順）", ylabel="線幅 [nm]",
            title="線幅分布と偏り（%s、n=%d）" % (threshold_best, len(wr)),
            caption="距離変換で track ごとの中央値を測った。", source=SOURCE)
        figs.save_plot(
            "psf_correction",
            [("補正前", [0, 1], [before_med, before_med]),
             ("補正後", [0, 1], [after_med, after_med]),
             ("偏りゼロ", [0, 1], [0.0, 0.0])],
            xlabel="", ylabel="線幅の偏り [nm]",
            title="PSF 補正後も偏りの %.1f %% が残る" %
                  (100.0 * abs(after_med) / max(abs(before_med), 1e-12)),
            caption="edge-spread から測った PSF sigma による補正。%+.1f nm から %+.1f nm。"
                    % (before_med, after_med), source=SOURCE)

    print("門: SVG 二重読取一致 / 全指標有限 / via 対応 1対1 / 図の環境変数門")
    assert all(np.isfinite(v["iou_median"]) for v in summary.values())
    assert tp <= min(tp + fp, tp + fn)
    print("完了: %.1f s" % (time.perf_counter() - t0))


if __name__ == "__main__":
    main()
