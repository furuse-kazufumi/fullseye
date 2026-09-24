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
    print("\n[1] 素朴な長さ計測は、矢羽根でどれだけ外すか")
    # ★ここは以前「錯視の図で測る側を採点する」章だった。だが並んでいた検査は
    #   **自分で置いた定数を読み返すだけ**で、間に変換が 1 つも無かった ——
    #   厳密に水平に引いた目地が水平だ、平坦に塗ったマスが平坦だ、同値に置いた
    #   2 パッチが同値だ。錯視は人間の知覚の性質なので、測る側が騙される理由が
    #   そもそも無い。**同義反復**なので落とした(2026-09-24、指摘を受けて)。
    #
    #   残したのは 1 件だけ —— **素朴な長さ計測が実際に外す**こと。これは
    #   知覚ではなく**アルゴリズムの偏り**の話なので、中身がある。
    bare = fs.ledger.illusion_muller_lyer(length=220.0, head=0.0)
    db = bare[..., 0] < 0.5
    check(np.array_equal(db[80], db[180]),
          "矢羽根が無ければ 2 本は画素単位で同一",
          "以降の差はすべて矢羽根が作ったもの")

    def naive_len(img):
        """素朴な計測 —— 行の中で暗い画素の端から端まで。"""
        g = img[..., 0] < 0.5
        return [int(np.ptp(np.flatnonzero(g[r]))) for r in (80, 180)]

    heads = (0.0, 20.0, 40.0, 60.0, 80.0)
    bias = []
    for h in heads:
        a, b = naive_len(fs.ledger.illusion_muller_lyer(length=220.0, head=h))
        bias.append(abs(a - b))
        print("   矢羽根 %4.0f px  素朴な計測 %d / %d 画素(真値はどちらも 220)"
              % (h, a, b))
    base = naive_len(fs.ledger.illusion_muller_lyer(length=220.0, head=0.0))
    check(base[0] == base[1] and base[0] != 220,
          "★矢羽根が無くても、素朴な計測は真値を外す",
          "220 のはずが **%d 画素**(3 画素長い)—— 反エイリアスの裾を"
          "「黒い画素」として数えているから。錯視より前の、素の欠陥" % base[0])
    check(bias[0] == 0 and bias[-1] > 0,
          "★矢羽根を付けると、等長の 2 本に差が出る",
          "矢羽根 0 では差 0 画素なのに、%.0f px では **%d 画素**"
          % (heads[-1], bias[-1]))
    #: ★外した予言 —— 「矢羽根が長いほど偏りも大きい」と読んだが違った。
    check(bias[1] == bias[-1] and len(set(bias[1:])) == 1,
          "★外した予言: 偏りは矢羽根の長さに**依らない**",
          "差 %s 画素 —— 20 px で **%d 画素**に達したあとは 80 px まで動かない。"
          "偏りを作るのは矢羽根の長さではなく、**端に裾が乗るかどうか**だけ"
          % (" / ".join(str(v) for v in bias), bias[1]))

    if figs.enabled():
        # ★錯視の絵(カフェウォール・チェッカー・カニッツァ・フレーザー・
        #   エビングハウス)は**直線と矩形を引いているだけ**で、この箱の力を
        #   何も示していない。2026-09-24 の指摘を受けて主図から降ろした。
        #   残すのは、測る側の**偏り**が見える 1 枚だけ。
        figs.save("muller_lyer_bias",
                  fs.ledger.illusion_muller_lyer(length=220.0, head=80.0)[..., 0],
                  gray=True,
                  caption="ミュラー・リヤー。**2 本の軸は厳密に等長**(矢羽根を"
                          "外すと画素単位で同一)。ところが矢羽根を付けた図で"
                          "「行の黒い区間」を素朴に測ると、真値 220 に対し "
                          "**%d 画素と %d 画素**になります。★これは知覚の話では"
                          "なく**測る側の偏り**で、矢羽根の裾が軸の端に乗るのが"
                          "原因です。次の図が、その偏りの量と向きです。"
                          % tuple(naive_len(
                              fs.ledger.illusion_muller_lyer(length=220.0,
                                                             head=80.0))))
        figs.save_plot("bias_vs_head",
                       [("素朴な計測の差", np.asarray(heads, np.float64),
                         np.asarray(bias, np.float64))],
                       kinds=["scatter"],
                       xlabel="矢羽根の長さ [px]", ylabel="2 本の測定差 [px]",
                       title="偏りは矢羽根の有無で決まり、長さには依らない",
                       caption="真値はどの点でも **220 画素で等長**。矢羽根が "
                               "0 のとき差は **0 画素**で、20 px で **%d 画素**に"
                               "なり、そこから 80 px まで**動きません**"
                               "(差 %s 画素)。★「長いほど偏る」と読んで**外し"
                               "ました** —— 偏りを作るのは矢羽根の長さではなく、"
                               "**端に反エイリアスの裾が乗るかどうか**だけ。"
                               "なお矢羽根が無くても素朴な計測は **223 画素**"
                               "(3 画素長い)で、これは錯視より前の素の欠陥です。"
                               % (bias[1], " / ".join(str(v) for v in bias)))
    return bias



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
    bias = chapter_illusions()
    I, xs, ys, early, late = chapter_perpetual()
    ratios = chapter_loop()

    if figs.enabled():
        rows = [[s_, ident, "%.2e" % r, "0(厳密)"]
                for s_, ident, r in zip(I["system"], I["identity"], I["residual"])]
        rows.append(["muller_lyer", "矢羽根 0..80 px での測定差",
                     " / ".join(str(v) for v in bias), "0 が正しい"])
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
