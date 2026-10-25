# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ViEW2026 の会場(横浜・みなとみらい)の建物を PLATEAU の CityGML LOD2 から小さな npz にする。

    py -3.11 -I tools/gen_plateau_venue.py <CityGML の置き場> [--out data/plateau_yokohama]

原本(国土交通省 Project PLATEAU、横浜市 2020 年度、``udx/bldg/5339154[01]_bldg_6697_op.gml`` と
``53391550_bldg_6697_op.gml``)は repo の外に置き、**信頼しないデータ**として ``-I`` で読む。
出典・ライセンス・改変の内容は ``data/plateau_yokohama/README.md``。

門(どれか 1 つでも外れたら npz を書かずに exit 1):

1. **measuredHeight との一致**: メッシュの高さ(屋根の最高点 − 地面の最低点、``plateau_lod2_mesh`` の
   ``height_mesh``)が CityGML の ``bldg:measuredHeight`` と ±0.05 m で一致する(measuredHeight は 0.1 m 単位
   の値なので、丸めの幅の半分)。
2. **生の座標からの独立な箱**: XML を木にせず、原本のバイト列から正規表現で部位ごとの ``lod2MultiSurface`` の
   ``posList`` を拾い、**別の式**(重心の緯度での子午線・卯酉線の曲率半径を掛ける等距円筒)で東西・南北の幅と
   高さの幅を出す。メッシュ(GRS80 の地心直交座標経由の厳密な ENU)の幅と ±0.05 m で一致する。
   2 つの式の差は接平面の傾き(原点から 300 m で約 3e-5 rad)と地球の丸み(d²/2R、300 m で 7 mm)だけ。
3. ``measuredHeight`` の値そのものも正規表現で拾い直し、``plateau_lod2_mesh`` が読んだ値と完全一致する。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import driveplateau as PL  # noqa: E402

#: 会場の建物。座標で同定し、公開地図の施設名の位置と照合した(2026-10-25: 4 棟は外接箱の中心が 3 m 以内、
#: ホテル棟と会議センターは両方の位置が 1 つの部位の中に入る)。
#: label は場所の説明だけ(運営会社・ホテルの銘柄の名前は書かない)。
VENUE = [
    # (タイル, Building の gml:id, 部位, 日本語の名前, 英語の名前)
    ("53391540_bldg_6697_op.gml", "BLD_c093e09a-37ea-4a19-ba14-cf690d6b622e", 1,
     "ホテル棟と会議センター(PLATEAU では 1 つの部位)", "Hotel tower and conference center (one PLATEAU part)"),
    ("53391540_bldg_6697_op.gml", "BLD_c093e09a-37ea-4a19-ba14-cf690d6b622e", 2,
     "ホテル棟の付属部(低層)", "Hotel annex (low-rise part)"),
    ("53391550_bldg_6697_op.gml", "BLD_b2c1da89-8244-4428-b26f-4cbc561b3861", 0,
     "国立大ホール", "National Convention Hall"),
    ("53391550_bldg_6697_op.gml", "BLD_a81d155c-e0ee-4866-882b-432c17f2bafd", 1,
     "展示ホール", "Exhibition hall"),
    ("53391550_bldg_6697_op.gml", "BLD_a81d155c-e0ee-4866-882b-432c17f2bafd", 2,
     "展示ホールの付属部(低層)", "Exhibition hall annex (low-rise part)"),
    ("53391550_bldg_6697_op.gml", "BLD_edc79b33-05de-4bd0-99b2-3e5e9a3a4e56", 0,
     "アネックスホール", "Annex hall"),
    ("53391550_bldg_6697_op.gml", "BLD_a942a524-0881-46d8-bdaf-2aa10b2a7555", 0,
     "ノース(2020 年開業の多目的施設)", "North building (multi-purpose, opened 2020)"),
]

TOL_HEIGHT_M = 0.05
TOL_EXTENT_M = 0.05

_GRS80_A = 6378137.0
_GRS80_F = 1.0 / 298.257222101


def _raw_units(raw: bytes, bid: str) -> dict:
    """原本のバイト列から 1 棟を切り出し、部位ごとの LOD2 の点列 (k,3) と measuredHeight を返す(XML を木にしない)。"""
    m = re.search(rb'<bldg:Building gml:id="' + re.escape(bid.encode()) + rb'">', raw)
    if m is None:
        raise SystemExit("原本に %s がありません" % bid)
    end = raw.find(b"</bldg:Building>", m.end())
    if end < 0:
        raise SystemExit("%s の閉じタグがありません" % bid)
    body = raw[m.end():end]
    starts = [p.start() for p in re.finditer(rb"<bldg:BuildingPart[ >]", body)]
    chunks = {}
    if starts:
        own = body[:starts[0]]
        chunks[0] = own
        for k, s in enumerate(starts):
            e = body.find(b"</bldg:BuildingPart>", s)
            chunks[k + 1] = body[s:e]
    else:
        chunks[0] = body
    out = {}
    for part, ch in chunks.items():
        pts = []
        for blk in re.findall(rb"<bldg:lod2MultiSurface>(.*?)</bldg:lod2MultiSurface>", ch, re.S):
            for pl in re.findall(rb"<gml:posList>([^<]*)</gml:posList>", blk):
                v = np.array(pl.split(), dtype=float)
                pts.append(v.reshape(-1, 3))
        if not pts:
            continue
        # 部位の直下の measuredHeight(子の部位のものは含まない —— 部位 0 は最初の部位より前だけを見ている)
        mh = re.search(rb"<bldg:measuredHeight[^>]*>([^<]*)</bldg:measuredHeight>", ch)
        out[part] = (np.vstack(pts), float(mh.group(1)) if mh else None)
    return out


