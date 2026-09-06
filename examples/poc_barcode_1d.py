# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""1 次元バーコードが読めなくなる境界 —— 誤読と読み取り不能を分けて数える。

    py -3.11 examples/poc_barcode_1d.py

真値が**符号化した数字そのもの**なので、読めた / 読めないが二値で決まる。
1 枚ごとに 3 通りのどれかに落ちる: **成功**(真値と一致)/ **誤読**(9 桁を
返したが違う数字)/ **読み取り不能**(桁を返さなかった)。★誤読は読み取り
不能よりはるかに危険なので、**1 つの「読取率」に畳まない**。

【ここで符号化するもの —— EAN-13 準拠ではない】
規格は使わない。**自分で定義した簡易符号**を使う:

  * 1 桁 = 4 本の run(バー・空白・バー・空白)、幅の合計が 7 モジュール。
    10 桁ぶんの幅の並びは :data:`PATTERN` に直書きしてある(例: 0 は
    (1,1,2,3)、6 は (1,1,1,4))。合計が常に 7 なので、**桁ごとに自己クロック**
    できる —— 拡大率や 1/cos の伸びは桁の中で正規化されて消える。
  * 並び = 開始ガード (1,1,1,1) + **8 桁の本文** + **検査数字 1 桁** +
    終了ガード (1,1,1)。合計 70 モジュール / 43 run / 22 本のバー。
  * 検査数字は自分で決めた mod 10(重み 3,1,3,1,...)。

EXTEND: 実在の規格を読むなら符号表とガードを差し替えるだけで
:func:`decode_runs` 以降はそのまま使える。ただし規格には (a) 左右で
符号表が違う(EAN の奇偶パリティ)、(b) 中央ガードで前半後半が分かれる、
(c) 全体の向きが分からない(逆さ読みの判定が要る)、の 3 つが増える。
本 PoC の読取率を規格準拠リーダの性能として引用してはいけない。

【この PoC が測って分かったこと(数字はすべて実行時の実測値)】

1. ★**ゼロ点(1 本の走査線 + 固定しきい値 0.5 + run 数を 43 に要求)は、
   無傷なら 24/24 で読める**。対比の 4 つ(9 行多数決 / 9 行平均 /
   適応しきい値 / :func:`fullseye.ledger.measure_pos` のサブピクセルエッジ)も
   無傷では全部 24/24 —— **無傷で差は出ない**。差が出るのは壊してから。
2. ★★**「読めない」と言える実装かどうかが、誤読率を 2 桁変える。**
   run 数を 43 に要求する厳格デコーダはぼけでも汚れでも誤読を **1 % 未満**に
   抑え、失敗はほぼ全部「読み取り不能」になる。同じ画像を、走査線を
   70 等分してモジュール中心を読む**寛容デコーダ**(構造を検査せず必ず 9 桁
   返す)に通すと、**誤読が 32 % まで上がる**。読めないと言う口を持たない
   実装は、同じ入力で黙って違う数字を返す。
3. ★検査数字は誤読を**約 10 分の 1** にするが 0 にはしない(1/10 は偶然
   通る)。寛容デコーダの誤読 32.3 % → 3.5 %。**構造の検査(run 数)のほうが
   検査数字より効いている**。
4. ★★**傾きは「にじみ」ではなく「打ち切り」で死ぬ。** 1 本の走査線は
   傾いても幅が 1/cos 倍に伸びるだけで、桁ごとの正規化がそれを消す。
   壊れるのは**走査線が符号の上下からはみ出す**とき。限界は幾何だけで決まり
   θ_max = atan(バー高さ / 符号長) = atan(60/210) = 15.9 度。実測の崖は
   15 度(成功 24/24)と 16 度(0/24)のあいだ —— **予測の 1 度以内**。
   モジュール寸法にもぼけにも依らない。
5. ★★**汚れは大きいほうが安全**(非単調)。9 行多数決の成功率は
   汚れ 1 → 2 → 3 → 4 → 6 モジュールで 22 → 12 → 15 → 22 → 24 / 24。
   大きい汚れは走査線を**構造的に壊す**ので「読めない」と言えるが、
   小さい汚れは**読めてしまう**ので他の行と食い違う票を投じる。
6. ★★**ぼけと傾きは「モジュール 1 本あたりの実効ぼけ幅」に畳めるか** ——
   **ぼけは完全に畳める**。モジュール寸法 m = 2 / 3 / 4 px の 3 通りで、
   崖は σ/m = 0.7〜0.8 の**同じ位置**に来た。**傾きは畳みきれない**。
   帯平均のにじみを同じ標準偏差のガウスへ換算すると崖は σ_eq/m = 0.58〜0.74
   で、ぼけより **15 % 手前**。矩形とガウスは標準偏差を揃えても裾が違う。
7. 既存 op :func:`fullseye.op` の ``decode_barcode`` は **バーの本数を数える
   だけ**(docstring にもそう書いてある)。無傷で 22 本を正しく数え、
   ぼけ σ = 2.2 px で 21 本に落ちる —— 桁は返さないので、この PoC の
   デコーダの代わりにはならない。**在るものを測ってから**そう書いている。

