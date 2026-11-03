# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: ロット番号のインクジェット印字を古典的な OCR で読む —— 可読性の POD と、誤読を数える意味。

    PYTHONPATH=. py -3.11 examples/poc_symbol_lot_ocr.py

食品・医薬の包装に連続式インクジェット(CIJ)で打つ 5x7 ドットのロット番号・期限と、
部品ラベルに熱転写で打つ線の文字を**合成で**作る(真値 = 描いた文字列そのもの)。
学習は Deep Learning でなく古典(k 最近傍 + 区画濃度と射影の特徴量、学習の分布から
決めた棄却)。字種は 0-9 A-Z - . / :。

見せたいこと(数字はすべてこの実行で測ったもの):

1. きれいな印字は両方の書体で全件読める。切り出しの外接箱は描いた真値と一致する。
2. 字種の外の字(手で足した ``#``)は**棄却**され、別の字に化けない。
3. ★可読性の POD: デフォーカスと字高を掃引し、「90 % の行を 1 字も違えず読める限界」
   (d90 / d90/95、h90 / h90/95)を出す。読み取りの POD と同じ鎖(``symbol_read_pod``)。
4. ★★誤読を別に数える: ぼけが学習の範囲(〜0.14 字高)を越えると、距離による棄却が
   効かなくなって**誤読**(別の字に読む)が増える。ロット番号の誤読は回収の範囲を
   取り違える事故なので、「読めた率」と「誤読率」を 1 つにしない。誤読の片側上限も出す。
5. 線の書体は同じぼけでドットより長く読める(線は点より低い空間周波数で太い)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

L = fs.ledger
FAIL = []
LOT = "LOT2611A-0731"
EXP = "EXP2027/11/03"


def check(ok, label, detail=""):
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))
    if not ok:
        FAIL.append(label)


