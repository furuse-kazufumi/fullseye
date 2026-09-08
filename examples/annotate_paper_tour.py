# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""annotate_paper_tour — 論文図の「経路に沿う文字」と「パネル文字 (a)(b)」を組み、配置を閉形式で検算する。

    py -3.11 examples/annotate_paper_tour.py
    py -3.11 examples/annotate_paper_tour.py --save out/annotate_paper_tour.png

【この例が示すこと】
``annotate_text_path_layout`` は折れ線に沿って 1 文字ずつ「弧長 → 位置と傾き」を決める
表(table)を返す。``annotate_panel_label`` は多パネル図の ``(a)`` ``(b)`` を隅に置く。
どちらも**描く前に数値で測れる**ので、描いた結果と閉形式を突き合わせる。

【グラウンドトゥルース(すべて assert で落とす)】
1. 文字 i の中心弧長 ``s_i = start + Σ_{j<i} w_j*spacing + w_i/2``、``used = Σ w_i*spacing``、
   ``length`` = 折れ線長(誤差 1e-9)。水平線なら位置は ``(x0 + s_i, y0)`` で傾き 0。
2. L 字の経路(右 → 下)では、角の前の字は傾き 0、角の後は傾き 90 度で、位置は
   ``(x_corner, y_corner + (s_i - 100))``(誤差 1e-9)。角をまたぐ字は無い。
3. 各字の幅は ``measure_text`` の幅と一致(1 px 以内)。経路より長い文字列は ValueError。
4. パネル文字: 左/上の隅では板の縁がちょうど ``margin`` の位置。右/下の隅では
   アンカー画素が排他的なので ``margin + 1``(実測して印字 —— honest)。
5. ``annotate_panel_label(letter=1)`` と ``letter='b'`` は同一、かつ ``text_box("(b)")`` を
   同じ位置に置いたものと画素単位で同一。style upper は ``"B"``。未知の corner は ValueError。

【読み方】各節の印字は「真値 / 実測 / 差」。PASS 行が出れば全部通っている。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import annotate as A          # noqa: E402  図注の層

PH, PW = 140, 220             # パネルの大きさ(非正方)


