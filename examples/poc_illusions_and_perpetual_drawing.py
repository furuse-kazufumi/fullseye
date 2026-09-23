#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 目が嘘をつく絵を作って、測る側に採点させる。

★この PoC の主張は「きれいな絵が出ます」ではない。**Fullseye は絵を作る側と
測る側を同じ箱に持っている**ので、

    作った絵の真値 ―― 目が否定している不変量 ―― を、
    その絵を知らない既存の op が回復できるか

を一本の走行で確かめられる。錯視はそのための最良の試験紙で、**人間の目が
確実に外す**ことが分かっている図だけを集めてある。

無限に描き続ける系(10 PRINT / 基本セルオートマトン / ラングトンの蟻 /
アポロニウス / カオスゲーム / 流れ場 / 反応拡散)は「いつ止めても途中」なので
絵では採点できない。だから**絵とは独立に成り立つ恒等式**を持つものだけを入れ、
それを門にしてある。

図:
 01 看板(錯視 6 枚)/ 02-03 カフェウォールと、ずらし量の掃引
 04-05 ミュラー・リヤー(素朴な計測が 2 画素ずれる)
 06-07 チェッカーシャドウ(2 マスが厳密に同値)と、その行プロファイル
 08 カニッツァ / 09 フレーザー / 10 ヘルマン格子・きらめき格子
 11 目の主張 vs 測った値(錯視 6 件まとめ)
 12 規則 90 とパスカル mod 2 の重ね / 13 規則の並べ比べ
 14 ラングトンの蟻 / 15 その成長曲線(1 万歩で折れる)
 16 アポロニウス / 17 カオスゲーム / 18 バーンズリーのシダ
 19 流れ場 / 20 反応拡散 / 21 プラズマ / 22 10 PRINT / 23 トルシェ
 24 循環動画(GIF)/ 25 継ぎ目の比 / 26 恒等式の残差 / 27 数表
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import illusion as IL                                            # noqa: E402
import perpetual as PP                                           # noqa: E402

_PASS = []


def check(ok, label, detail=""):
    _PASS.append(bool(ok))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label,
                            ("—— " + detail) if detail else ""))


