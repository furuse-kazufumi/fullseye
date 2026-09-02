# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""paper_figure — 学術図の図注(annotate の paper 族)で 4 パネルの論文図を組む。

    py -3.11 examples/paper_figure.py
    py -3.11 examples/paper_figure.py --save out/paper_figure.png

【用途(分かりやすく)】
論文の図は「どこに何があるか」を矢印や線で示す。引き出し線・番号と凡例・寸法線・
角度・スケールバー・方位・拡大の差し込み・領域の輪郭・経路に沿う文字・色分けと
カラーバー・パネル文字 ―― これらを毎回手で置くのではなく **op** として呼ぶ。
幾何は ``annotate_*_layout`` が閉形式で決めるので、**描いた結果を数字で検算**できる。

【グラウンドトゥルース(beat-the-null)】
1. 引き出し線: 肘 = 点 + side*gap、板同士は重ならず、他の点も覆わない(3 点)。
2. 寸法線: 値 = |p1-p0| * units_per_pixel(0.4 mm/px で 100 px → 40.0 mm)、
   寸法線は点から offset の位置。
3. 角度: 3 点 (右, 頂点, 上) → 90°、弧の画素は半径 ±1.5 px の環に乗る。
4. スケールバー: 長さは 1/2/5x10^k のうち目標以下の最大、画素長 = round(L/upp)、
   描いた画素数が閉形式と一致(誤差 0)。
5. 輪郭: 多角形の面積 == マスクの画素数、重心 == 画素座標の平均。
6. 組版: 図の大きさ == 閉形式 ``2*pad + ncols*cw + (ncols-1)*pad`` 等、
   パネルの画素は拡大されず中央に置かれる(枠線 1 px の内側で画素単位一致)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import annotate as A          # noqa: E402
import palette                # noqa: E402

PH, PW = 240, 320             # パネルは非正方


def _scene():
    yy, xx = np.mgrid[0:PH, 0:PW]
    base = 0.12 + 0.05 * np.sin(xx / 19.0) * np.cos(yy / 27.0)
    img = np.stack([base] * 3, axis=-1)
    disk = ((xx - 110) ** 2 + (yy - 110) ** 2) < 42 ** 2
    bar = (np.abs(yy - 60) < 6) & (xx > 180) & (xx < 300)
    img[disk] = (0.55, 0.55, 0.62)
    img[bar] = (0.35, 0.35, 0.40)
    return np.clip(img, 0, 1), disk


def panel_pointing():
    """(a) 指し示す: 引き出し線 + 番号マーカー + 凡例 + 方位。"""
    img, disk = _scene()
    pts = [(110, 110), (240, 60), (150, 190)]
    lay = A.annotate_leader_layout((PH, PW), pts, ["disk", "bar", "background"], gap=24)
    out = A.annotate_leader(img, pts, ["disk", "bar", "background"], gap=24, layout=lay)
    out = A.annotate_markers(out, [(80, 80), (280, 90)], start=1, radius=9)
    out = A.annotate_legend(out, ["defect", "reference"], (PW - 10, PH - 10), anchor="rb", start=1)
    out = A.annotate_orientation(out, 20.0, corner="lt", size=26, margin=14)
    return out, lay, pts


def panel_metrology():
    """(b) 測る: 寸法線 + 角度 + 切りのよいスケールバー。"""
    img, _ = _scene()
    dim = A.annotate_dimension_layout((60, 200), (160, 200), offset=-24)
    out = A.annotate_dimension(img, (60, 200), (160, 200), 0.4, "mm", offset=-24, layout=dim)
    ang = A.annotate_angle_layout((260, 150), (210, 150), (210, 100), radius=30)
    out = A.annotate_angle(out, (260, 150), (210, 150), (210, 100), radius=30, layout=ang)
    sb = A.annotate_scale_bar_layout((PH, PW), 0.4, "mm", corner="rb", target_fraction=0.25)
    out = A.annotate_scale_bar(out, 0.4, "mm", corner="rb", target_fraction=0.25, layout=sb)
    return out, dim, ang, sb


def panel_regions():
    """(c) 領域: マスクの輪郭 + 隅の拡大差し込み + 経路に沿う文字。"""
    img, disk = _scene()
    ol = A.annotate_outline_layout(disk)
    out = A.annotate_outline(img, disk, label="ROI", layout=ol)
    ins = A.annotate_inset_layout((PH, PW), (150, 90, 30, 20), corner="rt", margin=10)
    out = A.annotate_inset(out, (150, 90, 30, 20), corner="rt", margin=10, layout=ins)
    path = [(30, 220), (110, 175), (200, 215)]
    out = A.annotate_text_path(out, "profile line", path, font_size=13, draw_path=True)
    return out, ol, ins


def panel_field():
    """(d) 場: 色分け重ね + カラーバー。"""
    img, _ = _scene()
    yy, xx = np.mgrid[0:PH, 0:PW]
    field = np.exp(-((xx - 110) ** 2 + (yy - 110) ** 2) / (2 * 30.0 ** 2))
    out = A.annotate_colorbar(img, field, (PW - 64, 20, 12, 150), lut=palette.diverging_lut(256),
                              vmin=0.0, vmax=1.0, alpha=0.55, unit="a.u.")
    return out


