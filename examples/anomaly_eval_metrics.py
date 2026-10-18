# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""anomaly_eval_metrics — 画素 AUROC は大きな傷 1 つで満点近くになり、小さな傷の見落としを隠す。PRO はそれを出す。

    py -3.11 examples/anomaly_eval_metrics.py

【この例が示すこと】
欠陥図の方法を比べる物差し(``anomeval`` の 4 op)を、答えの分かっている合成の例で使う。
16 枚の画像に、大きな傷(1 枚 = 900 画素)と小さな傷(9 枚 × 4 画素)を描き、2 つの「検出器」の
スコアの図を作る:

* 検出器 A は大きな傷だけを見つけ、小さな傷は良品と同じスコアにする。
* 検出器 B は大きな傷を半分だけ、小さな傷は全部見つける。

画素 AUROC は**画素を数える**ので、900 画素の傷を当てた A が勝つ。PRO(Bergmann ら 2020)は
**傷を 1 つずつ数える**ので、10 個中 9 個を見落とした A は低く出る。どちらの指標が正しいかではなく、
「何を数えているか」が違う —— 小さな欠陥の見落としが致命的な検査では PRO を見る。

【グラウンドトゥルース】傷は自分で描いたので、検出器ごとの PRO は手で書ける:
A は FPR が小さい範囲で (1 + 0·9)/10 = 0.1、B は (0.5 + 1·9)/10 = 0.95。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fullseye as fs          # noqa: E402  公開経路(fs.ledger.<名前>)から呼ぶ

H = W = 64
N = 16


def make_case(seed=0):
    rng = np.random.default_rng(seed)
    masks = np.zeros((N, H, W), dtype=bool)
    masks[0, 10:40, 10:40] = True                         # 大きな傷 900 画素
    for i in range(1, 10):                                # 小さな傷 9 個 × 4 画素
        r, c = 8 + 5 * i, 50
        masks[i, r:r + 2, c:c + 2] = True
    base = rng.random((N, H, W))                          # 良品の地のスコア [0, 1)
    a = base.copy()
    a[0][masks[0]] += 2.0                                 # A: 大きな傷だけ
    b = base.copy()
    big = np.zeros_like(masks[0])
    big[10:40, 10:25] = True                              # B: 大きな傷の左半分
    b[0][big] += 2.0
    for i in range(1, 10):
        b[i][masks[i]] += 2.0                             # B: 小さな傷は全部
    labels = masks.reshape(N, -1).any(axis=1)
    return masks, a, b, labels


def main() -> int:
    masks, a, b, labels = make_case()
    rows = {}
    for name, s in (("A (大きな傷だけ)", a), ("B (小さな傷を全部)", b)):
        pa = fs.ledger.anomaly_pixel_auroc(s, masks)["auroc"]
        pr = fs.ledger.anomaly_pro(s, masks, fpr_max=0.3)
        img = fs.ledger.anomaly_image_auroc(s.reshape(N, -1).max(axis=1), labels)["auroc"]
        thr = fs.ledger.anomaly_region_overlap(s >= 1.5, masks, min_overlap=0.5)
        rows[name] = (pa, pr["aupro"], img, thr)
        print("%-18s 画素 AUROC %.3f  AUPRO(FPR<=0.3) %.3f  画像 AUROC %.3f  "
              "閾値 1.5 で見つけた傷 %d/%d(重なり 0.5 以上)"
              % (name, pa, pr["aupro"], img, round(thr["detected_fraction"] * thr["n_regions"]),
                 thr["n_regions"]))
    (pa_a, pro_a, _, thr_a), (pa_b, pro_b, _, thr_b) = rows.values()
    assert thr_a["n_regions"] == thr_b["n_regions"] == 10, "傷は 10 個描いた"
    ok = True
    # 画素を数えると A が勝ち、傷を数えると B が勝つ
    ok &= pa_a > pa_b
    ok &= pro_b > pro_a
    # 手計算: 閾値 1.5 の点の PRO は A = 0.1、B = 0.95(FPR は 0)
    ok &= abs(thr_a["pro"] - 0.1) < 1e-12 and abs(thr_b["pro"] - 0.95) < 1e-12
    ok &= thr_a["fpr"] == 0.0 and thr_b["fpr"] == 0.0
    # 面積は手計算の平台より下がらない(FPR 0 で既にその値に届いている)
    ok &= pro_a >= 0.1 - 1e-12 and pro_b >= 0.95 - 1e-12
    print("画素 AUROC は A が上 (%.3f > %.3f)、PRO は B が上 (%.3f > %.3f)" % (pa_a, pa_b, pro_b, pro_a))
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
