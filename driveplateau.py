"""PLATEAU(CityGML 2.0)の建物を自前 3D 世界の押し出し柱に変える部品。

国交省 Project PLATEAU の 3D 都市モデル(CityGML 2.0, ``bldg:Building``)を
``xml.etree.ElementTree.iterparse`` でストリーム読みし、建物ごとに
足元の多角形(局所 x, y [m])・高さ・底面標高を取り出す。取り出した建物は
``building_prisms`` で頂点 V (n,3)・三角形 F (m,3)・面色 (m,3)・面→建物番号 (m,)
の押し出し柱メッシュになる。

依存は numpy と標準ライブラリだけ(lxml は使わない)。

座標系の約束
------------
PLATEAU の ``gml:posList`` は **EPSG:6697**(JGD2011 地理座標 + 東京湾平均海面高)で、
値の順序は **「緯度 経度 標高」(lat lon alt)** の 3 つ組である(経度が先ではない)。
本モジュールの局所座標は等距円筒(equirectangular)近似で、x = 東 [m]、y = 北 [m]、
z = 上 [m]。足元の多角形は上から見て **反時計回り**に正規化して返す。

名前空間の扱い
--------------
PLATEAU は bldg/gml/uro の名前空間 URI が版で異なりうるので、要素名の照合は
``{URI}local`` の **ローカル名だけ**で行う(接頭辞・URI に依存しない)。

後で ``drivejapan.py`` 本体に取り込む前提の 1 ファイル実装。
"""
from __future__ import annotations

import io
import math
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Sequence

import numpy as np

__all__ = [
    "EARTH_RADIUS_M",
    "latlon_to_local",
    "plateau_parse",
    "buildings_in_box",
    "building_prisms",
    "prism_mesh",
    "polygon_area",
    "triangulate_polygon",
    "citygml_synthetic",
]

#: 等距円筒近似に使う地球半径 [m](WGS84 / GRS80 の長半径)。
EARTH_RADIUS_M: float = 6378137.0

# CityGML 2.0 の名前空間(合成データ生成と、読み手のコメント用。照合には使わない)。
_NS_CORE = "http://www.opengis.net/citygml/2.0"
_NS_BLDG = "http://www.opengis.net/citygml/building/2.0"
_NS_GML = "http://www.opengis.net/gml"
_NS_GEN = "http://www.opengis.net/citygml/generics/2.0"


# --------------------------------------------------------------------------
# 1. 座標変換
# --------------------------------------------------------------------------
def latlon_to_local(
    lat: float | np.ndarray | Sequence[float],
    lon: float | np.ndarray | Sequence[float],
    origin: tuple[float, float],
) -> tuple[Any, Any]:
    """緯度経度 [deg] を原点まわりの局所座標 (x 東, y 北) [m] に変える(等距円筒近似)。

    x = R·cos(lat0)·Δlon[rad]、y = R·Δlat[rad]、R = 6378137 m。
    数 km 程度の範囲では歪みは 1e-4 オーダーで、道路・建物の配置には十分。

    Args:
        lat: 緯度 [deg]。スカラーか配列。
        lon: 経度 [deg]。``lat`` と同じ形。
        origin: ``(lat0, lon0)`` 原点の緯度経度 [deg]。

    Returns:
        ``(x, y)``。入力がスカラーなら float、配列なら同形の ndarray。

    Raises:
        ValueError: origin が 2 要素でない、緯度が ±90 を超える、非有限値を含む。
    """
    lat0, lon0 = _check_origin(origin)
    lat_a = np.asarray(lat, dtype=float)
    lon_a = np.asarray(lon, dtype=float)
    if lat_a.shape != lon_a.shape:
        raise ValueError(f"lat と lon の形が違います: {lat_a.shape} vs {lon_a.shape}")
    if not (np.all(np.isfinite(lat_a)) and np.all(np.isfinite(lon_a))):
        raise ValueError("lat/lon に非有限値があります")
    if np.any(np.abs(lat_a) > 90.0):
        raise ValueError("緯度は -90..90 [deg] の範囲でなければなりません")
    dlat = np.radians(lat_a - lat0)
    dlon = np.radians(lon_a - lon0)
    x = EARTH_RADIUS_M * math.cos(math.radians(lat0)) * dlon
    y = EARTH_RADIUS_M * dlat
    if lat_a.ndim == 0:
        return float(x), float(y)
    return x, y


