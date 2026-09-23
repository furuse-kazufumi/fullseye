# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""MSA(測定システム解析)と GUM(測定の不確かさ)の 8 op を、**絵の外**から採点する。

採点の出どころは 3 つだけ —— ① 代数的な恒等式(分解・定義)② 解析的に別経路で
出せる値(マルコフ鎖のエントロピー率にあたるもの = 期待平均平方・Welch-Satterthwaite)
③ **構成上答えを知っているデータ**(仕込んだ偏り・既知の全単射)。使った式でそのまま
答え合わせをする検査は 1 つも置いていない。

★この検査を書いたとき、**落ちた 5 件はすべて期待のほうが誤っていた**(op の欠陥は 0)。
記録として残す:

  * 繰り返し性が 0.4 に対し 0.3798 —— 偏りでなく揺れ。種 40 本で平均 0.39710 /
    標準偏差 0.00788、理論 ``sigma/sqrt(2 df)`` が 0.00913(df=960)。1 本の種に
    1 % の精度を求めた許容が狭すぎただけだった。
  * 「負の分散成分は稀」—— 逆。真値 0 のとき **40 本中 31 本**で負になる。
  * 「完全適合なら t = inf」—— 残差は浮動小数なので厳密に 0 にならず 1e14 級の有限値。
  * 寄与の合計に絶対許容 1e-18 —— 値が 0.06 なら eps でも 1.3e-17 で、狭すぎた。
  * 「矩形 1 成分の 95 % 区間の半幅 = 支持の端 a」—— 正しくは **0.95 a**
    (95 % ぶんの幅しか要らない)。直したら一致が 4e-4 まで締まり、門が強くなった。
