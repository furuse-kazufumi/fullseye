# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_plateau_venue_lod2 — 会場の建物(PLATEAU の LOD2)と小惑星イトカワを同じ物差しで並べる

    py -3.11 examples/poc_plateau_venue_lod2.py                 # 検査と比較の表だけ
    py -3.11 examples/poc_plateau_venue_lod2.py --html out/venue_itokawa.html   # 触って見るビューアも書く

【平たく言うと】
「イトカワは長さ約 535 m」と聞いても大きさは実感しにくい。そこで、ViEW2026 の会場(横浜・みなとみらい)の
建物を国土交通省の 3D 都市モデル(Project PLATEAU、CityGML LOD2)から読み、同じメートルの座標でイトカワの
点群と並べる。建物は ``driveplateau.plateau_lod2_mesh`` で三角形メッシュにした小さな npz
(``data/plateau_yokohama/venue_lod2.npz``、出典・ライセンス・加工の内容は同じ場所の README)。

【何を期待し、何と比べるか】
  * plateau_lod2_mesh(合成)  : 切妻屋根の建物(本体 20 × 10 m・軒 8 m・棟 12 m + 6 m 角の部位)を読み、
                                 高さ 12 / 4 m・体積 2000 / 144 m³(発散定理)・屋根の面積 2·20·√41 + 36 − 4 m²
                                 (穴の分を引く)が閉形式どおり。座標参照系が違うファイルは拒む(fail-closed)。
  * 会場の npz                 : 7 部位それぞれ、メッシュの高さ(屋根の最高点 − 地面の最低点)が CityGML の
                                 measuredHeight と ±0.05 m(0.1 m 単位の値の丸めの半分)で一致、面は外向き(体積 > 0)。
  * イトカワとの比較           : 文献値の長さ 535 m(Fujiwara et al., Science 312, 2006)を「展示ホールの長辺の
                                 何倍」「ホテル棟の高さの何本分」に言い換える。点群(Gaskell の形状モデルから間引いた
                                 3000 点、studio_assets/sample_3d)は細長さ(長 > 中 > 短)だけを門にする —— 主軸方向の
                                 外接幅は 562 × 298 × 244 m で文献値より 1〜17 % 大きく、取り方の違いなので門にしない。

EXTEND: 別の会場・別の建物は、PLATEAU の該当タイルの CityGML を ``plateau_lod2_mesh(path, ids=[...])``
に渡すだけ(``tools/gen_plateau_venue.py`` が npz の作り方と門の見本)。
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import driveplateau as PL  # noqa: E402

VENUE = ROOT / "data" / "plateau_yokohama" / "venue_lod2.npz"
ITOKAWA = ROOT / "studio_assets" / "sample_3d" / "itokawa_points.npy"
#: 文献値(Fujiwara et al. 2006, Science 312, 1330)。主軸方向の長さ [m]。
ITOKAWA_AXES_M = (535.0, 294.0, 209.0)

_ROWS: list[tuple[str, bool]] = []


def check(what: str, expected: str, got: str, ok: bool) -> None:
    """1 行 = 何を期待し、何が出て、合ったか。"""
    _ROWS.append((what, bool(ok)))
    print("  %-46s 期待 %-26s 実測 %-26s %s" % (what, expected, got, "ok" if ok else "NG"))


def _vol(V: np.ndarray, F: np.ndarray) -> float:
    v0, v1, v2 = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return float(np.sum(np.einsum("ij,ij->i", v0, np.cross(v1, v2))) / 6.0)


def _area(V: np.ndarray, F: np.ndarray) -> float:
    return float(0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1).sum())