def section_text_path():
    """1-3. 経路に沿う文字の配置表。"""
    text, fs = "fullseye", 14
    # ★EXTEND: text と path を自分の図の文字と折れ線 (x, y) に差し替える
    x0, y0 = 20.0, 60.0
    lay = A.annotate_text_path_layout(text, [(x0, y0), (x0 + 200.0, y0)], font_size=fs)
    w = np.array([c["width"] for c in lay["chars"]])
    s_want = np.cumsum(np.concatenate([[0.0], w[:-1]])) + w / 2.0          # start=0, spacing=1
    s_got = np.array([c["s"] for c in lay["chars"]])
    xy = np.array([c["xy"] for c in lay["chars"]])
    ang = np.array([c["angle_deg"] for c in lay["chars"]])
    e_s = float(np.abs(s_got - s_want).max())
    e_xy = float(np.abs(xy - np.column_stack([x0 + s_want, np.full(len(w), y0)])).max())
    e_used = abs(lay["used"] - float(w.sum()))
    print(f"1) 水平線 '{text}' {len(w)} 字: 弧長の閉形式との差 {e_s:.1e}、位置の差 {e_xy:.1e}、"
          f"傾き最大 {float(np.abs(ang).max()):.1e} 度、used {lay['used']:.1f} = Σw {float(w.sum()):.1f}"
          f"(差 {e_used:.1e})、length {lay['length']:.1f}")
    assert e_s < 1e-9 and e_xy < 1e-9 and float(np.abs(ang).max()) < 1e-9
    assert e_used < 1e-9 and abs(lay["length"] - 200.0) < 1e-9

    # spacing / start を変えても同じ式
    sp, st = 1.5, 10.0
    lay2 = A.annotate_text_path_layout(text, [(x0, y0), (x0 + 200.0, y0)], font_size=fs,
                                       spacing=sp, start=st)
    w2 = np.array([c["width"] for c in lay2["chars"]])
    s2_want = st + np.cumsum(np.concatenate([[0.0], w2[:-1] * sp])) + w2 / 2.0
    e_s2 = float(np.abs(np.array([c["s"] for c in lay2["chars"]]) - s2_want).max())
    e_used2 = abs(lay2["used"] - float((w2 * sp).sum()))
    print(f"   spacing={sp}, start={st}: 弧長の閉形式との差 {e_s2:.1e}、used の差 {e_used2:.1e}")
    assert e_s2 < 1e-9 and e_used2 < 1e-9

    # 2) L 字の経路: 角の前は 0 度、後は 90 度
    cx, cy = x0 + 100.0, y0
    layL = A.annotate_text_path_layout("fullseye turns here", [(x0, y0), (cx, cy), (cx, cy + 100.0)],
                                       font_size=fs)
    before = [c for c in layL["chars"] if c["s"] < 100.0]
    after = [c for c in layL["chars"] if c["s"] >= 100.0]
    e_b = max(max(abs(c["angle_deg"]), abs(c["xy"][0] - (x0 + c["s"])), abs(c["xy"][1] - y0))
              for c in before)
    e_a = max(max(abs(c["angle_deg"] - 90.0), abs(c["xy"][0] - cx), abs(c["xy"][1] - (cy + c["s"] - 100.0)))
              for c in after)
    print(f"2) L 字経路: 角の前 {len(before)} 字(傾き 0、位置差 {e_b:.1e})/ 角の後 {len(after)} 字"
          f"(傾き 90、位置差 {e_a:.1e})、length {layL['length']:.0f}")
    assert before and after and e_b < 1e-9 and e_a < 1e-9 and abs(layL["length"] - 200.0) < 1e-9

    # 3) 字幅は measure_text と一致、長すぎる文字列は拒否
    e_w = max(abs(c["width"] - A.measure_text(c["char"], font_size=fs, min_font_size=1)["width"])
              for c in lay["chars"] if c["char"] != " ")
    try:
        A.annotate_text_path_layout("x" * 200, [(0.0, 0.0), (50.0, 0.0)], font_size=fs)
        too_long = False
    except ValueError:
        too_long = True
    print(f"3) 字幅と measure_text の最大差 {e_w:.2f} px、経路より長い文字列は ValueError {too_long}")
    assert e_w <= 1.0 and too_long

    # 絵にする(表をそのまま描画 op に渡す)
    img = np.full((PH, PW, 3), 0.08)
    path = [(20.0, 100.0), (110.0, 40.0), (200.0, 100.0)]
    lay_v = A.annotate_text_path_layout("along the path", path, font_size=fs)
    img = A.annotate_text_path(img, "along the path", path, font_size=fs, color="emphasis",
                               draw_path=True, layout=lay_v)
    return img, {"path_s_err": e_s, "path_xy_err": e_xy, "path_used_err": e_used,
                 "path_L_err": max(e_b, e_a), "width_err": e_w, "too_long_rejected": too_long}


