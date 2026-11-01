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
空振り(無欠陥の面で鳴る回数)は**別の物差し**として、同じ素材の重ならない
切り出しで決めた閾値で数えます —— 同じ画像から閾値を決めると、定義上その
分位数ぶんしか超えないので弁別を測れません。

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

import os
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
GAP = 10          #: 左右・上下の仕切り[px]
ZOOM_R = 16       #: 拡大して差し込む正方形の半辺[px]


def _pair_rgb(left, right):
    """2 枚を仕切りつきで横に並べ、**固定の尺度**で疑似カラーにする。

    ★``colorize_depth`` は既定で 1 枚ずつ正規化する。``vmin``/``vmax`` を渡さないと、
    コマごとに明るさが動いて「振幅を上げると見えてくる」という主張そのものが壊れる。
    """
    pair = np.concatenate([np.clip(left, 0.0, 1.0), np.zeros((N, GAP)),
                           np.clip(right, 0.0, 1.0)], axis=1)
    return np.asarray(fs.colorize_depth(pair, vmin=0.0, vmax=1.0),
                      dtype=np.float64)[..., :3]


SHOWCASE_SIZE = (1280, 720)
SHOWCASE_POS = (104, 72)       #: table の中央値と閾値交差が同じ格子に乗る代表位置
SHOWCASE_AMPS = np.round(np.geomspace(0.02, 1.2, 36), 4)