"""
import numpy as np
import pytest

import opsspc
import spc


def _rr_table(p=10, o=3, r=3, sd_part=1.0, sd_oper=0.2, sd_err=0.3, seed=0):
    """部品 x 測定者 x 繰り返しの釣り合った表を、**分散成分を指定して**作る。

    ★乱数だけの表は対称性の破れを隠すので、成分ごとに**違う大きさ**を与えて、
    どの成分がどこに出るかを追えるようにする。
    """
    rng = np.random.default_rng(seed)
    a = rng.normal(0.0, sd_part, p)
    b = rng.normal(0.0, sd_oper, o) if sd_oper > 0 else np.zeros(o)
    part, oper, val = [], [], []
    for i in range(p):
        for j in range(o):
            for _ in range(r):
                part.append("P%02d" % i)
                oper.append("A%d" % j)
                val.append(10.0 + a[i] + b[j] + rng.normal(0.0, sd_err))
    return {"part": np.array(part, dtype=object),
            "operator": np.array(oper, dtype=object),
            "value": np.array(val, dtype=np.float64)}


# --------------------------------------------------------------------------- #
# 1. 分散分析: 代数的な恒等式(分散成分の出し方と独立)
# --------------------------------------------------------------------------- #
def test_the_sums_of_squares_close_exactly():
    """``SS_total == SS_part + SS_oper + SS_inter + SS_err``。

    これは分解の代数そのものなので、分散成分をどう導こうと必ず成り立つ。片方が
    壊れれば一致しない = **推定の正しさとは別の層**で実装を押さえられる。
    """
    A = spc.msa_anova_table(_rr_table(seed=1))
    ss = dict(zip(A["source"], A["ss"]))
    df = dict(zip(A["source"], A["df"]))
    parts = ss["part"] + ss["operator"] + ss["interaction"] + ss["repeatability"]
    assert abs(parts - ss["total"]) < 1e-12 * ss["total"], (
        "平方和が閉じない: 部分の和 %.12g vs 全体 %.12g" % (parts, ss["total"]))
    assert df["total"] == (df["part"] + df["operator"] + df["interaction"]
                           + df["repeatability"])


def test_repeatability_equals_the_pooled_within_cell_variance_numpy_computes():
    """★**既存実装(numpy)が真値**: 繰り返し性は升目ごとの標本分散の平均に厳密一致。

    期待平均平方から導いた ``var_repeat = MS_err`` は、釣り合った設計では
    「各升目の ``np.var(ddof=1)`` の平均」に**代数的に等しい**。導出も実装も別なので、
    片方が壊れれば一致しない。
    """
    p, o, r = 10, 3, 3
    t = _rr_table(p=p, o=o, r=r, seed=1)
    cells = t["value"].reshape(p, o, r)
    by_cell = np.array([[np.var(cells[i, j], ddof=1) for j in range(o)]
                        for i in range(p)])
    # ★この恒等式は**交互作用を残すモデル**の性質なので、モデルを明示して問う。
    #   既定の "auto" は規格の手順に従って交互作用を誤差へ畳むことがあり、そのとき
    #   EV^2 は「升目ごとの分散の平均」ではなく「畳んだあとの平均平方」になる。
    #   (この門は実際にその切替を捕まえた —— 既定を変えた瞬間に落ちた)
    ev = float(spc.msa_gauge_rr(t, pool_interaction=False)["sigma"][0])
    assert abs(ev ** 2 - by_cell.mean()) < 1e-12 * by_cell.mean(), (
        "EV^2 %.12g が升目ごと標本分散の平均 %.12g と違う" % (ev ** 2, by_cell.mean()))


#: 分散分析表で **値が存在しない**セル(行, 列)。ここ以外に非有限が出たら欠陥。
#:
#: ★★連鎖ファザーが ``msa_anova_table`` の NONFINITE を実検出した(2026-09-23)。
#: 正しい対処は「この op の非有限を許す」ではなく「**どこに出るかを宣言する**」
#: こと —— 丸ごと許すと二度と鳴らない門になり、将来 0 除算や自由度計算の誤りで
#: 部品行や測定者行に NaN が漏れても捕まえられなくなる。
#:
#:   残差の F / p     —— F = MS/MS_error の**分母そのもの**なので検定できない
#:   全体の F / p / ms —— 平方和の合計行で、検定対象の効果ではない
#:   交互作用(測定者 1 人)—— df = (p-1)(o-1) が 0 で推定量が存在しない
_ANOVA_NAN_CELLS = {("repeatability", "f"), ("repeatability", "p"),
                    ("total", "f"), ("total", "p"), ("total", "ms")}


def test_the_anova_table_is_non_finite_only_where_the_statistic_does_not_exist():
    """★**NaN は宣言したセルにだけ**。宣言外に出たら失敗する門。"""
    A = spc.msa_anova_table(_rr_table(seed=4))
    src = list(A["source"])
    bad = []
    for col in ("ss", "df", "ms", "f", "p"):
        for row, v in zip(src, A[col]):
            if not np.isfinite(float(v)) and (row, col) not in _ANOVA_NAN_CELLS:
                bad.append((row, col, float(v)))
    assert not bad, "宣言していないセルに非有限が出た: %s" % bad
    # 宣言したセルは**実際に**非有限であること(宣言が空を通していない)
    for row, col in _ANOVA_NAN_CELLS:
        i = src.index(row)
        assert not np.isfinite(float(A[col][i])), (
            "(%s, %s) を NaN と宣言したのに有限値 %s が出ている —— 宣言が古い"
            % (row, col, A[col][i]))


def test_with_a_single_operator_the_interaction_cells_are_the_ones_that_vanish():
    """測定者 1 人では交互作用の自由度が 0 —— そこだけ追加で非有限になる。"""
    A = spc.msa_anova_table(_rr_table(o=1, seed=4))
    src = list(A["source"])
    i = src.index("interaction")
    assert A["df"][i] == 0
    for col in ("ms", "f", "p"):
        assert not np.isfinite(float(A[col][i])), (
            "測定者 1 人なのに交互作用の %s が有限(%s)" % (col, A[col][i]))
    # 部品と残差は**有限のまま**(全部 NaN にする実装なら、ここで落ちる)
    for row in ("part", "repeatability"):
        j = src.index(row)
        assert np.isfinite(float(A["ss"][j])) and np.isfinite(float(A["ms"][j]))


def test_the_anova_table_satisfies_its_internal_identities_on_arbitrary_input():
    """★表の**内部恒等式**を任意の入力で固定する(公表例題とは独立の門)。

    加法性(SS と df)・``MS = SS/df``・``F = MS_effect / MS_error``。公表値の門が
    「外から見て正しい」を見るのに対し、こちらは「中で辻褄が合っている」を見る
    —— 表は両側から挟まれる。
    """
    rng = np.random.default_rng(9)
    for trial in range(6):
        t = _rr_table(p=int(rng.integers(3, 9)), o=int(rng.integers(2, 5)),
                      r=int(rng.integers(2, 5)), sd_part=float(rng.uniform(0.2, 3.0)),
                      sd_oper=float(rng.uniform(0.0, 1.0)),
                      sd_err=float(rng.uniform(0.05, 1.0)), seed=trial)
        A = spc.msa_anova_table(t)
        src = list(A["source"])
        ss = dict(zip(src, A["ss"]))
        df = dict(zip(src, A["df"]))
        ms = dict(zip(src, A["ms"]))
        eff = ("part", "operator", "interaction", "repeatability")
        assert abs(sum(ss[e] for e in eff) - ss["total"]) < 1e-10 * max(ss["total"], 1.0)
        assert sum(df[e] for e in eff) == df["total"]
        for e in eff:
            if df[e] > 0:
                assert abs(ms[e] - ss[e] / df[e]) < 1e-12 * max(abs(ms[e]), 1.0), (
                    "MS = SS/df が成り立たない(%s)" % e)
        # F は交互作用平均平方で検定する(規格の慣行)。定義される行だけ。
        f = dict(zip(src, A["f"]))
        if df["interaction"] > 0:
            for e in ("part", "operator"):
                assert abs(f[e] - ms[e] / ms["interaction"]) < 1e-10 * max(abs(f[e]), 1.0)
            assert abs(f["interaction"]
                       - ms["interaction"] / ms["repeatability"]) < 1e-10 * max(abs(f["interaction"]), 1.0)


# --------------------------------------------------------------------------- #
# 2. ゲージ R&R: 定義そのものの関係
# --------------------------------------------------------------------------- #
def test_the_variance_components_add_up_the_way_the_definitions_say():
    G = spc.msa_gauge_rr(_rr_table(seed=2))
    s = dict(zip(G["component"], G["sigma"]))
    assert abs(s["gauge_rr"] ** 2 - (s["repeatability"] ** 2 + s["reproducibility"] ** 2)) < 1e-12
    assert abs(s["total"] ** 2 - (s["gauge_rr"] ** 2 + s["part"] ** 2)) < 1e-12
    pc = dict(zip(G["component"], G["pct_contribution"]))
    assert abs(pc["gauge_rr"] + pc["part"] - 100.0) < 1e-9, (
        "寄与率が 100 %% にならない: %.9f" % (pc["gauge_rr"] + pc["part"]))
    assert abs(G["ndc"][0] - 1.41 * s["part"] / s["gauge_rr"]) < 1e-12
    assert abs(G["pct_grr"][0] - 100.0 * s["gauge_rr"] / s["total"]) < 1e-12


def test_the_estimator_lands_within_the_spread_theory_predicts():
    """仕込んだ成分を取り戻す —— ただし**理論の揺れで採点**する。

    ★「0.4 に対し 0.02 以内」のような絶対値の許容は根拠が無い。釣り合った計画では
    ``sigma`` の推定の揺れは ``sigma/sqrt(2 df)`` なので、それを基準にする
    (種 40 本の実測: 平均 0.39710 / 標準偏差 0.00788、理論 0.00913)。
    """
    p, o, r = 60, 4, 5
    t = _rr_table(p=p, o=o, r=r, sd_part=2.0, sd_oper=0.5, sd_err=0.4, seed=7)
    s = dict(zip(*(spc.msa_gauge_rr(t)[k] for k in ("component", "sigma"))))
    sd_theory = 0.4 / np.sqrt(2 * p * o * (r - 1))
    assert abs(s["repeatability"] - 0.4) < 4 * sd_theory, (
        "繰り返し性 %.4f が理論の揺れ %.5f の 4 倍を超えてずれている"
        % (s["repeatability"], sd_theory))
    # 部品と再現性は自由度が桁違いに小さいので、桁が合うことだけを見る
    assert 1.5 < s["part"] < 2.5
    assert 0.1 < s["reproducibility"] < 1.0


def test_a_control_group_without_operator_effect_collapses_the_reproducibility():
    """対照群: 測定者差を**厳密に 0** にすると再現性が桁で落ちること。"""
    kw = dict(p=60, o=4, r=5, sd_part=2.0, sd_err=0.4, seed=7)
    with_op = dict(zip(*(spc.msa_gauge_rr(_rr_table(sd_oper=0.5, **kw))[k]
                         for k in ("component", "sigma"))))
    without = dict(zip(*(spc.msa_gauge_rr(_rr_table(sd_oper=0.0, **kw))[k]
                         for k in ("component", "sigma"))))
    assert without["reproducibility"] < with_op["reproducibility"] / 5.0, (
        "測定者差を消しても再現性が落ちない: %.4f -> %.4f"
        % (with_op["reproducibility"], without["reproducibility"]))


def test_a_negative_variance_component_is_the_normal_case_and_is_declared():
    """★**負の分散成分は稀な端ではない**。真値 0 なら多数派で出る(40 本中 31 本)。

    期待平均平方の差は推定量なので、真の成分が 0 に近いと半分前後は負になる。
    0 に丸めるのは妥当だが、**丸めたことを申告しない実装は「差は無い」と言い切る**
    —— 正しくは「推定できなかった」。``clamped`` 列がその申告。
    """
    negs = sum(bool(spc.msa_gauge_rr(
        _rr_table(p=60, o=4, r=5, sd_part=2.0, sd_oper=0.0, sd_err=0.4, seed=s)
    )["clamped"][1]) for s in range(40))
    assert negs > 20, (
        "真値 0 なのに負の成分が 40 本中 %d 本しか出ない —— 丸めの申告が働いていないか、"
        "分散成分の導出が違う" % negs)


def test_an_unbalanced_design_is_refused_rather_than_silently_answered():
    """釣り合っていない表は**拒む**(黙って別の量を返さない)。"""
    t = _rr_table(seed=3)
    short = {k: v[:-1] for k, v in t.items()}
    with pytest.raises(ValueError, match="unbalanced"):
        spc.msa_gauge_rr(short)


def test_one_measurement_per_cell_leaves_nothing_to_estimate_repeatability_with():
    t = _rr_table(r=1, seed=3)
    with pytest.raises(ValueError, match="replicate"):
        spc.msa_gauge_rr(t)


# --------------------------------------------------------------------------- #
# 3. 偏りと直線性
# --------------------------------------------------------------------------- #
def test_a_noiseless_line_is_recovered_exactly():
    """雑音 0 の ``bias = a + b*ref`` は最小二乗が厳密に取り戻す。"""
    ref = np.repeat([1.0, 2.0, 3.0, 4.0, 5.0], 6)
    a0, b0 = 0.07, -0.013
    B = spc.msa_bias_linearity({"reference": ref, "measured": ref + a0 + b0 * ref})
    co = dict(zip(B["term"], B["coef"]))
    assert abs(co["intercept"] - a0) < 1e-12
    assert abs(co["slope"] - b0) < 1e-12
    assert abs(B["bias_overall"][0] - (a0 + b0 * ref).mean()) < 1e-14


def test_a_perfect_fit_reports_a_huge_t_not_a_broken_one():
    """★完全適合の ``t`` は ``inf`` ではなく **1e14 級の有限値**(残差が浮動小数)。

    ここを ``inf`` で待つと、op が正しいのに落ちる。最初そう書いて落とした。
    """
    ref = np.repeat([1.0, 2.0, 3.0, 4.0, 5.0], 6)
    B = spc.msa_bias_linearity({"reference": ref, "measured": ref + 0.07 - 0.013 * ref})
    assert abs(B["t"][1]) > 1e10
    assert B["p"][1] == 0.0


def test_a_constant_bias_has_no_slope():
    """対照群: 偏りが基準値に依らなければ傾きは 0。"""
    ref = np.repeat([1.0, 2.0, 3.0, 4.0, 5.0], 6)
    B = spc.msa_bias_linearity({"reference": ref, "measured": ref + 0.07})
    assert abs(dict(zip(B["term"], B["coef"]))["slope"]) < 1e-14


def test_a_single_reference_is_refused_because_the_slope_is_not_estimable():
    with pytest.raises(ValueError, match="not estimable|linearity study"):
        spc.msa_bias_linearity({"reference": np.ones(10), "measured": np.ones(10) + 0.1})


# --------------------------------------------------------------------------- #
# 4. 計数値検査の一致度(カッパ)
# --------------------------------------------------------------------------- #
def test_identical_appraisals_give_kappa_exactly_one():
    parts = np.array(["p%02d" % i for i in range(50)])
    rating = np.where(np.arange(50) < 45, "pass", "fail")
    K = spc.msa_attribute_agreement({"appraiser": np.repeat(["A", "B"], 50),
                                     "part": np.tile(parts, 2),
                                     "rating": np.tile(rating, 2)})
    assert abs(K["kappa"][0] - 1.0) < 1e-15
    assert abs(K["fleiss_kappa"][0] - 1.0) < 1e-12


def test_cohen_kappa_matches_the_closed_form_for_two_raters_and_two_categories():
    """★2x2 の閉形式 ``2(ad-bc)/((a+b)(b+d)+(a+c)(c+d))`` と一致すること。

    実装は一般の k x k の ``(p_o - p_e)/(1 - p_e)`` なので、2x2 の閉形式は
    **別の式**であり、答え合わせに使える。
    """
    rng = np.random.default_rng(3)
    ra = np.where(rng.random(200) < 0.9, "pass", "fail")
    rb = np.where(rng.random(200) < 0.9, "pass", "fail")
    parts = np.array(["q%03d" % i for i in range(200)])
    K = spc.msa_attribute_agreement({"appraiser": np.repeat(["A", "B"], 200),
                                     "part": np.tile(parts, 2),
                                     "rating": np.concatenate([ra, rb])})
    a = int(((ra == "fail") & (rb == "fail")).sum())
    b = int(((ra == "fail") & (rb == "pass")).sum())
    c = int(((ra == "pass") & (rb == "fail")).sum())
    d = int(((ra == "pass") & (rb == "pass")).sum())
    closed = 2.0 * (a * d - b * c) / ((a + b) * (b + d) + (a + c) * (c + d))
    assert abs(K["kappa"][0] - closed) < 1e-12


def test_a_high_agreement_rate_can_still_mean_no_agreement_at_all():
    """★**これがこの op の存在理由**。合格率が高い工程では、でたらめに判を押しても
    素の一致率は 8 割を超える。カッパはそれを 0 付近まで割り引く。
    """
    rng = np.random.default_rng(3)
    ra = np.where(rng.random(200) < 0.9, "pass", "fail")
    rb = np.where(rng.random(200) < 0.9, "pass", "fail")
    parts = np.array(["q%03d" % i for i in range(200)])
    K = spc.msa_attribute_agreement({"appraiser": np.repeat(["A", "B"], 200),
                                     "part": np.tile(parts, 2),
                                     "rating": np.concatenate([ra, rb])})
    assert K["observed_agreement"][0] > 0.80, "この対照群の作り方が壊れている"
    assert abs(K["kappa"][0]) < 0.25, (
        "独立な判定なのに kappa が %.3f —— 偶然の一致を割り引けていない" % K["kappa"][0])


def test_repeated_appraisals_are_refused_rather_than_silently_reduced():
    """同じ人が同じ部品を 2 回見ている表は拒む(どの回を採るかで答えが変わる)。"""
    with pytest.raises(ValueError, match="more than once"):
        spc.msa_attribute_agreement({"appraiser": ["A", "A", "B", "B"],
                                     "part": ["p1", "p1", "p1", "p2"],
                                     "rating": ["pass", "fail", "pass", "pass"]})


# --------------------------------------------------------------------------- #
# 5. GUM: 分布の形 -> 標準不確かさ
# --------------------------------------------------------------------------- #
def test_the_divisors_are_the_exact_standard_deviations_of_those_distributions():
    S = spc.gum_standard_uncertainty(
        {"halfwidth": [1.0, 1.0, 1.0, 1.0],
         "distribution": ["rectangular", "triangular", "u_shaped", "normal_95"]})
    want = [1 / np.sqrt(3), 1 / np.sqrt(6), 1 / np.sqrt(2), 1 / 1.959963984540054]
    assert np.allclose(S["u"], want, atol=1e-15), (
        "分布ごとの除数が分散の定義と合わない: %s" % S["u"])


def test_an_unnamed_distribution_is_refused_instead_of_defaulted():
    """★**既定の分布を置かない**。矩形を既定にすると、形を書き忘れた成分が黙って
    ``a/sqrt(3)`` になり、三角のつもりなら 1.41 倍ずれた不確かさが例外なしで流れる。
    """
    with pytest.raises(ValueError, match="unknown distribution"):
        spc.gum_standard_uncertainty({"halfwidth": [1.0], "distribution": ["gaussian-ish"]})


# --------------------------------------------------------------------------- #
# 6. GUM: 伝播則
# --------------------------------------------------------------------------- #
def test_the_product_rule_matches_the_closed_form():
    """``f = x y`` の相対不確かさは二乗和 —— 閉形式と厳密に一致する。"""
    x, y, ux, uy = 4.0, 7.0, 0.02, 0.05
    P = spc.gum_propagate({"u": [ux, uy], "sensitivity": [y, x]})
    assert abs(P["u_combined"][0] / (x * y) - np.hypot(ux / x, uy / y)) < 1e-15


def test_perfect_correlation_adds_and_perfect_anticorrelation_cancels():
    """``r = +1`` で ``|c1u1 + c2u2|``、``r = -1`` で ``|c1u1 - c2u2|`` に厳密一致。"""
    tab = {"u": [0.3, 0.4], "sensitivity": [1.0, 1.0]}
    up = spc.gum_propagate(tab, correlation=np.array([[1.0, 1.0], [1.0, 1.0]]))
    um = spc.gum_propagate(tab, correlation=np.array([[1.0, -1.0], [-1.0, 1.0]]))
    assert abs(up["u_combined"][0] - 0.7) < 1e-12
    assert abs(um["u_combined"][0] - 0.1) < 1e-12


def test_the_contributions_close_on_the_combined_variance_when_uncorrelated():
    P = spc.gum_propagate({"u": [0.02, 0.05], "sensitivity": [7.0, 4.0]})
    uc2 = P["u_combined"][0] ** 2
    assert abs(P["contribution"].sum() - uc2) < 1e-15 * uc2


def test_an_impossible_correlation_matrix_is_refused():
    with pytest.raises(ValueError, match=r"\[-1, 1\]"):
        spc.gum_propagate({"u": [1.0, 1.0], "sensitivity": [1.0, 1.0]},
                          correlation=np.array([[1.0, -2.0], [-2.0, 1.0]]))


# --------------------------------------------------------------------------- #
# 7. GUM: Welch-Satterthwaite
# --------------------------------------------------------------------------- #
def test_a_single_component_keeps_its_own_degrees_of_freedom():
    E = spc.gum_expanded({"u": [0.5], "sensitivity": [1.0], "dof": [7.0]})
    assert abs(E["dof_effective"][0] - 7.0) < 1e-12


def test_the_effective_dof_is_never_below_the_smallest_one():
    """★**定理**: ``nu_eff >= min nu``。

    証明: ``sum u_i^4/nu_i <= (1/nu_min) sum u_i^4 <= (1/nu_min) (sum u_i^2)^2``
    なので ``nu_eff = u_c^4 / sum(...) >= nu_min``。破れたら計算が壊れている。
    """
    rng = np.random.default_rng(11)
    for _ in range(50):
        n = int(rng.integers(2, 6))
        u = rng.uniform(0.05, 1.0, n)
        c = rng.uniform(-3.0, 3.0, n)
        nu = rng.uniform(2.0, 50.0, n)
        E = spc.gum_expanded({"u": u, "sensitivity": c, "dof": nu})
        assert E["dof_effective"][0] >= nu.min() - 1e-9, (
            "nu_eff %.6f が min(nu) %.6f を下回った" % (E["dof_effective"][0], nu.min()))


def test_infinite_degrees_of_freedom_give_the_normal_quantile():
    E = spc.gum_expanded({"u": [0.3, 0.4], "sensitivity": [1.0, 1.0],
                          "dof": [np.inf, np.inf]})
    assert abs(E["coverage_factor"][0] - 1.959963984540054) < 1e-9
    assert abs(E["expanded"][0] - E["coverage_factor"][0] * E["u_combined"][0]) < 1e-15


def test_fewer_degrees_of_freedom_widen_the_interval():
    small = spc.gum_expanded({"u": [0.5], "sensitivity": [1.0], "dof": [4.0]})
    large = spc.gum_expanded({"u": [0.5], "sensitivity": [1.0], "dof": [400.0]})
    assert small["coverage_factor"][0] > large["coverage_factor"][0] > 1.959


# --------------------------------------------------------------------------- #
# 8. GUM: モンテカルロは伝播則の独立な検算
# --------------------------------------------------------------------------- #
def test_monte_carlo_agrees_with_the_propagation_law_for_a_linear_model():
    """★導出も実装も別(代数 vs 標本)なので、片方が壊れれば一致しない。"""
    tab = {"u": [0.3, 0.4, 0.1], "sensitivity": [1.0, -2.0, 3.0]}
    analytic = spc.gum_propagate(tab)["u_combined"][0]
    mc = spc.gum_monte_carlo(tab, n=200_000, seed=11)["u_monte_carlo"][0]
    assert abs(mc - analytic) / analytic < 0.02, (
        "モンテカルロ %.6f と伝播則 %.6f が合わない" % (mc, analytic))


def test_monte_carlo_agrees_with_the_correlated_propagation_too():
    """相関は Cholesky で入れる —— 伝播則の相関項とは**別の経路**。"""
    R = np.array([[1.0, 0.6], [0.6, 1.0]])
    tab = {"u": [0.3, 0.4], "sensitivity": [1.0, 1.0]}
    analytic = spc.gum_propagate(tab, correlation=R)["u_combined"][0]
    mc = spc.gum_monte_carlo(tab, n=200_000, seed=12, correlation=R)["u_monte_carlo"][0]
    assert abs(mc - analytic) / analytic < 0.02


def test_the_coverage_interval_of_a_rectangular_input_is_narrower_than_k_times_u():
    """★★**伝播則は分布の形を捨てている**ことを数で見せる。

    矩形 1 成分の最短 95 % 区間の半幅は **``0.95 a``**(支持の端 ``a`` ではない ——
    95 % ぶんの幅しか要らない)。一方 ``k u = 1.96 a/sqrt(3) = 1.1316 a`` なので、
    比は ``1.959964/(sqrt(3) x 0.95) = 1.1911`` という閉形式になる。
    """
    tab = {"u": [1 / np.sqrt(3)], "sensitivity": [1.0], "distribution": ["rectangular"]}
    mc = spc.gum_monte_carlo(tab, n=200_000, seed=13, distribution="distribution")
    E = spc.gum_expanded({"u": tab["u"], "sensitivity": [1.0], "dof": [np.inf]})
    assert abs(mc["half_width"][0] - 0.95) < 5e-3, (
        "一様分布の 95 %% 区間の半幅が 0.95 でない: %.5f" % mc["half_width"][0])
    ratio = E["expanded"][0] / mc["half_width"][0]
    closed = 1.959963984540054 / (np.sqrt(3) * 0.95)
    assert abs(ratio - closed) < 0.01, "比 %.4f が閉形式 %.4f と違う" % (ratio, closed)


def test_a_correlation_matrix_with_no_joint_distribution_is_refused():
    """半正定値でない相関行列は、そもそも標本が存在しないので拒む。"""
    R = np.array([[1.0, 0.9, -0.9], [0.9, 1.0, 0.9], [-0.9, 0.9, 1.0]])
    with pytest.raises(ValueError, match="positive definite|symmetric"):
        spc.gum_monte_carlo({"u": [1.0, 1.0, 1.0], "sensitivity": [1.0, 1.0, 1.0]},
                            n=10_000, seed=1, correlation=R)


# --------------------------------------------------------------------------- #
# 8.5 規格の worked example —— **外の権威が出した答え**と突き合わせる
# --------------------------------------------------------------------------- #
#: 測定システム解析の参考マニュアル(第 4 版)に載る分散分析法の例題。
#: 10 部品 x 測定者 3 人 x 3 回 = 90 点。印刷値は小数 2 桁。
_REFERENCE_GRR_DATA = {
    "A": {1: [0.29, 0.41, 0.64], 2: [-0.56, -0.68, -0.58], 3: [1.34, 1.17, 1.27],
          4: [0.47, 0.50, 0.64], 5: [-0.80, -0.92, -0.84], 6: [0.02, -0.11, -0.21],
          7: [0.59, 0.75, 0.66], 8: [-0.31, -0.20, -0.17], 9: [2.26, 1.99, 2.01],
          10: [-1.36, -1.25, -1.31]},
    "B": {1: [0.08, 0.25, 0.07], 2: [-0.47, -1.22, -0.68], 3: [1.19, 0.94, 1.34],
          4: [0.01, 1.03, 0.20], 5: [-0.56, -1.20, -1.28], 6: [-0.20, 0.22, 0.06],
          7: [0.47, 0.55, 0.83], 8: [-0.63, 0.08, -0.34], 9: [1.80, 2.12, 2.19],
          10: [-1.68, -1.62, -1.50]},
    "C": {1: [0.04, -0.11, -0.15], 2: [-1.38, -1.13, -0.96], 3: [0.88, 1.09, 0.67],
          4: [0.14, 0.20, 0.11], 5: [-1.46, -1.07, -1.45], 6: [-0.29, -0.67, -0.49],
          7: [0.02, 0.01, 0.21], 8: [-0.46, -0.56, -0.49], 9: [1.77, 1.45, 1.87],
          10: [-1.49, -1.77, -2.16]},
}


def _reference_table():
    part, oper, val = [], [], []
    for o in "ABC":
        for p in range(1, 11):
            for v in _REFERENCE_GRR_DATA[o][p]:
                part.append("P%02d" % p)
                oper.append(o)
                val.append(v)
    return {"part": np.array(part, dtype=object),
            "operator": np.array(oper, dtype=object),
            "value": np.array(val, dtype=np.float64)}


def test_the_published_worked_example_is_reproduced():
    """★★**外の権威が出した答え**を再現する —— この族で一番強い門。

    分散成分も百分率も、こちらの導出とは独立に印刷されている数字である。
    実測の差(2026-09-23):

        EV  0.199933 / 公表 0.199933   差 1.8e-07
        AV  0.226838 / 公表 0.226838   差 4.8e-07
        GRR 0.302372 / 公表 0.302373   差 1.5e-06
        PV  1.042327 / 公表 1.042327   差 4.9e-07
        寄与率 3.4 / 4.4 / 7.8 / 92.2  —— 公表と完全一致

    TV だけ 3e-4 ずれるが、これは公表が 1.085(小数 3 桁)で印刷されているため
    (こちらの計算は 1.085300)。**数字の不一致ではなく印刷桁**なので、許容は
    印刷桁に合わせて取る。
    """
    # ★表の脚注が「α = 0.05 で判定」と書いているので、**表の再現を名乗る門は
    #   その α を明示して**通す(既定 0.25 の妥当性とは別の話)。この例題では
    #   F = 0.434 がどちらの α でも非有意なので、結果はどちらでも同じ。
    G = spc.msa_gauge_rr(_reference_table(), pool_alpha=0.05)
    s = dict(zip(G["component"], G["sigma"]))
    for name, published in (("repeatability", 0.199933), ("reproducibility", 0.226838),
                            ("gauge_rr", 0.302373), ("part", 1.042327)):
        assert abs(s[name] - published) < 5e-6, (
            "%s %.6f が公表値 %.6f と違う" % (name, s[name], published))
    assert abs(s["total"] - 1.085) < 5e-4, "TV %.6f(公表は 1.085 = 小数 3 桁)" % s["total"]

    pc = dict(zip(G["component"], G["pct_contribution"]))
    for name, published in (("repeatability", 3.4), ("reproducibility", 4.4),
                            ("gauge_rr", 7.8), ("part", 92.2)):
        assert abs(pc[name] - published) < 0.05, (
            "寄与率 %s %.2f %% が公表 %.1f %% と違う" % (name, pc[name], published))
    assert abs(G["ndc"][0] - 4.861) < 5e-3
    assert abs(G["pct_grr"][0] - 27.9) < 0.05


def test_the_example_only_matches_because_the_interaction_is_pooled():
    """★**なぜ一致するのか**を門に書く —— 一致が偶然でないことを示すため。

    この例題は交互作用の F 検定が ``p = 0.9741`` とまったく有意でないので、規格は
    交互作用を誤差に畳んで再計算した値を公表している。交互作用を残したままだと
    EV は 0.214435 で、**7.3 % 高く**出る。つまりこの門は「実装が合っている」だけ
    でなく「**同じモデルを選べている**」ことまで見ている。

    ★モデル選択が答えを動かすので、``interaction_pooled`` / ``interaction_p`` を
    返り値に載せてある。黙って切り替える実装は、同じ工程について別の数字を返し、
    その理由をどこにも残さない。
    """
    t = _reference_table()
    for alpha in (0.05, 0.25):                        # 表の α と既定の α の両方で
        auto = spc.msa_gauge_rr(t, pool_alpha=alpha)
        assert bool(auto["interaction_pooled"][0]), (
            "alpha=%.2f でプールされない(F=0.434 はどちらでも非有意のはず)" % alpha)
    auto = spc.msa_gauge_rr(t, pool_alpha=0.05)
    assert abs(auto["interaction_p"][0] - 0.9741) < 5e-4, (
        "交互作用の p が %.4f(期待 0.9741)" % auto["interaction_p"][0])

    keep = spc.msa_gauge_rr(t, pool_interaction=False)
    ev_keep = dict(zip(keep["component"], keep["sigma"]))["repeatability"]
    assert abs(ev_keep - 0.214435) < 5e-6
    assert abs(ev_keep / 0.199933 - 1.0) > 0.05, (
        "モデルを変えても答えが動かない = プール経路が効いていない")
    assert not bool(keep["interaction_pooled"][0])

    forced = spc.msa_gauge_rr(t, pool_interaction=True)
    assert bool(forced["interaction_pooled"][0])
    assert abs(dict(zip(forced["component"], forced["sigma"]))["repeatability"]
               - 0.199933) < 5e-6


def test_a_significant_interaction_is_not_pooled_by_auto():
    """対照群: 交互作用を**わざと入れた**データでは ``auto`` はプールしない。

    これが無いと「auto は常にプールする」実装でも上の門は通ってしまう(空の一致)。
    """
    rng = np.random.default_rng(5)
    p, o, r = 10, 3, 3
    a = rng.normal(0.0, 1.0, p)
    b = rng.normal(0.0, 0.2, o)
    ab = rng.normal(0.0, 1.5, (p, o))               # 大きな交互作用
    part, oper, val = [], [], []
    for i in range(p):
        for j in range(o):
            for _ in range(r):
                part.append("P%02d" % i)
                oper.append("A%d" % j)
                val.append(10.0 + a[i] + b[j] + ab[i, j] + rng.normal(0.0, 0.1))
    t = {"part": np.array(part, dtype=object), "operator": np.array(oper, dtype=object),
         "value": np.array(val, dtype=np.float64)}
    G = spc.msa_gauge_rr(t)
    assert G["interaction_p"][0] < 0.25, "この対照群の交互作用が有意でない = 作り方が壊れている"
    assert not bool(G["interaction_pooled"][0]), "有意な交互作用までプールしている"


def test_the_pooling_switch_is_validated():
    with pytest.raises(ValueError, match="pool_interaction"):
        spc.msa_gauge_rr(_reference_table(), pool_interaction="yes")
    with pytest.raises(ValueError, match="pool_alpha"):
        spc.msa_gauge_rr(_reference_table(), pool_alpha=1.5)


# --------------------------------------------------------------------------- #
# 8.6 測定の不確かさの規格例題 —— **外の権威が出した答え**
# --------------------------------------------------------------------------- #
def test_the_end_gauge_example_reproduces_its_uncertainty_budget():
    """端度器校正の例題(附属書 H.1)の不確かさバジェットを再現する。

    公表の寄与(nm): 25 / 5.8 / 3.9 / 6.7 / 2.9 / 16.6。後ろ 2 つは入力が別単位
    (``1/degC`` と ``degC``)なので、感度係数を掛けて初めて nm になる ——
    ``c(d_alpha) = l_S x dTheta`` と ``c(d_theta) = l_S x alpha_S``。実装が
    2.9 と 16.68 を出すことで、**感度係数の扱いまで含めて**合っていると言える。
    """
    l_s_nm = 50e6                     # 端度器の呼び長さ 50 mm を nm で
    budget = {"u": [25.0, 5.8, 3.9, 6.7, 0.58e-6, 0.029],
              "sensitivity": [1.0, 1.0, 1.0, 1.0, l_s_nm * (-0.1), l_s_nm * 11.5e-6],
              "dof": [18.0, 24.0, 5.0, 8.0, 50.0, 2.0]}
    contrib = np.sqrt(spc.gum_propagate(budget)["contribution"])
    for got, published in zip(contrib, [25.0, 5.8, 3.9, 6.7, 2.9, 16.6]):
        assert abs(got - published) < 0.1, "寄与 %.2f nm が公表 %.1f nm と違う" % (got, published)
    E = spc.gum_expanded(budget, level=0.95)
    assert abs(E["u_combined"][0] - 32.0) < 0.5, (
        "u_c %.2f nm(公表は 32 nm = 2 桁印刷)" % E["u_combined"][0])


def test_the_effective_dof_is_truncated_before_the_t_lookup_not_after():
    """★**切り捨ては t 表を引く直前**(規格 G.4.1)。順序を間違えると k が変わる。

    門を 2 段に分ける:

      1. **切り捨て後の整数**で照合する(連続値 16.64 と公表の 16.7 は、公表側が
         中間値を 2 桁で印刷しているだけの差なので、連続値を門にすると永久に落ちる)
      2. その整数で引いた ``k`` が公表の 2.12 に一致する

    実測: ``nu_eff = 16.64`` を切り捨てず引くと ``k = 2.1132``、切り捨てて 16 で
    引くと ``2.1199``。**t 分布の実装は両方正しく、違うのは手順の順序だけ** ——
    この診断ができるのは、公表値が中間結果(``nu_eff``)も出しているおかげ。
    """
    l_s_nm = 50e6
    E = spc.gum_expanded({"u": [25.0, 5.8, 3.9, 6.7, 0.58e-6, 0.029],
                          "sensitivity": [1.0, 1.0, 1.0, 1.0,
                                          l_s_nm * (-0.1), l_s_nm * 11.5e-6],
                          "dof": [18.0, 24.0, 5.0, 8.0, 50.0, 2.0]}, level=0.95)
    assert E["dof_used"][0] == 16.0, (
        "切り捨て後の自由度が %s(公表は 16.7 -> 16)" % E["dof_used"][0])
    assert E["dof_effective"][0] < E["dof_used"][0] + 1.0        # 切り捨て前も残っている
    assert abs(E["coverage_factor"][0] - 2.12) < 5e-3, (
        "k %.4f が公表 2.12 と違う(切り捨てを t 引きの後にしていないか)"
        % E["coverage_factor"][0])


def _impedance_budget():
    """附属書 H.2 の観測(電圧 V / 電流 A / 位相差 rad、5 回)から予算を組む。"""
    V = np.array([5.007, 4.994, 5.005, 4.990, 4.999])
    I = np.array([19.663, 19.639, 19.640, 19.685, 19.678]) * 1e-3
    ph = np.array([1.0456, 1.0438, 1.0468, 1.0428, 1.0433])
    n = V.size
    u = [V.std(ddof=1) / np.sqrt(n), I.std(ddof=1) / np.sqrt(n), ph.std(ddof=1) / np.sqrt(n)]
    return V.mean(), I.mean(), ph.mean(), u, np.array(
        [[1.0, -0.36, 0.86], [-0.36, 1.0, -0.65], [0.86, -0.65, 1.0]])


def test_the_simultaneous_resistance_and_reactance_example_reproduces():
    """相関つきの例題(附属書 H.2)—— 共分散項の実装を外から検算する唯一の例。

    3 つの出力すべてが 3 桁印刷の範囲で一致すること。値そのもの
    (127.732 / 219.847 / 254.260 Ohm)も突き合わせる。
    """
    v, i, ph, u, R = _impedance_budget()
    for value, sens, pub_val, pub_u in (
            (v / i * np.cos(ph), [np.cos(ph) / i, -v * np.cos(ph) / i ** 2,
                                  -v * np.sin(ph) / i], 127.732, 0.071),
            (v / i * np.sin(ph), [np.sin(ph) / i, -v * np.sin(ph) / i ** 2,
                                  v * np.cos(ph) / i], 219.847, 0.295),
            (v / i, [1.0 / i, -v / i ** 2, 0.0], 254.260, 0.236)):
        assert abs(value - pub_val) < 1e-3, "%.3f が公表 %.3f と違う" % (value, pub_val)
        g = spc.gum_propagate({"u": u, "sensitivity": sens}, correlation=R)
        assert abs(g["u_combined"][0] - pub_u) < 1.5e-3, (
            "u_c %.4f が公表 %.3f と違う" % (g["u_combined"][0], pub_u))


def test_ignoring_correlation_errs_in_both_directions_on_the_same_data():
    """★★**「相関を無視すると過小評価」は偽**。同じ 1 つのデータで向きが逆に出る。

    附属書 H.2 で相関行列を落とすと(実測 2026-09-23):

        u_c(R)  0.0702 -> 0.1945   **2.8 倍の過大**
        u_c(X)  0.2961 -> 0.2009   過小

    「安全側に外れるから省いてよい」という判断は、R については 3 倍近く過大な
    不確かさを報告することになる。
    """
    v, i, ph, u, R = _impedance_budget()
    sens_r = [np.cos(ph) / i, -v * np.cos(ph) / i ** 2, -v * np.sin(ph) / i]
    sens_x = [np.sin(ph) / i, -v * np.sin(ph) / i ** 2, v * np.cos(ph) / i]
    r_with = spc.gum_propagate({"u": u, "sensitivity": sens_r}, correlation=R)["u_combined"][0]
    r_none = spc.gum_propagate({"u": u, "sensitivity": sens_r})["u_combined"][0]
    x_with = spc.gum_propagate({"u": u, "sensitivity": sens_x}, correlation=R)["u_combined"][0]
    x_none = spc.gum_propagate({"u": u, "sensitivity": sens_x})["u_combined"][0]
    assert r_none > 2.0 * r_with, "R で過大にならない(%.4f -> %.4f)" % (r_with, r_none)
    assert x_none < x_with, "X で過小にならない(%.4f -> %.4f)" % (x_with, x_none)


def test_the_sign_of_the_correlation_error_follows_the_closed_form():
    """原理の側からも固定する: ``u_c^2 = (c1u1)^2 + (c2u2)^2 + 2 r c1u1 c2u2``。

    実データ(H.2)は「両方向に出る」ことの実例、こちらは**符号の積で決まる**ことの
    閉形式。2 本で補完関係になる。
    """
    tab = {"u": [0.3, 0.4], "sensitivity": [1.0, 1.0]}
    none = spc.gum_propagate(tab)["u_combined"][0]
    pos = spc.gum_propagate(tab, correlation=np.array([[1.0, 0.5], [0.5, 1.0]]))["u_combined"][0]
    neg = spc.gum_propagate(tab, correlation=np.array([[1.0, -0.5], [-0.5, 1.0]]))["u_combined"][0]
    assert pos > none > neg, "相関の符号で大小が動かない: %.4f / %.4f / %.4f" % (neg, none, pos)
    for r, got in ((0.5, pos), (-0.5, neg)):
        closed = np.sqrt(0.3 ** 2 + 0.4 ** 2 + 2 * r * 0.3 * 0.4)
        assert abs(got - closed) < 1e-14
    # 感度の符号を反転すると向きも反転する(積で決まることの直接確認)
    flip = {"u": [0.3, 0.4], "sensitivity": [1.0, -1.0]}
    pos_f = spc.gum_propagate(flip, correlation=np.array([[1.0, 0.5], [0.5, 1.0]]))["u_combined"][0]
    assert pos_f < spc.gum_propagate(flip)["u_combined"][0]


def test_the_additive_example_agrees_and_the_rectangular_one_narrows():
    """補遺 1 の加法モデル —— **一致すべきところで一致し、狭まるべきところで狭まる**。

    4 つの入力(各 ``u = 1``)の和。正規なら伝播則とモンテカルロは同じ区間
    ``+-3.92`` を出す。矩形にすると同じ ``u`` のまま区間は ``+-3.88`` に**狭まる**
    —— 矩形の和は台形分布に近づき、裾が正規より薄いから。伝播則は分布の形を
    捨てているので、この差は原理的なもの。
    """
    lin = {"u": [1.0] * 4, "sensitivity": [1.0] * 4}
    guf = spc.gum_expanded({**lin, "dof": [np.inf] * 4})
    assert abs(guf["u_combined"][0] - 2.0) < 1e-12
    assert abs(guf["expanded"][0] - 3.92) < 5e-3

    gauss = spc.gum_monte_carlo(lin, n=200_000, seed=1)
    assert abs(gauss["half_width"][0] - 3.92) < 0.05, (
        "正規入力で伝播則と食い違う: %.3f" % gauss["half_width"][0])

    rect = spc.gum_monte_carlo({**lin, "distribution": ["rectangular"] * 4},
                               n=200_000, seed=1, distribution="distribution")
    assert abs(rect["u_monte_carlo"][0] - 2.0) < 0.02, "u は同じはず"
    assert abs(rect["half_width"][0] - 3.88) < 0.03, (
        "矩形の和の 95 %% 区間が %.3f(公表 3.88)" % rect["half_width"][0])
    assert rect["half_width"][0] < guf["expanded"][0], "狭まっていない"


def test_the_propagation_law_breaks_at_a_stationary_point_and_says_so():
    """★★**伝播則が破綻する場面を再現し、破綻を申告することまで見る**。

    比較損失 ``dY = X1^2 + X2^2``(各 ``u = 0.005``)を ``x1 = x2 = 0`` で評価すると、
    感度 ``c_i = 2 x_i`` が両方 0 になるので伝播則は ``u_c = 0`` / 区間 ``[0, 0]``。
    同じ状況でモンテカルロは ``dy = 50e-6`` / ``u = 50e-6`` / ``[0, 150e-6]`` を返す。

    これは実装の誤りではなく**1 次近似が極値で情報を失う**という手法の限界で、
    補遺 1 のモンテカルロが存在する理由そのもの。だから ``u_c = 0`` を返すこと自体は
    止めないが、``first_order_degenerate`` で**それが近似の限界だと申告する**。

    実測の 3 点(公表値と一致):

        x1=0.000  伝播則 u=0 / [0,0]        モンテカルロ 50.0 / 49.9 / [0, 149]
        x1=0.010  伝播則 [-96, +296](負!)  モンテカルロ [0, 366]
        x1=0.050  伝播則 [1520, 3480]        モンテカルロ [1588, 3543]
    """
    u = [0.005, 0.005]
    # --- x1 = 0: 伝播則の破綻と、その申告 ---
    G0 = spc.gum_propagate({"u": u, "sensitivity": [0.0, 0.0]})
    assert G0["u_combined"][0] == 0.0
    assert not bool(G0["guf_valid"][0]), (
        "感度が全部 0 で u_c=0 なのに、伝播則が有効だと言っている")
    assert "stationary_point" in list(G0["invalid_reasons"]), (
        "理由が付いていない —— 呼んだ側は u=0 を「完璧な測定」と読む")
    M0 = spc.gum_monte_carlo({"u": u, "sensitivity": [1.0, 1.0],
                              "value": [0.0, 0.0], "power": [2.0, 2.0]},
                             n=200_000, seed=3, value="value", power="power")
    assert abs(M0["mean"][0] * 1e6 - 50.0) < 1.0, "MCM の平均 %.1f e-6" % (M0["mean"][0] * 1e6)
    assert abs(M0["u_monte_carlo"][0] * 1e6 - 50.0) < 1.5
    assert abs(M0["low"][0]) < 1e-9, "損失は負になれない"
    assert abs(M0["high"][0] * 1e6 - 150.0) < 3.0, (
        "MCM の上端 %.1f e-6(公表 150)" % (M0["high"][0] * 1e6))

    # --- 対照群: 極値から離れれば両者は近づく ---
    x1 = 0.050
    E = spc.gum_expanded({"u": u, "sensitivity": [2 * x1, 0.0], "dof": [np.inf] * 2})
    lo_guf = (x1 ** 2 - E["expanded"][0]) * 1e6
    # ★区間の端は**標本の分位点**なので 1/sqrt(n) で揺れる。実測(種 8 本):
    #   n=200,000 で標準偏差 10.0 / n=1,000,000 で 4.2。偏りではないので、n を
    #   決めた上で揺れの 3 倍で採る(「小さい」ではなく「この n ならこの幅」)。
    M = spc.gum_monte_carlo({"u": u, "sensitivity": [1.0, 1.0],
                             "value": [x1, 0.0], "power": [2.0, 2.0]},
                            n=1_000_000, seed=3, value="value", power="power")
    assert abs(lo_guf - 1520.0) < 5.0
    assert abs(M["low"][0] * 1e6 - 1590.0) < 15.0, (
        "MCM の下端 %.1f e-6(公表 1590、n=1e6 の揺れは標準偏差 4.2)" % (M["low"][0] * 1e6))
    assert bool(spc.gum_propagate(
        {"u": u, "sensitivity": [2 * x1, 0.0]})["guf_valid"][0])

    # --- 検出器 2: 極値の**近く**では区間が定義域を出る(負の損失) ---
    x1 = 0.010
    E2 = spc.gum_expanded({"u": u, "sensitivity": [2 * x1, 0.0], "dof": [np.inf] * 2},
                          estimate=x1 ** 2, lower_bound=0.0)
    assert abs(E2["low"][0] * 1e6 + 96.0) < 1.0, "下端 %.1f e-6(公表 -96)" % (E2["low"][0] * 1e6)
    assert abs(E2["high"][0] * 1e6 - 296.0) < 1.0
    assert not bool(E2["guf_valid"][0])
    assert "infeasible_interval" in list(E2["invalid_reasons"])
    # ★**境界を渡さなければ検査しない**(勝手に 0 を下限と仮定しない)
    assert bool(spc.gum_expanded({"u": u, "sensitivity": [2 * x1, 0.0], "dof": [np.inf] * 2},
                                 estimate=x1 ** 2)["guf_valid"][0])


def test_a_fractional_power_is_refused():
    with pytest.raises(ValueError, match="whole number"):
        spc.gum_monte_carlo({"u": [1.0], "sensitivity": [1.0], "value": [0.0],
                             "power": [0.5]}, n=10_000, value="value", power="power")


# --------------------------------------------------------------------------- #
# 8.7 モンテカルロで伝播則を検証する(規格 8.1.3 の手続き)
# --------------------------------------------------------------------------- #
def test_the_numerical_tolerance_follows_the_standards_definition():
    """``delta`` は ``u(y)`` を ndig 桁の整数 x 10^l に書いたときの ``0.5 x 10^l``。

    ``u(y) = 2.00`` なら ndig 1/2/3 で ``2 x 10^0`` / ``20 x 10^-1`` / ``200 x 10^-2``
    なので ``delta`` は **0.5 / 0.05 / 0.005**。★桁を増やすほど許容は**狭く**なる
    —— 「ndig を下げると判定が変わる」は向きが逆で、緩くなるだけ。
    """
    lin = {"u": [1.0] * 4, "sensitivity": [1.0] * 4}
    guf = spc.gum_expanded({**lin, "dof": [np.inf] * 4}, estimate=0.0)
    mc = spc.gum_monte_carlo(lin, n=200_000, seed=1)
    for ndig, want in ((1, 0.5), (2, 0.05), (3, 0.005)):
        v = spc.gum_validate(guf, mc, ndig=ndig)
        assert abs(v["delta"][0] - want) < 1e-15, (
            "ndig=%d の delta が %.6f(期待 %.6f)" % (ndig, v["delta"][0], want))
    assert (spc.gum_validate(guf, mc, ndig=1)["delta"][0]
            > spc.gum_validate(guf, mc, ndig=3)["delta"][0])


def test_the_additive_example_validates_at_the_standards_typical_digits():
    """加法モデルは正規でも矩形でも ndig=2 で検証を通る(規格が典型と述べる桁)。

    ★矩形のほうが端点差は大きい(区間が実際に狭いので当然)。公表の端点差 0.04 に対し
    実測 0.029 / 0.050 —— ``delta = 0.05`` にぎりぎり収まる。「通った」ことより
    **どれだけ余裕が無いか**が読み取れるように、差も返している。
    """
    lin = {"u": [1.0] * 4, "sensitivity": [1.0] * 4}
    guf = spc.gum_expanded({**lin, "dof": [np.inf] * 4}, estimate=0.0)
    for tab, kw in ((lin, {}),
                    ({**lin, "distribution": ["rectangular"] * 4},
                     {"distribution": "distribution"})):
        mc = spc.gum_monte_carlo(tab, n=1_000_000, seed=1, **kw)
        v = spc.gum_validate(guf, mc, ndig=2)
        assert bool(v["agree"][0]), (
            "ndig=2 で検証に落ちた(dlow=%.4f dhigh=%.4f delta=%.4f)"
            % (v["dlow"][0], v["dhigh"][0], v["delta"][0]))
        # ★端点は位置の揺れを拾うので、**幅**でも別に見る(こちらは sd 0.0035)
        half = 0.5 * (mc["high"][0] - mc["low"][0])
        assert abs(half - guf["expanded"][0]) < 0.06, (
            "半幅 %.4f が GUF の %.4f と大きく違う" % (half, guf["expanded"][0]))


def test_a_failed_validation_at_three_digits_is_the_monte_carlos_limit():
    """★★**「検証に落ちた」と「伝播則が誤り」は別物**。

    正規入力なら伝播則とモンテカルロは理論上**厳密に一致**する。それでも
    ``ndig=3``(``delta = 0.005``)では落ちる —— 最短区間の**位置**の揺れが
    n=1,000,000 でも標準偏差 0.0146 あるからで、伝播則の誤りではない。

    ここを門にしておかないと、将来 ndig の既定を上げた人が「伝播則が壊れた」と
    読み違える。落ちることと、落ちる理由が位置の揺れであることを同時に固定する。
    """
    lin = {"u": [1.0] * 4, "sensitivity": [1.0] * 4}
    guf = spc.gum_expanded({**lin, "dof": [np.inf] * 4}, estimate=0.0)
    mc = spc.gum_monte_carlo(lin, n=1_000_000, seed=1)
    v3 = spc.gum_validate(guf, mc, ndig=3)
    assert not bool(v3["agree"][0]), "ndig=3 が通ってしまう(揺れの見積りが変わった?)"
    # 幅は合っている —— ずれているのは位置のほう、という切り分けを数で固定する
    half = 0.5 * (mc["high"][0] - mc["low"][0])
    centre = 0.5 * (mc["high"][0] + mc["low"][0])
    # ★許容は**測った揺れ**から取る。n=1,000,000 の半幅の標準偏差は種 12 本で
    #   0.0035(位置は 0.0146)。1 本の種に 2 sigma を当てて落とすのは 3 度目の
    #   同じ誤りなので、4 sigma = 0.014 で採る。
    assert abs(half - guf["expanded"][0]) < 0.014, (
        "半幅まで合っていない(%.5f vs %.5f、揺れは標準偏差 0.0035)—— "
        "これなら伝播則側を疑うべき" % (half, guf["expanded"][0]))
    assert abs(centre) > 0.004, "中心が動いていない = この門の前提が崩れている"


def test_validation_is_refused_when_there_is_no_tolerance_to_build():
    """``u(y) = 0``(停留点)では数値許容差が作れないので拒む。

    ★ここで 0 を許すと ``delta = 0`` になり「端点差が厳密に 0 でなければ不一致」と
    いう無意味な判定になる。伝播則が記述できない場面を、検証の側で取り繕わない。
    """
    guf = spc.gum_expanded({"u": [0.005, 0.005], "sensitivity": [0.0, 0.0],
                            "dof": [np.inf] * 2}, estimate=0.0)
    mc = spc.gum_monte_carlo({"u": [0.005, 0.005], "sensitivity": [1.0, 1.0],
                              "value": [0.0, 0.0], "power": [2.0, 2.0]},
                             n=50_000, seed=1, value="value", power="power")
    with pytest.raises(ValueError, match="stationary-point|u\\(y\\)"):
        spc.gum_validate(guf, mc)


def test_a_guf_table_without_an_interval_is_refused_with_the_reason():
    """区間を持たない表(``estimate`` を渡さずに呼んだ結果)は拒む。

    比べるのは**端点**であって ``U`` ではないので、区間が無ければ手続きが成立しない。
    """
    guf = spc.gum_expanded({"u": [1.0], "sensitivity": [1.0], "dof": [np.inf]})
    mc = spc.gum_monte_carlo({"u": [1.0], "sensitivity": [1.0]}, n=50_000, seed=1)
    with pytest.raises(ValueError, match="interval endpoints"):
        spc.gum_validate(guf, mc)


#: 4 つの ``U(-a, a)``(各 ``u = 1`` なので ``a = sqrt(3)``)の和は、スケールした
#: Irwin-Hall(4) になる。``F(s) = s^4/24``(``s`` が [0,1] のとき。``F(1) = 1/24 =
#: 0.0417 > 0.025`` なので 2.5 % 点はこの枝にある)を反転すると
#: ``s = 0.6^(1/4)``、``y_low = sqrt(3) (2 s - 4)``。**乱数を 1 つも使わない厳密値**。
_IRWIN_HALL_4_LOW = np.sqrt(3.0) * (2.0 * 0.6 ** 0.25 - 4.0)      # = -3.879407...


def test_the_rectangular_sum_has_an_exact_coverage_interval():
    """★★**公表の [-3.88, +3.88] は厳密分位点の丸め**であって MC の産物ではない。

    これが効くのは、同じ「``ndig=3`` で落ちる」でも**原因が逆**だと証明できる点:

      * 正規の例 —— 伝播則は真値と**厳密に一致**する。落ちるのは最短区間の
        **位置の揺れ**(推定器の問題)。
      * 矩形の例 —— 真の半幅は ``1.939703 sigma`` なのに伝播則は正規近似の
        ``1.959964 sigma`` を使う。差 **0.040521** は ``delta = 0.005`` の 8 倍で、
        **手法そのものの誤差**(Irwin-Hall(4) の超過尖度は ``-6/(5n) = -0.3`` で
        正規より裾が薄いから、正規近似は構造的に広く出る)。

    厳密解があるので、この門は乱数に一切依存しない。
    """
    assert abs(_IRWIN_HALL_4_LOW + 3.879407) < 1e-5, (
        "厳密値の計算が変わった: %.6f" % _IRWIN_HALL_4_LOW)
    lin = {"u": [1.0] * 4, "sensitivity": [1.0] * 4}
    guf = spc.gum_expanded({**lin, "dof": [np.inf] * 4}, estimate=0.0)
    # 伝播則は真値より**広い**(尖度が負 = 裾が薄いので正規近似は保守側に外れる)
    assert guf["expanded"][0] > -_IRWIN_HALL_4_LOW
    assert abs((guf["expanded"][0] + _IRWIN_HALL_4_LOW) - 0.040521) < 1e-4, (
        "伝播則と厳密値の差が %.6f(実測 0.040521)"
        % (guf["expanded"][0] + _IRWIN_HALL_4_LOW))
    assert abs(-_IRWIN_HALL_4_LOW / 2.0 - 1.939703) < 1e-5, "真の被覆係数 sigma 倍"


def test_the_ndig_ladder_against_the_exact_interval_is_deterministic():
    """厳密な区間を相手にすると、``ndig`` の梯子は**乱数なしで固定値**になる。

    ``u(y) = 2.00`` なので ``delta`` は 0.5 / 0.05 / 0.005。端点差は両側とも
    **0.040521**(手法の誤差)なので:

        ndig=1  delta 0.5    -> 一致
        ndig=2  delta 0.05   -> 一致(0.0405 / 0.05 = 余裕 19 %)
        ndig=3  delta 0.005  -> **不一致**(8 倍超過)
    """
    lin = {"u": [1.0] * 4, "sensitivity": [1.0] * 4}
    guf = spc.gum_expanded({**lin, "dof": [np.inf] * 4}, estimate=0.0)
    exact = {"low": np.array([_IRWIN_HALL_4_LOW]),
             "high": np.array([-_IRWIN_HALL_4_LOW])}
    for ndig, want in ((1, True), (2, True), (3, False)):
        v = spc.gum_validate(guf, exact, ndig=ndig)
        assert bool(v["agree"][0]) is want, (
            "ndig=%d の判定が %s(期待 %s、dlow=%.6f delta=%.6f)"
            % (ndig, bool(v["agree"][0]), want, v["dlow"][0], v["delta"][0]))
        assert abs(v["dlow"][0] - 0.040521) < 1e-4
        assert abs(v["dhigh"][0] - 0.040521) < 1e-4


def test_the_monte_carlo_converges_to_the_exact_rectangular_interval():
    """``gum_monte_carlo`` の矩形経路が**厳密値**に寄ること(公表値ではなく真値と)。"""
    mc = spc.gum_monte_carlo({"u": [1.0] * 4, "sensitivity": [1.0] * 4,
                              "distribution": ["rectangular"] * 4},
                             n=1_000_000, seed=1, distribution="distribution")
    half = 0.5 * (mc["high"][0] - mc["low"][0])
    assert abs(half + _IRWIN_HALL_4_LOW) < 0.015, (
        "半幅 %.5f が厳密 %.5f と違う" % (half, -_IRWIN_HALL_4_LOW))


def test_the_interval_position_is_only_unstable_for_symmetric_outputs():
    """★位置が定まらないのは**対称な出力のとき**だけ(主張の適用範囲を固定する)。

    実測(種 12 本、位置 sd / 幅 sd の比):

        対称(正規の和)   n=200,000 -> 5.2    n=1,000,000 -> 4.1
        歪み(二乗の和)   n=200,000 -> 1.0    n=1,000,000 -> 1.0

    歪んだ出力では最短区間の最適点が一意に強く決まるので、位置も幅と同じ速さで
    収束する。この門が無いと「最短区間は位置が不安定」を無条件の性質だと誤読する。
    """
    def spread(tab, n, **kw):
        cs, hs = [], []
        for s in range(8):
            m = spc.gum_monte_carlo(tab, n=n, seed=s, **kw)
            cs.append(0.5 * (m["high"][0] + m["low"][0]))
            hs.append(m["half_width"][0])
        return np.std(cs, ddof=1), np.std(hs, ddof=1)

    c_sym, h_sym = spread({"u": [1.0] * 4, "sensitivity": [1.0] * 4}, 200_000)
    c_skw, h_skw = spread({"u": [0.005, 0.005], "sensitivity": [1.0, 1.0],
                           "value": [0.0, 0.0], "power": [2.0, 2.0]}, 200_000,
                          value="value", power="power")
    assert c_sym / h_sym > 3.0, "対称なのに位置が安定している(%.2f)" % (c_sym / h_sym)
    assert c_skw / h_skw < 2.0, "歪んでいるのに位置が不安定(%.2f)" % (c_skw / h_skw)


# --------------------------------------------------------------------------- #
# 9. 台帳の登録(足しただけで公開経路に出ないことを防ぐ)
# --------------------------------------------------------------------------- #
def test_the_nine_ops_are_on_the_ledger_with_a_body():
    """★**登録されて初めて op**。ここが無いと、実装はあるのに op_find から見えない
    (この repo で繰り返し起きている型 —— glyphops の 19 関数がまさにそれ)。
    """
    want = {"msa_anova_table", "msa_gauge_rr", "msa_bias_linearity",
            "msa_attribute_agreement", "gum_standard_uncertainty",
            "gum_propagate", "gum_expanded", "gum_monte_carlo", "gum_validate"}
    listed = set(opsspc.list_ops("msa")) | set(opsspc.list_ops("uncertainty"))
    assert want == listed, "台帳の中身が違う: 欠け %s / 余り %s" % (want - listed, listed - want)
    assert not opsspc.missing(), "実体の無い op がある: %s" % opsspc.missing()
    for name in want:
        assert opsspc.info(name)["doc"], "%s の doc が空" % name
        assert opsspc.info(name)["out"] == "table"
