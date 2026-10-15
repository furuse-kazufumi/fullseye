# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""doe_plan_tour — 検査カメラの条件出しを「1 つずつ振る」以外のやり方で計画する。

    py -3.11 examples/doe_plan_tour.py

【題材】金属の表面の細い傷を、照明の角度・照明の強さ・露光時間・ゲインの 4 条件で撮る。どの条件で傷が一番
よく見えるかを決めたいが、4 条件 x 3 水準を全部撮ると 81 回。現場では「1 つずつ振る」が多いが、それでは
条件の組み合わせ(角度を寝かせたら露光を減らす、のような)が見えない。

【この例が示すこと】
1. **直交表 L9** —— 4 条件 x 3 水準を 9 回で。どの 2 条件を取っても 9 通りの組がちょうど 1 回ずつ出る
   (公表された表そのもの。tests/test_multivar_doe.py が NIST の表と行まで照合)。9 回の画像を並べる。
2. **一部実施の落とし穴** —— 5 条件を 2^(5-2) = 8 回で振ると、「ゲイン」の主効果と「角度 x 露光」の交互作用が
   同じ列になる(分解能 III)。ゲインは何もしていないのに、8 回の計画は「ゲインが効く」と答える。
   全 32 回の計画ではゲインの効果は 0。交絡表はこの取り違えを事前に言っている。
3. **LHS** —— 20 回を乱数で置くと、空いた区間ができる。ラテン超方格は各条件の各区間にちょうど 1 点。
4. **応答曲面の計画** —— 中心複合計画(回転可能、α = 2^{2/4} = 1.414)は軸の点が範囲の外に出る
   (照明をそこまで寝かせられるかを先に確かめる)。Box-Behnken は角を踏まない。

【グラウンドトゥルース】公表表(NIST)・定義関係から計算した交絡・層の数え上げ・α = F^{1/4}。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs      # noqa: E402
import fullseye as fs          # noqa: E402  公開経路(fs.ledger.<名前>)から呼ぶ

N = 96
FULL_WELL = 4095.0