def _local_to_latlon(
    x: float | np.ndarray | Sequence[float],
    y: float | np.ndarray | Sequence[float],
    origin: tuple[float, float],
) -> tuple[Any, Any]:
    """``latlon_to_local`` の逆変換(合成データ生成と検算に使う)。

    Args:
        x: 東向き局所座標 [m]。
        y: 北向き局所座標 [m]。
        origin: ``(lat0, lon0)`` [deg]。

    Returns:
        ``(lat, lon)`` [deg]。
    """
    lat0, lon0 = _check_origin(origin)
    x_a = np.asarray(x, dtype=float)
    y_a = np.asarray(y, dtype=float)
    if x_a.shape != y_a.shape:
        raise ValueError(f"x と y の形が違います: {x_a.shape} vs {y_a.shape}")
    if not (np.all(np.isfinite(x_a)) and np.all(np.isfinite(y_a))):
        raise ValueError("x/y に非有限値があります")
    lat = lat0 + np.degrees(y_a / EARTH_RADIUS_M)
    lon = lon0 + np.degrees(x_a / (EARTH_RADIUS_M * math.cos(math.radians(lat0))))
    if x_a.ndim == 0:
        return float(lat), float(lon)
    return lat, lon


def _check_origin(origin: Any) -> tuple[float, float]:
    """origin を検証して ``(lat0, lon0)`` の float 組にする。"""
    try:
        lat0, lon0 = origin
    except (TypeError, ValueError) as exc:
        raise ValueError(f"origin は (lat0, lon0) でなければなりません: {origin!r}") from exc
    lat0 = float(lat0)
    lon0 = float(lon0)
    if not (math.isfinite(lat0) and math.isfinite(lon0)):
        raise ValueError("origin に非有限値があります")
    if abs(lat0) >= 90.0:
        raise ValueError("origin の緯度は |lat0| < 90 でなければなりません(cos が 0 になる)")
    return lat0, lon0


# --------------------------------------------------------------------------
# 2. CityGML の読み取り
# --------------------------------------------------------------------------
def _local_name(tag: Any) -> str:
    """``{URI}local`` 形式のタグからローカル名だけを返す(URI 非依存)。"""
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _parse_poslist(text: str | None, srs_dim: str | None) -> np.ndarray:
    """``gml:posList`` の本文を (k,3) の [lat, lon, alt] 配列に変える。

    EPSG:6697 の値順は「緯度 経度 標高」。閉じたリング(先頭 == 末尾)は末尾を落とす。

    Raises:
        ValueError: 空、数値でない、3 の倍数でない、srsDimension が 3 以外、点が 3 未満。
    """
    if srs_dim is not None and srs_dim.strip() != "3":
        raise ValueError(f"posList の srsDimension={srs_dim!r} は未対応(3 のみ)")
    if text is None or not text.strip():
        raise ValueError("posList が空です")
    try:
        vals = np.array(text.split(), dtype=float)
    except ValueError as exc:
        raise ValueError(f"posList に数値でない要素があります: {exc}") from exc
    if vals.size % 3 != 0:
        raise ValueError(f"posList の要素数 {vals.size} が 3 の倍数ではありません")
    if not np.all(np.isfinite(vals)):
        raise ValueError("posList に非有限値があります")
    pts = vals.reshape(-1, 3)  # 列 = [lat, lon, alt]
    if pts.shape[0] >= 2 and np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    if pts.shape[0] < 3:
        raise ValueError(f"posList の点が {pts.shape[0]} 個しかありません(3 以上必要)")
    if np.any(np.abs(pts[:, 0]) > 90.0):
        raise ValueError("posList の第 1 成分(緯度)が ±90 を超えています。値順は lat lon alt のはず")
    return pts


def _iter_poslists(elem: ET.Element) -> Iterator[tuple[str | None, str | None]]:
    """要素配下のすべての ``posList`` を (本文, srsDimension) で返す。"""
    for sub in elem.iter():
        if _local_name(sub.tag) == "posList":
            yield sub.text, sub.get("srsDimension")


def _first_child_by_local(elem: ET.Element, name: str) -> ET.Element | None:
    """子孫から最初のローカル名一致要素を返す(無ければ None)。"""
    for sub in elem.iter():
        if sub is elem:
            continue
        if _local_name(sub.tag) == name:
            return sub
    return None


