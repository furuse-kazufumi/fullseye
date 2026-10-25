# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gsplat_product_viewer — 商品を 3D Gaussian Splatting にして、ブラウザで回して見る 1 枚の HTML とカタログを書く。

    py -3.11 examples/gsplat_product_viewer.py                    # out/gsplat/ に書く
    py -3.11 examples/gsplat_product_viewer.py --out docs/gsplat  # 公開ページ(tools/build_gsplat_pages.py も同じ)

【この例が示すこと】
1. 形は Fullseye の op で作る: 符号付き距離場の部品(``cylinder_sdf`` / ``torus_sdf`` / ``capsule_sdf`` / ``box_sdf`` /
   ``sphere_sdf`` / ``plane_sdf``)を ``sdf_union`` / ``sdf_subtract`` / ``sdf_intersect`` / ``sdf_smooth_union`` で組み、
   ``voxel_to_mesh``(marching cubes)でメッシュにする。部品ごとに色を付けて世界(三角形の束)へ足す。
2. その世界を ``gs_from_world`` で 3DGS にする(メッシュから初期化した 3DGS。写真から学習したものではない ——
   ページの「この表示について」にもそう書く)。
3. ``gs_viewer_html`` で 1 品のビューア(注記点つきのヘッドホン)、``gs_catalog_html`` で 5 品のカタログを書く。
   寸法(W × D × H mm)は ``smallest_box3`` が出した外形の箱。
4. 書いた HTML を読み戻して、量子化の範囲で元のガウシアンに戻ること・外部 URL が 0 であることを確かめて PASS を出す。

EXTEND: 自分の .ply / .splat なら ``py -3.11 -m gsviewer in.ply --out view.html --title "..."``(2 つ以上でカタログ)。
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import driveworld  # noqa: E402
import gsplatnp  # noqa: E402
import gsviewer  # noqa: E402
import match3d  # noqa: E402
import sdf_ops as S  # noqa: E402

LANGS = gsviewer.LANGS


def _t(ja, en, zh, tw, ko, de, hi, fr):
    return dict(zip(LANGS, (ja, en, zh, tw, ko, de, hi, fr)))


#: どの品にも付ける正直な注記(8 言語)。
NOTE = _t("メッシュ(Fullseye の符号付き距離場の op + marching cubes)から初期化した 3DGS です。写真から学習したものではありません。"
          "陰影は固定した光で色に焼き込んでいます。",
          "A 3DGS initialised from a mesh (Fullseye signed-distance ops + marching cubes), not trained from photographs. "
          "Shading is baked into the colours with a fixed light.",
          "这是由网格(Fullseye 的符号距离场算子 + marching cubes)初始化的 3DGS,并非由照片训练得到。阴影以固定光源烘焙进颜色。",
          "這是由網格(Fullseye 的符號距離場算子 + marching cubes)初始化的 3DGS,並非由照片訓練而來。陰影以固定光源烘焙進顏色。",
          "메시(Fullseye의 부호 거리장 op + marching cubes)에서 초기화한 3DGS이며, 사진으로 학습한 것이 아닙니다. "
          "음영은 고정된 조명으로 색에 구워 넣었습니다.",
          "Ein aus einem Netz initialisiertes 3DGS (Fullseye-SDF-Operatoren + Marching Cubes), nicht aus Fotos trainiert. "
          "Die Schattierung ist mit festem Licht in die Farben eingebrannt.",
          "यह मेश (Fullseye के signed-distance op + marching cubes) से आरंभ किया गया 3DGS है, तस्वीरों से प्रशिक्षित नहीं। "
          "छाया एक स्थिर प्रकाश से रंगों में पकाई गई है।",
          "Un 3DGS initialisé à partir d’un maillage (opérateurs SDF de Fullseye + marching cubes), non entraîné sur des photos. "
          "L’ombrage est cuit dans les couleurs avec une lumière fixe.")


def _part(bounds, voxel: float, sdf_fn):
    """部品 1 つ: 範囲 ``bounds`` を ``voxel`` 刻みの格子にして ``sdf_fn(格子)`` を評価し、0 の等値面をメッシュにする。"""
    b = np.asarray(bounds, np.float64)
    res = np.maximum(8, np.ceil((b[:, 1] - b[:, 0]) / voxel)).astype(int)
    g, _ext = S.grid_coords(b, res)
    v, f, _n = match3d.voxel_to_mesh(sdf_fn(g), iso=0.0)
    span = b[:, 1] - b[:, 0]
    V = b[:, 0] + (v + 0.5) / res * span                    # 格子の添字 → 世界(grid_coords の中心合わせと同じ)
    return V, np.asarray(f, np.int64)


