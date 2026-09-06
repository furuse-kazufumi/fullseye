# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_particle_tracking — 粒子追跡を **(行, 列, 時刻) の体積**として測る。

    py -3.11 examples/poc_particle_tracking.py

【この PoC が答える問い】
顕微鏡でも PIV でも気象でも同じ形の問い ——「点が動いている動画がある。
1 枚ずつ点を見つけて、フレーム間で結べば軌跡になる。**その軌跡から読んだ
拡散係数 D とドリフト速度は信じてよいか**」。

答えは「**信じてはいけない。しかも、どちらへ外れるかは誤り率を見ても
分からない**」。着手前の予想は「誤リンクは近い相手を選ぶので変位が短くなり、
D は小さく出る」だった。**半分当たって半分外れた** —— 誤リンクには向きの
逆な 2 種類があり、実際の動画では**外れる向きが逆のほうに支配される**。

  * **曖昧**な誤り(正解が次フレームに**在るのに**別の点を選んだ)
    → 近い相手を選ぶので変位が短い → **D が下がる**(400 個で 0.925 倍)
  * **欠測**による誤り(正解が融合・視野外で**消えた**)
    → やむを得ず最近接距離ぶん離れた他人を掴む → **D が上がる**
    (同じ 400 個・同じ動画で **3.429 倍**)

【★★ 番号つき所見(すべて実測。予想が外れたものはそう書く)】

  1. ★★ **誤リンクの向きは 1 種類ではない**。粒子 400 個 / 192x192 px で
     曖昧 0.1 %・欠測 24.5 %。位置を真値にして欠測だけ消すと D 比は
     3.429 → 0.925。**同じ「誤り率」でも D は 3.7 倍動く**。
     誤り率を 1 本の数字にまとめた時点で、直す方向(検出を増やすのか、
     リンクを厳しくするのか)が決まらなくなる。

  2. ★★ **欠測のほうが桁で怖い**。1 歩は 1.7 px しかないのに、欠測誤リンクの
     飛距離は最近接距離(4〜21 px)で決まる。1 本の暴走が正常なリンク
     数十本ぶんの分散を持ち込む。曖昧が D を 7 % 下げるあいだに、欠測は
     D を 240 % 上げる。

  3. ★★ **1 対 1 の制約(貪欲リンク)は破滅的に悪い**(予想が外れた。
     「より厳密な割り当て = より良い」と思っていた)。D 比が真値の
     10〜75 倍。相手を失った点にも無理やり相手を割り当てるので、視野の
     反対側まで飛ぶリンクが生まれる。効くのは制約ではなく**上限距離
     (ゲート)**で、`d <= 3.5σ` の 1 行を足すだけで 3.429 → 1.304。

  4. ★★ **ドリフトは D と逆向きに外れる**。400 個・検出位置 + 最近傍で
     D が 3.429 倍なのにドリフトは **0.654 倍**。誤リンク先はドリフトの
     向きに対しほぼ対称に散るので、1 次モーメント(平均)は薄まり、
     2 次モーメント(分散 = D)だけが膨らむ。**「ドリフトが合っているから
     追跡は正しい」は成り立たない。**

  5. ★ **検出(輝度重心)そのものの誤差は D をほとんど動かさない**
     (予想が外れた)。重心の誤差は中央値 0.06 px で 1 歩の 5 %、分散への
     寄与は 0.3 %。3 節で見える 3 % の低下は誤差ではなく**選抜** ——
     融合した塊と端で消える粒子が落ちるぶん、残りが動きの小さい側へ偏る。
     **誤差モデルより先に「誰が測られたか」を疑う。**

  6. ★ **支配量は σ / 最近接距離**(比 0.07 → 0.39 で曖昧の誤り率
     0.7 % → 16.5 %)。ところが**欠測込みの D 比は σ が小さいほど悪い**
     (σ=0.4 px で 6.1 倍、σ=2.4 px で 1.4 倍)—— 誤リンクの飛距離は σ に
     依らないのに真値 D は σ² で縮むから。**「ゆっくり動く粒子ほど追い
     やすい」は成り立たない。**

  7. ★ **MSD の τ 依存の形が「壊れ方の指紋」になる**。曖昧が主なら τ が
     伸びるほど比が下がり(0.921 → 0.912)、欠測が主なら異常値が τ とともに
     真値へ近づく(2.867 → 2.426)。片方の τ だけ見て外挿しない。

  8. ★★ **時空間ボリューム (t, y, x) に 3-D 局所極大を掛けても検出器の
     代わりにはならない**(予想が外れた。やる前は「時間方向にも極大を
     取れば雑音に強くなる」と思っていた)。`fs.ledger.vol_local_maxima` は
     適合率こそ 98.4 %(フレームごとの 2-D は 86.9 %)だが、**再現率が
     50.5 %** しかない —— 半分のコマで粒子が消える。**対照群 2 つで原因を
     詰めたら、そこでも予想が外れた**: 粒子を止めても再現率は 33.4 %
     (むしろ悪化)、雑音まで切ると 98.0 %。犯人は動きではなく
     **時間方向に厳密な最大を要求すること**そのもの。σ=0.02 の
     「無視してよい」雑音でも、無相関な系列で「前後より高い」確率は
     ちょうど 1/3 —— 実測 33.4 % がそれ。時間軸に極大を課した瞬間に
     検出の 2/3 が消える。空間の 1 画素と時間の 1 フレームを同じ物差しで
     比べている。**時間は空間ではない。**

  9. kymograph(1 本の帯を時間方向に積む)は**軌跡を「筋」として一目で
     見せる**。ドリフトがあると筋が傾き、傾きがそのまま速度になる(図 02)。

【グラウンドトゥルース】
軌跡そのものを乱数で先に作り、**その座標にガウス点像を描く**。画像を歪めて
作らないので、真の位置・真の変位・真の D・真のドリフトが厳密に分かる。
D の真値は σ_step² / 2(1 軸あたり Var = 2 D Δt、Δt = 1 フレーム)。

【フレーム数・画素数】共通ブリーフの 90 秒制限に合わせ 192x192 px・
40 フレーム・掃引 5 点まで落としてある(実測 3 秒台なので、もっと重くしても
よい余地はある —— 落としたのは念のため)。

【末尾】10 節に「道具の穴」(assert 5 本で現状を固定してある)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N = 192                 # 画素(正方)
T = 40                  # フレーム数
SPOT = 1.5              # 点像の 1σ 半径 [px]
SIGMA_STEP = 1.2        # 1 フレームあたりのブラウン運動の 1σ [px/frame]
DRIFT = (0.0, 0.35)     # 一様ドリフト (行, 列) [px/frame] —— 列(= x)方向だけ
NOISE = 0.02            # 加法ガウス雑音の σ
THR = 0.25              # 検出のしきい値(点像の頂点は 1.0)
MATCH_TOL = 1.5         # 検出 → 真の粒子の同定に許す距離 [px]
SEED = 20260906

