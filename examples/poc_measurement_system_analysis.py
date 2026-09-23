# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: その数字のうち、いくつが測り方のものか

管理図も工程能力も、**測定のばらつきを含んだままの数字**を見ている。この PoC は
それを分ける —— 総変動のうち何割が部品どうしの差で、何割が「測るという行為」の
差なのか。そして 1 回の測定について、成分ごとの不確かさを合成して報告可能な形に
するまでを、**全部「絵の外」から採点する**。

★**この回の規律**: 使った式で答え合わせをしない。真値は次のどれかに限った。

1. **代数的な恒等式** —— 平方和の分解 ``SS_total = SS_部品 + SS_測定者 +
   SS_交互作用 + SS_誤差`` は、分散成分をどう導こうと必ず閉じる。
2. **既存実装(numpy)** —— 繰り返し性は「升目ごとの ``np.var(ddof=1)`` の平均」に
   代数的に等しい。導出も実装も別。
3. **公表された worked example** —— 測定システム解析の参考マニュアルに載る
   10 部品 x 3 測定者 x 3 回の例題。EV / AV / GRR / PV / 寄与率が印刷されている。
4. **厳密解** —— 4 つの矩形分布の和はスケールした Irwin-Hall(4) で、
   ``F(s) = s^4/24`` を反転すれば ``y_2.5% = sqrt(3)(2 x 0.6^(1/4) - 4)``。
   乱数を 1 つも使わない真値。
5. **導出の違う 2 経路** —— 不確かさの伝播則(偏微分と分散の代数)と
   モンテカルロ(乱数の標本)。線形では一致し、**非線形では食い違うのが正しい**。

★★この PoC が示したい一番のことは「**道具が正しく失敗する**」ことである。
伝播則は極値で ``u_c = 0`` を返す —— 実装の誤りではなく 1 次近似の限界だが、
それを黙って返せば読み手は「測定が完璧だった」と受け取る。だから破綻を
**構造で申告する**(``guf_valid`` / ``invalid_reasons``)。

図:
1. ``components``: 分散成分の内訳(公表値との重ね合わせ)。
2. ``pooling``: 交互作用を残すかプールするかで EV が 7.3 % 動く。
3. ``spread``: 推定量の揺れ(種 40 本)と、負の分散成分が出る頻度。
4. ``bias``: 基準値に対する偏りと直線性。
5. ``kappa``: 一致率が高くてもカッパは 0 —— 合格率を振って見せる。
6. ``correlation``: 相関を無視した誤りの向きは**一定でない**。
7. ``breakdown``: 伝播則が破綻する場所とモンテカルロ。
8. ``rectangular``: 矩形和の厳密解 vs 伝播則 vs モンテカルロ。
9. ``breakdown_movie``: **動く図** —— 評価点を動かすと、真の分布が指数から
   正規へ変形し、伝播則の区間が「潰れる → 負へ張り出す → 追いつく」の
   3 段階を通る。壊れ方が連続でないことは静止画では見せられない。
10. ``numbers``: 数表。

走らせ方: ``py -3.11 examples/poc_measurement_system_analysis.py``
(図は ``out/figures/poc_measurement_system_analysis/``)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

CHECKS = []

#: 参考マニュアルの分散分析法の例題(10 部品 x 測定者 3 人 x 3 回)。
_REF = {
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
#: 同じ例題の公表値(EV / AV / GRR / PV)。
_PUB = {"repeatability": 0.199933, "reproducibility": 0.226838,
        "gauge_rr": 0.302373, "part": 1.042327}


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s%s" % ("OK" if ok else "NG", label,
                           ("  —— " + detail) if detail else ""))
    return bool(ok)


def reference_table():
    part, oper, val = [], [], []
    for o in "ABC":
        for p in range(1, 11):
            for v in _REF[o][p]:
                part.append("P%02d" % p)
                oper.append(o)
                val.append(v)
    return {"part": np.array(part, dtype=object),
            "operator": np.array(oper, dtype=object),
            "value": np.array(val, dtype=np.float64)}


def synth_table(p=10, o=3, r=3, sd_part=1.0, sd_oper=0.2, sd_err=0.3, seed=0):
    """分散成分を**指定して**釣り合った表を作る(答えを知っている合成データ)。"""
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
# 第 1 章 分解は代数、そして公表値と突き合わせる                                  #
# --------------------------------------------------------------------------- #
def chapter_components():
    print("\n[1] 総変動を分ける —— 恒等式で閉じ、公表値と一致する")
    t = reference_table()
    A = fs.ledger.msa_anova_table(t)
    ss = dict(zip(A["source"], A["ss"]))
    df = dict(zip(A["source"], A["df"]))
    parts = ss["part"] + ss["operator"] + ss["interaction"] + ss["repeatability"]
    check(abs(parts - ss["total"]) < 1e-10 * ss["total"],
          "平方和が代数的に閉じる",
          "部分の和 %.9f vs 全体 %.9f" % (parts, ss["total"]))
    check(df["total"] == df["part"] + df["operator"] + df["interaction"]
          + df["repeatability"], "自由度も閉じる", "89 = 9 + 2 + 18 + 60")

    G = fs.ledger.msa_gauge_rr(t, pool_alpha=0.05)     # 表の脚注は α=0.05
    s = dict(zip(G["component"], G["sigma"]))
    worst = max(abs(s[k] - v) for k, v in _PUB.items())
    check(worst < 5e-6, "★公表された worked example を再現する",
          "EV/AV/GRR/PV の最大差 %.2e" % worst)
    pc = dict(zip(G["component"], G["pct_contribution"]))
    check(abs(pc["gauge_rr"] - 7.8) < 0.05 and abs(pc["part"] - 92.2) < 0.05,
          "寄与率も公表値と一致", "GRR %.1f %% / 部品 %.1f %%"
          % (pc["gauge_rr"], pc["part"]))
    check(abs(G["ndc"][0] - 4.861) < 5e-3, "区別できる階級数 ndc",
          "%.3f(公表 4.861)" % G["ndc"][0])

    # 既存実装が真値: 交互作用を残したモデルの EV は升目ごと標本分散の平均
    keep = fs.ledger.msa_gauge_rr(t, pool_interaction=False)
    ev_keep = dict(zip(keep["component"], keep["sigma"]))["repeatability"]
    cells = t["value"].reshape(10, 3, 3)
    by_cell = np.array([[np.var(cells[i, j], ddof=1) for j in range(3)]
                        for i in range(10)])
    check(abs(ev_keep ** 2 - by_cell.mean()) < 1e-12 * by_cell.mean(),
          "★既存 numpy が真値: EV² = 升目ごと標本分散の平均",
          "%.10f vs %.10f" % (ev_keep ** 2, by_cell.mean()))

    if figs.enabled():
        # ★★看板は**一目で読める**ものにする。濃淡の地図は情報としては正しいが
        #   読者には「色のついた雑音」で、何の図か分からない。ゲージ R&R の古典的な
        #   見せ方 —— 部品ごとに測定値を縦に並べる —— なら、10 個の塊が縦に離れて
        #   いるのが部品差、各塊の**太さ**が測る行為のばらつき、と目で読める。
        m = t["value"].reshape(3, 10, 3).transpose(1, 0, 2)      # (部品, 測定者, 繰り返し)
        series = []
        for j_ in range(3):
            xj = np.repeat(np.arange(1, 11, dtype=float), 3) + (j_ - 1) * 0.17
            series.append(("測定者 %s" % "ABC"[j_], xj, m[:, j_, :].ravel()))
        pv = dict(zip(G["component"], G["sigma"]))["part"]
        figs.save_plot("scene", series, kinds=["scatter"] * 3,
                       xlabel="部品(10 個)", ylabel="測定値",
                       title="その数字のうち、いくつが測り方のものか",
                       caption="規格の例題の 90 点を、部品ごとに縦に並べたもの。"
                               "**塊が縦に離れている幅**が部品どうしの差(標準偏差 "
                               "%.3f、総変動の 92.2 %%)、**各塊の太さ**が同じ部品を"
                               "測り直したときのばらつき(0.302、7.8 %%)。測定器が"
                               "使えるかどうかは、この 2 つの比で決まる —— "
                               "塊が潰れて重なり始めたら、その測定系では部品を"
                               "区別できない。" % pv)
        keys = ["repeatability", "reproducibility", "gauge_rr", "part"]
        x = np.arange(len(keys), dtype=float)
        figs.save_plot("components",
                       [("実測", x, np.array([s[k] for k in keys])),
                        ("公表値", x, np.array([_PUB[k] for k in keys]))],
                       xlabel="成分(0=EV 1=AV 2=GRR 3=PV)", ylabel="標準偏差",
                       title="分散成分 —— 公表値との重ね合わせ",
                       caption="測定の行為(GRR)が総変動に占めるのは 7.8 %%、"
                               "部品どうしの差が 92.2 %%。どちらも公表値と一致する"
                               "(最大差 %.1e)。" % worst,
                       kinds=["scatter", "scatter"])
    return G, keep