def section_panel_label():
    """4-5. パネル文字の置き場所。"""
    canvas = np.full((PH, PW, 3), 0.05)
    margin = 10
    kw = dict(margin=margin, box_alpha=1.0, box_color=(1.0, 1.0, 1.0), text_color=(0.0, 0.0, 0.0))
    edges = {}
    for corner in ("lt", "rt", "lb", "rb"):
        out = A.annotate_panel_label(canvas, "b", corner=corner, **kw)
        ch = np.abs(out - canvas).max(-1) > 1e-6            # 板が塗った画素
        rows, cols = np.nonzero(ch)
        edges[corner] = (int(rows.min()), int(rows.max()), int(cols.min()), int(cols.max()))
    # 左/上: 縁 == margin。右/下: アンカー画素 (W-1-margin) が排他的なので縁 == W-1-margin-1
    lt_ok = edges["lt"][0] == margin and edges["lt"][2] == margin
    rt_ok = edges["rt"][0] == margin and edges["rt"][3] == PW - 1 - margin - 1
    lb_ok = edges["lb"][1] == PH - 1 - margin - 1 and edges["lb"][2] == margin
    rb_ok = edges["rb"][1] == PH - 1 - margin - 1 and edges["rb"][3] == PW - 1 - margin - 1
    print(f"4) パネル文字の板の縁(row0,row1,col0,col1): {edges}")
    print(f"   左/上の縁 = margin({margin}) {lt_ok and lb_ok} / 右/下の縁 = 端 - margin - 1"
          f"(右 {PW - 1 - margin - 1}, 下 {PH - 1 - margin - 1}){rt_ok and rb_ok}"
          f" —— 右/下はアンカー画素が排他的で 1 px 内側(honest)")
    assert lt_ok and rt_ok and lb_ok and rb_ok

    # 5) 番号と文字は同じ、text_box と画素単位で同じ、style
    by_idx = A.annotate_panel_label(canvas, 1, corner="lt", **kw)
    by_chr = A.annotate_panel_label(canvas, "b", corner="lt", **kw)
    tb = A.text_box(canvas, "(b)", (margin, margin), anchor="lt", pad=4, font_size=16,
                    min_font_size=9, box_alpha=1.0, box_color=(1.0, 1.0, 1.0), text_color=(0.0, 0.0, 0.0))
    same_idx = np.array_equal(by_idx, by_chr)
    same_tb = np.array_equal(by_idx, tb)
    up = A.annotate_panel_label(canvas, 1, corner="lt", style="upper", **kw)
    tb_up = A.text_box(canvas, "B", (margin, margin), anchor="lt", pad=4, font_size=16,
                       min_font_size=9, box_alpha=1.0, box_color=(1.0, 1.0, 1.0), text_color=(0.0, 0.0, 0.0))
    same_up = np.array_equal(up, tb_up)
    try:
        A.annotate_panel_label(canvas, "b", corner="middle")
        bad_corner = False
    except ValueError:
        bad_corner = True
    print(f"5) letter=1 と 'b' が同一 {same_idx}、text_box('(b)') と画素単位で同一 {same_tb}、"
          f"style='upper' は 'B' {same_up}、未知の corner は ValueError {bad_corner}")
    assert same_idx and same_tb and same_up and bad_corner
    return {"edges": edges, "index_equals_letter": same_idx, "equals_text_box": same_tb,
            "upper_ok": same_up, "bad_corner_rejected": bad_corner}


