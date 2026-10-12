# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""gallery_drive_japan_roads — 日本の道の部品(標識・信号機・電柱・踏切警標・カーブミラー・「止まれ」)を寸法で確かめる

    py -3.11 examples/gallery_drive_japan_roads.py

【平たく言うと】
運転の世界に置く日本の道の部品は、見た目が「それっぽい」だけでは足りない。標識の一辺、灯器の幅、
レンズの並び(運転者から見て左から青・黄・赤)、表示面がどちらを向くか —— これを取り違えると、
カメラで読む側の門が嘘の合格を出す。ここでは drivejapan と roadjp の op 10 本を、出典つきの寸法・
閉形式の面積・メッシュの不変量(AABB・頂点数・面の向き)で 1 本ずつ確かめる。

【何を期待し、何と比べるか】
  * jp_stop_marking_length : 「止まれ」3 字 = 3 × 字高 2.4 m + 2 × 字間 1.0 m = 9.2 m(警察庁「交通規制基準」図例)。
  * jp_pole_mesh           : 円柱 10 角 + 腕金の箱 = 頂点 28・面 40、AABB = 腕金の 1.8 m と高さ、腕金は頂上の 1 m 下。
  * jp_crossbuck_mesh      : × 印は 45° に傾いた 1.2 × 0.16 m の板 → 上端 = 中心 + (arm/2 + w/2)·sin45°(閉形式)。
  * jp_mirror_mesh         : 鏡の頂点は (y, z) = (0, height) を中心とする半径 r の円の上、AABB の上端 = height + r。
  * sign_params            : 円 直径 0.6 m、逆三角形 一辺 0.6 m(高さ = 一辺·√3/2)、菱形 一辺 0.45 m(対角 = 一辺·√2)、
                             板の下端 1.8 m(roadjp の docstring が引く「道路標識、区画線及び道路標示に関する命令」別表第二)。
  * sign_image             : 円の標識の alpha の平均 = π/4、菱形 = 1/2(面積比の閉形式)。
  * plate_mesh_from_image  : 手で作った 8×12 の RGBA → 面の数・頂点数・面積・α 重みの平均色・表面の向き(−x)が閉形式どおり。
  * sign_mesh              : 「車両進入禁止」の板の表面積 ≈ π·0.3²(区画で近似するので 3 % 以内)、AABB は 0.6 m 四方。
  * signal_jp_mesh         : 幅 = 3·(0.30 + 0.10) + 0.05 = 1.25 m、高さ 0.43 m、青が +y・赤が −y、点灯は state の灯だけ。
  * add_signal_jp          : 灯器の底 = lamp_bottom、アームの先 = 柱から運転者の右へ arm、表示面の法線 = (−cos yaw, −sin yaw)。
                             灯器の底 4.5 m 未満は拒む(公表値の下限)。

正直に: 寸法の多くは op の docstring が「一次資料で要確認」としている公表値で、この例が確かめるのは
「op が docstring の値どおりの形を作るか」まで。規格そのものの正しさではない。文字を含む標識(止まれ・徐行・
速度規制)は PIL のフォントに依存するので、この例では文字の無い標識(円・菱形)だけを使う。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import drivecourse  # noqa: E402
import drivejapan as DJ  # noqa: E402
import driveworld as DW  # noqa: E402
import roadjp as RJ  # noqa: E402

_ROWS = []


def check(op, what, expected, got, ok):
    """1 行 = 何を期待し、何が出て、合ったか。"""
    _ROWS.append((op, bool(ok)))
    print("  %-22s %-46s 期待 %-24s 実測 %-24s %s" % (op, what, expected, got, "ok" if ok else "NG"))


def _normals(V, F):
    return np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])


def _area(V, F):
    return float(0.5 * np.linalg.norm(_normals(V, F), axis=1).sum())


