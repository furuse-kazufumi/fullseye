# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsspc — fullseye statistical-process-control op registry.

Motivation (2026-09-13): fullseye produces measurements from images (measure1d /
shapestat / imgmetrics / blob) but had no operator to answer the line's question —
*is this process in control, and is it capable?* This registry is that pathway
(spc.py, 17 ops / 7 categories). Every op is a closed-form textbook / standards model
with an exact identity to check it against, not a fitted model (see the thresholds
in the guide and ``tests/test_spc.py``).

Provenance is public standards and textbooks only (docs/PROVENANCE.md naming rule —
no product or company names): Shewhart 1931 (control chart) / ISO 8258:1991 (A2, D3,
D4 constants) / Page, *Biometrika* 1954 (CUSUM) / Kane, *J. Quality Technology* 1986
(Cp, Cpk) / Hotelling 1947 (T² multivariate control).

Coexistence with existing assets (compose, do not re-implement):
  * measurements come from measure1d / shapestat / imgmetrics / blob. SPC consumes
    their plain 1-D series (signal) and (m, p) matrices — it adds the *quality
    verdict*, not new measurement.
  * general statistics = statistics / multivariate. Those describe a sample; SPC
    charts it against control limits over time. `spc_hotelling_t2` needs an inverse
    covariance but does not re-wrap the general estimators — it uses numpy.cov and
    fail-closes on a singular matrix.

POD (2026-10-12): a measurement is only half of an inspection — the other half is *how
likely the system is to find a flaw of a given size*. The ``pod`` category (pod.py,
5 ops) is MIL-HDBK-1823A's answer: â vs a regression with left/right censoring, the
hit/miss GLM, a90/95 by the delta method and by the likelihood ratio, false-call
probability from unflawed sites, and the decision-threshold trade-off. Same table-in,
table-out shape as msa / gum, so no new type word.

Anomaly evaluation (2026-10-18): the ``anomaly_eval`` category (anomeval.py, 4 ops) is the
yard-stick every defect-map method is compared with — image AUROC, pixel AUROC, PRO / AUPRO
(per-region overlap integrated to FPR 0.3, Bergmann et al. 2020) and the per-region overlap at
one operating point. It depends on no detection method, only on score maps and masks, so the
variation model, RPCA, golden comparison and later patch-feature methods share one scorer.
Score / mask stacks are the existing ``video`` sort ((n, H, W)), per-image scores ``signal``;
every op returns a table, so no 2-D bridge is built (TYPE_TO_SORT has no ``table``).

Variation model (2026-10-18): the ``variation`` category (varmodel.py, 5 ops) is the classic
"learn every pixel's usual value and spread from aligned good samples, flag what leaves the band"
— with the band's half-width derived from a DECLARED per-pixel false-alarm rate (t prediction
interval / empirical-Bayes moderated t / a Monte-Carlo pivot for median-MAD), an alignment check
that refuses a misaligned stack (or registers it by a Fourier shift), shrinkage for few samples,
a robust variant for contaminated good sets, held-out calibration for real images, and a
per-region explanation in sigmas. Stacks are ``video``, one image ``image2d``, model and
results ``table``; every op returns a table, so no 2-D bridge is built.

Usage:
    import opsspc
    opsspc.list_ops("chart")
    opsspc.get("spc_xbar_r")(subgroups)
