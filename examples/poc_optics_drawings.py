# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 光学系の図面を出す —— 計算した処方そのものから、レンズ断面図・装置の設置図・単レンズの製作図を SVG / DXF で。

【問い】外観検査・計測の打ち合わせでは、レンズの断面図と装置の設置図(作動距離・視野・照明の角度)が共通言語で、
レンズの製作を頼むには ISO 10110 の製作図が要る。Fullseye は処方を実光線で評価し(``raytrace``)、撮像系の
光学バジェットを出す(``optscene.vision_layout``)が、**図を 1 枚も出さなかった**。新 op 8 本(``optdraw``)で
図を出し、**図に書いた線と文字を SVG / DXF から読み戻して**、計算と公表値に突き合わせる。見た目では採点しない。
仮番号(収蔵番号は統合のときに振る)。6 章:

  1. **教科書の Cooke triplet 2 本**: 処方 A(f = 50 mm、F/5、半画角 20°、SK16 / F2 —— 光学設計ソフトの同梱
     サンプルと同じ数値が OSS の optiland のギャラリーに公表、EFL 49.9998 mm at 0.55 µm)と処方 B(Geiser の例、
     f = 50 mm、F/4、LAK9 / SF5、Sasian の講義資料 OPTI 517)。門: EFL が公表値と 1e-3 以内(硝材は同じ名前の
     現行の鉛フリー品 N- の Sellmeier なので完全一致はしない)、読み戻した面の座標が球面の sag の閉形式
     R − sign(R)·√(R² − y²) と 1e-5 mm 以内、光線の折れ点が面の上(同じ閉形式)に 1e-5 mm 以内、主光線が
     ``raytrace.chief_ray`` と 1e-6 mm 以内、寸法の数字(EFL・BFL・全長・像高)が ``paraxial_trace`` と表示の桁で一致、
     処方表の R と間隔が入力と表示の桁で一致。
  2. **テレセン 3 種の断面図**: ``telecentric_lens`` の通常 / 物体側 / 両側テレセンを描く。光線は絞りを狙って
     割線法で探す(入射瞳を使わない)ので、入射瞳が無限遠でも描ける。門: 読み戻した主光線の物体側の傾きが
     ``telecentric.chief_ray_angle``(Newton 法、別の実装)と 1e-6° 以内、テレセン 2 種は 0.06° 未満、通常は 1° 超。
  3. **撮像系の設置図**: 照明 5 種(ring / dome / bar / coaxial / backlight)を描き分ける。門: 視野の錐の 4 本の線が
     作業面で ±(画素数 × 画素 / m)/2 に届く(m = f/(WD − f)、作動距離に合焦させた薄肉レンズ、1e-6 mm)、WD・視野・DOF の
     数字が閉形式(DOF = (2N_w·c + 2λN_w²)/m²)と表示の桁で一致、仰角の数字が atan(H/R) と一致、上面図の円環の半径が R。
     さらに図と独立の経路として、同じ構成を ``layout_capture`` で**撮った画像**の上で、幅の分かった部品が
     幅 × m / 画素 の画素数に写ることを見る(1 画素以内)。★2026-10-15 の検分で、描いた視野(画素数 × 画素 × WD / f)と
     バジェットの倍率 f/(WD − f) が同じ図の中で 14 % 食い違っているのが見つかった —— 当時のこの門は視野を同じ
     WD / f の式で採点していた(両辺に同じ模型を入れた門)。原因は ``optscene.vision_layout`` がピンホールの距離に
     焦点距離 f を渡していたことで、像距離 v = f·WD/(WD − f) に直した(``optscene`` の修正)。
  4. **単レンズの製作図(ISO 10110)**: BK7 相当のホウケイ酸クラウン(n_d 1.517・ν_d 64.2)の平凸 f = 100 mm と両凸。門: 読み戻した R・中心厚・外径の文字が
     処方どおり、n_d・ν_d が公開の硝材カタログ値(1.51680 / 64.17)と表示の桁で一致、注記の EFL が厚肉
     レンズの公式と一致、縞の本数が sag の差 / (λ/2) の閉形式と一致、Monte-Carlo の EFL の幅が
     ``tolerance_analysis`` と一致。
  5. **往復**: 図 → DXF → ``dxf_entities`` → 図、図 → SVG → ``svg_entities`` → 図 で座標が 1e-6 mm、文字が一致。
     第二の実装として OSS の ezdxf(MIT)があれば DXF を読ませて要素の数と座標を突き合わせる(手元に無ければ
     2026-10-15 に別の venv で得た記録を印字する。門には使わない)。
  6. **壊して確かめる**: sag の符号を反転した図、光線の折れ点を 0.01 mm ずらした SVG、EFL の数字を書き換えた SVG、
     VERTEX を 1 つ抜いた DXF、ENDSEC の無い DXF を作り、上の門がすべて赤になる(または読み戻しが ValueError)
     ことを確かめる。