def part_street_furniture():
    print("== 1. 路上の構造物(drivejapan)")
    L = DJ.jp_stop_marking_length()
    check("jp_stop_marking_length", "3 × 字高 2.4 + 2 × 字間 1.0", "9.2 m", "%.12g m" % L, abs(L - 9.2) < 1e-12)

    V, F, C = DJ.jp_pole_mesh(height=10.0, r=0.17)
    check("jp_pole_mesh", "頂点数・面数・面色数(円柱 10 角 + 箱)", "28・40・40", "%d・%d・%d" % (len(V), len(F), len(C)),
          (len(V), len(F), len(C)) == (28, 40, 40))
    lo, hi = V.min(axis=0), V.max(axis=0)
    check("jp_pole_mesh", "AABB(腕金 1.8 m・半径 0.17・高さ 10)", "[±0.17, ±0.9, 0..10]",
          "[%.2f, %.2f, %.2f..%.2f]" % (hi[0], hi[1], lo[2], hi[2]),
          np.allclose(lo, [-0.17, -0.9, 0.0]) and np.allclose(hi, [0.17, 0.9, 10.0]))
    wide = V[np.abs(V[:, 1]) > 0.5]                       # 腕金の頂点(柱の半径より外)
    check("jp_pole_mesh", "腕金の高さ = 頂上の 1 m 下 〜 0.9 m 下", "9.0..9.1 m",
          "%.2f..%.2f m" % (wide[:, 2].min(), wide[:, 2].max()),
          np.isclose(wide[:, 2].min(), 9.0) and np.isclose(wide[:, 2].max(), 9.1))
    V8, _, _ = DJ.jp_pole_mesh(height=8.0)
    check("jp_pole_mesh", "height = 8 なら上端も 8", "8 m", "%.12g m" % V8[:, 2].max(), V8[:, 2].max() == 8.0)

    V, F, C = DJ.jp_crossbuck_mesh(arm=1.2, height=3.0)
    reach = (0.6 + 0.08) * math.sin(math.pi / 4)
    check("jp_crossbuck_mesh", "× の上端 = (h − 0.3) + (arm/2 + w/2)·sin45°", "%.6f m" % (2.7 + reach),
          "%.6f m" % V[:, 2].max(), abs(V[:, 2].max() - (2.7 + reach)) < 1e-12)
    check("jp_crossbuck_mesh", "× は左右対称(y の幅 ±)", "±%.6f m" % reach,
          "%.6f / %.6f" % (V[:, 1].min(), V[:, 1].max()), abs(V[:, 1].max() - reach) < 1e-12
          and abs(V[:, 1].min() + reach) < 1e-12)
    board = np.all(np.isclose(C, (0.98, 0.80, 0.08)), axis=1) | np.all(np.isclose(C, (0.08, 0.08, 0.08)), axis=1)
    xs = sorted(set(np.round(V[F[board]][:, :, 0], 9).ravel().tolist()))
    nb = _normals(V, F[board])
    check("jp_crossbuck_mesh", "黄・黒の板は x 一定の面(法線 ±x)", "x ∈ {0.02, 0.035}", str(xs),
          xs == [0.02, 0.035] and np.allclose(nb[:, 1:], 0.0) and int(board.sum()) == 16)

    V, F, C = DJ.jp_mirror_mesh(height=2.7, r=0.3)
    mirror = np.all(np.isclose(C, (0.80, 0.84, 0.90)), axis=1)
    mv = V[np.unique(F[mirror])]
    rad = np.hypot(mv[:, 1], mv[:, 2] - 2.7)
    check("jp_mirror_mesh", "鏡の頂点は中心 (0, 2.7) の半径 0.3 の円の上", "0.3 m",
          "%.6f..%.6f m" % (rad.min(), rad.max()), np.allclose(rad, 0.3, atol=1e-12))
    check("jp_mirror_mesh", "AABB の上端 = height + r", "3.0 m", "%.12g m" % V[:, 2].max(), abs(V[:, 2].max() - 3.0) < 1e-12)