# --------------------------------------------------------------------------- #
# 第 1b 章 古典的なゲージ R&R 報告の面 —— 別の推定法が真値になる                    #
# --------------------------------------------------------------------------- #
#: n = 3 の管理図定数(範囲法)。``d2`` は範囲の期待値を σ に戻す係数、``D4``/``A2``
#: は管理限界の係数。**分散分析とは独立に導かれた表の値**なので、ここから出した
#: 繰り返し性は「既存の別実装が真値になる」の条件を満たす。
_D2_N3, _D4_N3, _A2_N3 = 1.693, 2.574, 1.023


def chapter_report_panels(G):
    print("\n[1b] 古典的な報告の面 —— 範囲法という**別の推定**で確かめる")
    t = reference_table()
    m = t["value"].reshape(3, 10, 3)                  # (測定者, 部品, 繰り返し)
    rng_ = m.max(axis=2) - m.min(axis=2)              # 各升目の範囲
    rbar = float(rng_.mean())
    ev_range = rbar / _D2_N3
    ev_anova = dict(zip(G["component"], G["sigma"]))["repeatability"]
    check(abs(ev_range / ev_anova - 1.0) < 0.02,
          "★範囲法(R̄/d₂)が分散分析の繰り返し性と一致する",
          "%.6f vs %.6f(差 %.2f %%)—— 導出も実装も別"
          % (ev_range, ev_anova, 100 * (ev_range / ev_anova - 1.0)))
    ucl = _D4_N3 * rbar
    # ★「全部内側のはず」と書いたら 1 升はみ出した。実データのほうが正しい ——
    #   規格の例題は**わざと 1 点だけ管理外**にしてある(範囲図の読み方を示すため)。
    n_out = int((rng_ > ucl).sum())
    check(n_out == 1, "範囲図は 1 升だけ管理限界の外(例題が仕込んだ読みどころ)",
          "限界 %.4f を超えた升目 %d / 30" % (ucl, n_out))

    xbar = m.mean(axis=2)
    grand = float(xbar.mean())
    lo_l, hi_l = grand - _A2_N3 * rbar, grand + _A2_N3 * rbar
    out = int(((xbar < lo_l) | (xbar > hi_l)).sum())
    check(out > 15,
          "★平均管理図では**外に出るほうが良い**(限界は測定雑音だけで作る)",
          "30 点中 %d 点が外 —— 部品の差が測定のばらつきを超えている証拠" % out)

    # ndc は閉形式で書ける。寄与率 ρ(= GRR の分散の割合)だけで決まる。
    pc = dict(zip(G["component"], G["pct_contribution"]))
    rho = pc["gauge_rr"] / 100.0
    ndc_closed = 1.41 * np.sqrt((1.0 - rho) / rho)
    check(abs(ndc_closed - G["ndc"][0]) < 1e-3,
          "★ndc は寄与率だけの閉形式 1.41√((1−ρ)/ρ)",
          "%.4f vs op の %.4f" % (ndc_closed, G["ndc"][0]))

    if not figs.enabled():
        return
    x = np.arange(1, 11, dtype=float)
    figs.save_plot("r_chart",
                   [("測定者 A", x, rng_[0]), ("測定者 B", x, rng_[1]),
                    ("測定者 C", x, rng_[2]),
                    ("管理限界 D₄R̄ = %.3f" % ucl, np.array([1.0, 10.0]),
                     np.full(2, ucl))],
                   xlabel="部品", ylabel="3 回の測定値の範囲",
                   title="範囲管理図 —— 測る行為そのものが安定しているか",
                   kinds=["line", "line", "line", "line"],
                   caption="各升目(部品 × 測定者)で 3 回測った値の**幅**。"
                           "ここだけは**限界の内側に収まってほしい** —— はみ出す升目は"
                           "「その部品をその人が測るとき、測り方が揺れている」という"
                           "意味だからです。実測は 1 升だけ外(例題が仕込んだ読みどころ)。★この図の平均 R̄ から"
                           "**分散分析とは別の道**で繰り返し性が出ます(R̄/d₂ = %.6f、"
                           "分散分析 %.6f、差 %.2f %%)—— 導出も実装も違うので、"
                           "片方が壊れれば一致しません。"
                           % (ev_range, ev_anova, 100 * (ev_range / ev_anova - 1.0)))
    figs.save_plot("xbar_chart",
                   [("測定者 A", x, xbar[0]), ("測定者 B", x, xbar[1]),
                    ("測定者 C", x, xbar[2]),
                    ("上限 %.3f" % hi_l, np.array([1.0, 10.0]), np.full(2, hi_l)),
                    ("下限 %.3f" % lo_l, np.array([1.0, 10.0]), np.full(2, lo_l))],
                   xlabel="部品", ylabel="3 回の平均",
                   title="平均管理図 —— ここだけは**外に出るほうが良い**",
                   kinds=["line", "line", "line", "line", "line"],
                   caption="管理図というと「限界の外は異常」ですが、ゲージ R&R の"
                           "平均図だけは**逆**です。この限界は**測定のばらつきだけ**から"
                           "引いてあるので、部品に本当の差があるなら点は外へ出ます。"
                           "実測は 30 点中 **%d 点**が外 —— 測定系が部品の差を"
                           "見分けられている、という読み方をします。3 本の線が"
                           "**ほぼ重なっている**ことが、測定者を変えても同じ物が"
                           "同じに見えている(再現性が良い)ということ。" % out)
    figs.save_plot("by_operator",
                   [("測定者 %s の 30 点" % "ABC"[j],
                     np.full(30, float(j + 1)) + np.linspace(-0.22, 0.22, 30),
                     m[j].ravel()) for j in range(3)]
                   + [("各測定者の平均", np.arange(1.0, 4.0), xbar.mean(axis=1))],
                   xlabel="測定者", ylabel="測定値",
                   kinds=["scatter", "scatter", "scatter", "line"],
                   title="再現性 —— 人が変わると答えはどれだけ動くか",
                   caption="測定者ごとに 30 点すべてを並べたもの。**縦の広がりは"
                           "ほとんど部品の差**で、見たいのは 3 つの塊の**中心のずれ**の"
                           "ほうです(実測 %.4f / %.4f / %.4f)。この小さなずれが"
                           "再現性 AV = 0.226838 の正体で、総変動の 4.4 %% にあたります。"
                           % tuple(xbar.mean(axis=1)))
    rr = np.linspace(0.005, 0.60, 400)
    figs.save_plot("ndc_curve",
                   [("ndc = 1.41√((1−ρ)/ρ)", 100 * rr,
                     1.41 * np.sqrt((1.0 - rr) / rr)),
                    ("使ってよい下限 ndc = 4", np.array([0.5, 60.0]), np.full(2, 4.0)),
                    ("この例題(ρ = %.1f %%)" % (100 * rho),
                     np.array([100 * rho]), np.array([ndc_closed]))],
                   kinds=["line", "line", "scatter"],
                   xlabel="GRR が総変動に占める割合 ρ [%]",
                   ylabel="区別できる階級数 ndc", ylim=(0.0, 20.0),
                   title="「使える測定器か」は 1 本の曲線で決まる",
                   caption="区別できる階級数は、測定の寄与率 ρ **だけ**の関数です —— "
                           "`ndc = 1.41√((1−ρ)/ρ)`。部品の実際の大きさにも単位にも"
                           "よりません。規格の例題は ρ = %.2f %% で **ndc = %.4f**、"
                           "曲線にぴったり乗ります(op の返り値と 1e-3 まで一致)。"
                           "慣行の合格線 4 を割るのは ρ が約 11 %% を超えたあたり。"
                           % (100 * rho, ndc_closed))


