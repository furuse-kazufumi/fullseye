# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fix_text_in_image — 画像の中の文字を「本当はこう書いてあるべき文字列」に合わせて直す。

    py -3.11 examples/fix_text_in_image.py
    FULLSEYE_FIGURE_DIR=out/figs py -3.11 examples/fix_text_in_image.py   # 前後の図も書く

【この例が示すこと】
生成 AI が出したレポート用の画像・看板の文字が 1 字だけ壊れている —— そういうとき
**画像を作り直さず**、正しい文字列を渡して直す。入口は JSON 一枚(``spec``)で、
Python(``fullseye.glyph_correct_spec``)からも MCP(``fullseye_fix_text``)からも
**同じ形**で呼べる。

1. ``mode="repair_flagged"``(既定): 床(書体雑音の 95 % 点)を超えた字**だけ**置き換え、
   正しい字には触らない。置換後に床より近くならなければ**元に戻す**(``failed_verification``)。
2. ``mode="rewrite_line"``: bbox の行を**同じ書体で丸ごと描き直す**。見逃し・誤検出が結果に
   残らず、字数の違いも直る。代わりに書体は変わる。
3. 報告の ``mismatch``: 壊れたマスの距離の中央値 ÷ 床 が 2 倍未満なら ``typo``(誤字)、
   2 倍以上なら ``unrelated``(**元の字が指示と無関係**)。描き直しは別物でも成功して
   しまうので、「指示か画像のどちらかが違う」を別枝で返す。
4. 直せないときは ``skipped`` と、人向けの ``reason`` + 機械向けの ``reason_code``
   (``fullseye.glyphops.REASON_CODES`` の鍵)。縁取り文字は色が多峰なので断る。
5. ``glyph_make_spec``: 行の位置(bbox)を人が測らず、暗い字の行を上から検出して指示書に
   する。版面が取れなければ ``layout.status`` で断り、items に bbox を入れない。

【真値】掲示は自分で描く(正しい字を描き、1 字を似た字に差し替える)。どの位置を壊したか
分かっているので、報告の ``status`` 列と突き合わせて印字する。
CJK を描ける書体がこの環境に無ければ ``[skip]`` を印字して 0 で終わる。

【MCP から呼ぶとき】同じ ``items`` をそのまま渡す(画像はハンドル)::

    {"name": "fullseye_fix_text",
     "arguments": {"handle": "fullseye://img/<16 hex>",
                   "items": [{"text": "電気設備", "bbox": [24, 40, 384, 96]}],
                   "mode": "repair_flagged"}}

EXTEND: bbox を省くなら ``glyph_make_spec(rgb, texts)``(MCP は items の bbox を省くだけ)。
行が複数あるなら ``items`` を増やす。翻訳版を作るなら ``text`` に訳文を入れる
(長い訳文は行に収まる大きさで描かれる)。閾値を固定したいなら ``policy.threshold``。
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402


def draw_sign(font: str, text: str, wrong_at: int | None = None, wrong: str = "誤",
              outline: int = 0) -> tuple[np.ndarray, list[int]]:
    """1 行の掲示を描いて ``(rgb, bbox)`` を返す。``wrong_at`` の字を ``wrong`` に差し替える。

    ``outline`` > 0 なら縁取り文字にする(色が多峰になり、道具が**断る**例に使う)。
    bbox は**描いた後のインク**から取る —— PIL は書体の ascent ぶん下げて描くので、
    指定座標をそのまま bbox にすると字が縦にはみ出す。
    """
    from PIL import Image, ImageDraw, ImageFont
    size, pad = 96, 24
    shown = list(text)
    if wrong_at is not None:
        shown[wrong_at] = wrong
    f = ImageFont.truetype(font, size)
    im = Image.new("RGB", (pad * 2 + size * len(text), pad * 2 + size), (235, 235, 230))
    d = ImageDraw.Draw(im)
    for i, c in enumerate(shown):
        xy = (pad + i * size, pad)
        if outline:
            d.text(xy, c, font=f, fill=(20, 20, 20), stroke_width=outline, stroke_fill=(200, 30, 30))
        else:
            d.text(xy, c, font=f, fill=(20, 20, 20))
    rgb = np.asarray(im, np.float64) / 255.0
    ys, xs = np.nonzero(rgb.mean(axis=-1) < 0.6)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max() + 1 - xs.min()), int(ys.max() + 1 - ys.min())]
    return rgb, bbox


def draw_two_lines(font: str, lines, wrong_at=None, wrong: str = "誤") -> np.ndarray:
    """2 行の掲示(行間 40 px)。``wrong_at=(行, 字)`` を差し替える。bbox は返さない ——
    それを測るのが ``glyph_make_spec`` の仕事だから。"""
    from PIL import Image, ImageDraw, ImageFont
    size, pad, gap = 96, 24, 40
    f = ImageFont.truetype(font, size)
    W = pad * 2 + size * max(len(s) for s in lines)
    H = pad * 2 + size * len(lines) + gap * (len(lines) - 1)
    im = Image.new("RGB", (W, H), (235, 235, 230))
    d = ImageDraw.Draw(im)
    for r, s in enumerate(lines):
        shown = list(s)
        if wrong_at and wrong_at[0] == r:
            shown[wrong_at[1]] = wrong
        for i, c in enumerate(shown):
            d.text((pad + i * size, pad + r * (size + gap)), c, font=f, fill=(20, 20, 20))
    return np.asarray(im, np.float64) / 255.0


