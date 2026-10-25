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
    "plateau_lod2_mesh",
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
                        if max_buildings is not None and len(raw) >= max_buildings:
                            break
                        raw.append(rec)
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

    返す三角形は入力頂点の添字で、共線頂点を除いた有効頂点数を m として (m-2, 3)。各三角形は反時計回り(入力が時計回りなら
    内部で反転して扱い、添字は元の頂点番号で返す)。

    Args:
        poly: (k,2) 頂点列。閉じていなくてよい。

    Returns:
        (m-2, 3) int64 配列。m は共線頂点を除いた有効頂点数。

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
    """建物の足跡(footprint)を高さまで押し出し、1 つの三角形メッシュにまとめる。

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

    空の入力(``buildings`` が 0 件)は空を返す(理由: 建物が 0 件のタイルは実データに普通にある。空の角柱集合が正しい答え)。
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


# --------------------------------------------------------------------------
# 6. LOD2 の建物 → 三角形メッシュ(屋根・壁・地面の面種つき、BuildingPart ごと)
# --------------------------------------------------------------------------
#: GRS80 楕円体(JGD2011 の基準楕円体)の長半径 [m] と扁平率。
_GRS80_A: float = 6378137.0
_GRS80_F: float = 1.0 / 298.257222101

#: 面種の番号 → 名前。``face_kind`` はこの番号で持つ。
LOD2_KINDS: tuple[str, ...] = ("ground", "wall", "roof", "other")

#: ``bldg:boundedBy`` の子(主題面)のローカル名 → 面種番号。表に無い名前は fail-closed で拒否する。
_LOD2_SURFACE_KIND: dict[str, int] = {
    "GroundSurface": 0,
    "WallSurface": 1,
    "RoofSurface": 2,
    "OuterCeilingSurface": 3,
    "OuterFloorSurface": 3,
    "ClosureSurface": 3,
}

#: LOD2 の幾何の部分木に現れてよい gml 要素のローカル名。これ以外(``Triangle``・``OrientableSurface``・
#: ``pos`` の点列・曲線など)は読み方を決めていないので **黙って捨てずに拒否する**。
_LOD2_GML_ALLOWED: frozenset[str] = frozenset(
    {"MultiSurface", "CompositeSurface", "Solid", "surfaceMember", "Polygon", "exterior", "interior",
     "LinearRing", "posList"}
)

#: 建物・部位の直下から拾う単純属性(ローカル名)。
_LOD2_SIMPLE_ATTRS: tuple[str, ...] = (
    "name", "class", "usage", "function", "yearOfConstruction", "storeysAboveGround", "storeysBelowGround",
)


def _geodetic_to_enu(llh: np.ndarray, origin: tuple[float, float, float]) -> np.ndarray:
    """(n,3) の [緯度 deg, 経度 deg, 高さ m] を、原点の接平面の局所 ENU [m](x 東, y 北, z 上)へ厳密に移す。

    GRS80 楕円体で地心直交座標(ECEF)へ上げてから原点の回転で ENU に落とす(近似なし)。PLATEAU の高さは
    標高(東京湾平均海面)なので楕円体高との差(ジオイド高、横浜で約 37 m)を無視している —— その影響は
    ECEF の半径が 37 m ずれるだけで、数百 m の範囲の水平距離に 6e-6 の相対誤差しか生まない。
    """
    a, f = _GRS80_A, _GRS80_F
    e2 = f * (2.0 - f)

    def ecef(lat_d: np.ndarray, lon_d: np.ndarray, h: np.ndarray) -> np.ndarray:
        lat = np.radians(lat_d)
        lon = np.radians(lon_d)
        n = a / np.sqrt(1.0 - e2 * np.sin(lat) ** 2)
        return np.stack([(n + h) * np.cos(lat) * np.cos(lon),
                         (n + h) * np.cos(lat) * np.sin(lon),
                         (n * (1.0 - e2) + h) * np.sin(lat)], axis=-1)

    p = ecef(llh[:, 0], llh[:, 1], llh[:, 2])
    o = ecef(np.array([origin[0]]), np.array([origin[1]]), np.array([origin[2]]))[0]
    lat0, lon0 = math.radians(origin[0]), math.radians(origin[1])
    sl, cl = math.sin(lat0), math.cos(lat0)
    so, co = math.sin(lon0), math.cos(lon0)
    rot = np.array([[-so, co, 0.0],
                    [-sl * co, -sl * so, cl],
                    [cl * co, cl * so, sl]])
    return (p - o) @ rot.T


def _enu_to_geodetic(enu: np.ndarray, origin: tuple[float, float, float]) -> np.ndarray:
    """:func:`_geodetic_to_enu` の逆(ENU [m] → [緯度 deg, 経度 deg, 高さ m])。合成データと検算に使う。

    ECEF から緯度は固定点反復(10 回で 1e-12 deg 未満に収束、数百 km 以内の点で)で戻す。
    """
    a, f = _GRS80_A, _GRS80_F
    e2 = f * (2.0 - f)
    lat0, lon0 = math.radians(origin[0]), math.radians(origin[1])
    sl, cl = math.sin(lat0), math.cos(lat0)
    so, co = math.sin(lon0), math.cos(lon0)
    rot = np.array([[-so, co, 0.0],
                    [-sl * co, -sl * so, cl],
                    [cl * co, cl * so, sl]])
    n0 = a / math.sqrt(1.0 - e2 * sl * sl)
    o = np.array([(n0 + origin[2]) * cl * co, (n0 + origin[2]) * cl * so, (n0 * (1.0 - e2) + origin[2]) * sl])
    p = np.asarray(enu, dtype=float) @ rot + o
    lon = np.arctan2(p[:, 1], p[:, 0])
    r = np.hypot(p[:, 0], p[:, 1])
    lat = np.arctan2(p[:, 2], r * (1.0 - e2))
    for _ in range(10):
        n = a / np.sqrt(1.0 - e2 * np.sin(lat) ** 2)
        h = r / np.cos(lat) - n
        lat = np.arctan2(p[:, 2], r * (1.0 - e2 * n / (n + h)))
    n = a / np.sqrt(1.0 - e2 * np.sin(lat) ** 2)
    h = r / np.cos(lat) - n
    return np.column_stack([np.degrees(lat), np.degrees(lon), h])


def _srs_is_6697(srs: str) -> bool:
    """srsName が EPSG:6697(JGD2011 地理 3 次元)を指すか。URI・URN・短縮形のどれでも受ける。"""
    s = srs.strip()
    return s.endswith("/6697") or s.endswith(":6697") or s.upper() == "EPSG:6697"


def _gml_id(elem: ET.Element) -> str | None:
    for key, val in elem.attrib.items():
        if _local_name(key) == "id":
            return val
    return None


def _check_lod2_geometry(root: ET.Element, where: str) -> None:
    """LOD2 幾何の部分木に未知の gml 要素や 6697 以外の srsName が無いことを確かめる(fail-closed)。"""
    for sub in root.iter():
        if sub is root:
            continue
        name = _local_name(sub.tag)
        if name not in _LOD2_GML_ALLOWED:
            raise ValueError(f"{where}: LOD2 の幾何に未対応の要素 <{name}> があります(読み方を決めていないので拒否)")
        for key, val in sub.attrib.items():
            k = _local_name(key)
            if k == "srsName" and not _srs_is_6697(val):
                raise ValueError(f"{where}: srsName={val!r} は未対応(EPSG:6697 のみ)")
            if k == "srsDimension" and val.strip() != "3":
                raise ValueError(f"{where}: srsDimension={val!r} は未対応(3 のみ)")


def _polygons_of(geom_root: ET.Element, where: str) -> tuple[list[tuple[str | None, np.ndarray, list[np.ndarray]]], list[str]]:
    """幾何の部分木から ``(polygon_id, exterior (k,3), [interior (k,3), ...])`` と xlink 参照の一覧を返す。"""
    _check_lod2_geometry(geom_root, where)
    polys: list[tuple[str | None, np.ndarray, list[np.ndarray]]] = []
    hrefs: list[str] = []
    for sub in geom_root.iter():
        name = _local_name(sub.tag)
        if name == "surfaceMember":
            for key, val in sub.attrib.items():
                if _local_name(key) == "href":
                    if not val.startswith("#"):
                        raise ValueError(f"{where}: 外部ファイルへの xlink:href={val!r} は未対応")
                    hrefs.append(val[1:])
        elif name == "Polygon":
            ext: np.ndarray | None = None
            holes: list[np.ndarray] = []
            for ch in sub:
                cname = _local_name(ch.tag)
                rings = [r for r in ch.iter() if _local_name(r.tag) == "posList"]
                if len(rings) != 1:
                    raise ValueError(f"{where}: Polygon の {cname} に posList が {len(rings)} 本あります(1 本のはず)")
                ring = _parse_poslist(rings[0].text, rings[0].get("srsDimension"))
                if cname == "exterior":
                    if ext is not None:
                        raise ValueError(f"{where}: Polygon に exterior が 2 つあります")
                    ext = ring
                elif cname == "interior":
                    holes.append(ring)
                else:
                    raise ValueError(f"{where}: Polygon の子 <{cname}> は未対応")
            if ext is None:
                raise ValueError(f"{where}: exterior の無い Polygon があります")
            polys.append((_gml_id(sub), ext, holes))
    return polys, hrefs


def _plane_basis(ring: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """3-D 多角形の Newell 法線と、それに直交する 2 軸 (u, v)、面積(Newell ノルム / 2)。

    (u, v, n) は右手系なので、(u, v) に射影した環は元の向き(n から見て反時計回り)を保つ。
    """
    c = ring.mean(axis=0)
    q = ring - c
    nxt = np.roll(q, -1, axis=0)
    n = np.array([np.sum((q[:, 1] - nxt[:, 1]) * (q[:, 2] + nxt[:, 2])),
                  np.sum((q[:, 2] - nxt[:, 2]) * (q[:, 0] + nxt[:, 0])),
                  np.sum((q[:, 0] - nxt[:, 0]) * (q[:, 1] + nxt[:, 1]))])
    norm = float(np.linalg.norm(n))
    if norm == 0.0:
        return n, n, n, 0.0
    n = n / norm
    helper = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    u = np.cross(helper, n)
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    return n, u, v, 0.5 * norm


def _segments_cross(p1: np.ndarray, p2: np.ndarray, q1: np.ndarray, q2: np.ndarray) -> bool:
    """線分 p1p2 と q1q2 が端点以外で交わるか(端点の共有は交差としない)。"""
    d1 = _cross2(q1, q2, p1)
    d2 = _cross2(q1, q2, p2)
    d3 = _cross2(p1, p2, q1)
    d4 = _cross2(p1, p2, q2)
    return (d1 * d2 < 0.0) and (d3 * d4 < 0.0)


def _bridge_holes(outer: np.ndarray, holes: list[np.ndarray]) -> tuple[np.ndarray, list[int]]:
    """穴を外周へ橋渡しして 1 本の(弱単純な)環にする。``(全頂点 (N,2), 環の添字列)``。

    穴は x 最大の頂点から始め、交差しない最も近い外周頂点へ往復の橋を架ける(古典的な Eberly の手順の
    簡略版)。外周は反時計回り、穴は時計回りに揃えてから繋ぐ。
    """
    pts = [outer if polygon_area(outer) > 0.0 else outer[::-1]]
    ring = list(range(pts[0].shape[0]))
    base = pts[0].shape[0]
    hole_sets = []
    for h in holes:
        hh = h if polygon_area(h) < 0.0 else h[::-1]
        hole_sets.append((base, hh))
        pts.append(hh)
        base += hh.shape[0]
    allp = np.vstack(pts)
    for start, hh in sorted(hole_sets, key=lambda t: -float(t[1][:, 0].max())):
        k = hh.shape[0]
        mi = int(np.argmax(hh[:, 0]))
        m = allp[start + mi]
        order = sorted(range(len(ring)), key=lambda i: float(np.sum((allp[ring[i]] - m) ** 2)))
        edges = [(allp[ring[i]], allp[ring[(i + 1) % len(ring)]]) for i in range(len(ring))]
        for s2, h2 in hole_sets:
            for j in range(h2.shape[0]):
                edges.append((allp[s2 + j], allp[s2 + (j + 1) % h2.shape[0]]))
        chosen = None
        for i in order:
            p = allp[ring[i]]
            if not any(_segments_cross(m, p, a, b) for a, b in edges):
                chosen = i
                break
        if chosen is None:
            raise ValueError("穴を外周へ繋ぐ橋が見つかりません(自己交差の疑い)")
        hole_loop = [start + (mi + t) % k for t in range(k)] + [start + mi]
        ring = ring[: chosen + 1] + hole_loop + ring[chosen:]
    return allp, ring


def _triangulate_3d(ext: np.ndarray, holes: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray, float]:
    """3-D の平面多角形(穴あり可)を三角形にする。``(頂点 (k,3), 三角形 (t,3), 非平面性 [m])``。

    三角形の向きは元の環の向き(CityGML では外向き法線)を保つ。入力は [緯度, 経度, 高さ] なので、まず環の
    重心まわりで子午線・卯酉線の曲率半径を掛けてメートルの局所直交座標に直してから平面を求める(度とメートルの
    混ざった空間で法線を取ると条件が悪く、非平面性も意味を持たない)。この写像は線形なので三角形の添字は
    最終の ENU でもそのまま有効。
    """
    a, f = _GRS80_A, _GRS80_F
    e2 = f * (2.0 - f)
    lat_c = math.radians(float(ext[:, 0].mean()))
    w = math.sqrt(1.0 - e2 * math.sin(lat_c) ** 2)
    k_lat = math.radians(1.0) * a * (1.0 - e2) / w ** 3       # 子午線曲率半径 M × 1 deg
    k_lon = math.radians(1.0) * a / w * math.cos(lat_c)        # 卯酉線曲率半径 N cos φ × 1 deg
    c0 = ext.mean(axis=0)
    scale = np.array([k_lat, k_lon, 1.0])
    ext0, holes0 = ext, list(holes)                            # 返す頂点は元の値そのもの(丸めない)
    ext = (ext - c0) * scale
    holes = [(h - c0) * scale for h in holes]
    allring = np.vstack([ext] + holes)
    n, u, v, area = _plane_basis(ext)
    if area <= 0.0:
        raise ValueError("面積 0 の Polygon")
    c = ext.mean(axis=0)
    nonplanar = float(np.max(np.abs((allring - c) @ n)))
    to2 = lambda r: np.column_stack([(r - c) @ u, (r - c) @ v])  # noqa: E731
    if holes:
        flat, ring = _bridge_holes(to2(ext), [to2(h) for h in holes])
        # _bridge_holes は外周を反時計回り・穴を時計回りに揃えて並べるので、元の頂点も同じ判定で並べ直す
        src = ext0 if polygon_area(to2(ext)) > 0.0 else ext0[::-1]
        V3 = np.vstack([src] + [h0 if polygon_area(to2(h)) < 0.0 else h0[::-1] for h, h0 in zip(holes, holes0)])
        tri = triangulate_polygon(flat[ring])
        T = np.asarray(ring, dtype=np.int64)[tri]
        return V3, T, nonplanar
    tri = triangulate_polygon(to2(ext))
    return ext0, tri, nonplanar


def _unit_record(elem: ET.Element, where: str, on_bad_polygon: str) -> dict[str, Any] | None:
    """Building 本体か BuildingPart 1 つ分(部位は再帰しない)の LOD2 面と属性を集める。"""
    attrs: dict[str, Any] = {}
    measured: float | None = None
    thematic: list[tuple[int, ET.Element]] = []
    direct: list[ET.Element] = []
    solid: ET.Element | None = None
    for ch in elem:
        name = _local_name(ch.tag)
        if name == "consistsOfBuildingPart":
            continue
        if name == "measuredHeight":
            uom = ch.get("uom")
            if uom is not None and uom.strip() not in ("m", "urn:adv:uom:m"):
                raise ValueError(f"{where}: measuredHeight の単位 {uom!r} は未対応(m のみ)")
            try:
                measured = float((ch.text or "").strip())
            except ValueError as exc:
                raise ValueError(f"{where}: measuredHeight が数値ではありません: {ch.text!r}") from exc
            if not math.isfinite(measured):
                raise ValueError(f"{where}: measuredHeight が非有限値です")
        elif name in _LOD2_SIMPLE_ATTRS and (ch.text or "").strip():
            attrs[name] = ch.text.strip()
        elif name in ("stringAttribute", "intAttribute", "doubleAttribute"):
            key = ch.get("name")
            val = next((g.text for g in ch if _local_name(g.tag) == "value"), None)
            if key and val is not None:
                attrs[key] = val.strip()
        elif name == "boundedBy":
            for surf in ch:
                kind = _LOD2_SURFACE_KIND.get(_local_name(surf.tag))
                if kind is None:
                    raise ValueError(f"{where}: 未対応の主題面 <{_local_name(surf.tag)}>(読み方を決めていないので拒否)")
                for g in surf:
                    if _local_name(g.tag) == "lod2MultiSurface":
                        thematic.append((kind, g))
        elif name == "lod2MultiSurface":
            direct.append(ch)
        elif name == "lod2Solid":
            solid = ch

    polys: list[tuple[int, str | None, np.ndarray, list[np.ndarray]]] = []
    for kind, g in thematic:
        got, _ = _polygons_of(g, where)
        polys += [(kind, pid, e, h) for pid, e, h in got]
    for g in direct:
        got, _ = _polygons_of(g, where)
        polys += [(3, pid, e, h) for pid, e, h in got]
    if solid is not None:
        got, hrefs = _polygons_of(solid, where)
        if got and polys:
            raise ValueError(f"{where}: lod2Solid の中の面と主題面の両方があり、重複の扱いを決めていないので拒否")
        polys += [(3, pid, e, h) for pid, e, h in got]
        known = {pid for _k, pid, _e, _h in polys if pid}
        missing = [h for h in hrefs if h not in known]
        if missing:
            raise ValueError(f"{where}: lod2Solid が参照する面 {len(missing)} 枚が見つかりません(例 {missing[0]})")
    if not polys:
        return None

    verts: list[np.ndarray] = []
    tris: list[np.ndarray] = []
    kinds: list[np.ndarray] = []
    offset = 0
    n_bad = 0
    nonplanar = 0.0
    for kind, pid, ext, holes in polys:
        try:
            V3, T, npl = _triangulate_3d(ext, holes)
        except ValueError as exc:
            if on_bad_polygon == "raise":
                raise ValueError(f"{where}: Polygon {pid} を三角形にできません: {exc}") from exc
            n_bad += 1
            continue
        nonplanar = max(nonplanar, npl)
        verts.append(V3)
        tris.append(T + offset)
        kinds.append(np.full(T.shape[0], kind, dtype=np.int8))
        offset += V3.shape[0]
    if not verts:
        return None
    llh = np.vstack(verts)
    T = np.vstack(tris)
    # 同じ点(緯度・経度・高さが完全一致)を 1 頂点にまとめる。丸めはしない(可逆)。
    uniq, inv = np.unique(llh, axis=0, return_inverse=True)
    return {
        "gml_id": _gml_id(elem),
        "measured_height": measured,
        "attrs": attrs,
        "llh": uniq,
        "F": inv.reshape(-1)[T],
        "kind": np.concatenate(kinds),
        "n_polygons": len(polys),
        "n_bad_polygons": n_bad,
        "max_nonplanarity_m": nonplanar,
    }


def plateau_lod2_mesh(
    source: str | Path | bytes,
    *,
    origin: tuple[float, float, float] | None = None,
    ids: Iterable[str] | None = None,
    bbox_latlon: tuple[float, float, float, float] | None = None,
    on_bad_polygon: str = "raise",
) -> dict[str, Any]:
    """PLATEAU の CityGML から LOD2 の建物を読み、局所メートル座標の三角形メッシュ (V, F) と建物ごとの属性を返す。

    ``bldg:Building`` を ``iterparse`` でストリーム読みし、本体と ``bldg:BuildingPart`` を 1 つずつ **部位**
    (unit)として扱う。面は主題面(``GroundSurface`` / ``WallSurface`` / ``RoofSurface`` / ``OuterCeilingSurface``
    / ``OuterFloorSurface`` / ``ClosureSurface``)の ``lod2MultiSurface`` から取り、面種を ``face_kind`` に残す。
    ``lod2Solid`` が ``xlink:href`` で参照する面はすべて見つかることを確かめる。穴(``gml:interior``)は外周へ
    橋を架けて耳切りで三角形にし、三角形の向きは元の環の向き(外向き法線)を保つ。

    座標は EPSG:6697(JGD2011 の緯度・経度・標高)を GRS80 の地心直交座標経由で原点の接平面の
    ENU(x 東, y 北, z 上, メートル)へ厳密に移す。既定の原点は **地面の重心**: ``GroundSurface`` の頂点の
    緯度経度の平均と、その最低標高(地面が無ければ全頂点)。

    **fail-closed**: 6697 以外の ``srsName``、``srsDimension`` が 3 以外、LOD2 の幾何に未知の gml 要素
    (``Triangle``・``OrientableSurface``・``pos`` の点列など)、表に無い主題面、見つからない xlink、
    m 以外の ``measuredHeight`` の単位は、読み飛ばさず ``ValueError`` にする。

    Args:
        source: CityGML の文字列(``<`` で始まる)、bytes、またはファイルパス(str/Path)。
        origin: 局所座標の原点 ``(lat0 [deg], lon0 [deg], h0 [m])``。None なら地面の重心。
        ids: 読む建物の ``gml:id``(``bldg:Building`` の id)。None なら全部。
        bbox_latlon: ``(lat_min, lon_min, lat_max, lon_max)``。部位の頂点の平均がこの箱に入る部位だけ残す。
        on_bad_polygon: 三角形にできない Polygon(面積 0・自己交差)の扱い。``"raise"``(既定)か
            ``"skip"``(数えて ``n_bad_polygons`` に残す)。

    Returns:
        ``{"V": (n,3) float64 [m], "F": (m,3) int64, "face_unit": (m,) int64, "face_kind": (m,) int8,
        "kinds": LOD2_KINDS, "units": [...], "origin": (lat0, lon0, h0), "crs": str,
        "n_buildings": int, "n_no_lod2": int, "n_bad_polygons": int, "max_nonplanarity_m": float}``。
        ``units[i]`` は ``{"building_id", "part", "gml_id", "measured_height", "attrs", "z_min", "z_max",
        "ground_z", "height_mesh", "extent_xy", "lat", "lon", "n_faces"}``。``height_mesh`` は
        ``z_max − ground_z``(``measuredHeight`` と比べる値)、``extent_xy`` は ENU の (x 幅, y 幅) [m]。

    Raises:
        ValueError: 上の fail-closed の条件、source が空・不正、XML が壊れている、該当する部位が 0 件、
            ``on_bad_polygon`` が未知、``origin`` / ``bbox_latlon`` が不正。

    Examples:
        >>> import driveplateau as PL
        >>> m = PL.plateau_lod2_mesh(PL._citygml_lod2_example())
        >>> [round(u["height_mesh"], 3) for u in m["units"]]
        [12.0, 4.0]
        >>> m["V"].shape[1], m["F"].shape[1], sorted(set(m["face_kind"].tolist()))
        (3, 3, [0, 1, 2])
    """
    if on_bad_polygon not in ("raise", "skip"):
        raise ValueError(f"on_bad_polygon は 'raise' か 'skip': {on_bad_polygon!r}")
    want = None if ids is None else {str(i) for i in ids}
    if want is not None and not want:
        raise ValueError("ids が空です(None なら全部)")
    if bbox_latlon is not None:
        try:
            la0, lo0, la1, lo1 = (float(t) for t in bbox_latlon)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"bbox_latlon は (lat_min, lon_min, lat_max, lon_max): {bbox_latlon!r}") from exc
        if not (la0 <= la1 and lo0 <= lo1) or not all(math.isfinite(t) for t in (la0, lo0, la1, lo1)):
            raise ValueError(f"bbox_latlon が反転しているか非有限です: {bbox_latlon!r}")
    if origin is not None:
        try:
            o_lat, o_lon, o_h = (float(t) for t in origin)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"origin は (lat0, lon0, h0): {origin!r}") from exc
        if not all(math.isfinite(t) for t in (o_lat, o_lon, o_h)) or abs(o_lat) >= 90.0:
            raise ValueError(f"origin が不正です: {origin!r}")

    stream = _open_source(source)
    units: list[dict[str, Any]] = []
    n_buildings = 0
    n_no_lod2 = 0
    srs_seen: str | None = None
    try:
        try:
            for _event, elem in ET.iterparse(stream, events=("end",)):
                name = _local_name(elem.tag)
                if name == "Envelope" and srs_seen is None:
                    srs = elem.get("srsName")
                    if srs is not None:
                        if not _srs_is_6697(srs):
                            raise ValueError(f"srsName={srs!r} は未対応(EPSG:6697 のみ)")
                        srs_seen = srs
                elif name == "Building":
                    try:
                        bid = _gml_id(elem)
                        if want is not None and bid not in want:
                            continue
                        n_buildings += 1
                        if srs_seen is None:
                            srs = next((s.get("srsName") for s in elem.iter() if s.get("srsName")), None)
                            if srs is None:
                                raise ValueError("座標参照系(srsName)が見つかりません(fail-closed)")
                            if not _srs_is_6697(srs):
                                raise ValueError(f"srsName={srs!r} は未対応(EPSG:6697 のみ)")
                            srs_seen = srs
                        bodies = [(0, elem)] + [
                            (k + 1, p) for k, p in enumerate(
                                q for c in elem if _local_name(c.tag) == "consistsOfBuildingPart"
                                for q in c if _local_name(q.tag) == "BuildingPart")
                        ]
                        got_any = False
                        for part, body in bodies:
                            rec = _unit_record(body, f"Building {bid} part {part}", on_bad_polygon)
                            if rec is None:
                                continue
                            got_any = True
                            rec["building_id"] = bid
                            rec["part"] = part
                            units.append(rec)
                        if not got_any:
                            n_no_lod2 += 1
                    finally:
                        elem.clear()
                elif name == "cityObjectMember":
                    elem.clear()
        except ET.ParseError as exc:
            raise ValueError(f"CityGML の XML 解析に失敗: {exc}") from exc
    finally:
        stream.close()

    if bbox_latlon is not None:
        units = [u for u in units
                 if la0 <= float(u["llh"][:, 0].mean()) <= la1 and lo0 <= float(u["llh"][:, 1].mean()) <= lo1]
    if not units:
        raise ValueError("LOD2 の面を持つ部位が 1 つもありません(ids / bbox_latlon / ファイルを確かめてください)")

    if origin is None:
        ground = [u["llh"][np.unique(u["F"][u["kind"] == 0])] for u in units if np.any(u["kind"] == 0)]
        pool = np.vstack(ground) if ground else np.vstack([u["llh"] for u in units])
        o_lat, o_lon, o_h = float(pool[:, 0].mean()), float(pool[:, 1].mean()), float(pool[:, 2].min())
    org = (o_lat, o_lon, o_h)

    Vs: list[np.ndarray] = []
    Fs: list[np.ndarray] = []
    Us: list[np.ndarray] = []
    Ks: list[np.ndarray] = []
    out_units: list[dict[str, Any]] = []
    offset = 0
    for i, u in enumerate(units):
        V = _geodetic_to_enu(u["llh"], org)
        gidx = np.unique(u["F"][u["kind"] == 0])
        ground_z = float(V[gidx, 2].min()) if gidx.size else float(V[:, 2].min())
        z_max = float(V[:, 2].max())
        out_units.append({
            "building_id": u["building_id"],
            "part": u["part"],
            "gml_id": u["gml_id"],
            "measured_height": u["measured_height"],
            "attrs": u["attrs"],
            "z_min": float(V[:, 2].min()),
            "z_max": z_max,
            "ground_z": ground_z,
            "height_mesh": z_max - ground_z,
            "extent_xy": (float(np.ptp(V[:, 0])), float(np.ptp(V[:, 1]))),
            "lat": float(u["llh"][:, 0].mean()),
            "lon": float(u["llh"][:, 1].mean()),
            "n_faces": int(u["F"].shape[0]),
        })
        Vs.append(V)
        Fs.append(u["F"] + offset)
        Us.append(np.full(u["F"].shape[0], i, dtype=np.int64))
        Ks.append(u["kind"])
        offset += V.shape[0]
    return {
        "V": np.vstack(Vs),
        "F": np.vstack(Fs).astype(np.int64),
        "face_unit": np.concatenate(Us),
        "face_kind": np.concatenate(Ks).astype(np.int8),
        "kinds": LOD2_KINDS,
        "units": out_units,
        "origin": org,
        "crs": "EPSG:6697 (lat, lon, alt) -> local ENU [m] (GRS80, exact)",
        "n_buildings": n_buildings,
        "n_no_lod2": n_no_lod2,
        "n_bad_polygons": int(sum(u["n_bad_polygons"] for u in units)),
        "max_nonplanarity_m": float(max(u["max_nonplanarity_m"] for u in units)),
    }


def _citygml_lod2_example(
    *,
    origin: tuple[float, float] = (35.4575, 139.6375),
    ground_z: float = 3.0,
    with_hole: bool = True,
) -> str:
    """LOD2 の最小 CityGML(テスト・作例・説明のコード例用)。

    座標は原点 ``(origin, ground_z)`` の接平面 ENU で書いた点を楕円体の厳密な逆変換で緯度経度へ戻して置く。
    建物 1 棟 = 本体(20 m × 10 m、軒 8 m・棟 12 m の切妻、x 方向の棟)+ BuildingPart(6 m × 6 m × 4 m の
    箱、本体の東に接する)。面は主題面(地面・壁・屋根)の ``lod2MultiSurface`` に書き、本体の
    ``lod2Solid`` は ``xlink:href`` で参照する(PLATEAU と同じ形)。``with_hole`` なら部位の屋根に
    2 m 角の穴(``gml:interior``)を開け、穴の中は面を持たない(穴の扱いの試験用)。

    閉形式: 本体の体積 = 20·10·8 + 20·(10·4/2) = 2000 m³、部位の体積 = 144 m³(穴が無いとき)。
    """
    lat0, lon0 = _check_origin(origin)

    def ll(x: float, y: float, z: float) -> tuple[float, float, float]:
        # 読み手と同じ厳密な楕円体の逆変換で置く(閉形式の寸法が読み戻しで 1e-6 m 以内に戻る)
        la, lo, h = _enu_to_geodetic(np.array([[x, y, z]]), (lat0, lon0, ground_z))[0]
        return (float(la), float(lo), float(h))

    def poly(pid: str, ring: list[tuple[float, float, float]], holes: Sequence[list[tuple[float, float, float]]] = ()) -> str:
        inner = "".join(
            f"<gml:interior><gml:LinearRing><gml:posList>{_ring_text(h)}</gml:posList></gml:LinearRing></gml:interior>"
            for h in holes)
        return (f"<gml:surfaceMember><gml:Polygon gml:id=\"{pid}\"><gml:exterior><gml:LinearRing>"
                f"<gml:posList>{_ring_text(ring)}</gml:posList></gml:LinearRing></gml:exterior>{inner}"
                "</gml:Polygon></gml:surfaceMember>")

    def surf(kind: str, members: list[str]) -> str:
        return (f"<bldg:boundedBy><bldg:{kind}><bldg:lod2MultiSurface><gml:MultiSurface>{''.join(members)}"
                f"</gml:MultiSurface></bldg:lod2MultiSurface></bldg:{kind}></bldg:boundedBy>")

    # 本体: 足元 (0,0)-(20,10)、軒 8、棟 12(y=5)。外向き法線になる向きで環を書く。
    a = [ll(0, 0, 0), ll(20, 0, 0), ll(20, 10, 0), ll(0, 10, 0)]
    e = [ll(0, 0, 8), ll(20, 0, 8), ll(20, 10, 8), ll(0, 10, 8)]
    r0, r1 = ll(0, 5, 12), ll(20, 5, 12)
    body_polys = {
        "GroundSurface": [poly("b_g", a[::-1])],
        "WallSurface": [poly("b_w0", [a[0], a[1], e[1], e[0]]),
                        poly("b_w1", [a[1], a[2], e[2], r1, e[1]]),
                        poly("b_w2", [a[2], a[3], e[3], e[2]]),
                        poly("b_w3", [a[3], a[0], e[0], r0, e[3]])],
        "RoofSurface": [poly("b_r0", [e[0], e[1], r1, r0]), poly("b_r1", [e[2], e[3], r0, r1])],
    }
    ids = [pid for k in body_polys for m in body_polys[k] for pid in [m.split('gml:id="')[1].split('"')[0]]]
    solid = ("<bldg:lod2Solid><gml:Solid><gml:exterior><gml:CompositeSurface>"
             + "".join(f"<gml:surfaceMember xlink:href=\"#{i}\"/>" for i in ids)
             + "</gml:CompositeSurface></gml:exterior></gml:Solid></bldg:lod2Solid>")
    body = ("<bldg:measuredHeight uom=\"m\">12.0</bldg:measuredHeight>" + solid
            + "".join(surf(k, v) for k, v in body_polys.items()))

    # 部位: 足元 (20,2)-(26,8)、高さ 4。屋根に (22,4)-(24,6) の穴(穴の環は外周と逆向き)。
    b = [ll(20, 2, 0), ll(26, 2, 0), ll(26, 8, 0), ll(20, 8, 0)]
    t = [ll(20, 2, 4), ll(26, 2, 4), ll(26, 8, 4), ll(20, 8, 4)]
    hole = [ll(22, 4, 4), ll(22, 6, 4), ll(24, 6, 4), ll(24, 4, 4)] if with_hole else None
    part_polys = {
        "GroundSurface": [poly("p_g", b[::-1])],
        "WallSurface": [poly(f"p_w{k}", [b[k], b[(k + 1) % 4], t[(k + 1) % 4], t[k]]) for k in range(4)],
        "RoofSurface": [poly("p_r", t, [hole] if hole else [])],
    }
    part = ("<bldg:measuredHeight uom=\"m\">4.0</bldg:measuredHeight>"
            + "".join(surf(k, v) for k, v in part_polys.items()))
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        f"<core:CityModel xmlns:core=\"{_NS_CORE}\" xmlns:bldg=\"{_NS_BLDG}\" xmlns:gml=\"{_NS_GML}\""
        f" xmlns:gen=\"{_NS_GEN}\" xmlns:xlink=\"http://www.w3.org/1999/xlink\">"
        "<gml:boundedBy><gml:Envelope srsName=\"http://www.opengis.net/def/crs/EPSG/0/6697\" srsDimension=\"3\">"
        f"<gml:lowerCorner>{_fmt(lat0)} {_fmt(lon0)} {_fmt(ground_z)}</gml:lowerCorner>"
        f"<gml:upperCorner>{_fmt(lat0 + 0.001)} {_fmt(lon0 + 0.001)} {_fmt(ground_z + 12)}</gml:upperCorner>"
        "</gml:Envelope></gml:boundedBy>"
        "<core:cityObjectMember><bldg:Building gml:id=\"lod2_example_0001\">"
        "<gen:stringAttribute name=\"note\"><gen:value>synthetic</gen:value></gen:stringAttribute>"
        f"{body}<bldg:consistsOfBuildingPart><bldg:BuildingPart gml:id=\"lod2_example_0001_p1\">{part}"
        "</bldg:BuildingPart></bldg:consistsOfBuildingPart></bldg:Building></core:cityObjectMember>"
        "</core:CityModel>\n"
    )