# --------------------------------------------------------------------------- #
# 第 7b 章 GUM の「形」を 4 枚で —— 除数・Welch・畳み込み・収束                     #
# --------------------------------------------------------------------------- #
def chapter_gum_gallery():
    print("\n[7b] 不確かさの形 —— 除数・自由度・畳み込み・収束")
    # (a) 分布形ごとの除数。半幅 a を形ごとに変えると、**どれも u = 1** になる。
    a_rect, a_tri, a_u, s_nor = np.sqrt(3.0), np.sqrt(6.0), np.sqrt(2.0), 1.0
    z = np.linspace(-3.4, 3.4, 1201)
    rect = np.where(np.abs(z) <= a_rect, 1.0 / (2 * a_rect), 0.0)
    tri = np.where(np.abs(z) <= a_tri, (a_tri - np.abs(z)) / (a_tri ** 2), 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ush = np.where(np.abs(z) < a_u * 0.999,
                       1.0 / (np.pi * np.sqrt(np.maximum(a_u ** 2 - z ** 2, 1e-12))), 0.0)
    nor = np.exp(-0.5 * (z / s_nor) ** 2) / (s_nor * np.sqrt(2 * np.pi))
    rg = np.random.default_rng(3)
    n_s = 2_000_000
    smp = (rg.uniform(-a_rect, a_rect, n_s),                       # 矩形
           a_tri * 0.5 * (rg.uniform(-1, 1, n_s) + rg.uniform(-1, 1, n_s)),  # 三角
           a_u * np.sin(rg.uniform(0.0, 2 * np.pi, n_s)),          # U 字(逆正弦)
           rg.normal(0.0, s_nor, n_s))                             # 正規
    sds = [float(v.std(ddof=1)) for v in smp]
    # 標本からの標準偏差の誤差は σ/√(2n) ≈ 5e-4。その 10 倍を許容にする。
    check(max(abs(v - 1.0) for v in sds) < 5e-3,
          "★4 つの分布形は半幅を変えると**どれも u = 1** になる",
          "実測 " + " / ".join("%.4f" % v for v in sds))

    # (b) Welch-Satterthwaite: 定理「ν_eff は最小の自由度を下回らない」
    w = np.linspace(0.0, 1.0, 401)
    nu1, nu2 = 3.0, 30.0
    u1, u2 = w, np.sqrt(np.maximum(1.0 - w ** 2, 0.0))
    uc4 = (u1 ** 2 + u2 ** 2) ** 2
    nu_eff = uc4 / (u1 ** 4 / nu1 + u2 ** 4 / nu2 + 1e-300)
    check(float(nu_eff.min()) >= min(nu1, nu2) - 1e-9,
          "★定理: ν_eff は最小の自由度を下回らない",
          "掃引の最小 %.4f(min ν = %.0f)" % (nu_eff.min(), min(nu1, nu2)))

    # (c) Irwin-Hall n = 1..4(どれも u = 1 になるよう規格化)+ 超過尖度の閉形式
    def ih_density(n, y):
        a = np.sqrt(3.0 / n)                       # 各一様の半幅(和の u が 1 になる)
        s = (y + n * a) / (2 * a)                  # y -> [0, n] の変数
        out = np.zeros_like(y)
        for i, zz in enumerate(s):
            acc = 0.0
            for k in range(n + 1):
                c = 1.0
                for q in range(k):
                    c *= (n - q) / (q + 1)
                acc += (-1) ** k * c * max(zz - k, 0.0) ** (n - 1)
            f = 1.0
            for q in range(2, n):
                f *= q
            out[i] = acc / f
        return out / (2 * a)

    y = np.linspace(-4.6, 4.6, 601)
    dens = [ih_density(n, y) for n in (1, 2, 3, 4)]
    dy = float(y[1] - y[0])
    m4 = float(np.sum(dens[3] * y ** 4) * dy)
    check(abs((m4 - 3.0) + 0.3) < 2e-3,
          "★Irwin-Hall(4) の超過尖度は閉形式 −6/(5n) = −0.3",
          "実測 %.4f" % (m4 - 3.0))

    # (d) モンテカルロの収束 —— 端点が厳密解へ 1/√n で寄る
    exact_lo = np.sqrt(3.0) * (2.0 * 0.6 ** 0.25 - 4.0)
    ns = np.array([2_000, 8_000, 32_000, 128_000, 512_000], dtype=float)
    lows = []
    for nn in ns:
        mc = fs.ledger.gum_monte_carlo(
            {"u": [1.0] * 4, "sensitivity": [1.0] * 4,
             "distribution": ["rectangular"] * 4},
            n=int(nn), seed=7, distribution="distribution")
        lows.append(float(mc["low"][0]))
    err = np.abs(np.array(lows) - exact_lo)
    check(err[-1] < err[0],
          "標本を増やすとモンテカルロは厳密解へ寄る",
          "誤差 %.4f(n=2e3) -> %.4f(n=5.1e5)" % (err[0], err[-1]))

    if not figs.enabled():
        return
    figs.save_plot("divisors",
                   [("矩形(半幅 a = √3、除数 √3)", z, rect),
                    ("三角(a = √6、除数 √6)", z, tri),
                    # U 字は両端で**発散する**ので、描くときだけ頭を切る
                    ("U 字(a = √2、除数 √2。両端は切ってある)", z,
                     np.minimum(ush, 0.88)),
                    ("正規(95 %% 幅 / 1.959964)", z, nor)],
                   xlabel="入力量のずれ", ylabel="確率密度", ylim=(0.0, 0.95),
                   title="形が違っても、同じ「u = 1」になる",
                   caption="校正証明書に「±a」とだけ書いてあるとき、それを標準不確かさへ"
                           "直す除数は**形で決まります** —— 矩形なら a/√3、三角なら a/√6、"
                           "両端に寄る U 字(温度の上下動など)なら a/√2、「95 %% の幅」と"
                           "書いてあるなら 1.959964 で割る。この 4 本は**半幅をわざと"
                           "変えて、どれも u = 1 に揃えたもの**(実測 %s)。"
                           "形を取り違えると、同じ ±a が最大 √3 倍ずれます。"
                           % " / ".join("%.4f" % v for v in sds))
    figs.save_plot("welch",
                   [("ν_eff(掃引)", w, nu_eff),
                    ("定理の下限 min ν = 3", np.array([0.0, 1.0]), np.full(2, nu1)),
                    ("成分の自由度の和 33", np.array([0.0, 1.0]), np.full(2, nu1 + nu2))],
                   xlabel="自由度 3 の成分が占める割合 u₁ / u_c", ylabel="有効自由度 ν_eff",
                   title="Welch–Satterthwaite —— 定理がそのまま絵になる",
                   ylim=(0.0, 36.0),
                   caption="自由度 3 の成分と自由度 30 の成分を混ぜ、比だけを左から右へ"
                           "動かしたもの。**ν_eff は下の線(最小の自由度)を決して"
                           "割りません** —— 合成の自由度が、いちばん頼りない成分より"
                           "悪くなることはない、という定理です。左端は自由度 30 の成分"
                           "だけ、右端は自由度 3 の成分だけ。実測の最小 %.4f。"
                           % nu_eff.min())
    figs.save_plot("irwin_hall",
                   [("一様 1 つ", y, dens[0]), ("2 つの和", y, dens[1]),
                    ("3 つの和", y, dens[2]), ("4 つの和", y, dens[3]),
                    ("正規(同じ u = 1)", y,
                     np.exp(-0.5 * y ** 2) / np.sqrt(2 * np.pi))],
                   xlabel="出力 y(どれも u = 1 に規格化)", ylabel="確率密度",
                   title="足すほど正規に近づく —— ただし裾は最後まで薄い",
                   caption="矩形分布を n 個足した分布(Irwin–Hall)を、**どれも"
                           "u = 1 になるように**重ねたもの。n が増えると形は急速に"
                           "正規へ寄りますが、**裾は最後まで薄いまま**です —— "
                           "超過尖度は `−6/(5n)`(n=4 で **−0.3**、実測 %.4f)。"
                           "伝播則が矩形の例で 95 %% 区間を広めに出すのは、この"
                           "薄い裾に正規の厚い裾を当てているからです。" % (m4 - 3.0))
    figs.save_plot("mc_convergence",
                   [("モンテカルロの 2.5 %% 点", ns, np.array(lows)),
                    ("厳密解 √3(2·0.6^¼ − 4) = %.6f" % exact_lo,
                     np.array([ns[0], ns[-1]]), np.full(2, exact_lo))],
                   kinds=["scatter", "line"],
                   xlabel="標本数 n", ylabel="区間の下端",
                   title="乱数は厳密解に寄るだけで、厳密解を超えない",
                   caption="同じ問題(4 つの矩形分布の和)を標本数を変えて 5 回。"
                           "点は**厳密解の線へ寄っていく**だけで、それ以上の情報は"
                           "出てきません(誤差 %.4f → %.4f)。だから厳密解があるなら"
                           "乱数は捨てます —— 公表されている「MCM の区間 ±3.88」も、"
                           "実はモンテカルロの産物ではなく**厳密分位点の丸め**でした。"
                           % (err[0], err[-1]))


# --------------------------------------------------------------------------- #
# 第 2 章 モデルの選択が答えを動かす                                              #
# --------------------------------------------------------------------------- #
def chapter_pooling(G, keep):
    print("\n[2] 交互作用を残すか畳むか —— 同じデータで EV が 7.3 % 動く")
    ev_pool = dict(zip(G["component"], G["sigma"]))["repeatability"]
    ev_keep = dict(zip(keep["component"], keep["sigma"]))["repeatability"]
    ratio = ev_keep / ev_pool - 1.0
    check(abs(ratio - 0.0725) < 0.01, "モデル選択で EV が約 7.3 % 動く",
          "残す %.6f / 畳む %.6f(比 +%.1f %%)" % (ev_keep, ev_pool, 100 * ratio))
    check(bool(G["interaction_pooled"][0]) and not bool(keep["interaction_pooled"][0]),
          "★どちらのモデルで出したかを返り値が申告する",
          "交互作用 p = %.4f(閾値 %.2f)" % (G["interaction_p"][0], G["pool_alpha"][0]))
    # 対照群: 交互作用を大きく入れると auto はプールしない
    rng = np.random.default_rng(5)
    p, o, r = 10, 3, 3
    a, b = rng.normal(0, 1, p), rng.normal(0, .2, o)
    ab = rng.normal(0, 1.5, (p, o))
    part, oper, val = [], [], []
    for i in range(p):
        for j in range(o):
            for _ in range(r):
                part.append("P%02d" % i); oper.append("A%d" % j)
                val.append(10 + a[i] + b[j] + ab[i, j] + rng.normal(0, .1))
    strong = fs.ledger.msa_gauge_rr({"part": np.array(part, dtype=object),
                                     "operator": np.array(oper, dtype=object),
                                     "value": np.array(val)})
    check(not bool(strong["interaction_pooled"][0]),
          "対照群: 交互作用が有意なら畳まない", "p = %.2e" % strong["interaction_p"][0])

    if figs.enabled():
        # ★2 点を結んだ直線では「7.3 % 違う」としか言えない。**交互作用の強さを
        #   掃引**すると、いつモデル選択が効いていつ効かないのかが曲線で見える。
        sds = np.linspace(0.0, 0.8, 9)
        k_ev, p_ev, pooled_at = [], [], []
        for sd in sds:
            rng2 = np.random.default_rng(11)
            pp, oo, vv = [], [], []
            aa = rng2.normal(0, 1.0, 10); bb = rng2.normal(0, 0.2, 3)
            abx = rng2.normal(0, sd, (10, 3)) if sd > 0 else np.zeros((10, 3))
            for i in range(10):
                for j in range(3):
                    for _ in range(3):
                        pp.append("P%02d" % i); oo.append("A%d" % j)
                        vv.append(10 + aa[i] + bb[j] + abx[i, j] + rng2.normal(0, 0.30))
            tb = {"part": np.array(pp, dtype=object),
                  "operator": np.array(oo, dtype=object), "value": np.array(vv)}
            gk = fs.ledger.msa_gauge_rr(tb, pool_interaction=False)
            gp = fs.ledger.msa_gauge_rr(tb, pool_interaction=True)
            ga = fs.ledger.msa_gauge_rr(tb)
            k_ev.append(dict(zip(gk["component"], gk["sigma"]))["repeatability"])
            p_ev.append(dict(zip(gp["component"], gp["sigma"]))["repeatability"])
            pooled_at.append(bool(ga["interaction_pooled"][0]))
        k_ev, p_ev = np.asarray(k_ev), np.asarray(p_ev)
        switch = next((float(sds[i]) for i in range(len(sds)) if not pooled_at[i]), float("nan"))
        figs.save_plot("pooling",
                       [("交互作用を残す", sds, k_ev),
                        ("誤差へ畳む", sds, p_ev),
                        ("仕込んだ真値 0.30", sds, np.full_like(sds, 0.30))],
                       xlabel="仕込んだ交互作用の大きさ", ylabel="繰り返し性 EV の推定",
                       title="モデルの選択はいつ効くのか(交互作用を掃引)",
                       caption="交互作用が**無い**ところ(左端)では畳むほうが真値 0.30 "
                               "に近く、あるところでは畳むと交互作用を誤差に混ぜて"
                               "しまうので上へ外れる。既定の auto は %s 付近で"
                               "「畳まない」へ切り替わった。規格の例題は左端に当たり、"
                               "同じ 90 点で EV は %.6f 対 %.6f = 7.3 %% 違う。"
                               % (("%.2f" % switch) if switch == switch else "検出されない",
                                  ev_keep, ev_pool))


# --------------------------------------------------------------------------- #
# 第 3 章 推定量の揺れと、負の分散成分                                            #
# --------------------------------------------------------------------------- #
def chapter_spread():
    print("\n[3] 推定量の揺れ —— 1 本の種を 1 % の精度で信じてはいけない")
    evs, avs, pvs = [], [], []
    for s in range(40):
        g = fs.ledger.msa_gauge_rr(synth_table(p=60, o=4, r=5, sd_part=2.0,
                                               sd_oper=0.5, sd_err=0.4, seed=s))
        d = dict(zip(g["component"], g["sigma"]))
        evs.append(d["repeatability"]); avs.append(d["reproducibility"])
        pvs.append(d["part"])
    evs, avs, pvs = map(np.asarray, (evs, avs, pvs))
    theory = 0.4 / np.sqrt(2 * 60 * 4 * 4)
    check(abs(evs.std(ddof=1) / theory - 1.0) < 0.35,
          "繰り返し性の揺れが理論 σ/√(2df) と同じ桁",
          "実測 %.5f / 理論 %.5f(df=960)" % (evs.std(ddof=1), theory))
    check(avs.std(ddof=1) > 10 * evs.std(ddof=1),
          "★再現性は桁違いに不確か(測定者 4 人 = 自由度 3)",
          "AV の標準偏差 %.4f vs EV の %.5f" % (avs.std(ddof=1), evs.std(ddof=1)))

    negs = sum(bool(fs.ledger.msa_gauge_rr(
        synth_table(p=60, o=4, r=5, sd_part=2.0, sd_oper=0.0, sd_err=0.4,
                    seed=s))["clamped"][1]) for s in range(40))
    check(negs > 20, "★真値 0 のとき負の分散成分が**多数派**で出る",
          "40 本中 %d 本 —— 丸めを申告しない実装は「差は無い」と言い切る" % negs)

    if figs.enabled():
        idx = np.arange(40, dtype=float)
        figs.save_plot("spread",
                       [("繰り返し性(真値 0.4)", idx, evs),
                        ("再現性(真値 0.5)", idx, avs),
                        ("部品(真値 2.0)", idx, pvs)],
                       xlabel="種", ylabel="推定された標準偏差",
                       title="推定量の揺れ —— 自由度の差がそのまま出る",
                       caption="繰り返し性は 960 の自由度から出るので締まる"
                               "(標準偏差 %.5f)。再現性は測定者 4 人 = 自由度 3 "
                               "しかないので %.3f も揺れる —— 桁が合えば上等という量。"
                               "真値 0 なら 40 本中 %d 本で負になり 0 へ丸められる。"
                               % (evs.std(ddof=1), avs.std(ddof=1), negs),
                       kinds=["scatter", "scatter", "scatter"])
    return evs, avs, negs


# --------------------------------------------------------------------------- #
# 第 4 章 偏りと直線性、そしてカッパ                                              #
# --------------------------------------------------------------------------- #
def chapter_bias_and_kappa():
    print("\n[4] 偏りは基準値で変わるか / 一致率とカッパは別物")
    ref = np.repeat(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), 6)
    a0, b0 = 0.07, -0.013
    B = fs.ledger.msa_bias_linearity({"reference": ref,
                                      "measured": ref + a0 + b0 * ref})
    co = dict(zip(B["term"], B["coef"]))
    check(abs(co["intercept"] - a0) < 1e-12 and abs(co["slope"] - b0) < 1e-12,
          "雑音 0 の直線を厳密に取り戻す",
          "切片 %.15f / 傾き %.15f" % (co["intercept"], co["slope"]))
    flat = fs.ledger.msa_bias_linearity({"reference": ref, "measured": ref + a0})
    check(abs(dict(zip(flat["term"], flat["coef"]))["slope"]) < 1e-14,
          "対照群: 定数偏りなら傾きは 0")

    # カッパ: 合格率を振ると、一致率は上がるのにカッパは上がらない
    rng = np.random.default_rng(3)
    rates, obs, kap = [], [], []
    parts = np.array(["q%03d" % i for i in range(300)])
    for rate in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
        ra = np.where(rng.random(300) < rate, "pass", "fail")
        rb = np.where(rng.random(300) < rate, "pass", "fail")
        K = fs.ledger.msa_attribute_agreement(
            {"appraiser": np.repeat(["A", "B"], 300), "part": np.tile(parts, 2),
             "rating": np.concatenate([ra, rb])})
        rates.append(rate); obs.append(K["observed_agreement"][0])
        kap.append(K["kappa"][0])
    obs, kap = np.asarray(obs), np.asarray(kap)
    check(obs[-1] > 0.85 and abs(kap).max() < 0.2,
          "★独立でたらめでも合格率が高ければ一致率は 9 割近い",
          "一致率 %.3f(合格率 0.95)に対しカッパ %.3f" % (obs[-1], kap[-1]))
    same = fs.ledger.msa_attribute_agreement(
        {"appraiser": np.repeat(["A", "B"], 50),
         "part": np.tile(np.array(["p%02d" % i for i in range(50)]), 2),
         "rating": np.tile(np.where(np.arange(50) < 45, "pass", "fail"), 2)})
    check(abs(same["kappa"][0] - 1.0) < 1e-15, "全員一致なら κ = 1(厳密)")

    if figs.enabled():
        figs.save_plot("bias",
                       [("基準値ごとの平均偏り", B["ref"], B["bias_mean"])],
                       xlabel="基準値", ylabel="偏り(測定値 − 基準値)",
                       title="偏りは基準値で変わる(直線性)",
                       caption="偏り = %.3f %+.3f x 基準値。雑音 0 のデータでは"
                               "最小二乗がこの係数を 1e-15 まで厳密に取り戻す。"
                               "傾きが 0 でなければ、測定系は測定範囲の場所によって"
                               "違う量だけずれている。" % (a0, b0),
                       kinds=["scatter"])
        figs.save_plot("kappa",
                       [("素の一致率", np.asarray(rates), obs),
                        ("カッパ", np.asarray(rates), kap)],
                       xlabel="工程の合格率", ylabel="一致の度合い",
                       title="一致率とカッパは別物 —— 判定は独立(でたらめ)",
                       caption="2 人の検査員が**独立に**判を押している。合格率が"
                               "上がるほど素の一致率は上がる(0.5 → 0.95 で %.2f → "
                               "%.2f)が、カッパは 0 付近に張り付いたまま。"
                               "一致率だけ見ると「よく合っている」と読めてしまう。"
                               % (obs[0], obs[-1]))
    return obs, kap