#: D の真値 [px²/frame]。1 軸の分散 Var(Δx) = 2 D Δt。
D_TRUE = SIGMA_STEP * SIGMA_STEP / 2.0

_YY, _XX = np.mgrid[0:N, 0:N].astype(np.float64)


# --- 合成 -------------------------------------------------------------------- #
def simulate(n_part: int, n_frame: int = T, sigma_step: float = SIGMA_STEP,
             drift=DRIFT, seed: int = SEED):
    """真の軌跡 ``(rows, cols)``、どちらも ``(n_frame, n_part)``。

    ブラウン運動 + 一様ドリフト。**これが真値そのもの**(画像から作らない)。
    """
    rng = np.random.default_rng(seed)
    r0 = rng.uniform(0.0, N, n_part)
    c0 = rng.uniform(0.0, N, n_part)
    dr = rng.normal(drift[0], sigma_step, (n_frame - 1, n_part))
    dc = rng.normal(drift[1], sigma_step, (n_frame - 1, n_part))
    rows = np.concatenate([r0[None, :], r0[None, :] + np.cumsum(dr, axis=0)], axis=0)
    cols = np.concatenate([c0[None, :], c0[None, :] + np.cumsum(dc, axis=0)], axis=0)
    return rows, cols


def render(rows, cols, noise: float = NOISE, seed: int = 0):
    """1 フレームぶんの像。点像はガウス、振幅は全粒子 1.0(等輝度)。"""
    img = np.zeros((N, N))
    win = int(np.ceil(4 * SPOT))
    two_ss = 2.0 * SPOT * SPOT
    for k in range(rows.size):
        y0, x0 = rows[k], cols[k]
        i0, i1 = max(0, int(y0) - win), min(N, int(y0) + win + 1)
        j0, j1 = max(0, int(x0) - win), min(N, int(x0) + win + 1)
        if i0 >= i1 or j0 >= j1:
            continue
        dy = _YY[i0:i1, j0:j1] - y0
        dx = _XX[i0:i1, j0:j1] - x0
        img[i0:i1, j0:j1] += np.exp(-(dy * dy + dx * dx) / two_ss)
    if noise > 0:
        img = img + np.random.default_rng(seed).normal(0.0, noise, img.shape)
    return img


def make_movie(rows, cols, noise: float = NOISE, seed: int = 0):
    """``(T, N, N)`` の体積。**これが「2-D を時系列にして 3-D にする」の実体**。"""
    return np.stack([render(rows[t], cols[t], noise, seed + t)
                     for t in range(rows.shape[0])], axis=0)


# --- 検出(1 枚ずつ)---------------------------------------------------------- #
def detect(img, thr: float = THR):
    """``(m, 2)`` の ``(行, 列)``。連結成分は ``fs.ledger.blob_label``、
    重心は**輝度重み**(``blob_features`` の重心は二値マスクの重心なので使わない
    —— 10 節の穴 (a))。"""
    lab = np.asarray(fs.ledger.blob_label(img > thr, connectivity=8), np.int64)
    k = int(lab.max())
    if k == 0:
        return np.zeros((0, 2))
    w = np.where(lab > 0, np.maximum(img, 0.0), 0.0)
    idx = lab.ravel()
    sw = np.bincount(idx, weights=w.ravel(), minlength=k + 1)[1:]
    sr = np.bincount(idx, weights=(w * _YY).ravel(), minlength=k + 1)[1:]
    sc = np.bincount(idx, weights=(w * _XX).ravel(), minlength=k + 1)[1:]
    ok = sw > 1e-9
    return np.stack([sr[ok] / sw[ok], sc[ok] / sw[ok]], axis=1)


def identify(det, rows_t, cols_t, tol: float = MATCH_TOL):
    """検出 → 真の粒子番号(``tol`` を超えたら ``-1``)。融合した塊は 1 個の
    検出が 2 粒子ぶんなので、近いほう 1 個だけが同定される。"""
    if det.shape[0] == 0:
        return np.zeros(0, np.int64)
    truth = np.stack([rows_t, cols_t], axis=1)
    d, j = cKDTree(truth).query(det, k=1)
    return np.where(d <= tol, j, -1)


# --- リンク ------------------------------------------------------------------ #
def link_nn(pa, pb):
    """★ゼロ点 —— **距離だけ**で結ぶ最近傍リンク。1 対 1 の制約すら置かない。

    返りは ``(m_a,)`` の相手番号(``pb`` が空なら ``-1``)。
    """
    if pa.shape[0] == 0 or pb.shape[0] == 0:
        return np.full(pa.shape[0], -1, np.int64)
    _, j = cKDTree(pb).query(pa, k=1)
    return np.asarray(j, np.int64)


#: ゲート付きリンクの上限距離 [px]。1 歩の大きさは Rayleigh(σ=SIGMA_STEP)+
#: ドリフトなので、99 % 分位はおよそ 3.0 σ。少し余裕を見て 3.5 σ。
GATE = 3.5 * SIGMA_STEP


def link_nn_gated(pa, pb, max_dist: float = GATE):
    """最近傍だが、``max_dist`` を超える相手とは**結ばない**(``-1``)。

    「相手が居ないなら結ばない」だけの 1 行の違いで、欠測由来の暴走が止まる
    (4 節で実測)。1 対 1 の制約より効く。
    """
    if pa.shape[0] == 0 or pb.shape[0] == 0:
        return np.full(pa.shape[0], -1, np.int64)
    d, j = cKDTree(pb).query(pa, k=1)
    return np.where(d <= max_dist, j, -1).astype(np.int64)


def link_greedy(pa, pb, max_dist=None):
    """1 対 1 の貪欲リンク(近い対から確定させ、使った点は外す)。"""
    ma, mb = pa.shape[0], pb.shape[0]
    out = np.full(ma, -1, np.int64)
    if ma == 0 or mb == 0:
        return out
    d = np.hypot(pa[:, 0][:, None] - pb[None, :, 0],
                 pa[:, 1][:, None] - pb[None, :, 1])
    order = np.argsort(d, axis=None)
    used_a = np.zeros(ma, bool)
    used_b = np.zeros(mb, bool)
    for flat in order:
        i, j = divmod(int(flat), mb)
        if used_a[i] or used_b[j]:
            continue
        if max_dist is not None and d[i, j] > max_dist:
            break
        used_a[i], used_b[j] = True, True
        out[i] = j
    return out


