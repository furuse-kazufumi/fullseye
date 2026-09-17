# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 画像に書かれた誤字を、**認識せずに**見つけて**実際に直す**。

正しい文字列は入力で貰える(「本当はこう書いてあるべき」を人が知っている場面が
対象 —— 画像生成 AI が壊した掲示、差し替えたい看板)。だから 6000 通りの多クラス
分類は要らず、各マスを指定の 1 字と比べるだけで済む。閾値は勘で置かず、
``glyphops.typeface_noise_floor`` が**書体の違いだけで出る距離**から導く。

真値は自分で植える: 正しい掲示を描き、**形の似た字**に差し替えて誤字を作る。
どの位置を壊したか分かっているので、検出率も修復の良し悪しも厳密に測れる。
ぼけ・ノイズ・量子化も既知の量で加える。

★``GLYPH_POC_DIR`` に画像と台帳(``ledger.json``)を置いたディレクトリを指すと、
**実写にも同じ手順を掛ける**。台帳が無ければ合成だけで完結する(repo に画像は
入れない —— 生成 AI の出力なので来歴を別に管理する)。

    py -3.11 examples/poc_glyph_typo_detection.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examplefig as figs  # noqa: E402
import glyphops  # noqa: E402

#: 形が似ていて実際に取り違えが起きる対(正しい字 -> 紛らわしい字)。
#: 全漢字 6,356 字を粗い記述子で総当たりして選んだ上位から、目で確かめたものだけ。
CONFUSABLE = {"検": "横", "土": "士", "未": "末", "日": "曰", "大": "犬", "電": "雷",
              "設": "股", "備": "儒", "点": "煮", "場": "揚"}

#: 合成する掲示の文面(2 行)。
LINES = ("電気設備点検中", "立入禁止")
#: 壊す位置(行, 列)。★真値はここで決まる。
BREAK_AT = ((0, 2), (0, 3), (0, 5), (1, 0))

_PLATE = (0.89, 0.80, 0.43)      # 看板の地(クリーム)
_INK = (0.10, 0.10, 0.11)        # 文字(黒)