# --------------------------------------------------------------------------- #
# 第 5 章 不確かさ —— 相関の向きは一定でない                                      #
# --------------------------------------------------------------------------- #
def chapter_uncertainty():
    print("\n[5] 不確かさの合成 —— 相関を無視した誤りの向きは一定でない")
    S = fs.ledger.gum_standard_uncertainty(
        {"halfwidth": [1.0, 1.0, 1.0, 1.0],
         "distribution": ["rectangular", "triangular", "u_shaped", "normal_95"]})
    want = [1 / np.sqrt(3), 1 / np.sqrt(6), 1 / np.sqrt(2), 1 / 1.959963984540054]
    check(np.allclose(S["u"], want, atol=1e-15),
          "分布の形から標準不確かさへ(分散の定義から出る厳密値)",
          "矩形 %.6f / 三角 %.6f / U 字 %.6f" % tuple(S["u"][:3]))

    # 公表例題: 電圧・電流・位相差 -> 抵抗・リアクタンス・インピーダンス
    V = np.array([5.007, 4.994, 5.005, 4.990, 4.999])
    I = np.array([19.663, 19.639, 19.640, 19.685, 19.678]) * 1e-3
    ph = np.array([1.0456, 1.0438, 1.0468, 1.0428, 1.0433])
    n = V.size
    u = [V.std(ddof=1) / np.sqrt(n), I.std(ddof=1) / np.sqrt(n),
         ph.std(ddof=1) / np.sqrt(n)]
    R = np.array([[1.0, -0.36, 0.86], [-0.36, 1.0, -0.65], [0.86, -0.65, 1.0]])
    v, i, p = V.mean(), I.mean(), ph.mean()
    got, none_, pub = [], [], [0.071, 0.295, 0.236]
    for sens in ([np.cos(p) / i, -v * np.cos(p) / i ** 2, -v * np.sin(p) / i],
                 [np.sin(p) / i, -v * np.sin(p) / i ** 2, v * np.cos(p) / i],
                 [1.0 / i, -v / i ** 2, 0.0]):
        got.append(fs.ledger.gum_propagate({"u": u, "sensitivity": sens},
                                           correlation=R)["u_combined"][0])
        none_.append(fs.ledger.gum_propagate({"u": u, "sensitivity": sens})["u_combined"][0])
    got, none_ = np.asarray(got), np.asarray(none_)
    check(np.abs(got - np.asarray(pub)).max() < 1.5e-3,
          "相関つきの公表例題を再現する",
          "u_c = %.4f / %.4f / %.4f(公表 0.071 / 0.295 / 0.236)" % tuple(got))
    check(none_[0] > 2 * got[0] and none_[1] < got[1],
          "★★相関を無視した誤りの向きは**一定でない**",
          "R は %.4f→%.4f(2.8 倍の過大)、X は %.4f→%.4f(過小)"
          % (got[0], none_[0], got[1], none_[1]))

    # Welch-Satterthwaite: 切り捨ては t 表を引く直前
    l_s = 50e6
    E = fs.ledger.gum_expanded(
        {"u": [25.0, 5.8, 3.9, 6.7, 0.58e-6, 0.029],
         "sensitivity": [1.0, 1.0, 1.0, 1.0, l_s * (-0.1), l_s * 11.5e-6],
         "dof": [18.0, 24.0, 5.0, 8.0, 50.0, 2.0]})
    check(E["dof_used"][0] == 16.0 and abs(E["coverage_factor"][0] - 2.12) < 5e-3,
          "★有効自由度は t 表を引く直前に切り捨てる",
          "ν_eff %.2f → 16 で k = %.4f(切り捨てないと 2.1132)"
          % (E["dof_effective"][0], E["coverage_factor"][0]))

    if figs.enabled():
        # ★★規格の「t 表を引く直前に切り捨てる」は、滑らかな t(ν) に対する**階段**。
        #   実装が踏んだ欠陥(切り捨てずに引いた)が、そのまま曲線と階段の差になる。
        from scipy import stats as _st
        nus = np.linspace(2.0, 40.0, 381)
        smooth = _st.t.ppf(0.975, nus)
        stair = _st.t.ppf(0.975, np.floor(nus))
        nu_e, k_used = float(E["dof_effective"][0]), float(E["coverage_factor"][0])
        k_naive = float(_st.t.ppf(0.975, nu_e))
        figs.save_plot("coverage_staircase",
                       [("t₀.₉₇₅(ν) —— 切り捨てない", nus, smooth),
                        ("規格の手順 —— 切り捨ててから引く", nus, stair),
                        ("この例題 ν_eff = %.2f" % nu_e,
                         np.array([nu_e, nu_e]), np.array([1.95, 2.45])),
                        ("正規の分位点 1.959964", nus, np.full_like(nus, 1.959963984540054))],
                       xlabel="有効自由度 ν", ylabel="包含係数 k(95 %)",
                       title="規格が要求する切り捨ては、t 曲線に対する階段である",
                       caption="有効自由度は整数とは限らないので、規格は**次に小さい"
                               "整数へ切り捨ててから** t 表を引けと定める(安全側へ"
                               "倒すため)。端度器校正の例題では ν_eff = %.2f を"
                               "そのまま引くと k = %.4f、16 へ切り捨てると **%.4f** "
                               "—— 公表値は後者。0.3 %% の差だが、拡張不確かさは"
                               "報告書に載る数字である。ν → ∞ で階段も曲線も"
                               "正規の 1.959964 に収束する。" % (nu_e, k_naive, k_used))
        # ★3 点の散布では「向きが逆」が読み取れない。**相関係数を掃引**すると、
        #   2 本の曲線が無相関の水平線を**反対側で**横切るのが見える。
        rr = np.linspace(-0.95, 0.95, 39)
        cr = [np.cos(p) / i, -v * np.cos(p) / i ** 2, -v * np.sin(p) / i]
        cx = [np.sin(p) / i, -v * np.sin(p) / i ** 2, v * np.cos(p) / i]
        sweep_r, sweep_x = [], []
        for rho in rr:
            M = np.array([[1.0, rho, 0.86], [rho, 1.0, -0.65], [0.86, -0.65, 1.0]])
            if np.linalg.eigvalsh(M).min() <= 0:      # 半正定値でない相関は存在しない
                sweep_r.append(np.nan); sweep_x.append(np.nan); continue
            sweep_r.append(fs.ledger.gum_propagate({"u": u, "sensitivity": cr},
                                                   correlation=M)["u_combined"][0])
            sweep_x.append(fs.ledger.gum_propagate({"u": u, "sensitivity": cx},
                                                   correlation=M)["u_combined"][0])
        ok = ~np.isnan(np.asarray(sweep_r))
        figs.save_plot("correlation_sweep",
                       [("抵抗 u_c(R)", rr[ok], np.asarray(sweep_r)[ok]),
                        ("リアクタンス u_c(X)", rr[ok], np.asarray(sweep_x)[ok]),
                        ("R を無相関とした値", rr[ok], np.full(ok.sum(), none_[0])),
                        ("X を無相関とした値", rr[ok], np.full(ok.sum(), none_[1]))],
                       xlabel="電圧と電流の相関係数", ylabel="合成標準不確かさ",
                       title="相関を無視した誤りの向きは、量によって逆になる",
                       caption="電圧と電流の相関だけを振った(他の 2 つは実測値で固定)。"
                               "抵抗の曲線は無相関の水平線より**下**、リアクタンスは"
                               "**上**に来る領域がある —— 同じ 1 組の観測でも、"
                               "感度係数の符号と相関の符号の積で向きが決まるため。"
                               "実測点(r = −0.36)では R が 2.8 倍の過大、X が過小。"
                               "灰色に欠けている両端は、相関行列が半正定値でなくなる"
                               "= そんな相関の組み合わせは存在しない領域。")
        x = np.arange(3, dtype=float)
        figs.save_plot("correlation",
                       [("相関を入れる", x, got), ("相関を無視", x, none_),
                        ("公表値", x, np.asarray(pub))],
                       xlabel="出力(0=抵抗 1=リアクタンス 2=インピーダンス)",
                       ylabel="合成標準不確かさ",
                       title="相関を無視した誤りの向きは一定でない",
                       caption="同じ 1 組の観測から 3 つの量を出している。相関を"
                               "落とすと抵抗は %.4f→%.4f と **2.8 倍過大**に、"
                               "リアクタンスは %.4f→%.4f と過小になる。"
                               "「安全側に外れるから省いてよい」は成り立たない。"
                               % (got[0], none_[0], got[1], none_[1]),
                       kinds=["scatter", "scatter", "scatter"])
    return got, none_, E