def _building_record(elem: ET.Element) -> dict[str, Any] | None:
    """1 つの ``bldg:Building`` 要素から生の建物情報(lat/lon のまま)を抜く。

    Returns:
        ``{"id", "ring_latlon" (k,3), "height", "ground_z"}`` か、
        足元・高さが決まらない建物なら None(呼び手が n_skipped に数える)。

    Raises:
        ValueError: posList が壊れている(fail-closed)。
    """
    gml_id = None
    for key, val in elem.attrib.items():
        if _local_name(key) == "id":
            gml_id = val
            break

    measured: float | None = None
    mh = _first_child_by_local(elem, "measuredHeight")
    if mh is not None and mh.text is not None and mh.text.strip():
        try:
            measured = float(mh.text.strip())
        except ValueError as exc:
            raise ValueError(f"measuredHeight が数値ではありません: {mh.text!r}") from exc
        if not math.isfinite(measured):
            raise ValueError("measuredHeight が非有限値です")

    ring: np.ndarray | None = None
    solid_min: float | None = None
    solid_max: float | None = None

    # BuildingPart 配下は別の建物部位なので、ここでは直下の Building 本体の
    # lod0FootPrint / lod1Solid だけを見る(未検証: 実データで BuildingPart 主体の棟)。
    fp = _first_child_by_local(elem, "lod0FootPrint")
    if fp is not None:
        rings = [_parse_poslist(t, d) for t, d in _iter_poslists(fp)]
        if rings:
            # lod0FootPrint が MultiSurface で複数面なら面積最大の面を足元にする。
            ring = max(rings, key=lambda r: abs(_shoelace_latlon(r)))

    solid = _first_child_by_local(elem, "lod1Solid")
    if solid is not None:
        faces = [_parse_poslist(t, d) for t, d in _iter_poslists(solid)]
        if faces:
            alts = np.concatenate([f[:, 2] for f in faces])
            solid_min = float(alts.min())
            solid_max = float(alts.max())
            if ring is None:
                # LOD1 は押し出し柱なので、平均標高が最も低い面が底面。
                ring = min(faces, key=lambda f: float(f[:, 2].mean()))

    if ring is None:
        return None

    height: float | None = measured
    if height is None:
        if solid_min is None or solid_max is None:
            return None
        height = solid_max - solid_min
    if not (height > 0.0):
        return None

    ground_z = float(ring[:, 2].mean())
    return {"id": gml_id, "ring_latlon": ring, "height": float(height), "ground_z": ground_z}


def _shoelace_latlon(ring: np.ndarray) -> float:
    """lat/lon 平面での符号つき面積(度²)。面の大小比較にだけ使う。"""
    lat = ring[:, 0]
    lon = ring[:, 1]
    return 0.5 * float(np.dot(lon, np.roll(lat, -1)) - np.dot(np.roll(lon, -1), lat))


def _open_source(source: str | Path | bytes) -> Any:
    """source(XML 文字列 / bytes / パス)を iterparse に渡せるバイナリ stream にする。"""
    if isinstance(source, bytes):
        if not source.strip():
            raise ValueError("source が空です")
        return io.BytesIO(source)
    if isinstance(source, Path):
        if not source.is_file():
            raise ValueError(f"ファイルがありません: {source}")
        return open(source, "rb")
    if isinstance(source, str):
        s = source.strip()
        if not s:
            raise ValueError("source が空文字です")
        if s.startswith("<"):
            return io.BytesIO(source.encode("utf-8"))
        p = Path(source)
        if not p.is_file():
            raise ValueError(f"source は XML 文字列でもファイルパスでもありません: {source[:80]!r}")
        return open(p, "rb")
    raise ValueError(f"source の型が未対応です: {type(source).__name__}")