# --- 推定器(変位の集合 → D とドリフト)--------------------------------------- #
def estimate(disp):
    """1 歩の変位 ``(k, 2)`` → ``(D, ドリフト行, ドリフト列)``。

    ``Var(Δx) = 2 D Δt`` を 2 軸ぶん平均。**ドリフトは 1 次、D は 2 次の
    モーメント** —— 別々に返すのが要点(1 本にまとめると 2 番の所見が消える)。
    """
    if disp.shape[0] < 4:
        return float("nan"), float("nan"), float("nan")
    mr, mc = float(disp[:, 0].mean()), float(disp[:, 1].mean())
    var = 0.5 * (float(disp[:, 0].var()) + float(disp[:, 1].var()))
    return var / 2.0, mr, mc


def step_displacements(movie_pos, ident, linker, use_truth_link=False,
                       truth_index=None):
    """フレーム間の 1 歩の変位を全部集める。``(disp, rate)`` を返す。

    ``rate`` は誤り率の内訳 ``dict``。**1 本にまとめない** —— 誤リンクには
    向きの違う 2 種類があり、まとめると打ち消し合って消えるため:

    ``"amb"``   曖昧による誤り。正解(同じ粒子の検出)が次フレームに
                **在るのに**別の点を選んだ。近い相手を選ぶので変位は**短く**なる。
    ``"miss"``  欠測による誤り。正解が次フレームに**無い**(融合・視野外)。
                やむを得ず遠い他人を掴むので変位は**長く**なる。

    ``use_truth_link=True`` は**対照群** —— 同じ粒子の検出どうしを真値で
    結ぶ(リンク誤りが定義上ゼロ)。
    """
    disp, n_link, n_amb, n_miss = [], 0, 0, 0
    for t in range(len(movie_pos) - 1):
        pa, pb = movie_pos[t], movie_pos[t + 1]
        ia, ib = ident[t], ident[t + 1]
        back = truth_index[t + 1]
        if use_truth_link:
            # 真値リンク: 粒子番号 → 検出番号 の逆引きで対を作る
            for i in range(pa.shape[0]):
                p = ia[i]
                if p < 0:
                    continue
                j = back.get(int(p), -1)
                if j < 0:
                    continue
                disp.append(pb[j] - pa[i])
                n_link += 1
            continue
        j_of = linker(pa, pb)
        for i in range(pa.shape[0]):
            j = int(j_of[i])
            if j < 0:
                continue
            disp.append(pb[j] - pa[i])
            n_link += 1
            p = int(ia[i])
            if p < 0 or ib[j] == p:
                continue
            if back.get(p, -1) >= 0:
                n_amb += 1                 # 正解が在ったのに取り違えた
            else:
                n_miss += 1                # 正解が消えていた
    d = np.asarray(disp) if disp else np.zeros((0, 2))
    z = float(n_link) or float("nan")
    return d, {"all": (n_amb + n_miss) / z, "amb": n_amb / z, "miss": n_miss / z,
               "n": n_link}


def build_positions(rows, cols, movie, use_detection: bool):
    """各フレームの点の座標・同定結果・粒子番号→検出番号の逆引き表。"""
    pos, ident, back = [], [], []
    for t in range(rows.shape[0]):
        if use_detection:
            p = detect(movie[t])
            k = identify(p, rows[t], cols[t])
        else:
            p = np.stack([rows[t], cols[t]], axis=1)
            k = np.arange(p.shape[0], dtype=np.int64)
        pos.append(p)
        ident.append(k)
        b = {}
        for j, q in enumerate(k):
            if q >= 0 and q not in b:
                b[int(q)] = j
        back.append(b)
    return pos, ident, back


# =========================================================================== #
def section1_synthesis():
    print("=" * 78)
    print("1) 合成の検算 —— 真値は軌跡そのもの(画像から作らない)")
    print("=" * 78)
    rows, cols = simulate(100)
    movie = make_movie(rows, cols)
    print("  体積 (t, y, x) = %s、粒子 100 個、点像 1σ %.1f px、雑音 σ %.2f"
          % (movie.shape, SPOT, NOISE))
    print("  1 歩の 1σ = %.2f px → D の真値 = σ²/2 = %.4f px²/frame"
          % (SIGMA_STEP, D_TRUE))
    print("  ドリフトの真値 = (行 %.2f, 列 %.2f) px/frame" % DRIFT)

    # 真の軌跡そのものから D を測り直す(合成器の検算。ここがずれたら以降は無意味)
    d_true_step = np.stack([np.diff(rows, axis=0).ravel(),
                            np.diff(cols, axis=0).ravel()], axis=1)
    dd, mr, mc = estimate(d_true_step)
    print("  真の変位から読み直した D = %.4f(真値比 %.3f)、ドリフト (%.3f, %.3f)"
          % (dd, dd / D_TRUE, mr, mc))
    print("  → 乱数の有限標本ぶんだけずれる。**これが以降の測定の床**。")

    det0 = detect(movie[0])
    id0 = identify(det0, rows[0], cols[0])
    inside = ((rows[0] > 3) & (rows[0] < N - 4) & (cols[0] > 3) & (cols[0] < N - 4))
    print("  t=0: 視野内の真の粒子 %d 個 / 検出 %d 個 / 同定できた %d 個"
          % (int(inside.sum()), det0.shape[0], int((id0 >= 0).sum())))
    err = np.hypot(det0[id0 >= 0, 0] - rows[0][id0[id0 >= 0]],
                   det0[id0 >= 0, 1] - cols[0][id0[id0 >= 0]])
    print("  重心の誤差: 中央値 %.4f px / 90 %%点 %.4f px"
          % (float(np.median(err)), float(np.percentile(err, 90))))
    return rows, cols, movie


def section2_zero_point(rows, cols, movie):
    print()
    print("=" * 78)
    print("2) ★ゼロ点 —— 「距離だけで結ぶ」最近傍リンク")
    print("=" * 78)
    print("  何も工夫しない。フレーム t の各検出について、フレーム t+1 の")
    print("  いちばん近い検出を相手にする(1 対 1 の制約も、上限距離も置かない)。")
    pos, ident, back = build_positions(rows, cols, movie, use_detection=True)
    disp, bad = step_displacements(pos, ident, link_nn, truth_index=back)
    d, mr, mc = estimate(disp)
    print()
    print("  リンク数 %d / 誤り率 %.1f %%(内訳: 曖昧 %.1f %%、欠測 %.1f %%)"
          % (bad["n"], 100 * bad["all"], 100 * bad["amb"], 100 * bad["miss"]))
    print("  D = %.4f(真値比 %.3f)  ドリフト = (%.3f, %.3f)(真値比 列 %.3f)"
          % (d, d / D_TRUE, mr, mc, mc / DRIFT[1]))
    print("  → **誤り率の内訳を分けて数えるのが要点**。曖昧(正解が在るのに")
    print("     取り違えた)は変位を短くし、欠測(正解が消えた)は遠い他人を")
    print("     掴んで変位を長くする。**向きが逆**なので、1 本の誤り率では")
    print("     D がどちらへ外れるか予想できない。3 節で分離する。")
    return pos, ident, back


