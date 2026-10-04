# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""日本の町を実在の地図から組む(drivejapan、2026-10-04)。

著者の発案「出来れば日本のマップでやりたい」→ 外部シミュレータの同梱マップは欧米の町(右側通行)で、日本の町を入れるには
エディタのビルドと日本の資産が要る。代わりに **自前の世界に日本を作る**: 道路網は OpenStreetMap(ODbL)、建物は国交省 PLATEAU
(CC BY 4.0、:mod:`drivejapan` の plateau_* 系)、道具立て(一時停止の標識・「止まれ」の路面標示・踏切警標・電柱・カーブミラー・
日本式の横断歩道)は規格の寸法から自前のメッシュ、規則は drivetown の法規パック(JP)で採点する。

道路の形はこう作る(全部 Fullseye の既存部品):

1. :func:`osm_parse` —— OSM XML を読み、等距円筒近似で局所の平面座標 [m] に落とす(:func:`latlon_to_local`)。
2. :func:`osm_road_graph` —— ``highway`` の way を辺に切り、幅を OSM の ``width`` / ``lanes`` か道路構造令の車線幅の既定から決める。
3. :func:`osm_road_mask` —— 辺を幅つきの線分としてラスタに描き **和集合** を取る(多角形の和集合を解析的に解かず、画像として解く)。
4. :func:`japan_world` —— 和集合の **境界を画素の辺に沿って追跡**(:func:`contours_xld._trace_mask_boundaries`、面積は画素数に厳密に一致)し、
   外側のループは道路の縁、穴のループは街区。街区は Douglas–Peucker で間引いて耳切りで三角形にし、歩道(0.15 m 高)と縁石の帯を置く。
   節点の ``highway=traffic_signals`` に信号機、``crossing`` に日本式の横断歩道(進行方向に平行な縞)、``stop`` に一時停止の標識 +
   停止線 + 「止まれ」、``railway=level_crossing`` に踏切警標とレール、生活道路の左側に電柱、を立てる。
5. :func:`osm_route` —— 2 節点間の最短路(Dijkstra、一方通行を守る)を **左側通行の車線中心** に寄せた折線にし、途中の停止線
   (信号 = intersection / 一時停止 = stop_sign / 踏切 = crossing)を弧長で並べる。drivetown.town_run に渡せる "route" 形式。