def main():
    t0 = time.time()
    print("=" * 76)
    print("PoC: ロット番号の CIJ 印字を古典 OCR で読む —— 可読性の POD と誤読の数え方")
    print("=" * 76)
    font = L.ocr_font("dot5x7")
    print("  書体 %s、字種 %d 字: %s" % (font["name"], len(font["charset"]), font["charset"]))
    models = {f: L.ocr_train(f) for f in ("dot5x7", "stroke")}
    print("  学習の型: dot5x7 %d 個 / stroke %d 個" % tuple(len(models[f]["labels"]) for f in models))

    print("\n[1] きれいな印字")
    for f in ("dot5x7", "stroke"):
        for txt in (LOT, EXP):
            r = L.ocr_render_text(txt, font=f, char_height_px=24)
            seg = L.ocr_segment_line(r["image"])
            got = L.ocr_read_line(r["image"], models[f])
            ious = []
            for (a0, b0, a1, b1), (c0, d0, c1, d1) in zip(seg["boxes"], r["boxes"]):
                inter = max(0, min(a1, c1) - max(a0, c0)) * max(0, min(b1, d1) - max(b0, d0))
                uni = (a1 - a0) * (b1 - b0) + (c1 - c0) * (d1 - d0) - inter
                ious.append(inter / uni)
            check(got["text"] == txt and len(seg["boxes"]) == len(txt) and min(ious) > 0.7,
                  "%s %s を読む" % (f, txt), "(外接箱の IoU 最小 %.2f)" % min(ious))
    feats = L.ocr_features(L.ocr_render_text("8", char_height_px=32)["image"])
    cl = L.ocr_classify(np.atleast_2d(feats), models["dot5x7"])
    print("  1 字の特徴量 %d 次元、識別 %s(距離比 %.2f)" % (feats.size, cl["labels"], cl["margin"][0]))

    print("\n[2] 字種の外の字は棄却する")
    f2 = L.ocr_font("dot5x7")
    f2 = dict(f2, glyphs=dict(f2["glyphs"]), charset=f2["charset"] + "#")
    f2["glyphs"]["#"] = np.array([[0, 1, 0, 1, 0], [0, 1, 0, 1, 0], [1, 1, 1, 1, 1], [0, 1, 0, 1, 0],
                                  [1, 1, 1, 1, 1], [0, 1, 0, 1, 0], [0, 1, 0, 1, 0]], np.uint8)
    img = L.ocr_render_text("LOT#42", font=f2, char_height_px=24)["image"]
    got = L.ocr_read_line(img, models["dot5x7"])["text"]
    sc = L.ocr_score(got, "LOT#42")
    print("  'LOT#42' → %r(正解 %d、棄却 %d、誤読 %d)" % (got, sc["correct"], sc["rejected"],
                                                       sc["substituted"]))
    check(sc["substituted"] == 0 and sc["rejected"] == 1, "'#' は ? になり、別の字に化けない")

    print("\n[3] 可読性の POD(13 字の行、雑音 20000 e / 10 e、揺らぎ 5 %)")
    res = {}
    for f in ("dot5x7", "stroke"):
        tr = L.ocr_read_trials(LOT, "defocus_px", np.linspace(1.0, 16.0, 7), model=models[f],
                               font=f, char_height_px=24, trials=24, refine=True,
                               level_jitter=0.05, seed=5)
        p = L.symbol_read_pod(tr)
        res[f] = (tr, p)
        print("  %-7s デフォーカス: %s  d50 %.2f  d90 %.2f  d90/95 %.2f px(字高 24 px)"
              "  誤読 %d 行 / 文字列を返した %d 行、単調 %s"
              % (f, p["method"], p["level50"] or np.nan, p["level90"] or np.nan,
                 p["level90_95"] or np.nan, p["misread_total"], p["decoded_total"] + 0,
                 p["monotone"]))
    pd, ps = res["dot5x7"][1], res["stroke"][1]
    check(pd["method"] == "hitmiss_glm" and pd["level90_95"] < pd["level90"] < pd["level50"],
          "ドットの POD: d90/95 < d90 < d50")
    check(ps["level90"] > pd["level90"], "線の書体はドットより大きなぼけまで読める",
          "(%.2f > %.2f px)" % (ps["level90"], pd["level90"]))
    trh = L.ocr_read_trials(LOT, "char_height_px", np.linspace(6.0, 20.0, 7), model=models["dot5x7"],
                            font="dot5x7", trials=24, capture={"gauss_px": 1.0}, refine=True,
                            level_jitter=0.05, seed=6)
    ph = L.symbol_read_pod(trh)
    print("  dot5x7  字高(ぼけ σ 1.0 px): %s  h50 %s  h90 %s  h90/95 %s px"
          % (ph["method"], *("%.2f" % v if v is not None else "-"
                             for v in (ph["level50"], ph["level90"], ph["level90_95"]))))
    if ph["method"] == "hitmiss_glm":
        check(ph["level50"] < ph["level90"] < ph["level90_95"], "字高は大きいほど良い: h50 < h90 < h90/95")
    else:
        check(ph["level90_95"] is not None, "字高: 全数成功の実証", str(ph["separation_bracket"]))

    print("\n[4] 誤読の数え方(ドット、水準ごと)")
    tr = res["dot5x7"][0]
    for d in res["dot5x7"][1]["per_level"]:
        if d["n"] >= 20:
            m = tr["level"] == d["level"]
            print("  直径 %5.2f px(%.2f 字高): 読めた %2d / 誤読 %2d / 不能 %2d(棄却した字 %d、置換した字 %d)"
                  % (d["level"], d["level"] / 24.0, d["hits"], d["misreads"], d["noreads"],
                     int(tr["rejected_chars"][m].sum()), int(tr["substituted_chars"][m].sum())))
    print("  誤読の片側 95 %% 上限(誤読 / 1 字以上返した行): %.3f" % pd["misread_rate_upper"])
    mild = [d for d in pd["per_level"] if d["level"] <= pd["level90"]]
    check(sum(d["misreads"] for d in mild) == 0, "d90 までのぼけでは誤読 0 行")
    worst = max(pd["per_level"], key=lambda d: d["level"])
    print("  ★最も強いぼけ(%.1f px)では誤読 %d / %d 行 —— 学習の範囲を越えたぼけは"
          "距離の棄却で拾い切れない(ocrclassic の限界、隠さない)" % (worst["level"],
                                                          worst["misreads"], worst["n"]))

    # 図: ロット番号(くっきり / d90 / 強いぼけ)と水準ごとの読めた・誤読・不能
    if figs.enabled():
        shots = []
        for d in (0.0, float(pd["level90"]), 13.5):
            img = L.ocr_render_text(LOT, font="dot5x7", char_height_px=24)["image"]
            shots.append(L.capture_degrade(img, defocus_px=d, full_well_e=20000.0, read_noise_e=10.0,
                                           bits=8, seed=2))
        figs.save_grid("lot_ocr_defocus", shots,
                       ["くっきり", "d90 = %.1f px" % pd["level90"], "13.5 px(誤読が増える)"],
                       ncols=1, gray=True, vrange=(0.0, 1.0), title="5x7 ドットのロット番号",
                       caption="学習の範囲を越えたぼけでは棄却が効かず、誤読が増える。")
        figs.save_table("lot_ocr_levels", ["直径 [px]", "行", "読めた", "誤読", "不能"],
                        [["%.2f" % d["level"], d["n"], d["hits"], d["misreads"], d["noreads"]]
                         for d in pd["per_level"]], title="可読性(dot5x7、字高 24 px)")
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\n%.0f 秒。" % (time.time() - t0))
    if FAIL:
        print("FAIL: %s" % FAIL)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