def part_signs():
    print("== 2. 標識(roadjp)")
    sp = RJ.sign_params("no_entry")
    check("sign_params", "円(車両進入禁止)の直径", "0.6 × 0.6 m", "%.3g × %.3g m" % (sp["width"], sp["height"]),
          sp["shape"] == "circle" and sp["width"] == 0.6 and sp["height"] == 0.6)
    st = RJ.sign_params("stop")
    check("sign_params", "逆三角形(一時停止)の高さ = 一辺·√3/2", "%.6f m" % (0.6 * math.sqrt(3) / 2),
          "%.6f m" % st["height"], st["shape"] == "triangle_down" and abs(st["height"] - 0.6 * math.sqrt(3) / 2) < 1e-12)
    st8 = RJ.sign_params("stop", side=0.8)
    check("sign_params", "side = 0.8 で一辺を置き換える", "0.8 × %.6f" % (0.8 * math.sqrt(3) / 2),
          "%.3g × %.6f" % (st8["width"], st8["height"]), st8["width"] == 0.8
          and abs(st8["height"] - 0.8 * math.sqrt(3) / 2) < 1e-12)
    dm = RJ.sign_params("caution_signal")
    check("sign_params", "菱形(信号機あり)の対角 = 0.45·√2", "%.6f m" % (0.45 * math.sqrt(2)), "%.6f m" % dm["width"],
          dm["shape"] == "diamond" and abs(dm["width"] - 0.45 * math.sqrt(2)) < 1e-12)
    check("sign_params", "路側式の板の下端", "1.8 m", "%.3g m" % sp["mount_height"], sp["mount_height"] == 1.8)
    bad = False
    try:
        RJ.sign_params("no_such_sign")
    except ValueError:
        bad = True
    check("sign_params", "未知の kind は拒む", "ValueError", "ValueError" if bad else "通った", bad)

    circ = RJ.sign_image("no_entry", size_px=128)
    dia = RJ.sign_image("caution_signal", size_px=128)
    a_c, a_d = float(circ[..., 3].mean()), float(dia[..., 3].mean())
    check("sign_image", "円の alpha の平均 = π/4", "%.4f" % (math.pi / 4), "%.4f" % a_c, abs(a_c - math.pi / 4) < 0.01)
    check("sign_image", "菱形の alpha の平均 = 1/2", "0.5000", "%.4f" % a_d, abs(a_d - 0.5) < 0.01)
    red = np.array(RJ.SIGN_COLORS["red"])
    top = circ[12, 64, :3]                                # 円の上の方は赤地(白の横棒は中央)
    mid = circ[64, 64, :3]
    check("sign_image", "車両進入禁止: 上は赤地・中央は白の横棒", "赤 / 白",
          "%s / %s" % (np.round(top, 2).tolist(), np.round(mid, 2).tolist()),
          np.allclose(top, red, atol=0.02) and mid.min() > 0.9 and circ.shape == (128, 128, 4))

    m = RJ.sign_mesh("no_entry")
    f0, f1 = m["front_faces"]
    Af = _area(m["V"], m["F"][f0:f1])
    want = math.pi * 0.3 ** 2
    check("sign_mesh", "表面の面積 ≈ π·0.3²(区画近似)", "%.4f m²" % want, "%.4f m²" % Af, abs(Af / want - 1) < 0.03)
    lo, hi = m["V"].min(axis=0), m["V"].max(axis=0)
    check("sign_mesh", "AABB の y・z 幅 ≤ 0.6 m(板の外形)", "≤ 0.6 × 0.6",
          "%.3f × %.3f" % (hi[1] - lo[1], hi[2] - lo[2]), hi[1] - lo[1] <= 0.6 + 1e-12 and hi[2] - lo[2] <= 0.6 + 1e-12
          and hi[1] - lo[1] > 0.55)


def part_plate():
    print("== 3. 画像 → 板のメッシュ(閉形式の入力)")
    img = np.zeros((8, 12, 4))
    img[..., :3] = (0.2, 0.6, 0.2)
    img[..., 3] = 1.0
    img[4:8, 8:12, 3] = 0.0                               # 区画 (1, 2) は透明 → 面にしない
    img[0:4, 0:2, :3] = (1.0, 0.0, 0.0)                   # 区画 (0, 0) の左半分は赤 α 1、右半分は青 α 0.5
    img[0:4, 2:4, :3] = (0.0, 0.0, 1.0)
    img[0:4, 2:4, 3] = 0.5
    m = RJ.plate_mesh_from_image(img, 0.3, 0.2, cell=4, thickness=0.004)
    nF = len(m["F"])
    check("plate_mesh_from_image", "面 = 5 区画 × 2 三角形 × 表裏", "20", str(nF), nF == 20 and m["cells"] == (2, 3))
    check("plate_mesh_from_image", "頂点 = 使う格子点 11 × 表裏", "22", str(len(m["V"])), len(m["V"]) == 22)
    f0, f1 = m["front_faces"]
    Af = _area(m["V"], m["F"][f0:f1])
    check("plate_mesh_from_image", "表面の面積 = 5 × 0.1 × 0.1", "0.05 m²", "%.12g m²" % Af, abs(Af - 0.05) < 1e-12)
    nrm = _normals(m["V"], m["F"][f0:f1])
    check("plate_mesh_from_image", "表面の法線は −x を向く", "全部 −x", "%d / %d" % ((nrm[:, 0] < 0).sum(), len(nrm)),
          bool(np.all(nrm[:, 0] < 0)) and np.allclose(nrm[:, 1:], 0))
    c00 = m["color"][0]
    want = np.array([2.0 / 3.0, 0.0, 1.0 / 3.0])          # (1·赤·8 + 0.5·青·8) / (8 + 4)
    check("plate_mesh_from_image", "区画 (0,0) の色 = α 重みの平均", "(0.667, 0, 0.333)",
          "(%.3f, %.3f, %.3f)" % tuple(c00), np.allclose(c00, want, atol=1e-12))
    left = m["V"][m["F"][0]][:, 1].max()
    check("plate_mesh_from_image", "画像の左 = +y(区画 (0,0) の左端 y = 幅/2)", "0.15 m", "%.12g m" % left,
          abs(left - 0.15) < 1e-12)