【外部真値】球面・円錐の sag の閉形式、厚肉レンズの公式、教科書・講義資料・OSS ギャラリーの処方と EFL、
メーカーの硝材の公表値、``optscene.optical_camera`` の視野の閉形式、別の実装(``telecentric`` の Newton 法の狙い、
ezdxf)。【学習】0。【較正】0。

【来歴】Smith, *Modern Lens Design*(Cooke triplet)/ J. Sasian, OPTI 517 Lecture 20 "Cooke triplet"
(Univ. of Arizona)/ optiland のギャラリー "Cooke Triplet"(MIT)/ ISO 10110 の公開解説: J. Lane, "Tutorial on
ISO 10110 Optical Drawing Standard"(OPTI 521, Univ. of Arizona, 2009)、J. H. Burge, "Introduction to ISO 10110"
(講義スライド)/ ISO 129-1:2018 のプレビュー(寸法の文字は寸法線の上・下と右から読む)/ ezdxf の文書
(DXF R12 の構成)。

EXTEND: 非球面の製作図(ISO 10110-12 の sag の表)、接合レンズの製作図、鏡・傾き・偏心のある系の断面図、
3-D の設置図(STEP)は扱っていない。設置図の鏡筒とカメラ本体の大きさは ``lens_spec`` に無いので図のための仮の寸法。

使い方:
    py -3.11 examples/poc_optics_drawings.py                 # 門だけ
    py -3.11 examples/poc_optics_drawings.py --out DIR       # 図を SVG / DXF / PNG で DIR に書く(等倍で見る用)