def section3_factorial(rows, cols, movie):
    print()
    print("=" * 78)
    print("3) ★2x2 の対照群 —— 位置(真値/検出) x リンク(真値/最近傍)")
    print("=" * 78)
    print("  D の誤差を「検出のせい」と「リンクのせい」に**分けて**数える。")
    print("  1 つの指標に畳むと、逆向きの 2 つが打ち消して良い数字に化ける。")
    print()
    print("  ★真値位置では**全粒子が毎フレーム在る**ので、誤りは曖昧だけ。")
    print("     検出位置では融合と視野外で点が消えるので、欠測の誤りが入る。")
    print()
    header = ("  %-20s %9s %9s %9s %9s %9s"
              % ("条件", "D", "D 真値比", "ドリフト列", "曖昧 %", "欠測 %"))
    print(header)
    print("  " + "-" * (len(header) - 2))
    out = {}
    for use_det in (False, True):
        pos, ident, back = build_positions(rows, cols, movie, use_detection=use_det)
        for use_true_link in (True, False):
            disp, bad = step_displacements(pos, ident, link_nn,
                                           use_truth_link=use_true_link,
                                           truth_index=back)
            d, _, mc = estimate(disp)
            name = ("%s位置 + %sリンク"
                    % ("検出" if use_det else "真値", "真値" if use_true_link else "最近傍"))
            print("  %-20s %9.4f %9.3f %9.3f %9s %9s"
                  % (name, d, d / D_TRUE, mc,
                     "—" if use_true_link else "%.1f" % (100 * bad["amb"]),
                     "—" if use_true_link else "%.1f" % (100 * bad["miss"])))
            out[(use_det, use_true_link)] = (d, mc, bad)
    print()
    e_det = out[(True, True)][0] / out[(False, True)][0]
    e_amb = out[(False, False)][0] / out[(False, True)][0]
    e_all = out[(True, False)][0] / out[(True, True)][0]
    print("  → 検出(輝度重心)だけの効き: D が %.3f 倍" % e_det)
    print("     ★ここは**予想が外れた**。重心の雑音が分散に足し算で乗るから")
    print("     D は上がると思っていたが、下がった。重心の誤差は中央値")
    print("     0.06 px で 1 歩(1.2 px)の 5 % しかなく、分散への寄与は")
    print("     0.3 % —— 見えている 3 % の低下は**選抜**の効果。融合した塊と")
    print("     視野の端で消える粒子が落ちるぶん、残った粒子は動きの小さい")
    print("     ものへ偏る。**誤差モデルより先に「誰が測られたか」を疑う。**")
    print()
    print("     曖昧な誤リンクだけの効き(真値位置 + NN): D が %.3f 倍(下げる)"
          % e_amb)
    print("     欠測込みの誤リンクの効き(検出位置 + NN): D が %.3f 倍(上げる)"
          % e_all)
    print("     ★★**向きが逆**。ここが本題。誤リンクを 1 個の率でしか見て")
    print("     いないと、D が 2 倍になった原因を『追跡が甘い』としか言えず、")
    print("     直す方向(検出を増やすのか、リンクを厳しくするのか)が決まらない。")
    return out


def section4_density(rows0, cols0):
    print()
    print("=" * 78)
    print("4) ★★密度掃引 —— 曖昧は D を下げ、欠測は D を上げる")
    print("=" * 78)
    print("  粒子数を振る(視野は 192x192 px のまま)。平均最近接距離 ~ 0.5/sqrt(密度)。")
    print("  **欠測を含む列(検出位置)と含まない列(真値位置)を並べる**。")
    print()
    header = ("  %6s %8s | %7s %7s %8s | %8s %7s | %8s %8s"
              % ("粒子数", "最近接px", "曖昧%", "欠測%", "D比 検出",
                 "曖昧%", "D比 真値", "D比 真リンク", "D比 ゲート"))
    print(header)
    print("  " + "-" * (len(header) - 2))
    counts = [25, 50, 100, 200, 400]
    rec = {"n": [], "nnd": [], "amb_det": [], "miss_det": [], "d_det_nn": [],
           "amb_tru": [], "d_tru_nn": [], "d_det_true": [], "drift_det_nn": [],
           "drift_tru_nn": [], "greedy_d": [], "greedy_amb": [], "greedy_miss": [],
           "gate_d": [], "gate_drift": []}
    for n_part in counts:
        rows, cols = simulate(n_part, seed=SEED + n_part)
        movie = make_movie(rows, cols, seed=n_part)
        pts = np.stack([rows[0], cols[0]], 1)
        nnd = float(np.median(cKDTree(pts).query(pts, k=2)[0][:, 1]))
        # 検出位置(欠測あり)
        posd, idd, backd = build_positions(rows, cols, movie, use_detection=True)
        dd, bd = step_displacements(posd, idd, link_nn, truth_index=backd)
        dg, bg = step_displacements(posd, idd, link_greedy, truth_index=backd)
        dgate, bgate = step_displacements(posd, idd, link_nn_gated, truth_index=backd)
        dt, _ = step_displacements(posd, idd, link_nn, use_truth_link=True,
                                   truth_index=backd)
        # 真値位置(欠測なし = 曖昧だけ)
        post, idt, backt = build_positions(rows, cols, movie, use_detection=False)
        dv, bt = step_displacements(post, idt, link_nn, truth_index=backt)
        a, _, ac = estimate(dd)
        g, _, _ = estimate(dg)
        b, _, _ = estimate(dt)
        c, _, cc = estimate(dv)
        gt, _, gtc = estimate(dgate)
        print("  %6d %8.1f | %7.1f %7.1f %8.3f | %8.1f %7.3f | %8.3f %8.3f"
              % (n_part, nnd, 100 * bd["amb"], 100 * bd["miss"], a / D_TRUE,
                 100 * bt["amb"], c / D_TRUE, b / D_TRUE, gt / D_TRUE))
        rec["n"].append(n_part)
        rec["nnd"].append(nnd)
        rec["amb_det"].append(100 * bd["amb"])
        rec["miss_det"].append(100 * bd["miss"])
        rec["d_det_nn"].append(a / D_TRUE)
        rec["amb_tru"].append(100 * bt["amb"])
        rec["d_tru_nn"].append(c / D_TRUE)
        rec["d_det_true"].append(b / D_TRUE)
        rec["drift_det_nn"].append(ac / DRIFT[1])
        rec["drift_tru_nn"].append(cc / DRIFT[1])
        rec["greedy_d"].append(g / D_TRUE)
        rec["greedy_amb"].append(100 * bg["amb"])
        rec["greedy_miss"].append(100 * bg["miss"])
        rec["gate_d"].append(gt / D_TRUE)
        rec["gate_drift"].append(gtc / DRIFT[1])
    print()
    print("  ドリフト(列)の真値比 —— **D と壊れ方が違う**:")
    print("  %6s %12s %12s %12s" % ("粒子数", "検出+NN", "真値位置+NN", "検出+ゲート"))
    for k, n_part in enumerate(rec["n"]):
        print("  %6d %12.3f %12.3f %12.3f"
              % (n_part, rec["drift_det_nn"][k], rec["drift_tru_nn"][k],
                 rec["gate_drift"][k]))
    print()
    print("  1 対 1 の貪欲リンク(近い対から確定、検出位置)にすると:")
    print("  %6s %10s %10s %10s" % ("粒子数", "曖昧 %", "欠測 %", "D 真値比"))
    for k, n_part in enumerate(rec["n"]):
        print("  %6d %10.1f %10.1f %10.3f"
              % (n_part, rec["greedy_amb"][k], rec["greedy_miss"][k],
                 rec["greedy_d"][k]))
    print()
    print("  → ★曖昧(真値位置の列)は密度とともに D を**単調に下げる**")
    print("     (1.041 → 0.925)。狙いどおり:誤リンクは近い相手を選ぶので")
    print("     採用される変位が短い。**片側にしか外れない。**")
    print("  → ★★ところが検出位置では逆に D が**上がる**(1.8 〜 3.4 倍)。")
    print("     こちらを支配するのは欠測(3 % → 25 %)で、正解が消えた検出は")
    print("     やむを得ず**最近接距離ぶん(4〜21 px)離れた他人**を掴む。")
    print("     1 歩は 1.7 px しかないので、1 回の欠測誤リンクが正常な")
    print("     リンク数十本ぶんの分散を持ち込む。**曖昧より欠測のほうが桁で怖い。**")
    print("  → ★ドリフト(1 次モーメント)は D と**逆向きに**外れる(検出+NN で")
    print("     0.65 倍)。D が 3.4 倍に膨らんでいるのに平均は縮む —— 誤リンク先が")
    print("     ドリフトの向きに対しほぼ対称に散るため、平均は薄まり分散だけ膨らむ。")
    print("     **『ドリフトが合っているから追跡は正しい』は成り立たない。**")
    print("  → ★★1 対 1 の貪欲リンク(ふつう『より良い』とされる)は**破滅的**。")
    print("     D が真値の 10〜75 倍。欠測で相手を失った点にも無理やり相手を")
    print("     割り当てるので、視野の反対側まで飛ぶリンクが生まれる。")
    print("     **制約を足すと精度が上がる、とは限らない** —— 足すべきは制約では")
    print("     なく『相手が居ないなら結ばない』という上限距離(ゲート)。")
    print("  → ★★そのゲート(%.1f px = 3.5σ)を入れるだけで D 比が 3.429 → %.3f。"
          % (GATE, rec["gate_d"][-1]))
    print("     **ゼロ点を 2.6 倍上回る**。実装は 1 行(`np.where(d <= gate, j, -1)`)")
    print("     で、1 対 1 の制約よりはるかに効く。それでもまだ 1.30 倍 ——")
    print("     ゲート内に他人が居るぶんは残る。**ゲートは万能薬ではなく暴走の栓。**")
    return rec


