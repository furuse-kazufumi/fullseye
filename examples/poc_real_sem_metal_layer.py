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
   IoU、対称境界距離、ラベルの主中心線上の等間隔な法線方向断面幅を
   nm で出す。両端と曲がり角は除き、ラベルと切り出しを同じ断面で測る。
3. Otsu 切り出し自身の境界を横切る edge-spread から、ラベルを使わず PSF sigma と
   しきい値位置を測る。ラベルを使う推定は 10 枚を 5/5 に分けて逆側へだけ適用する。
   同じ画像・同じラベルへ戻す循環値は参考行に隔離する。
4. ``sem_line_profile`` / ``sem_cd_measure`` の 15 keV BSE 模型へ 14.65 nm の
   標本間隔と 350 nm の線を入れ、予測される幅偏りを実測と比べる。データに無い
   材料・断面は仮定を明記し、模型に入らない条件を一致と取り違えない。
5. 高しきい値の blob を via とし、重複を除いたラベルに対する適合率・再現率を出す。

図(``FULLSEYE_FIGURE_DIR`` があるときだけ): (a) 実像とラベルの重ね合わせ(代表図)、
(b) 切り出しとの差、(c) 線幅分布と偏り、(d) PSF 補正の前後。図中ラベルは日本語。
データが無い CI では取得せず、下の ``RECORDED`` を表示して実データ章を飛ばす。

経緯: 初版は切り出しのざらついた縁から生えたスケルトンの枝上で距離変換の
中央値を取り、ラベルと異なる量を比べていた。そのため旧版の大きな負の幅偏りは
計測手順の誤りであり、この版で同一断面の対応比較に取り直した。次版では、同じ
ラベルから補正量と補正後誤差を求めた循環評価も修正し、像単独推定を主結果とした。

実行例::

    py -3.11 tools/fetch_sem_metal_layer.py
    FULLSEYE_FIGURE_DIR=out/sem-metal py -3.11 examples/poc_real_sem_metal_layer.py
