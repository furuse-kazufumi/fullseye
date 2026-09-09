# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""薄い欠陥の検出限界を決めるのは、雑音の大きさではなく地の構造。

検査の現場で「どこまで薄い傷が見えるか」を見積もるとき、いちばん普通のやり方は
**平らな地に白色雑音を載せた合成画像**で限界を測ることです。この PoC は、その
見積もりが**どれだけ甘いか**を、真値を厳密に持ったまま実写の地で測ります。

やり方は 1 つだけ: **実写の地に、位置と大きさと振幅が既知のガウシアン欠陥を仕込む**。
地は本物(scikit-image 同梱の CC0 実写テクスチャ brick / grass / gravel)、仕込む物は
閉形式なので、真値は「どこに何を置いたか」として厳密に分かります。比較相手は
**検出器が実際に見る残差の標準偏差を揃えた**合成の地 —— つまり「雑音の量」は同じに
してから、structure の効果だけを取り出します。

判定は **仕込んだ位置が検出器の応答の最大点になる最小の振幅**(= 検出限界)。
閾値を使わないので、op 側の正規化(``signed01`` など)の影響を受けません。

EXTEND: 自分のラインで使うなら :func:`grounds` の戻り値を撮影した無欠陥画像に、
:data:`DEFECT_SIGMA` を欠陥の実寸(px)に置き換えます。**無欠陥画像が要ります** ——
この PoC の主張は「地が限界を決める」なので、欠陥入りの画像しか無いと測れません。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. ★★**雑音を揃えても足りない**。検出器が見る残差 σ を実写と合成で一致させても、
   実写の地の検出限界は **2.03〜3.47 倍**高い。「平らな地に白色雑音」で出した
   見積もりは、**同じ雑音量でも 2 倍以上楽観的**になる。
2. ★**ノブを振っても消えない**。背景窓 3 通り × 欠陥の大きさ 2 通り × 地 3 種の
   **18 通り全部**で比は 1 を超える(実測 1.72〜4.56)。
   ★**外した予測**: 「欠陥が大きいほど差が開く」と思ったが、σ=1.5 と σ=3.0 の
   中央値はどちらも 3.30 倍で**差が無い**。粗い振幅の刻み(34 段)では 2 つが
   別々の格子点に丸まって差が有るように見えていた —— **刻みが作った差**だった。
3. ★**検出器を変えても残る**。整合フィルタ(背景差 + ガウシアン相関)と
   fullseye の :func:`laplace_of_gauss` という独立な 2 つで比はそれぞれ
   2.17〜3.47 倍と 2.03〜3.20 倍。**片方の癖ではない**。
4. ★★**「実写だから場所で変わる」は誤り**。場所による限界の散らばりは
   brick が 16.8 倍(σ を揃えた合成では 3.3 倍)なのに、grass 2.4 倍・
   gravel 3.3 倍は**合成の 3.3 倍と区別がつかない**。散らばりを生むのは
   「実写であること」ではなく**目地という構造**です。不変性が記述子だけでなく
   入力の性質でもあるのと同じ形。
5. ★★**ゼロ点は、物差しを 1 つにすると勝ってしまう**。背景を引かず生の画素の
   最大点を取るだけのゼロ点は、**「当てる」だけなら整合フィルタより 0.65〜0.90 倍
   良い**(整合フィルタは地の構造も一緒に増幅するので損をする)。無欠陥面での
   空振りも brick では 0 対 0 の引き分け。★★分かれるのは**照明が 2 % ずれた瞬間**で、
   ゼロ点は 1 万画素あたり 10.3 回鳴り、整合フィルタは 0.0 回のまま —— 生の画素の
   閾値は明るさの絶対値だから。**当てる力・空振り・ずれへの強さを別々に数えないと、
   役に立たない検出器を勝たせられる。**
   ★これは予測を 2 回外した末の形。最初は「ゼロ点は何も見つけない」と書こうとしたが
   振幅を上げれば当たり、次に「閾値を足せば逆転する」と思ったが**閾値は一度も
   効かなかった**(位置が最大点になった時点で必ず超えるので)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import examplefig as figs                                       # noqa: E402