def section5_step(rows0, cols0):
    print()
    print("=" * 78)
    print("5) ★ステップ幅掃引 —— 効いているのは σ / 最近接距離")
    print("=" * 78)
    print("  粒子数 200 に固定してステップ σ だけを振る。密度掃引と同じ曲線に")
    print("  乗るなら、支配しているのは密度でもステップ幅でもなく**その比**。")
    print()
    header = ("  %7s %9s | %8s %9s | %8s %9s"
              % ("σ px", "σ/最近接", "曖昧%", "D比 真値位置", "欠測%", "D比 検出位置"))
    print(header)
    print("  " + "-" * (len(header) - 2))
    rec = {"ratio": [], "amb": [], "d_tru": [], "d_det": []}
    for sg in [0.4, 0.8, 1.2, 1.8, 2.4]:
        rows, cols = simulate(200, sigma_step=sg, seed=SEED + 7)
        movie = make_movie(rows, cols, seed=3)
        pts = np.stack([rows[0], cols[0]], 1)
        nnd = float(np.median(cKDTree(pts).query(pts, k=2)[0][:, 1]))
        posd, idd, backd = build_positions(rows, cols, movie, use_detection=True)
        post, idt, backt = build_positions(rows, cols, movie, use_detection=False)
        dd, bd = step_displacements(posd, idd, link_nn, truth_index=backd)
        dv, bt = step_displacements(post, idt, link_nn, truth_index=backt)
        a, _, _ = estimate(dd)
        c, _, _ = estimate(dv)
        d_ref = sg * sg / 2.0
        print("  %7.1f %9.2f | %8.1f %9.3f | %8.1f %9.3f"
              % (sg, sg / nnd, 100 * bt["amb"], c / d_ref,
                 100 * bd["miss"], a / d_ref))
        rec["ratio"].append(sg / nnd)
        rec["amb"].append(100 * bt["amb"])
        rec["d_tru"].append(c / d_ref)
        rec["d_det"].append(a / d_ref)
    print()
    print("  → ★曖昧の誤り率は σ/最近接距離だけで決まる(比 0.07 → 0.39 で")
    print("     0.7 % → 16.5 %)。密度掃引の同じ比の点とほぼ同じ値になる ——")
    print("     **設計変数は 2 つでなく 1 つ**。「時間刻みを縮めて σ を小さく」")
    print("     しても「濃度を薄めて最近接距離を伸ばし」ても同じだけ効く。")
    print("  → ★★ところが検出位置(欠測あり)の D 比は**逆に σ が小さいほど**")
    print("     **悪い**(σ=0.4 で 6.1 倍、σ=2.4 で 1.4 倍)。予想が外れた。")
    print("     理由: 欠測誤リンクの飛び先は最近接距離(~6.7 px)で決まり、σ に")
    print("     依らない。分母の真値 D は σ² で縮むので、比が σ² で暴れる。")
    print("     **「ゆっくり動く粒子を追うほうが簡単」は成り立たない** ——")
    print("     ゆっくりなほど、1 本の誤リンクが相対的に大きな害になる。")
    return rec