def section_invert():
    """反転色(annotate_invert 族)—— 崖の位置を閉形式で当ててから描く。

    反転色は「地の明暗を知らなくても見える色で描く」ための古典手だが、
    **中間調では反転しても同じ色になる**。ここでは

    1. 全 256 階調で補色とのコントラスト比を測り、消える帯を特定する
       (WCAG の式を**この場で書き下して**照合 —— op で op を測らない)、
    2. 逃げ道 ``mode="contrast"`` が全階調で 4.58 以上を出すことを確かめる、
    3. 左右に明→暗の傾斜を持つ地に線と領域を反転色で描き、**帯の位置が
       予測どおり**であることを画素で確かめる

    の 3 つを行う。
    """
    def wcag(v):                              # op の実装とは別に書き下した零点
        v = np.asarray(v, dtype=np.float64)
        return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)

    levels = np.arange(256) / 255.0
    lo, hi = wcag(levels), wcag(1.0 - levels)
    cr = (np.maximum(lo, hi) + 0.05) / (np.minimum(lo, hi) + 0.05)
    bad = np.where(cr < A.INVERT_MIN_CONTRAST)[0]
    assert (int(bad.min()), int(bad.max()), int(bad.size)) == (113, 142, 30), bad
    assert round(float(cr[128]), 3) == 1.014, cr[128]
    print(f"  補色が消える帯: v ∈ [{bad.min()}, {bad.max()}] の {bad.size}/256 階調 "
          f"({100.0 * bad.size / 256:.1f} %)、v=128 の比は {cr[128]:.3f}(1.0 = 同じ色)")

    strip = np.tile(levels, (4, 1))
    esc = A.annotate_invert_visibility(strip, np.ones(strip.shape, bool), mode="contrast")
    assert esc["min_contrast"] >= 4.58, esc
    assert esc["invisible_fraction"] == 0.0, esc
    print(f'  逃げ道 mode="contrast": 全 256 階調で最悪 {esc["min_contrast"]:.2f} '
          f"(連続の下界 1.05/√0.0525 = 4.583)")

    # 明 → 暗の横傾斜。x が真ん中に来るところで補色が消える
    ramp = np.tile(np.linspace(1.0, 0.0, PW), (PH, 1))
    line = [(6.0, PH * 0.35), (PW - 7.0, PH * 0.35)]
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        panel = A.annotate_invert_path(ramp, line, width=3.0)
    assert any("invisible" in str(w.message) for w in caught), "傾斜の中央で警告が出るはず"
    row = int(round(PH * 0.35))
    delta = np.abs(panel[row] - ramp[row])
    dead = np.where(delta < 1.0 / 255.0)[0]
    dead = dead[(dead >= 6) & (dead <= PW - 7)]              # 線が乗る範囲だけ見る
    want = int(round((1.0 - 128.0 / 255.0) * (PW - 1)))      # v=128 になる列(閉形式)
    assert abs(int(np.median(dead)) - want) <= 2, (np.median(dead), want)
    print(f"  傾斜の上の線: 消える列の中央は {int(np.median(dead))}(閉形式の予測 {want})、"
          f"消える幅 {dead.size} 列")

    # 同じ地に、領域を fill と margin で。margin は中身を触らない
    m = np.zeros((PH, PW), bool)
    m[int(PH * 0.55):int(PH * 0.85), 20:PW - 20] = True
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        panel = A.annotate_invert(panel, m, draw="margin", width=2)
        inside = A.annotate_invert(ramp, m, draw="fill")
    cy, cx = int(PH * 0.70), PW // 2
    assert panel[cy, cx] == ramp[cy, cx], "margin は中身を触らない"
    assert not np.isclose(inside[cy, cx], ramp[cy, cx], atol=1e-6) or \
        abs(ramp[cy, cx] - 0.5) < 1e-3, "fill は中身を反転する(中間調は除く)"
    panel = A.annotate_invert(panel, m, draw="margin", width=2, mode="contrast")
    return (np.repeat(panel[..., None], 3, axis=2),
            {"invisible_levels": int(bad.size), "cr_at_128": float(cr[128]),
             "escape_min_contrast": float(esc["min_contrast"]),
             "dead_columns": int(dead.size)})


def run() -> dict:
    """全 6 節を回し、真値との照合結果と組んだ図を返す(失敗は assert で落ちる)。"""
    t0 = time.perf_counter()
    panel_a, r1 = section_text_path()
    r2 = section_panel_label()
    panel_c, r3 = section_invert()
    # 2 パネルの図: (a) 経路に沿う文字、(b) 目盛りつきの空の枠 —— それぞれ隅に文字を置く
    panel_b = np.full((PH, PW, 3), 0.08)
    ax = A.axes_transform((40, 20, 160, 90), (0.0, 1.0), (0.0, 1.0))
    panel_b = A.axes_frame(panel_b, ax, color="neutral", width=1)
    panel_b = A.ticks(panel_b, ax, tick_len=4, font_size=9)
    panel_a = A.annotate_panel_label(panel_a, 0, corner="lt", margin=6)
    panel_b = A.annotate_panel_label(panel_b, 1, corner="lt", margin=6)
    sheet = A.panel_grid([panel_a, panel_b], ncols=2, pad=10, label_h=0, background=0.04)
    out = {"sheet": sheet}
    out.update(r1)
    out.update(r2)
    out["elapsed_s"] = time.perf_counter() - t0
    return out


def main(save=None):
    r = run()
    print(f"\nPASS: annotate_text_path_layout(弧長・位置・傾き・used の閉形式一致、L 字で 0/90 度)と "
          f"annotate_panel_label(板の縁 = margin、text_box と画素同一)。 実行 {r['elapsed_s']:.2f} 秒")
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