def _render_line(chars, font, size=96, weight=5):
    """1 行を**フォントの字送りのまま**描く。

    ★1 字ずつ外接箱で正規化して並べてはいけない —— 字ごとに拡大率が変わるので
    マスのインク量がばらつき、実写から導いた版面の門(ばらつき <= 0.45)に
    自分で引っかかる(実測 0.61)。合成は実写に似せる意味があるときだけ意味を持つ。
    """
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(font, size)
    text = "".join(chars)
    w = int(round(size * len(chars) * 1.02))
    img = Image.new("L", (w, int(size * 1.4)), 0)
    ImageDraw.Draw(img).text((w // 2, int(size * 0.7)), text, fill=255, font=f, anchor="mm")
    a = np.asarray(img, np.float64) / 255.0
    ys, xs = np.where(a > 0.5)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return ndimage.grey_dilation(a, size=weight)


def make_sign(font, blur=1.2, noise=0.01, levels=64, seed=20260917):
    """真値つきの掲示を作る。返り値は (RGB, 行ごとの文字列, 壊した位置の集合)。"""
    rng = np.random.default_rng(seed)
    shown = [list(s) for s in LINES]
    broken = set()
    flat = 0
    for li, line in enumerate(LINES):
        for ci in range(len(line)):
            if (li, ci) in BREAK_AT:
                shown[li][ci] = CONFUSABLE.get(line[ci], "乕")
                broken.add(flat)
            flat += 1
    rows = [_render_line(s, font) for s in shown]
    w = max(r.shape[1] for r in rows)
    pad = 40
    h = sum(r.shape[0] for r in rows) + pad * (len(rows) + 1)
    ink = np.zeros((h, w + 2 * pad))
    y = pad
    for r in rows:
        x = pad + (w - r.shape[1]) // 2
        ink[y:y + r.shape[0], x:x + r.shape[1]] = r
        y += r.shape[0] + pad
    ink = ndimage.gaussian_filter(ink, blur)
    rgb = np.empty(ink.shape + (3,))
    rgb[:] = np.asarray(_PLATE)
    rgb = rgb * (1.0 - ink[..., None]) + np.asarray(_INK) * ink[..., None]
    rgb = rgb + rng.normal(0.0, noise, rgb.shape)
    rgb = np.round(np.clip(rgb, 0, 1) * (levels - 1)) / (levels - 1)   # 量子化
    return rgb, LINES, broken


def find_text_lines(gray, n_lines=0, dark=0.35, min_area=200):
    """字のインクだけを残し、**行**の外接箱を上から順に返す。

    ★看板の枠は「大きな外接箱なのに中身が薄い」成分として出る。外すだけにして、
    枠の内側に限定はしない —— 限定すると、枠が二重に見える看板で内側の枠を掴み、
    その外にある 1 行目をまるごと落とす(実測)。
    """
    ink = np.asarray(gray) < dark
    lab, n = ndimage.label(ink)
    if n == 0:
        return [], None
    boxes = []
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        area = int((lab[sl] == i).sum())
        if area >= min_area:
            boxes.append({"id": i, "sl": sl, "h": h, "w": w, "area": area,
                          "fill": area / float(h * w)})
    boxes = [b for b in boxes
             if not (b["fill"] < 0.35 and b["h"] * b["w"] > 0.02 * ink.size)]
    if not boxes:
        return [], None
    keep = np.zeros_like(ink)
    for b in boxes:
        keep[b["sl"]] |= (lab[b["sl"]] == b["id"])

    # 行は**水平投影の帯**で取る。★成分をまとめる方法は使えない —— 漢字は部品に
    # 分かれて出る(``電`` は 3 つ)ので、重なりや中心距離で束ねると行間の狭い
    # 看板で 2 行が 1 行に融け、逆に離れた部品が 3 行目になった(実測 6/12 枚)。
    prof = keep.sum(axis=1).astype(float)
    on = prof > max(1.0, 0.02 * prof.max())
    runs, i = [], 0
    while i < len(on):
        if on[i]:
            j = i
            while j + 1 < len(on) and on[j + 1]:
                j += 1
            runs.append((i, j + 1))
            i = j + 1
        else:
            i += 1
    if not runs:
        return [], None
    # 欧文の副題を落とす。**帯の高さ**で切る(実測: 漢字 80 px に対し英字 28 px)。
    tall = max(y1 - y0 for y0, y1 in runs)
    runs = [r for r in runs if (r[1] - r[0]) >= 0.6 * tall]
    # 行間が詰まっていると 2 行が 1 帯に融ける。**期待する行数**は呼び出し側が
    # 知っている(直す文字列を持っているのだから)ので、足りない分を谷で割る。
    while n_lines and len(runs) < n_lines:
        k = max(range(len(runs)), key=lambda t: runs[t][1] - runs[t][0])
        y0, y1 = runs[k]
        m0, m1 = y0 + int(0.25 * (y1 - y0)), y0 + int(0.75 * (y1 - y0))
        if m1 - m0 < 2:
            break
        cut = m0 + int(np.argmin(prof[m0:m1]))
        runs[k:k + 1] = [(y0, cut), (cut, y1)]
    out = []
    for y0, y1 in runs:
        cols = np.where(keep[y0:y1].any(axis=0))[0]
        if cols.size:
            out.append((slice(y0, y1), slice(int(cols.min()), int(cols.max()) + 1)))
    out.sort(key=lambda bx: bx[0].start)
    return out, ink


def split_cells(box, n, ink=None, snap=0.25):
    """行を **n 等分**し、切れ目をインクの**谷**に吸着させる。

    等幅を仮定できるのは CJK の掲示だからで、欧文では成り立たない。字数は
    **入力の文字列から**来る —— ここでも「読む」必要は無い。等分だけだと、細い字と
    太い字が混ざったときに切れ目が字に食い込むので、谷に寄せる。
    """
    ys, xs = box
    w = (xs.stop - xs.start) / float(n)
    cuts = [xs.start + i * w for i in range(n + 1)]
    if ink is not None and n > 1:
        prof = ink[ys, xs].sum(axis=0).astype(float)
        r = max(1, int(round(snap * w)))
        for i in range(1, n):
            c = int(round(cuts[i] - xs.start))
            lo, hi = max(0, c - r), min(len(prof), c + r + 1)
            if hi > lo:
                cuts[i] = xs.start + lo + int(np.argmin(prof[lo:hi]))
    return [(ys, slice(int(round(cuts[i])), int(round(cuts[i + 1])))) for i in range(n)]


def layout_is_plausible(boxes, want_lines, ink):
    """判定の前に**版面が正しいか**を確かめる。外れているなら理由を返す。

    ★これが無いと、切り方を間違えたまま全部の字を「壊れている」と報告する
    (実測: 無事な字 45 本のうち 37 本を誤って咎めた)。**字が壊れているのか、
    切り方が外れているのか**を取り違えないための門。
    """
    if len(boxes) != len(want_lines):
        return f"行の数が合わない(画像 {len(boxes)} / 指定 {len(want_lines)})"
    fr = []
    for box, want in zip(boxes, want_lines):
        n = len([c for c in want if not c.isspace()])
        h = box[0].stop - box[0].start
        w = (box[1].stop - box[1].start) / float(max(n, 1))
        if not (0.6 <= w / max(h, 1) <= 1.7):
            return f"マスが正方でない(幅/高さ {w / max(h, 1):.2f})"
        fr += [ink[cy, cx].mean() for cy, cx in split_cells(box, n, ink)]
    # 看板の枠・壁のざらつき・絵文字の行を掴んでいてもマスは正方になりうる。
    # 実測 12 枚: 良い版面は IQR/中央 0.08〜0.41・最小 0.23〜0.40、壊れた版面は
    # 0.42〜23.6・0.00〜0.07 で、次の 2 条件が完全に仕分ける。
    # ★統計は**画像の全マスをまとめて**取る —— 閾値をその形で導いたから。
    #   行ごとに取ると、4 字の行では四分位が粗すぎて 0.48〜0.59 に跳ね、
    #   正しい版面を自分で断ってしまう(実測)。**導出と適用で統計を変えない**。
    fr = np.asarray(fr, float)
    med = float(np.median(fr))
    iqr = float(np.quantile(fr, 0.75) - np.quantile(fr, 0.25))
    if fr.min() < 0.15 or (med > 0 and iqr / med > 0.45):
        return (f"マスのインク量が文字らしくない(最小 {fr.min():.3f} / "
                f"ばらつき {iqr / max(med, 1e-9):.2f})")
    return None


def judge(rgb, want_lines, floor, fonts, norm=160):
    """各マスの距離と、床を超えたか。版面が怪しければ**断る**。"""
    gray = rgb.mean(axis=-1) if rgb.ndim == 3 else rgb
    boxes, ink = find_text_lines(gray, len(want_lines))
    if not boxes:
        return None, "行が取れなかった", None, None
    bad = layout_is_plausible(boxes, want_lines, ink)
    if bad:
        return None, bad, boxes, ink
    out, i = [], 0
    for box, want in zip(boxes, want_lines):
        chars = [c for c in want if not c.isspace()]
        for j, (cy, cx) in enumerate(split_cells(box, len(chars), ink)):
            cell = ink[cy, cx].astype(np.float64)
            if cell.sum() < 20:
                out.append({"i": i, "char": chars[j], "distance": float("nan"),
                            "flag": None})
            else:
                # 書体は分からないので、手元の書体のうち**一番近いもの**を採る。
                d = min(glyphops.glyph_distance(
                    cell, glyphops.render_glyph(chars[j], f, 160), norm) for f in fonts)
                out.append({"i": i, "char": chars[j], "distance": d,
                            "flag": bool(d > floor)})
            i += 1
    return out, None, boxes, ink


def repair(rgb, want_lines, targets, boxes, ink, fonts):
    """``targets`` の位置を実際に置き換える。★線幅は**行全体**から測る。

    1 マスだけで測ると、壊れた字自身の太さに引きずられる。
    """
    out = rgb.copy()
    done, refused, why = 0, 0, []
    i = 0
    for box, want in zip(boxes, want_lines):
        thick = glyphops.stroke_thickness(ink[box])
        chars = [c for c in want if not c.isspace()]
        for j, (cy, cx) in enumerate(split_cells(box, len(chars), ink)):
            if i in targets:
                # ★マスを**少し広げて**切り出し、その中で「このマスに属する成分」
                #   だけをマスクにする。隣の字がマスの縁からはみ出していると、
                #   マスちょうどで切ったときにその分が消し残り、置換後に
                #   **旧字の切れ端**が浮いて見える(実測)。
                pad = max(4, int(0.15 * (cx.stop - cx.start)))
                py0, py1 = max(0, cy.start - pad), min(ink.shape[0], cy.stop + pad)
                px0, px1 = max(0, cx.start - pad), min(ink.shape[1], cx.stop + pad)
                sub = ink[py0:py1, px0:px1]
                lab, nlab = ndimage.label(sub)
                keep = np.zeros_like(sub)
                for k in range(1, nlab + 1):
                    ys_, xs_ = np.where(lab == k)
                    if cx.start <= px0 + xs_.mean() < cx.stop:
                        keep[lab == k] = True
                new, err = glyphops.replace_glyph(
                    rgb[py0:py1, px0:px1], keep, chars[j], fonts[0],
                    target_thickness=thick)
                if new is None:
                    refused += 1
                    why.append(f"{i} {chars[j]}: {err}")
                else:
                    out[py0:py1, px0:px1] = new
                    done += 1
            i += 1
    return out, done, refused, why


def _score(res, broken):
    tp = sum(1 for c in res if c["flag"] and c["i"] in broken)
    fp = sum(1 for c in res if c["flag"] and c["i"] not in broken)
    fn = sum(1 for c in res if c["flag"] is False and c["i"] in broken)
    tn = sum(1 for c in res if c["flag"] is False and c["i"] not in broken)
    return tp, fp, fn, tn


def _marks(res, broken):
    return "".join("*" if c["flag"] and c["i"] in broken else
                   "!" if c["flag"] else
                   "_" if c["i"] in broken else "." for c in res)


def _real_images(floor, fonts):
    """``GLYPH_POC_DIR`` に台帳があれば、実写にも同じ手順を掛ける。"""
    data = os.environ.get("GLYPH_POC_DIR")
    ledger = os.path.join(data, "ledger.json") if data else None
    if not ledger or not os.path.exists(ledger):
        return
    from PIL import Image
    print("\n= 実写(外部の画像生成 AI が描いた掲示)=")
    rows = json.load(open(ledger, encoding="utf-8"))
    tp = fp = fn = tn = 0
    for r in rows:
        path = os.path.join(data, r["file"])
        if not os.path.exists(path):
            continue
        im = np.asarray(Image.open(path).convert("RGB"), np.float64) / 255.0
        res, err, _, _ = judge(im, r["lines"], floor, fonts)
        if err:
            print(f"  {r['name']:<17}断った: {err}")
            continue
        broken = set(r["broken_index"])
        a, b, c, d = _score(res, broken)
        tp += a; fp += b; fn += c; tn += d
        print(f"  {r['name']:<17}{_marks(res, broken)}")
    if tp + fp + fn + tn:
        print(f"  壊れた字 {tp + fn} 本中 {tp} 本を検出(見逃し {fn})、"
              f"無事な字 {tn + fp} 本中 {fp} 本を誤って咎めた")


def main() -> int:
    fonts = glyphops.available_fonts()
    if len(fonts) < 2:
        print(f"[skip] CJK フォントが {len(fonts)} 本しかない —— 床は書体の散らばりな"
              "ので 2 本要る(Debian/Ubuntu: apt-get install fonts-noto-cjk)")
        return 0

    nf = glyphops.typeface_noise_floor("電気設備点検中立入禁止検横土士未末日曰大犬",
                                       fonts, size=160, out=160)
    floor = nf["floor"]
    print("= 閾値の由来 =")
    print(f"書体雑音の床 {floor:.4f}(中央 {nf['median']:.4f} / 最大 {nf['max']:.4f}、"
          f"書体 {nf['n_fonts']} 本・{nf['n_pairs']} 対)")
    print("  勘で置いた値ではなく、**同じ字を別の書体で描いたときの距離**の 95 % 点。\n")

    rgb, lines, broken = make_sign(fonts[0])
    print(f"= 合成した掲示({' / '.join(lines)}、{sum(len(s) for s in lines)} 字)=")
    print(f"壊した位置 {sorted(broken)} —— 形の似た字に差し替えた(これが真値)\n")

    res, err, boxes, ink = judge(rgb, lines, floor, fonts)
    if err:
        print(f"判定を断った: {err}")
        return 1
    tp, fp, fn, tn = _score(res, broken)
    print("= 検出 =")
    print("  " + _marks(res, broken) + "   "
          + " ".join(f"{c['distance']:.3f}" for c in res))
    print(f"  壊れた字 {tp + fn} 本中 {tp} 本を検出(見逃し {fn})、"
          f"無事な字 {tn + fp} 本中 {fp} 本を誤って咎めた")
    print("  記号: * 正しく検出 / _ 見逃し / ! 誤検出 / . 正しく無視\n")

    fixed, done, refused, why = repair(rgb, lines, broken, boxes, ink, fonts)
    print("= 修復 =")
    print(f"  置換 {done} / 断った {refused}")
    for w in why:
        print("   ", w)

    # 修復が効いたかを**数で**確かめる: 直した後のマスが指定の字に近づいたか。
    after, err2, _, _ = judge(fixed, lines, floor, fonts)
    if after:
        b = np.array([c["distance"] for c in res if c["i"] in broken])
        a = np.array([c["distance"] for c in after if c["i"] in broken])
        print(f"  壊れていた位置の距離: 修復前 中央 {np.median(b):.4f} → "
              f"修復後 中央 {np.median(a):.4f}(床 {floor:.4f})")
        print(f"  床を下回った位置 {int((a <= floor).sum())}/{len(a)}")
    else:
        print(f"  修復後の判定を断った: {err2}")

    if figs.enabled():
        figs.save_grid("sign_before_after", [rgb, fixed],
                       captions=["誤字入りの掲示(合成)", "置換後"],
                       title="誤字を見つけて置き換える",
                       caption=f"壊した {len(broken)} 字を検出して置き換えた。"
                               f"閾値は書体雑音の 95 % 点 {floor:.4f}。")
        xs = list(range(len(res)))
        figs.save_plot("cell_distance",
                       [("マスごとの距離", xs, [c["distance"] for c in res]),
                        ("書体雑音の床", xs, [floor] * len(res))],
                       xlabel="マスの位置", ylabel="骨格距離(99 % 点)",
                       title="どのマスが指定の字から離れているか",
                       caption="床を超えたマスが誤字。壊した位置は "
                               + ", ".join(str(i) for i in sorted(broken)) + "。")

    _real_images(floor, fonts)

    # ★合成に対する主張を固定する(真値は自分で植えたので厳密に測れる)。
    #   ここが割れたら、穴が塞がったか本当に壊れたかのどちらかで、
    #   assert を消して通すのはどちらでもない。
    assert fn == 0, f"壊した字を {fn} 本見逃した"
    assert fp == 0, f"無事な字を {fp} 本誤って咎めた"
    assert done == len(broken), f"置換できたのは {done}/{len(broken)}"
    assert after is not None, "修復後の判定を断った"
    assert float(np.median(a)) < float(np.median(b)), "置換しても指定の字に近づいていない"
    assert int((a <= floor).sum()) == len(a), "置換後に床を下回らない位置がある"

    print("
PASS: 合成の掲示で "
          f"壊した {len(broken)} 字を全部検出(誤検出 0)、全部置換して "
          f"距離が {np.median(b):.4f} → {np.median(a):.4f}(床 {floor:.4f})まで下がった")
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