def _world(parts):
    w = driveworld._empty_world()
    for i, (name, (V, F), color) in enumerate(parts):
        driveworld.world_add(w, V, F, i + 1, color, name=name)
    return w


Z = (0.0, 0.0, 1.0)
X = (1.0, 0.0, 0.0)
Y = (0.0, 1.0, 0.0)


def mug():
    """マグカップ(高さ 95 mm、外径 82 mm、取っ手つき、コーヒー入り)。"""
    vx = 0.0012
    body = _part(((-0.045, 0.045), (-0.045, 0.045), (-0.002, 0.098)), vx, lambda g: S.sdf_subtract(
        S.cylinder_sdf(g, (0, 0, 0.0475), Z, 0.041, 0.095), S.cylinder_sdf(g, (0, 0, 0.06), Z, 0.0365, 0.09)))
    handle = _part(((0.035, 0.085), (-0.01, 0.01), (0.018, 0.082)), vx * 0.8, lambda g: S.sdf_subtract(
        S.torus_sdf(g, (0.052, 0, 0.05), Y, 0.024, 0.0062), S.cylinder_sdf(g, (0, 0, 0.05), Z, 0.04, 0.2)))
    coffee = _part(((-0.04, 0.04), (-0.04, 0.04), (0.074, 0.086)), vx, lambda g: S.cylinder_sdf(g, (0, 0, 0.08), Z, 0.0368, 0.006))
    return _world([("body", body, (0.16, 0.52, 0.58)), ("handle", handle, (0.16, 0.52, 0.58)),
                   ("coffee", coffee, (0.32, 0.18, 0.09))])


def headphones():
    """ヘッドホン(幅 約 190 mm、高さ 約 200 mm)。"""
    vx = 0.0016
    band = _part(((-0.1, 0.1), (-0.015, 0.015), (0.09, 0.2)), vx, lambda g: S.sdf_intersect(
        S.torus_sdf(g, (0, 0, 0.1), Y, 0.087, 0.0085), S.plane_sdf(g, (0, 0, 0.1), (0, 0, -1))))
    pads = (0.005, 0.11)
    cups, cush, yokes = [], [], []
    for sx in (-1, 1):
        def xr(c, h, sx=sx):
            return (sx * c - h, sx * c + h)
        cups.append(_part((xr(0.093, 0.02), (-0.05, 0.05), pads), vx,
                          lambda g, sx=sx: S.cylinder_sdf(g, (sx * 0.093, 0, 0.055), X, 0.045, 0.026)))
        cush.append(_part((xr(0.074, 0.016), (-0.05, 0.05), pads), vx,
                          lambda g, sx=sx: S.torus_sdf(g, (sx * 0.074, 0, 0.055), X, 0.034, 0.011)))
        yokes.append(_part((xr(0.091, 0.014), (-0.012, 0.012), (0.085, 0.115)), vx * 0.7,
                           lambda g, sx=sx: S.capsule_sdf(g, (sx * 0.089, 0, 0.1), (sx * 0.093, 0, 0.098), 0.009)))
    parts = [("headband", band, (0.13, 0.13, 0.14))]
    for i in range(2):
        parts += [("cup%d" % i, cups[i], (0.72, 0.12, 0.16)), ("cushion%d" % i, cush[i], (0.22, 0.22, 0.24)),
                  ("yoke%d" % i, yokes[i], (0.7, 0.72, 0.75))]
    return _world(parts)


