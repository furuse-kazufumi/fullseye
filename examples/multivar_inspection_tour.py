# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""multivar_inspection_tour — 撮った画像から「どの条件が効いたか」「最良はどこか」「画像から条件を読めるか」を出す。

    py -3.11 examples/multivar_inspection_tour.py

【題材】金属の表面の細い傷を、照明の角度・照明の強さ・露光時間・ゲインで撮る(doe_plan_tour と同じ簡単な
物理モデル: 研磨目 + V 字の傷、拡散 + 鏡面、光子雑音 + 読み出し雑音、12 bit で飽和)。

【この例が示すこと】
1. **主効果(直交表 L9 x 繰り返し 3)** —— 9 条件 x 3 回の撮影で、各条件の水準ごとの平均(応答表)を出す。
   照明の角度が支配的で、ゲインはほぼ効かない(信号も雑音も同じ倍率で増えるから)。望大 SN 比も出すが、
   推奨の水準は平均と log s から決める(SN 比は平均と散らばりを 1 つに混ぜる、Box 1988)。
2. **応答曲面(中心複合計画)** —— 角度(4〜20°)と露光(6〜30 ms)の 2 条件を 13 回で振り、二次曲面を当てる。
   同じモデルを 21 x 21 の格子で総当たりした「真の地図」と並べ、停留点が真の最良の近くにあるかを確かめる。
   当てはまりの悪さ(純誤差との F 検定)も出す —— 二次で足りなければ、ここが言う。
3. **PCA(特徴量 9 本)** —— ラテン超方格の 40 回で撮った画像から 9 つの特徴量(平均・散らばり・分位点・
   コントラスト・鮮鋭さ・飽和の割合)を取ると、平行分析は「独立な情報は 2〜3 次元」と言う。
4. **PLS(画像 → 条件)** —— 特徴量から照明の角度を読む。30 回で学習し、残り 10 回で確かめる。NIPALS と
   SIMPLS(第 2 実装)の係数が一致、VIP が効いた特徴を並べる。同じ特徴量で露光を読もうとすると読めない
   (強さ・露光・ゲインが明るさを同じように変えるので、画像からは積しか決まらない)—— それも数字で出す。

【グラウンドトゥルース】二次式の停留点 = 解析解(テストで固定)、格子の総当たり、PLS の 2 実装の一致、
ホールドアウトの誤差。
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
    """金属面の細い傷を撮った 12 bit 画像と傷の見え(コントラスト / 背景の雑音)。doe_plan_tour と同じモデル。"""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:N, 0:N].astype(float)
    d = (x - y) / np.sqrt(2.0)
    h = -3.0 * np.exp(-0.5 * (d / 2.0) ** 2) + 0.05 * np.random.default_rng(0).standard_normal((N, N))
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
    e = power * exposure_ms * 150.0 * refl
    e = e + np.sqrt(np.maximum(e, 0)) * rng.standard_normal((N, N)) + 2.0 * rng.standard_normal((N, N))
    dn = np.clip(np.round(e * 10 ** (gain_db / 20.0)), 0, FULL_WELL)
    on, bg = np.abs(d) < 1.5, np.abs(d) > 8
    return dn, float(abs(dn[on].mean() - dn[bg].mean()) / max(dn[bg].std(), 1e-9))