正直に: 等距円筒近似は 1 km 四方で 1e-5 の歪み。幅は OSM にタグが無ければ道路の種別の既定(断定しない)。車線は幅から数える
だけで、OSM の車線の割り付け(``turn:lanes``)は読まない。「止まれ」の字形は 4〜5 画の略字形で、規格の字体ではない。建物の無い
世界(PLATEAU を渡さないとき)は街区が平らな歩道だけ。歩行者・他車は置かない。
"""
from __future__ import annotations

import heapq
import io
import math
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "ROAD_TYPES", "LANE_WIDTH_JP", "DEFAULT_LANES", "NODE_FEATURES", "JP_SIGN_STOP_SIDE_M", "JP_STOP_LINE_WIDTH_M",
    "latlon_to_local", "osm_synthetic", "osm_parse", "osm_road_graph", "osm_road_mask", "osm_road_loops",
    "osm_route", "japan_world", "japan_stats", "jp_sign_stop_mesh", "jp_crossbuck_mesh", "jp_pole_mesh",
    "jp_mirror_mesh", "jp_stop_marking_mesh", "jp_stop_marking_length", "JP_TOMARE_CHAR_H_M", "JP_TOMARE_CHAR_W_M",
    "JP_TOMARE_GAP_M", "JP_TOMARE_SETBACK_M", "JP_CROSSWALK_STRIPE_M",
]

R_EARTH_M = 6378137.0
# 道路構造令 第 5 条の車線幅(第 4 種 = 都市部: 1 級 3.25 / 2 級 3.0 / 3 級 2.75 を種別に当てる。断定せず「既定」とする)
LANE_WIDTH_JP = {"motorway": 3.5, "motorway_link": 3.5, "trunk": 3.25, "trunk_link": 3.25, "primary": 3.25, "primary_link": 3.25,
                 "secondary": 3.0, "secondary_link": 3.0, "tertiary": 3.0, "tertiary_link": 3.0, "unclassified": 2.75,
                 "residential": 2.75, "living_street": 2.0, "service": 2.0}
DEFAULT_LANES = {"motorway": 4, "motorway_link": 1, "trunk": 4, "trunk_link": 1, "primary": 4, "primary_link": 1,
                 "secondary": 2, "secondary_link": 1, "tertiary": 2, "tertiary_link": 1, "unclassified": 2,
                 "residential": 2, "living_street": 2, "service": 2}
ROAD_TYPES = tuple(LANE_WIDTH_JP)
NODE_FEATURES = ("traffic_signals", "crossing", "stop", "give_way", "level_crossing")
JP_SIGN_STOP_SIDE_M = 0.8        # 一時停止(330-A)の逆正三角形の一辺 80 cm(道路標識、区画線及び道路標示に関する命令 別表第二。角の丸み R 5、「止まれ」字高 13)
JP_STOP_LINE_WIDTH_M = 0.45      # 停止線(203)の線幅 0.30〜0.45 m(同命令 別表第六、白)
JP_CROSSWALK_STRIPE_M = 0.45     # 横断歩道の縞幅と間隔(0.45 m)、縞は進行方向に平行
_LABEL_BUILDING, _LABEL_SIDEWALK, _LABEL_POLE = 14, 15, 16
_C_SIDEWALK = (0.62, 0.60, 0.56)
_C_KERB = (0.78, 0.78, 0.74)
_C_LINE = (0.95, 0.95, 0.92)
_C_RED = (0.85, 0.10, 0.10)
_C_WHITE = (0.97, 0.97, 0.95)
_C_YELLOW = (0.98, 0.80, 0.08)
_C_BLACK = (0.08, 0.08, 0.08)
_C_GREY = (0.55, 0.56, 0.58)
_C_ORANGE = (0.95, 0.45, 0.08)
_C_RAIL = (0.35, 0.33, 0.30)


# ----------------------------------------------------------------------------------------------------------------------
# 1. 座標と OSM の読み込み
def latlon_to_local(lat, lon, origin) -> Tuple[np.ndarray, np.ndarray]:
    """緯度経度 [deg] → 原点 origin = (lat0, lon0) まわりの等距円筒近似の平面座標 (x 東, y 北) [m]。

    x = R cos(lat0) Δλ、y = R Δφ(R = 6378137 m)。1 km 四方で 1e-5 の歪み(cos の変化)なので町 1 つには十分。配列可。
    **Raises** ``ValueError``: 緯度経度が範囲外・非有限。"""
    lat = np.asarray(lat, np.float64)
    lon = np.asarray(lon, np.float64)
    lat0, lon0 = float(origin[0]), float(origin[1])
    for v in (lat, lon, np.array([lat0, lon0])):
        if not np.all(np.isfinite(v)):
            raise ValueError("latlon_to_local: latitude/longitude must be finite")
    if np.any(np.abs(lat) > 90) or np.any(np.abs(lon) > 180) or abs(lat0) > 90 or abs(lon0) > 180:
        raise ValueError("latlon_to_local: latitude within [-90, 90], longitude within [-180, 180]")
    k = math.pi / 180.0
    return R_EARTH_M * math.cos(lat0 * k) * (lon - lon0) * k, R_EARTH_M * (lat - lat0) * k


def osm_synthetic(kind: str = "grid", *, origin=(35.6716, 139.7650), n: int = 3, pitch: float = 80.0) -> str:
    """テストと fuzz 用の最小の OSM XML(本物と同じ要素: bounds / node / way / tag)。

    "grid" = n × n の格子(東西 = primary、lanes=2、南北 = residential、幅は既定)。中央の交差点に ``highway=traffic_signals``、
    東の縁の中段(T 字路)に ``highway=stop``、西の辺の途中に ``highway=crossing``、南の辺の途中に ``railway=level_crossing``。
    "line" = 東西 1 本の residential(長さ pitch × (n − 1))。**Raises** ``ValueError``: kind が未知、n < 2、pitch ≤ 0。"""
    if kind not in ("grid", "line"):
        raise ValueError("osm_synthetic: kind must be 'grid' or 'line', got %r" % (kind,))
    n = int(n)
    if n < 2 or not (float(pitch) > 0):
        raise ValueError("osm_synthetic: n >= 2 and pitch > 0")
    lat0, lon0 = float(origin[0]), float(origin[1])
    k = 180.0 / math.pi
    dlat = pitch / R_EARTH_M * k
    dlon = pitch / (R_EARTH_M * math.cos(lat0 / k)) * k
    nodes, ways = [], []
    nid = {}
    def node(i, j, tags=()):
        key = (i, j)
        if key not in nid:
            nid[key] = len(nid) + 1
            nodes.append((nid[key], lat0 + (j - (n - 1) / 2) * dlat, lon0 + (i - (n - 1) / 2) * dlon, dict(tags)))
        return nid[key]
    if kind == "line":
        ids = [node(i, 0) for i in range(n)]
        ways.append((1, ids, {"highway": "residential", "name": "test line"}))
    else:
        c = (n - 1) // 2
        for j in range(n):
            ids = [node(i, j, {"highway": "traffic_signals"} if (i == c and j == c) else
                        ({"highway": "stop"} if (i == n - 1 and j == c) else ())) for i in range(n)]
            ways.append((100 + j, ids, {"highway": "primary", "lanes": "2", "name": "EW %d" % j}))
        for i in range(n):
            ids = [node(i, j) for j in range(n)]
            ways.append((200 + i, ids, {"highway": "residential", "name": "NS %d" % i}))
        # 西の辺(i = 0, j = 0〜1 の間)に横断歩道、南の辺(j = 0, i = 0〜1 の間)に踏切: way の途中に節点を挿す
        nodes.append((900, lat0 + (0.5 - (n - 1) / 2) * dlat, lon0 + (0 - (n - 1) / 2) * dlon, {"highway": "crossing"}))
        nodes.append((901, lat0 + (0 - (n - 1) / 2) * dlat, lon0 + (0.5 - (n - 1) / 2) * dlon, {"railway": "level_crossing"}))
        w = ways[n]  # NS 0
        w[1].insert(1, 900)
        w0 = ways[0]  # EW 0
        w0[1].insert(1, 901)
    out = io.StringIO()
    out.write('<?xml version="1.0" encoding="UTF-8"?>\n<osm version="0.6" generator="drivejapan.osm_synthetic">\n')
    lats = [nd[1] for nd in nodes]
    lons = [nd[2] for nd in nodes]
    out.write('  <bounds minlat="%.11f" minlon="%.11f" maxlat="%.11f" maxlon="%.11f"/>\n' % (min(lats), min(lons), max(lats), max(lons)))
    for i, la, lo, tags in nodes:
        if tags:
            out.write('  <node id="%d" lat="%.11f" lon="%.11f">\n' % (i, la, lo))
            for kk, vv in tags.items():
                out.write('    <tag k="%s" v="%s"/>\n' % (kk, vv))
            out.write('  </node>\n')
        else:
            out.write('  <node id="%d" lat="%.11f" lon="%.11f"/>\n' % (i, la, lo))
    for wid, ids, tags in ways:
        out.write('  <way id="%d">\n' % wid)
        for i in ids:
            out.write('    <nd ref="%d"/>\n' % i)
        for kk, vv in tags.items():
            out.write('    <tag k="%s" v="%s"/>\n' % (kk, vv))
        out.write('  </way>\n')
    out.write('</osm>\n')
    return out.getvalue()


def osm_parse(source, *, origin=None) -> Dict[str, object]:
    """OSM XML(文字列かファイルパス)を読み、節点を局所平面座標 [m] に落とす。

    返り値 ``{"origin": (lat0, lon0), "nodes": {id: {"xy": (x, y), "lat", "lon", "tags": {}}}, "ways": [{"id", "nodes": [id], "tags": {}}],
    "bbox": (xmin, xmax, ymin, ymax)(``<bounds>`` があればそれ、無ければ節点の範囲), "n_nodes", "n_ways"}``。
    origin が None なら ``<bounds>`` の中心(無ければ節点の平均)。``<nd ref>`` が未知の節点を指す way はその節点を落とす(件数を ``n_dangling`` に)。
    **Raises** ``ValueError``: XML でない、``<osm>`` でない、節点が 1 つも無い。"""
    text = source
    if isinstance(source, (str, Path)) and not (isinstance(source, str) and source.lstrip().startswith("<")):
        p = Path(source)
        if not p.is_file():
            raise ValueError("osm_parse: %s is not a file nor XML text" % (source,))
        text = p.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise ValueError("osm_parse: not well-formed XML (%s)" % e) from None
    if root.tag != "osm":
        raise ValueError("osm_parse: root element must be <osm>, got <%s>" % root.tag)
    raw = {}
    for nd in root.iter("node"):
        try:
            i, la, lo = int(nd.get("id")), float(nd.get("lat")), float(nd.get("lon"))
        except (TypeError, ValueError):
            raise ValueError("osm_parse: <node> needs integer id and float lat/lon") from None
        raw[i] = (la, lo, {t.get("k"): t.get("v") for t in nd.findall("tag")})
    if not raw:
        raise ValueError("osm_parse: no <node> in the document")
    b = root.find("bounds")
    if origin is None:
        if b is not None:
            origin = ((float(b.get("minlat")) + float(b.get("maxlat"))) / 2, (float(b.get("minlon")) + float(b.get("maxlon"))) / 2)
        else:
            origin = (float(np.mean([v[0] for v in raw.values()])), float(np.mean([v[1] for v in raw.values()])))
    origin = (float(origin[0]), float(origin[1]))
    ids = np.array(sorted(raw))
    lat = np.array([raw[i][0] for i in ids])
    lon = np.array([raw[i][1] for i in ids])
    x, y = latlon_to_local(lat, lon, origin)
    nodes = {int(i): {"xy": (float(xx), float(yy)), "lat": float(la), "lon": float(lo), "tags": raw[int(i)][2]}
             for i, xx, yy, la, lo in zip(ids, x, y, lat, lon)}
    ways, dangling = [], 0
    for w in root.iter("way"):
        refs = []
        for nd in w.findall("nd"):
            r = int(nd.get("ref"))
            if r in nodes:
                refs.append(r)
            else:
                dangling += 1
        ways.append({"id": int(w.get("id")), "nodes": refs, "tags": {t.get("k"): t.get("v") for t in w.findall("tag")}})
    if b is not None:
        bx, by = latlon_to_local(np.array([float(b.get("minlat")), float(b.get("maxlat"))]),
                                 np.array([float(b.get("minlon")), float(b.get("maxlon"))]), origin)
        bbox = (float(bx[0]), float(bx[1]), float(by[0]), float(by[1]))
    else:
        bbox = (float(x.min()), float(x.max()), float(y.min()), float(y.max()))
    return {"origin": origin, "nodes": nodes, "ways": ways, "bbox": bbox, "n_nodes": len(nodes), "n_ways": len(ways),
            "n_dangling": dangling, "license": "OpenStreetMap contributors, ODbL 1.0"}


# ----------------------------------------------------------------------------------------------------------------------
# 2. 道路網(辺 = 幅つき線分)
def _parse_metres(v) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip().lower().replace("m", "").replace(",", ".").split(";")[0].strip()
    try:
        f = float(s)
    except ValueError:
        return None
    return f if math.isfinite(f) and f > 0 else None


def _edge_width(tags: dict, highway: str) -> Tuple[float, int, str]:
    """(幅 [m], 車線数, 由来) —— OSM の width → lanes × 既定車線幅 → 既定車線数 × 既定車線幅。幅は [2.5, 40] に切る。"""
    lw = LANE_WIDTH_JP[highway]
    w = _parse_metres(tags.get("width"))
    if w is not None:
        lanes = max(1, int(round(w / lw)))
        return min(40.0, max(2.5, w)), lanes, "width"
    lanes = None
    try:
        lanes = int(float(str(tags.get("lanes", "")).split(";")[0]))
    except ValueError:
        lanes = None
    if lanes is not None and lanes > 0:
        return min(40.0, max(2.5, lanes * lw)), lanes, "lanes"
    lanes = DEFAULT_LANES[highway]
    return min(40.0, max(2.5, lanes * lw)), lanes, "default"


def osm_road_graph(osm: dict, *, way_types: Sequence[str] = ROAD_TYPES, bbox=None, margin: float = 0.0) -> Dict[str, object]:
    """OSM の読み込み結果から道路網を作る。

    辺 = way の隣り合う節点の対 ``{"a", "b", "way", "highway", "width", "lanes", "width_from", "oneway", "length", "tags"}``。
    節点 = ``{"xy", "degree", "features": [NODE_FEATURES の部分集合], "tags", "edges": [辺の索引]}``(辺に使われた節点だけ)。
    ``bbox`` = (xmin, xmax, ymin, ymax) を渡すと **両端が箱(+ margin)の外** の辺を落とす(片端だけ外の辺は残す = 箱の縁で道が切れる)。
    ``oneway`` は "yes" / "1" / "true" が順方向、"-1" / "reverse" は a, b を入れ替えて順方向にする。
    **Raises** ``ValueError``: way_types に知らない種別、辺が 1 本も無い。"""
    for t in way_types:
        if t not in LANE_WIDTH_JP:
            raise ValueError("osm_road_graph: unknown way type %r (known: %s)" % (t, ", ".join(ROAD_TYPES)))
    if bbox is not None:
        xmin, xmax, ymin, ymax = (float(v) for v in bbox)
        xmin, xmax, ymin, ymax = xmin - margin, xmax + margin, ymin - margin, ymax + margin
    def inside(p):
        return bbox is None or (xmin <= p[0] <= xmax and ymin <= p[1] <= ymax)
    N = osm["nodes"]
    edges: List[dict] = []
    for w in osm["ways"]:
        hw = w["tags"].get("highway")
        if hw not in way_types or len(w["nodes"]) < 2:
            continue
        if w["tags"].get("area") == "yes":
            continue
        width, lanes, src = _edge_width(w["tags"], hw)
        ow = str(w["tags"].get("oneway", "no")).lower()
        oneway = ow in ("yes", "1", "true", "-1", "reverse")
        reverse = ow in ("-1", "reverse")
        seq = list(reversed(w["nodes"])) if reverse else list(w["nodes"])
        for a, b in zip(seq[:-1], seq[1:]):
            if a == b:
                continue
            pa, pb = N[a]["xy"], N[b]["xy"]
            if not (inside(pa) or inside(pb)):
                continue
            L = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
            if L < 1e-6:
                continue
            edges.append({"a": a, "b": b, "way": w["id"], "highway": hw, "width": width, "lanes": lanes, "width_from": src,
                          "oneway": oneway, "length": L, "tags": w["tags"]})
    if not edges:
        raise ValueError("osm_road_graph: no road edge (check way_types / bbox)")
    nodes: Dict[int, dict] = {}
    for k, e in enumerate(edges):
        for i in (e["a"], e["b"]):
            if i not in nodes:
                tg = N[i]["tags"]
                feats = [f for f in NODE_FEATURES if tg.get("highway") == f or tg.get("railway") == f]
                nodes[i] = {"xy": N[i]["xy"], "degree": 0, "features": feats, "tags": tg, "edges": []}
            nodes[i]["degree"] += 1
            nodes[i]["edges"].append(k)
    return {"nodes": nodes, "edges": edges, "origin": osm["origin"], "bbox": tuple(bbox) if bbox is not None else osm["bbox"],
            "n_nodes": len(nodes), "n_edges": len(edges), "total_length": float(sum(e["length"] for e in edges)),
            "license": osm.get("license", "")}


def _node_radius(graph: dict, i: int, exclude: Optional[int] = None, d_in=None, parallel_cos: float = 0.906) -> float:
    """節点 i で **交差する** 辺の最大半幅(交差点の大きさの目安 = 停止線を下げる量)。

    exclude の辺と、``d_in``(進入の向き)にほぼ平行な辺(|cos| > parallel_cos ≈ 25°、= 同じ道の続き)は数えない。次数 2 以下なら 0。"""
    n = graph["nodes"][i]
    if n["degree"] <= 2 and exclude is not None:
        return 0.0
    ws = []
    for k in n["edges"]:
        if k == exclude:
            continue
        e = graph["edges"][k]
        if d_in is not None:
            other = e["b"] if e["a"] == i else e["a"]
            d, _ = _unit(graph["nodes"][i]["xy"], graph["nodes"][other]["xy"])
            if abs(float(d[0] * d_in[0] + d[1] * d_in[1])) > parallel_cos:
                continue
        ws.append(e["width"])
    return max(ws) / 2.0 if ws else 0.0


# ----------------------------------------------------------------------------------------------------------------------
# 3. ラスタの和集合と境界
def osm_road_mask(graph: dict, *, step: float = 0.5, margin: float = 6.0, bbox=None) -> Dict[str, object]:
    """辺を幅つきの線分(端は丸)として描いた **道路の和集合** の 2 値画像。

    画素 (r, c) の中心 = (xmin + (c + ½) step, ymin + (r + ½) step)、行は y の増える向き(数学座標。表示で上下を返す)。
    返り値 ``{"mask": (H, W) bool, "xmin", "ymin", "step", "shape", "area_m2": 画素数 × step²}``。
    **Raises** ``ValueError``: step ≤ 0、画像が 4e7 画素を超える(step を粗く)。"""
    step = float(step)
    if not (step > 0):
        raise ValueError("osm_road_mask: step must be > 0")
    xmin, xmax, ymin, ymax = (float(v) for v in (bbox if bbox is not None else graph["bbox"]))
    xmin, xmax, ymin, ymax = xmin - margin, xmax + margin, ymin - margin, ymax + margin
    W, H = int(math.ceil((xmax - xmin) / step)), int(math.ceil((ymax - ymin) / step))
    if W * H > 4e7:
        raise ValueError("osm_road_mask: %d x %d pixels is too many; use a coarser step or a smaller bbox" % (W, H))
    mask = np.zeros((H, W), bool)
    N = graph["nodes"]
    for e in graph["edges"]:
        (xa, ya), (xb, yb) = N[e["a"]]["xy"], N[e["b"]]["xy"]
        hw = e["width"] / 2.0
        c0 = max(0, int((min(xa, xb) - hw - xmin) / step) - 1)
        c1 = min(W, int((max(xa, xb) + hw - xmin) / step) + 2)
        r0 = max(0, int((min(ya, yb) - hw - ymin) / step) - 1)
        r1 = min(H, int((max(ya, yb) + hw - ymin) / step) + 2)
        if c1 <= c0 or r1 <= r0:
            continue
        xs = xmin + (np.arange(c0, c1) + 0.5) * step
        ys = ymin + (np.arange(r0, r1) + 0.5) * step
        X, Y = np.meshgrid(xs, ys)
        dx, dy = xb - xa, yb - ya
        L2 = dx * dx + dy * dy
        t = np.clip(((X - xa) * dx + (Y - ya) * dy) / L2, 0.0, 1.0)
        d2 = (X - (xa + t * dx)) ** 2 + (Y - (ya + t * dy)) ** 2
        mask[r0:r1, c0:c1] |= d2 <= hw * hw
    return {"mask": mask, "xmin": xmin, "ymin": ymin, "step": step, "shape": (H, W), "area_m2": float(mask.sum()) * step * step}


def _loop_to_xy(loop: np.ndarray, rm: dict) -> np.ndarray:
    """境界ループ(row, col の画素の角、半整数)→ 平面座標 [m]。角 (r, c) は中心 (r+½, c+½) の画素の左下 → x = xmin + (c + ½) step。"""
    return np.column_stack([rm["xmin"] + (loop[:, 1] + 0.5) * rm["step"], rm["ymin"] + (loop[:, 0] + 0.5) * rm["step"]])


def _signed_area(P: np.ndarray) -> float:
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))


def _runs_mesh(Praw: np.ndarray, rm: dict, z: float):
    """間引く前のループ(画素の辺に沿う)が囲む画素を行ごとの連続区間(run)の長方形で埋めた平らなメッシュ。

    偶奇則で画素中心の内外を決める(画素の辺に沿うループなので中心が辺に乗ることは無い)。面積 = 画素数 × step²。"""
    step, xmin, ymin = rm["step"], rm["xmin"], rm["ymin"]
    # ループを画素の角(半整数)に戻す
    rr = (Praw[:, 1] - ymin) / step - 0.5
    cc = (Praw[:, 0] - xmin) / step - 0.5
    r0, r1 = int(math.floor(rr.min())), int(math.ceil(rr.max()))
    c0, c1 = int(math.floor(cc.min())), int(math.ceil(cc.max()))
    V, F = [], []
    n = len(Praw)
    for r in range(r0, r1 + 1):
        yc = r + 0.0          # 画素 r の中心(角の座標系では r)
        xs = []
        for k in range(n):
            ra, ca = rr[k], cc[k]
            rb, cb = rr[(k + 1) % n], cc[(k + 1) % n]
            if abs(ra - rb) < 1e-9:
                continue                       # 水平な辺は交わらない
            if (ra <= yc) != (rb <= yc):
                xs.append(ca)                  # 縦の辺(ca == cb)
        if len(xs) < 2:
            continue
        xs.sort()
        for a, b in zip(xs[0::2], xs[1::2]):
            ca, cb = int(round(a + 0.5)), int(round(b + 0.5))   # 画素の列の範囲 [ca, cb)
            if cb <= ca:
                continue
            xa, xb = xmin + ca * step, xmin + cb * step
            ya, yb = ymin + r * step, ymin + (r + 1) * step
            base = len(V)
            V += [[xa, ya, z], [xb, ya, z], [xb, yb, z], [xa, yb, z]]
            F += [[base, base + 1, base + 2], [base, base + 2, base + 3]]
    return np.asarray(V, np.float64).reshape(-1, 3), np.asarray(F, np.int64).reshape(-1, 3)


def osm_road_loops(roadmask: dict, *, tolerance_px: float = 0.75) -> Dict[str, object]:
    """道路の和集合の境界ループ。外側(道路の縁)と穴(街区)に分け、Douglas–Peucker で間引く。

    追跡は画素の辺に沿う(:func:`contours_xld._trace_mask_boundaries`)ので、間引く前のループの面積の和 = 画素数 × step²
    (外側 − 穴)が厳密に成り立つ(``area_check``)。穴か外側かは、ループの最も左の縦の辺のすぐ右の画素が道路かどうかで決める。
    返り値 ``{"outer": [(K,2) xy], "holes": [(K,2) xy], "outer_raw", "holes_raw", "area_check": {"loops_m2", "pixels_m2", "abs_err"}}``。"""
    import contours_xld as CX
    mask = roadmask["mask"]
    step = roadmask["step"]
    loops = CX._trace_mask_boundaries(mask)
    outer_raw, holes_raw = [], []
    for lp in loops:
        lp = np.asarray(lp, np.float64)
        if len(lp) > 1 and np.allclose(lp[0], lp[-1]):
            lp = lp[:-1]
        if len(lp) < 4:
            continue
        cmin = lp[:, 1].min()
        is_hole = None
        n = len(lp)
        for k in range(n):
            a, b = lp[k], lp[(k + 1) % n]
            if abs(a[1] - cmin) < 1e-9 and abs(b[1] - cmin) < 1e-9 and abs(a[0] - b[0]) > 1e-9:
                r = int(math.floor((a[0] + b[0]) / 2.0 + 0.5))
                c = int(math.floor(cmin + 1.0))
                r = min(max(r, 0), mask.shape[0] - 1)
                c = min(max(c, 0), mask.shape[1] - 1)
                is_hole = not bool(mask[r, c])
                break
        if is_hole is None:
            continue
        (holes_raw if is_hole else outer_raw).append(_loop_to_xy(lp, roadmask))
    def simplify(P):
        c = CX._contour(mask.shape, [np.vstack([P, P[:1]])])
        Q = CX.get_polygon_xld(c, tolerance=tolerance_px * step)[0]
        if len(Q) > 1 and np.allclose(Q[0], Q[-1]):
            Q = Q[:-1]
        return Q
    outer = [simplify(P) for P in outer_raw]
    holes = [simplify(P) for P in holes_raw]
    loops_m2 = sum(abs(_signed_area(P)) for P in outer_raw) - sum(abs(_signed_area(P)) for P in holes_raw)
    pix = float(mask.sum()) * step * step
    return {"outer": outer, "holes": holes, "outer_raw": outer_raw, "holes_raw": holes_raw,
            "area_check": {"loops_m2": float(loops_m2), "pixels_m2": pix, "abs_err": abs(float(loops_m2) - pix)}}


# ----------------------------------------------------------------------------------------------------------------------
# 4. 日本の道具立て(局所座標: +x = 板の法線 = 車が来る向き、z 上。place_mesh で姿勢に置く)
def _box(L, W, H, z0=0.0, cx=0.0, cy=0.0):
    V = np.array([[cx + x, cy + y, z] for z in (z0, z0 + H) for y in (-W / 2, W / 2) for x in (-L / 2, L / 2)], np.float64)
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 6, 7], [4, 7, 5], [0, 4, 5], [0, 5, 1], [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4],
                  [1, 5, 7], [1, 7, 3]], np.int64)
    return V, F


def _merge(parts):
    V = np.zeros((0, 3))
    F = np.zeros((0, 3), np.int64)
    C = []
    for v, f, c in parts:
        F = np.vstack([F, np.asarray(f, np.int64) + len(V)])
        V = np.vstack([V, np.asarray(v, np.float64)])
        C.append(np.tile(np.asarray(c, np.float64), (len(f), 1)))
    return V, F, (np.vstack(C) if C else np.zeros((0, 3)))


def _plate_x(x, pts_yz, color):
    """x = 一定の平面に置いた多角形の板(両面)。pts_yz = (K,2) の (y, z)。"""
    import driveworld as DW
    P = np.asarray(pts_yz, np.float64)
    F = DW.polygon_triangulate(P)
    V = np.column_stack([np.full(len(P), float(x)), P[:, 0], P[:, 1]])
    F2 = np.vstack([F, F[:, ::-1]])
    return V, F2, color


def _cylinder(r, h, z0=0.0, n=8, cx=0.0, cy=0.0):
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ring = np.column_stack([cx + r * np.cos(ang), cy + r * np.sin(ang)])
    V = np.vstack([np.column_stack([ring, np.full(n, z0)]), np.column_stack([ring, np.full(n, z0 + h)])])
    F = []
    for k in range(n):
        a, b = k, (k + 1) % n
        F += [[a, b, n + b], [a, n + b, n + a]]
    for k in range(1, n - 1):
        F.append([n, n + k, n + k + 1])
    return V, np.asarray(F, np.int64)


def jp_sign_stop_mesh(*, side: float = JP_SIGN_STOP_SIDE_M, height: float = 2.5, pole_r: float = 0.04):
    """一時停止(規制標識 330-A)の標識: 赤地の逆正三角形(一辺 side = 80 cm、縁線と文字は白、縁と地は赤 —— 別表第二 備考一(三)3(8))+ 柱。
    板は +x を向く(来る車の側)。角の丸み(R 5 cm)と「止まれ」の文字(字高 13 cm)は省く(字は路面文字 :func:`jp_stop_marking_mesh` で見せる)。
    返り値 (V, F, colors) 面色つき。"""
    h = side * math.sqrt(3) / 2
    z_top = height
    tri = lambda s, dz: np.array([[-s / 2, z_top - dz], [s / 2, z_top - dz], [0.0, z_top - dz - s * math.sqrt(3) / 2]])
    parts = [_cylinder(pole_r, height - 0.05) + (_C_GREY,),
             _plate_x(0.02, tri(side, 0.0), _C_WHITE),
             _plate_x(0.035, tri(side * 0.82, 0.07), _C_RED)]
    return _merge(parts)


def jp_crossbuck_mesh(*, arm: float = 1.2, height: float = 3.0):
    """踏切警標(× 印、黄地に黒の縁)+ 柱。板は +x を向く。"""
    parts = [_cylinder(0.05, height - 0.1) + (_C_GREY,)]
    w = 0.16
    for ang in (math.pi / 4, -math.pi / 4):
        c, s = math.cos(ang), math.sin(ang)
        rect = np.array([[-arm / 2, -w / 2], [arm / 2, -w / 2], [arm / 2, w / 2], [-arm / 2, w / 2]])
        R = np.array([[c, -s], [s, c]])
        yz = rect @ R.T + np.array([0.0, height - 0.3])
        parts.append(_plate_x(0.02, yz, _C_BLACK))
        rect2 = rect * np.array([0.97, 0.6])
        parts.append(_plate_x(0.035, rect2 @ R.T + np.array([0.0, height - 0.3]), _C_YELLOW))
    return _merge(parts)


def jp_pole_mesh(*, height: float = 10.0, r: float = 0.17):
    """電柱(コンクリート柱 + 腕金)。"""
    parts = [_cylinder(r, height, n=10) + ((0.66, 0.65, 0.62),), _box(0.1, 1.8, 0.1, z0=height - 1.0) + ((0.30, 0.30, 0.32),)]
    return _merge(parts)


def jp_mirror_mesh(*, height: float = 2.7, r: float = 0.3):
    """カーブミラー(橙の柱 + 丸い鏡、鏡は +x を向く)。"""
    ang = np.linspace(0, 2 * np.pi, 16, endpoint=False)
    disc = np.column_stack([r * np.cos(ang), height + r * np.sin(ang)])
    parts = [_cylinder(0.04, height) + (_C_ORANGE,), _plate_x(0.02, disc * np.array([1.08, 1.0]) + np.array([0.0, 0.0]), _C_ORANGE),
             _plate_x(0.035, disc, (0.80, 0.84, 0.90))]
    return _merge(parts)


# 「止まれ」の字形: 警察庁「交通規制基準」第 46 一時停止 図例(1)の寸法図(1 字 = 高さ 240 × 幅 80 cm、画の幅 15 cm、横棒の
# 太さ 30 cm、字間 1 m、停止線の 1〜3 m 手前から縦表示)。各字は [0,1]×[0,1](x = 運転者から見て右、y = 進む向き = 字の上)で、
# 画は (折線, 太さ[字幅に対する比]) —— 15 cm = 0.1875、30 cm = 0.375。曲線(ま の結び・れ の払い)は折線で近似した略字形。
_GLYPHS = {
    "止": [([(0.5, 1.0), (0.5, 0.125)], 0.1875), ([(0.5, 0.60), (1.0, 0.60)], 0.375), ([(0.19, 0.70), (0.19, 0.125)], 0.1875),
          ([(0.0, 0.0625), (1.0, 0.0625)], 0.375)],
    "ま": [([(0.0, 0.80), (1.0, 0.80)], 0.375), ([(0.0, 0.58), (1.0, 0.58)], 0.375), ([(0.5, 1.0), (0.5, 0.20)], 0.1875),
          ([(0.5, 0.20), (0.15, 0.14), (0.20, 0.0), (0.60, 0.0), (0.72, 0.10), (0.52, 0.30), (0.95, 0.0)], 0.1875)],
    "れ": [([(0.25, 1.0), (0.25, 0.0)], 0.1875), ([(0.0, 0.76), (0.5, 0.76)], 0.375),
          ([(0.25, 0.42), (0.0, 0.08)], 0.1875), ([(0.60, 1.0), (0.60, 0.08), (0.78, 0.0), (1.0, 0.22)], 0.1875)],
}


def _stroke_quads(P: np.ndarray, width: float, z: float):
    """折線 P (K,3 or K,2) を幅 width の帯(両側に width/2)にした平らな三角形。"""
    V, F = [], []
    for a, b in zip(P[:-1], P[1:]):
        d = b[:2] - a[:2]
        L = np.hypot(*d)
        if L < 1e-9:
            continue
        nrm = np.array([-d[1], d[0]]) / L * (width / 2)
        base = len(V)
        for q in (a[:2] - nrm, b[:2] - nrm, b[:2] + nrm, a[:2] + nrm):
            V.append([q[0], q[1], z])
        F += [[base, base + 1, base + 2], [base, base + 2, base + 3]]
    return np.asarray(V, np.float64).reshape(-1, 3), np.asarray(F, np.int64).reshape(-1, 3)


JP_TOMARE_CHAR_H_M, JP_TOMARE_CHAR_W_M, JP_TOMARE_GAP_M, JP_TOMARE_SETBACK_M = 2.4, 0.8, 1.0, 1.5


def jp_stop_marking_mesh(*, char_h: float = JP_TOMARE_CHAR_H_M, char_w: float = JP_TOMARE_CHAR_W_M, gap: float = JP_TOMARE_GAP_M,
                         z: float = 0.007):
    """路面文字「止まれ」(法定外表示、白)。局所座標: 原点 = 字の列の手前端(車に近い側)の車線中心、+x = 進む向き、+y = 左。

    寸法は警察庁「交通規制基準」第 46 の図例(1): 1 字 240 × 80 cm、画 15 cm、横棒 30 cm、字間 1 m、縦表示で遠い方から
    止・ま・れ(運転者は上から読む = 遠い字が上)。設置指針では停止線の 1〜3 m 手前から(:data:`JP_TOMARE_SETBACK_M`)。
    字形は折線の略字形(曲線は近似)。返り値 (V, F, colors)。**Raises** ``ValueError``: 寸法が正でない。"""
    if not (char_h > 0 and char_w > 0 and gap >= 0):
        raise ValueError("jp_stop_marking_mesh: char_h, char_w > 0 and gap >= 0")
    parts = []
    chars = ["れ", "ま", "止"]           # 手前から
    for k, ch in enumerate(chars):
        s0 = k * (char_h + gap)
        for strokep, wfrac in _GLYPHS[ch]:
            P = np.array([[s0 + gy * char_h, (0.5 - gx) * char_w] for gx, gy in strokep])
            Vq, Fq = _stroke_quads(P, wfrac * char_w, z)
            Vq[:, 0] = np.clip(Vq[:, 0], s0, s0 + char_h)                  # 帯の端を字の箱(240 × 80)に収める
            Vq[:, 1] = np.clip(Vq[:, 1], -char_w / 2, char_w / 2)
            parts.append((Vq, Fq, _C_WHITE))
    return _merge(parts)


def jp_stop_marking_length() -> float:
    """「止まれ」3 字の列の全長 [m](= 3 × 字高 + 2 × 字間 = 9.2 m)。"""
    return 3 * JP_TOMARE_CHAR_H_M + 2 * JP_TOMARE_GAP_M


# ----------------------------------------------------------------------------------------------------------------------
# 5. 世界
def _place(V: np.ndarray, x: float, y: float, yaw: float) -> np.ndarray:
    import driveworld as DW
    return DW.place_mesh(V, x, y, yaw, 0.0)


def _unit(a, b):
    d = np.asarray(b, np.float64) - np.asarray(a, np.float64)
    L = float(np.hypot(*d))
    return d / L if L > 1e-12 else np.array([1.0, 0.0]), L


def _flat_rect(centre, d, along, across, z, color):
    """中心 centre、向き d(単位)、長さ along(d 方向)・幅 across の平らな長方形。"""
    d = np.asarray(d, np.float64)
    n = np.array([-d[1], d[0]])
    c = np.asarray(centre, np.float64)
    q = [c - d * along / 2 - n * across / 2, c + d * along / 2 - n * across / 2, c + d * along / 2 + n * across / 2, c - d * along / 2 + n * across / 2]
    V = np.array([[p[0], p[1], z] for p in q])
    return V, np.array([[0, 1, 2], [0, 2, 3]], np.int64), color


def japan_world(graph: dict, *, step: float = 0.5, kerb_height: float = 0.15, kerb_width: float = 0.3, ground_step: float = 2.0,
                margin: float = 6.0, buildings=None, props: bool = True, pole_pitch: float = 30.0, lines: bool = True,
                tolerance_px: float = 0.75, side: str = "left") -> Dict[str, object]:
    """道路網から日本の町の 3-D 世界(driveworld 形式)を組む。

    路面 = 全体の格子平面(z 0、ラベル 0)。道路の和集合の **穴** = 街区: 歩道の面(z = kerb_height、ラベル 15)と縁石の帯(ラベル 1)。
    外側の縁にも縁石。車線の印(ラベル 9): 2 車線の両方向路は中央線を白の破線(5 m / 5 m)、4 車線以上は実線、車線境界は破線。交差点では
    他の辺の半幅ぶん印を切る。``props`` なら節点の特徴に: 信号機(``traffic_signals``、進入する辺ごと、交差点の向こう側・左)、横断歩道
    (``crossing``、進行方向に平行な 0.45 m の縞、ラベル 12)、一時停止(``stop`` / ``give_way``: 標識 + 停止線 + 「止まれ」、進入する辺ごと)、
    踏切(``level_crossing``: 2 本のレール(ラベル 8)+ 踏切警標 + 停止線)。生活道路(residential / unclassified / living_street)の
    通行側の縁に ``pole_pitch`` 間隔で電柱(ラベル 16)。``buildings`` = plateau_parse の建物の列なら押し出し柱(ラベル 14)。
    返り値 = driveworld の世界 + ``{"graph", "roadmask", "loops", "signals": [{"node", "edge", "object", "pose"}], "stats": {...}}``。
    **Raises** ``ValueError``: side が left/right 以外、kerb/step が不正。"""
    import driveworld as DW
    if side not in ("left", "right"):
        raise ValueError("japan_world: side must be 'left' or 'right'")
    if not (kerb_height > 0 and kerb_width > 0 and step > 0):
        raise ValueError("japan_world: kerb_height, kerb_width and step must be > 0")
    sgn = 1.0 if side == "left" else -1.0
    rm = osm_road_mask(graph, step=step, margin=margin)
    loops = osm_road_loops(rm, tolerance_px=tolerance_px)
    world = DW._empty_world()
    xmin, ymin = rm["xmin"], rm["ymin"]
    xmax, ymax = xmin + rm["shape"][1] * step, ymin + rm["shape"][0] * step
    world["bounds"] = (xmin, xmax, ymin, ymax)
    world["course"] = {"kind": "osm", "bbox": graph["bbox"]}
    def _inb(q):                      # 箱の外(片端だけ箱の中の辺の続き)には印も道具も置かない
        return xmin <= q[0] <= xmax and ymin <= q[1] <= ymax
    Vg, Fg = DW._grid_plane(xmin, xmax, ymin, ymax, step=ground_step)
    DW.world_add(world, Vg, Fg, 0, DW._ROAD_COLOR, name="ground")
    stats = {"blocks": 0, "blocks_skipped": 0, "blocks_rasterised": 0, "kerb_m": 0.0, "signals": 0, "crosswalks": 0, "stop_signs": 0, "crossings": 0,
             "poles": 0, "buildings": 0, "markings": 0}
    # 街区: 歩道の面 + 縁石(反時計回りに揃え、帯は外側 = 道路側)
    for P, Praw in zip(loops["holes"], loops["holes_raw"]):
        if len(P) < 3 or abs(_signed_area(P)) < 4.0:
            stats["blocks_skipped"] += 1
            continue
        if _signed_area(P) < 0:
            P = P[::-1]
        try:
            F = DW.polygon_triangulate(P)
            V = np.column_stack([P, np.full(len(P), kerb_height)])
        except ValueError:
            # 画素の角で自分に触れる輪郭(斜めに接する街区)は単純多角形でない → その街区の画素を行の束で埋める(面積は画素数に一致)
            V, F = _runs_mesh(Praw, rm, kerb_height)
            stats["blocks_rasterised"] += 1
            if not len(F):
                stats["blocks_skipped"] += 1
                continue
        DW.world_add(world, V, F, _LABEL_SIDEWALK, _C_SIDEWALK, name="sidewalk")
        Vk, Fk = DW._band_mesh(P, True, kerb_width, kerb_height)
        if len(Fk):
            DW.world_add(world, Vk, Fk, 1, _C_KERB, name="kerb:block")
        stats["blocks"] += 1
        stats["kerb_m"] += float(np.sum(np.hypot(*(np.roll(P, -1, axis=0) - P).T)))
    # 外側の縁: 時計回りに揃えると帯(右手側)が内側 = 道路側 … ではなく外へ出したいので反時計回りのまま(外 = 道路の外)
    for P in loops["outer"]:
        if len(P) < 3:
            continue
        if _signed_area(P) < 0:
            P = P[::-1]
        Vk, Fk = DW._band_mesh(P, True, kerb_width, kerb_height)
        if len(Fk):
            DW.world_add(world, Vk, Fk, 1, _C_KERB, name="kerb:outer")
        stats["kerb_m"] += float(np.sum(np.hypot(*(np.roll(P, -1, axis=0) - P).T)))
    N = graph["nodes"]
    E = graph["edges"]
    # 車線の印
    if lines:
        parts = []
        for k, e in enumerate(E):
            pa, pb = np.asarray(N[e["a"]]["xy"]), np.asarray(N[e["b"]]["xy"])
            d, L = _unit(pa, pb)
            ra, rb = _node_radius(graph, e["a"], exclude=k, d_in=d), _node_radius(graph, e["b"], exclude=k, d_in=d)
            s0, s1 = ra + 0.5, L - rb - 0.5
            if s1 - s0 < 1.0:
                continue
            n = np.array([-d[1], d[0]])
            offsets = []
            if not e["oneway"] and e["lanes"] >= 2:
                offsets.append((0.0, e["lanes"] <= 2))                      # 中央線: 2 車線は破線、それ以上は実線
            lw = e["width"] / max(1, e["lanes"])
            for j in range(1, e["lanes"]):
                off = -e["width"] / 2 + j * lw
                if abs(off) > 1e-6:
                    offsets.append((off, True))
            for off, dashed in offsets:
                if dashed:
                    s = s0
                    while s + 1.0 < s1:
                        seg = min(5.0, s1 - s)
                        c = pa + d * (s + seg / 2) + n * off
                        if _inb(c):
                            parts.append(_flat_rect(c, d, seg, 0.15, 0.006, _C_LINE))
                        s += 10.0
                else:
                    c = pa + d * ((s0 + s1) / 2) + n * off
                    if _inb(c):
                        parts.append(_flat_rect(c, d, s1 - s0, 0.15, 0.006, _C_LINE))
        if parts:
            V, F, C = _merge(parts)
            DW.world_add(world, V, F, 9, C, name="lane_marks")
            stats["markings"] = len(parts)
    signals = []
    if props:
        for i, nd in N.items():
            p = np.asarray(nd["xy"])
            feats = nd["features"]
            approaches = []                     # (辺の索引, 進入の向き d(節点へ), 幅)
            for k in nd["edges"]:
                e = E[k]
                other = e["b"] if e["a"] == i else e["a"]
                if e["oneway"] and e["b"] != i:
                    continue                    # 一方通行で節点から出て行く辺は進入しない
                d, _ = _unit(N[other]["xy"], p)
                approaches.append((k, d, e["width"]))
            if "traffic_signals" in feats and approaches and _inb(p):
                for k, d, w in approaches:
                    r = _node_radius(graph, i, exclude=k, d_in=d)
                    n = np.array([-d[1], d[0]]) * sgn
                    pos = p + d * (r + 0.6) + n * (w / 2 + 0.4)
                    yaw = math.atan2(-d[1], -d[0])
                    j = DW.add_signal(world, float(pos[0]), float(pos[1]), yaw, state="red", height=5.0)
                    signals.append({"node": i, "edge": k, "object": j, "pose": (float(pos[0]), float(pos[1]), yaw)})
                    stats["signals"] += 1
            if "crossing" in feats and nd["edges"] and nd["degree"] <= 2 and _inb(p):
                k = nd["edges"][0]
                e = E[k]
                d, _ = _unit(N[e["a"]]["xy"], N[e["b"]]["xy"])
                n = np.array([-d[1], d[0]])
                parts = []
                m = int(e["width"] / (2 * JP_CROSSWALK_STRIPE_M))
                for q in range(m):
                    off = -e["width"] / 2 + JP_CROSSWALK_STRIPE_M * (2 * q + 1)
                    if abs(off) + JP_CROSSWALK_STRIPE_M / 2 > e["width"] / 2:
                        continue
                    parts.append(_flat_rect(p + n * off, d, 4.0, JP_CROSSWALK_STRIPE_M, 0.006, _C_WHITE))
                if parts:
                    V, F, C = _merge(parts)
                    DW.world_add(world, V, F, 12, C, name="crosswalk", pose=(float(p[0]), float(p[1]), float(math.atan2(d[1], d[0]))))
                    stats["crosswalks"] += 1
            if ("stop" in feats or "give_way" in feats) and approaches and _inb(p):
                for k, d, w in approaches:
                    r = _node_radius(graph, i, exclude=k, d_in=d)
                    n = np.array([-d[1], d[0]]) * sgn
                    s_line = r + 1.0 if r > 0 else 0.0
                    lane_c = p - d * s_line + n * (w / 4 if not E[k]["oneway"] else 0.0)
                    half = w / 2 if not E[k]["oneway"] else w
                    V, F, C = _flat_rect(lane_c, d, JP_STOP_LINE_WIDTH_M, half, 0.006, _C_WHITE)
                    DW.world_add(world, V, F, 9, C, name="stop_line:stop_sign")
                    Vm, Fm, Cm = jp_stop_marking_mesh()
                    yaw = math.atan2(d[1], d[0])
                    org = lane_c - d * (JP_TOMARE_SETBACK_M + jp_stop_marking_length())
                    DW.world_add(world, _place(Vm, float(org[0]), float(org[1]), yaw), Fm, 9, Cm, name="marking:tomare")
                    Vs, Fs, Cs = jp_sign_stop_mesh()
                    pos = p - d * s_line + n * (w / 2 + 0.5)
                    DW.world_add(world, _place(Vs, float(pos[0]), float(pos[1]), math.atan2(-d[1], -d[0])), Fs, 4, Cs,
                                 name="sign:stop", pose=(float(pos[0]), float(pos[1]), math.atan2(-d[1], -d[0])))
                    stats["stop_signs"] += 1
            if "level_crossing" in feats and nd["edges"] and _inb(p):
                k = nd["edges"][0]
                e = E[k]
                d, _ = _unit(N[e["a"]]["xy"], N[e["b"]]["xy"])
                n = np.array([-d[1], d[0]])
                parts = [_flat_rect(p + d * off, n, e["width"] + 2.0, 0.07, 0.02, _C_RAIL) for off in (-0.72, 0.72)]
                V, F, C = _merge(parts)
                DW.world_add(world, V, F, 8, C, name="rails")
                for k2, d2, w in approaches:
                    n2 = np.array([-d2[1], d2[0]]) * sgn
                    lane_c = p - d2 * 3.0 + n2 * (w / 4 if not E[k2]["oneway"] else 0.0)
                    half = w / 2 if not E[k2]["oneway"] else w
                    V, F, C = _flat_rect(lane_c, d2, JP_STOP_LINE_WIDTH_M, half, 0.006, _C_WHITE)
                    DW.world_add(world, V, F, 9, C, name="stop_line:crossing")
                    Vx, Fx, Cx = jp_crossbuck_mesh()
                    pos = p - d2 * 2.5 + n2 * (w / 2 + 0.5)
                    DW.world_add(world, _place(Vx, float(pos[0]), float(pos[1]), math.atan2(-d2[1], -d2[0])), Fx, 4, Cx,
                                 name="sign:crossbuck", pose=(float(pos[0]), float(pos[1]), math.atan2(-d2[1], -d2[0])))
                stats["crossings"] += 1
        # 電柱: 生活道路の通行側の縁
        Vp, Fp, Cp = jp_pole_mesh()
        for k, e in enumerate(E):
            if e["highway"] not in ("residential", "unclassified", "living_street"):
                continue
            pa, pb = np.asarray(N[e["a"]]["xy"]), np.asarray(N[e["b"]]["xy"])
            d, L = _unit(pa, pb)
            n = np.array([-d[1], d[0]]) * sgn
            s = pole_pitch / 2
            while s < L - 2.0:
                pos = pa + d * s + n * (e["width"] / 2 + 0.5)
                if _inb(pos):
                    DW.world_add(world, _place(Vp, float(pos[0]), float(pos[1]), 0.0), Fp, _LABEL_POLE, Cp, name="pole",
                                 pose=(float(pos[0]), float(pos[1]), 0.0))
                    stats["poles"] += 1
                s += pole_pitch
    if buildings:
        import driveplateau as PL
        inside = [b for b in buildings if xmin <= float(np.mean(b["footprint"][:, 0])) <= xmax
                  and ymin <= float(np.mean(b["footprint"][:, 1])) <= ymax]
        if inside:
            V, F, C, _ids = PL.building_prisms(inside, base_z=0.0)
            DW.world_add(world, V, F, _LABEL_BUILDING, C, name="buildings")
            stats["buildings"] = len(inside)
        stats["buildings_outside"] = len(buildings) - len(inside)
    world.update({"graph": graph, "roadmask": rm, "loops": loops, "signals": signals, "stats": stats})
    return world


# ----------------------------------------------------------------------------------------------------------------------
# 6. 経路(最短路 → 車線中心の折線 + 停止線)
def _neighbors(graph: dict, i: int):
    for k in graph["nodes"][i]["edges"]:
        e = graph["edges"][k]
        if e["a"] == i:
            yield e["b"], k
        elif not e["oneway"]:
            yield e["a"], k


def osm_route(graph: dict, src: int, dst: int, *, side: str = "left", step: float = 0.5, lane_offset=None,
              signal_setback: float = 1.0, crossing_setback: float = 3.0) -> Dict[str, object]:
    """2 節点間の最短路(Dijkstra、一方通行を守る)を車線中心の折線にし、停止線を弧長で並べる。

    車線中心 = 辺の中心線を通行側(side)へ **幅/4**(両方向路)か 0(一方通行)だけ寄せた線(``lane_offset`` で上書き)。節点では隣り合う
    法線の平均で継ぐ(マイター)。停止線(drivetown.town_run が読む形 ``{"s", "x", "y", "yaw", "kind", "node", "element"}``):
    ``traffic_signals`` の節点 = "intersection"(交差する道の半幅 = 交差点の縁、の signal_setback 手前。同じ道の続きは数えない)、``stop`` / ``give_way`` = "stop_sign"(同じ位置)、
    ``level_crossing`` = "crossing"(crossing_setback 手前、``crossing_zone`` = レールの前後 1.5 m)。経路の最初の節点は飛ばす。
    返り値 ``{"kind": "route", "nodes", "edges", "polyline": (K,2), "cum": (K,), "length", "stop_lines", "side", "waypoints": (n,3) 節点の
    車線中心, "crosswalks": [s]}``。
    **Raises** ``ValueError``: 節点が無い、到達不能、side が不正。"""
    if side not in ("left", "right"):
        raise ValueError("osm_route: side must be 'left' or 'right'")
    N = graph["nodes"]
    if src not in N or dst not in N:
        raise ValueError("osm_route: src/dst must be node ids of the graph")
    if src == dst:
        raise ValueError("osm_route: src and dst must differ")
    dist = {src: 0.0}
    prev: Dict[int, Tuple[int, int]] = {}
    pq = [(0.0, src)]
    while pq:
        d0, i = heapq.heappop(pq)
        if d0 > dist.get(i, math.inf):
            continue
        if i == dst:
            break
        for j, k in _neighbors(graph, i):
            nd = d0 + graph["edges"][k]["length"]
            if nd < dist.get(j, math.inf):
                dist[j] = nd
                prev[j] = (i, k)
                heapq.heappush(pq, (nd, j))
    if dst not in prev:
        raise ValueError("osm_route: node %d is not reachable from %d" % (dst, src))
    path, eds = [dst], []
    while path[-1] != src:
        i, k = prev[path[-1]]
        path.append(i)
        eds.append(k)
    path.reverse()
    eds.reverse()
    sgn = 1.0 if side == "left" else -1.0
    E = graph["edges"]
    dirs, offs = [], []
    for i, k in zip(path[:-1], eds):
        e = E[k]
        j = e["b"] if e["a"] == i else e["a"]
        d, _ = _unit(N[i]["xy"], N[j]["xy"])
        dirs.append(d)
        off = (0.0 if e["oneway"] else e["width"] / 4) if lane_offset is None else float(lane_offset)
        offs.append(off)
    pts = []
    for q, i in enumerate(path):
        p = np.asarray(N[i]["xy"])
        if q == 0:
            d, off = dirs[0], offs[0]
            nrm = np.array([-d[1], d[0]]) * sgn
            pts.append(p + nrm * off)
        elif q == len(path) - 1:
            d, off = dirs[-1], offs[-1]
            nrm = np.array([-d[1], d[0]]) * sgn
            pts.append(p + nrm * off)
        else:
            n1 = np.array([-dirs[q - 1][1], dirs[q - 1][0]]) * sgn
            n2 = np.array([-dirs[q][1], dirs[q][0]]) * sgn
            m = n1 + n2
            Lm = float(np.hypot(*m))
            if Lm < 1e-9:
                m, Lm = n2, 1.0
            m = m / Lm
            off = 0.5 * (offs[q - 1] + offs[q])
            pts.append(p + m * (off / max(0.5, float(np.dot(m, n1)))))
    W = np.asarray(pts, np.float64)
    seg = np.hypot(*(W[1:] - W[:-1]).T)
    s_nodes = np.concatenate([[0.0], np.cumsum(seg)])
    # 標本化
    P = [W[0]]
    for a, b, L in zip(W[:-1], W[1:], seg):
        n = max(1, int(math.ceil(L / step)))
        for t in np.linspace(0, 1, n + 1)[1:]:
            P.append(a + (b - a) * t)
    P = np.asarray(P)
    cum = np.concatenate([[0.0], np.cumsum(np.hypot(*(P[1:] - P[:-1]).T))])
    stop_lines, crosswalks = [], []
    for q in range(1, len(path)):
        i = path[q]
        feats = N[i]["features"]
        k_in = eds[q - 1]
        d = dirs[q - 1]
        yaw = float(math.atan2(d[1], d[0]))
        r = _node_radius(graph, i, exclude=k_in, d_in=d)
        def line(kind, setback, zone=None):
            s_l = float(s_nodes[q] - setback)
            if s_l <= 0.0:
                return
            xy = W[q] - d * setback
            stop_lines.append({"s": s_l, "x": float(xy[0]), "y": float(xy[1]), "yaw": yaw, "kind": kind, "node": i, "element": q,
                               "crossing_zone": zone, "drawn": True})
        if "traffic_signals" in feats:
            line("intersection", r + signal_setback)
        elif "stop" in feats or "give_way" in feats:
            line("stop_sign", (r + signal_setback) if r > 0 else 0.0)
        if "level_crossing" in feats:
            line("crossing", crossing_setback, (float(s_nodes[q] - 1.5), float(s_nodes[q] + 1.5)))
        if "crossing" in feats:
            crosswalks.append(float(s_nodes[q]))
    stop_lines.sort(key=lambda d_: d_["s"])
    return {"kind": "route", "nodes": path, "edges": eds, "polyline": P, "cum": cum, "length": float(cum[-1]), "stop_lines": stop_lines,
            "side": side, "waypoints": np.column_stack([W, s_nodes]), "crosswalks": crosswalks, "graph_length": float(dist[dst])}


def japan_stats(graph: dict) -> Dict[str, object]:
    """道路網の内訳の表: 種別ごとの辺数・延長・平均幅、幅の由来の内訳、特徴のある節点の数。"""
    rows = {}
    for e in graph["edges"]:
        r = rows.setdefault(e["highway"], {"edges": 0, "length_m": 0.0, "width_sum": 0.0})
        r["edges"] += 1
        r["length_m"] += e["length"]
        r["width_sum"] += e["width"] * e["length"]
    table = [{"highway": k, "edges": v["edges"], "length_m": round(v["length_m"], 1),
              "mean_width_m": round(v["width_sum"] / v["length_m"], 2)} for k, v in sorted(rows.items(), key=lambda kv: -kv[1]["length_m"])]
    src = {}
    for e in graph["edges"]:
        src[e["width_from"]] = src.get(e["width_from"], 0) + 1
    feats = {f: sum(1 for n in graph["nodes"].values() if f in n["features"]) for f in NODE_FEATURES}
    return {"table": table, "width_from": src, "features": feats, "n_nodes": graph["n_nodes"], "n_edges": graph["n_edges"],
            "total_length_m": round(graph["total_length"], 1),
            "junctions": sum(1 for n in graph["nodes"].values() if n["degree"] >= 3), "license": graph.get("license", "")}
