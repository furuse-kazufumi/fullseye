# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 3D プリンタの層検査 ―― 形 → 層 → 経路 → 画像 の往復を自分で閉じ、仕込んだ欠陥を数字で捕まえる

3D プリンタのデータは「形(メッシュ)→ 層(スライス)→ 経路(G-code)→ 印刷中の層画像」と流れる。この往復が全部
Fullseye の既存語彙(mesh / voxel / table / image2d)で閉じるので、**真値を自分で仕込める**: 期待の層画像は G-code から
描け(``gcode_layer_image``)、観測の層画像には欠陥(欠け・はみ出し・層ずれ)を既知の場所に注入できる。

**主張(合成の真値で確かめる)**:
1. スライスは正確: 角穴つきの箱と、歯車状の柱(穴つき)を 0.2 mm で切った層マスクの面積が閉形式の真値と 1 % 以内、
   輪郭を周回する G-code の押し出し量は「周長 × 線幅 × 層厚 / フィラメント断面積」と一致し、G-code は読み書きで往復する。
2. 層検査: 観測の層画像に注入した欠陥(欠け 6 か所・はみ出し 6 か所、大きさ 1〜4 mm)を ``print_layer_defect_map`` が
   符号つきで捕まえる —— 位置ずれ許容 tolerance を振って精度・再現率の曲線を出し、0.3 mm(3 px)で再現率 ≥ 0.95 かつ
   偽陽性の面積 < 欠陥面積の 5 %。0.2 mm の全体ずれ(カメラの位置ずれ)を足すと tolerance 3 px で再現率は約 0.9 に落ちる
   (ずれの分だけ欠陥の縁を許容に食われる —— 正直に曲線で出す)、偽陽性は欠陥面積の 10 % 未満。
3. 3MF: 書いて読んで頂点・面が一致する。

図:
1. ``slice_stack``: 層マスクの積みを立体に(videocube の ``vol_render_transfer``、高さの色)。
2. ``layers``: 期待の層画像 / 欠陥を注入した観測 / 符号つきの欠陥図(+ = 欠け、− = はみ出し)。
3. ``tolerance_curve``: 許容 px を振ったときの精度・再現率(ずれ無し / 0.2 mm ずれ)。
4. ``numbers``: 数字の表(押し出し体積、所要時間、層数、検出率)。