def _showcase_font(size=22, bold=False):
    """日本語を 22 px 以上で描くフォントを fail-closed で選ぶ。"""
    from PIL import ImageFont

    names = ([r"C:\Windows\Fonts\YuGothB.ttc", r"C:\Windows\Fonts\meiryob.ttc"]
             if bold else
             [r"C:\Windows\Fonts\YuGothM.ttc", r"C:\Windows\Fonts\meiryo.ttc",
              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"])
    for name in names:
        if Path(name).is_file():
            return ImageFont.truetype(name, size)
    raise RuntimeError("showcase 用の日本語フォントが見つからない")


def _showcase_text(draw, xy, text, box, *, size=22, fill=(238, 242, 246), bold=False):
    """描画前に文字幅を測り、指定余白から 1 px でもはみ出せば止める。"""
    font = _showcase_font(size, bold)
    x, y = xy
    bb = draw.multiline_textbbox((x, y), text, font=font, spacing=4)
    bx0, by0, bx1, by1 = box
    assert bb[0] >= bx0 and bb[1] >= by0 and bb[2] <= bx1 and bb[3] <= by1, \
        (text, bb, box)
    draw.multiline_text((x, y), text, font=font, fill=fill, spacing=4)


def _showcase_rgb(a, vmin, vmax):
    x = np.asarray(fs.colorize_depth(a, vmin=float(vmin), vmax=float(vmax)))[..., :3]
    return np.rint(255 * np.clip(x, 0.0, 1.0)).astype(np.uint8)


def _showcase_local_peak(response, pos=SHOWCASE_POS, radius=3):
    """仕込んだ中心から 3 px 内の応答最大値と座標。"""
    r, c = pos
    yy, xx = np.mgrid[:response.shape[0], :response.shape[1]]
    mask = (yy - r) ** 2 + (xx - c) ** 2 <= radius ** 2
    flat = np.where(mask, response, -np.inf)
    pr, pc = np.unravel_index(np.argmax(flat), response.shape)
    assert (pr - r) ** 2 + (pc - c) ** 2 <= 3 ** 2, (pos, (pr, pc))
    return float(response[pr, pc]), (int(pr), int(pc))


def _showcase_audit(frames, name):
    """依頼時だけ、先頭・中間・末尾と 12 コマの接触印画を書く。"""
    root = os.environ.get("FULLSEYE_AUDIT_DIR", "").strip()
    if not root:
        return
    from PIL import Image

    out = Path(root) / name
    out.mkdir(parents=True, exist_ok=True)
    for fn, i in (("f000.png", 0), ("f_mid.png", len(frames) // 2),
                  ("f_end.png", len(frames) - 1)):
        Image.fromarray(frames[i]).save(out / fn)
    ids = np.linspace(0, len(frames) - 1, 12).round().astype(int)
    sheet = Image.new("RGB", (1280, 540), (10, 15, 22))
    for n, i in enumerate(ids):
        thumb = Image.fromarray(frames[i]).resize((320, 180), Image.Resampling.LANCZOS)
        sheet.paste(thumb, ((n % 4) * 320, (n // 4) * 180))
    sheet.save(out / "contact.png")


def make_defect_floor_explained(real, table):
    """検出器の応答・偽警報閾値・限界を 1 画面で結ぶ 36 コマ。"""
    from PIL import Image, ImageDraw

    g, syn = real["brick"], table["brick"][5]
    r0, c0 = SHOWCASE_POS
    grounds_ = (g, syn)
    names = ("brick", "合成")
    colors = ((238, 139, 71), (64, 164, 223))
    thresholds = tuple(float(np.percentile(matched(a), 99.99)) for a in grounds_)

    # 応答の疑似カラーは全コマ・両地で 1 つの尺度に固定する。
    responses = [[matched(a + blob(a.shape, r0, c0, amp))
                  for amp in SHOWCASE_AMPS] for a in grounds_]
    response_lo = min(float(x.min()) for seq in responses for x in seq)
    response_hi = max(float(x.max()) for seq in responses for x in seq)
    scores = [[_showcase_local_peak(x)[0] for x in seq] for seq in responses]

    # 表の限界は 16 位置の中央値なので、代表位置の閾値交差とは最大 1 格子だけ許す。
    limit_grid = []
    table_limits = (float(table["brick"][1]), float(table["brick"][2]))
    for a, thr, tab in zip(grounds_, thresholds, table_limits):
        vals = []
        for amp in AMPS:
            vals.append(_showcase_local_peak(matched(a + blob(a.shape, r0, c0, amp)))[0])
        lim = next(float(amp) for amp, val in zip(AMPS, vals) if val > thr)
        j = int(np.argmin(np.abs(AMPS - tab)))
        one_step = max(tab - AMPS[max(0, j - 1)], AMPS[min(len(AMPS) - 1, j + 1)] - tab)
        assert abs(lim - tab) <= one_step + 1e-12, (lim, tab, one_step)
        limit_grid.append(lim)

    # 残差 σ は同じ実行の地から計算し、揃っていることも数値で押さえる。
    sigmas = (residual_std(g), residual_std(syn))
    assert abs(sigmas[0] - sigmas[1]) < 1e-12, sigmas

    def line(draw, pts, fill, width=2):
        if len(pts) >= 2:
            draw.line(pts, fill=fill, width=width, joint="curve")

    frames = []
    for k, amp in enumerate(SHOWCASE_AMPS):
        im = Image.new("RGB", SHOWCASE_SIZE, (10, 15, 22))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 1279, 55), fill=(25, 35, 48))
        d.rectangle((0, 690, 1279, 719), fill=(25, 35, 48))
        _showcase_text(d, (18, 10),
                       "薄い傷はどこで見えなくなるか —— 実写の地(brick)と雑音を揃えた合成の地",
                       (0, 0, 1010, 56), size=25, bold=True)
        _showcase_text(d, (1060, 12), "振幅 %.3f(%d/36)" % (amp, k + 1),
                       (1040, 0, 1276, 56), size=22)

        panel_x = (20, 335, 650, 965)
        titles = ("実写 brick + 欠陥", "その検出器応答", "合成の地 + 欠陥", "その検出器応答")
        panel_arrays = (g + blob(g.shape, r0, c0, amp), responses[0][k],
                        syn + blob(syn.shape, r0, c0, amp), responses[1][k])
        peak_positions = {}
        for p, (x, title, a) in enumerate(zip(panel_x, titles, panel_arrays)):
            d.rectangle((x, 70, x + 299, 369), fill=(18, 25, 34), outline=(83, 96, 111))
            _showcase_text(d, (x + 8, 71), title, (x, 70, x + 300, 96), size=22, bold=True)
            rgb = (_showcase_rgb(a, 0.0, 1.0) if p in (0, 2)
                   else _showcase_rgb(a, response_lo, response_hi))
            pane = Image.fromarray(rgb).resize((274, 274), Image.Resampling.BILINEAR)
            im.paste(pane, (x + 13, 96))
            if p in (0, 2):
                crop = Image.fromarray(rgb).crop((c0 - 16, r0 - 16, c0 + 16, r0 + 16))
                inset = crop.resize((64, 64), Image.Resampling.NEAREST)
                im.paste(inset, (x + 222, 305))
                d.rectangle((x + 221, 304, x + 286, 369), outline=(255, 255, 255), width=2)
                _showcase_text(d, (x + 86, 371), "拡大 2×", (x, 370, x + 300, 400), size=22)
            else:
                gi = 0 if p == 1 else 1
                val, (pr, pc) = _showcase_local_peak(a)
                peak_positions[gi] = (pr, pc)
                px = x + 13 + (pc + 0.5) * 274 / N
                py = 96 + (pr + 0.5) * 274 / N
                d.ellipse((px - 10, py - 10, px + 10, py + 10), outline=(255, 255, 255), width=3)
                _showcase_text(d, (x + 55, 371), "応答 %.3f" % val,
                               (x, 370, x + 300, 400), size=22)
        assert all((p[0] - r0) ** 2 + (p[1] - c0) ** 2 <= 3 ** 2
                   for p in peak_positions.values()), peak_positions

        # 左下: 対数振幅に対する応答。文字は上・左・下の余白だけに置く。
        d.rectangle((20, 400, 879, 679), fill=(18, 25, 34), outline=(83, 96, 111))
        _showcase_text(d, (92, 402), "限界 brick %.3f" % table_limits[0],
                       (20, 400, 410, 430), size=22, fill=colors[0], bold=True)
        _showcase_text(d, (438, 402), "限界 合成 %.3f" % table_limits[1],
                       (410, 400, 780, 430), size=22, fill=colors[1], bold=True)
        x0, y0, x1, y1 = 104, 438, 855, 632
        d.line((x0, y1, x1, y1), fill=(185, 195, 207), width=2)
        d.line((x0, y0, x0, y1), fill=(185, 195, 207), width=2)
        ymin = min(min(v) for v in scores + [list(thresholds)])
        ymax = max(max(v) for v in scores + [list(thresholds)])
        pad = 0.08 * (ymax - ymin)
        ymin, ymax = ymin - pad, ymax + pad
        xp = lambda a: x0 + (np.log(a) - np.log(.02)) / (np.log(1.2) - np.log(.02)) * (x1 - x0)
        yp = lambda v: y1 - (v - ymin) / (ymax - ymin) * (y1 - y0)
        for tick in (.02, .05, .1, .2, .5, 1.2):
            xx = xp(tick)
            d.line((xx, y1, xx, y1 + 5), fill=(185, 195, 207), width=2)
            _showcase_text(d, (xx - 18, y1 + 7), "%g" % tick,
                           (20, y1, 880, 662), size=22)
        _showcase_text(d, (390, 651), "振幅(対数)", (20, 646, 880, 680), size=22)
        ylabel = Image.new("RGBA", (132, 30), (0, 0, 0, 0))
        yd = ImageDraw.Draw(ylabel)
        _showcase_text(yd, (0, 0), "検出器応答", (0, 0, 132, 30), size=22)
        ylabel = ylabel.rotate(90, expand=True)
        im.paste(ylabel, (28, 469), ylabel)
        for gi, color in enumerate(colors):
            pale = tuple((v + 80) // 2 for v in color)
            pts = [(xp(a), yp(v)) for a, v in zip(SHOWCASE_AMPS, scores[gi])]
            line(d, pts, pale, 2)
            line(d, pts[:k + 1], color, 4)
            yy = yp(thresholds[gi])
            for xx in np.arange(x0, x1, 12):
                d.line((xx, yy, min(xx + 6, x1), yy), fill=color, width=2)
            xx = xp(table_limits[gi])
            for yy0 in np.arange(y0, y1, 12):
                d.line((xx, yy0, xx, min(yy0 + 6, y1)), fill=color, width=2)
            d.ellipse((xp(amp) - 7, yp(scores[gi][k]) - 7,
                       xp(amp) + 7, yp(scores[gi][k]) + 7), fill=color, outline=(255, 255, 255), width=2)

        # 右下: このコマの判定は応答と閾値の比較から作る。
        d.rectangle((900, 400, 1259, 679), fill=(25, 35, 48), outline=(83, 96, 111))
        verdicts = ["見える" if scores[i][k] > thresholds[i] else "見えない" for i in range(2)]
        card = ["振幅 %.3f" % amp,
                "brick: 応答 %.2f / 閾値 %.2f" % (scores[0][k], thresholds[0]),
                "  → %s" % verdicts[0],
                "合成: 応答 %.2f / 閾値 %.2f" % (scores[1][k], thresholds[1]),
                "  → %s" % verdicts[1],
                "残差 σ: brick %.3f = 合成 %.3f" % sigmas]
        for i, text in enumerate(card):
            _showcase_text(d, (916, 414 + 40 * i), text, (900, 400, 1260, 680),
                           size=22, bold=(i == 0))

        _showcase_text(d, (8, 692),
                       "Fullseye: matched filter(matched)→無欠陥の地の99.99 %分位を閾値に。雑音量が同じでも地の構造(目地)が応答を押し下げる。",
                       (0, 690, 1280, 720), size=22)
        frames.append(np.asarray(im))

    caption = ("同じ欠陥を実写 brick と残差 σ を揃えた合成の地へ仕込み、整合フィルタの応答が 99.99 %% 閾値を越えるまでを示す。"
               "検出限界は brick %.3f、合成 %.3f、閾値は %.3f / %.3f。"
               % (table_limits[0], table_limits[1], thresholds[0], thresholds[1]))
    figs.save_video("defect_floor_explained", frames, fps=6.0, gif_every=1,
                    caption=caption)
    _showcase_audit(frames, "poc_real_defect_floor")
    return len(frames), {"limits": table_limits, "thresholds": thresholds,
                         "sigmas": sigmas}


def make_figures(real, table):
    """限界の振幅で仕込んだ姿を並べ、振幅を上げていく GIF を書く。

    ★最初の版は地と欠陥をただ並べただけで、**仕込んだ欠陥がどこにあるか読み手に
    分からなかった**(2026-09-09、書いたあと自分で開いて気づいた)。限界ちょうどの
    欠陥は「言われれば見える」大きさなので、**位置を示して拡大しないと図が主張を
    運ばない**。素材名と限界値は背景板つきの凡例に、地と欠陥の同じ場所は 2 倍に
    拡大して隅へ差し込む(``annotate_inset`` は最近傍の整数倍 = 元の画素のまま)。
    """
    cx = cy = N // 2
    rows = []
    for name, g in real.items():
        amp = table[name][1]
        rgb = _pair_rgb(g, g + blob(g.shape, cx, cy, amp))
        rgb = np.asarray(fs.annotate_inset(rgb, (cx - ZOOM_R, cy - ZOOM_R,
                                                 2 * ZOOM_R, 2 * ZOOM_R),
                                           corner="lb", factor=2, label="地"),
                         dtype=np.float64)
        rgb = np.asarray(fs.annotate_inset(rgb, (N + GAP + cx - ZOOM_R, cy - ZOOM_R,
                                                 2 * ZOOM_R, 2 * ZOOM_R),
                                           corner="rb", factor=2, label="欠陥"),
                         dtype=np.float64)
        rgb = np.asarray(fs.annotate_legend(
            rgb, ["%s: 左=地のまま / 右=限界 %.3f の欠陥" % (name, amp)],
            (6, 6), anchor="lt", font_size=11, radius=5.0), dtype=np.float64)
        rows += [rgb, np.ones((GAP, rgb.shape[1], 3))]
    figs.save("defect_floor_panels", np.concatenate(rows[:-1], axis=0),
              caption="左=地のまま、右=**検出限界ちょうど**の欠陥を中央に仕込んだところ"
                      "(上から brick / grass / gravel)。隅の枠は同じ場所の 2 倍拡大 ——"
                      "限界の振幅では、拡大して初めて見える。限界は %s。"
                      % " / ".join("%s %.3f" % (n, table[n][1]) for n in real))

    amps = np.round(np.geomspace(0.02, 1.2, 18), 4)
    g, syn = real["brick"], table["brick"][5]
    frames = []
    for amp in amps:
        rgb = _pair_rgb(g + blob(g.shape, cx, cy, amp),
                        syn + blob(syn.shape, cx, cy, amp))
        rgb = np.asarray(fs.annotate_legend(
            rgb, ["左=実写 brick / 右=残差 σ を揃えた合成", "振幅 %.3f" % amp],
            (6, 6), anchor="lt", font_size=11, radius=5.0), dtype=np.float64)
        frames.append((np.clip(rgb, 0.0, 1.0) * 255).astype(np.uint8))
    figs.save_gif("defect_floor_sweep", frames, fps=6,
                  caption="同じ欠陥を振幅 %.2f から %.2f まで上げていく。左=実写の brick、"
                          "右=**残差 σ を揃えた**合成の地。雑音の量は同じなのに、"
                          "右のほうが先に見えてくる。"
                          % (amps[0], amps[-1]))
    n, _metrics = make_defect_floor_explained(real, table)
    return n


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