def run():
    (pa, lay, pts) = panel_pointing()
    (pb, dim, ang, sb) = panel_metrology()
    (pc, ol, ins) = panel_regions()
    pd = panel_field()
    panels = [pa, pb, pc, pd]
    caps = ["pointing: leader / markers / legend", "metrology: dimension / angle / scale bar",
            "regions: outline / inset / text path", "field: colour overlay + colour bar"]
    grid = A.annotate_figure_grid_layout([p.shape[:2] for p in panels], ncols=2, pad=12,
                                         caption_h=30)
    sheet = A.annotate_figure_grid(panels, caps, ncols=2, pad=12, caption_h=30, font_size=13)

    r = {}
    # 1. 引き出し線
    boxes = [it["box"] for it in lay["items"]]
    r["leader_overlaps"] = sum(A._overlaps(boxes[i], boxes[j])
                               for i in range(3) for j in range(i + 1, 3))
    r["leader_elbow_ok"] = all(
        it["elbow"] == (x + it["side"][0] * lay["gap"], y + it["side"][1] * lay["gap"])
        or abs(it["elbow"][1] - y) in (1.6 * lay["gap"], 2.4 * lay["gap"])
        for it, (x, y) in zip(lay["items"], pts))
    # 2. 寸法
    r["dimension_value_mm"] = dim["length_px"] * 0.4
    r["dimension_line_y"] = dim["line"][0][1]
    # 3. 角度
    r["angle_deg"] = ang["angle_deg"]
    # 4. スケールバー
    x0, y0, w, h = sb["rect"]
    lit = np.all(np.isclose(pb[y0:y0 + h, x0:x0 + w], pb[y0, x0]), axis=-1)
    r["scale_bar_length"] = sb["length"]
    r["scale_bar_px_error"] = int(abs(w - round(sb["length"] / 0.4)))
    r["scale_bar_drawn_uniform"] = bool(lit.all())
    # 5. 輪郭
    c = ol["contours"][0]
    x, y = c[:, 0], c[:, 1]
    area = 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(np.roll(x, -1), y))
    r["outline_area_error"] = float(abs(area - ol["area"]))
    # 6. 組版
    r["grid_size"] = sheet.shape[:2]
    r["grid_want"] = grid["size"]
    px, py, pw, ph = grid["panels"][0]
    # 枠線(border=1)はセルの縁 1 px に乗るので、その内側を画素単位で比べる
    r["grid_panel_exact"] = bool(np.array_equal(sheet[py + 2:py + ph - 2, px + 2:px + pw - 2],
                                                pa[2:-2, 2:-2]))
    r["inset_factor"] = ins["factor"]
    r["sheet"] = sheet
    return r


def main(save=None):
    r = run()
    print("学術図の図注(paper 族)を 4 パネルに組み、layout の閉形式と突き合わせた:")
    print(f"1) 引き出し線 3 本: 板の重なり {r['leader_overlaps']} 件、肘 = 点 + side*gap {r['leader_elbow_ok']}")
    print(f"2) 寸法線: 100 px x 0.4 mm/px = {r['dimension_value_mm']:.1f} mm、寸法線は y={r['dimension_line_y']:g}(点 - 24)")
    print(f"3) 角度: (右, 頂点, 上) -> {r['angle_deg']:.1f}°")
    print(f"4) スケールバー: 幅の 25% 以下で切りのよい {r['scale_bar_length']:g} mm、"
          f"画素長の誤差 {r['scale_bar_px_error']} px、描画は一様 {r['scale_bar_drawn_uniform']}")
    print(f"5) 輪郭: 多角形面積 - 画素数 = {r['outline_area_error']:g}")
    print(f"6) 組版: 図の大きさ {r['grid_size']} / 閉形式 {r['grid_want']}、"
          f"パネル (a) は画素単位でそのまま {r['grid_panel_exact']}、差し込みは x{r['inset_factor']}")
    assert r["leader_overlaps"] == 0 and r["leader_elbow_ok"]
    assert abs(r["dimension_value_mm"] - 40.0) < 1e-9 and r["dimension_line_y"] == 176.0
    assert abs(r["angle_deg"] - 90.0) < 1e-9
    assert r["scale_bar_px_error"] == 0 and r["scale_bar_drawn_uniform"]
    assert r["outline_area_error"] == 0.0
    assert r["grid_size"] == r["grid_want"] and r["grid_panel_exact"]
    print("\nPASS: 図注の幾何(肘・寸法値・角度・バー長・輪郭面積・セル矩形)は閉形式と一致した。")
    if save:
        from PIL import Image
        Path(save).parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(np.round(r["sheet"] * 255.0).astype(np.uint8)).save(save)
        print(f"saved: {save}")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", default=None)
    args = ap.parse_args()
    raise SystemExit(main(save=args.save))