# --------------------------------------------------------------------------- #
# 第 6 章 正しく失敗する —— 伝播則が破綻する場所                                   #
# --------------------------------------------------------------------------- #
def chapter_breakdown():
    print("\n[6] 正しく失敗する —— 1 次近似が極値で情報を失う")
    u = [0.005, 0.005]
    xs = np.array([0.0, 0.005, 0.010, 0.020, 0.030, 0.050])
    guf_lo, guf_hi, mc_lo, mc_hi, flags = [], [], [], [], []
    for x1 in xs:
        E = fs.ledger.gum_expanded({"u": u, "sensitivity": [2 * x1, 0.0],
                                    "dof": [np.inf, np.inf]},
                                   estimate=x1 ** 2, lower_bound=0.0)
        M = fs.ledger.gum_monte_carlo({"u": u, "sensitivity": [1.0, 1.0],
                                       "value": [x1, 0.0], "power": [2.0, 2.0]},
                                      n=200_000, seed=3, value="value", power="power")
        guf_lo.append(E["low"][0] * 1e6); guf_hi.append(E["high"][0] * 1e6)
        mc_lo.append(M["low"][0] * 1e6); mc_hi.append(M["high"][0] * 1e6)
        flags.append(list(E["invalid_reasons"]))
    guf_lo, guf_hi = np.asarray(guf_lo), np.asarray(guf_hi)
    mc_lo, mc_hi = np.asarray(mc_lo), np.asarray(mc_hi)

    check(guf_lo[0] == 0.0 and guf_hi[0] == 0.0 and "stationary_point" in flags[0],
          "★★x₁=0 で伝播則は u=0 を返し、**破綻を申告する**",
          "区間 [0, 0]、理由 %s" % flags[0])
    check(abs(mc_hi[0] - 150.0) < 3.0,
          "同じ状況でモンテカルロは [0, 150]e-6 を返す",
          "実測 [%.0f, %.0f]e-6" % (mc_lo[0], mc_hi[0]))
    # ★★その 150 は乱数ではなく**閉形式**で出る: X1²+X2² は u²χ²₂ = 平均 2u² の
    #   指数分布なので、上側 95 % 点は 2u² ln 20。公表値と小数 1 桁まで合う。
    q95 = 2.0 * 0.005 ** 2 * np.log(20.0) * 1e6
    check(abs(q95 - 150.0) < 0.3, "★その上端は 2u²ln20 という閉形式である",
          "%.2f e-6(公表 150)—— 乱数を使わずに出る" % q95)
    check(abs(mc_hi[0] - q95) < 2.0, "モンテカルロが閉形式に寄る",
          "実測 %.1f vs 閉形式 %.2f" % (mc_hi[0], q95))
    neg = [i for i, lo in enumerate(guf_lo) if lo < -1e-9]
    check(neg and all("infeasible_interval" in flags[i] for i in neg),
          "★区間が定義域(非負)を出たら申告する",
          "x₁=%.3f で下端 %.0f e-6" % (xs[neg[0]], guf_lo[neg[0]]))
    check(not flags[-1], "対照群: 極値から離れれば有効",
          "x₁=0.050 で [%.0f, %.0f]e-6" % (guf_lo[-1], guf_hi[-1]))

    if figs.enabled():
        # ★★閉形式が絵になる場所。x1 = x2 = 0 では X1^2 + X2^2 は u^2 chi^2_2、
        #   すなわち**平均 2u^2 の指数分布**。95 % 点は 2 u^2 ln 20 で閉形式。
        uu = 0.005
        mean_exp = 2.0 * uu ** 2                        # = 5.0e-5
        q95 = mean_exp * np.log(20.0)                   # = 1.4979e-4 -> 149.79e-6
        yy = np.linspace(0.0, 2.6e-4, 601)
        dens = np.exp(-yy / mean_exp) / mean_exp
        # 伝播則が仮定する姿: 平均 0・標準偏差 0 の一点集中(= 何も分からない)
        figs.save_plot("stationary_density",
                       [("真の密度(指数 = u² χ²₂)", yy * 1e6, dens * 1e-6),
                        ("閉形式の 95 % 点 2u²ln20", np.array([q95, q95]) * 1e6,
                         np.array([0.0, float(dens.max()) * 1e-6])),
                        ("伝播則が返した区間 [0, 0]", np.array([0.0, 0.0]),
                         np.array([0.0, float(dens.max()) * 1e-6]))],
                       xlabel="比較損失 δY [×10⁻⁶]", ylabel="確率密度 [×10⁶]",
                       title="伝播則が [0, 0] を返した場所の、本当の分布",
                       caption="x₁ = x₂ = 0 では X₁²+X₂² は **u²χ²₂ = 平均 2u² の"
                               "指数分布**になる —— 原点に肩を持つ強く非対称な分布で、"
                               "95 %% 点は **2u²ln20 = %.2f×10⁻⁶** という閉形式"
                               "(公表値 150 と一致)。伝播則は感度 c = 2x₁ が 0 に"
                               "なるので「不確かさゼロ」= 原点の一点しか返せない。"
                               "1 次近似がこの分布まるごとを失っているのが、"
                               "2 本の縦線の距離。" % (q95 * 1e6))
        figs.save_plot("breakdown",
                       [("伝播則 下端", xs, guf_lo), ("伝播則 上端", xs, guf_hi),
                        ("モンテカルロ 下端", xs, mc_lo),
                        ("モンテカルロ 上端", xs, mc_hi)],
                       xlabel="評価点 x₁", ylabel="95 % 区間 [x10⁻⁶]",
                       title="伝播則が破綻する場所(比較損失 δY = X₁² + X₂²)",
                       caption="感度 c₁ = 2x₁ なので x₁=0 では 1 次近似が情報を"
                               "全部失い、伝播則は [0, 0] を返す。x₁ が小さい間は"
                               "区間が**負の損失**を含む(物理的にありえない)。"
                               "モンテカルロは同じ場所で [0, 150] を返す —— "
                               "実装の誤りでなく手法の限界なので、構造で申告する。")
    return xs, guf_lo, guf_hi, mc_lo, mc_hi