"""
import anomaly_patch
import anomeval
import pod
import spc
import varmodel

_MOD = {"spc": spc, "pod": pod, "anomeval": anomeval, "varmodel": varmodel, "anomaly_patch": anomaly_patch}

# --------------------------------------------------------------------------
# Type vocabulary: no new word is coined (it all fits the existing pool).
# --------------------------------------------------------------------------
#   * matrix  — `spc_xbar_r` eats (m, n) subgroups and `spc_hotelling_t2` eats
#     (m, p) observations: general 2-D numeric matrices (opsmath's matrix), not
#     images. Row/column shape is validated at call time (fail-closed).
#   * signal  — `spc_cusum` / `spc_capability` eat a 1-D measurement series, the
#     same sort measure1d / dsp produce and consume.
#   * table   — every op returns a dict of chart limits, statistics and the
#     out-of-control indices: the existing table sort.
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    "chart": [
        ("spc_xbar_r", "spc", ["matrix"], "table"),
    ],
    "change": [
        ("spc_cusum", "spc", ["signal"], "table"),
        ("spc_ewma", "spc", ["signal"], "table"),
    ],
    "capability": [
        ("spc_capability", "spc", ["signal"], "table"),
    ],
    "multivariate": [
        ("spc_hotelling_t2", "spc", ["matrix"], "table"),
    ],
    # MT 法(マハラノビス・タグチ)。Hotelling と同じ「相関した測定をまとめて見る」
    # 問いだが、基準が**既知良品の単位空間**で、尺度は分布の裾ではなく参照集団。
    # だから閾値(慣習的に 3)を製品を変えても持ち回せる。
    # ★単位空間の MD² の平均は **ちょうど (n-1)/n**(導出、当てはめではない)。
    #   教科書の「単位空間の距離は平均 1」を有限標本で正確に言い直したもので、
    #   1.0 を固定する試験はどんな標本でも間違い、(n-1)/n は全部で正しい。
    "mt": [
        ("spc_mt_unit_space", "spc", ["matrix"], "table"),
        ("spc_mt_distance", "spc", ["matrix"], "table"),
        # 項目選択の採点。異常標本の距離(1 次元)を受けて SN 比を返す。
        ("spc_mt_sn_ratio", "spc", ["signal"], "table"),
    ],
    # 測定システム解析。入力は「1 行 = 1 回の測定」の表(部品 / 測定者 / 値)で、
    # 返りも表 —— 新しい型の語は 1 つも要らない。
    "msa": [
        ("msa_anova_table", "spc", ["table"], "table"),
        ("msa_gauge_rr", "spc", ["table"], "table"),
        ("msa_bias_linearity", "spc", ["table"], "table"),
        ("msa_attribute_agreement", "spc", ["table"], "table"),
    ],
    # 測定の不確かさ(GUM)。成分の表 -> 合成不確かさ -> 拡張不確かさ、の 3 段と、
    # その独立な検算になるモンテカルロ。
    "uncertainty": [
        ("gum_standard_uncertainty", "spc", ["table"], "table"),
        ("gum_propagate", "spc", ["table"], "table"),
        ("gum_expanded", "spc", ["table"], "table"),
        ("gum_monte_carlo", "spc", ["table"], "table"),
        # 検証は**2 つの表を突き合わせる** —— 伝播則の結果とモンテカルロの結果。
        ("gum_validate", "spc", ["table", "table"], "table"),
    ],
    # 検出確率(POD、MIL-HDBK-1823A)。入力は「1 行 = 1 つの欠陥」の表(大きさ / 応答 or
    # 検出の有無)と、無欠陥部位の応答の 1-D 列(signal)。返りはすべて表。
    # ★新しい型の語は作らない。曲線(大きさの格子・POD・下限)も表の列として返す。
    # ★2-D の橋(tb_*)は架からない: 出力の table は backends_typed.TYPE_TO_SORT に
    #   写らないので _OP_BRIDGE_SKIP に入れる必要も無い(2026-10-12 に確認して決めた)。
    "pod": [
        ("pod_ahat_fit", "pod", ["table"], "table"),
        ("pod_from_ahat", "pod", ["table"], "table"),
        ("pod_hitmiss_fit", "pod", ["table"], "table"),
        ("pod_false_call", "pod", ["signal"], "table"),
        ("pod_decision_tradeoff", "pod", ["table", "signal"], "table"),
    ],
    # 異常検知の評価指標(anomeval.py)。どの欠陥図の方法にも依存しない物差し。
    # 入力: 画像ごとのスコアとラベルは 1-D(signal)、スコアの図とマスクの積み重ねは
    # (n, H, W) の video(新しい型の語は作らない)。返りは表なので 2-D の橋は架からない。
    "anomaly_eval": [
        ("anomaly_image_auroc", "anomeval", ["signal", "signal"], "table"),
        ("anomaly_pixel_auroc", "anomeval", ["video", "video"], "table"),
        ("anomaly_pro", "anomeval", ["video", "video"], "table"),
        ("anomaly_region_overlap", "anomeval", ["video", "video"], "table"),
        ("anomaly_pixel_f1_max", "anomeval", ["video", "video"], "table"),
        ("anomaly_image_f1_max", "anomeval", ["signal", "signal"], "table"),
        ("anomaly_operating_point", "anomeval", ["signal", "signal"], "table"),
    ],
    # パッチ特徴の異常検知(anomaly_patch.py)。古典特徴(勾配・Gabor・LBP・周波数帯・色)で良品から学ぶ。
    # 画像は image2d、良品の積み重ねは (n, H, W) の video、模型と結果は表。評価は anomaly_eval を使う。
    "anomaly_patch": [
        ("patch_features", "anomaly_patch", ["image2d"], "table"),
        ("patchdist_fit", "anomaly_patch", ["video"], "table"),
        ("patchdist_score", "anomaly_patch", ["image2d", "table"], "table"),
        ("patchbank_fit", "anomaly_patch", ["video"], "table"),
        ("patchbank_score", "anomaly_patch", ["image2d", "table"], "table"),
    ],
    # 良品統計の変動モデル(varmodel.py)。良品の積み重ねは video、試験の 1 枚は image2d、
    # 模型と結果は表。k は宣言した誤検出率から決まる(欠陥で調整しない)。
    # varmodel_band_k は入力の無い op(n と far だけから帯の幅)。
    "variation": [
        ("varmodel_alignment", "varmodel", ["video"], "table"),
        ("varmodel_band_k", "varmodel", [], "table"),
        ("varmodel_fit", "varmodel", ["video"], "table"),
        ("varmodel_calibrate", "varmodel", ["table", "video"], "table"),
        ("varmodel_score", "varmodel", ["image2d", "table"], "table"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = ""
            if fn is not None and fn.__doc__:
                doc = fn.__doc__.strip().splitlines()[0]
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSSPC = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSSPC.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**空 — 意図的に**。4 op はすべて宣言型どおり
#: (dict = table)を素で返すので、adapter を挟まないほうが連鎖ファザーの検証が
#: 最も厳しい(素の返りをそのまま宣言と突き合わせる)。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSSPC[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSSPC[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSSPC[name]


def missing():
    """レジストリに載っているが実体が見つからない op。"""
    return [n for n, m in OPSSPC.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"opsspc: {len(OPSSPC)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