走らせ方: ``py -3.11 examples/poc_print_layer_inspection.py``(図は ``out/figures/poc_print_layer_inspection/``)。
"""
from __future__ import annotations

import os
import sys
import tempfile
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
LAYER_MM = 0.2
LINE_MM = 0.4
PX_PER_MM = 10.0
FIL_AREA = np.pi * (1.75 / 2) ** 2


def box_mesh(x0, y0, z0, x1, y1, z1, flip=False):
    V = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0], [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], float)
    F = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
    return V, (F[:, ::-1] if flip else F)


def prism_mesh(poly, z0, z1, flip=False):
    """2-D 多角形(反時計回り)を z0..z1 に押し出した柱(側面 + 上下の扇)。"""
    n = len(poly)
    c = poly.mean(axis=0)
    V = np.vstack([np.column_stack([poly, np.full(n, z0)]), np.column_stack([poly, np.full(n, z1)]),
                   [[c[0], c[1], z0]], [[c[0], c[1], z1]]])
    F = []
    for i in range(n):
        j = (i + 1) % n
        F += [[i, j, n + j], [i, n + j, n + i]]                              # 側面(外向き)
        F += [[2 * n, j, i], [2 * n + 1, n + i, n + j]]                      # 底(下向き)と上(上向き)
    F = np.array(F)
    return V, (F[:, ::-1] if flip else F)


def gear_polygon(r_out=9.0, r_in=7.5, teeth=8, n_per=6):
    ang = np.linspace(0.0, 2 * np.pi, teeth * n_per, endpoint=False)
    r = np.where((np.arange(teeth * n_per) % n_per) < n_per // 2, r_out, r_in)
    return np.column_stack([r * np.cos(ang), r * np.sin(ang)])


def parts():
    """(名前, mesh, 真値の層面積 mm²)。"""
    V1, F1 = box_mesh(0, 0, 0, 20, 10, 6)
    V2, F2 = box_mesh(8, 3, -1, 12, 7, 7, flip=True)
    box = (np.vstack([V1, V2]), np.vstack([F1, F2 + 8]))
    poly = gear_polygon()
    area_poly = 0.5 * abs(np.sum(poly[:, 0] * np.roll(poly[:, 1], -1) - np.roll(poly[:, 0], -1) * poly[:, 1]))
    hole = np.column_stack([3.0 * np.cos(np.linspace(0, 2 * np.pi, 48, endpoint=False)), 3.0 * np.sin(np.linspace(0, 2 * np.pi, 48, endpoint=False))])
    area_hole = 0.5 * abs(np.sum(hole[:, 0] * np.roll(hole[:, 1], -1) - np.roll(hole[:, 0], -1) * hole[:, 1]))
    Vg, Fg = prism_mesh(poly + 30.0, 0, 4)
    Vh, Fh = prism_mesh(hole + 30.0, -1, 5, flip=True)
    gear = (np.vstack([Vg, Vh]), np.vstack([Fg, Fh + len(Vg)]))
    return [("box with a square hole", box, 200.0 - 16.0), ("gear-like boss with a round hole", gear, area_poly - area_hole)]


def inject_defects(img, rng, n_missing=6, n_extra=6, px_per_mm=PX_PER_MM):
    """観測画像を作る: 欠け(経路の上の矩形を消す)とはみ出し(経路の外に塊を足す)。真値マスクを返す。"""
    H, W = img.shape
    obs = img.copy()
    truth = np.zeros((H, W))
    ys, xs = np.nonzero(img > 0.5)
    for _ in range(n_missing):
        k = rng.integers(len(ys))
        h, w = int(rng.uniform(1.0, 4.0) * px_per_mm), int(rng.uniform(1.0, 4.0) * px_per_mm)
        y0, x0 = max(0, ys[k] - h // 2), max(0, xs[k] - w // 2)
        region = (slice(y0, min(H, y0 + h)), slice(x0, min(W, x0 + w)))
        truth[region][obs[region] > 0.5] = 1.0
        obs[region] = 0.0
    for _ in range(n_extra):
        while True:
            y0, x0 = rng.integers(0, H - 40), rng.integers(0, W - 40)
            h, w = int(rng.uniform(1.0, 4.0) * px_per_mm), int(rng.uniform(1.0, 4.0) * px_per_mm)
            region = (slice(y0, min(H, y0 + h)), slice(x0, min(W, x0 + w)))
            if img[region].max() < 0.5:
                break
        obs[region] = 1.0
        truth[region] = -1.0
    return obs, truth


def score(defect_map, truth):
    """検出の精度・再現率(画素、符号も一致で正解)。"""
    hit = (defect_map != 0) & (np.sign(defect_map) == np.sign(truth)) & (truth != 0)
    tp = float(hit.sum())
    fp = float(((defect_map != 0) & (truth == 0)).sum())
    fn = float(((truth != 0) & ~hit).sum())
    prec = tp / max(tp + fp, 1.0)
    rec = tp / max(tp + fn, 1.0)
    return prec, rec, fp


def main() -> int:
    t0 = time.time()
    L = fs.ledger
    rng = np.random.default_rng(0)
    rows = []
    tmp = tempfile.mkdtemp(prefix="fullseye_print_")
    stacks, layer_imgs, meshes = [], [], []
    for name, mesh, area_true in parts():
        stack = L.mesh_slice_stack(mesh, layer_mm=LAYER_MM, px_per_mm=PX_PER_MM)
        mid = stack.shape[0] // 2
        area = float(stack[mid].sum()) / PX_PER_MM ** 2
        print("%-34s layers %3d  mid-layer area %.2f mm² (truth %.2f, %.2f %%)" % (name, stack.shape[0], area, area_true, 100 * abs(area - area_true) / area_true))
        assert abs(area - area_true) / area_true < 0.01, (name, area, area_true)
        rows.append(("slice area, %s (mm²)" % name, "%.2f" % area, "%.2f (< 1 %%)" % area_true))
        # 全層の G-code を 1 本に
        segs = []
        z0 = float(mesh[0][:, 2].min())
        for k in range(stack.shape[0]):
            zc = z0 + (k + 0.5) * LAYER_MM
            try:
                c = L.mesh_slice_contours(mesh, zc)
            except ValueError:
                continue
            segs.append(L.contours_to_gcode(c, zc, layer=k, layer_mm=LAYER_MM, line_width_mm=LINE_MM))
        table = {col: np.concatenate([s[col] for s in segs]) for col in segs[0]}
        path = L.gcode_write(table, os.path.join(tmp, "%s.gcode" % name.split()[0]))
        back = L.gcode_read(path)
        assert abs(back["e"].sum() - table["e"].sum()) < 1e-5 and int((back["e"] > 0).sum()) == int((table["e"] > 0).sum())
        vol, tsec = L.gcode_extrusion_volume(back), L.gcode_time_estimate(back)
        # 押し出し量の閉形式: 各層の周長 × 線幅 × 層厚
        c_mid = L.mesh_slice_contours(mesh, z0 + (mid + 0.5) * LAYER_MM)
        perim = 0.0
        for r in np.unique(c_mid["ring"]):
            P = np.column_stack([c_mid["x"][c_mid["ring"] == r], c_mid["y"][c_mid["ring"] == r]])
            perim += float(np.sum(np.hypot(*(np.roll(P, -1, axis=0) - P).T)))
        e_mid = float(table["e"][table["layer"] == mid].sum())
        assert abs(e_mid - perim * LINE_MM * LAYER_MM / FIL_AREA) < 1e-9
        print("   G-code: %d moves, extruded %.1f mm³, lower-bound time %.0f s, round trip ok, mid-layer E = perimeter x width x height / filament area" % (len(back["e"]), vol, tsec))
        rows.append(("G-code %s: moves / volume mm³ / time s" % name.split()[0], "%d / %.1f / %.0f" % (len(back["e"]), vol, tsec), "-"))
        p3 = L.write_3mf(os.path.join(tmp, "part.3mf"), mesh)
        V2, F2 = L.read_3mf(p3)
        assert np.allclose(V2, mesh[0]) and np.array_equal(F2, mesh[1])
        stacks.append((name, stack))
        meshes.append(mesh)
        layer_imgs.append((name, back, mid))

    # 層検査 ------------------------------------------------------------------
    name, back, mid = layer_imgs[1]
    expected = L.gcode_layer_image(back, mid, px_per_mm=PX_PER_MM, line_width_mm=LINE_MM)
    observed, truth = inject_defects(expected, rng)
    curve = []
    for tol in (0, 1, 2, 3, 4, 6):
        d = L.print_layer_defect_map(observed, expected, tolerance_px=tol)
        prec, rec, fp = score(d, truth)
        curve.append((tol, prec, rec))
        print("tolerance %d px: precision %.3f recall %.3f (false-positive px %d of %d defect px)" % (tol, prec, rec, fp, int((truth != 0).sum())))
    d3 = L.print_layer_defect_map(observed, expected, tolerance_px=3)
    prec3, rec3, fp3 = score(d3, truth)
    assert rec3 >= 0.95 and fp3 < 0.05 * (truth != 0).sum(), (prec3, rec3, fp3)
    rows.append(("defect detection at 3 px: precision / recall", "%.3f / %.3f" % (prec3, rec3), "recall >= 0.95, FP < 5 %"))
    # カメラの位置ずれ 0.2 mm(2 px)
    shifted = np.roll(np.roll(observed, 2, axis=0), 1, axis=1)
    truth_s = np.roll(np.roll(truth, 2, axis=0), 1, axis=1)
    curve_s = []
    for tol in (0, 1, 2, 3, 4, 6):
        d = L.print_layer_defect_map(shifted, expected, tolerance_px=tol)
        prec, rec, fp = score(d, truth_s)
        curve_s.append((tol, prec, rec, fp))
    ds = L.print_layer_defect_map(shifted, expected, tolerance_px=3)
    precs, recs, fps = score(ds, truth_s)
    print("with a 0.2 mm camera shift, tolerance 3 px: precision %.3f recall %.3f (FP px %d)" % (precs, recs, fps))
    assert fps < 0.10 * (truth != 0).sum() and recs >= 0.85, (precs, recs, fps)   # ずれの分だけ欠陥の縁を落とす(正直に)
    rows.append(("same with a 0.2 mm camera shift: precision / recall", "%.3f / %.3f" % (precs, recs), "FP < 10 %, recall >= 0.85"))

    if figs.enabled():
        name0, stack0 = stacks[1]
        zz = np.linspace(0.0, 1.0, stack0.shape[0])[:, None, None] * np.ones_like(stack0)
        img = L.vol_render_transfer(stack0, color=zz, yaw=35.0, pitch=25.0, size=256 if REDUCED else 320, depth_samples=64)
        figs.save("slice_stack", img, caption="%s sliced at %.1f mm into %d layer masks (mesh_slice_stack) and rendered as a solid, grey = height" % (name0, LAYER_MM, stack0.shape[0]))
        figs.save_grid("layers", [expected, observed, d3], captions=["expected (gcode_layer_image)", "observed (6 gaps + 6 blobs injected)", "defect map: +1 missing / -1 extra (3 px)"],
                       ncols=3, signed=[False, False, True], gray=[True, True, False],
                       caption="one layer of the gear-like part: the expected raster from the G-code, the observed image with injected defects, and the signed defect map")
        tols = np.array([c[0] for c in curve], dtype=float)
        figs.save_plot("tolerance_curve", [("precision", tols, np.array([c[1] for c in curve])), ("recall", tols, np.array([c[2] for c in curve])),
                                           ("precision, 0.2 mm shift", tols, np.array([c[1] for c in curve_s])), ("recall, 0.2 mm shift", tols, np.array([c[2] for c in curve_s]))],
                       xlabel="tolerance (px, 10 px = 1 mm)", ylabel="score", title="how much misalignment the check forgives",
                       caption="precision and recall of the defect map against the injected truth as the tolerance grows, without and with a 0.2 mm camera shift: a small tolerance absorbs the shift without hiding millimetre-size defects")
        figs.save_table("numbers", ["quantity", "value", "bar"], rows, title="print layer inspection numbers", caption="every number with the bar it had to clear")
        assert not figs.errors(), figs.errors()
    print("elapsed %.0fs" % (time.time() - t0))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