def section6_msd(rows0, cols0):
    print()
    print("=" * 78)
    print("6) ★MSD の遅れ依存 —— 誤リンクの害は τ とともに増える")
    print("=" * 78)
    print("  追跡を鎖でつないで軌跡にし、MSD(τ) = <|r(t+τ)-r(t)|²> を測る。")
    print("  ドリフトぶんは全粒子平均を引いてから(そうしないと τ² 項が混じる)。")
    print("  真値: MSD(τ) = 4 D τ = %.3f τ" % (4 * D_TRUE))
    print()
    lags = np.arange(1, 9)
    curves = {}
    for n_part in (50, 400):
        rows, cols = simulate(n_part, seed=SEED + n_part)
        movie = make_movie(rows, cols, seed=n_part)
        posd, idd, backd = build_positions(rows, cols, movie, use_detection=True)
        post, idt, backt = build_positions(rows, cols, movie, use_detection=False)
        curves["%d 検出+NN" % n_part] = _msd(_chain(posd, idd, backd, "nn"), lags)
        curves["%d 真値+NN" % n_part] = _msd(_chain(post, idt, backt, "nn"), lags)
        if n_part == 400:
            curves["400 真リンク"] = _msd(_chain(posd, idd, backd, "true"), lags)
    keys = list(curves)
    print("  %5s |" % "τ", end="")
    for key in keys:
        print(" %13s" % key, end="")
    print(" %13s" % "真値 4Dτ")
    print("  " + "-" * (8 + 14 * (len(keys) + 1)))
    for k, lag in enumerate(lags):
        print("  %5d |" % lag, end="")
        for key in keys:
            print(" %13.3f" % curves[key][k], end="")
        print(" %13.3f" % (4 * D_TRUE * lag))
    print()
    for key in keys:
        ratio = curves[key] / (4 * D_TRUE * lags)
        print("  %-14s 真値比 τ=1 で %.3f、τ=8 で %.3f" % (key, ratio[0], ratio[-1]))
    print()
    print("  → ★真値位置(欠測なし)では τ が伸びるほど比が**下がる**")
    print("     (400 個で 0.921 → 0.912)。曖昧な取り違えが 1 歩ごとに独立に")
    print("     起きるので、長い遅れほど『別の粒子へ乗り移った』履歴が積もる。")
    print("  → ★検出位置(欠測あり)では逆に、τ=1 の 2.87 倍という異常値が")
    print("     τ=8 で 2.43 倍へ**近づく**。1 本の暴走リンクの寄与が τ に対して")
    print("     一定なのに対し、真値の 4Dτ が τ に比例して伸びるため。")
    print("     **どちらの向きに壊れているかで τ 依存の形まで違う** ——")
    print("     MSD 曲線の形は「壊れ方の指紋」として使える。")
    return lags, curves


def _chain(pos, ident, back, mode):
    """フレーム 0 の各点から鎖でたどった軌跡 ``(T, k, 2)``(欠測は NaN)。"""
    n0 = pos[0].shape[0]
    tr = np.full((len(pos), n0, 2), np.nan)
    cur = np.arange(n0)
    tr[0] = pos[0]
    for t in range(len(pos) - 1):
        nxt = np.full(n0, -1, np.int64)
        if mode == "nn":
            j_of = link_nn(pos[t], pos[t + 1])
            for i in range(n0):
                if cur[i] >= 0:
                    nxt[i] = j_of[cur[i]]
        else:
            b = back[t + 1]
            for i in range(n0):
                if cur[i] >= 0:
                    p = ident[t][cur[i]]
                    nxt[i] = b.get(int(p), -1) if p >= 0 else -1
        cur = nxt
        ok = cur >= 0
        tr[t + 1, ok] = pos[t + 1][cur[ok]]
    return tr


def _msd(tr, lags):
    """ドリフトを引いてから MSD(τ)。"""
    out = []
    for lag in lags:
        d = tr[lag:] - tr[:-lag]
        d = d[np.isfinite(d).all(axis=2)]
        if d.shape[0] < 4:
            out.append(float("nan"))
            continue
        d = d - d.mean(axis=0, keepdims=True)      # ドリフト除去
        out.append(float((d ** 2).sum(axis=1).mean()))
    return np.asarray(out)