def plateau_parse(
    source: str | Path | bytes,
    *,
    origin: tuple[float, float] | None = None,
    max_buildings: int | None = None,
) -> dict[str, Any]:
    """PLATEAU CityGML から建物の足元多角形・高さ・底面標高をストリーム読みする。

    ``iterparse`` で ``Building``(ローカル名)の end イベントごとに処理し、
    処理後 ``elem.clear()`` でメモリを解放する(1 ファイル数百 MB でも動く設計)。

    建物ごとに:
      * ``measuredHeight`` があれば高さに使う。無ければ ``lod1Solid`` の最大標高 − 最小標高。
      * 足元: ``lod0FootPrint`` があればその posList。無ければ ``lod1Solid`` の全面のうち
        **平均標高が最も低い面**(LOD1 は押し出し柱なので底面がある)。
      * posList は EPSG:6697 の「緯度 経度 標高」3 つ組として読む。

    Args:
        source: CityGML の文字列(``<`` で始まる)、bytes、またはファイルパス(str/Path)。
        origin: 局所座標の原点 ``(lat0, lon0)`` [deg]。None なら最初に採用した建物の重心。
        max_buildings: 採用する建物数の上限(None で無制限)。到達したら読み取りを止める。

    Returns:
        ``{"origin": (lat0, lon0), "buildings": [...], "n_skipped": int,
        "crs": "EPSG:6697 (lat, lon, alt)"}``。各建物は
        ``{"id", "footprint" (k,2) float64(局所 x,y[m]、閉じない、反時計回り),
        "height", "ground_z", "lat", "lon"}``(lat/lon は足元頂点の平均 = 重心)。

    Raises:
        ValueError: source が空/不正、posList が 3 の倍数でない、XML が壊れている、
            max_buildings が負、origin が不正。
    """
    if max_buildings is not None:
        if not isinstance(max_buildings, int) or isinstance(max_buildings, bool) or max_buildings < 0:
            raise ValueError(f"max_buildings は非負整数か None: {max_buildings!r}")
    if origin is not None:
        origin = _check_origin(origin)

    stream = _open_source(source)
    raw: list[dict[str, Any]] = []
    n_skipped = 0
    try:
        try:
            for _event, elem in ET.iterparse(stream, events=("end",)):
                name = _local_name(elem.tag)
                if name == "Building":
                    try:
                        rec = _building_record(elem)
                    finally:
                        elem.clear()
                    if rec is None:
                        n_skipped += 1
                    else:
                        raw.append(rec)
                        if max_buildings is not None and len(raw) >= max_buildings:
                            break
                elif name == "cityObjectMember":
                    # Building を包む要素も空にして木の成長を止める。
                    elem.clear()
        except ET.ParseError as exc:
            raise ValueError(f"CityGML の XML 解析に失敗: {exc}") from exc
    finally:
        stream.close()

    if origin is None:
        if not raw:
            raise ValueError("建物が 1 つも読めず、origin も指定されていません")
        first = raw[0]["ring_latlon"]
        origin = (float(first[:, 0].mean()), float(first[:, 1].mean()))

    buildings: list[dict[str, Any]] = []
    for rec in raw:
        ring = rec["ring_latlon"]
        x, y = latlon_to_local(ring[:, 0], ring[:, 1], origin)
        fp = np.column_stack([x, y]).astype(float)
        fp = _dedupe_consecutive(fp)
        if fp.shape[0] < 3:
            n_skipped += 1
            continue
        area = polygon_area(fp)
        if abs(area) < 1e-9:
            n_skipped += 1
            continue
        if area < 0.0:
            fp = fp[::-1].copy()
        buildings.append(
            {
                "id": rec["id"],
                "footprint": fp,
                "height": rec["height"],
                "ground_z": rec["ground_z"],
                "lat": float(ring[:, 0].mean()),
                "lon": float(ring[:, 1].mean()),
            }
        )

    return {
        "origin": (float(origin[0]), float(origin[1])),
        "buildings": buildings,
        "n_skipped": n_skipped,
        "crs": "EPSG:6697 (lat, lon, alt)",
    }


def _dedupe_consecutive(poly: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    """隣り合う同一点(環状に末尾→先頭も)を落とす。"""
    if poly.shape[0] == 0:
        return poly
    keep = [0]
    for i in range(1, poly.shape[0]):
        if np.linalg.norm(poly[i] - poly[keep[-1]]) > eps:
            keep.append(i)
    if len(keep) > 1 and np.linalg.norm(poly[keep[-1]] - poly[keep[0]]) <= eps:
        keep.pop()
    return poly[keep]


# --------------------------------------------------------------------------
# 3. 箱で絞る
# --------------------------------------------------------------------------
def buildings_in_box(
    parsed: dict[str, Any], xmin: float, xmax: float, ymin: float, ymax: float
) -> list[dict[str, Any]]:
    """重心(足元頂点の平均)が箱 [xmin,xmax]×[ymin,ymax] に入る建物だけを返す。

    Args:
        parsed: ``plateau_parse`` の返り値。
        xmin, xmax, ymin, ymax: 局所座標の箱 [m](両端を含む)。

    Raises:
        ValueError: parsed に ``buildings`` が無い、xmin > xmax または ymin > ymax。
    """
    if not isinstance(parsed, dict) or "buildings" not in parsed:
        raise ValueError("parsed は plateau_parse の返り値(dict with 'buildings')でなければなりません")
    if not (xmin <= xmax and ymin <= ymax):
        raise ValueError(f"箱が反転しています: x[{xmin},{xmax}] y[{ymin},{ymax}]")
    out: list[dict[str, Any]] = []
    for b in parsed["buildings"]:
        c = np.asarray(b["footprint"], dtype=float).mean(axis=0)
        if xmin <= c[0] <= xmax and ymin <= c[1] <= ymax:
            out.append(b)
    return out


# --------------------------------------------------------------------------
# 4. 多角形の道具と押し出し
# --------------------------------------------------------------------------
def polygon_area(poly: np.ndarray | Sequence[Sequence[float]]) -> float:
    """単純多角形の符号つき面積(靴紐公式)。反時計回りで正。

    Args:
        poly: (k,2) の頂点列。閉じていなくてよい。

    Raises:
        ValueError: 形が (k,2) でない、k < 3、非有限値。
    """
    p = _check_polygon(poly)
    x = p[:, 0]
    y = p[:, 1]
    return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))