def _raw_extent(llh: np.ndarray) -> tuple[float, float, float]:
    """等距円筒(重心の緯度の曲率半径 M, N)での東西・南北の幅と高さの幅 [m]。ENU とは別の式。"""
    e2 = _GRS80_F * (2.0 - _GRS80_F)
    lat_c = math.radians(float(llh[:, 0].mean()))
    w = math.sqrt(1.0 - e2 * math.sin(lat_c) ** 2)
    m_rad = _GRS80_A * (1.0 - e2) / w ** 3
    n_rad = _GRS80_A / w
    ns = math.radians(float(np.ptp(llh[:, 0]))) * m_rad
    ew = math.radians(float(np.ptp(llh[:, 1]))) * n_rad * math.cos(lat_c)
    return ew, ns, float(np.ptp(llh[:, 2]))


def _hull(P: np.ndarray) -> np.ndarray:
    """2-D 凸包(Andrew の単調鎖、反時計回り)。"""
    P = np.unique(P, axis=0)
    P = P[np.lexsort((P[:, 1], P[:, 0]))]

    def half(pts):
        h = []
        for p in pts:
            while len(h) >= 2 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1])
                                   - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(P), half(P[::-1])
    return np.array(lo[:-1] + up[:-1])


def _min_rect(P: np.ndarray) -> tuple[float, float, float]:
    """最小面積の外接長方形(凸包の辺の向きを全部試す)。``(長辺, 短辺, 長辺の向き [deg, 東から反時計回り])``。"""
    H = _hull(P)
    best = None
    for i in range(len(H)):
        d = H[(i + 1) % len(H)] - H[i]
        n = float(np.hypot(*d))
        if n == 0.0:
            continue
        u = d / n
        v = np.array([-u[1], u[0]])
        a, b = H @ u, H @ v
        w, h = float(np.ptp(a)), float(np.ptp(b))
        if best is None or w * h < best[0]:
            ang = math.degrees(math.atan2(u[1], u[0])) if w >= h else math.degrees(math.atan2(v[1], v[0]))
            best = (w * h, max(w, h), min(w, h), (ang + 180.0) % 180.0)
    return best[1], best[2], best[3]


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build(src: Path, out_dir: Path) -> int:
    files = sorted({t for t, *_ in VENUE})
    per_file = {}
    for f in files:
        ids = sorted({b for t, b, *_ in VENUE if t == f})
        per_file[f] = ids
    # 1 回目: 仮の原点で読み、地面の三角形の面積重心(ENU)を求めて、それを原点にもう 1 回読む。
    first = PL.plateau_lod2_mesh(src / files[0], ids=per_file[files[0]])
    o1 = first["origin"]
    acc_a, acc_c = 0.0, np.zeros(3)
    for f in files:
        m = PL.plateau_lod2_mesh(src / f, ids=per_file[f], origin=o1)
        keep = {(b, p) for t, b, p, *_ in VENUE if t == f}
        V, F = m["V"], m["F"]
        sel_unit = np.array([(u["building_id"], u["part"]) in keep for u in m["units"]])
        g = F[(m["face_kind"] == 0) & sel_unit[m["face_unit"]]]
        a = 0.5 * np.linalg.norm(np.cross(V[g[:, 1]] - V[g[:, 0]], V[g[:, 2]] - V[g[:, 0]]), axis=1)
        acc_a += float(a.sum())
        acc_c += (a[:, None] * V[g].mean(axis=1)).sum(axis=0)
    centroid = acc_c / acc_a
    org = tuple(float(t) for t in PL._enu_to_geodetic(centroid[None, :], o1)[0])

    Vs, Fs, Us, Ks, rows = [], [], [], [], []
    offset = 0
    ok = True
    for f in files:
        raw = (src / f).read_bytes()
        m = PL.plateau_lod2_mesh(src / f, ids=per_file[f], origin=org)
        by = {(u["building_id"], u["part"]): (i, u) for i, u in enumerate(m["units"])}
        rawcache = {}
        for t, bid, part, ja, en in VENUE:
            if t != f:
                continue
            i, u = by[(bid, part)]
            sel = m["face_unit"] == i
            Fi = m["F"][sel]
            used = np.unique(Fi)
            Vi = m["V"][used]
            remap = np.full(m["V"].shape[0], -1, dtype=np.int64)
            remap[used] = np.arange(used.size) + offset
            if bid not in rawcache:
                rawcache[bid] = _raw_units(raw, bid)
            rpts, rmh = rawcache[bid][part]
            ew, ns, dz = _raw_extent(rpts)
            ex, ey = u["extent_xy"]
            dz_mesh = u["z_max"] - u["z_min"]
            g1 = u["measured_height"] is not None and abs(u["height_mesh"] - u["measured_height"]) <= TOL_HEIGHT_M
            g2 = abs(ex - ew) <= TOL_EXTENT_M and abs(ey - ns) <= TOL_EXTENT_M and abs(dz_mesh - dz) <= TOL_EXTENT_M
            g3 = rmh == u["measured_height"]
            L, W, ang = _min_rect(Vi[:, :2])
            row = dict(label_ja=ja, label_en=en, building_id=bid, part=part, tile=f[:8],
                       measured_height=u["measured_height"], height_mesh=u["height_mesh"],
                       ground_z=u["ground_z"], z_max=u["z_max"], extent_ew=ex, extent_ns=ey,
                       raw_extent_ew=ew, raw_extent_ns=ns, raw_dz=dz, mesh_dz=dz_mesh,
                       rect_long=L, rect_short=W, rect_angle_deg=ang, n_faces=int(Fi.shape[0]),
                       lat=u["lat"], lon=u["lon"], attrs=u["attrs"], gates=[bool(g1), bool(g2), bool(g3)])
            rows.append(row)
            ok &= g1 and g2 and g3
            print("%-44s mh %6.1f mesh %8.3f (Δ %+.3f) | EW %7.2f raw %7.2f | NS %7.2f raw %7.2f | dz Δ %+.4f | "
                  "rect %6.1f×%5.1f m @%5.1f° | faces %5d | %s" % (
                      en[:44], u["measured_height"], u["height_mesh"], u["height_mesh"] - u["measured_height"],
                      ex, ew, ey, ns, dz_mesh - dz, L, W, ang, Fi.shape[0],
                      "ok" if (g1 and g2 and g3) else "NG"))
            Vs.append(Vi)
            Fs.append(remap[Fi])
            Us.append(np.full(Fi.shape[0], len(rows) - 1, dtype=np.int16))
            Ks.append(m["face_kind"][sel])
            offset += used.size
    print("max |height_mesh - measuredHeight| = %.4f m (tol %.2f) / max |extent - raw| = %.4f m (tol %.2f)" % (
        max(abs(r["height_mesh"] - r["measured_height"]) for r in rows), TOL_HEIGHT_M,
        max(max(abs(r["extent_ew"] - r["raw_extent_ew"]), abs(r["extent_ns"] - r["raw_extent_ns"]),
                abs(r["mesh_dz"] - r["raw_dz"])) for r in rows), TOL_EXTENT_M))
    if not ok:
        print("FAILED: 門が外れたので npz を書かない")
        return 1
    V = np.vstack(Vs)
    F = np.vstack(Fs)
    assert F.max() < V.shape[0] and F.min() >= 0
    out_dir.mkdir(parents=True, exist_ok=True)
    npz = out_dir / "venue_lod2.npz"
    src_meta = [{"file": f, "sha256": _sha256(src / f)} for f in files]
    np.savez_compressed(
        npz,
        V=V.astype(np.float64), F=F.astype(np.int32), face_unit=np.concatenate(Us), face_kind=np.concatenate(Ks),
        kinds=np.array(PL.LOD2_KINDS),
        origin_llh=np.array(org, dtype=np.float64),
        unit_label_ja=np.array([r["label_ja"] for r in rows]),
        unit_label_en=np.array([r["label_en"] for r in rows]),
        unit_building_id=np.array([r["building_id"] for r in rows]),
        unit_part=np.array([r["part"] for r in rows], dtype=np.int16),
        unit_measured_height=np.array([r["measured_height"] for r in rows], dtype=np.float64),
        unit_height_mesh=np.array([r["height_mesh"] for r in rows], dtype=np.float64),
        unit_ground_z=np.array([r["ground_z"] for r in rows], dtype=np.float64),
        unit_rect=np.array([[r["rect_long"], r["rect_short"], r["rect_angle_deg"]] for r in rows], dtype=np.float64),
        meta_json=np.array(json.dumps({
            "crs": "local ENU [m] (x east, y north, z up), origin = area-weighted centroid of the GroundSurface "
                   "triangles; from EPSG:6697 via GRS80 ECEF (exact)",
            "source": "MLIT Project PLATEAU, Yokohama City 2020 (CityGML 2.0 LOD2, bldg)",
            "licence": "PLATEAU site policy section 3: Public Data License 1.0 (PDL1.0), compatible with CC BY 4.0",
            "files": src_meta,
            "units": [{k: v for k, v in r.items()} for r in rows],
        }, ensure_ascii=False)),
    )
    print("wrote %s (%d bytes, V %d, F %d)" % (npz.relative_to(ROOT) if npz.is_relative_to(ROOT) else npz,
                                               npz.stat().st_size, V.shape[0], F.shape[0]))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", help="原本の CityGML の置き場(repo の外)")
    ap.add_argument("--out", default=str(ROOT / "data" / "plateau_yokohama"))
    a = ap.parse_args(argv)
    return build(Path(a.src), Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