import fullseye as fs                                           # noqa: E402
import realdata                                                 # noqa: E402

N = 192                      #: 切り出す一辺[px]
DEFECT_SIGMA = 2.0           #: 仕込む欠陥のガウシアン σ[px]
BG_WIN = 9                   #: 背景推定の窓[px]
TOL = 2.0                    #: 「当てた」と認める位置ずれ[px]
GROUNDS = ("brick", "grass", "gravel")
SEED = 7


# --------------------------------------------------------------------------- #
# 仕込む物と、2 つの独立した検出器
# --------------------------------------------------------------------------- #
def blob(shape, row, col, amp, sigma=DEFECT_SIGMA):
    """真値そのもの: 位置 (row, col)・振幅 amp・幅 sigma のガウシアン。"""
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    return amp * np.exp(-((yy - row) ** 2 + (xx - col) ** 2) / (2.0 * sigma ** 2))


def _matched_kernel(sigma):
    k = int(4 * sigma) | 1
    yy, xx = np.mgrid[0:k, 0:k]
    g = np.exp(-((yy - k // 2) ** 2 + (xx - k // 2) ** 2) / (2.0 * sigma ** 2))
    g -= g.mean()                        # 直流を抜く(平らな地には反応しない)
    return g / np.sqrt((g ** 2).sum())


def matched(img, bg=BG_WIN, sigma=DEFECT_SIGMA):
    """検出器 A: 背景(移動平均)を引いて、欠陥と同じ形で相関を取る。"""
    return ndi.correlate(img - ndi.uniform_filter(img, bg),
                         _matched_kernel(sigma), mode="reflect")


def log_op(img, a=0.5):
    """検出器 B: fullseye の ``laplace_of_gauss``(明るいスポットは負に出る)。"""
    return -np.asarray(fs.op.laplace_of_gauss(img, a=a), dtype=np.float64)


def raw(img, **_):
    """ゼロ点: 何も引かず、生の画素そのもの。"""
    return np.asarray(img, dtype=np.float64)


def residual_std(img, bg=BG_WIN):
    """**検出器が実際に見る**ばらつき(背景を引いた残りの σ)。"""
    return float(np.std(img - ndi.uniform_filter(img, bg)))


# --------------------------------------------------------------------------- #
# 地
# --------------------------------------------------------------------------- #
def grounds():
    """実写 3 種を [0,1] のグレーで返す(CC0、scikit-image 同梱)。"""
    return {n: realdata.sample_photo(n)[:N, :N].astype(np.float64) for n in GROUNDS}


def matched_synthetic(target_sigma, rng, bg=BG_WIN):
    """**残差 σ を実写に揃えた**白色雑音の地(比較の公平さはここで担保する)。"""
    s = 0.5 + rng.normal(0.0, 1.0, (N, N))
    return 0.5 + (s - s.mean()) * (target_sigma / residual_std(s, bg))


def positions(step=32, margin=40):
    return [(r, c) for r in range(margin, N - margin, step)
            for c in range(margin, N - margin, step)]


# --------------------------------------------------------------------------- #
# 検出限界
# --------------------------------------------------------------------------- #
def floors(ground, detector, pos, amps, sigma=DEFECT_SIGMA, tol=TOL, **kw):
    """位置ごとに「仕込んだ所が応答の最大点になる最小の振幅」を返す。

    ★閾値を使わない。閾値を置くと、op 側の per-image 正規化で答えが変わる
    (`colorize_depth` が 1 枚ずつ正規化していて GIF の尺度が壊れたのと同じ罠)。
    最大点の**位置**は単調な写像で動かないので、正規化の有無に依らない。
    """
    out = []
    for (r, c) in pos:
        got = np.inf
        for amp in amps:
            s = detector(ground + blob(ground.shape, r, c, amp, sigma), **kw)
            pr, pc = np.unravel_index(np.argmax(s), s.shape)
            if (pr - r) ** 2 + (pc - c) ** 2 <= tol ** 2:
                got = amp
                break
        out.append(got)
    return np.array(out, dtype=np.float64)


#: 振幅の刻み。★これ自体がノブ。粗いと限界が同じ格子点に丸まって、
#: 「σ が大きいほど差が開く」のような**刻みが作った差**を本物と誤読する
#: (2026-09-09、34 段では σ=1.5 と σ=3.0 の中央値がどちらも 3.20 に丸まった)。
AMPS = np.round(np.geomspace(0.005, 3.0, 60), 5)


def section_floor(real, rng):
    """節 1-3: 雑音を揃えても実写の限界は高い。検出器 2 つで確かめる。"""
    pos = positions()
    print("1) 検出限界(仕込んだ位置が応答の最大点になる最小の振幅)")
    print("   地は %d x %d、欠陥 σ=%.1f px、位置 %d 点、振幅 %d 段 %.3f〜%.1f"
          % (N, N, DEFECT_SIGMA, len(pos), len(AMPS), AMPS[0], AMPS[-1]))
    print("   合成の地は、検出器が見る残差 σ を実写に**揃えて**ある(雑音量は同じ)")
    print()
    print("   %-8s %8s | %-24s | %-24s" % ("地", "残差σ", "整合フィルタ", "fullseye laplace_of_gauss"))
    print("   %-8s %8s | %8s %8s %6s | %8s %8s %6s"
          % ("", "", "実写", "合成", "比", "実写", "合成", "比"))
    ratios, table = [], {}
    for name, g in real.items():
        rs = residual_std(g)
        syn = matched_synthetic(rs, rng)
        fr_m = float(np.median(floors(g, matched, pos, AMPS)))
        fs_m = float(np.median(floors(syn, matched, pos, AMPS)))
        fr_l = float(np.median(floors(g, log_op, pos, AMPS)))
        fs_l = float(np.median(floors(syn, log_op, pos, AMPS)))
        ratios += [fr_m / fs_m, fr_l / fs_l]
        table[name] = (rs, fr_m, fs_m, fr_l, fs_l, syn)
        print("   %-8s %8.4f | %8.4f %8.4f %5.2fx | %8.4f %8.4f %5.2fx"
              % (name, rs, fr_m, fs_m, fr_m / fs_m, fr_l, fs_l, fr_l / fs_l))
    print("\n   → 雑音の量を揃えても、実写の地の限界は %.2f〜%.2f 倍。"
          "**限界を決めているのは雑音ではない**。" % (min(ratios), max(ratios)))
    return table, ratios


def section_knobs(real, rng):
    """節 2: ノブ(背景窓・欠陥の大きさ)を振っても比は 1 を割らない。"""
    pos = positions(step=48)
    print("\n2) ノブを振る(ノブを 1 点に固定した比較は比較ではない)")
    print("   %-8s %-8s %8s %8s %8s" % ("背景窓", "欠陥σ", *GROUNDS))
    worst, best, by_sigma = np.inf, 0.0, {}
    for bg in (5, 9, 17):
        for sg in (1.5, 3.0):
            row = []
            for name, g in real.items():
                rs = residual_std(g, bg)
                syn = matched_synthetic(rs, rng, bg)
                fr = float(np.median(floors(g, matched, pos, AMPS, sigma=sg, bg=bg)))
                fy = float(np.median(floors(syn, matched, pos, AMPS, sigma=sg, bg=bg)))
                row.append(fr / fy)
            worst, best = min(worst, min(row)), max(best, max(row))
            by_sigma.setdefault(sg, []).extend(row)
            print("   %-8d %-8.1f %8.2f %8.2f %8.2f" % (bg, sg, *row))
    small, large = np.median(by_sigma[1.5]), np.median(by_sigma[3.0])
    print("   → %d 通り全部で 1 を超える(%.2f〜%.2f)。"
          % (len(by_sigma[1.5]) + len(by_sigma[3.0]), worst, best))
    print("   → 欠陥の大きさ別の中央: σ=1.5 で %.2f 倍、σ=3.0 で %.2f 倍。"
          % (small, large))
    return worst, best, small, large


def section_position(real, rng):
    """節 3: 場所による散らばりは「実写だから」ではなく「構造があるから」。"""
    pos = positions()
    print("\n3) 場所によるばらつき(最大/最小)")
    print("   %-8s %10s %10s %8s" % ("地", "実写", "合成(σ一致)", "実写/合成"))
    spread = {}
    for name, g in real.items():
        rs = residual_std(g)
        syn = matched_synthetic(rs, rng)
        fr = floors(g, matched, pos, AMPS)
        fy = floors(syn, matched, pos, AMPS)
        sr = float(fr.max() / fr.min())
        sy = float(fy.max() / fy.min())
        spread[name] = (sr, sy)
        print("   %-8s %10.1fx %10.1fx %8.2f" % (name, sr, sy, sr / sy))
    print("   → brick だけが突出(%.1f 倍 対 %.1f 倍)。grass %.1f / gravel %.1f は"
          "合成の %.1f と区別がつかない。**散らばりを生むのは目地という構造**であって、"
          "「実写であること」ではない。"
          % (spread["brick"][0], spread["brick"][1], spread["grass"][0],
             spread["gravel"][0], spread["grass"][1]))
    return spread


#: 検査中に起きる照明のずれ(ランプの劣化・絞りの個体差)。2 % は控えめな値。
LAMP_DRIFT = 0.02


def false_alarms(train, test, detector, quantile=99.99, offset=0.0, **kw):
    """**別の無欠陥画像**で決めた閾値が、無欠陥の検査画像で何回鳴るか(1 万画素あたり)。

    ★同じ画像から閾値を決めると、定義上その分位数ぶんしか超えないので**弁別を
    測れない**。現場では閾値は別のロットで決めるので、ここでも同じ素材の
    **重ならない切り出し**で決める。``offset`` は照明のずれ(全体を一律に持ち上げる)。
    """
    thr = float(np.percentile(detector(train, **kw), quantile))
    s = detector(test + offset, **kw)
    return float((s > thr).sum()) * 1e4 / s.size, thr


def section_null(real):
    """節 4: ゼロ点 —— 背景を引かず、生の画素の最大点を取る。

    ★予想を 2 回外した(2026-09-09)。まず「ゼロ点は何も見つけない」と書こうと
    したが、**振幅を上げれば当たる**(地の最大値を超えればよいだけ)。次に
    「当てる限界」で比べたら**ゼロ点のほうが低かった** —— 整合フィルタは地の
    構造も一緒に増幅するから。

    ★★ここが要点: **1 つの指標だと、役に立たない検出器が勝つ**。ゼロ点には
    「何も無い」と言う手段が無い —— 無欠陥の地でも必ずどこかを最大点として
    指す。だから「当てる(位置)」と「**弁別する(地だけで決めた閾値を超える)**」を
    別々に数える。
    """
    pos = positions(step=48)
    print("\n4) ゼロ点(背景を引かず、生の画素の最大点)—— 物差しを 2 つに分ける")
    print("   %-8s | %-17s | %-17s | %-17s"
          % ("", "当てる(位置)", "空振り(そのまま)", "空振り(照明 +%.0f%%)" % (100 * LAMP_DRIFT)))
    print("   %-8s | %8s %8s | %8s %8s | %8s %8s"
          % ("地", "ゼロ点", "整合", "ゼロ点", "整合", "ゼロ点", "整合"))
    loc, fa, drift = {}, {}, {}
    for name, g in real.items():
        held = realdata.sample_photo(name)[-N:, -N:].astype(np.float64)   # 重ならない切り出し
        l0 = float(np.median(floors(g, raw, pos, AMPS)))
        l1 = float(np.median(floors(g, matched, pos, AMPS)))
        a0, _ = false_alarms(g, held, raw)
        a1, _ = false_alarms(g, held, matched)
        d0, _ = false_alarms(g, held, raw, offset=LAMP_DRIFT)
        d1, _ = false_alarms(g, held, matched, offset=LAMP_DRIFT)
        loc[name], fa[name], drift[name] = l0 / l1, (a0, a1), (d0, d1)
        print("   %-8s | %8.4f %8.4f | %8.1f %8.1f | %8.1f %8.1f"
              % (name, l0, l1, a0, a1, d0, d1))
    print("   ★空振りの単位は 1 万画素あたり。閾値は**同じ素材の別の切り出し**で決めた"
          "(同じ画像から決めると、定義上その分位数ぶんしか超えないので弁別を測れない)。")
    print("   → ★位置だけで見るとゼロ点が %.2f〜%.2f 倍**良い** —— 整合フィルタは"
          "地の構造も一緒に増やすから。そのままの空振りも brick では %.0f 対 %.0f の"
          "引き分けで、ここまでならゼロ点は負けていない。"
          % (min(loc.values()), max(loc.values()), fa["brick"][0], fa["brick"][1]))
    print("   → ★★ところが照明が %.0f %% ずれた途端に分かれる: ゼロ点 %.0f 対 整合 %.0f"
          "(brick)。生の画素の閾値は**明るさの絶対値**なので、ランプが少し劣化した"
          "だけで全面が鳴る。整合フィルタは核の直流を抜いてあるので動かない。"
          % (100 * LAMP_DRIFT, drift["brick"][0], drift["brick"][1]))
    print("   → **1 つの数字だけを報告すれば、どちらの検出器でも勝たせられる。**"
          "当てる力・空振り・ずれへの強さは、別々に数えること。")
    return loc, fa, drift


# --------------------------------------------------------------------------- #
# 図
# --------------------------------------------------------------------------- #
def make_figures(real, table):
    """限界の振幅で仕込んだ姿を並べ、振幅を上げていく GIF を書く。"""
    tiles = []
    for name, g in real.items():
        amp = table[name][1]
        tiles.append(np.concatenate([g, g + blob(g.shape, N // 2, N // 2, amp)], axis=1))
    figs.save("defect_floor_panels", np.concatenate(tiles, axis=0),
              caption="左=地のまま、右=検出限界ちょうどの欠陥を中央に仕込んだところ"
                      "(上から brick / grass / gravel)。"
                      "限界の振幅は %s。"
                      % " / ".join("%s %.3f" % (n, table[n][1]) for n in real))
    frames, amps = [], np.round(np.geomspace(0.02, 1.2, 18), 4)
    g = real["brick"]
    syn = table["brick"][5]
    for amp in amps:
        frames.append(np.concatenate(
            [g + blob(g.shape, N // 2, N // 2, amp),
             syn + blob(syn.shape, N // 2, N // 2, amp)], axis=1))
    figs.save_gif("defect_floor_sweep", frames, fps=6,
                  caption="同じ欠陥を、振幅 %.2f から %.2f まで上げていく。"
                          "左=実写の brick、右=**残差 σ を揃えた**合成の地。"
                          "雑音の量は同じなのに、右のほうが先に見えてくる。"
                          % (amps[0], amps[-1]))
    return len(frames)


def main():
    t0 = time.perf_counter()
    rng = np.random.default_rng(SEED)
    real = grounds()
    table, ratios = section_floor(real, rng)
    worst, best, _small, _large = section_knobs(real, rng)
    spread = section_position(real, rng)
    loc, fa, drift = section_null(real)
    n = make_figures(real, table)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))

    # ---- 主張の検査(数字が動いたら、文章のほうを直すこと) ----
    assert min(ratios) > 1.0, "雑音を揃えたら差が消えた: %r" % ratios
    assert worst > 1.0, "ノブのどこかで比が 1 を割った: %.3f" % worst
    assert spread["brick"][0] > 3.0 * spread["grass"][0], \
        "brick の場所依存が突出しなくなった: %r" % spread
    assert max(loc.values()) < 1.0, "位置だけの物差しでゼロ点が負けた: %r" % loc
    assert all(d0 > d1 for d0, d1 in drift.values()),         "照明がずれてもゼロ点が空振りしなかった: %r" % drift

    print("\nPASS: 実写の地では検出限界が %.2f〜%.2f 倍高い(雑音の量は揃えてある)。"
          "ノブ 6 通り・検出器 2 つで残り、場所依存は brick(目地)だけが %.1f 倍。"
          "ゼロ点は当てるだけなら %.2f 倍良いが、照明が %.0f %% ずれると 1 万画素あたり"
          " %.0f 回空振りする(整合フィルタは %.0f 回)。GIF %d コマ。実行 %.2f 秒"
          % (min(ratios), max(ratios), spread["brick"][0],
             min(loc.values()), 100 * LAMP_DRIFT,
             drift["brick"][0], drift["brick"][1], n, time.perf_counter() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