def watch():
    """腕時計(ケース径 42 mm、ベルトを伸ばした長さ 約 120 mm)。"""
    vx = 0.0006
    case = _part(((-0.024, 0.024), (-0.024, 0.024), (0.0, 0.013)), vx, lambda g: S.cylinder_sdf(g, (0, 0, 0.0065), Z, 0.021, 0.011))
    bezel = _part(((-0.023, 0.023), (-0.023, 0.023), (0.009, 0.016)), vx, lambda g: S.torus_sdf(g, (0, 0, 0.0122), Z, 0.0195, 0.0019))
    dial = _part(((-0.02, 0.02), (-0.02, 0.02), (0.0105, 0.0135)), vx, lambda g: S.cylinder_sdf(g, (0, 0, 0.012), Z, 0.0182, 0.0016))
    hands = _part(((-0.016, 0.016), (-0.016, 0.016), (0.012, 0.0155)), vx * 0.6, lambda g: S.sdf_union(
        S.box_sdf(g, (0.0, 0.006, 0.0137), (0.0007, 0.0075, 0.0005)), S.box_sdf(g, (0.0045, -0.002, 0.0141), (0.0055, 0.0006, 0.0005))))
    crown = _part(((0.019, 0.028), (-0.004, 0.004), (0.002, 0.011)), vx * 0.6, lambda g: S.cylinder_sdf(g, (0.0235, 0, 0.0065), X, 0.0028, 0.004))
    strap = _part(((-0.013, 0.013), (-0.064, 0.064), (0.0, 0.008)), vx * 1.5, lambda g: S.sdf_subtract(
        S.sdf_offset(S.box_sdf(g, (0, 0, 0.004), (0.0095, 0.06, 0.0018)), 0.0008), S.cylinder_sdf(g, (0, 0, 0.0065), Z, 0.02, 0.012)))
    return _world([("case", case, (0.76, 0.77, 0.8)), ("bezel", bezel, (0.6, 0.62, 0.66)), ("dial", dial, (0.95, 0.95, 0.91)),
                   ("hands", hands, (0.08, 0.08, 0.1)), ("crown", crown, (0.76, 0.77, 0.8)), ("strap", strap, (0.46, 0.28, 0.15))])


def sneaker():
    """スニーカー(長さ 約 280 mm)。"""
    vx = 0.0018
    sole = _part(((-0.145, 0.145), (-0.055, 0.055), (-0.002, 0.026)), vx, lambda g: S.sdf_offset(
        S.box_sdf(g, (0, 0, 0.012), (0.128, 0.04, 0.007)), 0.005))

    def upper_sdf(g):
        foot = S.sdf_smooth_union(S.capsule_sdf(g, (-0.085, 0, 0.05), (0.07, 0, 0.032), 0.04),
                                  S.capsule_sdf(g, (-0.095, 0, 0.055), (-0.085, 0, 0.1), 0.038), 0.02)
        foot = S.sdf_intersect(foot, S.plane_sdf(g, (0, 0, 0.018), (0, 0, -1)))
        return S.sdf_subtract(foot, S.cylinder_sdf(g, (-0.085, 0, 0.12), Z, 0.03, 0.06))
    upper = _part(((-0.14, 0.12), (-0.045, 0.045), (0.016, 0.14)), vx, upper_sdf)
    laces = _part(((-0.06, 0.04), (-0.025, 0.025), (0.05, 0.1)), vx * 0.6, lambda g: S.sdf_union(S.sdf_union(
        S.capsule_sdf(g, (-0.04, -0.018, 0.079), (-0.04, 0.018, 0.079), 0.0028),
        S.capsule_sdf(g, (-0.015, -0.018, 0.072), (-0.015, 0.018, 0.072), 0.0028)),
        S.capsule_sdf(g, (0.01, -0.017, 0.066), (0.01, 0.017, 0.066), 0.0028)))
    return _world([("sole", sole, (0.94, 0.94, 0.92)), ("upper", upper, (0.16, 0.32, 0.72)), ("laces", laces, (0.97, 0.97, 0.97))])


def lamp():
    """卓上ランプ(高さ 約 370 mm)。"""
    vx = 0.0018
    base = _part(((-0.075, 0.075), (-0.075, 0.075), (-0.002, 0.024)), vx, lambda g: S.sdf_offset(
        S.cylinder_sdf(g, (0, 0, 0.011), Z, 0.066, 0.016), 0.003))
    stem = _part(((-0.012, 0.135), (-0.012, 0.012), (0.015, 0.355)), vx * 0.7, lambda g: S.sdf_union(
        S.capsule_sdf(g, (0, 0, 0.02), (0, 0, 0.31), 0.0075), S.capsule_sdf(g, (0, 0, 0.31), (0.125, 0, 0.345), 0.0065)))

    def shade_sdf(g):
        shell = S.sdf_subtract(S.sphere_sdf(g, (0.16, 0, 0.3), 0.07), S.sphere_sdf(g, (0.16, 0, 0.3), 0.066))
        return S.sdf_intersect(shell, S.plane_sdf(g, (0, 0, 0.29), (0, 0, -1)))
    shade = _part(((0.085, 0.235), (-0.075, 0.075), (0.28, 0.375)), vx, shade_sdf)
    bulb = _part(((0.13, 0.19), (-0.03, 0.03), (0.26, 0.32)), vx * 0.7, lambda g: S.sphere_sdf(g, (0.16, 0, 0.292), 0.024))
    return _world([("base", base, (0.2, 0.21, 0.23)), ("stem", stem, (0.74, 0.75, 0.78)), ("shade", shade, (0.95, 0.74, 0.18)),
                   ("bulb", bulb, (1.0, 0.96, 0.82))])