def _check_polygon(poly: Any) -> np.ndarray:
    p = np.asarray(poly, dtype=float)
    if p.ndim != 2 or p.shape[1] != 2:
        raise ValueError(f"多角形は (k,2) でなければなりません: shape={p.shape}")
    if p.shape[0] < 3:
        raise ValueError(f"多角形の頂点が {p.shape[0]} 個しかありません(3 以上必要)")
    if not np.all(np.isfinite(p)):
        raise ValueError("多角形に非有限値があります")
    return p


def _cross2(o: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    """2D 外積 (a-o)×(b-o)。"""
    return float((a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]))


def _point_in_triangle(p: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray, eps: float) -> bool:
    """点 p が三角形 abc(反時計回り)の内部または辺上にあるか。"""
    return (
        _cross2(a, b, p) >= -eps
        and _cross2(b, c, p) >= -eps
        and _cross2(c, a, p) >= -eps
    )


def triangulate_polygon(poly: np.ndarray | Sequence[Sequence[float]]) -> np.ndarray:
    """単純多角形(凸・凹どちらも、自己交差なし)を耳切り法で三角形分割する。

    返す三角形は入力頂点の添字 (k-2, 3) で、各三角形は反時計回り(入力が時計回りなら
    内部で反転して扱い、添字は元の頂点番号で返す)。

    Args:
        poly: (k,2) 頂点列。閉じていなくてよい。

    Returns:
        (k-2, 3) int64 配列。

    Raises:
        ValueError: 頂点が 3 未満、面積がほぼ 0、耳が見つからない(自己交差や重複点の疑い)。
    """
    p = _check_polygon(poly)
    area = polygon_area(p)
    scale = float(np.max(np.abs(p - p.mean(axis=0)))) or 1.0
    eps = 1e-12 * scale * scale
    if abs(area) <= eps:
        raise ValueError("多角形の面積がほぼ 0 で三角形分割できません")
    idx = list(range(p.shape[0]))
    if area < 0.0:
        idx = idx[::-1]  # 反時計回りに揃える

    # 一直線上の頂点(外積 ≈ 0)は先に落としておく。耳切りが詰まる原因になる。
    changed = True
    while changed and len(idx) > 3:
        changed = False
        for k in range(len(idx)):
            a, b, c = p[idx[k - 1]], p[idx[k]], p[idx[(k + 1) % len(idx)]]
            if abs(_cross2(a, b, c)) <= eps:
                del idx[k]
                changed = True
                break

    tris: list[tuple[int, int, int]] = []
    guard = 0
    while len(idx) > 3:
        guard += 1
        if guard > 10 * p.shape[0] + 10:
            raise ValueError("耳切りが収束しません(自己交差または重複頂点の疑い)")
        found = False
        n = len(idx)
        for k in range(n):
            i_prev, i_cur, i_next = idx[k - 1], idx[k], idx[(k + 1) % n]
            a, b, c = p[i_prev], p[i_cur], p[i_next]
            if _cross2(a, b, c) <= eps:
                continue  # 凹頂点(または一直線)は耳ではない
            ear = True
            for j in idx:
                if j in (i_prev, i_cur, i_next):
                    continue
                q = p[j]
                if (np.allclose(q, a) or np.allclose(q, b) or np.allclose(q, c)):
                    continue
                if _point_in_triangle(q, a, b, c, eps):
                    ear = False
                    break
            if ear:
                tris.append((i_prev, i_cur, i_next))
                del idx[k]
                found = True
                break
        if not found:
            raise ValueError("耳が見つかりません(自己交差多角形の疑い)")
    tris.append((idx[0], idx[1], idx[2]))
    return np.asarray(tris, dtype=np.int64)