来歴(公開文献のみ): Palmer, *The Bar Code Book*, 5th ed. (Trafford, 2007) ——
自己クロック符号と幅の正規化 / Joseph & Pavlidis, *IEEE TPAMI* 16 (1994) 630
—— ぼけたバーコードの波形解析 / ISO/IEC 15416 —— 印刷品質の等級付け
(本 PoC は等級付けを実装していない)。
"""
from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter1d, minimum_filter1d

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 符号の定義(自作。規格ではない)------------------------------------------ #
#: 数字 -> 4 本の run 幅(バー, 空白, バー, 空白)。合計は必ず 7 モジュール。
PATTERN = {0: (1, 1, 2, 3), 1: (1, 2, 2, 2), 2: (2, 2, 2, 1), 3: (1, 1, 3, 2),
           4: (1, 3, 1, 2), 5: (2, 1, 1, 3), 6: (1, 1, 1, 4), 7: (1, 3, 2, 1),
           8: (2, 1, 3, 1), 9: (3, 1, 1, 2)}
GUARD_START = (1, 1, 1, 1)     # バー,空白,バー,空白 —— 次の桁がバーで始まる
GUARD_END = (1, 1, 1)          # バー,空白,バー —— 右の白地と溶けない
N_DIGIT = 9                    # 本文 8 桁 + 検査数字 1 桁
N_RUN = len(GUARD_START) + 4 * N_DIGIT + len(GUARD_END)      # 43
N_MODULE = sum(GUARD_START) + 7 * N_DIGIT + sum(GUARD_END)   # 70

#: 幅の並びを実数ベクトルで持ったもの(最近傍分類に使う)
_PVEC = np.array([PATTERN[d] for d in range(10)], np.float64)


def _digit_bits(d: int) -> list[int]:
    """1 桁を 7 モジュールのビット列(1 = バー)に展開する。"""
    out: list[int] = []
    for j, w in enumerate(PATTERN[d]):
        out += [1 if j % 2 == 0 else 0] * w
    return out


_PBITS = np.array([_digit_bits(d) for d in range(10)], np.float64)

# --- 撮像の諸元 -------------------------------------------------------------- #
MODULE_PX = 3.0            # 1 モジュールの幅 [px]
BAR_H = 60                 # バーの高さ [px]
IMG_H = 90                 # 画像の高さ [px]
PAD = 26                   # 左右の静止帯 [px]
SS = 3                     # 描画のスーパーサンプル(1 画素を SS x SS)
TRIALS = 24                # 1 条件あたりの試行数
CENTER_ROW = IMG_H // 2
#: measure_pos に渡す平滑化 sigma の候補(1 つに決められなかった。9 章 (d))
CALIPER_SIGMAS = (0.4, 0.6, 0.8, 1.2)
VOTE_ROWS = np.linspace(CENTER_ROW - 24, CENTER_ROW + 24, 9).astype(int)
BAND_ROWS = np.arange(CENTER_ROW - 4, CENTER_ROW + 5)


def check_digit(body: list[int]) -> int:
    """自作の mod 10 検査数字(重み 3,1,3,1,...)。"""
    return (10 - sum(w * d for w, d in zip([3, 1] * 4, body)) % 10) % 10


def make_message(rng) -> tuple[int, ...]:
    """本文 8 桁を引いて検査数字を足した 9 桁。**これが真値**。"""
    body = [int(v) for v in rng.integers(0, 10, 8)]
    return tuple(body + [check_digit(body)])


def run_widths(digits) -> list[int]:
    """9 桁 -> 43 本の run 幅(モジュール単位)。"""
    w = list(GUARD_START)
    for d in digits:
        w += list(PATTERN[d])
    return w + list(GUARD_END)


# --------------------------------------------------------------------------- #
# 描画 —— 回転は解析的に(再標本化を通さないので幾何が厳密)                     #
# --------------------------------------------------------------------------- #
def render(digits, module_px=MODULE_PX, theta=0.0, phase=0.0,
           img_h=IMG_H, pad=PAD, bar_h=BAR_H) -> np.ndarray:
    """バーコードの画像(白 1.0 / バー 0.0、端は被覆率で反エイリアス)。

    ``theta`` は画像中心まわりの回転 [rad]、``phase`` は符号全体の
    サブピクセル横ずれ [px]。**位相を振らないと**モジュール境界が画素境界に
    張り付いて、実機ではありえないほど良い成績が出る。
    """
    widths = run_widths(digits)
    span = sum(widths) * module_px
    img_w = int(round(span + 2 * pad))
    bounds = np.cumsum([0] + widths) * module_px
    ii, jj = np.mgrid[0:img_h, 0:img_w].astype(np.float64)
    cy, cx = (img_h - 1) / 2.0, (img_w - 1) / 2.0
    off = np.linspace(-0.5 + 0.5 / SS, 0.5 - 0.5 / SS, SS)
    ct, st = np.cos(theta), np.sin(theta)
    acc = np.zeros((img_h, img_w), np.float64)
    for dy in off:
        for dx in off:
            y, x = ii + dy - cy, jj + dx - cx
            u = x * ct + y * st + span / 2.0 + phase
            v = -x * st + y * ct
            inside = (np.abs(v) <= bar_h / 2.0) & (u >= 0) & (u < span)
            k = np.clip(np.searchsorted(bounds, u, "right") - 1, 0, len(widths) - 1)
            acc += np.where(inside & (k % 2 == 0), 0.0, 1.0)
    return acc / (SS * SS)


# --------------------------------------------------------------------------- #
# デコーダ —— 厳格(run 数を検査)と寛容(検査しない)                          #
# --------------------------------------------------------------------------- #
def decode_runs(lens) -> tuple | None:
    """43 本の run 幅 -> 9 桁。**本数が合わなければ ``None``**(= 読み取り不能)。"""
    lens = np.asarray(lens, np.float64)
    if lens.size != N_RUN:
        return None
    body = lens[len(GUARD_START):len(GUARD_START) + 4 * N_DIGIT]
    out = []
    for g in range(N_DIGIT):
        seg = body[4 * g:4 * g + 4]
        s = float(seg.sum())
        if s <= 0.0:
            return None
        # 桁の中で合計 7 に正規化する = 自己クロック(拡大率と 1/cos が消える)
        nw = 7.0 * seg / s
        out.append(int(np.argmin(np.abs(_PVEC - nw).sum(1))))
    return tuple(out)


def _runs_from_mask(dark: np.ndarray):
    """2 値プロファイル -> run 長。最初が暗でなければ ``None``。"""
    idx = np.flatnonzero(np.diff(dark.astype(np.int8)) != 0)
    if idx.size < 2 or not dark[idx[0] + 1]:
        return None
    return np.diff(idx + 0.5)


def decode_strict(prof: np.ndarray, thr: float = 0.5) -> tuple | None:
    """★ゼロ点のデコーダ: 固定しきい値 -> run 長 -> 43 本を要求。"""
    lens = _runs_from_mask(prof < thr)
    return None if lens is None else decode_runs(lens)


def decode_lenient(prof: np.ndarray, thr: float = 0.5) -> tuple | None:
    """**構造を検査しない**デコーダ: 暗い範囲を 70 等分してモジュール中心を読む。

    run 数を見ないので、壊れていても必ず 9 桁を返す —— つまり
    「読めません」と言う口を持たない。2 章の対比はこれ。
    """
    dark = prof < thr
    nz = np.flatnonzero(dark)
    if nz.size < 10:
        return None
    a, b = nz[0] - 0.5, nz[-1] + 0.5
    cen = a + (np.arange(N_MODULE) + 0.5) * (b - a) / N_MODULE
    bits = (np.interp(cen, np.arange(prof.size), prof) < thr).astype(np.float64)
    body = bits[len(GUARD_START):len(GUARD_START) + 7 * N_DIGIT]
    return tuple(int(np.argmin(np.abs(_PBITS - body[7 * g:7 * g + 7]).sum(1)))
                 for g in range(N_DIGIT))


# --------------------------------------------------------------------------- #
# 走査の取り方(手法)                                                          #
# --------------------------------------------------------------------------- #
def m0_single(img):
    """★ゼロ点 —— 中央 1 行 + 固定しきい値 0.5。"""
    return decode_strict(img[CENTER_ROW])


def m1_vote(img):
    """9 行を**独立に**復号して多数決(最頻の結果を返す)。"""
    got = [decode_strict(img[r]) for r in VOTE_ROWS]
    cnt = Counter(g for g in got if g is not None)
    return cnt.most_common(1)[0][0] if cnt else None


def m2_band(img):
    """9 行を**平均**してから 1 本のプロファイルとして読む(行ビニング)。"""
    return decode_strict(img[BAND_ROWS].mean(axis=0))


def m3_adaptive(img):
    """中央 1 行 + 局所しきい値(Bernsen: 窓 8 モジュールの最大最小の中点)。

    ★**対比の門が要る**: 局所平均だけで切ると、白しかない静止帯でしきい値が
    その白の平均に来るので、雑音の半分が「暗」に化けて run が増える
    (最初にそう書いて、雑音のある条件が全滅した)。窓の中の振れ幅が
    画像全体の振れ幅の 35 % を切ったら「ここには構造が無い」と見なす。
    """
    prof = img[CENTER_ROW]
    win = int(round(8 * MODULE_PX))
    lo = minimum_filter1d(prof, win, mode="nearest")
    hi = maximum_filter1d(prof, win, mode="nearest")
    swing = float(np.percentile(prof, 98) - np.percentile(prof, 2))
    dark = (prof < 0.5 * (lo + hi)) & ((hi - lo) > 0.35 * swing)
    lens = _runs_from_mask(dark)
    return None if lens is None else decode_runs(lens)


def m4_subpixel(img):
    """中央 1 行 + :func:`fullseye.ledger.measure_pos` のサブピクセルエッジ。

    微分の極大をサブピクセルへ精緻化した位置を run の境界に使う。
    振幅のしきい値は**行のコントラストに比例**させる(固定値だと
    低コントラストの条件でエッジを全部落としてしまう)。

    ★``sigma`` を 1 つに決められなかった。1 モジュール 3 px の周期構造では
    エッジ**本数**が sigma に非単調に依存する(9 章 (d) に実測表)ので、
    0.4 / 0.6 / 0.8 / 1.2 を順に試して **44 本ちょうど**になった最初のものを
    採る。どれも本数が合わなければ「読めません」と答える。
    """
    h, w = img.shape
    prof = img[CENTER_ROW]
    rng_amp = float(np.percentile(prof, 95) - np.percentile(prof, 5))
    handle = fs.ledger.gen_measure_rectangle2(float(CENTER_ROW), (w - 1) / 2.0,
                                              0.0, (w - 1) / 2.0, 1, (h, w))
    for sigma in CALIPER_SIGMAS:
        edges = fs.ledger.measure_pos(img, handle, sigma=sigma,
                                      threshold=max(0.25 * rng_amp, 0.03))
        if len(edges) == N_RUN + 1 and edges[0]["polarity"] == "negative":
            pos = np.array([e["pos"] for e in edges], np.float64)
            return decode_runs(np.diff(pos))
    return None


def m5_lenient(img):
    """ゼロ点と同じ二値化のまま、**デコーダだけ寛容**にしたもの。"""
    return decode_lenient(img[CENTER_ROW])


METHODS = [("ゼロ点(1行)", m0_single), ("9行多数決", m1_vote),
           ("9行平均", m2_band), ("適応しきい", m3_adaptive),
           ("サブピクセル", m4_subpixel)]


# --------------------------------------------------------------------------- #
# 壊し方                                                                       #
# --------------------------------------------------------------------------- #
def dmg_blur(img, level, rng, digits):
    """(a) ぼけ —— 等方ガウス、σ [px]。"""
    return img if level <= 0 else gaussian_filter(img, level)


def dmg_contrast(img, level, rng, digits):
    """(c) コントラスト低下 + 明るさの持ち上がり + 雑音(1 つのつまみ)。

    ★3 つを**同時に**動かす。どれが効いているかは 8 章の対照群で分ける。
    """
    amp, ctr = 1.0 - 0.6 * level, 0.5 + 0.35 * level
    out = ctr + (img - 0.5) * amp
    return np.clip(out + rng.normal(0.0, 0.05 * level, img.shape), 0.0, 1.0)


def dmg_smudge(img, level, rng, digits):
    """(d) 汚れ —— 幅 ``level`` モジュール、バー高さの上から 6 割を黒く塗る。

    **中央の走査線は必ず含む**(含まないと汚れの有無が試行ごとにばらつく)。
    """
    if level <= 0:
        return img
    out = img.copy()
    h, w = img.shape
    x0 = PAD + float(rng.uniform(0, max(N_MODULE - level, 1))) * MODULE_PX
    r1 = (h - BAR_H) // 2
    r2 = r1 + int(BAR_H * 0.6)
    assert r1 <= CENTER_ROW < r2, "中央行が汚れの外にある"
    out[r1:r2, int(x0):int(x0 + level * MODULE_PX)] = 0.0
    return out


def _render_tilt(digits, level, rng):
    return render(digits, theta=np.deg2rad(level), phase=rng.uniform(0, MODULE_PX))


DAMAGES = [
    ("(a) ぼけ σ px", [0.0, 1.0, 1.8, 2.1, 2.3, 2.6], dmg_blur, None),
    ("(b) 傾き 度", [0.0, 8.0, 14.0, 15.0, 16.0, 20.0], None, _render_tilt),
    ("(c) 低コントラスト+雑音", [0.0, 0.3, 0.5, 0.65, 0.75, 0.95], dmg_contrast, None),
    ("(d) 汚れ モジュール", [0, 1, 2, 3, 4, 6], dmg_smudge, None),
]


def make_case(digits, damage, level, rng):
    """1 枚の観測画像を作る。傾きだけは描画の段で入る。"""
    _, _, post, custom = damage
    if custom is not None:
        return custom(digits, level, rng)
    img = render(digits, phase=rng.uniform(0, MODULE_PX))
    return post(img, level, rng, digits)


def tally(decoded, truth, use_check: bool) -> str:
    """1 枚の結果を 3 通りに分ける。★ここを 1 つの率に畳まない。"""
    if decoded is None:
        return "unread"
    if use_check and check_digit(list(decoded[:8])) != decoded[8]:
        return "unread"          # 検査数字が合わない = 読めなかった、と申告する
    return "ok" if tuple(decoded) == tuple(truth) else "misread"


# =========================================================================== #
def section1_code() -> None:
    print("=" * 78)
    print("1) 符号の定義と検算(自作の簡易符号。EAN-13 準拠ではない)")
    print("=" * 78)
    print("  1 桁 = 4 run(バー,空白,バー,空白)/ 合計 7 モジュール")
    print("  並び = ガード %s + 8 桁 + 検査数字 + ガード %s"
          % (GUARD_START, GUARD_END))
    print("  合計 %d モジュール / %d run / バー %d 本 / モジュール %.1f px"
          % (N_MODULE, N_RUN, (N_RUN + 1) // 2, MODULE_PX))
    widths = np.array([PATTERN[d] for d in range(10)])
    assert widths.sum(1).tolist() == [7] * 10
    dmin = min(np.abs(widths[i] - widths[j]).sum()
               for i in range(10) for j in range(i + 1, 10))
    print("  符号表の最小 L1 距離: %d モジュール(1 本の幅が %d 動くと隣の数字になる)"
          % (dmin, dmin))
    rng = np.random.default_rng(0)
    msg = make_message(rng)
    img = render(msg)
    print("  検算: 無傷の 1 枚 %s -> %s" % (str(msg), str(decode_strict(img[CENTER_ROW]))))
    assert decode_strict(img[CENTER_ROW]) == msg, "無傷で読めない(符号の定義が壊れている)"
    print("  画像 %s / 白 %.2f / バー %.2f" % (img.shape, img.max(), img.min()))

    # 既存 op を先に測る —— 「無い」と書く前に。
    bars = float(fs.op.decode_barcode(img, a=0.5, b=0.0))
    print()
    print("  ★既存 op `fs.op.decode_barcode` を先に測る: %d 本(真値 %d 本)。"
          % (bars, (N_RUN + 1) // 2))
    print("    %s" % ("本数は正しい。" if bars == (N_RUN + 1) // 2 else "★本数が違う。"))
    for sg in (1.0, 2.0, 2.2, 2.6):
        b = float(fs.op.decode_barcode(gaussian_filter(img, sg), a=0.5, b=0.0))
        print("      ぼけ σ=%.1f -> %d 本" % (sg, b))
    print("    docstring どおり**本数を数えるだけ**で桁は返さない。以降は自前。")


def section2_zero_point() -> dict:
    print()
    print("=" * 78)
    print("2) ★ゼロ点と 4 つの対比 —— まず無傷で並べる")
    print("=" * 78)
    rng = np.random.default_rng(1)
    cases = []
    for _ in range(TRIALS):
        msg = make_message(rng)
        cases.append((msg, render(msg, phase=rng.uniform(0, MODULE_PX))))
    print("  無傷 %d 枚(符号もサブピクセル位相も毎回引き直す):" % TRIALS)
    print()
    print("  %-16s %8s %8s %8s" % ("手法", "成功", "誤読", "読取不能"))
    print("  " + "-" * 44)
    for name, fn in METHODS + [("寛容デコーダ", m5_lenient)]:
        c = Counter(tally(fn(img), msg, False) for msg, img in cases)
        print("  %-16s %8d %8d %8d" % (name, c["ok"], c["misread"], c["unread"]))
    print()
    print("  → **無傷では 6 つとも全部読める。差は出ない。**")
    print("     道具の良し悪しは、壊してからしか分からない。")
    return {"cases": cases}


def section3_sweeps() -> dict:
    print()
    print("=" * 78)
    print("3) ★4 つの壊し方 × 5 つの手法 —— 成功率(%d 枚中)" % TRIALS)
    print("=" * 78)
    out = {}
    for dname, levels, post, custom in DAMAGES:
        dmg = (dname, levels, post, custom)
        print()
        print("  %s" % dname)
        print("  %10s |" % "水準", end="")
        for name, _ in METHODS:
            print(" %13s" % name, end="")
        print()
        print("  " + "-" * (12 + 14 * len(METHODS)))
        table = {name: [] for name, _ in METHODS}
        for lv in levels:
            rng = np.random.default_rng(100 + int(lv * 17))
            imgs = []
            for _ in range(TRIALS):
                msg = make_message(rng)
                imgs.append((msg, make_case(msg, dmg, lv, rng)))
            print("  %10s |" % ("%g" % lv), end="")
            for name, fn in METHODS:
                ok = sum(tally(fn(img), msg, False) == "ok" for msg, img in imgs)
                table[name].append(ok)
                print(" %13s" % ("%d/%d" % (ok, TRIALS)), end="")
            print()
        out[dname] = {"levels": levels, "table": table}
    print()
    print("  → 壊し方ごとに勝つ手法が違う。**どれか 1 つを既定にしてはいけない**。")
    print("     ・ぼけ: 固定しきい値の 3 つが σ=2.1 px まで持ち、★適応しきい値と")
    print("       サブピクセルのほうが**先に**(1.8 px で)落ちる。局所の差を見る")
    print("       方式は、なまると差そのものが消えるので早く死ぬ。")
    print("     ・傾き: 5 つとも同じ 16 度で落ちる —— 二値化の問題ではない(5 章)。")
    print("     ・低コントラスト: 固定しきい値の 3 つだけが落ちる。適応しきい値と")
    print("       サブピクセルは最後まで残る(原因の切り分けは 8 章)。")
    print("     ・汚れ: 多数決だけが残る。他は中央の 1 行が汚れの中にあるので同じ")
    print("       ように落ちる(6 章で非単調になる理由まで見る)。")
    return out


def section4_misread() -> dict:
    print()
    print("=" * 78)
    print("4) ★★誤読と読み取り不能を分けて数える —— 厳格 / 寛容 / 検査数字")
    print("=" * 78)
    print("  同じ画像・同じ二値化で、**デコーダの厳しさだけ**を変える。")
    print("  厳格 = run 数が %d 本でなければ「読めません」と言う。" % N_RUN)
    print("  寛容 = 走査線を %d 等分してモジュール中心を読む(必ず 9 桁返す)。"
          % N_MODULE)
    print()
    print("  %-22s %7s %7s %7s | %7s %7s %7s"
          % ("条件", "厳格 ok", "誤読", "不能", "寛容 ok", "誤読", "不能"))
    print("  " + "-" * 74)
    tot = {"strict": Counter(), "lenient": Counter(), "lenient_chk": Counter()}
    rows = []
    for dname, levels, post, custom in DAMAGES:
        dmg = (dname, levels, post, custom)
        for lv in levels[2:]:                      # 壊れ始めてからの水準だけ
            rng = np.random.default_rng(200 + int(lv * 31))
            cs, cl, cc = Counter(), Counter(), Counter()
            for _ in range(TRIALS):
                msg = make_message(rng)
                img = make_case(msg, dmg, lv, rng)
                cs[tally(m0_single(img), msg, False)] += 1
                cl[tally(m5_lenient(img), msg, False)] += 1
                cc[tally(m5_lenient(img), msg, True)] += 1
            for key, c in (("strict", cs), ("lenient", cl), ("lenient_chk", cc)):
                tot[key] += c
            rows.append(["%s %g" % (dname.split()[0], lv),
                         "%d" % cs["ok"], "%d" % cs["misread"], "%d" % cs["unread"],
                         "%d" % cl["ok"], "%d" % cl["misread"], "%d" % cl["unread"]])
            print("  %-22s %7d %7d %7d | %7d %7d %7d"
                  % ("%s %g" % (dname.split()[0], lv), cs["ok"], cs["misread"],
                     cs["unread"], cl["ok"], cl["misread"], cl["unread"]))
    n = sum(tot["strict"].values())
    print("  " + "-" * 74)
    print("  %-22s %7d %7d %7d | %7d %7d %7d"
          % ("合計 (%d 枚)" % n, tot["strict"]["ok"], tot["strict"]["misread"],
             tot["strict"]["unread"], tot["lenient"]["ok"],
             tot["lenient"]["misread"], tot["lenient"]["unread"]))
    print()
    print("  誤読率: 厳格 %.1f %% / 寛容 %.1f %% / 寛容+検査数字 %.1f %%"
          % (100 * tot["strict"]["misread"] / n, 100 * tot["lenient"]["misread"] / n,
             100 * tot["lenient_chk"]["misread"] / n))
    print("  成功率: 厳格 %.1f %% / 寛容 %.1f %% / 寛容+検査数字 %.1f %%"
          % (100 * tot["strict"]["ok"] / n, 100 * tot["lenient"]["ok"] / n,
             100 * tot["lenient_chk"]["ok"] / n))
    print()
    print("  → ★★寛容デコーダは**成功率も高い**(壊れかけでも当たることがある)。")
    print("     読取率だけを見ると寛容のほうが良い道具に見える。**内訳を分けて")
    print("     数えないと、誤読を成功として買ってしまう**。")
    print("  → ★検査数字は寛容の誤読を %.1f %% -> %.1f %%(約 %.0f 分の 1)に"
          % (100 * tot["lenient"]["misread"] / n,
             100 * tot["lenient_chk"]["misread"] / n,
             tot["lenient"]["misread"] / max(tot["lenient_chk"]["misread"], 1)))
    print("     するが 0 にはしない —— 10 桁のうち 1 つは偶然通る。")
    print("     **構造の検査(run 数)のほうが検査数字より強い**。桁だけを守る")
    print("     符号より、読めないと言える読み方のほうが効く。")
    figs.save_table("misread_split",
                    ["条件", "厳格 成功", "厳格 誤読", "厳格 不能",
                     "寛容 成功", "寛容 誤読", "寛容 不能"],
                    rows + [["合計 %d 枚" % n, "%d" % tot["strict"]["ok"],
                             "%d" % tot["strict"]["misread"],
                             "%d" % tot["strict"]["unread"],
                             "%d" % tot["lenient"]["ok"],
                             "%d" % tot["lenient"]["misread"],
                             "%d" % tot["lenient"]["unread"]]],
                    title="誤読と読み取り不能を分けて数える(1 条件 %d 枚)" % TRIALS,
                    caption="同じ画像・同じ二値化で、run 数を検査するかどうかだけが違う。")
    return tot


def section5_tilt() -> None:
    print()
    print("=" * 78)
    print("5) ★★傾きは「にじみ」ではなく「打ち切り」で死ぬ")
    print("=" * 78)
    lim = np.degrees(np.arctan(BAR_H / (N_MODULE * MODULE_PX)))
    print("  1 本の走査線は、傾いても run 幅が 1/cos 倍に伸びるだけ —— 桁ごとの")
    print("  正規化がそれを消す。壊れるのは走査線が符号の**上下からはみ出す**とき。")
    print("  予測: θ_max = atan(バー高 %d / 符号長 %.0f) = **%.2f 度**"
          % (BAR_H, N_MODULE * MODULE_PX, lim))
    print()
    print("  %8s | %10s %10s %10s" % ("角度 度", "1/cos", "ゼロ点", "9行多数決"))
    print("  " + "-" * 44)
    for th in [10.0, 14.0, 15.0, 15.5, 16.0, 18.0]:
        rng = np.random.default_rng(300 + int(th * 7))
        ok0 = ok1 = 0
        for _ in range(TRIALS):
            msg = make_message(rng)
            img = _render_tilt(msg, th, rng)
            ok0 += m0_single(img) == msg
            ok1 += m1_vote(img) == msg
        print("  %8.1f | %10.4f %10s %10s"
              % (th, 1 / np.cos(np.deg2rad(th)), "%d/%d" % (ok0, TRIALS),
                 "%d/%d" % (ok1, TRIALS)))
    print()
    print("  → 崖は 15.0 度(全数成功)と 16.0 度(全数失敗)のあいだ。予測 %.2f 度。"
          % lim)
    print("     ★この限界は**モジュール寸法にもぼけにも雑音にも依らない**。")
    print("     符号の縦横比だけで決まる。バーを高くすれば線形に伸びる。")
    print("     9 行多数決も同じ角度で落ちる —— どの行も同じ幾何で切れるから。")


def section6_smudge() -> None:
    print()
    print("=" * 78)
    print("6) ★★汚れは大きいほうが安全 —— 成功率が非単調になる")
    print("=" * 78)
    print("  汚れはバー高さの上 6 割を黒く塗る(中央の走査線は必ず中)。")
    print("  9 行のうち下側の %d 行は汚れの外に出る。"
          % int(np.sum(VOTE_ROWS >= (IMG_H - BAR_H) // 2 + int(BAR_H * 0.6))))
    print()
    print("  %10s | %10s %10s %10s %10s"
          % ("汚れ mod", "ゼロ点", "多数決 ok", "多数決 誤読", "多数決 不能"))
    print("  " + "-" * 56)
    xs, ys = [], []
    for nm in [0, 1, 2, 3, 4, 6, 8]:
        rng = np.random.default_rng(400 + nm)
        ok0 = 0
        c = Counter()
        for _ in range(TRIALS):
            msg = make_message(rng)
            img = dmg_smudge(render(msg, phase=rng.uniform(0, MODULE_PX)),
                             nm, rng, msg)
            ok0 += m0_single(img) == msg
            c[tally(m1_vote(img), msg, False)] += 1
        xs.append(nm)
        ys.append(c["ok"])
        print("  %10d | %10s %10d %10d %10d"
              % (nm, "%d/%d" % (ok0, TRIALS), c["ok"], c["misread"], c["unread"]))
    print()
    print("  → 多数決の成功率が**いったん下がってから上がる**。")
    print("     大きい汚れは走査線を構造的に壊すので、汚れた行は「読めません」と")
    print("     答える —— 票を投じない。**きれいな行だけが投票する**ので多数決が")
    print("     効く。小さい汚れは**読めてしまう**ので、間違った票が入る。")
    print("     ★「軽い損傷のほうが危ない」は直感に反するが、投票で決める系では")
    print("     いつもこうなる(棄権できない誤りが多数派を作る)。")
    figs.save_plot("smudge_nonmonotone",
                   [("9行多数決 成功数", np.array(xs, float), np.array(ys, float)),
                    ("試行数", np.array(xs, float), np.full(len(xs), TRIALS, float))],
                   xlabel="汚れの幅 [モジュール]", ylabel="成功枚数 / %d" % TRIALS,
                   title="汚れは大きいほうが安全(非単調)",
                   caption="小さい汚れは行が「読めてしまう」ので誤った票を投じる。"
                           "大きい汚れは棄権するので多数決が効く。")


def section7_collapse() -> None:
    print()
    print("=" * 78)
    print("7) ★★ぼけと傾きは「モジュール 1 本あたりの実効ぼけ」に畳めるか")
    print("=" * 78)
    print("  仮説: どちらも run の境界をなまらせるだけなら、**σ/m の 1 本の曲線**に")
    print("  乗るはず。傾きのにじみは、帯 %d 行を平均したときの矩形の幅" % 31)
    print("  %d·tanθ [px]。同じ**標準偏差**のガウスへ直すと σ_eq = 幅/√12。" % 31)
    print()
    print("  (i) ぼけ: モジュール寸法 m を変えても σ/m の同じ場所で落ちるか")
    print()
    print("  %8s |" % "σ/m", end="")
    es = [0.60, 0.68, 0.71, 0.74, 0.77, 0.85]
    for e in es:
        print(" %7.2f" % e, end="")
    print()
    print("  " + "-" * (10 + 8 * len(es)))
    curves = {}
    for m in (2.0, 3.0, 4.0):
        vals = []
        print("  %8s |" % ("m=%.0f px" % m), end="")
        for e in es:
            rng = np.random.default_rng(500 + int(m * 100 + e * 1000))
            ok = 0
            for _ in range(TRIALS):
                msg = make_message(rng)
                img = gaussian_filter(render(msg, module_px=m,
                                             phase=rng.uniform(0, m)), e * m)
                ok += m0_single(img) == msg
            vals.append(ok / TRIALS)
            print(" %7s" % ("%d/%d" % (ok, TRIALS)), end="")
        print()
        curves["ぼけ m=%.0f" % m] = np.array(vals)

    print()
    print("  (ii) 傾き: 打ち切りが効かないように**バーを高くして**帯平均で読む")
    print()
    band = 31
    tall = dict(img_h=340, pad=70, bar_h=220)
    lim = np.degrees(np.arctan(tall["bar_h"] / (N_MODULE * MODULE_PX)))
    print("      バー高 %d / 符号長 %.0f -> 打ち切り限界 %.1f 度(掃引はその手前)"
          % (tall["bar_h"], N_MODULE * MODULE_PX, lim))
    print("  %8s | %9s %9s %9s" % ("角度 度", "にじみ px", "σ_eq/m", "成功"))
    print("  " + "-" * 42)
    tilt_e, tilt_ok = [], []
    for th in [5.0, 9.0, 10.0, 10.5, 11.0, 12.0]:
        smear = band * np.tan(np.deg2rad(th))
        e = smear / np.sqrt(12.0) / MODULE_PX
        rng = np.random.default_rng(600 + int(th * 13))
        ok = 0
        for _ in range(TRIALS):
            msg = make_message(rng)
            img = render(msg, theta=np.deg2rad(th),
                         phase=rng.uniform(0, MODULE_PX), **tall)
            c = img.shape[0] // 2
            ok += decode_strict(img[c - band // 2:c + band // 2 + 1].mean(0)) == msg
        tilt_e.append(e)
        tilt_ok.append(ok / TRIALS)
        print("  %8.1f | %9.2f %9.3f %9s"
              % (th, smear, e, "%d/%d" % (ok, TRIALS)))

    def _cliff(x, y):
        """成功率が 0.5 を切る位置を線形に内挿する。"""
        x, y = np.asarray(x, float), np.asarray(y, float)
        for i in range(len(y) - 1):
            if y[i] >= 0.5 > y[i + 1]:
                t = (y[i] - 0.5) / (y[i] - y[i + 1])
                return x[i] + t * (x[i + 1] - x[i])
        return float("nan")

    print()
    print("  50 % を切る位置(内挿):")
    for k, v in curves.items():
        print("    %-12s σ/m = %.3f" % (k, _cliff(es, v)))
    tc = _cliff(tilt_e, tilt_ok)
    print("    %-12s σ_eq/m = %.3f" % ("傾き", tc))
    bs = [_cliff(es, v) for v in curves.values()]
    print()
    print("  → ★★**ぼけは完全に畳める**: m = 2/3/4 px で崖が %.3f / %.3f / %.3f"
          % tuple(bs))
    print("     —— 3 つとも同じ。ぼけの効き目は σ/m だけで決まる。")
    print("  → ★**傾きは畳みきれない**: σ_eq/m = %.3f で、ぼけより %.0f %% 手前。"
          % (tc, 100 * (1 - tc / np.mean(bs))))
    print("     標準偏差を揃えても、矩形の裾はガウスと違う(矩形は端で急に切れる)。")
    print("     **同じ 1 本の軸に乗る、と言えるのは 2 割の精度まで**。")
    print("     半値幅で揃えると σ_eq/m = %.3f になり、もっと外れる。"
          % (band * np.tan(np.deg2rad(13.0)) / 2.355 / MODULE_PX))
    if figs.enabled():
        series = [(k, np.array(es), v) for k, v in curves.items()]
        series.append(("傾き(σ_eq)", np.array(tilt_e), np.array(tilt_ok)))
        figs.save_plot("collapse", series,
                       xlabel="モジュール 1 本あたりの実効ぼけ σ/m",
                       ylabel="成功率", title="ぼけと傾きは同じ軸に畳めるか",
                       caption="ぼけ 3 本(m=2,3,4 px)は 1 本に重なる。"
                               "傾きを同じ標準偏差へ換算した曲線は 2 割手前で落ちる。")


def section8_controls() -> None:
    print()
    print("=" * 78)
    print("8) 対照群 —— 低コントラストの何が効いているのか")
    print("=" * 78)
    print("  3 章の (c) は**コントラスト・明るさ・雑音を同時に**動かしている。")
    print("  水準 0.75 で 1 つずつ止めて、原因を分ける。")
    print()
    lv = 0.75
    variants = [("3 つとも", True, True, True), ("コントラストのみ", True, False, False),
                ("明るさのみ", False, True, False), ("雑音のみ", False, False, True)]
    print("  %-16s | %10s %10s %10s"
          % ("止めない要素", "ゼロ点", "適応しきい", "サブピクセル"))
    print("  " + "-" * 54)
    for name, use_amp, use_ctr, use_noise in variants:
        rng = np.random.default_rng(700)
        ok = [0, 0, 0]
        for _ in range(TRIALS):
            msg = make_message(rng)
            img = render(msg, phase=rng.uniform(0, MODULE_PX))
            amp = 1.0 - 0.6 * lv if use_amp else 1.0
            ctr = 0.5 + 0.35 * lv if use_ctr else 0.5
            out = ctr + (img - 0.5) * amp
            if use_noise:
                out = out + rng.normal(0.0, 0.05 * lv, img.shape)
            out = np.clip(out, 0.0, 1.0)
            for i, fn in enumerate((m0_single, m3_adaptive, m4_subpixel)):
                ok[i] += fn(out) == msg
        print("  %-16s | %10s %10s %10s"
              % (name, *["%d/%d" % (v, TRIALS) for v in ok]))
    print()
    print("  → ★効いているのは**明るさの持ち上がり**で、コントラスト低下でも")
    print("     雑音でもない。固定しきい値 0.5 が符号の外へ出るから落ちる。")
    print("     適応しきい値とサブピクセルは明るさに触られても平気 —— どちらも")
    print("     **絶対値でなく局所の差**を見ているから。")
    print("     3 つ同時の水準だけを見て「低コントラストに弱い」と書くと、")
    print("     直しどころ(しきい値の決め方)を外す。")


def section9_figures() -> None:
    if not figs.enabled():
        return
    rng = np.random.default_rng(2)
    msg = make_message(rng)
    clean = render(msg, phase=0.4)
    blurred = gaussian_filter(clean, 2.3)
    smudged = dmg_smudge(clean, 3, np.random.default_rng(7), msg)
    tilted = render(msg, theta=np.deg2rad(16.0), phase=0.4)
    figs.save_grid("barcode_damage", [clean, blurred, smudged, tilted],
                   ["(a) 無傷", "(b) ぼけ 2.3", "(c) 汚れ 3", "(d) 傾き 16 度"],
                   ncols=2, title="4 つの壊し方(モジュール %.0f px)" % MODULE_PX,
                   caption="(d) は走査線が符号の上下からはみ出す角度。"
                           "にじんでいないのに読めない。")


def section10_tool_gaps() -> None:
    print()
    print("=" * 78)
    print("9) 道具の穴(1-D 符号を読むのに使ってみて)")
    print("=" * 78)

    # (a) 桁を返すデコーダは無い。在るのは本数を数える op だけ(測って確認済み)。
    assert not hasattr(fs, "decode_barcode") and not hasattr(fs.ledger, "decode_barcode")
    assert "decode_barcode" in [r["op"] for r in fs.op_find("barcode")]
    print("  (a) `decode_barcode` は**進化 op(fs.op)にだけ**在り、ファサードにも")
    print("      台帳にも無い。しかも中身は 1 章で測ったとおり**バーの本数**で、")
    print("      桁は返さない(docstring は正直に書いてある)。1-D 符号を")
    print("      「読む」口はこの repo に無い。")

    # (b) 1-D の run 長を出す op が無い(3-D の RLE はある)。
    assert hasattr(fs, "vol_rle_encode")
    for nm in ("rle_encode", "run_lengths", "runlength_encode"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    print("  (b) **1-D の run 長符号化が無い**。3-D voxel の `vol_rle_encode` は")
    print("      在るのに、プロファイル 1 本を run に割る口が無い(自前 3 行)。")
    print("      run 長は 1-D 符号・欠陥検査・テクスチャの共通部品なので、")
    print("      `r2_runlength_features` が内部で数えているものを外に出すだけでよい。")

    # (c) 1-D の適応しきい値が無い。2-D の局所しきい値は窓が画素で固定
    #     (これは poc_matrix_code_reading が先に指摘した穴。ここでは再掲のみ)。
    for nm in ("local_threshold_1d", "adaptive_threshold_1d"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    print("  (c) 1-D プロファイル向けの適応しきい値が無い(2-D の局所しきい値は")
    print("      窓が画素で固定という別の穴を `poc_matrix_code_reading` が既に")
    print("      指摘している)。本 PoC の Bernsen は scipy の順位フィルタから")
    print("      手で組んでいる —— **対比の門**まで含めて毎回書き直すことになる。")

    # (d) ★measure_pos のエッジ本数が sigma に**非単調**に依存する。
    prof_img = render(make_message(np.random.default_rng(1)),
                      phase=float(np.random.default_rng(1).uniform(0, MODULE_PX)))
    h, w = prof_img.shape
    hd = fs.ledger.gen_measure_rectangle2(float(CENTER_ROW), (w - 1) / 2.0, 0.0,
                                          (w - 1) / 2.0, 1, (h, w))
    counts = [(sg, len(fs.ledger.measure_pos(prof_img, hd, sigma=sg, threshold=0.03)))
              for sg in (0.0, 0.3, 0.4, 0.6, 0.8, 1.0, 1.5)]
    got = dict(counts)
    assert got[0.0] == 0 and got[1.0] != N_RUN + 1 and got[0.6] == N_RUN + 1, counts
    print("  (d) ★**`measure_pos` のエッジ本数が sigma に非単調に依存する**。")
    print("      同じ無傷の 1 枚(真値 %d 本)で: %s"
          % (N_RUN + 1, " / ".join("σ=%.1f→%d 本" % c for c in counts)))
    print("      σ=0 で **0 本**(平滑無しだと勾配の台地が厳密な極大にならない)、")
    print("      σ=1.0 で 11 本落ちる。1 モジュール 3 px の周期構造では隣の")
    print("      勾配ローブが重なり、どちらか一方が極大でなくなる —— どの σ が")
    print("      当たるかは**サブピクセル位相しだい**。だから手法 5 は σ を")
    print("      %s の順に試している。例外は出ず、本数が静かに減る。"
          % str(CALIPER_SIGMAS))

    # (e) polarity の表現が 2 通りある(文字列 と ±1)。
    e2 = fs.ledger.measure_pos(prof_img, hd, sigma=0.6, threshold=0.2)
    assert isinstance(e2[0]["polarity"], str), e2[0]
    vol = np.repeat(prof_img[None], 4, axis=0)
    e3 = fs.vol_edge_probe(vol, (0, CENTER_ROW, 0), (0, CENTER_ROW, w - 1),
                           sigma=1.0, threshold=0.2)
    assert e3 and not isinstance(e3[0]["polarity"], str), e3[0] if e3 else e3
    print("  (e) **同じ「極性」が 2 つの型で返る**: `measure_pos` は文字列")
    print("      (\"positive\"/\"negative\")、`vol_edge_probe` は ±1 の数値。")
    print("      どちらも 3 点放物線のサブピクセルエッジで、中身は同じ概念。")
    print("      呼び分ける側が毎回変換する。")

    # (f) 成功 / 誤読 / 読み取り不能 を分けて数える枠組みが無い。
    for nm in ("classification_report", "confusion_counts", "decode_report"):
        assert not hasattr(fs, nm) and not hasattr(fs.ledger, nm), nm
    print("  (f) 「成功 / 誤読 / 読み取り不能」のような**3 通りの採点**を集計する")
    print("      口が無い。この repo の PoC が繰り返し必要としている型なのに、")
    print("      毎回 Counter を手で書いている(4 章がまさにそれ)。")

    # (g) 在って助かったもの
    assert hasattr(fs.ledger, "gen_measure_rectangle2") and hasattr(fs.ledger, "measure_pos")
    print("  (g) 在って助かった: `gen_measure_rectangle2` + `measure_pos`。")
    print("      サブピクセルのエッジ位置が 1 行で取れるので、手法 5 は")
    print("      **自前の微分も零交差も書かずに**組めた((d) の σ 探索を除けば)。")
    print("      3 章のとおり低コントラストに最も強い(勾配だけを見ているから)。")


def main() -> None:
    t0 = time.perf_counter()
    print("poc_barcode_1d — 1 次元バーコードが読めなくなる境界")
    print("(真値は符号化した数字そのもの。成功 / 誤読 / 読み取り不能を分けて数える)")
    print()
    section1_code()
    section2_zero_point()
    section3_sweeps()
    section4_misread()
    section5_tilt()
    section6_smudge()
    section7_collapse()
    section8_controls()
    section9_figures()
    section10_tool_gaps()
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
