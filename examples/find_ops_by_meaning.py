# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 「やりたいこと」を 7 つの言語で書いて、同じ op にたどり着く(RAG の入口)。

やりたいこと: op の名前を知らないまま、母語で「エッジを検出したい」「ノイズを除きたい」と
書いて、使える op とそのノート(型の契約・呼び出し形・実行できる例)を引く。

使う関数: ``fullseye.search_ops``(コマンドなら ``fullseye-rag search "<言葉>"``、MCP なら
``fullseye_find_ops``)。索引は op の要約 6 言語(ja 原文 + en / zh / tw / ko / de の訳)と
名前・HALCON 名・型(hi は訳の方針で術語を英語のまま書くので、術語は英語で引く)。埋め込みも外部サービスも使わない(BM25、標準ライブラリだけ)。

検証(GT): 言語ごとに書いた同じ意味の問い合わせの上位 8 件に、その意味の op の集合
(エッジ = 勾配の大きさ / Canny 系、ノイズ = 平滑化・ノイズ除去系)のどれかが**全言語で**入る。
さらに、上位に出た op を**実際に呼んで**、エッジ op は段差の上で応答が最大になり、ノイズ op は
雑音の標準偏差を下げることを確かめる —— 検索が「それらしい名前」を返しただけでなく、返った op が
その仕事をすることまで見る。

beat-the-null: 知識層のノートを grep する零点との対比 —— ノートの本文は日本語なので、
「Rauschen」「降噪」「잡음」は grep で 0 件(2026-10-07 実測)。ここでは同じ言葉で op が並ぶ。
限界も正直に: 同義語は拾わない(要約が「偵測」と書いていれば「檢測」の当たりは弱い)ので、
当たりが薄いときは別の言い方か英語で引き直す。
"""
import numpy as np

import fullseye as fs

EDGE = {"canny3d", "sobel_mag", "sobel_amp", "prewitt_mag", "roberts_mag", "xpil_find_edges", "xkor_canny",
        "hx_detect_edge_segments", "xsp_gauss_grad_mag", "sk_canny", "edges_image", "roberts"}
NOISE = {"xsp_dct_denoise", "xcv3_denoise_tvl1", "cv_median", "sk_wavelet", "sk_tv", "sk_tv_bregman", "sk_nlm",
         "cv_nlmeans", "temporal_bilateral", "tb_temporal_bilateral", "bilateral_filter_depth", "median_image",
         "tb_mls_smooth", "mls_smooth", "ph_total_variation_flow", "xwt_firm_denoise", "remove_noise_region",
         "gray_opening_rect", "xmh_majority"}
QUERIES = {
    "edge": [("ja", "エッジ検出"), ("en", "edge detection"), ("zh", "边缘检测"), ("ko", "에지 검출"),
             ("de", "Kantenerkennung"), ("tw", "邊緣"), ("hi", "edge पहचान")],
    "noise": [("ja", "ノイズ除去"), ("en", "denoise"), ("zh", "去噪"), ("ko", "노이즈 제거"),
              ("de", "Rauschen entfernen"), ("tw", "雜訊去除"), ("hi", "noise हटाना")],
}


def main():
    print("== 1. 同じ意味を 7 言語で引く(上位 8 件のうち、その意味の op が何件あるか)")
    returned = {"edge": set(), "noise": set()}
    for concept, qs in QUERIES.items():
        want = EDGE if concept == "edge" else NOISE
        for lang, q in qs:
            r = fs.search_ops(q, k=8, lang=lang)
            names = [o["name"] for o in r["ops"]]
            good = [n for n in names if n in want]
            print("  [%s] %-20s -> %d/8  先頭: %s" % (lang, q, len(good), names[0] if names else "-"))
            if r["ops"]:
                print("        %s" % r["ops"][0]["summary"][:110].replace("\n", " "))
            assert good, "%s: %r の上位 8 件にその意味の op が無い: %s" % (lang, q, names)
            returned[concept].update(names)

    print("\n== 2. 返った op を実際に呼ぶ(検索が名前でなく仕事を当てたか)")
    assert "sobel_mag" in returned["edge"] and "cv_median" in returned["noise"], returned
    step = np.zeros((32, 32))
    step[:, 16:] = 1.0
    e = np.asarray(fs.apply(step, "sobel_mag", 0.5, 0.5), float)
    col = int(np.argmax(e.mean(axis=0)))
    print("  sobel_mag: 段差の列 15/16 に対し応答の最大は列 %d" % col)
    assert col in (15, 16)
    rng = np.random.default_rng(0)
    noisy = np.clip(0.5 + 0.1 * rng.standard_normal((48, 48)), 0, 1)
    d = np.asarray(fs.apply(noisy, "cv_median", 0.5, 0.5), float)
    print("  cv_median: 雑音の標準偏差 %.4f -> %.4f" % (noisy.std(), d.std()))
    assert d.std() < 0.8 * noisy.std()

    print("\n== 3. 名前を知っていれば先頭に来る / 言葉が無ければ hint")
    r = fs.search_ops("otsu", k=3)
    print("  'otsu' -> %s" % [o["name"] for o in r["ops"]])
    assert r["ops"][0]["name"] == "otsu"
    r = fs.search_ops("qqqzzzxx", k=3)
    print("  'qqqzzzxx' -> %d 件、hint: %s" % (r["total"], r["hint"]))
    assert r["total"] == 0 and r["hint"]
    print("\nPASS")


if __name__ == "__main__":
    main()