def part_signal():
    print("== 4. 信号機(roadjp)")
    h = RJ.signal_jp_mesh(lens=0.30, n=3, state="red")
    check("signal_jp_mesh", "灯器の幅・高さ(3 灯・300 mm)", "1.25 × 0.43 m", "%.4g × %.4g m" % (h["width"], h["height"]),
          abs(h["width"] - 1.25) < 1e-12 and abs(h["height"] - 0.43) < 1e-12)
    cy = {k: float(h["V"][np.unique(h["F"][a:b])][:, 1].mean()) for k, (a, b) in h["lamp_faces"].items()}
    check("signal_jp_mesh", "−x を向いて左から青・黄・赤(青 +y・赤 −y)", "+0.4 / 0 / −0.4",
          "%+.2f / %+.2f / %+.2f" % (cy["green"], cy["yellow"], cy["red"]),
          np.isclose(cy["green"], 0.4) and np.isclose(cy["yellow"], 0.0) and np.isclose(cy["red"], -0.4))
    lit = {k: tuple(h["color"][a]) for k, (a, b) in h["lamp_faces"].items()}
    check("signal_jp_mesh", "点灯は state = red の灯だけ", "赤だけ点灯",
          "赤 %s・青 %s" % (np.round(lit["red"], 2).tolist(), np.round(lit["green"], 2).tolist()),
          np.allclose(lit["red"], DW._LAMP["red"]) and np.allclose(lit["green"], DW._LAMP["off"])
          and np.allclose(lit["yellow"], DW._LAMP["off"]))
    a, b = h["lamp_faces"]["red"]
    nrm = _normals(h["V"], h["F"][a:b])
    check("signal_jp_mesh", "レンズの法線は −x(表示面の向き)", "全部 −x", "%d / %d" % ((nrm[:, 0] < 0).sum(), len(nrm)),
          bool(np.all(nrm[:, 0] < 0)))

    world = DW.world_build(drivecourse.course_road(length=60.0, width=7.0))
    for yaw in (0.0, math.pi / 2):
        i = RJ.add_signal_jp(world, 30.0, 3.5, yaw, state="green", arm=2.0, lamp_bottom=5.0)
        obj = world["objects"][i]
        v0, v1 = obj["verts"]
        Vh = world["V"][v0:v1]
        a, b = obj["lamp_faces"]["green"]
        nrm = _normals(world["V"], world["F"][a:b])
        nrm = nrm / np.linalg.norm(nrm, axis=1, keepdims=True)
        want_n = np.array([-math.cos(yaw), -math.sin(yaw), 0.0])
        # 柱の局所系(x = 表示面の裏向き、y = 運転者の左)に戻して、灯器の左右の中点 = −arm(運転者の右へ 2 m)
        c, s_ = math.cos(yaw), math.sin(yaw)
        ly = -s_ * (Vh[:, 0] - 30.0) + c * (Vh[:, 1] - 3.5)
        mid = 0.5 * (ly.min() + ly.max())
        tag = "yaw %d°" % round(math.degrees(yaw))
        check("add_signal_jp", "%s: 灯器の底 = lamp_bottom" % tag, "5.0 m", "%.12g m" % Vh[:, 2].min(),
              abs(Vh[:, 2].min() - 5.0) < 1e-9)
        check("add_signal_jp", "%s: 表示面の法線 (−cos, −sin)" % tag, "(%.0f, %.0f)" % tuple(want_n[:2]),
              "(%.3f, %.3f)" % tuple(nrm.mean(axis=0)[:2]), np.allclose(nrm, want_n, atol=1e-9))
        check("add_signal_jp", "%s: 灯器の左右の中点 = 柱から右へ 2 m" % tag, "−2 m",
              "%+.12g m" % mid, abs(mid + 2.0) < 1e-9)
        check("add_signal_jp", "%s: 世界の点灯面の色 = 青" % tag, "green",
              str(np.round(world["face_color"][a], 2).tolist()), np.allclose(world["face_color"][a:b], DW._LAMP["green"]))
    low = False
    try:
        RJ.add_signal_jp(world, 0.0, 0.0, 0.0, lamp_bottom=4.0)
    except ValueError:
        low = True
    check("add_signal_jp", "灯器の底 4.0 m(< 4.5 m)は拒む", "ValueError", "ValueError" if low else "通った", low)


def run():
    t0 = time.perf_counter()
    part_street_furniture()
    part_signs()
    part_plate()
    part_signal()
    return time.perf_counter() - t0


if __name__ == "__main__":
    sec = run()
    ng = [op for op, ok in _ROWS if not ok]
    print("japan roads: %d op / %d 検査 / NG %d / %.2f s" % (len({op for op, _ in _ROWS}), len(_ROWS), len(ng), sec))
    if ng:
        print("FAILED:", sorted(set(ng)))
        raise SystemExit(1)
    print("PASS")