def show(title: str, report: dict) -> None:
    """報告を 1 行ずつ印字する(記号: ・無事 ◆直した ×戻した ?直せない)。"""
    marks = {"ok": "・", "replaced": "◆", "rewritten": "◆", "failed_verification": "×", "skipped": "?"}
    print("%s  床=%.4f(%s)" % (title, report["threshold"], report["floor_source"]))
    for it in report["items"]:
        cells = "".join(marks.get(c.get("status", ""), "?") for c in it["cells"])
        line = "  %-19s %-8s %s  mismatch=%s" % (it["status"], it["text"], cells, it.get("mismatch"))
        if "mismatch_ratio" in it:
            line += "(%.2f 倍)" % it["mismatch_ratio"]
        if it.get("reason_code"):
            line += "  [%s] %s" % (it["reason_code"], it["reason"])
        print(line)


def main() -> int:
    fonts = fs.glyph_fonts()
    if not fonts:
        print("[skip] CJK を描けるフォントがこの環境に無い(Debian/Ubuntu: apt-get install fonts-noto-cjk)")
        return 0
    font = fonts[0]

    # 1. 「電気設備」の 3 字目を「誤」に差し替えた掲示。壊れた字だけ直す。
    rgb, bbox = draw_sign(font, "電気設備", wrong_at=2)
    spec = {"items": [{"text": "電気設備", "bbox": bbox}]}       # ← MCP に渡す items と同じ
    fixed, rep = fs.glyph_correct_spec(rgb, spec)
    show("1. repair_flagged(壊れた字だけ置換)", rep)
    cells = rep["items"][0]["cells"]
    assert [c["status"] for c in cells] == ["ok", "ok", "replaced", "ok"], cells

    # 2. 同じ掲示を行ごと描き直す。全マスが rewritten、bbox の外は 1 画素も変わらない。
    spec2 = dict(spec, policy={"mode": "rewrite_line"})
    rewritten, rep2 = fs.glyph_correct_spec(rgb, spec2)
    show("2. rewrite_line(行を丸ごと描き直す)", rep2)
    x, y, w, h = bbox
    outside = np.ones(rgb.shape[:2], bool)
    outside[y:y + h, x:x + w] = False
    assert np.array_equal(rewritten[outside], rgb[outside]), "bbox の外を触った"

    # 3. 板には「本日休業」、指示は「電気設備」。描き直しは成功するが mismatch=unrelated。
    rgb3, bbox3 = draw_sign(font, "本日休業")
    spec3 = {"items": [{"text": "電気設備", "bbox": bbox3}], "policy": {"mode": "rewrite_line"}}
    out3, rep3 = fs.glyph_correct_spec(rgb3, spec3)
    show("3. 元の字が指示と無関係(unrelated の疑いを返す)", rep3)
    assert rep3["items"][0]["mismatch"] == "unrelated", rep3["items"][0]

    # 4. 縁取り文字は色が多峰なので断る(黙って塗らない)。reason_code で分岐できる。
    rgb4, bbox4 = draw_sign(font, "電気設備", wrong_at=2, outline=5)
    out4, rep4 = fs.glyph_correct_spec(rgb4, {"items": [{"text": "電気設備", "bbox": bbox4}]})
    show("4. 縁取り文字(断る)", rep4)
    codes = {c.get("reason_code") for c in rep4["items"][0]["cells"] if c.get("status") == "skipped"}
    assert codes <= set(fs.glyphops.REASON_CODES), codes
    assert np.array_equal(out4, rgb4), "断ったのに画像を変えた"
    assert rep4["items"][0]["mismatch"] == "unknown", rep4["items"][0]   # 測れない距離で別物を言わない

    # 5. bbox を人が測らない: 2 行の掲示から指示書(JSON)を自動で作り、そのまま直す。
    #    MCP では items の bbox を省くだけで同じ道を通る。
    rgb5 = draw_two_lines(font, ("電気設備", "点検中"), wrong_at=(0, 2))
    spec5 = fs.glyph_make_spec(rgb5, ["電気設備", "点検中"])
    print("5. make_spec(bbox を自動で): layout=%s  bbox=%s" % (
        spec5["layout"]["status"], [it.get("bbox") for it in spec5["items"]]))
    assert spec5["layout"]["status"] == "ok", spec5["layout"]
    out5, rep5 = fs.glyph_correct_spec(rgb5, spec5)
    show("   → correct_spec", rep5)
    assert rep5["items"][0]["cells"][2]["status"] == "replaced", rep5["items"][0]
    assert all(it["status"] in ("ok", "replaced") for it in rep5["items"]), rep5["items"]

    # 図(FULLSEYE_FIGURE_DIR があるときだけ)。
    figs.save_grid("fix_text_before_after",
                   [rgb, fixed, rewritten, rgb3, out3, rgb5, out5],
                   ["入力(設→誤)", "repair_flagged", "rewrite_line", "本日休業(指示は電気設備)",
                    "描き直し(unrelated)", "2 行(bbox 無し)", "make_spec → 直した"],
                   ncols=3, caption="壊れた字だけ直す / 行ごと描き直す / 別物の疑いを返す / bbox を自動で")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