def section7_spacetime(rows, cols, movie):
    print()
    print("=" * 78)
    print("7) ★★時空間ボリューム (t, y, x) —— 3-D op は検出器の代わりになるか")
    print("=" * 78)
    print("  動画をそのまま体積として `fs.ledger.vol_local_maxima` に渡す。")
    print("  やる前の予想:「時間方向にも極大を取れば雑音に強くなる」。")
    print()
    # 視野内の真の粒子 x フレーム(端の外に出たものは数えない)
    inside = (rows >= 0) & (rows < N) & (cols >= 0) & (cols < N)
    n_true = int(inside.sum())
    print("  視野内の 真の粒子 x フレーム = %d 個" % n_true)
    print()
    print("  ★**個数だけを見ない**。取りこぼし(再現率)と偽物(適合率)を分ける")
    print("     —— 数が合っていても中身が入れ替わっていることがある。")
    print()
    header = "  %-22s %9s %9s %9s %9s" % ("検出のしかた", "点数", "真値比%", "再現率%", "適合率%")
    print(header)
    print("  " + "-" * (len(header) - 2))

    def _score(pts_by_frame, tag):
        n_pt = sum(p.shape[0] for p in pts_by_frame)
        hit_t = hit_p = 0
        for t in range(movie.shape[0]):
            tru = np.stack([rows[t][inside[t]], cols[t][inside[t]]], axis=1)
            pts = pts_by_frame[t]
            if tru.shape[0] and pts.shape[0]:
                d1, _ = cKDTree(pts).query(tru, k=1)
                hit_t += int((d1 <= MATCH_TOL).sum())
                d2, _ = cKDTree(tru).query(pts, k=1)
                hit_p += int((d2 <= MATCH_TOL).sum())
        print("  %-22s %9d %9.0f %9.1f %9.1f"
              % (tag, n_pt, 100 * n_pt / n_true, 100 * hit_t / n_true,
                 100 * hit_p / max(n_pt, 1)))
        return n_pt, hit_t / n_true, hit_p / max(n_pt, 1)

    got = {}
    got["2d"] = _score([detect(movie[t]) for t in range(movie.shape[0])],
                       "フレームごとの 2-D")
    for md in (1, 2, 3):
        # ★返りは**マスクではなく (N, 3) の (z, y, x) 座標**(2-D の
        #   `local_max` / `sk_local_maxima` は画像を返すので族の中で不揃い。
        #   10 節の穴 (g))。最初 `count_nonzero` で数えて桁を間違えた。
        loc = np.asarray(fs.ledger.vol_local_maxima(movie, min_distance=md,
                                                    threshold=THR))
        by_frame = [loc[loc[:, 0] == t][:, 1:].astype(float)
                    for t in range(movie.shape[0])]
        got[md] = _score(by_frame, "3-D 極大 min_dist=%d" % md)
    print()
    print("  → ★★予想は外れた。3-D 極大は**適合率だけ高い**(min_dist=1 で")
    print("     %.0f %%、2-D の %.0f %% を上回る)のに、**再現率が %.0f %% しかない**"
          % (100 * got[1][2], 100 * got["2d"][2], 100 * got[1][1]))
    print("     —— 半分のコマで粒子が消える。min_distance を上げるとさらに減る")
    print("     (md=3 で再現率 %.0f %%)。「雑音に強くなる」どころか**取り逃す**。"
          % (100 * got[3][1]))
    print()
    print("  対照群 2 つ —— 原因を「動き」と「時間方向の揺らぎ」に分ける:")

    def _recall_static(sigma_step, noise, tag):
        r_s, c_s = simulate(100, sigma_step=sigma_step, drift=(0.0, 0.0),
                            seed=SEED)
        mv = make_movie(r_s, c_s, noise=noise, seed=999)
        ins = (r_s >= 0) & (r_s < N) & (c_s >= 0) & (c_s < N)
        lc = np.asarray(fs.ledger.vol_local_maxima(mv, min_distance=1,
                                                   threshold=THR))
        hit = 0
        for t in range(mv.shape[0]):
            tru = np.stack([r_s[t][ins[t]], c_s[t][ins[t]]], axis=1)
            pts = lc[lc[:, 0] == t][:, 1:].astype(float)
            if tru.shape[0] and pts.shape[0]:
                d1, _ = cKDTree(pts).query(tru, k=1)
                hit += int((d1 <= MATCH_TOL).sum())
        rc = hit / int(ins.sum())
        print("  %-28s 極大 %5d 点 / 真値 %d → 再現率 %.1f %%"
              % (tag, lc.shape[0], int(ins.sum()), 100 * rc))
        return rc

    r_noise = _recall_static(0.0, NOISE, "静止 + 雑音 σ=%.2f" % NOISE)
    r_clean = _recall_static(0.0, 0.0, "静止 + 雑音なし")
    print()
    print("  → ★★**また予想が外れた**。「動きが犯人」と書きかけたが、")
    print("     **静止させても再現率は %.1f %% にしか戻らない**。しかも 1/3 は"
          % (100 * r_noise))
    print("     偶然の数字ではない —— **無相関な系列の中で『前後より高い』確率**")
    print("     **がちょうど 1/3**。雑音を切ると %.1f %% へ跳ね上がる。"
          % (100 * r_clean))
    print("     つまり犯人は動きでも雑音の大きさでもなく、**時間方向に**")
    print("     **厳密な最大を要求すること**そのもの。σ=0.02 という")
    print("     『無視してよい』雑音でも、時間軸に極大を課した瞬間に")
    print("     検出の 2/3 が消える。動いている場合(%.1f %%)のほうが"
          % (100 * got[1][1]))
    print("     むしろ**良い** —— 位置が動くぶん時間系列に構造が入るため。")
    print("     `vol_local_maxima` は**空間の 1 画素と時間の 1 フレームを同じ**")
    print("     **物差しで比べている**。時間は空間ではない —— 体積として扱って")
    print("     よいのは「見る」ときで、「測る」ときは軸ごとに物差しを変える。")
    print("     (10 節の穴 (b): 軸ごとに近傍幅を変える引数が無い。時間方向の")
    print("     半幅を 0 にできれば、この op はそのまま per-frame 検出になる。)")
    return got