"""
from __future__ import annotations

import argparse
import math
import os
import re
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import materials as MT  # noqa: E402
import optdraw as OD  # noqa: E402
import optscene as OS  # noqa: E402
import raytrace as RT  # noqa: E402
import telecentric as TC  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

FAILS: list[str] = []
GATES: list[str] = []
NUMBERS: dict[str, float] = {}

#: 公表値。A: optiland のギャラリー(光学設計ソフトの同梱サンプル "Cooke 40 degree field" と同じ数値)、
#: EFL 49.9998 mm(基準波長 0.55 µm)。B: Sasian OPTI 517 L20 の Geiser の例、f = 50 mm。
COOKE_A_EFL = 49.9998
COOKE_B_EFL = 50.0
#: BK7 相当のホウケイ酸クラウンの公開の硝材カタログ値(データシート)。
NBK7_ND, NBK7_VD = 1.51680, 64.17


def glass_near(nd, vd):
    """材料表の硝子から n_d・ν_d が最も近いものの名前(公開側に硝材の銘柄名を書かないため、性質で指す)。
    最も近い硝子が n_d で 0.002・ν_d で 0.5 より離れていれば止める(黙って別の硝子にしない)。"""
    best = min(MT.glass_map("glass"), key=lambda r: abs(r["nd"] - nd) / 0.002 + abs(r["vd"] - vd) / 0.5)
    if abs(best["nd"] - nd) > 0.002 or abs(best["vd"] - vd) > 0.5:
        raise SystemExit("no glass near n_d %.4f / nu_d %.2f in the material table" % (nd, vd))
    return best["name"]


#: 硝材は n_d・ν_d の 6 桁コードで指す(BK7 相当のホウケイ酸クラウン、Cooke triplet の重クラウンとフリント、
#: Geiser の例のランタンクラウンと重フリント)。
GLASS_517642 = glass_near(1.5168, 64.17)
GLASS_620603 = glass_near(1.6204, 60.32)
GLASS_620364 = glass_near(1.6200, 36.43)
GLASS_691547 = glass_near(1.6910, 54.71)
GLASS_673323 = glass_near(1.6727, 32.25)
#: 2026-10-15 に ezdxf 1.4(別の venv)で cooke_a.dxf を読ませた結果。手元に ezdxf が無いときに印字する(門には使わない)。
EZDXF_RECORDED = ("ezdxf 1.4.4: 11 files read as AC1009, audit errors 0 / fixes 0, 1158 entities; layer, text and "
                  "coordinates identical to dxf_entities (max difference 0 mm)")


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


# --------------------------------------------------------------------------- #
# 独立の真値と、読み戻した図の採点(optdraw の関数は使わない)
# --------------------------------------------------------------------------- #
def sag_closed(R, k, y):
    """球面は R − sign(R)·√(R² − y²)、円錐は c y²/(1 + √(1 − (1+k) c² y²))(raytrace の docstring の式を書き直したもの)。"""
    y = np.asarray(y, float)
    if R == math.inf:
        return np.zeros_like(y)
    if k == 0.0:
        return R - np.sign(R) * np.sqrt(R * R - y * y)
    c = 1.0 / R
    return c * y * y / (1.0 + np.sqrt(1.0 - (1.0 + k) * c * c * y * y))


def vertices(system):
    z = [0.0]
    for s in system["surfaces"][:-1]:
        z.append(z[-1] + s["t"])
    return z


def surface_polylines(ents, system):
    """読み戻した要素から面の曲線を拾い、面の番号に割り当てる(y ≈ 0 の点の z がいちばん近い頂点)。"""
    zv = vertices(system)
    out = {}
    for e in ents:
        if e["type"] != "polyline" or e["layer"] not in ("OUTLINE", "THIN") or len(e["points"]) < 11:
            continue
        p = np.asarray(e["points"])
        z0 = p[np.argmin(np.abs(p[:, 1])), 0]
        i = int(np.argmin([abs(z0 - v) for v in zv]))
        if abs(z0 - zv[i]) < 1e-3:
            out[i] = p
    return out


def sag_residual(ents, system):
    zv = vertices(system)
    polys = surface_polylines(ents, system)
    worst = 0.0
    for i, p in polys.items():
        s = system["surfaces"][i]
        worst = max(worst, float(np.max(np.abs(p[:, 0] - zv[i] - sag_closed(s["R"], s["k"], p[:, 1])))))
    return worst, len(polys)


def ray_polylines(ents):
    return [np.asarray(e["points"]) for e in ents if e["type"] == "polyline" and e["layer"].startswith("RAY_F")]


def ray_on_surface_residual(ents, system):
    """光線の折れ点 k(1..面の数)が面 k−1 の上にあるか(閉形式の sag で)。"""
    zv = vertices(system)
    worst, n = 0.0, 0
    for p in ray_polylines(ents):
        for i, s in enumerate(system["surfaces"]):
            z, y = p[1 + i]
            worst = max(worst, abs(z - zv[i] - float(sag_closed(s["R"], s["k"], [y])[0])))
            n += 1
    return worst, n


def texts(ents):
    return [e["text"] for e in ents if e["type"] == "text"]


def dim_value(ents, name):
    vals = [float(m.group(1)) for t in texts(ents) for m in [re.fullmatch(r"%s (-?\d+\.\d+)" % name, t)] if m]
    return vals[0] if len(vals) == 1 else None


def roundtrip_residual(model, back, by_layer=False):
    """図のモデルと読み戻しの要素を順に比べる(型・層・座標・文字)。SVG は層ごとの ``<g>`` にまとめて書くので
    *by_layer* で同じ並べ替え(層の表の順、層の中は元の順)をしてから比べる。"""
    a, b = model["entities"], back["entities"]
    if by_layer:
        order = {k: i for i, k in enumerate(OD.LAYERS)}
        a = sorted(a, key=lambda e: order[e["layer"]])
    if len(a) != len(b):
        return math.inf, "count %d vs %d" % (len(a), len(b))
    worst = 0.0
    for ea, eb in zip(a, b):
        if ea["type"] != eb["type"] or ea["layer"] != eb["layer"]:
            return math.inf, "type/layer %s/%s vs %s/%s" % (ea["type"], ea["layer"], eb["type"], eb["layer"])
        if ea["type"] in ("line", "polyline"):
            pa, pb = np.asarray(ea["points"]), np.asarray(eb["points"])
            if pa.shape != pb.shape:
                return math.inf, "points %s vs %s" % (pa.shape, pb.shape)
            worst = max(worst, float(np.max(np.abs(pa - pb))))
        elif ea["type"] in ("circle", "arc"):
            worst = max(worst, float(np.max(np.abs(np.subtract(ea["center"], eb["center"])))), abs(ea["r"] - eb["r"]))
            if ea["type"] == "arc":
                for k in ("start_deg", "end_deg"):
                    d = (ea[k] - eb[k] + 180.0) % 360.0 - 180.0
                    worst = max(worst, abs(d) * math.pi / 180.0 * ea["r"])
        else:
            if ea["text"].replace("∞", "INF") != eb["text"].replace("∞", "INF"):
                return math.inf, "text %r vs %r" % (ea["text"], eb["text"])
            worst = max(worst, float(np.max(np.abs(np.subtract(ea["at"], eb["at"])))))
    return worst, ""


# --------------------------------------------------------------------------- #
# 処方
# --------------------------------------------------------------------------- #
def cooke_a():
    """処方 A: f = 50、F/5、半画角 20°(重クラウン n_d 1.620・ν_d 60.3 とフリント n_d 1.620・ν_d 36.4、どちらも現行の鉛フリー品)。絞りは第 4 面、入射瞳径 10 mm に合わせる。"""
    c = [{"R": 22.01359, "t": 3.25896, "n": GLASS_620603}, {"R": -435.76044, "t": 6.00755, "n": 1.0},
         {"R": -22.21328, "t": 0.99997, "n": GLASS_620364}, {"R": 20.29192, "t": 4.75041, "n": 1.0, "ap": 4.6},
         {"R": 79.68360, "t": 2.95208, "n": GLASS_620603}, {"R": -18.39533, "t": 42.20778, "n": 1.0}]
    s = RT.lens_system(c, stop=3, wavelength_um=0.55, field=20.0)
    c[3]["ap"] = 4.6 * 5.0 / RT.paraxial_trace(s)["ep_radius"]
    return RT.lens_system(c, stop=3, wavelength_um=0.55, field=20.0)


def cooke_b():
    """処方 B: Geiser の例(f = 50、F/4、±20°、ランタンクラウン n_d 1.691・ν_d 54.7 と重フリント n_d 1.673・ν_d 32.3 の現行の鉛フリー品)。絞りは第 3 面、入射瞳径 12.5 mm。"""
    c = [{"R": 23.713, "t": 4.831, "n": GLASS_691547}, {"R": 7331.288, "t": 5.86, "n": 1.0},
         {"R": -24.456, "t": 0.975, "n": GLASS_673323, "ap": 5.0}, {"R": 21.896, "t": 4.822, "n": 1.0},
         {"R": 86.759, "t": 3.127, "n": GLASS_691547}, {"R": -20.4942, "t": 41.10346, "n": 1.0}]
    s = RT.lens_system(c, stop=2, field=20.0)
    c[2]["ap"] = 5.0 * 6.25 / RT.paraxial_trace(s)["ep_radius"]
    return RT.lens_system(c, stop=2, field=20.0)


OUT = {}


def emit(name, drawing):
    """--out があれば SVG / DXF / PNG を書く(等倍で見る用)。図は常に PoC の Figures にも出す。"""
    OUT[name] = drawing
    if not REDUCED and figs.target_dir() is not None:
        figs.save(name, OD.drawing_raster(drawing, dpi=120), drawing["values"].get("caption", name))


# --------------------------------------------------------------------------- #
# 1. Cooke triplet
# --------------------------------------------------------------------------- #
def chapter_cooke():
    print("\n1. 教科書の Cooke triplet 2 本 —— 図から読み戻して、計算と公表値に突き合わせる")
    for key, sysf, pub in (("A", cooke_a, COOKE_A_EFL), ("B", cooke_b, COOKE_B_EFL)):
        system = sysf()
        para = RT.paraxial_trace(system)
        d = OD.lens_section_drawing(system, rays=5)
        emit("cooke_%s" % key.lower(), d)
        svg, dxf = OD.drawing_svg(d), OD.drawing_dxf(d)
        rs, rd = OD.svg_entities(svg)["entities"], OD.dxf_entities(dxf)["entities"]
        print("   処方 %s: EFL %.5f mm(公表 %g)、BFL %.4f、F/%.3f、像高 %.4f mm、要素 %d 個"
              % (key, para["efl"], pub, para["bfl"], para["fno"], d["values"]["image_height"], len(d["entities"])))
        NUMBERS["efl_%s" % key] = para["efl"]
        gate("処方 %s: EFL %.4f が公表値 %g と 1e-3 以内(硝材は現行の N- 品)" % (key, para["efl"], pub),
             abs(para["efl"] / pub - 1.0) < 1e-3, "相対差 %.1e" % abs(para["efl"] / pub - 1.0))
        for fmt, ents in (("SVG", rs), ("DXF", rd)):
            w, n = sag_residual(ents, system)
            gate("処方 %s %s: 面 %d 枚の座標が球面の sag の閉形式と < 1e-5 mm" % (key, fmt, n),
                 n == len(system["surfaces"]) and w < 1e-5, "最大 %.1e mm" % w)
            w, n = ray_on_surface_residual(ents, system)
            gate("処方 %s %s: 光線の折れ点 %d 個が面の上(閉形式)に < 1e-5 mm" % (key, fmt, n),
                 n > 0 and w < 1e-5, "最大 %.1e mm" % w)
        # 主光線 = raytrace.chief_ray(別経路: 近軸の入射瞳 + Newton の補正)
        worst = 0.0
        for j, f in enumerate(d["values"]["fields"]):
            cr = RT.chief_ray(system, field=f)
            tagged = [e for e in OD.svg_entities(svg)["entities"] if e.get("tag") == "ray:%d:2" % j]
            p = np.asarray(tagged[0]["points"])
            ref = np.asarray(cr["points"])[1:, [2, 1]]
            worst = max(worst, float(np.max(np.abs(p[1:] - ref))))
        gate("処方 %s: 図の主光線(3 視野)が raytrace.chief_ray と < 1e-6 mm" % key, worst < 1e-6, "最大 %.1e mm" % worst)
        ok = True
        detail = []
        for name, val in (("EFL", para["efl"]), ("BFL", para["bfl"]), ("OAL", d["values"]["total_track"]),
                          ("IMH", abs(d["values"]["image_height"]))):
            for ents in (rs, rd):
                got = dim_value(ents, name)
                ok &= got is not None and abs(got - val) <= 0.005 + 1e-9
            detail.append("%s %s" % (name, dim_value(rs, name)))
        gate("処方 %s: 寸法の数字(SVG と DXF)が paraxial_trace と表示の桁(0.01)で一致" % key, ok, ", ".join(detail))
        rows = [t for t in texts(rs) if re.match(r"S\d+ ", t)]
        bad = 0
        for i, s in enumerate(system["surfaces"]):
            toks = rows[i].split()
            if abs(float(toks[1]) - s["R"]) > 5e-5:
                bad += 1
            if s["t"] is not None and i < len(system["surfaces"]) - 1 and abs(float(toks[2]) - s["t"]) > 5e-5:
                bad += 1
        gate("処方 %s: 処方表の R と間隔が入力と 4 桁で一致" % key, bad == 0 and len(rows) == len(system["surfaces"]),
             "不一致 %d" % bad)
    return OUT


# --------------------------------------------------------------------------- #
# 2. テレセン 3 種
# --------------------------------------------------------------------------- #
def chapter_telecentric():
    print("\n2. テレセン 3 種の断面図 —— 入射瞳が無限遠でも、絞りを狙えば描ける")
    res = {}
    for kind in ("entocentric", "object", "bi"):
        L = TC.telecentric_lens(kind)
        d = OD.lens_section_drawing(L, fields=(0.0, 4.0, 8.0), rays=5)
        emit("telecentric_%s" % kind, d)
        ents = OD.svg_entities(OD.drawing_svg(d))["entities"]
        ch = [e for e in ents if e.get("tag") == "ray:2:2"][0]
        p = np.asarray(ch["points"])
        ang = math.degrees(math.atan2(p[1, 1] - p[0, 1], p[1, 0] - p[0, 0]))   # 物点 → 第 1 面
        ref = TC.chief_ray_angle(L, 8.0)["object_angle_deg"]
        res[kind] = (ang, ref)
        print("   %-11s 物高 8 mm の主光線の物体側の傾き: 図 %.6f°、telecentric.chief_ray_angle %.6f°" % (kind, ang, ref))
        gate("%s: 図の主光線の傾きが telecentric.chief_ray_angle(Newton 法)と < 1e-6°" % kind,
             abs(ang - ref) < 1e-6, "差 %.1e°" % abs(ang - ref))
    gate("テレセン 2 種は物高 8 mm で 0.06° 未満、通常は 1° 超",
         abs(res["object"][0]) < 0.06 and abs(res["bi"][0]) < 0.06 and abs(res["entocentric"][0]) > 1.0,
         "物体側 %.3f° / 両側 %.3f° / 通常 %.3f°" % (res["object"][0], res["bi"][0], res["entocentric"][0]))
    NUMBERS["tele_angle_object"] = res["object"][0]


# --------------------------------------------------------------------------- #
# 3. 撮像系の設置図
# --------------------------------------------------------------------------- #
def setups():
    sensor = OS.sensor_spec(pixel_um=3.45, resolution=(1024, 768))
    lens = OS.lens_spec(focal_mm=25.0, f_number=4.0, working_distance_mm=200.0)
    part = [OS.scene_box((0.0, 0.0, 4.0), (12.0, 8.0, 4.0))]
    return {
        "ring_coaxial": OS.vision_layout(sensor, lens, [OS.light_spec("ring", radius_mm=70.0, height_mm=60.0),
                                                        OS.light_spec("coaxial", radius_mm=30.0, height_mm=150.0)],
                                         scene=part),
        "dome": OS.vision_layout(sensor, lens, [OS.light_spec("dome", radius_mm=80.0, height_mm=70.0)], scene=part),
        "bar_lowangle": OS.vision_layout(sensor, lens, [OS.light_spec("bar", radius_mm=90.0, height_mm=25.0)],
                                         scene=part),
        "backlight": OS.vision_layout(sensor, lens, [OS.light_spec("backlight", radius_mm=40.0, height_mm=30.0, n=12)],
                                      scene=part),
    }


def chapter_setup():
    print("\n3. 撮像系の設置図 —— 視野の錐・作動距離・DOF・照明の角度を閉形式に突き合わせる")
    for name, lay in setups().items():
        d = OD.vision_setup_drawing(lay)
        emit("setup_%s" % name, d)
        ents = OD.svg_entities(OD.drawing_svg(d))["entities"]
        cam, lens = lay["camera"], lay["lens"]
        f, wd, N, px = lens["focal_mm"], lens["working_distance_mm"], lens["f_number"], lay["sensor"]["pixel_um"]
        w, h = lay["sensor"]["width"], lay["sensor"]["height"]
        m_thin = f / (wd - f)                          # 薄肉レンズを WD に合焦(図にもカメラにも頼らない)
        fov_w, fov_h = w * px * 1e-3 / m_thin, h * px * 1e-3 / m_thin
        # 視野の錐: 側面図の 4 本の線の作業面側の端
        ys = []
        for e in ents:
            if e.get("tag") == "side:fov_ray":
                (a, b) = e["points"]
                end = a if abs(a[1]) < abs(b[1]) else b
                ys.append((end[0], end[1]))
        yy = np.array([y for y, _ in ys])
        zz = np.array([z for _, z in ys])
        err = max(abs(yy.max() - fov_h / 2), abs(yy.min() + fov_h / 2), float(np.abs(zz).max()))
        gate("%s: 視野の錐が作業面で ±%.4f mm に届く(画素数 × 画素 / m、< 1e-6 mm)" % (name, fov_h / 2),
             len(ys) == 4 and err < 1e-6, "誤差 %.1e mm" % err)
        m = f / (wd - f)
        Nw = (1 + m) * N
        lam = 0.55
        dof = (2 * Nw * px + 2 * lam * Nw * Nw) / (m * m) / 1000.0
        got = {k: dim_value(ents, k) for k in ("WD", "FOV", "DOF")}
        fov_vals = sorted(float(mm.group(1)) for t in texts(ents) for mm in [re.fullmatch(r"FOV (\d+\.\d+)", t)] if mm)
        ok = (got["WD"] is not None and abs(got["WD"] - wd) <= 0.005 and got["DOF"] is not None
              and abs(got["DOF"] - dof) <= 0.0005 + 1e-9
              and all(min(abs(v - fov_w), abs(v - fov_h)) <= 0.005 for v in fov_vals) and len(fov_vals) == 3)
        gate("%s: WD・視野(3 本)・DOF の数字が閉形式と表示の桁で一致" % name, ok,
             "WD %s / FOV %s / DOF %s(閉形式 %.4f)" % (got["WD"], fov_vals, got["DOF"], dof))
        for li, L in enumerate(lay["lights"]):
            if L["kind"] in ("ring", "bar"):
                el = math.degrees(math.atan2(L["height_mm"], L["radius_mm"]))
                txt = [t for t in texts(ents) if re.fullmatch(r"\d+\.\d°", t)]
                gate("%s: 照明 %d(%s)の仰角の数字が atan(H/R) = %.2f° と一致" % (name, li + 1, L["kind"], el),
                     len(txt) >= 1 and abs(float(txt[0][:-1]) - el) <= 0.05 + 1e-9, "図 %s" % txt)
            if L["kind"] == "ring":
                rr = [e["r"] for e in ents if e["type"] == "circle" and e.get("tag", "").startswith("top:light%d" % li)]
                gate("%s: 上面図の円環(2 本の円)の中心の半径が R = %g" % (name, L["radius_mm"]),
                     len(rr) == 2 and abs(0.5 * sum(rr) - L["radius_mm"]) < 1e-9, "半径 %s" % rr)


# --------------------------------------------------------------------------- #
# 4. 単レンズの製作図
# --------------------------------------------------------------------------- #
def chapter_element():
    print("\n4. 単レンズの製作図(ISO 10110)—— 表の文字を処方と公表値と閉形式に突き合わせる")
    n = NBK7_ND
    cases = {"planoconvex": [{"R": 51.68, "t": 5.0, "n": GLASS_517642, "ap": 12.5}, {"R": math.inf, "t": None, "n": 1.0}],
             "biconvex": [{"R": 102.0, "t": 6.0, "n": GLASS_517642, "ap": 15.0}, {"R": -102.0, "t": None, "n": 1.0}]}
    for name, surf in cases.items():
        system = RT.lens_system(surf, stop=0)
        tol = {"radius_pct": 0.2, "thickness_mm": 0.05, "index": 0.0005, "tilt_deg": 0.05}
        d = OD.lens_element_drawing(system, tolerances=tol, trials=100, seed=1)
        emit("element_%s" % name, d)
        ents = OD.svg_entities(OD.drawing_svg(d))["entities"]
        T = texts(ents)
        R1, R2, t = surf[0]["R"], surf[1]["R"], surf[0]["t"]
        want_r = ["R %.3f CX  ±%.3f" % (abs(R1), abs(R1) * 0.002),
                  "R ∞" if R2 == math.inf else "R %.3f CX  ±%.3f" % (abs(R2), abs(R2) * 0.002)]
        gate("%s: R の文字 %s が処方と ±0.2 %% の公差どおり" % (name, want_r), all(w in T for w in want_r))
        gate("%s: 中心厚 %s±0.05 と外径 ⌀%.2f の文字" % (name, "%.2f" % t, d["values"]["outer_diameter"]),
             ("%.2f±0.05" % t) in T and ("⌀%.2f" % d["values"]["outer_diameter"]) in T)
        nd_txt = [x for x in T if x.startswith("n_d ")][0]
        vd_txt = [x for x in T if x.startswith("v_d ")][0]
        gate("%s: n_d・ν_d の文字がメーカー公表値 %.5f / %.2f と表示の桁で一致" % (name, NBK7_ND, NBK7_VD),
             abs(float(nd_txt.split()[1]) - NBK7_ND) <= 5e-6 and abs(float(vd_txt.split()[1]) - NBK7_VD) <= 0.005 + 1e-9,
             "%s / %s" % (nd_txt, vd_txt))
        # 厚肉レンズの公式(公表の n_d で)
        c1 = 1 / R1
        c2 = 0.0 if R2 == math.inf else 1 / R2
        efl = 1.0 / ((n - 1) * (c1 - c2 + (n - 1) * t * c1 * c2 / n))
        note = [x for x in T if x.startswith("3. EFL ")][0]
        got = float(note.split()[2])
        gate("%s: 注記の EFL %.3f が厚肉レンズの公式 %.4f と表示の桁で一致" % (name, got, efl), abs(got - efl) <= 0.0005 + 2e-4)
        mc = RT.tolerance_analysis(RT.lens_system([{"R": R1, "t": t, "n": GLASS_517642, "ap": 0.5 * d["values"]["clear_aperture"]},
                                                  {"R": R2, "t": None, "n": 1.0}], stop=0),
                                   tolerances=dict(tol, decenter_mm=0.0), trials=100, seed=1)
        mm = re.search(r"p5 (\d+\.\d+) / p95 (\d+\.\d+)", note)
        gate("%s: 注記の Monte-Carlo の EFL の幅が tolerance_analysis(同じ公差・種)と一致" % name,
             mm is not None and abs(float(mm.group(1)) - mc["efl"]["p5"]) <= 0.0005
             and abs(float(mm.group(2)) - mc["efl"]["p95"]) <= 0.0005, note)
        y = 0.5 * d["values"]["clear_aperture"]
        lam = 0.54607e-3
        fr = max(abs(sag_closed(R1 * (1 + s), 0.0, [y])[0] - sag_closed(R1, 0.0, [y])[0]) for s in (0.002, -0.002)) / (lam / 2)
        note5 = [x for x in T if x.startswith("5. ")][0]
        got_fr = float(re.search(r"R1 ±0\.2 % = (\d+(?:\.\d)?) FRINGES", note5).group(1))
        gate("%s: R1 の公差の縞の本数 %s が sag の差 / (λ/2) = %.2f の 0.5 刻みの丸め" % (name, got_fr, fr),
             abs(got_fr - max(0.5, round(fr * 2) / 2)) < 1e-9)
        NUMBERS["fringes_%s" % name] = fr


# --------------------------------------------------------------------------- #
# 5. 往復と第二の実装
# --------------------------------------------------------------------------- #
def chapter_roundtrip():
    print("\n5. 往復 —— 書いた SVG / DXF を読み戻すと同じ図に戻るか")
    worst = 0.0
    for name, d in OUT.items():
        for kind, back in (("SVG", OD.svg_entities(OD.drawing_svg(d))), ("DXF", OD.dxf_entities(OD.drawing_dxf(d)))):
            w, why = roundtrip_residual(d, back, by_layer=kind == "SVG")
            if not math.isfinite(w):
                print("   %s %s: %s" % (name, kind, why))
            worst = max(worst, w)
    gate("図 %d 枚 × SVG / DXF の往復で要素の型・層・文字が一致し、座標が < 1e-6 mm" % len(OUT), worst < 1e-6,
         "最大 %.1e mm" % worst)
    try:
        import ezdxf  # noqa: F401
        from ezdxf import recover
    except ImportError:
        print("   ezdxf が手元に無い。記録: %s" % (EZDXF_RECORDED or "(未記録)"))
        return
    import io
    doc, auditor = recover.read(io.BytesIO(OD.drawing_dxf(OUT["cooke_a"]).encode("ascii")))
    msp = doc.modelspace()
    n = len(list(msp))
    want = len(OUT["cooke_a"]["entities"])
    gate("第二の実装 ezdxf が DXF を読み、要素の数 %d が一致(監査のエラー %d)" % (n, len(auditor.errors)),
         n == want and not auditor.errors)


# --------------------------------------------------------------------------- #
# 6. 壊して確かめる
# --------------------------------------------------------------------------- #
def imaged_width_px(OSm, f=25.0, wd=200.0, pixel_um=13.8, width_mm=12.0):
    """撮った画像の上の部品の幅 [画素]: 薄い板(幅 *width_mm*)を ``layout_capture`` で撮り、中央の行の部品マスクを数える。"""
    sensor = OSm.sensor_spec(pixel_um=pixel_um, resolution=(256, 192))
    lens = OSm.lens_spec(focal_mm=f, f_number=4.0, working_distance_mm=wd)
    part = OSm.scene_box((0.0, 0.0, 0.05), (0.5 * width_mm, 4.0, 0.05))
    lay = OSm.vision_layout(sensor, lens, [OSm.light_spec("dome", radius_mm=80.0, height_mm=70.0, n=24)],
                            scene=[part])
    cap = OSm.layout_capture(lay, supersample=1, apply_diffraction=False)
    mask = np.asarray(cap["part_mask"], bool)
    return int(mask[mask.shape[0] // 2].sum()), width_mm * (f / (wd - f)) / (pixel_um * 1e-3), lay


def chapter_imaging_scale():
    print("\n3b. 撮った画像で倍率を測る —— 図にも計算にも頼らない経路")
    got, want, lay = imaged_width_px(OS)
    NUMBERS["imaged_px"] = got
    gate("幅 12 mm の板が撮った画像で %d 画素 = 幅 × m / 画素 = %.1f 画素(1 画素以内)" % (got, want),
         abs(got - want) <= 1.0, "m = f/(WD − f) = %.5f" % (25.0 / 175.0))
    gate("描くカメラの倍率(像距離 / 作動距離)がバジェットの倍率と一致",
         abs(lay["camera"]["image_distance_mm"] / lay["camera"]["working_distance_mm"]
             - lay["budget"]["magnification"]) < 1e-12)


def chapter_probes():
    print("\n6. 壊して確かめる —— 門が赤になるか")
    system = cooke_a()
    orig = OD._sag_profile
    try:
        OD._sag_profile = lambda s, y: -orig(s, y)
        bad = OD.lens_section_drawing(system, rays=5)
    except ValueError:
        bad = None
    finally:
        OD._sag_profile = orig
    if bad is not None:
        w, _ = sag_residual(OD.svg_entities(OD.drawing_svg(bad))["entities"], system)
        gate("sag の符号を反転した図は sag の門で赤(残差 > 1e-3 mm)", w > 1e-3, "残差 %.3g mm" % w)
    else:
        gate("sag の符号を反転した図は描画の段階で拒否された(縁の厚さが負)", True)
    d = OD.lens_section_drawing(system, rays=5)
    svg = OD.drawing_svg(d)
    ents = OD.svg_entities(svg)["entities"]
    ray = [e for e in ents if e.get("tag") == "ray:1:0"][0]
    z, y = ray["points"][2]
    s_svg = svg.replace("%s,%s" % (OD._f(z), OD._f(-y)), "%s,%s" % (OD._f(z + 0.01), OD._f(-y)), 1)
    w, _ = ray_on_surface_residual(OD.svg_entities(s_svg)["entities"], system)
    gate("光線の折れ点を 0.01 mm ずらした SVG は面の上の門で赤", s_svg != svg and w > 5e-3, "残差 %.3g mm" % w)
    efl_txt = "EFL %.2f" % d["values"]["efl"]
    s_svg = svg.replace(">%s<" % efl_txt, ">EFL %.2f<" % (d["values"]["efl"] + 0.1))
    got = dim_value(OD.svg_entities(s_svg)["entities"], "EFL")
    gate("EFL の数字を 0.1 書き換えた SVG は寸法の門で赤", s_svg != svg and abs(got - d["values"]["efl"]) > 0.005,
         "図 %s" % got)
    dxf = OD.drawing_dxf(d)
    k = dxf.index("\r\n  0\r\nVERTEX\r\n")
    k2 = dxf.index("\r\n  0\r\n", k + 4)
    cut = dxf[:k] + dxf[k2:]
    w, why = roundtrip_residual(d, OD.dxf_entities(cut))
    gate("VERTEX を 1 つ抜いた DXF は往復の門で赤", not math.isfinite(w) or w > 1e-6, why)
    try:
        OD.dxf_entities(dxf.replace("\r\n  0\r\nENDSEC\r\n  0\r\nEOF\r\n", "\r\n  0\r\nEOF\r\n"))
        gate("ENTITIES が閉じていない DXF は ValueError", False)
    except ValueError:
        gate("ENTITIES が閉じていない DXF は ValueError", True)
    # 2026-10-15 に直した混ざり(ピンホールの距離に焦点距離)を戻すと、視野の門と撮像の門が両方赤になるか
    orig_v = OS._thin_lens_image_distance
    try:
        OS._thin_lens_image_distance = lambda f, wd: float(f)
        lay = setups()["dome"]
        d = OD.vision_setup_drawing(lay)
        ents = OD.svg_entities(OD.drawing_svg(d))["entities"]
        f, wd = lay["lens"]["focal_mm"], lay["lens"]["working_distance_mm"]
        fov_h = lay["sensor"]["height"] * lay["sensor"]["pixel_um"] * 1e-3 * (wd - f) / f
        ys = [min(e["points"], key=lambda q: abs(q[1]))[0] for e in ents if e.get("tag") == "side:fov_ray"]
        err = max(abs(max(ys) - fov_h / 2), abs(min(ys) + fov_h / 2))
        gate("像距離を焦点距離に戻した設置図は、視野の門で赤(> 1e-3 mm)", err > 1e-3, "誤差 %.3f mm" % err)
        got, want, _ = imaged_width_px(OS)
        gate("同じく、撮った画像の板の幅が 1 画素を超えてずれる(撮像の門で赤)", abs(got - want) > 1.0,
             "%d 画素 vs %.1f 画素" % (got, want))
    finally:
        OS._thin_lens_image_distance = orig_v


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=None, help="図を SVG / DXF / PNG で書くディレクトリ(等倍で見る用)")
    args = ap.parse_args()
    t0 = time.time()
    print("PoC 光学系の図面(予算 %s)" % ("reduced" if REDUCED else "full"))
    chapter_cooke()
    chapter_telecentric()
    chapter_setup()
    chapter_imaging_scale()
    chapter_element()
    chapter_roundtrip()
    chapter_probes()
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        for name, d in OUT.items():
            with open(os.path.join(args.out, name + ".svg"), "w", encoding="utf-8") as fh:
                fh.write(OD.drawing_svg(d))
            with open(os.path.join(args.out, name + ".dxf"), "w", encoding="ascii", newline="") as fh:
                fh.write(OD.drawing_dxf(d))
            try:
                from PIL import Image
                Image.fromarray(OD.drawing_raster(d, dpi=25.4 * 6)).save(os.path.join(args.out, name + ".png"))
            except ImportError:
                pass
        print("\n図 %d 枚を %s に書いた(SVG は 100 %% 表示で縮尺どおり)" % (len(OUT), args.out))
    print("\n所要 %.1f s、門 %d 件中 NG %d 件" % (time.time() - t0, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