# --------------------------------------------------------------------------- #
# 第 7 章 厳密解 —— 乱数を使わない真値                                            #
# --------------------------------------------------------------------------- #
def chapter_exact():
    print("\n[7] 厳密解で挟む —— 4 つの矩形分布の和(Irwin-Hall)")
    exact_lo = np.sqrt(3.0) * (2.0 * 0.6 ** 0.25 - 4.0)
    lin = {"u": [1.0] * 4, "sensitivity": [1.0] * 4}
    guf = fs.ledger.gum_expanded({**lin, "dof": [np.inf] * 4}, estimate=0.0)
    mc = fs.ledger.gum_monte_carlo({**lin, "distribution": ["rectangular"] * 4},
                                   n=1_000_000, seed=1, distribution="distribution")
    half = 0.5 * (mc["high"][0] - mc["low"][0])
    check(abs(exact_lo + 3.879407) < 1e-5, "厳密解 y₂.₅% = √3(2·0.6^¼ − 4)",
          "%.6f" % exact_lo)
    check(abs(half + exact_lo) < 0.02, "モンテカルロが厳密解に寄る",
          "半幅 %.5f vs 厳密 %.5f" % (half, -exact_lo))
    gap = guf["expanded"][0] + exact_lo
    check(abs(gap - 0.040521) < 1e-4,
          "★伝播則は真値より**広い**(正規近似は裾が薄い分布で保守側に外れる)",
          "%.6f(真の 1.939703σ に対し正規の 1.959964σ を使うため)" % gap)
    v2 = fs.ledger.gum_validate(guf, {"low": np.array([exact_lo]),
                                      "high": np.array([-exact_lo])}, ndig=2)
    v3 = fs.ledger.gum_validate(guf, {"low": np.array([exact_lo]),
                                      "high": np.array([-exact_lo])}, ndig=3)
    check(bool(v2["agree"][0]) and not bool(v3["agree"][0]),
          "★検証の梯子が**乱数なしで**決まる",
          "ndig=2(δ=%.3f)は一致、ndig=3(δ=%.3f)は不一致"
          % (v2["delta"][0], v3["delta"][0]))

    if figs.enabled():
        # ★★半幅を 3 本の水平線で並べても「なぜ違うのか」は見えない。**密度を
        #   重ねる**と、正規近似の裾が実際より厚いことが絵で分かる。
        a = np.sqrt(3.0)
        y = np.linspace(-5.2, 5.2, 801)
        s = (y + 4 * a) / (2 * a)                       # y -> Irwin-Hall の変数
        _BIN4 = (1.0, 4.0, 6.0, 4.0, 1.0)            # C(4,k) —— np.math は numpy 2.0 で消えた
        ih = np.array([sum((-1) ** k * _BIN4[k] * max(z - k, 0.0) ** 3
                           for k in range(5)) / 6.0 for z in s]) / (2 * a)
        nor = np.exp(-0.5 * (y / 2.0) ** 2) / (2.0 * np.sqrt(2 * np.pi))
        figs.save_plot("rectangular",
                       [("厳密な密度(Irwin-Hall)", y, ih),
                        ("伝播則が仮定する正規", y, nor),
                        # ★区間は**水平の線分**で描く(plot_series は非有限を拒むので
                        #   「NaN で区切って 2 本の縦線」は使えない。読みやすくもある)
                        ("厳密の 95 %% 区間 ±%.4f" % -exact_lo,
                         np.array([exact_lo, -exact_lo]),
                         np.full(2, float(ih.max()) * 0.62)),
                        ("伝播則の 95 %% 区間 ±%.4f" % guf["expanded"][0],
                         np.array([-guf["expanded"][0], guf["expanded"][0]]),
                         np.full(2, float(ih.max()) * 0.70))],
                       xlabel="出力 y", ylabel="確率密度",
                       title="正規近似が広く出る理由は、裾の厚みの違い",
                       caption="各 u=1 の一様分布 4 つの和は**スケールした "
                               "Irwin-Hall(4)** で、超過尖度が −6/(5n) = −0.3 —— "
                               "正規より**裾が薄い**(グラフの両端で 2 本が離れる)。"
                               "だから同じ標準偏差 2.00 でも 95 %% 区間は厳密 "
                               "±%.4f に対し正規近似 ±%.4f と **%.6f 広く**出る。"
                               "モンテカルロの実測は半幅 %.5f。この図に乱数は"
                               "1 つも使っていない(密度はどちらも閉形式)。"
                               % (-exact_lo, guf["expanded"][0], gap, half))
    return exact_lo, guf, half, gap