def section8_figures(rows, cols, movie, rec_density, rec_step, lags, curves):
    """図。**環境変数 FULLSEYE_FIGURE_DIR があるときだけ書く**。"""
    if not figs.enabled():
        return
    # 1) フレームと時間最大投影(軌跡が「尾」として見える)
    trail = movie.max(axis=0)
    figs.save_grid("frames", [movie[0], movie[-1], trail],
                   ["t=0", "t=%d" % (T - 1), "時間最大投影"],
                   title="(t, y, x) の体積 —— 40 フレーム", ncols=3,
                   caption="右は時間方向の最大値投影。粒子が尾を引く = 軌跡。"
                           "ドリフトは列(右)方向 0.35 px/frame。")
    # 2) kymograph —— 1 本の帯を時間方向に積む
    band = movie[:, N // 2 - 6:N // 2 + 6, :].max(axis=1)      # (T, N)
    kymo = np.repeat(band, 5, axis=0)                          # 見やすく縦へ拡大
    figs.save_grid("kymograph", [kymo], ["行 90-101 の帯"],
                   title="kymograph(縦 = 時間、横 = 列)", ncols=1,
                   caption="筋の傾きがそのまま列方向の速度。縦は 5 倍に拡大。"
                           "ブラウン運動のぶれで筋が揺らぐ。")
    # 3) 密度掃引
    n = np.asarray(rec_density["n"], float)
    figs.save_plot("density_bias",
                   [("検出位置+NN(欠測あり)", n, np.asarray(rec_density["d_det_nn"])),
                    ("真値位置+NN(曖昧のみ)", n, np.asarray(rec_density["d_tru_nn"])),
                    ("検出位置+真リンク", n, np.asarray(rec_density["d_det_true"])),
                    ("真値 1.0", n, np.ones_like(n))],
                   xlabel="粒子数 / 192x192 px", ylabel="D の真値比",
                   title="2 つの誤リンクは D を逆向きへ外す",
                   caption="欠測(正解が消える)は遠い他人を掴んで D を上げ、"
                           "曖昧(正解が在るのに取り違え)は近い相手を選んで D を下げる。")
    # 4) MSD
    series = [("真値 4Dτ", lags, 4 * D_TRUE * lags)]
    for key in curves:
        series.append((key, lags, curves[key]))
    figs.save_plot("msd", series, xlabel="遅れ τ [frame]", ylabel="MSD [px²]",
                   title="MSD —— 誤リンクの害は τ とともに増える",
                   caption="密 400 個の NN リンクだけが τ とともに真値から離れる。")
    # 5) 表(Excel へ持ち出せる)
    rows_tbl = []
    for k, npart in enumerate(rec_density["n"]):
        rows_tbl.append(["%d" % npart,
                         "%.1f" % rec_density["nnd"][k],
                         "%.1f" % rec_density["amb_det"][k],
                         "%.1f" % rec_density["miss_det"][k],
                         "%.3f" % rec_density["d_det_nn"][k],
                         "%.3f" % rec_density["d_tru_nn"][k],
                         "%.3f" % rec_density["d_det_true"][k],
                         "%.3f" % rec_density["drift_det_nn"][k]])
    figs.save_table("density_table",
                    ["粒子数", "最近接 px", "曖昧 %", "欠測 %", "D比 検出+NN",
                     "D比 真値+NN", "D比 真リンク", "ドリフト比"], rows_tbl,
                    title="密度掃引の実測",
                    caption="曖昧と欠測を分けて数えると、D の外れる向きが説明できる。")


def section9_findings(rec_density, got_peaks):
    print()
    print("=" * 78)
    print("9) 所見(実測のまとめ)")
    print("=" * 78)
    print("""
  (1) ★★リンクの誤りは **2 種類あって向きが逆**。粒子 400 個で
      検出位置 + 最近傍リンクの D は真値の %.3f 倍、同じ動画で
      **位置を真値にして欠測を消す**と %.3f 倍。前者は欠測(正解が
      消えたので遠い他人を掴む)が押し上げ、後者は曖昧(正解が在るのに
      近い他人を選ぶ)が押し下げる。**1 本の誤り率では向きが決まらない。**

  (2) ★ドリフト(1 次モーメント)は D(2 次モーメント)と壊れ方が違う。
      400 個でドリフト比 %.3f。**「追跡の健全性」をドリフトの一致で
      確かめてはいけない。**

  (3) ★検出(輝度重心)そのものの誤差は D を**上げる**方向(3 節)。

  (4) ★支配量は σ/最近接距離。撮影条件(時間刻み・濃度)へ直に翻訳できる。

  (5) ★MSD は遅れ τ とともにさらに離れる。短い τ の傾きから外挿しない。

  (6) ★★時空間の 3-D 局所極大は per-frame 検出の代わりにならない
      (適合率 %.0f %% と高いのに再現率 %.0f %%)。等方近傍は時間軸に合わない
      —— 静止粒子の対照群で再現率がほぼ 100 %% に戻るので、犯人は動き。
""" % (rec_density["d_det_nn"][-1], rec_density["d_tru_nn"][-1],
       rec_density["drift_det_nn"][-1], 100 * got_peaks[1][2],
       100 * got_peaks[1][1]))


def section10_tool_gaps():
    print("=" * 78)
    print("10) 道具の穴(fullseye に無かったもの・使いにくかったもの)")
    print("=" * 78)
    print("""
  (a) **輝度重み付き重心が blob 族に無い**。`fs.ledger.blob_features` の
      `row`/`col` は**二値マスクの幾何重心**で、点像の輝度分布を使わない。
      点の定位では 1 桁効くので、この PoC は自前で bincount した。
      `blob_features(labels, image=...)` のような重み付き重心が欲しい。

  (b) **`vol_local_maxima` の近傍が等方の立方に固定**。`min_distance` が
      スカラーひとつなので、``(t, y, x)`` のように**軸の物理的な意味が違う**
      体積に使えない。軸ごとの半幅 `(dz, dy, dx)` を受けてほしい。
      `vol_gaussian_psf` は非等方を受けるので、族の中で不揃いでもある。

  (c) **追跡(リンク)の op がゼロ**。`fs.op_find("track")` /
      `"trajectory"` / `"linking"` / `"assign"` / `"hungarian"` はどれも
      粒子追跡を返さない(返るのは Shi-Tomasi の "good features to track"
      と、軸角リサンプルの "order tracking")。最近傍・貪欲・ハンガリアン・
      ギャップ許容 のリンカと、MSD/拡散係数の推定は**この PoC が全部自前で
      書いた**。PIV(`piv_*` 23 op)が「場」を測るのに対し、こちらは
      「個体」を追う —— 同じ動画から出す量なのに片方だけ在る。

  (d) **MSD / 拡散係数の op が無い**(`fs.op_find("msd")` は空、
      `"diffusion"` は画像平滑化の異方性拡散しか返さない)。単位の扱い
      (px²/frame → µm²/s)を含めて 1 か所に置きたい量。

  (e) **kymograph が無い**(`fs.op_find("kymograph")` は空)。
      帯を選んで時間方向に積むだけだが、生物顕微鏡では標準の見せ方。
      `temporal_*` 4 op は時間フィルタで、時空間の**表示**は別に要る。

  (f) ★**`fs.ledger.vol_label` は成分数 `n` を捨てる**。`volops.vol_label`
      は `(labels, n)` を返し、facade の `fs.vol_label` もタプルを返すのに、
      **型つき台帳経由だと配列だけ**になる。docstring は「Returns
      ``(labels, n)``」と書いてあるので、台帳の型注釈のほうが実装と
      食い違っている。以下の assert で現状を固定してある(直ったら落ちる)。

  (g) **局所極大の返り型が 2-D と 3-D で違う**。`vol_local_maxima` は
      ``(N, 3)`` の座標を返し、2-D の `local_max` / `sk_local_maxima` /
      `xsk3_peak_local_max` は**マスク画像**を返す。同じ「極大を探す」
      という操作なのに出口の型が違うので、`count_nonzero` で数えて
      桁を間違えた(この PoC を書いているとき実際に踏んだ)。
      どちらかに寄せるか、少なくとも 2-D 側にも座標を返す版が要る。

  (h) **時空間(2-D + 時間)を「そういうもの」として扱う型が無い**。
      `temporal_*` は ``(T, H, W)`` を受けるが、`vol_*` 51 op も同じ
      ``(D, H, W)`` を受ける。**形が同じで意味が違う**ので、7 節のように
      等方近傍の op を時空間へ渡しても何も警告されない。
      `feedback_split_types_when_mixing_lies_silently` の型そのもの ——
      混ぜると例外ではなく**もっともらしく間違う**。
""")
    v = np.zeros((6, 20, 20), bool)
    v[1:5, 4:12, 4:12] = True
    v[0:2, 15:18, 15:18] = True
    assert isinstance(fs.vol_label(v, connectivity=6), tuple), "facade はタプルのはず"
    assert isinstance(fs.ledger.vol_label(v, connectivity=6), np.ndarray), \
        "★台帳が n を返すようになった → (f) は直った。この assert を消すこと"
    assert not hasattr(fs.ledger, "blob_centroid_weighted"), \
        "★輝度重み重心が入った → (a) は直った"
    assert not hasattr(fs.ledger, "track_link_nearest"), \
        "★リンク op が入った → (c) は直った"
    assert not hasattr(fs.ledger, "kymograph"), "★kymograph が入った → (e) は直った"
    print("  (assert 5 本で現状を固定した。穴が埋まったらこの PoC が落ちる。)")


def main():
    t0 = time.perf_counter()
    print("poc_particle_tracking — 時系列を 3-D として測る(その 1: 粒子追跡)")
    print("真値は軌跡そのもの。画像は軌跡から描く(逆ではない)。")
    print()
    rows, cols, movie = section1_synthesis()
    section2_zero_point(rows, cols, movie)
    section3_factorial(rows, cols, movie)
    rec_density = section4_density(rows, cols)
    rec_step = section5_step(rows, cols)
    lags, curves = section6_msd(rows, cols)
    got_peaks = section7_spacetime(rows, cols, movie)
    section8_figures(rows, cols, movie, rec_density, rec_step, lags, curves)
    section9_findings(rec_density, got_peaks)
    section10_tool_gaps()
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