def scratch_scene(angle_deg, power, exposure_ms, gain_db, seed=0):
    """金属面の細い傷を撮った 12 bit 画像(簡単な物理モデル)と、傷の見え(コントラスト対雑音比)。

    面: 細かい研磨目 + 斜めに走る V 字の傷(深さ 3、幅 2 画素)。照明は傷に直交する方位から仰角 ``angle_deg``。
    明るさ = 拡散 + 鏡面(Blinn-Phong)、電子数 = 強さ x 露光 x 明るさ、光子雑音 + 読み出し雑音 2 e-、
    ゲイン倍で DN、12 bit で丸めて飽和。見え = |傷 − 背景| / 背景の標準偏差。
    """
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:N, 0:N].astype(float)
    d = (x - y) / np.sqrt(2.0)                                   # 傷からの符号つき距離
    h = -3.0 * np.exp(-0.5 * (d / 2.0) ** 2) + 0.05 * rng.standard_normal((N, N))
    gy, gx = np.gradient(h)
    n = np.stack([-gx, -gy, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=0)
    a = np.radians(angle_deg)
    light = np.array([np.cos(a) / np.sqrt(2), -np.cos(a) / np.sqrt(2), np.sin(a)])
    half = light + np.array([0.0, 0.0, 1.0])
    half /= np.linalg.norm(half)
    ndl = np.clip(np.tensordot(light, n, 1), 0, None)
    ndh = np.clip(np.tensordot(half, n, 1), 0, None)
    refl = 0.3 * ndl + 0.7 * ndh ** 40
    electrons = power * exposure_ms * 150.0 * refl
    electrons = electrons + np.sqrt(np.maximum(electrons, 0)) * rng.standard_normal((N, N)) + 2.0 * rng.standard_normal((N, N))
    dn = np.clip(np.round(electrons * 10 ** (gain_db / 20.0)), 0, FULL_WELL)
    on = np.abs(d) < 1.5
    bg = np.abs(d) > 8
    cnr = abs(dn[on].mean() - dn[bg].mean()) / max(dn[bg].std(), 1e-9)
    return dn, float(cnr)


def run() -> dict:
    t0 = time.perf_counter()
    out = {}

    # ---- 1. 直交表 L9 ----------------------------------------------------------- #
    factors = [("angle", 15.0, 75.0, "deg"), ("power", 0.5, 1.5, "a.u."),
               ("exposure", 2.0, 8.0, "ms"), ("gain", 0.0, 12.0, "dB")]
    l9 = fs.ledger.doe_orthogonal_array("L9", factors)
    nat = fs.ledger.doe_decode(l9)
    imgs, cnr = [], []
    for row in nat:
        im, c = scratch_scene(*row)
        imgs.append(im)
        cnr.append(c)
    cnr = np.array(cnr)
    print("1) L9: 4 条件 x 3 水準を %d 回(全部なら 81 回)。強さ 2 の直交性 %s / 公表表 %s"
          % (len(nat), l9["meta"]["strength2_ok"], l9["meta"]["array"]))
    for row, c in zip(nat, cnr):
        print("   角度 %4.0f°  強さ %.1f  露光 %.0f ms  ゲイン %4.1f dB  ->  傷の見え %.1f" % (*row, c))
    assert l9["meta"]["strength2_ok"] and nat.shape == (9, 4)
    # 2 条件のどの組も 9 通りがちょうど 1 回(直交表の定義)
    for a in range(4):
        for b in range(a + 1, 4):
            assert len({(p, q) for p, q in zip(l9["coded"][:, a], l9["coded"][:, b])}) == 9
    out["l9_best_run"] = int(np.argmax(cnr)) + 1

    # ---- 2. 一部実施の落とし穴 --------------------------------------------------- #
    # 応答: 角度と露光の交互作用だけ(ゲインは本当に何もしない)+ 角度の主効果
    five = ["angle", "exposure", "power", "gain", "filter"]
    frac = fs.ledger.doe_fractional_factorial(five, 2)               # D=AB, E=AC(NIST Table 3.17)
    full = fs.ledger.doe_fractional_factorial(five, 0)

    def response(c):
        return 10.0 + 2.0 * c[:, 0] + 3.0 * c[:, 0] * c[:, 1]

    def effects(dsg):
        c = dsg["coded"]
        y = response(c)
        return np.array([y[c[:, j] > 0].mean() - y[c[:, j] < 0].mean() for j in range(c.shape[1])])

    ef, eF = effects(frac), effects(full)
    print("2) 2^(5-2) 分解能 %s、交絡: %s" % (frac["meta"]["resolution_roman"],
                                          [a for a in frac["alias"] if a.startswith("gain")]))
    print("   ゲインの効果: 8 回の計画 %.1f / 全 32 回 %.1f(真値 0)" % (ef[3], eF[3]))
    assert frac["resolution"] == 3 and abs(ef[3] - 6.0) < 1e-9 and abs(eF[3]) < 1e-12
    assert any(a.startswith("gain = angle*exposure") for a in frac["alias"])

    # ---- 3. LHS と乱数 ------------------------------------------------------------ #
    n = 20
    lhs = fs.ledger.doe_lhs(n, [("angle", 15, 75, "deg"), ("exposure", 2, 8, "ms")], seed=1, maximin=20)
    rnd = np.random.default_rng(1).random((n, 2))
    u = (lhs["coded"] + 1) / 2
    empty_lhs = sum(n - len(set(np.floor(u[:, j] * n).astype(int))) for j in range(2))
    empty_rnd = sum(n - len(set(np.floor(rnd[:, j] * n).astype(int))) for j in range(2))
    print("3) 20 回: 空いた区間 LHS %d / 乱数 %d(2 条件 x 20 区間のうち)" % (empty_lhs, empty_rnd))
    assert empty_lhs == 0 and empty_rnd > 0

    # ---- 4. 応答曲面の計画 -------------------------------------------------------- #
    two = [("angle", 30.0, 60.0, "deg"), ("exposure", 3.0, 6.0, "ms")]
    ccd = fs.ledger.doe_central_composite(two, center=5)
    bbd = fs.ledger.doe_box_behnken([("angle", 30.0, 60.0, "deg"), ("exposure", 3.0, 6.0, "ms"),
                                     ("power", 0.5, 1.5, "a.u.")], center=3)
    print("4) CCD: α = %.3f(= 4^(1/4))、範囲の外に出る条件 %s、角度 %.1f〜%.1f°"
          % (ccd["meta"]["alpha"], ccd["meta"]["outside_range"], ccd["natural"][:, 0].min(), ccd["natural"][:, 0].max()))
    print("   Box-Behnken 3 条件: %d 回、角(全部が端)の点 %d"
          % (len(bbd["coded"]), int(np.all(np.abs(bbd["coded"]) == 1, axis=1).sum())))
    assert abs(ccd["meta"]["alpha"] - 2 ** 0.5) < 1e-12 and ccd["meta"]["outside_range"] == ["angle", "exposure"]

    # ---- 図 ---------------------------------------------------------------------- #
    if figs.enabled():
        caps = ["#%d %.0f° x%.1f %.0fms %.0fdB 見え%.1f" % (i + 1, *r, c) for i, (r, c) in enumerate(zip(nat, cnr))]
        figs.save_grid("l9_images", [im / FULL_WELL for im in imgs], captions=caps, ncols=3, gray=True,
                       vrange=(0.0, 1.0),
                       title="直交表 L9: 4 条件 x 3 水準を 9 回で撮る",
                       caption="角度・強さ・露光・ゲインを L9 の 9 行どおりに設定して撮った傷。どの 2 条件の組も 9 通りが"
                               "1 回ずつ出るので、9 回でも各条件の効果を平均で比べられる。照明を寝かせる(15°)と傷の斜面が光り、"
                               "#3(強さ・露光・ゲインが最大)では傷の縁が 12 bit で飽和して見えが #2 より下がる。")
        figs.save_table("l9_runs", ["#", "angle (deg)", "power", "exposure (ms)", "gain (dB)", "scratch CNR"],
                        [[i + 1, "%.0f" % r[0], "%.1f" % r[1], "%.0f" % r[2], "%.0f" % r[3], "%.2f" % c]
                         for i, (r, c) in enumerate(zip(nat, cnr))],
                        title="L9 の 9 回と傷の見え(コントラスト / 背景の雑音)",
                        caption="自然単位は doe_decode が符号化(−1, 0, +1)から戻した値。")
        names = ["angle", "exposure", "power", "gain", "filter"]
        figs.save_plot("fraction_alias",
                       [("全 32 回で推定した効果", np.arange(5) - 0.12, eF),
                        ("8 回(2^(5-2))で推定した効果", np.arange(5) + 0.12, ef)]
                       + [("", [j - 0.12, j - 0.12], [0, eF[j]]) for j in range(5)]
                       + [("", [j + 0.12, j + 0.12], [0, ef[j]]) for j in range(5)],
                       kinds=["scatter", "scatter"] + ["line"] * 10,
                       colors=["reference", "wrong"] + ["reference"] * 5 + ["wrong"] * 5,
                       xlim=(-0.5, 4.5), ylim=(-0.5, 7.0),
                       xlabel="条件(0=角度 1=露光 2=強さ 3=ゲイン 4=フィルタ)", ylabel="主効果(+1 と −1 の差)",
                       title="ゲインは何もしていないのに、8 回の計画は「ゲインが効く」と言う",
                       caption="応答は 角度 + 角度 x 露光 の交互作用だけ。2^(5-2) は D = AB(ゲイン = 角度 x 露光)で作るので、"
                               "交互作用の 6 がゲインの列に乗る。doe_fractional_factorial の alias はこれを事前に "
                               "'gain = angle*exposure' と書いている。分解能 III の計画では主効果を交互作用から分けられない。")
        figs.save_plot("lhs_vs_random",
                       [("乱数(空いた区間 %d)" % empty_rnd, rnd[:, 0], rnd[:, 1]),
                        ("ラテン超方格(空いた区間 0)", u[:, 0], u[:, 1])]
                       + [("", [k / n, k / n], [0, 1]) for k in range(1, n)],
                       kinds=["scatter", "scatter"] + ["line"] * (n - 1),
                       styles=[None, None] + ["dotted"] * (n - 1),
                       colors=["wrong", "right"] + ["neutral"] * (n - 1), xlim=(0.0, 1.0), ylim=(0.0, 1.0), size=(560, 520),
                       xlabel="角度(0..1 に正規化)", ylabel="露光(0..1 に正規化)",
                       title="20 回の置き方 —— 縦線は角度の 20 区間",
                       caption="乱数は同じ区間に 2 点が入り、空く区間が出る。ラテン超方格はどの条件で見ても 20 区間に"
                               "1 点ずつ(McKay 1979)。maximin=20 は 20 通りのうち点どうしが一番離れたものを選ぶ。")
        box_x, box_y = [30, 60, 60, 30, 30], [3, 3, 6, 6, 3]
        figs.save_plot("ccd_layout",
                       [("中心複合(回転可能)", ccd["natural"][:, 0], ccd["natural"][:, 1]),
                        ("設定範囲(lo..hi)", box_x, box_y)],
                       kinds=["scatter", "line"], styles=[None, "dashed"], colors=["emphasis", "reference"],
                       xlabel="照明の角度 (deg)", ylabel="露光 (ms)",
                       title="中心複合計画 —— 軸の点は範囲の外に出る(α = 1.414)",
                       caption="要因の 4 点が範囲の角、軸の 4 点が中心から α 倍、中心 5 回。回転可能(予測の分散が中心からの"
                               "距離だけで決まる)にするための α = F^{1/4}。照明を %.1f° まで寝かせられないなら inscribed=True で"
                               "全体を範囲の内側へ縮める。" % ccd["natural"][:, 0].min())
    assert not figs.errors(), figs.errors()

    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  doe_plan_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