def plot_frame(series, xlabel="", ylabel="", title="", size=(560, 360),
               xlim=None, ylim=None, kinds=None):
    """``examplefig.save_plot`` と同じ手順で**画像を組んで返す**(保存しない)。

    ★GIF のコマを作るためだけの関数。軸・格子・凡例はすべて fullseye の
    annotate 族が引くので、静止画と見た目が揃う(別の描画器で描くと、同じ
    記事の中で図の様式が 2 つになる)。
    """
    w, h = size
    img = np.full((h, w, 3), 1.0)
    rect = (72, 44, w - 96, h - 92)
    ax = fs.axes_transform(rect, xlim, ylim)
    xt = fs.nice_ticks(xlim[0], xlim[1], 6)
    yt = fs.nice_ticks(ylim[0], ylim[1], 5)
    img = np.asarray(fs.grid_lines(img, ax, xticks=xt, yticks=yt, alpha=0.25))
    img = np.asarray(fs.axes_frame(img, ax, width=1))
    img = np.asarray(fs.ticks(img, ax, xticks=xt, yticks=yt, tick_len=5, font_size=10))
    colours = ("reference", "emphasis", "right", "wrong", "neutral")
    legend = []
    for k, (label, x, y) in enumerate(series):
        c = colours[k % len(colours)]
        img = np.asarray(fs.plot_series(img, ax, np.asarray(x, float),
                                        np.asarray(y, float),
                                        kind=(kinds[k] if kinds else "line"),
                                        color=c, width=2, marker_size=3))
        legend.append((c, label))
    if len(legend) > 1:
        img = np.asarray(fs.legend_box(img, legend, (w - 14, 50), anchor="rt",
                                       markers=True, font_size=11, swatch=11, pad=6))
    img = np.asarray(fs.text_box(img, title, (10, 8), anchor="lt", font_size=13))
    foot = (xlabel + ("   |   " if xlabel and ylabel else "") + ylabel).strip()
    if foot:
        img = np.asarray(fs.text_box(img, foot, (10, h - 10), anchor="lb", font_size=11))
    return img