def prism_mesh(
    footprint: np.ndarray | Sequence[Sequence[float]],
    height: float,
    *,
    base_z: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """足元多角形を高さ ``height`` の柱に押し出す(底面なし)。

    頂点の並びは ``V[0:k]`` が底の環、``V[k:2k]`` が天井の環(同じ順)。
    側面は辺ごとに四角形 2 三角形、屋根は耳切りの三角形。外向き法線になる向きで返す。

    Args:
        footprint: (k,2) 局所 x,y [m]。向きは任意(内部で反時計回りに揃える)。
        height: 柱の高さ [m] > 0。
        base_z: 底の z [m]。

    Returns:
        ``(V (2k,3) float64, F (m,3) int64, is_roof (m,) bool)``。

    Raises:
        ValueError: height ≤ 0 / 非有限、footprint が不正。
    """
    if not (isinstance(height, (int, float)) and math.isfinite(height) and height > 0.0):
        raise ValueError(f"height は正の有限値でなければなりません: {height!r}")
    if not (isinstance(base_z, (int, float)) and math.isfinite(base_z)):
        raise ValueError(f"base_z は有限値でなければなりません: {base_z!r}")
    p = _check_polygon(footprint)
    if polygon_area(p) < 0.0:
        p = p[::-1].copy()
    k = p.shape[0]
    bottom = np.column_stack([p, np.full(k, float(base_z))])
    top = np.column_stack([p, np.full(k, float(base_z) + float(height))])
    V = np.vstack([bottom, top])

    faces: list[tuple[int, int, int]] = []
    roof_flags: list[bool] = []
    for i in range(k):
        j = (i + 1) % k
        # 反時計回り足元で辺 i→j の右側が外。(b_i, b_j, t_j), (b_i, t_j, t_i) で外向き。
        faces.append((i, j, k + j))
        faces.append((i, k + j, k + i))
        roof_flags += [False, False]
    for tri in triangulate_polygon(p):
        faces.append((k + int(tri[0]), k + int(tri[1]), k + int(tri[2])))
        roof_flags.append(True)
    return V, np.asarray(faces, dtype=np.int64), np.asarray(roof_flags, dtype=bool)


def _default_building_color(building: dict[str, Any]) -> tuple[float, float, float]:
    """既定の建物色: 高さで少し変わる灰〜ベージュ(決定的、乱数なし)。

    低い建物は暖色寄りのベージュ、高いほど冷たい灰に寄る。0..1 の RGB。
    """
    h = float(building.get("height", 10.0))
    t = min(max(h / 60.0, 0.0), 1.0)
    low = np.array([0.82, 0.78, 0.70])
    high = np.array([0.68, 0.69, 0.72])
    rgb = (1.0 - t) * low + t * high
    return (float(rgb[0]), float(rgb[1]), float(rgb[2]))


def building_prisms(
    buildings: Iterable[dict[str, Any]],
    *,
    color_fn: Callable[[dict[str, Any]], Sequence[float]] | None = None,
    base_z: float | None = 0.0,
    roof_shade: float = 0.92,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """建物列を押し出し柱メッシュにまとめる。

    Args:
        buildings: ``plateau_parse`` の ``buildings``(``footprint``, ``height``, ``ground_z``)。
        color_fn: ``building -> (r,g,b)`` 0..1。None なら ``_default_building_color``。
        base_z: 全建物の底 z [m]。None なら各建物の ``ground_z`` を使う(起伏のある世界向け)。
            自前の平らな道路世界には 0.0 が合う。
        roof_shade: 屋根面の色の倍率(側面と見分けるための控えめな陰)。

    Returns:
        ``(V (n,3) float64, F (m,3) int64, colors (m,3) float64 0..1, ids (m,) int64)``。
        ``ids[f]`` は面 f が属する建物の番号(入力列の添字)。建物が 0 件なら各配列は空。

    Raises:
        ValueError: color_fn の返り値が RGB 3 要素 0..1 でない、建物の footprint/height が不正。
    """
    fn = color_fn if color_fn is not None else _default_building_color
    if not (0.0 < roof_shade <= 1.0):
        raise ValueError(f"roof_shade は (0,1] でなければなりません: {roof_shade!r}")
    Vs: list[np.ndarray] = []
    Fs: list[np.ndarray] = []
    Cs: list[np.ndarray] = []
    Is: list[np.ndarray] = []
    offset = 0
    for bi, b in enumerate(buildings):
        if not isinstance(b, dict) or "footprint" not in b or "height" not in b:
            raise ValueError(f"建物 {bi} に footprint/height がありません")
        bz = float(b.get("ground_z", 0.0)) if base_z is None else float(base_z)
        V, F, is_roof = prism_mesh(b["footprint"], float(b["height"]), base_z=bz)
        rgb = np.asarray(fn(b), dtype=float).reshape(-1)
        if rgb.shape != (3,) or not np.all(np.isfinite(rgb)) or np.any(rgb < 0.0) or np.any(rgb > 1.0):
            raise ValueError(f"color_fn は 0..1 の RGB 3 要素を返す必要があります: {rgb!r}")
        C = np.tile(rgb, (F.shape[0], 1))
        C[is_roof] *= roof_shade
        Vs.append(V)
        Fs.append(F + offset)
        Cs.append(C)
        Is.append(np.full(F.shape[0], bi, dtype=np.int64))
        offset += V.shape[0]
    if not Vs:
        return (
            np.zeros((0, 3), dtype=float),
            np.zeros((0, 3), dtype=np.int64),
            np.zeros((0, 3), dtype=float),
            np.zeros((0,), dtype=np.int64),
        )
    return np.vstack(Vs), np.vstack(Fs), np.vstack(Cs), np.concatenate(Is)


# --------------------------------------------------------------------------
# 5. テスト用の合成 CityGML
# --------------------------------------------------------------------------
def _fmt(v: float) -> str:
    """posList 用の数値表記(repr で丸めずに書く)。"""
    return repr(float(v))


def _ring_text(ring_latlon: Sequence[tuple[float, float, float]]) -> str:
    """閉じた LinearRing の posList 本文(lat lon alt の順、先頭を末尾に繰り返す)。"""
    pts = list(ring_latlon) + [ring_latlon[0]]
    return " ".join(f"{_fmt(a)} {_fmt(b)} {_fmt(c)}" for a, b, c in pts)


def citygml_synthetic(
    n: int = 4,
    *,
    origin: tuple[float, float] = (35.6716, 139.7650),
    spacing: float = 30.0,
    size: float = 12.0,
    heights: Sequence[float] | None = None,
    ground_z: float = 0.0,
    omit_measured_height: Iterable[int] = (),
    use_lod0_footprint: bool = False,
    ns_building: str = _NS_BLDG,
) -> str:
    """本物と同じ構造の最小 CityGML 2.0 文字列を作る(テスト・デモ用)。

    建物は ``size`` [m] の正方形を ``spacing`` [m] 間隔で x 方向に並べ、各建物に
    ``bldg:measuredHeight`` と ``bldg:lod1Solid > gml:Solid > gml:exterior >
    gml:CompositeSurface > gml:surfaceMember × 6 > gml:Polygon > gml:exterior >
    gml:LinearRing > gml:posList``(底面 + 側面 4 + 天面、lat lon alt の順)を書く。
    等距円筒近似は線形なので、局所座標で作った正方形は読み戻すと面積が size² に一致する。

    Args:
        n: 建物数(≥ 0)。
        origin: 建物 0 の中心の (lat, lon) [deg]。
        spacing: 建物中心の間隔 [m]。
        size: 正方形の一辺 [m]。
        heights: 各建物の高さ [m]。None なら ``10 + 5*i``。
        ground_z: 底面の標高 [m]。
        omit_measured_height: この添字の建物では ``measuredHeight`` を書かない。
        use_lod0_footprint: True なら lod1Solid の前に ``lod0FootPrint``(底面のみ)も書く。
        ns_building: bldg 名前空間 URI(版違いの試験用に差し替え可)。

    Returns:
        UTF-8 で書き出せる CityGML 文字列。

    Raises:
        ValueError: n が負、size/spacing が非正、heights の長さ不一致や非正。
    """
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise ValueError(f"n は非負整数: {n!r}")
    if not (size > 0.0 and spacing > 0.0):
        raise ValueError("size と spacing は正でなければなりません")
    if heights is None:
        heights = [10.0 + 5.0 * i for i in range(n)]
    heights = [float(h) for h in heights]
    if len(heights) != n:
        raise ValueError(f"heights の長さ {len(heights)} が n={n} と違います")
    if any(not (h > 0.0) for h in heights):
        raise ValueError("heights は正でなければなりません")
    omit = set(int(i) for i in omit_measured_height)
    lat0, lon0 = _check_origin(origin)

    half = size / 2.0
    members: list[str] = []
    for i in range(n):
        cx = spacing * i
        cy = 0.0
        # 上から見て反時計回りの底の環(局所 x,y)
        corners_xy = [(cx - half, cy - half), (cx + half, cy - half), (cx + half, cy + half), (cx - half, cy + half)]
        corners_ll = [_local_to_latlon(x, y, (lat0, lon0)) for x, y in corners_xy]
        z0 = float(ground_z)
        z1 = z0 + heights[i]
        bottom = [(la, lo, z0) for la, lo in corners_ll]
        top = [(la, lo, z1) for la, lo in corners_ll]
        faces: list[Sequence[tuple[float, float, float]]] = []
        faces.append(bottom[::-1])  # 底面は下向き法線になる順(時計回り)
        for a in range(4):
            b = (a + 1) % 4
            faces.append([bottom[a], bottom[b], top[b], top[a]])  # 側面
        faces.append(top)  # 天面
        surf = "\n".join(
            "          <gml:surfaceMember>\n"
            "            <gml:Polygon>\n"
            "              <gml:exterior>\n"
            "                <gml:LinearRing>\n"
            f"                  <gml:posList>{_ring_text(f)}</gml:posList>\n"
            "                </gml:LinearRing>\n"
            "              </gml:exterior>\n"
            "            </gml:Polygon>\n"
            "          </gml:surfaceMember>"
            for f in faces
        )
        mh = "" if i in omit else f"      <bldg:measuredHeight uom=\"m\">{_fmt(heights[i])}</bldg:measuredHeight>\n"
        lod0 = ""
        if use_lod0_footprint:
            lod0 = (
                "      <bldg:lod0FootPrint>\n"
                "        <gml:MultiSurface>\n"
                "          <gml:surfaceMember>\n"
                "            <gml:Polygon>\n"
                "              <gml:exterior>\n"
                "                <gml:LinearRing>\n"
                f"                  <gml:posList>{_ring_text(bottom)}</gml:posList>\n"
                "                </gml:LinearRing>\n"
                "              </gml:exterior>\n"
                "            </gml:Polygon>\n"
                "          </gml:surfaceMember>\n"
                "        </gml:MultiSurface>\n"
                "      </bldg:lod0FootPrint>\n"
            )
        members.append(
            "  <core:cityObjectMember>\n"
            f"    <bldg:Building gml:id=\"bldg_synth_{i:04d}\">\n"
            f"{mh}"
            f"{lod0}"
            "      <bldg:lod1Solid>\n"
            "        <gml:Solid>\n"
            "          <gml:exterior>\n"
            "            <gml:CompositeSurface>\n"
            f"{surf}\n"
            "            </gml:CompositeSurface>\n"
            "          </gml:exterior>\n"
            "        </gml:Solid>\n"
            "      </bldg:lod1Solid>\n"
            "    </bldg:Building>\n"
            "  </core:cityObjectMember>"
        )

    # boundedBy の Envelope(PLATEAU と同じく srsName は EPSG:6697、順序は lat lon alt)
    ext = spacing * max(n - 1, 0) + size
    lo_lat, lo_lon = _local_to_latlon(-half, -half, (lat0, lon0))
    hi_lat, hi_lon = _local_to_latlon(ext - half, half, (lat0, lon0))
    zmax = float(ground_z) + (max(heights) if heights else 0.0)
    body = "\n".join(members)
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<core:CityModel"
        f" xmlns:core=\"{_NS_CORE}\""
        f" xmlns:bldg=\"{ns_building}\""
        f" xmlns:gml=\"{_NS_GML}\""
        f" xmlns:gen=\"{_NS_GEN}\""
        " xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\">\n"
        "  <gml:boundedBy>\n"
        "    <gml:Envelope srsName=\"http://www.opengis.net/def/crs/EPSG/0/6697\" srsDimension=\"3\">\n"
        f"      <gml:lowerCorner>{_fmt(lo_lat)} {_fmt(lo_lon)} {_fmt(ground_z)}</gml:lowerCorner>\n"
        f"      <gml:upperCorner>{_fmt(hi_lat)} {_fmt(hi_lon)} {_fmt(zmax)}</gml:upperCorner>\n"
        "    </gml:Envelope>\n"
        "  </gml:boundedBy>\n"
        f"{body}\n"
        "</core:CityModel>\n"
    )