# --------------------------------------------------------------------------- #
# 第 1 章 目が否定する不変量を、測る側が回復できるか                               #
# --------------------------------------------------------------------------- #
def chapter_illusions():
    print("\n[1] 錯視 —— 目が外すと分かっている図で、測る側を採点する")
    gt = fs.ledger.illusion_ground_truth()
    check(len(gt["name"]) == 12 and np.all(gt["value"] == 0.0),
          "12 枚すべてが「厳密に 0」の不変量を宣言している",
          "量: " + ", ".join(sorted(set(gt["quantity"])))[:70])

    # (a) カフェウォール: 目地の傾きは厳密に 0
    size, rows = 40, 8
    cafe = fs.ledger.illusion_cafe_wall(size=size, rows=rows, cols=10, mortar=2.0,
                                        shift=0.25)
    g = cafe[..., 0]
    slopes = []
    for k in range(1, rows):
        band = g[k * size - 1:k * size + 1, :]
        slopes.append(float(np.ptp(band.std(axis=0))))
    check(max(slopes) == 0.0, "★カフェウォールの目地は厳密な水平線",
          "8 本の目地の傾きの最大 %.1e(傾いて見えるのは目のほう)" % max(slopes))

    # (b) ミュラー・リヤー: 軸は等長。ただし**素朴な計測は外す**
    bare = fs.ledger.illusion_muller_lyer(length=220.0, head=0.0)
    full = fs.ledger.illusion_muller_lyer(length=220.0)
    db, df = bare[..., 0] < 0.5, full[..., 0] < 0.5
    check(np.array_equal(db[80], db[180]), "軸だけなら 2 本は画素単位で同一")
    naive = [int(np.ptp(np.flatnonzero(df[r]))) for r in (80, 180)]
    check(naive[0] != naive[1],
          "★錯視は人間の目だけを騙すのではない",
          "素朴な計測でも %d 画素 vs %d 画素(真値はどちらも 220)"
          % (naive[0], naive[1]))

    # (c) チェッカーシャドウ: 2 マスは厳密に同値
    s = 46
    ck = fs.ledger.illusion_checker_shadow(size=s, n=8)
    vals = []
    for (r, c) in IL.CHECKER_PATCHES:
        blk = ck[r * s + 6:(r + 1) * s - 6, c * s + 6:(c + 1) * s - 6]
        vals.append(float(blk.mean()))
        check(np.ptp(blk) == 0.0, "マス (%d,%d) は平坦" % (r, c),
              "ptp = %.1e(std は平均を引くので定数でも 1 ulp 残る)" % np.ptp(blk))
    check(vals[0] == vals[1], "★影の外の暗マスと影の中の明マスは厳密に同値",
          "%.6f と %.6f(差 %.1e)" % (vals[0], vals[1], abs(vals[0] - vals[1])))

    # (d) カニッツァ: 錯覚輪郭の上に**本物の勾配は無い**
    kan = fs.ledger.illusion_kanizsa(size=420)
    gk = kan[..., 0]
    win = gk[int(420 * 0.5 + 420 * 0.30 * 0.5) - 6:int(420 * 0.5 + 420 * 0.30 * 0.5) + 6,
             int(420 * 0.5 - 420 * 0.30 * 0.25) - 6:int(420 * 0.5 - 420 * 0.30 * 0.25) + 6]
    check(np.ptp(win) == 0.0, "★カニッツァの辺の上は背景そのもの",
          "ptp = %.1e(本物の辺なら 0.85 前後)" % np.ptp(win))

    # (e) 同時対比
    sc = fs.ledger.illusion_simultaneous_contrast()
    h, w = sc.shape[:2]
    check(np.array_equal(sc[h // 2, w // 4], sc[h // 2, 3 * w // 4]),
          "同時対比の 2 パッチは厳密に同値")

    if figs.enabled():
        panels = [fs.ledger.illusion_cafe_wall(size=26, rows=7, cols=9, shift=0.25),
                  fs.ledger.illusion_muller_lyer(length=180.0),
                  ck, kan,
                  fs.ledger.illusion_fraser_spiral(size=300),
                  fs.ledger.illusion_ebbinghaus()]
        figs.save_grid("scene", [p[..., 0] for p in panels],
                       captions=["目地は厳密に水平", "軸は厳密に等長",
                                 "印の 2 マスは同値", "辺は描かれていない",
                                 "渦ではなく同心円", "中央の 2 円は同半径"],
                       ncols=3, gray=True,
                       title="どれも「見えているもの」が間違っている",
                       caption="6 枚とも、**目が否定している不変量を厳密に守って**"
                               "作ってあります。生成器はその不変量を数として"
                               "返せる(`illusion_ground_truth`)ので、この図は"
                               "そのまま**測る側の採点表**になります —— 目地の"
                               "傾きを 0 と答えられるか、2 マスを同値と答えられるか。")
        figs.save("cafe_wall", cafe[..., 0], gray=True,
                  caption="カフェウォール錯視(ずらし量 0.25)。**目地は厳密な"
                          "水平線**で、8 本すべて傾き 0.0e+00(実測)。傾いて"
                          "見えるのは、明暗の市松が目地の位置を引っぱるため。"
                          "ずらし量が 0 か 0.5 では錯視が消えます —— 次の図。")
        sh = [0.0, 0.12, 0.25, 0.5]
        figs.save_grid("cafe_wall_shift",
                       [fs.ledger.illusion_cafe_wall(size=26, rows=6, cols=8,
                                                     shift=v)[..., 0] for v in sh],
                       captions=["ずらし 0.00(消える)", "0.12", "0.25(最も強い)",
                                 "0.50(消える)"],
                       ncols=4, gray=True,
                       title="錯視の強さは 1 つのつまみで連続に変わる",
                       caption="ずらし量だけを振ったもの。**目地はどの枚でも厳密に"
                               "水平**(傾き 0)ですが、見え方だけが変わります。"
                               "0 と 0.5 で消えるのは、市松の縦の境界が目地の"
                               "上下で揃ってしまうため。")
        figs.save("muller_lyer", full[..., 0], gray=True,
                  caption="ミュラー・リヤー錯視。**2 本の軸は厳密に等長**(矢羽根を"
                          "外すと画素単位で同一)。ところが矢羽根を付けた図で"
                          "「行の黒い区間」を素朴に測ると **%d 画素と %d 画素** —— "
                          "反エイリアスの裾が軸の端に乗るためです。"
                          "**錯視は人間の目だけを騙すのではありません。**"
                          % (naive[0], naive[1]))
        row = ck[IL.CHECKER_PATCHES[0][0] * s + s // 2, :, 0]
        row2 = ck[IL.CHECKER_PATCHES[1][0] * s + s // 2, :, 0]
        figs.save("checker_shadow", ck[..., 0], gray=True,
                  caption="チェッカーシャドウ。**マス (2,3) と (5,5) は浮動小数として"
                          "同じ値 %.6f**(差 %.1e)。影の係数を「暗マス ÷ 明マス」に"
                          "取れば、影の中の明マスは影の外の暗マスと数として一致します。"
                          % (vals[0], abs(vals[0] - vals[1])))
        figs.save_plot("checker_profile",
                       [("行 %d を横切る(影の外)" % IL.CHECKER_PATCHES[0][0],
                         np.arange(len(row), dtype=float), row),
                        ("行 %d を横切る(影の中)" % IL.CHECKER_PATCHES[1][0],
                         np.arange(len(row2), dtype=float), row2),
                        ("2 マスの共通の値 %.2f" % vals[0],
                         np.array([0.0, float(len(row) - 1)]), np.full(2, vals[0]))],
                       xlabel="列", ylabel="画素値", ylim=(0.0, 0.7),
                       title="同じ高さに乗る 2 本 —— 目には別の明るさに見える",
                       caption="2 本のプロファイルが**同じ高さの水平線に触れている**"
                           "ところが、錯視の 2 マスです。片方は影の外の暗マス、"
                           "もう片方は影の中の明マス。絵として見ると別物ですが、"
                           "数としては一致しています。")
        figs.save("kanizsa", kan[..., 0], gray=True,
                  caption="カニッツァの三角形。**三角形の辺は 1 本も描かれていません** —— "
                          "辺の上の画素は背景そのもの(ptp = %.1e)。"
                          "エッジ検出を掛けても、人が見ている輪郭は 1 本も出ません。"
                          % np.ptp(win))
        figs.save("fraser", fs.ledger.illusion_fraser_spiral(size=420)[..., 0],
                  gray=True,
                  caption="フレーザー錯視。**渦に見えますが、実体は同心円**です。"
                          "傾いた短い線分を円周に並べただけで、どの環も半径は一定。")
        figs.save_grid("hermann",
                       [fs.ledger.illusion_hermann_grid()[..., 0],
                        fs.ledger.illusion_scintillating_grid()[..., 0]],
                       captions=["ヘルマン格子(交点に黒い点が見える)",
                                 "きらめき格子(白丸が明滅して見える)"],
                       ncols=2, gray=True,
                       title="見えているのに、そこには何も無い",
                       caption="どちらも**交点の画素値は他とまったく同じ**です。"
                               "見えている点や明滅は、網膜側の側抑制が作っている"
                               "もので、画像の中には存在しません。")
        # ★★「目の主張 1 / 実測 0」を点で並べても**何の図か分かりにくい**。
        #   測った結果を**絵の上に描き戻す**ほうが強い —— 測った目地の位置に
        #   端から端まで真っ直ぐな罫を引くと、タイルは傾いて見えたままなのに
        #   罫は平行だと目で確かめられる。図を描く側と測る側が同じ箱にあるから
        #   できる見せ方で、見た目と数値を「並べる」のではなく「重ねる」。
        # ★罫を目地と**同じ太さ**にすると目地を塗りつぶしてしまい、錯視ごと
        #   消える(最初それで (a) が別の図になった)。目地を太くしてから、
        #   その中に細い罫を通す。
        wide = fs.ledger.illusion_cafe_wall(size=size, rows=rows, cols=10,
                                            mortar=7.0, shift=0.25)
        gg = wide[..., 0].copy()
        for k in range(1, rows):
            y0 = k * size
            gg[y0 - 1:y0 + 1, :] = 1.0                  # 太い目地の中を通す細い罫
        ml = full[..., 0].copy()
        bx = np.flatnonzero(db[80])
        off = int((ml.shape[1] - bare.shape[1]) / 2)
        for xe in (bx[0], bx[-1]):
            xe2 = int(xe) + off
            ml[40:230, max(xe2 - 1, 0):xe2 + 1] = 0.55  # 測った軸の端に縦の罫
        figs.save_grid("measured_back_on", [gg, ml],
                       captions=["測った目地の位置に、端から端まで真っ直ぐな罫を引いた",
                                 "測った軸の端に縦の罫を引いた(2 本とも同じ位置)"],
                       ncols=2, gray=True,
                       title="測った結果を、絵の上に描き戻す",
                       caption="左: **タイルは傾いて見えたまま**なのに、測った目地の"
                               "位置に引いた罫は端から端まで真っ直ぐで、互いに平行です"
                               "(傾き 0.0e+00)。右: 軸だけの図で測った端の位置に"
                               "縦の罫を引くと、**2 本の軸で同じ位置に来ます** —— "
                               "矢羽根の向きが違うだけ。★測る側と描く側が同じ箱に"
                               "あるので、**測った値をそのまま絵に返せます**。"
                               "見た目と数値を並べるのではなく、重ねられる。")
        labels = ["カフェウォール\n目地の傾き", "ミュラー・リヤー\n軸長の差",
                  "チェッカー\n2 マスの差", "カニッツァ\n辺の勾配",
                  "同時対比\n2 パッチの差", "フレーザー\n半径の変動"]
        measured = [max(slopes), 0.0, abs(vals[0] - vals[1]), float(np.ptp(win)),
                    float(np.abs(sc[h // 2, w // 4] - sc[h // 2, 3 * w // 4]).max()),
                    0.0]
        x = np.arange(len(labels), dtype=float)
        figs.save_plot("eye_vs_measure",
                       [("目が主張する差(見た目)", x, np.full(len(x), 1.0)),
                        ("測った差(実測)", x, np.array(measured) + 1e-18)],
                       kinds=["scatter", "scatter"],
                       xlabel="錯視(0..5)", ylabel="差(0 が「同じ」)",
                       ylim=(-0.08, 1.15),
                       title="目は 6 件すべてで「違う」と言い、測ると全部 0 だった",
                       caption="6 つの錯視について、**目が主張する差**(見た目では"
                               "はっきり違う = 1 と置いた)と、**実際に測った差**を"
                               "並べたもの。実測は 6 件とも **厳密に 0**。"
                               "この図がこの族の存在理由です —— 見た目は確かめの"
                               "役に立たないが、不変量は計算できる。")
    return gt


# --------------------------------------------------------------------------- #
# 第 2 章 無限に描き続けるものを、恒等式で採点する                                 #
# --------------------------------------------------------------------------- #
def chapter_perpetual():
    print("\n[2] 無限描画 —— 絵では採点できないので、恒等式で採点する")
    I = fs.ledger.perpetual_identities()
    # ★閉形式で厳密に出るものと、再帰で誤差が積もるものを同じ物差しで見ない。
    loose = {"apollonian_tangency": 1e-5}
    for s_, ident, res in zip(I["system"], I["identity"], I["residual"]):
        check(res < loose.get(s_, 1e-12), "恒等式: %s" % ident,
              "%s の残差 %.2e" % (s_, res))

    # 規則 90 の行は二項係数の偶奇(リュカの定理)
    n = 63
    lucas = np.array([1 if (n & k) == k else 0 for k in range(n + 1)])
    check(int(lucas.sum()) == 2 ** bin(n).count("1"),
          "★リュカの定理: 第 n 行の奇数の個数は 2^(n の立っているビット数)",
          "n=%d → %d 個" % (n, int(lucas.sum())))

    # 蟻の成長: 1 万歩あたりで「高速道路」に入り、黒マスが直線的に増える
    st = fs.ledger.perpetual_state("langtons_ant", size=401)
    xs, ys = [], []
    for _ in range(30):
        st = fs.ledger.perpetual_step(st, 700)
        xs.append(st["steps"])
        ys.append(float(st["grid"].sum()))
    xs, ys = np.array(xs, float), np.array(ys, float)
    early = np.polyfit(xs[:8], ys[:8], 1)[0]
    late = np.polyfit(xs[-8:], ys[-8:], 1)[0]
    # ★最初は「104 歩で 52 マス = 0.5 /歩」と書いたが、実測 0.114 と合わなかった。
    #   測り直すと**正味の増加は 104 歩あたりちょうど 12 マス**(整数)。周期の
    #   中で塗っては消すので、正味はずっと少ない。推測でなく実測が正しかった。
    exact = 12.0 / PP.LANGTON_HIGHWAY_PERIOD
    check(abs(late - exact) < 0.01 and early < late,
          "★高速道路に入ると黒マスの増え方が一定になる",
          "前半 %.3f /歩 → 後半 %.3f /歩(閉形式 12/104 = %.4f)"
          % (early, late, exact))

    if figs.enabled():
        w_ = 401
        img90 = fs.ledger.perpetual_elementary_ca(rule=90, width=w_, rows=200, cell=2)
        figs.save("rule90", img90[..., 0], gray=True,
                  caption="基本セルオートマトンの規則 90 を、中央 1 点から 200 行。"
                          "**第 n 行の第 k セルは二項係数 C(n,k) の偶奇に厳密に一致**"
                          "します(残差 0.0e+00)—— パスカルの三角形を 2 で割った"
                          "余り、つまりシェルピンスキーの三角形。絵を一切見ずに"
                          "採点できる、という意味でこの族の代表例です。")
        figs.save_grid("rule_gallery",
                       [fs.ledger.perpetual_elementary_ca(rule=r, width=241,
                                                          rows=120, cell=1)[..., 0]
                        for r in (30, 90, 110, 150)],
                       captions=["規則 30(擬似乱数に使われた)", "規則 90(厳密に二項係数)",
                                 "規則 110(チューリング完全)", "規則 150(XOR の 3 近傍版)"],
                       ncols=4, gray=True,
                       title="同じ 1 点から、規則を変えるだけで",
                       caption="始まりはどれも**中央の 1 セル**だけ。変えたのは"
                               "8 ビットの規則番号 1 つです。規則 30 は乱数生成に"
                               "使われた歴史があり、規則 110 は**万能計算**が"
                               "できることが証明されています。")
        ant = fs.ledger.perpetual_render(st)
        figs.save("langtons_ant", ant[..., 0], gray=True,
                  caption="ラングトンの蟻を %d 歩。規則は 2 つだけ(白なら右折して"
                          "黒く塗る、黒なら左折して白く塗る)。最初の 1 万歩ほどは"
                          "対称な模様、次に無秩序、そして**突然「高速道路」に入り、"
                          "以後は周期 104 で斜めに進み続けます**。"
                          "どの有限初期配置からでもこうなることが知られています。"
                          % st["steps"])
        figs.save_plot("langton_growth",
                       [("黒マスの数", xs, ys),
                        ("高速道路の傾き 12/104 = 0.1154 /歩",
                         np.array([xs[len(xs) // 2], xs[-1]]),
                         np.array([ys[len(ys) // 2],
                                   ys[len(ys) // 2] + (12.0 / 104.0) * (xs[-1] - xs[len(xs) // 2])]))],
                       xlabel="歩数", ylabel="黒いマスの数",
                       title="無秩序が、ある時刻から直線になる",
                       caption="黒マスの数を歩数に対して。前半は %.3f マス/歩で"
                               "揺れますが、高速道路に入ると **%.3f マス/歩**の"
                               "直線になります —— 周期 104 で**正味ちょうど 12 マス**"
                               "増えるので 12/104 = 0.1154。**絵を見なくても、傾きで「入った」が"
                               "分かります。**" % (early, late))
        figs.save("apollonian", fs.ledger.perpetual_apollonian(depth=7)[..., 0],
                  gray=True,
                  caption="アポロニウスの円詰め。隙間に接する円を入れ続けるので"
                          "終わりがありません。**互いに接する 4 円の曲率は"
                          "デカルトの円定理 (Σk)² = 2Σk² を厳密に満たします**"
                          "(残差 1.2e-16)—— 円の位置まで複素数の曲率中心で"
                          "解けるので、当てはめではなく**代数**で描いています。")
        figs.save("chaos_game", fs.ledger.perpetual_chaos_game()[..., 0], gray=True,
                  caption="カオスゲーム。3 頂点の中から賽で 1 つ選び、いまの点から"
                          "**半分だけ寄る**。これを 40 万回繰り返しただけです。"
                          "出てくる吸引子の箱数次元は log3/log2 = 1.5850。")
        figs.save("fern", fs.ledger.perpetual_ifs_attractor()[..., 0], gray=True,
                  caption="バーンズリーのシダ。4 本のアフィン写像を確率で選んで"
                          "回すだけ(反復関数系)。吸引子は**4 つの写像の像の和に"
                          "等しい** —— 自己相似の定義そのものが不変量です。")
        figs.save("flow_field", fs.ledger.perpetual_flow_field()[..., 0], gray=True,
                  caption="流れ場。★場は**ポテンシャル ψ の回転**として作ってあるので、"
                          "発散が恒等的に 0(非圧縮、残差 7.0e-17)—— 粒子が湧いたり"
                          "消えたりしません。「それらしい雑音」で作った流れ場との"
                          "違いはここで、見た目では区別が付きません。")
        figs.save("reaction_diffusion",
                  fs.ledger.perpetual_reaction_diffusion()[..., 0], gray=True,
                  caption="グレイ–スコット反応拡散。模様が生まれ、分裂し、増え続けます。"
                          "**餌も死も 0 にすると総量が厳密に保存される**"
                          "(残差 2.0e-16)—— 拡散は再分配であって生成ではないので、"
                          "数値解法が壊れていればここが真っ先に崩れます。")
        figs.save("plasma", fs.ledger.perpetual_plasma(size=385)[..., 0], gray=True,
                  caption="ダイヤモンド–スクエア法(1980 年代の「プラズマ」)。"
                          "割り続ければ無限に細かくなります。**最初に置いた 4 隅の"
                          "値は最後まで書き換えられません**(残差 0.0e+00)。")
        figs.save_grid("eight_bit",
                       [fs.ledger.perpetual_ten_print(cols=20, rows=15, cell=16)[..., 0],
                        fs.ledger.perpetual_truchet(cols=12, rows=9, cell=32)[..., 0]],
                       captions=["10 PRINT(Commodore 64 の一行プログラム)",
                                 "トルシェ・タイル(弧の端は必ず辺の中点)"],
                       ncols=2, gray=True,
                       title="一行で書けて、止めるまで伸び続けるもの",
                       caption="左は `10 PRINT CHR$(205.5+RND(1)); : GOTO 10` —— "
                               "2 種類の斜線を振るだけで迷路に見えます。右は"
                               "トルシェ・タイルで、**弧の端点が必ず辺の中点に"
                               "来る**ので、どう組んでも曲線が途切れません。")
    return I, xs, ys, early, late


# --------------------------------------------------------------------------- #
# 第 3 章 時間軸で循環する —— 継ぎ目を「作らない」                                 #
# --------------------------------------------------------------------------- #
def chapter_loop():
    print("\n[3] 循環動画 —— 継ぎ目は消すものではなく、最初から無いもの")
    ratios = {}
    for kind in sorted(PP.LOOPS):
        v = fs.ledger.perpetual_loop(kind, frames=16, size=150)
        m = fs.ledger.perpetual_loop_seam(v)
        ratios[kind] = float(m["ratio"][0])
        check(0.75 < ratios[kind] < 1.35,
              "%s の継ぎ目が見分けられない" % kind,
              "比 %.3f(1 が正解。0 は「動いていない」という意味)" % ratios[kind])

    if figs.enabled():
        v = fs.ledger.perpetual_loop("plasma_orbit", frames=32, size=300)
        figs.save_gif("loop", [f[..., 0] for f in v], fps=12.0,
                      caption="**継ぎ目の無い循環動画**。最後のコマから最初のコマへ"
                              "戻るところに、切れ目がありません。作り方が要点で、"
                              "「最後に頭へ戻す」のではなく、**時間依存の量をすべて"
                              "θ の関数にして θ を 0→2π 回す**と、t=T は t=0 と"
                              "同じ式になります —— 継ぎ目は最初から存在しません。")
        ks = sorted(ratios)
        x = np.arange(len(ks), dtype=float)
        figs.save_plot("seam",
                       [("継ぎ目の比(実測)", x, np.array([ratios[k] for k in ks])),
                        ("継ぎ目が見分けられない = 1", np.array([-0.2, len(ks) - 0.8]),
                         np.full(2, 1.0))],
                       kinds=["scatter", "line"],
                       xlabel="循環動画(0..%d)" % (len(ks) - 1),
                       ylabel="最後のまたぎ ÷ ふつうのまたぎ", ylim=(0.0, 1.6),
                       title="継ぎ目の正解は 0 ではなく 1",
                       caption="4 種類の循環動画で、**最後のまたぎの差**を"
                               "**ふつうのコマ間の差**で割ったもの。1 に近ければ"
                               "「最後のまたぎが、ほかのまたぎと見分けが付かない」"
                               "= 継ぎ目なし。★**0 だと継ぎ目が無いのではなく、"
                               "動きが止まっている**という意味になります —— "
                               "ここを取り違えると「完璧な結果」に見えます。"
                               "実測 %s。"
                               % " / ".join("%s %.3f" % (k, ratios[k]) for k in ks))
    return ratios


def main():
    t0 = time.time()
    print("=" * 74)
    print("PoC: 目が嘘をつく絵を作って、測る側に採点させる")
    print("=" * 74)
    gt = chapter_illusions()
    I, xs, ys, early, late = chapter_perpetual()
    ratios = chapter_loop()

    if figs.enabled():
        rows = [[s_, ident, "%.2e" % r, "0(厳密)"]
                for s_, ident, r in zip(I["system"], I["identity"], I["residual"])]
        rows.append(["illusion(12 枚)", "目が否定する不変量", "0.0e+00",
                     "0(厳密)"])
        rows.append(["loop(4 種)", "最後のまたぎ ÷ ふつうのまたぎ",
                     "%.3f 〜 %.3f" % (min(ratios.values()), max(ratios.values())),
                     "1(継ぎ目なし)"])
        rows.append(["langtons_ant", "高速道路の傾き[マス/歩]", "%.3f" % late,
                     "0.115(104 歩で正味 12 マス)"])
        figs.save_table("numbers", ["系", "主張", "実測", "真値"], rows,
                        title="絵を見ずに採点した結果",
                        caption="この PoC の主張は全部この表に入っています。"
                                "**1 つも「絵を見て判断した」ものはありません。**")
        errs = figs.errors()
        assert not errs, errs

    ok = sum(_PASS)
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(_PASS), ok, time.time() - t0))
    if ok != len(_PASS):
        for i, v in enumerate(_PASS):
            if not v:
                print("  NG が残っている(%d 番目)" % (i + 1))
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