def chapter_breakdown_movie():
    """★動く図: 評価点を動かして、伝播則が壊れて追いつくまでを見せる。"""
    if not figs.enabled():
        return
    print("\n[6b] 動く図 —— 壊れ方は連続ではない")
    u = 0.005
    # ★窓は**3 段階すべてが入る**ように取る。伝播則の下端が 0 を超えるのは
    #   x1 > 2 k u = 0.0196 なので、そこまで届かない窓だと「追いつく」が見えない。
    xs = np.linspace(0.0, 0.026, 18)
    edges = np.linspace(0.0, 1.30e-3, 81)
    centres = 0.5 * (edges[1:] + edges[:-1])
    frames = []
    for x1 in xs:
        rng = np.random.default_rng(5)
        y = (x1 + rng.normal(0.0, u, 120_000)) ** 2 + rng.normal(0.0, u, 120_000) ** 2
        hist, _ = np.histogram(y, bins=edges, density=True)
        # ★各コマで最大値に正規化する。絶対密度のままだと、指数(原点で 2e4)と
        #   後半の正規(1.6e3)で 1 桁違い、後半が平らに潰れて**形の変化が見えない**。
        hist = hist / max(float(hist.max()), 1e-30)
        E = fs.ledger.gum_expanded({"u": [u, u], "sensitivity": [2 * x1, 0.0],
                                    "dof": [np.inf, np.inf]}, estimate=x1 ** 2,
                                   lower_bound=0.0)
        lo, hi = float(E["low"][0]), float(E["high"][0])
        frames.append(plot_frame(
            [("真の分布(モンテカルロ)", centres * 1e6, hist),
             # 区間は水平の線分(plot_series は非有限を拒む)
             ("伝播則の 95 % 区間", np.array([lo, hi]) * 1e6, np.full(2, 1.14)),
             ("評価点 x₁²", np.array([x1 ** 2, x1 ** 2]) * 1e6,
              np.array([0.0, 1.30]))],
            xlabel="比較損失 δY [×10⁻⁶]", ylabel="相対密度(各コマで最大 = 1)",
            title="x₁ = %.4f  —— 伝播則: %s" % (
                x1, "破綻(区間 [0,0])" if not E["guf_valid"][0] and lo == hi == 0.0
                else ("負へ張り出す" if lo < -1e-12 else "有効")),
            xlim=(-200.0, 1400.0), ylim=(0.0, 1.40)))
    figs.save_gif("breakdown_movie", frames, fps=4.0,
                  caption="評価点 x₁ を 0 から 0.026 へ動かしたもの。★左端では真の分布が"
                          "**原点に肩を持つ指数**(u²χ²₂)で、伝播則は感度 c = 2x₁ が 0 に"
                          "なるため区間が**1 点に潰れる**。少し動かすと今度は区間が"
                          "**負の損失**へ張り出す(物理的にありえない)。さらに離れると"
                          "真の分布が正規に近づき、両者はようやく重なる —— "
                          "**壊れ方は連続ではなく、3 つの段階がある**。")
    print("  [OK] 動く図を書いた(%d コマ)" % len(frames))


def main():
    t0 = time.time()
    print("=" * 74)
    print("PoC: その数字のうち、いくつが測り方のものか")
    print("=" * 74)
    G, keep = chapter_components()
    chapter_report_panels(G)
    chapter_pooling(G, keep)
    evs, avs, negs = chapter_spread()
    obs, kap = chapter_bias_and_kappa()
    got, none_, E = chapter_uncertainty()
    xs, guf_lo, guf_hi, mc_lo, mc_hi = chapter_breakdown()
    chapter_breakdown_movie()
    exact_lo, guf, half, gap = chapter_exact()
    chapter_gum_gallery()

    if figs.enabled():
        s = dict(zip(G["component"], G["sigma"]))
        rows = [
            ["平方和の分解", "SS の加法性", "相対差 1e-16", "恒等式(厳密)"],
            ["ゲージ R&R", "EV / AV / GRR / PV", "%.6f / %.6f / %.6f / %.6f"
             % (s["repeatability"], s["reproducibility"], s["gauge_rr"], s["part"]),
             "公表 0.199933 / 0.226838 / 0.302373 / 1.042327"],
            ["モデル選択", "EV(残す vs 畳む)", "%.6f vs %.6f"
             % (dict(zip(keep["component"], keep["sigma"]))["repeatability"],
                s["repeatability"]), "7.3 %% 動く(交互作用 p = %.4f)"
             % G["interaction_p"][0]],
            ["推定の揺れ", "EV の標準偏差(種 40 本)", "%.5f" % evs.std(ddof=1),
             "理論 σ/√(2df) = 0.00913"],
            ["負の分散成分", "真値 0 で負になる回数", "40 本中 %d 本" % negs,
             "稀な端ではなく多数派"],
            ["カッパ", "一致率 vs カッパ(合格率 0.95)", "%.3f vs %.3f"
             % (obs[-1], kap[-1]), "独立な判定なので κ ≈ 0 が正しい"],
            ["相関", "u_c(R) 相関あり → なし", "%.4f → %.4f" % (got[0], none_[0]),
             "2.8 倍の**過大**(向きは一定でない)"],
            ["有効自由度", "ν_eff → 切り捨て → k", "%.2f → %.0f → %.4f"
             % (E["dof_effective"][0], E["dof_used"][0], E["coverage_factor"][0]),
             "公表 16.7 → 16 → 2.12"],
            ["伝播則の破綻", "x₁=0 の区間", "[%.0f, %.0f]e-6" % (guf_lo[0], guf_hi[0]),
             "モンテカルロは [%.0f, %.0f]e-6" % (mc_lo[0], mc_hi[0])],
            ["厳密解", "矩形和の 95 % 半幅", "%.6f" % half,
             "Irwin-Hall %.6f / 伝播則 %.6f" % (-exact_lo, guf["expanded"][0])],
        ]
        figs.save_table("numbers", ["主張", "測った量", "実測", "真値 / 期待"], rows,
                        title="測り方のぶんを分ける —— 絵の外から当てた答え",
                        caption="どの行も「使った式」ではない真値で採点している: "
                                "平方和の代数的分解、既存 numpy の標本分散、公表"
                                "された worked example、Irwin-Hall の厳密解、"
                                "そして導出の違う 2 経路(伝播則とモンテカルロ)。")
    assert not figs.errors(), figs.errors()
    bad = [c for c in CHECKS if not c[0]]
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)"
          % (len(CHECKS), len(CHECKS) - len(bad), time.time() - t0))
    if bad:
        for _, label, detail in bad:
            print("  NG:", label, detail)
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()