def part_synthetic() -> None:
    print("[1] 合成の LOD2(閉形式の真値)")
    org = (35.4575, 139.6375, 3.0)
    m = PL.plateau_lod2_mesh(PL._citygml_lod2_example(with_hole=False), origin=org)
    h = [u["height_mesh"] for u in m["units"]]
    check("高さ(本体・部位)", "12 m・4 m", "%.6f・%.6f" % tuple(h), abs(h[0] - 12) < 1e-6 and abs(h[1] - 4) < 1e-6)
    v = [_vol(m["V"], m["F"][m["face_unit"] == i]) for i in (0, 1)]
    check("体積(発散定理、外向きなら正)", "2000・144 m³", "%.4f・%.4f" % tuple(v),
          abs(v[0] - 2000) < 1e-4 and abs(v[1] - 144) < 1e-4)
    m2 = PL.plateau_lod2_mesh(PL._citygml_lod2_example(with_hole=True), origin=org)
    want = 2 * 20 * math.hypot(5, 4) + 36 - 4
    got = _area(m2["V"], m2["F"][m2["face_kind"] == 2])
    check("屋根の面積(部位の屋根に 2 m 角の穴)", "%.6f m²" % want, "%.6f m²" % got, abs(got - want) < 1e-5)
    refused = False
    try:
        PL.plateau_lod2_mesh(PL._citygml_lod2_example().replace("EPSG/0/6697", "EPSG/0/4326"))
    except ValueError:
        refused = True
    check("EPSG:6697 以外は拒む(fail-closed)", "ValueError", "ValueError" if refused else "通った", refused)


def part_venue() -> dict:
    print("[2] 会場の建物(PLATEAU 横浜市 2020 年度、LOD2)")
    d = np.load(VENUE, allow_pickle=False)
    V, F, U, K = d["V"], d["F"], d["face_unit"], d["face_kind"]
    print("    %-34s %8s %8s %7s %18s" % ("部位", "測定高", "メッシュ", "差", "最小外接長方形"))
    worst = 0.0
    vols = []
    for i, name in enumerate(d["unit_label_ja"]):
        z = V[np.unique(F[U == i]), 2]
        g = V[np.unique(F[(U == i) & (K == 0)]), 2]
        hm = float(z.max() - g.min())
        mh = float(d["unit_measured_height"][i])
        worst = max(worst, abs(hm - mh))
        vols.append(_vol(V, F[U == i]))
        L, W, _ = d["unit_rect"][i]
        print("    %-34s %7.1f m %7.3f m %+6.3f %8.1f × %5.1f m" % (str(name)[:34], mh, hm, hm - mh, L, W))
    check("メッシュの高さ = measuredHeight(7 部位)", "±0.05 m", "最大差 %.3f m" % worst, worst <= 0.05)
    check("面は外向き(部位ごとの体積 > 0)", "7 部位とも正", "最小 %.0f m³" % min(vols), min(vols) > 0)
    return {"d": d, "vol_total": float(sum(vols))}


def part_itokawa(venue: dict) -> np.ndarray:
    print("[3] イトカワと並べる")
    P = np.load(ITOKAWA).astype(np.float64)
    Q = P - P.mean(axis=0)
    _, _, vt = np.linalg.svd(Q, full_matrices=False)
    ext = np.ptp(Q @ vt.T, axis=0)
    check("点群は細長い(主軸の長さが 長 > 中 > 短)", "長 > 中 > 短", "%.0f × %.0f × %.0f m" % tuple(ext),
          bool(ext[0] > ext[1] > ext[2]))
    # ★文献値との差は門にしない(正直に): 間引いた点群の主軸方向の外接幅は 562 × 298 × 244 m で、
    # 文献の 535 × 294 × 209 m より 1〜17 % 大きい。主軸の取り方(点の主成分か慣性主軸か)と外接の取り方の
    # 違いで、どちらが「正しい」かをこの例は決められない。比較の文には文献値(535 m)を使う。
    print("    (参考)点群の外接幅 / 文献値 = %s" % " / ".join("%.2f" % r for r in ext / np.array(ITOKAWA_AXES_M)))
    d = venue["d"]
    labels = list(map(str, d["unit_label_ja"]))
    hall = labels.index("展示ホール")
    hotel = int(np.argmax(d["unit_measured_height"]))
    L_hall = float(d["unit_rect"][hall][0])
    H_hotel = float(d["unit_measured_height"][hotel])
    print("    イトカワの長さ %.0f m = 展示ホールの長辺 %.0f m の %.1f 倍 = ホテル棟の高さ %.1f m の %.1f 本分"
          % (ITOKAWA_AXES_M[0], L_hall, ITOKAWA_AXES_M[0] / L_hall, H_hotel, ITOKAWA_AXES_M[0] / H_hotel))
    V = d["V"]
    span = np.ptp(V[:, :2], axis=0)
    print("    会場 7 部位を囲む範囲 %.0f × %.0f m、建物の体積の合計 %.2f × 10⁶ m³"
          % (span[0], span[1], venue["vol_total"] / 1e6))
    return Q @ vt.T