"""
from __future__ import annotations

import heapq
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
import semsim as SM  # noqa: E402

PIXEL_NM = 14.65
FIXED_TRACK_THRESHOLD = 67.0 / 255.0  # 配布元の conventional baseline と同じ値
VIA_THRESHOLD = 157.0 / 255.0
MAX_IMAGES = 10
MAX_WIDTH_TRACKS_PER_IMAGE = 160
PROFILE_STEP_PX = 8.0
PROFILE_SAMPLE_PX = 0.25
PROFILE_HALF_LENGTH_PX = 80.0
SOURCE = realdata.sem_metal_layer_credit()

# 実データを走らせた後、stdout の ``RECORDED_JSON`` と同じ値へ固定する。
RECORDED = {
    "date": "2026-11-01",
    "images": 10,
    "dataset_sha256": "14e0aef2ceeee0aa46b324521535133eba2e33bea222c9b360a0e7b505024753",
    "method": "大津",
    "iou_median": 0.8194012531006987,
    "boundary_nm_mean": 58.074351193503766,
    "label_width_nm_p10_p50_p90": [293.0, 380.90000000000003, 536.1900000000004],
    "measured_width_nm_p10_p50_p90": [263.7, 351.6, 518.9762500000002],
    "bias_before_nm": -14.649999999999977,
    "bias_after_nm": -7.776317219744855,
    "bias_reduction_fraction": 0.4691933638399408,
    "correction_effective": True,
    "psf_sigma_nm": 47.19316203771437,
    "correction_evaluation": {
        "label_free": {"correction_nm": -3.2590907839626007,
                       "before_nm": -14.649999999999977,
                       "after_nm": -7.776317219744855},
        "split_5_5": {"train_corrections_nm": [-1.4087537956515248,
                                                 -17.793311801127576],
                      "before_nm": -14.649999999999977,
                      "after_nm": -0.5191881988724241},
        "same_image_circular_reference": {"correction_nm": -8.043655672201684,
                                           "before_nm": -14.649999999999977,
                                           "after_nm": 3.1433118011275987},
    },
    "virtual_sem": {"energy_kev": 15.0, "detector": "BSE", "pixel_nm": 14.65,
                    "true_width_nm": 350.0, "predicted_width_nm": 339.51851017301385,
                    "predicted_edge_inflation_nm": -10.481489826986149,
                    "proxy": "Cu/Si, height 40 nm, sidewall 88 deg, beam sigma 1 nm"},
    "raw_skeleton_pixels_per_major_axis_label_pred": [1.0689945741812077,
                                                         6.798318698173031],
    "raw_skeleton_endpoints_label_pred": [2.0, 46.0],
    "profile_distance_delta_px_label_pred": [0.9999999999999984,
                                               1.0000000000000022],
    "via_precision": 0.9783519553072626,
    "via_recall": 0.9394803017602682,
    "via_tp_fp_fn": [5604, 124, 361],
    "label_defects": {"via_duplicates": 1740, "via_border": 112,
                      "track_clipped_labels": 1239, "track_missing_border_components": 51,
                      "track_partial_border_components": 7},
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
    """端から続く track のラベル欠けを数え、欠け部分の ROI を返す。

    配布元が明記する「tracks spanning multiple images」に対応する。成分全体が
    未ラベルの場合だけでなく、端に続く一本の一部だけがラベルになった場合も
    「部分欠け」として数える。部分欠けではラベル近傍の切り出しは残し、
    ラベルから 12 px より離れた未注釈区間だけを採点から除く。
    """
    labels = np.asarray(fs.ledger.blob_label(fixed), np.int32)
    n = int(labels.max(initial=0))
    sizes = np.bincount(labels.ravel(), minlength=n + 1)
    overlap = np.bincount(labels[label_mask].ravel(), minlength=n + 1)
    border_ids = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
    ratios = overlap / np.maximum(sizes, 1)
    valid = border_ids[(border_ids > 0) & (sizes[border_ids] >= 30)]
    missing_ids = valid[ratios[valid] < 0.10]
    missing = np.isin(labels, missing_ids)
    near_label = ndi.binary_dilation(label_mask, iterations=12)
    far_sizes = np.bincount(labels[~near_label].ravel(), minlength=n + 1)
    partial_ids = valid[(ratios[valid] >= 0.10) & (far_sizes[valid] >= 30)]
    if len(partial_ids):
        missing |= np.isin(labels, partial_ids) & ~near_label
    return missing, int(len(missing_ids)), int(len(partial_ids))


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


def _clean_width_mask(mask):
    """幅測定前にラベルと切り出しの両方へ同じ平滑化を施す。"""
    out = np.asarray(fs.op.opening_circle(mask.astype(np.float64), a=0.0, b=0.0), np.float64)
    out = np.asarray(fs.op.closing_circle(out, a=0.34, b=0.0), np.float64)
    out = np.asarray(fs.op.fill_holes(out, a=0.5, b=0.5), np.float64)
    return out > 0.5


def _skeleton_graph(mask):
    """スケルトンの 8 近傍グラフと次数を返す。"""
    skel = np.asarray(fs.op.skeleton(mask.astype(np.float64), a=0.5, b=0.5), bool)
    coords = np.argwhere(skel)
    if not len(coords):
        return skel, coords, [], np.empty(0, np.int32)
    index = np.full(skel.shape, -1, np.int32)
    index[coords[:, 0], coords[:, 1]] = np.arange(len(coords), dtype=np.int32)
    graph = [[] for _ in range(len(coords))]
    for i, (y, x) in enumerate(coords):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if (dy == 0 and dx == 0) or not (0 <= y + dy < skel.shape[0]
                                                   and 0 <= x + dx < skel.shape[1]):
                    continue
                j = int(index[y + dy, x + dx])
                if j >= 0:
                    graph[i].append((j, math.hypot(dx, dy)))
    degree = np.asarray([len(row) for row in graph], np.int32)
    return skel, coords, graph, degree


def _dijkstra_farthest(graph, start, candidates=None):
    dist = np.full(len(graph), np.inf, np.float64)
    previous = np.full(len(graph), -1, np.int32)
    dist[start] = 0.0
    queue = [(0.0, int(start))]
    while queue:
        d, i = heapq.heappop(queue)
        if d != dist[i]:
            continue
        for j, weight in graph[i]:
            nd = d + weight
            if nd < dist[j]:
                dist[j] = nd
                previous[j] = i
                heapq.heappush(queue, (nd, j))
    ids = np.flatnonzero(np.isfinite(dist)) if candidates is None else np.asarray(candidates)
    ids = ids[np.isfinite(dist[ids])]
    farthest = int(ids[np.argmax(dist[ids])]) if len(ids) else int(start)
    return farthest, dist, previous


def _main_centerline(mask):
    """ラベルスケルトンの最長経路を (x, y) 順で返す。"""
    skel, coords, graph, degree = _skeleton_graph(mask)
    if not len(coords):
        return np.empty((0, 2), np.float64), np.empty(0), skel, degree
    ends = np.flatnonzero(degree == 1)
    candidates = ends if len(ends) >= 2 else None
    start = int(ends[0]) if len(ends) else 0
    a, _dist, _prev = _dijkstra_farthest(graph, start, candidates)
    b, _dist, previous = _dijkstra_farthest(graph, a, candidates)
    path = [b]
    while path[-1] != a and previous[path[-1]] >= 0:
        path.append(int(previous[path[-1]]))
    path.reverse()
    xy = coords[np.asarray(path, np.int32)][:, ::-1].astype(np.float64)
    arc = np.zeros(len(xy), np.float64)
    if len(xy) > 1:
        arc[1:] = np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))
    return xy, arc, skel, degree


def _centerline_sections(label):
    """両端と曲がり角を除いた等間隔の (中心, 法線) を作る。"""
    path, arc, skel, degree = _main_centerline(label)
    if len(path) < 3 or arc[-1] <= 0:
        return [], skel, degree
    distance = ndi.distance_transform_edt(label)
    center_width = 2.0 * float(np.median(distance[skel])) if skel.any() else 0.0
    margin = max(8.0, 0.75 * center_width)
    if arc[-1] <= 2.0 * margin + PROFILE_STEP_PX:
        margin = max(3.0, 0.20 * arc[-1])
    targets = np.arange(margin, arc[-1] - margin + 1e-9, PROFILE_STEP_PX)
    sections = []
    for target in targets:
        i = int(np.argmin(np.abs(arc - target)))
        before = int(np.argmin(np.abs(arc - max(0.0, arc[i] - 6.0))))
        after = int(np.argmin(np.abs(arc - min(arc[-1], arc[i] + 6.0))))
        vb = path[i] - path[before]
        va = path[after] - path[i]
        nb, na = np.linalg.norm(vb), np.linalg.norm(va)
        if nb < 2.0 or na < 2.0 or float(np.dot(vb, va) / (nb * na)) < math.cos(math.radians(25.0)):
            continue
        tangent = path[after] - path[before]
        tangent /= np.linalg.norm(tangent)
        normal = np.array([-tangent[1], tangent[0]], np.float64)
        sections.append((path[i], normal))
    return sections, skel, degree


def _profile_width(mask, center, normal):
    """中心を含む 1-D 断面の連続前景長を返す [px]。"""
    s = np.arange(-PROFILE_HALF_LENGTH_PX, PROFILE_HALF_LENGTH_PX + 1e-9,
                  PROFILE_SAMPLE_PX)
    xy = np.asarray(center)[None, :] + s[:, None] * np.asarray(normal)[None, :]
    prof = ndi.map_coordinates(mask.astype(np.float64), [xy[:, 1], xy[:, 0]], order=0,
                               mode="constant", cval=0.0) > 0.5
    k0 = int(np.argmin(np.abs(s)))
    if not prof[k0]:
        return 0.0
    lo = k0
    hi = k0
    while lo > 0 and prof[lo - 1]:
        lo -= 1
    while hi + 1 < len(prof) and prof[hi + 1]:
        hi += 1
    return float((hi - lo + 1) * PROFILE_SAMPLE_PX)


def _centerline_distance_width(mask, sections):
    """同じ断面上の局所中心で測る距離変換幅 [px]。"""
    if not sections:
        return float("nan")
    distance = ndi.distance_transform_edt(mask)
    values = []
    offsets = np.arange(-PROFILE_HALF_LENGTH_PX, PROFILE_HALF_LENGTH_PX + 1.0)
    for center, normal in sections:
        xy = np.rint(np.asarray(center)[None, :] + offsets[:, None] * normal[None, :]).astype(int)
        inside = ((xy[:, 0] >= 0) & (xy[:, 0] < mask.shape[1])
                  & (xy[:, 1] >= 0) & (xy[:, 1] < mask.shape[0]))
        foreground = np.zeros(len(offsets), bool)
        foreground[inside] = mask[xy[inside, 1], xy[inside, 0]]
        k0 = len(offsets) // 2
        if not foreground[k0]:
            values.append(0.0)
            continue
        lo = hi = k0
        while lo > 0 and foreground[lo - 1]:
            lo -= 1
        while hi + 1 < len(foreground) and foreground[hi + 1]:
            hi += 1
        run_xy = xy[lo:hi + 1]
        d = float(np.max(distance[run_xy[:, 1], run_xy[:, 0]]))
        # EDT は画素中心から背景画素中心までなので、直径の連続前景長に
        # 合わせて 1 px のセル幅を戻す。
        values.append(0.0 if d <= 0.0 else 2.0 * d + 1.0)
    return float(np.median(values))


def _raw_skeleton_diagnostics(mask):
    """枝荒れの証拠となるスケルトン画素/主軸長と端点数。"""
    skel, coords, _graph, degree = _skeleton_graph(mask)
    if not len(coords):
        return {"pixels_per_major_axis": float("nan"), "endpoints": 0}
    xy = coords[:, ::-1].astype(np.float64)
    centered = xy - xy.mean(axis=0)
    _values, vectors = np.linalg.eigh(centered.T @ centered)
    projection = centered @ vectors[:, -1]
    major_axis = max(1.0, float(projection.max() - projection.min() + 1.0))
    return {"pixels_per_major_axis": float(len(coords) / major_axis),
            "endpoints": int(np.count_nonzero(degree == 1))}


def _prepare_track_width(points, shape):
    label, (y0, y1, x0, x1) = _one_polygon_mask(points, pad=16)
    h = min(label.shape[0], shape[0] - y0)
    w = min(label.shape[1], shape[1] - x0)
    label = label[:h, :w]
    raw_label_diag = _raw_skeleton_diagnostics(label)
    label = _clean_width_mask(label)
    if not label.any():
        return None
    sections, _skel, _degree = _centerline_sections(label)
    if not sections:
        return None
    label_profiles = np.asarray([_profile_width(label, center, normal)
                                 for center, normal in sections], np.float64)
    valid = label_profiles > 0
    if not valid.any():
        return None
    return {"bounds": (y0, y0 + h, x0, x0 + w),
            "gate": ndi.binary_dilation(label, iterations=12), "sections": sections,
            "valid": valid, "label_px": float(np.median(label_profiles[valid])),
            "label_distance_px": _centerline_distance_width(label, sections),
            "raw_label_diag": raw_label_diag}


def _measure_prepared_track(prepared, pred):
    y0, y1, x0, x1 = prepared["bounds"]
    pred_crop = pred[y0:y1, x0:x1]
    picked_raw = np.asarray(fs.apply([pred_crop, prepared["gate"]],
                                     "intersection", on_error="raise"), bool)
    raw_pred_diag = _raw_skeleton_diagnostics(picked_raw)
    picked = _clean_width_mask(picked_raw)
    if not picked.any():
        return None
    sections = prepared["sections"]
    pred_profiles = np.asarray([_profile_width(picked, center, normal)
                                for center, normal in sections], np.float64)
    valid = prepared["valid"]
    label_px = prepared["label_px"]
    pred_px = float(np.median(pred_profiles[valid]))
    pred_skeleton_px = _centerline_distance_width(picked, sections)
    raw_label_diag = prepared["raw_label_diag"]
    return {
        "label_nm": label_px * PIXEL_NM,
        "pred_nm": pred_px * PIXEL_NM,
        "sections": int(np.count_nonzero(valid)),
        "label_skeleton_nm": prepared["label_distance_px"] * PIXEL_NM,
        "pred_skeleton_nm": pred_skeleton_px * PIXEL_NM,
        "raw_label_skeleton_pixels_per_major_axis": raw_label_diag["pixels_per_major_axis"],
        "raw_pred_skeleton_pixels_per_major_axis": raw_pred_diag["pixels_per_major_axis"],
        "raw_label_skeleton_endpoints": raw_label_diag["endpoints"],
        "raw_pred_skeleton_endpoints": raw_pred_diag["endpoints"],
    }


def track_width_pair(points, pred):
    prepared = _prepare_track_width(points, pred.shape)
    return None if prepared is None else _measure_prepared_track(prepared, pred)


def synthetic_width_gate():
    """300 nm 相当の点雑音付き帯で断面測定を検査する。"""
    truth = np.zeros((96, 192), bool)
    truth[38:58, 20:172] = True  # 20 px = 293 nm; 300 nm に 0.48 px の帯
    noisy = truth.copy()
    noisy[37, 24:168:9] = True
    noisy[58, 29:168:11] = True
    noisy[38, 35:168:13] = False
    points = [(20, 38), (171, 38), (171, 57), (20, 57)]
    row = track_width_pair(points, noisy)
    if row is None:
        raise AssertionError("synthetic width gate produced no measurement")
    truth_px = 300.0 / PIXEL_NM
    label_px = row["label_nm"] / PIXEL_NM
    pred_px = row["pred_nm"] / PIXEL_NM
    skeleton_px = row["pred_skeleton_nm"] / PIXEL_NM
    assert abs(label_px - truth_px) <= 1.0, (label_px, truth_px)
    assert abs(pred_px - truth_px) <= 1.0, (pred_px, truth_px)
    assert abs(pred_px - skeleton_px) <= 1.0 + 1e-9, (pred_px, skeleton_px)
    return {"truth_px": truth_px, "label_px": label_px, "pred_px": pred_px,
            "skeleton_px": skeleton_px}


def _otsu_value(img):
    hist, edges = np.histogram(np.clip(img, 0, 1), 256, (0.0, 1.0))
    p = hist.astype(np.float64) / max(1, hist.sum())
    omega = np.cumsum(p)
    mids = (edges[:-1] + edges[1:]) / 2.0
    mu = np.cumsum(p * mids); den = omega * (1.0 - omega)
    sb = np.where(den > 1e-12, (mu[-1] * omega - mu) ** 2 / np.maximum(den, 1e-12), 0.0)
    return float(edges[int(np.argmax(sb)) + 1])


def psf_edge_model(img, truth, threshold):
    """ラベル境界を横切る edge-spread 模型（分割検証・循環参考用）。"""
    return _psf_edge_model_from_boundary(img, truth, threshold, uses_label=True)


def psf_edge_model_image_only(img, segmented, threshold):
    """切り出し自身の境界から edge-spread を取り、ラベルなしで補正量を出す。

    境界までの距離は Fullseye の ``blob_distance`` を内外へ通す。補正量の推定には
    ``segmented`` と ``img`` しか使わず、正解ラベルは補正後の採点だけに使う。
    """
    return _psf_edge_model_from_boundary(img, segmented, threshold, uses_label=False)


def _psf_edge_model_from_boundary(img, boundary_mask, threshold, *, uses_label):
    """任意の二値境界を横切る edge-spread の共通実装。"""
    boundary_mask = np.asarray(boundary_mask, bool)
    di = np.asarray(fs.ledger.blob_distance(boundary_mask, spacing=1.0), np.float64)
    do = np.asarray(fs.ledger.blob_distance(~boundary_mask, spacing=1.0), np.float64)
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
            "q": q, "outward_px": outward, "width_correction_nm": 2.0 * outward * PIXEL_NM,
            "uses_label": bool(uses_label)}


def evaluate_corrections(width_rows, image_models, label_models):
    """像単独・5/5 分割・同一画像（循環）の補正を同じ幅行で比べる。"""
    before = np.asarray([r["pred_nm"] - r["label_nm"] for r in width_rows], np.float64)
    images = sorted({int(r["image"]) for r in width_rows})
    if len(images) < 2:
        raise ValueError("correction evaluation needs at least two images")
    split = len(images) // 2
    first, second = set(images[:split]), set(images[split:])
    image_corr = {int(m["image"]): float(m["width_correction_nm"]) for m in image_models}
    label_corr = {int(m["image"]): float(m["width_correction_nm"]) for m in label_models}
    train_first = float(np.median([label_corr[i] for i in first if i in label_corr]))
    train_second = float(np.median([label_corr[i] for i in second if i in label_corr]))

    def collect(kind):
        b, a, corrections = [], [], []
        for value, row in zip(before, width_rows):
            image = int(row["image"])
            if kind == "image_only":
                correction = image_corr.get(image)
            elif kind == "split":
                correction = train_second if image in first else train_first
            else:
                correction = label_corr.get(image)
            if correction is None:
                continue
            b.append(float(value)); a.append(float(value - correction)); corrections.append(correction)
        b = np.asarray(b, np.float64); a = np.asarray(a, np.float64)
        before_med = float(np.median(b)); after_med = float(np.median(a))
        reduction = abs(before_med) - abs(after_med)
        return {"before_nm": before_med, "after_nm": after_med,
                "correction_nm_median": float(np.median(corrections)),
                "reduction_nm": reduction,
                "reduction_fraction": reduction / abs(before_med) if before_med else 0.0,
                "rows": int(len(a))}

    return {"image_only": collect("image_only"), "split": collect("split"),
            "same_image": collect("same_image"),
            "split_train_correction_nm": [train_first, train_second],
            "split_images": [sorted(first), sorted(second)]}


def virtual_sem_prediction():
    """既存 op の 15 keV BSE 模型による、明記した代理断面の幅偏り予測。"""
    width_nm = 350.0
    profile = SM.sem_line_profile(
        "CU", "SI", 15.0, width_nm=width_nm, height_nm=40.0, sidewall_deg=88.0,
        beam_sigma_nm=1.0, x_half_range_nm=500.0, x_step_nm=PIXEL_NM,
        electrons_per_point=900, seed=1)
    measured = SM.sem_cd_measure(
        np.stack([profile["x_nm"], profile["bse"]], axis=1), method="threshold",
        smooth_nm=1.5)
    return {"energy_kev": 15.0, "detector": "BSE", "pixel_nm": PIXEL_NM,
            "true_width_nm": width_nm, "predicted_width_nm": float(measured["width_nm"]),
            "predicted_edge_inflation_nm": float(measured["width_nm"] - width_nm),
            "line_material": "CU", "substrate": "SI", "height_nm": 40.0,
            "sidewall_deg": 88.0, "beam_sigma_nm": 1.0,
            "electrons_per_point": 900}


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


def _difference_image(img, truth, pred, roi, crop):
    y0, y1, x0, x1 = crop
    rgb = np.repeat(img[y0:y1, x0:x1, None] * 0.45, 3, axis=2)
    t = truth[y0:y1, x0:x1]; p = pred[y0:y1, x0:x1]
    rgb[t & p] = (0.1, 0.8, 0.2)
    rgb[p & ~t] = (1.0, 0.15, 0.10)  # 太り / false positive
    rgb[t & ~p] = (0.15, 0.35, 1.0)  # 欠け / false negative
    excluded = ~roi[y0:y1, x0:x1]
    rgb[excluded & p] = (1.0, 0.65, 0.05)  # 画像端へ続く未注釈 track
    return rgb


def _print_recorded():
    print("実データが無いため章を飛ばす。CI は 6.4 GB を取得しない。")
    print("記録値(RECORDED): " + json.dumps(RECORDED, ensure_ascii=False, sort_keys=True))


def main() -> None:
    t0 = time.perf_counter()
    synthetic = synthetic_width_gate()
    print("合成幅の門: 300 nm = %.2f px、断面 ラベル %.2f px / 切り出し "
          "%.2f px、同一中心線の距離変換 %.2f px" %
          (synthetic["truth_px"], synthetic["label_px"], synthetic["pred_px"],
           synthetic["skeleton_px"]))
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
    label_models = defaultdict(list)
    image_models = defaultdict(list)
    defects = {"via_duplicates": 0, "via_border": 0, "track_clipped_labels": 0,
               "track_missing_border_components": 0,
               "track_partial_border_components": 0}
    via_totals = [0, 0, 0]
    representative = None

    for index, (image_path, svg_path) in enumerate(pairs):
        img = _read_image(image_path)
        tracks, raw_vias = read_label(svg_path, img.shape)
        clean_tracks = [p for p in tracks if not _touches_border(p, img.shape)]
        clipped_tracks = [p for p in tracks if _touches_border(p, img.shape)]
        clipped = len(clipped_tracks)
        vias, duplicates, via_border = deduplicate_vias(raw_vias, img.shape)
        defects["via_duplicates"] += duplicates
        defects["via_border"] += via_border
        defects["track_clipped_labels"] += clipped
        truth = _polygon_mask(img.shape, clean_tracks)
        all_label = _polygon_mask(img.shape, tracks)
        methods = segment_tracks(img)
        missing, missing_n, partial_n = _label_missing_border_tracks(
            methods["固定しきい値"], all_label)
        defects["track_missing_border_components"] += missing_n
        defects["track_partial_border_components"] += partial_n
        # 端に触れる track ラベルは不完全なため truth から除いている。
        # その領域を ROI からも除かないと、正しい切り出しが false positive になる。
        clipped_mask = _polygon_mask(img.shape, clipped_tracks)
        roi = ~missing & ~ndi.binary_dilation(clipped_mask, iterations=12)
        roi[:2, :] = False; roi[-2:, :] = False; roi[:, :2] = False; roi[:, -2:] = False
        print("\n[%d/%d] %s: track %d (端切れ除外 %d)、via %d (重複除外 %d / 端除外 %d)、"
              "ラベル欠け 全体 %d / 部分 %d" %
              (index + 1, len(pairs), image_path.name, len(clean_tracks), clipped,
               len(vias), duplicates, via_border, missing_n, partial_n))
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
        prepared_tracks = [_prepare_track_width(points, img.shape) for points in ranked]
        for name, pred in methods.items():
            for prepared in prepared_tracks:
                row = None if prepared is None else _measure_prepared_track(prepared, pred)
                if row is not None:
                    row["image"] = index
                    widths[name].append(row)

        for name, threshold in (("固定しきい値", FIXED_TRACK_THRESHOLD), ("大津", _otsu_value(img))):
            label_model = psf_edge_model(img, truth, threshold)
            if label_model is not None:
                label_model["image"] = index
                label_models[name].append(label_model)
            image_model = psf_edge_model_image_only(img, methods[name], threshold)
            if image_model is not None:
                image_model["image"] = index
                image_models[name].append(image_model)

        detected = detect_vias(img)
        tp, fp, fn = score_vias(detected, vias)
        via_totals[0] += tp; via_totals[1] += fp; via_totals[2] += fn
        print("  via: 検出 %d / TP %d / FP %d / FN %d" % (len(detected), tp, fp, fn))
        if representative is None:
            h, w = img.shape
            cy, cx = h // 2, w // 2
            crop = (max(0, cy - 512), min(h, cy + 512), max(0, cx - 512), min(w, cx + 512))
            representative = (img, truth, vias, methods, roi, crop)

    print("\n集計: 切り出し")
    summary = {}
    for name in ("固定しきい値", "大津", "縁ベース"):
        a = np.asarray(method_scores[name], np.float64)
        rows = widths[name]
        bias = np.array([r["pred_nm"] - r["label_nm"] for r in rows], np.float64)
        label_width = np.array([r["label_nm"] for r in rows], np.float64)
        pred_width = np.array([r["pred_nm"] for r in rows], np.float64)
        label_skeleton = np.array([r["label_skeleton_nm"] for r in rows], np.float64)
        pred_skeleton = np.array([r["pred_skeleton_nm"] for r in rows], np.float64)
        finite_label_skeleton = label_skeleton[np.isfinite(label_skeleton)]
        finite_pred_skeleton = pred_skeleton[np.isfinite(pred_skeleton)]
        label_method_delta_px = abs(float(np.median(label_width))
                                    - float(np.median(finite_label_skeleton))) / PIXEL_NM
        pred_method_delta_px = abs(float(np.median(pred_width))
                                   - float(np.median(finite_pred_skeleton))) / PIXEL_NM
        rec = {
            "iou_median": float(np.nanmedian(a[:, 0])),
            "boundary_nm_mean": float(np.nanmean(a[:, 1])),
            "boundary_nm_p95": float(np.nanmean(a[:, 2])),
            "width_tracks": len(rows),
            "label_width_nm_p10_p50_p90": [float(x) for x in np.percentile(label_width, [10, 50, 90])],
            "pred_width_nm_p10_p50_p90": [float(x) for x in np.percentile(pred_width, [10, 50, 90])],
            "width_bias_nm_median": float(np.median(bias)),
            "sections": int(sum(r["sections"] for r in rows)),
            "label_skeleton_width_nm_median": float(np.median(finite_label_skeleton)),
            "pred_skeleton_width_nm_median": float(np.median(finite_pred_skeleton)),
            "label_profile_skeleton_delta_px": label_method_delta_px,
            "pred_profile_skeleton_delta_px": pred_method_delta_px,
            "raw_label_skeleton_pixels_per_major_axis_median": float(np.median(
                [r["raw_label_skeleton_pixels_per_major_axis"] for r in rows])),
            "raw_pred_skeleton_pixels_per_major_axis_median": float(np.median(
                [r["raw_pred_skeleton_pixels_per_major_axis"] for r in rows])),
            "raw_label_skeleton_endpoints_median": float(np.median(
                [r["raw_label_skeleton_endpoints"] for r in rows])),
            "raw_pred_skeleton_endpoints_median": float(np.median(
                [r["raw_pred_skeleton_endpoints"] for r in rows])),
        }
        summary[name] = rec
        print("  %s: IoU 中央 %.3f、境界平均 %.1f nm、幅 track=%d / 断面=%d、"
              "ラベル p10/50/90 "
              "%.1f/%.1f/%.1f nm、切出し %.1f/%.1f/%.1f nm、偏り %+.1f nm "
              "(断面 vs 同一中心線の距離変換: ラベル %.2f px / 切出し %.2f px)" %
              (name, rec["iou_median"], rec["boundary_nm_mean"], len(rows), rec["sections"],
               *rec["label_width_nm_p10_p50_p90"], *rec["pred_width_nm_p10_p50_p90"],
               rec["width_bias_nm_median"], label_method_delta_px, pred_method_delta_px))
        print("    生スケルトン: 画素/主軸長 ラベル %.2f / 切出し %.2f、"
              "端点中央 ラベル %.1f / 切出し %.1f" %
              (rec["raw_label_skeleton_pixels_per_major_axis_median"],
               rec["raw_pred_skeleton_pixels_per_major_axis_median"],
               rec["raw_label_skeleton_endpoints_median"],
               rec["raw_pred_skeleton_endpoints_median"]))

    threshold_best = max(("固定しきい値", "大津"), key=lambda n: summary[n]["iou_median"])
    correction_eval = evaluate_corrections(
        widths[threshold_best], image_models[threshold_best], label_models[threshold_best])
    sigma_nm = np.array([m["sigma_px"] * PIXEL_NM for m in image_models[threshold_best]],
                        np.float64)
    before_med = correction_eval["image_only"]["before_nm"]
    after_med = correction_eval["image_only"]["after_nm"]
    reduction_nm = correction_eval["image_only"]["reduction_nm"]
    reduction_fraction = correction_eval["image_only"]["reduction_fraction"]
    shrank = reduction_nm > 0.0
    effective = shrank and reduction_fraction >= 0.25
    print("\nPSF 補正の独立性 (%s、補正量だけを各方式で変更):" % threshold_best)
    print("  %-18s %10s %10s %10s" % ("方式", "補正量[nm]", "補正前[nm]", "補正後[nm]"))
    for key, label in (("image_only", "ラベル不使用"), ("split", "分割検証 5/5"),
                       ("same_image", "参考: 同一画像")):
        row = correction_eval[key]
        print("  %-18s %+10.1f %+10.1f %+10.1f" %
              (label, row["correction_nm_median"], row["before_nm"], row["after_nm"]))
    print("  注: 『参考: 同一画像』は同じ画像・同じラベルで補正量と誤差を求める循環評価。"
          "主結果には使わない。")
    print("  分割検証: 画像 %s から得た補正 %+.1f nmを画像 %sへ、逆向きは %+.1f nm。" %
          (correction_eval["split_images"][0], correction_eval["split_train_correction_nm"][0],
           correction_eval["split_images"][1], correction_eval["split_train_correction_nm"][1]))
    print("  ラベル不使用: 切り出し自身の符号付き距離を Fullseye blob_distance で作り、"
          "edge-spread の PSF sigma 中央 %.1f nm。絶対偏りを %.1f %% %s。" %
          (float(np.median(sigma_nm)), abs(100.0 * reduction_fraction),
           "縮小" if shrank else "悪化"))

    virtual = virtual_sem_prediction()
    virtual_delta = virtual["predicted_edge_inflation_nm"] - before_med
    print("\n仮想 SEM の予測と実測:")
    print("  15 keV BSE、標本間隔 %.2f nm、真幅 %.1f nm -> 模型幅 %.1f nm、"
          "縁の太り %+.1f nm。実測の補正前偏り %+.1f nm、差 %+.1f nm。" %
          (virtual["pixel_nm"], virtual["true_width_nm"], virtual["predicted_width_nm"],
           virtual["predicted_edge_inflation_nm"], before_med, virtual_delta))
    print("  模型へ入れた代理条件: Cu/Si、隆起高さ 40 nm、側壁 88 度、ビーム sigma 1 nm。"
          "データに無い材料組成・配線高さ・側壁角・ビーム径は決められない。"
          "sem_render の sec(theta) は SE 模型で BSE には使えず、sem_line_profile も"
          "平坦な埋込 metal-2 の材料境界を表せないため、数値の近さは模型の検証ではない。")

    tp, fp, fn = via_totals
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    print("\nvia (重複ラベルを除外): TP %d / FP %d / FN %d、適合率 %.3f、再現率 %.3f" %
          (tp, fp, fn, precision, recall))
    print("ラベル欠陥: via 重複 %d、via 端切れ %d、端で切れた track ラベル %d、"
          "端から続く未ラベル track 成分 %d、部分的なラベル欠け %d "
          "(すべて理由つきで採点から除外)" %
          (defects["via_duplicates"], defects["via_border"], defects["track_clipped_labels"],
           defects["track_missing_border_components"],
           defects["track_partial_border_components"]))

    record = {
        "date": "2026-11-01", "images": len(pairs), "pixel_nm": PIXEL_NM,
        "dataset_sha256": realdata.SEM_METAL_SHA256,
        "method": threshold_best, "methods": summary,
        "psf_sigma_nm_median": float(np.median(sigma_nm)),
        "correction_evaluation": correction_eval,
        "bias_before_nm": before_med, "bias_after_nm": after_med,
        "bias_reduction_nm": reduction_nm, "bias_reduction_fraction": reduction_fraction,
        "correction_shrank": shrank, "correction_effective": effective,
        "virtual_sem": virtual,
        "via_precision": precision, "via_recall": recall,
        "via_tp_fp_fn": [tp, fp, fn], "label_defects": defects,
    }
    print("RECORDED_JSON=" + json.dumps(record, ensure_ascii=False, sort_keys=True))

    if representative is not None and figs.enabled():
        img, truth, vias, methods, roi, crop = representative
        best_all = max(summary, key=lambda n: summary[n]["iou_median"])
        overlay = _overlay(img, truth, vias, crop)
        figs.save("scene", overlay,
                  caption="実 SEM 像。緑=track ラベル、赤=重複除去後の via ラベル。",
                  source=SOURCE)
        figs.save("segmentation_difference",
                  _difference_image(img, truth, methods[best_all], roi, crop),
                  caption="%s。緑=一致、赤=太り、青=欠け、橙=画像端から続く"
                          "ラベル欠け(採点除外)。" % best_all, source=SOURCE)
        wr = widths[threshold_best]
        figs.save_plot(
            "line_width_distribution",
            [("ラベル", list(range(len(wr))), sorted(r["label_nm"] for r in wr)),
             ("切り出し", list(range(len(wr))), sorted(r["pred_nm"] for r in wr))],
            xlabel="track（幅の小さい順）", ylabel="線幅 [nm]",
            title="線幅分布と偏り（%s、n=%d）" % (threshold_best, len(wr)),
            caption="ラベルの主中心線上で両端と曲がり角を除き、等間隔の連続断面幅を"
                    "ラベルと切り出しに同じ手続きで測った。", source=SOURCE)
        figs.save_plot(
            "psf_correction",
            [("補正前", [0, 1], [before_med, before_med]),
             ("ラベル不使用", [0, 1], [after_med, after_med]),
             ("分割検証", [0, 1], [correction_eval["split"]["after_nm"]] * 2),
             ("同一画像（循環）", [0, 1], [correction_eval["same_image"]["after_nm"]] * 2),
             ("偏りゼロ", [0, 1], [0.0, 0.0])],
            xlabel="", ylabel="線幅の偏り [nm]",
            title="PSF 補正: 像単独・5/5 分割・循環参考を分離",
            caption="補正前 %+.1f nmに対し、ラベル不使用 %+.1f nm、5/5 分割 %+.1f nm、"
                    "同一画像 %+.1f nm（同一画像は循環する参考値）。" %
                    (before_med, after_med, correction_eval["split"]["after_nm"],
                     correction_eval["same_image"]["after_nm"]), source=SOURCE)

    print("門: 合成幅 ±1 px / 実データの二方式 ±1 px / SVG 二重読取一致 / "
          "全指標有限 / via 対応 1対1 / 図の環境変数門")
    assert all(np.isfinite(v["iou_median"]) for v in summary.values())
    assert summary[threshold_best]["label_profile_skeleton_delta_px"] <= 1.0 + 1e-9
    assert summary[threshold_best]["pred_profile_skeleton_delta_px"] <= 1.0 + 1e-9
    assert tp <= min(tp + fp, tp + fn)
    print("完了: %.1f s" % (time.perf_counter() - t0))


if __name__ == "__main__":
    main()