def run() -> dict:
    t0 = time.perf_counter()
    out = {}

    # ---- 1. 主効果(L9 x 繰り返し 3)-------------------------------------------- #
    factors = [("angle", 15.0, 75.0, "deg"), ("power", 0.5, 1.5, "a.u."),
               ("exposure", 2.0, 8.0, "ms"), ("gain", 0.0, 12.0, "dB")]
    l9 = fs.ledger.doe_orthogonal_array("L9", factors)
    nat = fs.ledger.doe_decode(l9)
    Y = np.array([[scratch_scene(*row, seed=s)[1] for s in range(3)] for row in nat])
    me = fs.ledger.doe_main_effects(l9, Y, goal="larger")
    print("1) L9 x 3 回: 条件ごとの効果(水準平均の幅)と寄与率")
    for name in me["table"]:
        t = me["table"][name]
        print("   %-8s 水準平均 %s  幅 %5.2f  寄与 %4.1f%%  推奨 %s  (SN 比なら %s)"
              % (name, np.round(t["mean"], 2), t["range"], 100 * t["share"],
                 t["levels_natural"][list(t["levels_coded"]).index(me["best_levels"][name])],
                 t["levels_natural"][list(t["levels_coded"]).index(me["sn_best_levels"][name])]))
    shares = {k: v["share"] for k, v in me["table"].items()}
    assert max(shares, key=shares.get) == "angle" and shares["angle"] > 0.5
    assert shares["gain"] < 0.1
    out["main_effect_angle_share"] = round(shares["angle"], 3)

    # ---- 2. 応答曲面(角度 x 露光、中心複合計画)---------------------------------- #
    two = [("angle", 4.0, 20.0, "deg"), ("exposure", 6.0, 30.0, "ms")]
    ccd = fs.ledger.doe_central_composite(two, center=5, inscribed=True)
    nc = fs.ledger.doe_decode(ccd)
    y = np.array([scratch_scene(a, 1.0, e, 6.0, seed=i)[1] for i, (a, e) in enumerate(nc)])
    rs = fs.ledger.rsm_fit(ccd, y)
    st = rs["stationary"]
    ga = np.linspace(4, 20, 31)
    ge = np.linspace(6, 30, 31)
    truth = np.array([[np.mean([scratch_scene(a, 1.0, e, 6.0, seed=s)[1] for s in range(2)]) for a in ga] for e in ge])
    ib = np.unravel_index(np.argmax(truth), truth.shape)
    best_true = (ga[ib[1]], ge[ib[0]])
    print("2) 応答曲面 13 回: 停留点は %s、R² %.3f、当てはまりの悪さ(純誤差との F 検定)p = %s"
          % (rs["canonical"]["kind"], rs["r2"],
             "%.3g" % rs["lack_of_fit"]["p"] if rs["lack_of_fit"]["testable"] else rs["lack_of_fit"]["reason"]))
    if st is not None:
        print("   停留点 角度 %.1f° 露光 %.2f ms(予測の見え %.2f、領域の内側 %s)/ 総当たり 441 点の最良 角度 %.1f° 露光 %.2f ms"
              % (st["natural"][0], st["natural"][1], st["y"], st["inside_region"], *best_true))
    assert rs["r2"] > 0.8
    # 露光の山の向こうで縁が飽和して見えが折れる —— 二次では足りないことを当てはまりの悪さが言う
    lof_p = rs["lack_of_fit"]["p"] if rs["lack_of_fit"]["testable"] else None
    # 予測の地図(符号化の格子で当てた曲面を評価)
    cg = fs.ledger.doe_encode(np.stack(np.meshgrid(ga, ge), axis=-1).reshape(-1, 2), two)["coded"]
    M = np.column_stack([np.ones(len(cg)), cg[:, 0], cg[:, 1], cg[:, 0] * cg[:, 1], cg[:, 0] ** 2, cg[:, 1] ** 2])
    pred = (M @ rs["coef"]).reshape(truth.shape)
    i_pred = np.unravel_index(np.argmax(pred), pred.shape)
    best_pred = (ga[i_pred[1]], ge[i_pred[0]])
    loss = truth.max() - truth[i_pred]
    print("   曲面の最良(範囲内)角度 %.1f° 露光 %.2f ms → 真の地図で %.2f(真の最良 %.2f、損 %.1f%%)"
          % (*best_pred, truth[i_pred], truth.max(), 100 * loss / truth.max()))
    assert loss / truth.max() < 0.15
    out["rsm_loss_share"] = round(float(loss / truth.max()), 3)

    # ---- 3. PCA(LHS 40 回 x 特徴量 9 本)--------------------------------------- #
    lhs = fs.ledger.doe_lhs(40, factors, seed=2, maximin=20)
    nl = fs.ledger.doe_decode(lhs)
    imgs = [scratch_scene(*row, seed=100 + i)[0] for i, row in enumerate(nl)]
    feats = ["mean", "std", "p01", "p50", "p99", "michelson_contrast", "grad_energy", "laplacian_var",
             "saturated_fraction"]
    tab = fs.ledger.feat_image_vector(imgs, feats, data_range=(0.0, FULL_WELL), unit="DN")
    pca = fs.ledger.mv_pca(tab, seed=0)
    print("3) PCA: 特徴量 %d 本 → 平行分析 %d 成分 / 累積 90%% なら %d 成分(寄与 %s)"
          % (len(feats), pca["n_components"]["parallel"], pca["n_components"]["cumulative"],
             np.round(pca["explained_ratio"][:4], 3)))
    assert 1 <= pca["n_components"]["parallel"] <= 4

    # ---- 4. PLS(画像の特徴量 → 照明の角度)---------------------------------------- #
    X = np.log(np.maximum(tab["matrix"], 1e-6))
    # 露光は読めない: 強さ x 露光 x ゲインが同じ明るさを作るので、画像は露光だけを教えない(交絡)
    q2_exposure = fs.ledger.mv_pls(X[:30], nl[:30, 2])["q2"]
    yexp = nl[:, 0]
    tr, te = np.arange(40) < 30, np.arange(40) >= 30
    pls = fs.ledger.mv_pls(X[tr], yexp[tr])
    pls2 = fs.ledger.mv_pls(X[tr], yexp[tr], n_components=pls["n_components"], method="simpls")
    pred_te = X[te] @ pls["coef"][:, 0] + pls["intercept"][0]
    rmse = float(np.sqrt(np.mean((pred_te - yexp[te]) ** 2)))
    sd = float(yexp[te].std())
    order = np.argsort(-pls["vip"])
    print("4) PLS(特徴量 → 角度): %d 成分、Q² %.3f、ホールドアウト 10 回の RMSE %.1f°(角度の散らばり %.1f°)"
          % (pls["n_components"], pls["q2"], rmse, sd))
    print("   同じ特徴量で露光を読もうとすると Q² %.2f —— 強さ x 露光 x ゲインが同じ明るさを作るので画像は露光だけを"
          "教えない(何が決まるかは mv_confounding が答える)" % q2_exposure)
    print("   VIP の上位: %s / NIPALS と SIMPLS の係数の差 %.1e"
          % ([(feats[i], round(float(pls["vip"][i]), 2)) for i in order[:3]],
             float(np.abs(pls["coef"] - pls2["coef"]).max())))
    assert np.abs(pls["coef"] - pls2["coef"]).max() < 1e-8 * max(1.0, np.abs(pls["coef"]).max())
    assert pls["significant"] and rmse < 0.5 * sd and q2_exposure < pls["q2"]
    out["pls_rmse_deg"] = round(rmse, 3)

    # ---- 図 ---------------------------------------------------------------------- #
    if figs.enabled():
        names = list(me["table"])
        series, kinds, colors = [], [], []
        role = {"angle": "emphasis", "power": "neutral", "exposure": "right", "gain": "wrong"}
        for k, nm in enumerate(names):
            t = me["table"][nm]
            xs = k * 4 + np.arange(3)
            series.append((nm, xs, t["mean"]))
            kinds.append("line")
            colors.append(role[nm])
        series.append(("全体の平均", [-0.5, 4 * len(names) - 1.5], [me["grand_mean"]] * 2))
        kinds.append("line")
        colors.append("reference")
        figs.save_plot("main_effects", series, kinds=kinds, colors=colors,
                       styles=[None] * len(names) + ["dashed"],
                       xlabel="角度(0-2) / 強さ(4-6) / 露光(8-10) / ゲイン(12-14) の 3 水準", ylabel="傷の見え(平均)",
                       title="主効果 —— 角度が 8 割。強さ・露光・ゲインは同じ形(どれも明るさ)",
                       caption="L9 の 9 条件 x 3 回の撮影から、各条件の水準ごとの平均を結んだ(応答表)。寄与率 角度 %.0f%% / "
                               "強さ %.0f%% / 露光 %.0f%% / ゲイン %.0f%%。強さ・露光・ゲインの 3 本は同じ山形 —— どれも明るさを変えるだけで、"
                               "暗すぎると雑音に埋もれ、明るすぎると傷の縁が飽和する。画像から 3 つを別々には決められない"
                               "(sens_morris / mv_confounding の出番)。" % tuple(100 * shares[n] for n in names))
        figs.save_grid("rsm_maps", [truth, pred],
                       captions=["真の地図(総当たり 441 点)", "二次曲面(13 回から)"],
                       ncols=2, vrange=(float(min(truth.min(), pred.min())), float(max(truth.max(), pred.max()))),
                       title="応答曲面 —— 13 回の撮影で当てた二次曲面と、441 回の総当たり",
                       caption="横 = 照明の角度 4〜20°、縦 = 露光 6〜30 ms(上が 6 ms)、ゲイン 6 dB。露光を上げると傷は見えて"
                               "くるが、%.0f ms を越えると傷の縁が飽和して見えが落ちる(山)。角度の向きはほぼ平ら(尾根)。"
                               "中心複合計画(inscribed、範囲の内側)の 13 回で当てた曲面の最良 %.0f° %.1f ms は、総当たりの最良"
                               " %.0f° %.1f ms に対して見えの損 %.1f%%。ただし飽和の折れを二次は表せず、当てはまりの悪さが"
                               "有意(p = %.1g)—— 曲面の数字を信じる前に範囲を狭めて当て直す、という合図。"
                               % (best_true[1], *best_pred, *best_true, 100 * loss / truth.max(), lof_p if lof_p is not None else float("nan")))
        figs.save_plot("pca_scree",
                       [("特徴量の固有値", np.arange(1, len(feats) + 1), pca["eigenvalues"]),
                        ("乱数の表の固有値(平行分析)", np.arange(1, len(feats) + 1), pca["parallel_reference"])],
                       kinds=["line", "line"], styles=[None, "dashed"], colors=["emphasis", "reference"],
                       xlabel="成分の番号", ylabel="固有値(相関行列)",
                       title="特徴量 9 本の独立な情報は %d 次元" % pca["n_components"]["parallel"],
                       caption="同じ大きさの乱数の表の固有値(破線、Horn 1965)を上回る成分だけが構造。特徴量を増やしても、"
                               "条件 4 つの撮影から取れる独立な情報は条件の数を超えない。")
        figs.save_plot("pls_holdout",
                       [("学習 30 回", yexp[tr], pls["fitted"][:, 0]), ("確かめ 10 回", yexp[te], pred_te),
                        ("完全に読めたら", [15, 75], [15, 75])],
                       kinds=["scatter", "scatter", "line"], styles=[None, None, "dashed"],
                       colors=["neutral", "emphasis", "reference"], xlim=(10, 80), ylim=(10, 80),
                       xlabel="実際の照明の角度 (deg)", ylabel="画像の特徴量から読んだ角度 (deg)",
                       title="PLS —— 画像から照明の角度を読む(確かめ RMSE %.1f°)" % rmse,
                       caption="特徴量(対数)から照明の角度を PLS で読む。Q² = %.2f(7 分割の交差検証)、%d 成分。"
                               "学習に使っていない 10 回で確かめた。VIP の上位: %s。同じ特徴量で露光を読むと Q² %.2f —— "
                               "強さ・露光・ゲインは明るさを同じように変えるので、画像からは積しか決まらない。"
                               % (pls["q2"], pls["n_components"], ", ".join(feats[i] for i in order[:3]), q2_exposure))
    assert not figs.errors(), figs.errors()

    out["elapsed_s"] = round(time.perf_counter() - t0, 3)
    print("PASS  multivar_inspection_tour  (%.3f s)" % out["elapsed_s"])
    return out


if __name__ == "__main__":
    run()