def write_html(path: Path, venue: dict, ito: np.ndarray) -> None:
    import fullseye as fs

    def t(ja: str, en: str) -> dict:
        return fs.viewer_text(ja, en)

    d = venue["d"]
    V, F = d["V"], d["F"]
    cb = {"lo": 0.0, "hi": 145.0, "unit": "m", "cmap": "seq", "label": t("高さ", "Height")}
    t_mesh = fs.viewer_mesh_tab(
        "venue", t("会場の建物", "Venue buildings"), "passed",
        t("PLATEAU の LOD2 から 7 部位(色 = 地面からの高さ)。手前の高い塔がホテル棟(142 m)。",
          "Seven LOD2 parts from PLATEAU (colour = height above ground). The tall tower is the hotel (142 m)."),
        V, F, V[:, 2], cb,
        numbers=[fs.viewer_number(t("頂点", "Vertices"), str(len(V))),
                 fs.viewer_number(t("三角形", "Triangles"), str(len(F)))])
    # 比較: 会場の面を面積に比例して点で撒き、東に 700 m 離してイトカワの点群を置く
    rng = np.random.default_rng(0)
    a = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
    pick = rng.choice(len(F), size=12000, p=a / a.sum())
    r1, r2 = rng.random((2, len(pick)))
    s = np.sqrt(r1)
    pts_v = ((1 - s)[:, None] * V[F[pick, 0]] + (s * (1 - r2))[:, None] * V[F[pick, 1]]
             + (s * r2)[:, None] * V[F[pick, 2]])
    ito_pts = ito.copy()
    ito_pts[:, 2] += -ito_pts[:, 2].min()                       # 地面に置く
    ito_pts[:, 0] += float(V[:, 0].max()) + 450.0
    pos = np.vstack([pts_v, ito_pts])
    rgb = np.vstack([np.tile([120, 190, 255], (len(pts_v), 1)), np.tile([255, 170, 90], (len(ito_pts), 1))]).astype(np.uint8)
    t_cmp = fs.viewer_points_tab(
        "compare", t("イトカワと並べる", "Next to Itokawa"), "passed",
        t("青 = 会場の建物、橙 = イトカワ(長さ 535 m)。同じメートルの物差し。",
          "Blue = venue buildings, orange = Itokawa (535 m long). Same metre scale."),
        pos, rgb=rgb)
    spec = fs.viewer_spec(
        "plateau_venue_itokawa", t("会場とイトカワ", "The venue and Itokawa"),
        t("ViEW2026 の会場(パシフィコ横浜)の建物と小惑星イトカワを同じ縮尺で。",
          "The ViEW2026 venue buildings (Pacifico Yokohama) and asteroid Itokawa at the same scale."),
        t("ドラッグで回転、ホイールで拡大。", "Drag to rotate, wheel to zoom."),
        [t_mesh, t_cmp],
        credit=t("建物: 「3D都市モデル(Project PLATEAU)横浜市(2020年度)」(国土交通省)を加工して作成。"
                 "イトカワ: Gaskell の形状モデル(PDS 小天体ノード)から間引いた点群。",
                 "Buildings: processed from the 3D city model (Project PLATEAU) Yokohama City 2020 (MLIT). "
                 "Itokawa: points decimated from the Gaskell shape model (PDS Small Bodies Node)."))
    path.parent.mkdir(parents=True, exist_ok=True)
    out = fs.write_viewer(spec, str(path), ["ja", "en"])
    html = Path(out).read_text(encoding="utf-8")
    check("ビューアに外部 URL が無い", "http(s):// 0 件", "%d 件" % (html.count("http://") + html.count("https://")),
          "http://" not in html and "https://" not in html)
    print("    書いた: %s(%.0f KB)" % (out, Path(out).stat().st_size / 1e3))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--html", default=None, help="触って見るビューアの出力先(省略なら書かない)")
    a = ap.parse_args(argv)
    t0 = time.perf_counter()
    part_synthetic()
    venue = part_venue()
    ito = part_itokawa(venue)
    if a.html:
        write_html(Path(a.html), venue, ito)
    ng = [w for w, ok in _ROWS if not ok]
    print("plateau venue: %d 検査 / NG %d / %.2f s" % (len(_ROWS), len(ng), time.perf_counter() - t0))
    if ng:
        print("FAILED:", ng)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