#: カタログの品(作る関数、名前、説明、gs_from_world の間隔 [m])。
PRODUCTS = [
    (mug, _t("マグカップ", "Mug", "马克杯", "馬克杯", "머그컵", "Becher", "मग", "Tasse"),
     _t("陶器のマグ", "Ceramic mug", "陶瓷马克杯", "陶瓷馬克杯", "도자기 머그", "Keramikbecher", "चीनी मिट्टी का मग", "Tasse en céramique"), 0.0011),
    (headphones, _t("ヘッドホン", "Headphones", "头戴式耳机", "頭戴式耳機", "헤드폰", "Kopfhörer", "हेडफ़ोन", "Casque audio"),
     _t("密閉型", "Closed-back", "封闭式", "封閉式", "밀폐형", "Geschlossen", "क्लोज़्ड-बैक", "Fermé"), 0.0012),
    (watch, _t("腕時計", "Wristwatch", "手表", "手錶", "손목시계", "Armbanduhr", "कलाई घड़ी", "Montre"),
     _t("革ベルト", "Leather strap", "皮表带", "皮錶帶", "가죽 밴드", "Lederarmband", "चमड़े का पट्टा", "Bracelet en cuir"), 0.0005),
    (sneaker, _t("スニーカー", "Sneaker", "运动鞋", "運動鞋", "운동화", "Turnschuh", "स्नीकर", "Basket"),
     _t("片足ぶん", "One shoe", "单只", "單隻", "한 짝", "Ein Schuh", "एक जूता", "Une chaussure"), 0.0014),
    (lamp, _t("卓上ランプ", "Desk lamp", "台灯", "檯燈", "탁상 램프", "Schreibtischlampe", "डेस्क लैंप", "Lampe de bureau"),
     _t("アーム式", "Arm lamp", "悬臂式", "懸臂式", "암 타입", "Mit Arm", "आर्म वाला", "À bras"), 0.0015),
]

#: ヘッドホンの注記点(位置 [m] と 8 言語のラベル・説明)。
HEADPHONE_HOTSPOTS = [
    {"pos": (0.0, 0.0, 0.196),
     "label": _t("ヘッドバンド", "Headband", "头梁", "頭樑", "헤드밴드", "Kopfbügel", "हेडबैंड", "Arceau"),
     "desc": _t("左右のハウジングをつなぐ弧。頭の幅に合わせて広がる。", "The arc joining both housings; it widens to fit the head.",
                "连接左右耳罩的弧形,可随头宽张开。", "連接左右耳罩的弧形,可隨頭寬張開。", "양쪽 하우징을 잇는 호. 머리 폭에 맞게 벌어진다.",
                "Der Bogen zwischen beiden Gehäusen; er weitet sich passend zum Kopf.", "दोनों हाउसिंग को जोड़ने वाला चाप; सिर के अनुसार फैलता है।",
                "L’arc qui relie les deux coques ; il s’élargit selon la tête.")},
    {"pos": (0.108, 0.0, 0.055),
     "label": _t("ハウジング", "Housing", "耳罩外壳", "耳罩外殼", "하우징", "Gehäuse", "हाउसिंग", "Coque"),
     "desc": _t("ドライバーを収める円筒の殻。外径 90 mm。", "The cylindrical shell holding the driver; 90 mm across.",
                "容纳发声单元的圆筒外壳,外径 90 mm。", "容納發聲單元的圓筒外殼,外徑 90 mm。", "드라이버를 담는 원통형 껍데기. 외경 90 mm.",
                "Die zylindrische Schale mit dem Treiber; 90 mm Durchmesser.", "ड्राइवर रखने वाला बेलनाकार खोल; व्यास 90 mm।",
                "La coque cylindrique qui loge le transducteur ; 90 mm de diamètre.")},
    {"pos": (-0.061, -0.03, 0.08),
     "label": _t("イヤーパッド", "Ear cushion", "耳垫", "耳墊", "이어 쿠션", "Ohrpolster", "ईयर कुशन", "Coussinet"),
     "desc": _t("耳を囲むドーナツ形のクッション(トーラスで作った)。", "The ring cushion around the ear (made from a torus).",
                "环绕耳朵的环形软垫(由圆环面生成)。", "環繞耳朵的環形軟墊(由圓環面生成)。", "귀를 감싸는 도넛 모양 쿠션(토러스로 만듦).",
                "Das ringförmige Polster um das Ohr (aus einem Torus).", "कान के चारों ओर छल्लेदार गद्दी (टोरस से बनी)।",
                "Le coussin annulaire autour de l’oreille (fait d’un tore).")},
]


def splats(i: int):
    fn, _name, _desc, spacing = PRODUCTS[i]
    world = fn()
    return gsplatnp.gs_from_world(world, spacing=spacing, max_per_object=80000, seed=i)


def build(out_dir: str, *, report=print) -> dict:
    """1 品のビューア(ヘッドホン、注記点つき)と 5 品のカタログを ``out_dir`` に書き、読み戻して確かめる。"""
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.time()
    gss = [splats(i) for i in range(len(PRODUCTS))]
    report("3DGS: %s Gaussians (%.1f s)" % (", ".join("%s %d" % (p[1]["en"], len(g["mu"])) for p, g in zip(PRODUCTS, gss)),
                                          time.time() - t0))
    title1 = _t("ヘッドホン — 3DGS ビューア", "Headphones — 3DGS viewer", "头戴式耳机 — 3DGS 查看器", "頭戴式耳機 — 3DGS 檢視器",
                "헤드폰 — 3DGS 뷰어", "Kopfhörer — 3DGS-Betrachter", "हेडफ़ोन — 3DGS व्यूअर", "Casque audio — visionneuse 3DGS")
    single = gsviewer.gs_viewer_html(gss[1], os.path.join(out_dir, "headphones.html"), title=title1, note=NOTE,
                                     hotspots=HEADPHONE_HOTSPOTS, camera={"yaw": -62.0, "pitch": 18.0})
    report("viewer: %s  %.2f MB  %d Gaussians  dims %s mm" % (single["path"], single["bytes"] / 1048576, single["n_kept"],
                                                           " x ".join("%.0f" % single["dims_mm"][k] for k in "WDH")))
    titlec = _t("商品カタログ(3DGS)", "Product catalogue (3DGS)", "商品目录(3DGS)", "商品目錄(3DGS)", "상품 카탈로그(3DGS)",
                "Produktkatalog (3DGS)", "उत्पाद सूची (3DGS)", "Catalogue produits (3DGS)")
    items = [{"gs": g, "name": p[1], "desc": p[2], "note": NOTE} for p, g in zip(PRODUCTS, gss)]
    items[1]["hotspots"] = HEADPHONE_HOTSPOTS
    cat = gsviewer.gs_catalog_html(items, os.path.join(out_dir, "catalog.html"), title=titlec)
    report("catalogue: %s  %.2f MB  %d items  dropped %d" % (cat["path"], cat["bytes"] / 1048576, len(items), cat["n_dropped_total"]))
    for it in cat["items"]:
        report("  %-12s %6d Gaussians  %s mm" % (it["name"], it["n_kept"], " x ".join("%.0f" % it["dims_mm"][k] for k in "WDH")))
    # 読み戻し: 埋め込みが元のガウシアンに量子化の範囲で戻る / 外部 URL が無い
    ok = True
    for path, srcs in ((single["path"], [gss[1]]), (cat["path"], gss)):
        emb = gsviewer._read_embedded(path)
        page = open(path, encoding="utf-8").read()
        nurl = page.count("http://") + page.count("https://")
        for g, d, it in zip(srcs, emb["items"], emb["cfg"]["items"]):
            c = gsviewer._subset(gsviewer._canon(g), gsviewer._importance_order(gsviewer._canon(g)))
            step = np.asarray(it["meta"]["span"]) / 65535.0
            err = np.abs(c["mu"][: len(d["mu"])] - d["mu"]).max(0)
            good = bool(np.all(err <= 0.5 * step + 1e-12))
            ok &= good
        report("%s: position error within half a quantisation step: %s / external URLs: %d" % (os.path.basename(path), good, nurl))
        ok &= nurl == 0
    report("PASS" if ok else "FAIL")
    return {"single": single, "catalog": cat, "ok": ok}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out", "gsplat"))
    a = ap.parse_args(argv)
    r = build(a.out)
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
