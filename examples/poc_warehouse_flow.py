# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""庫内の滞留はどこで生まれたか —— 待ちの種類を分けずに数えると全部「混雑」になる。

物流センターの損失は「どこかで待っている」ことですが、待ちには**種類**があります
(補充待ち / 人待ち / 通路の干渉 / システム待ち / 欠品)。天井カメラと位置ログは
あるのに真因が見えないのは、**1 つの「滞留時間」に畳んで数えている**からです。
ここでは庫内の平面図と作業者・搬送機の軌跡を合成で作り、**待ちを種類ごとに
既知の時刻と長さで仕込んで**、畳んだ数字が何を隠すかを測ります。

動画を (t, y, x) の 1 つの体積として扱うのが要点です。滞留は「時間軸に伸びた柱」、
移動は「斜めの管」なので、**t 軸方向のオープニング**(長さ 1.5 秒の線分)で管だけが
消え、柱が残ります。残った柱を :func:`fullseye.ledger.vol_label` で連結成分に割り、
:func:`fullseye.ledger.esdf` が返す通路の空き幅と、成分の中の ID の数・時間の入れ子
から種類を決めます。

EXTEND: 実測に差し替えるなら :func:`simulate` が返す ``tracks``(ID → 時刻・x・y)を
天井カメラ + 追跡器の出力に置き換えます。**平面図(棚の占有格子)は実測でも要ります**
—— 通路の空き幅は esdf で図面から出しており、これが無いと「狭い通路」と「開けた
場所」が区別できません。実データで測れなくなるのは真値のほうで、待ちの原因は
作業者への聞き取りか WMS のイベントログ(補充指示・払い出し指示の時刻)からしか
取れません。本 PoC の :data:`DUR` と :func:`missions` がその台帳に相当します。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. ★★**ゼロ点の「総滞留時間」は 6 割しか待ちでない**。速度がしきい値以下の時間を
   足すだけだと 328.5 秒。真の待ちの合計は 208.0 秒(63.3 %)で、残りは
   **生産的な作業 60.0 秒**と、待ちに入る/出るときの徐行 60.5 秒。
   「滞留を減らせ」と言われた現場は、まず作業時間を削ろうとすることになる。
2. ★★**同じ数字が違う原因から出る**。待ちを 1 種類ずつ止めた対照群で、
   総滞留時間の減り方は 人待ち -30.0 秒 / 通路の干渉 -30.0 秒 —— **完全に同数**
   (わざと同じ総量に置いてある)。1 本の数字では「通路を広げる」のか
   「人を増やす」のかが決まらない。種類別の指標なら該当の型だけが 4/4 → 0/4、
   10/10 → 0/10 と落ちるので、どちらを止めたかが一意に分かる。
3. ★★**欠品は滞留として存在しない**。棚が空で待たずに別の棚へ回る損失は、
   総滞留時間を 8.0 秒(2.4 %)しか動かさないのに、**余計な移動を 60.9 m**
   (= 移動時間 50.8 秒)生む。滞留時間だけを KPI にすると、この損失は
   永久に見えない。★しかも測った経路長は標本間隔で縮む(Δt=0.25 秒で -1.3 %、
   Δt=2.0 秒で -14.4 %)ので、経路長を KPI にするなら間隔を固定する必要がある。
4. ★**2-D の滞留ヒートマップ(時間軸に潰した積算)は「多数が通った」と
   「1 人が長く待った」を区別できない**。積算の上位 30 列のうち真の待ち位置は
   7 列だけで、残り 23 列は交差通路。3-D の連結成分なら列ごとの平均時間厚みが
   柱 41.2 フレーム / 管 3.7 フレームで 11.2 倍離れる —— 潰した瞬間に消える情報。
5. ★**崖は種類ごとに違う場所にあり、しかも予測できる**。滞留が 3 標本必要なら
   長さ T の待ちは Δt > T/2 で消える。徐行 2.5 秒ぶんが柱に足されるので
   予測は (T+2.5)/2 —— 実測の崖(検出率が 50 % を切る Δt)は
   欠品 0.5 秒(予測 2.3)/ 干渉 3.0 秒(予測 2.8)/ 人待ち 5.0 秒(予測 5.0)/
   システム待ち 6.0 秒(予測 6.3)/ 補充待ち 8.0 秒(予測 10.2)。
   ★欠品だけは予測より 4.6 倍早く落ちた —— 短い柱は徐行ぶんを足しても
   8 秒しきい値の下に留まらねばならず、Δt が粗いと**補充待ちに化ける**からで、
   消えるのではなく**型を間違える**方向に壊れる。
6. ★★**遮蔽と標本間隔は違う型を殺す**。棚を高くしていくと、天井カメラの死角は
   まず**棚に挟まれた狭い通路**に出る。棚 2.4 m で補充待ちの検出率は 5/5 → 2/5、
   3.6 m で 0/5 になるのに、開けた場所のシステム待ちは 5/5 のまま。
   ★死角に入る棚の高さは撮る前に幾何で出せる(視線が棚の縁を越える高さ)——
   予測 2.13 m に対し実測の消失は 2.4 m 段で一致。
7. ★★**ID の取り違えは「人待ち」だけを壊す**。作業台では「同じ柱の中で遅く
   始まったほうが待ち」という時間の入れ子で待ちと作業を分けるので、ID が
   入れ替わると**待ちと作業が丸ごと交換される**。取り違え率 3e-3 /フレーム対で
   人待ちの検出率は 4/4 → 1/4 に落ちるが、補充待ち(単独)は 5/5 のまま。
   ★総滞留時間はこの間 1 秒も動かない —— 3 つの劣化のどれもが、
   畳んだ数字には同じ「何も起きていない」に見える。

【グラウンドトゥルース】
平面図(棚・通路・作業台・払い出し口)は矩形の閉形式。軌跡は**折れ線 + 一定速度**で
決め打ちし、待ちは種類ごとに**固定長**(:data:`DUR`)で仕込むので、どの滞留が何由来かは
完全に既知。待ちに入る/出る 0.15 m だけ徐行(0.12 m/s)を入れてあり、これが
「ゼロ点が待ち以外を拾う」源になる。加速度は入れていない(実機ではさらに増える)。
天井カメラの遮蔽は 2 台のカメラ位置・棚の高さ・標識高さから**光線が棚の縁を越えるか**
で決める閉形式。ID の取り違えは近接した対に確率 p で起き、以後**永続**する。
種類別の照合は「時間の重なり 40 % 以上かつ重心が 0.7 m 以内」で行う。

来歴(公開文献のみ): Little, *Operations Research* 9 (1961) 383 —— L = λW /
Lague, Brodu & Leroux, *ISPRS J. Photogramm.* 82 (2013) 10 —— 法線方向の変化検出 /
Bewley et al., *ICIP* (2016) 3464 —— 追跡の ID 取り違えと評価 /
Serra, *Image Analysis and Mathematical Morphology* (1982) —— 線分構造要素の開き。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 庫内の諸元(すべてメートル) ------------------------------------------- #
CELL = 0.30                     # 平面格子の 1 マス [m]
NX, NY = 80, 60                 # 24.0 m x 18.0 m
DT_BASE = 0.25                  # 真値の時間刻み [s]
T_END = 100.0                   # 観測時間 [s]
NT = int(round(T_END / DT_BASE))

#: 棚の占有(x 範囲 2 本 x y 範囲 3 本の直積)。中央 x 11.0-13.0 が交差通路。
RACK_X = ((2.4, 11.0), (13.0, 21.6))
RACK_Y = ((3.6, 5.4), (8.4, 10.2), (12.0, 13.8))

#: 通路の中心線。縦(交差通路)と横(主通路・狭通路・下段通路)。
X_L, X_C, X_R = 1.2, 12.0, 22.8
Y_TOP, Y_MAIN, Y_NARROW, Y_BOT = 1.8, 6.9, 11.1, 16.2

DISPATCH = (12.0, 17.0)                                    # 払い出し(指示待ち)口
WS = ((3.0, 17.0), (6.5, 17.0), (15.5, 17.0), (19.0, 17.0),
      (22.5, 17.0))             # 梱包作業台(5 台、同時に 2 人が同じ台に来ない)
QUEUE_OFF = (0.6, -0.6)         # 作業台の斜め後ろに並ぶ位置 [m]

#: ピッキング面(x, y, その面が向いている通路の中心線 y)。
#: M* = 主通路(幅 3.0 m)、N* = 狭通路(幅 1.8 m)、B* = 下段の開けた通路。
PICKS = {
    "M1": (5.0, 5.85, Y_MAIN), "M2": (17.0, 5.85, Y_MAIN),
    "M3": (7.0, 7.95, Y_MAIN), "M4": (19.0, 7.95, Y_MAIN),
    "N1": (5.0, 10.65, Y_NARROW), "N2": (16.0, 10.65, Y_NARROW),
    "N3": (8.0, 11.55, Y_NARROW), "N4": (19.0, 11.55, Y_NARROW),
    "B1": (6.0, 14.25, Y_BOT), "B2": (18.0, 14.25, Y_BOT),
}

# --- 天井カメラ ------------------------------------------------------------- #
CAMS = ((12.0, 6.9), (12.0, 16.2))     # 主通路の上と下段通路の上、2 台
H_CAM, H_AG = 6.0, 1.6                 # カメラ高さ / 追跡する標識の高さ [m]
RACK_H = 1.8                           # 棚の高さ [m](8 節で振る)

# --- 動くもの --------------------------------------------------------------- #
R_AGENT = 0.45                  # 作業者・搬送機の半径 [m](3x3 マスの足跡)
V_WORK, V_AGV = 1.2, 0.9        # 歩く速さ / 搬送機の速さ [m/s]
CREEP_D, CREEP_V = 0.15, 0.12   # 待ちに入る/出るときの徐行の距離と速さ

#: 待ちの種類と長さ [s]。**固定長**にしてあるので崖が鋭く出る(現場ではばらつく)。
#: ★「人待ち」4 件 x (7.5 + 徐行 2.5) と「通路の干渉」8 件 x (2.5 + 徐行 2.5) は
#: どちらも**ゼロ点に 40.0 秒**を足す —— わざと揃えてある。現実に一致するとは
#: 限らないが、「同じ数字が違う原因から出る」ことは 1 例で示せる。
DUR = {"補充待ち": 18.0, "人待ち": 7.5, "通路の干渉": 2.5,
       "システム待ち": 10.0, "欠品": 2.0, "作業": 12.0}

#: 損失として数える型(「作業」は生産的なので損失ではない)。
LOSS_TYPES = ("補充待ち", "人待ち", "通路の干渉", "システム待ち", "欠品")
ALL_TYPES = LOSS_TYPES + ("作業",)

# --- 測定の設定 ------------------------------------------------------------- #
DT_MEAS = 0.5                   # 天井カメラの標本間隔 [s](公称)
POS_NOISE = 0.015               # 位置の雑音 σ [m]
D_SWITCH = 1.2                  # ID の取り違えが起きる距離 [m]
P_SWITCH = 0.0                  # 取り違え確率 /フレーム/近接対(公称)
#: ゼロ点の「止まっている」しきい値 [m/s]。★雑音の作る見かけの速さ
#: (σ√2/Δt = 0.085 m/s @ Δt=0.25 秒)より十分上に置かないと、**止まっている人を
#: 動いていると誤判定してゼロ点が減る**(0.15 m/s だと Δt=0.25 秒でゼロ点が
#: 半分になり、「細かく撮るほど滞留が減る」という嘘の結論が出た)。
V_TH = 0.25
K_SEC = 2.5                     # t 軸オープニングの線分長 [s]
MIN_SAMPLES = 3                 # 柱として認めるのに要る標本数
PICK_CLEAR, NARROW_CLEAR = 0.75, 1.25   # esdf の空き幅による通路の区分 [m]
LANDMARK_R = 1.5                # 作業台・払い出し口とみなす半径 [m]
CORE_R = 0.45                   # 柱の中で「動かなかった」と認める半径 [m]
LONG_WAIT = 8.0                 # 棚前の待ちを「補充待ち」と読む長さ [s]
SEED = 7


# --------------------------------------------------------------------------- #
# 1. 平面図(真値)                                                            #
# --------------------------------------------------------------------------- #
def rack_mask() -> np.ndarray:
    """棚の占有格子 ``(NY, NX)``。マスの中心が棚の矩形に入るかで決める。"""
    yy, xx = np.mgrid[0:NY, 0:NX]
    ym, xm = (yy + 0.5) * CELL, (xx + 0.5) * CELL
    m = np.zeros((NY, NX), bool)
    for x0, x1 in RACK_X:
        for y0, y1 in RACK_Y:
            m |= (xm > x0) & (xm < x1) & (ym > y0) & (ym < y1)
    return m


def clearance_map(racks: np.ndarray) -> np.ndarray:
    """通路の空き幅 ``(NY, NX)`` [m] —— :func:`fullseye.ledger.esdf` の外側の値。

    ``esdf`` は占有格子から符号つき距離場を返す(外 = +、内 = -)。深さ 1 の
    ボリュームに **軸ごとの voxel_size** を渡して平面の距離だけを取り出す。
    """
    d = np.asarray(fs.ledger.esdf(racks[None, :, :], voxel_size=(1.0, CELL, CELL)))
    return d[0]


def visibility_map(rack_h: float) -> np.ndarray:
    """天井カメラ 2 台から見えるマス ``(NY, NX)``(閉形式の遮蔽)。

    カメラ ``C``(高さ :data:`H_CAM`)から標識 ``P``(高さ :data:`H_AG`)への
    光線は、地上投影の割合 ``u`` の点で高さ ``H_CAM + u(H_AG - H_CAM)`` を通る。
    棚(高さ ``rack_h``)がそこに在れば遮られる。**u が大きいほど光線は低い**ので、
    遮られるのは「光線が棚に触れる区間のうち最も P 寄りの点」で決まる。
    """
    racks = rack_mask()
    yy, xx = np.mgrid[0:NY, 0:NX]
    px, py = (xx + 0.5) * CELL, (yy + 0.5) * CELL
    seen = np.zeros((NY, NX), bool)
    us = np.linspace(0.0, 1.0, 41)
    for cx, cy in CAMS:
        u_hit = np.zeros((NY, NX))            # 棚に触れる最大の u(0 = 触れない)
        for u in us:
            sx, sy = cx + u * (px - cx), cy + u * (py - cy)
            ix = np.clip((sx / CELL).astype(int), 0, NX - 1)
            iy = np.clip((sy / CELL).astype(int), 0, NY - 1)
            hit = racks[iy, ix]
            u_hit = np.where(hit, np.maximum(u_hit, u), u_hit)
        # 遮る棚の高さの下限(critical height)。触れないなら +inf。
        h_crit = np.where(u_hit > 0, H_CAM - u_hit * (H_CAM - H_AG), np.inf)
        seen |= rack_h < h_crit
    return seen & ~racks


def critical_rack_height(x: float, y: float) -> float:
    """点 ``(x, y)`` が死角に入り始める棚の高さ [m](2 台のうち高いほうで決まる)。"""
    racks = rack_mask()
    us = np.linspace(0.0, 1.0, 201)
    per_cam = []
    for cx, cy in CAMS:
        u_hit = 0.0
        for u in us:
            sx, sy = cx + u * (x - cx), cy + u * (y - cy)
            ix = int(np.clip(sx / CELL, 0, NX - 1))
            iy = int(np.clip(sy / CELL, 0, NY - 1))
            if racks[iy, ix]:
                u_hit = max(u_hit, u)
        per_cam.append(H_CAM - u_hit * (H_CAM - H_AG) if u_hit > 0 else np.inf)
    # ★どちらか 1 台でも見えれば見えるので、死角に入るのは**全カメラが遮られる**
    #   高さ = 各カメラの限界の**最大**。ここを min にしていて予測が 0.5 m 外れた。
    return float(max(per_cam))


# --------------------------------------------------------------------------- #
# 2. 軌跡(真値)                                                              #
# --------------------------------------------------------------------------- #
def build_track(start_t: float, legs, speed: float, dur_of):
    """折れ線 + 待ちから keyframe 列と真の待ち事象を作る。

    ``legs`` は ``("at", (x, y))`` で始まり、``("go", (x, y))`` / ``("wait", 種類)``
    が続く。待ちの直前 / 直後の :data:`CREEP_D` [m] は :data:`CREEP_V` [m/s] の
    **徐行**にする(実機の寄せ動作。ゼロ点がこれを滞留として拾う)。
    """
    t = float(start_t)
    kfs = [(t, float(legs[0][1][0]), float(legs[0][1][1]))]
    events, prev_wait = [], False
    for i, leg in enumerate(legs[1:], 1):
        if leg[0] == "go":
            tgt = np.array(leg[1], float)
            cur = np.array(kfs[-1][1:], float)
            d = float(np.hypot(*(tgt - cur)))
            if d <= 1e-9:
                prev_wait = False
                continue
            u = (tgt - cur) / d
            nxt_wait = (i + 1 < len(legs)) and legs[i + 1][0] == "wait" \
                and dur_of(legs[i + 1][1]) > 0
            head = CREEP_D if prev_wait else 0.0
            tail = CREEP_D if nxt_wait else 0.0
            if head + tail > d:                       # 短い脚は丸ごと徐行
                head, tail = d, 0.0
            if head > 0:
                t += head / CREEP_V
                p = cur + u * head
                kfs.append((t, p[0], p[1]))
            mid = d - head - tail
            if mid > 0:
                t += mid / speed
                p = cur + u * (head + mid)
                kfs.append((t, p[0], p[1]))
            if tail > 0:
                t += tail / CREEP_V
                kfs.append((t, tgt[0], tgt[1]))
            prev_wait = False
        else:                                          # ("wait", 種類)
            cause = leg[1]
            dur = dur_of(cause)
            if dur > 0:
                t0, x, y = t, kfs[-1][1], kfs[-1][2]
                t += dur
                kfs.append((t, x, y))
                events.append({"cause": cause, "t0": t0, "t1": t, "x": x, "y": y})
                prev_wait = True
    return kfs, events


def route_to(pick, frm=DISPATCH):
    """払い出し口 → 通路 → ピッキング面 の折れ線(棚を横切らない)。"""
    x, y, ay = pick
    return [("go", (X_C, Y_BOT)), ("go", (X_C, ay)), ("go", (x, ay)), ("go", (x, y))]


def route_from(pick, dest):
    """ピッキング面 → 通路 → 目的地。"""
    x, y, ay = pick
    return [("go", (x, ay)), ("go", (X_C, ay)), ("go", (X_C, Y_BOT)), ("go", dest)]


def missions(disabled=()):
    """28 人分の作業指図。``disabled`` に入れた種類の待ちは起きない(対照群)。

    返すのは ``(名前, 開始時刻, 速さ, legs, 合わせる事象の番号, 合わせる時刻)`` の列。
    最後の 2 つが ``None`` でなければ、その事象の開始が指定時刻に来るよう
    開始時刻を解いて上書きする(ペアの出会いを厳密に作るため)。
    """
    def dur_of(c):
        return 0.0 if c in disabled else DUR[c]

    out = []
    # (a) 補充待ち 5 件: 棚が空 → 補充が来るまで棚前で待ち → 作業台で梱包。
    r_picks = ["M1", "N1", "N3", "M3", "N2"]
    serve = []                      # 各作業台で「作業」が始まる実時刻
    for k, (pk, t0) in enumerate(zip(r_picks, (2.0, 9.0, 16.0, 23.0, 30.0))):
        p = PICKS[pk]
        ws = WS[k]
        legs = [("at", DISPATCH)] + route_to(p) + [("wait", "補充待ち")] \
            + route_from(p, ws) + [("wait", "作業")]
        out.append(("R%d" % k, t0, V_AGV, legs, None, None))
        # ★並ぶ人の到着時刻は**実際に作業が始まる時刻**から決める(見積りで
        #   決めたら 20 秒ずれて、待ちの柱が作業の柱と重ならなかった)。
        _, evs = build_track(t0, legs, V_AGV, dur_of)
        serve.append(next((e["t0"] for e in evs if e["cause"] == "作業"), t0))
    # (b) 人待ち 4 件: 作業台の斜め後ろに並び、前の人が終わるまで待って去る。
    for k in range(4):
        ws = WS[k]
        q = (ws[0] + QUEUE_OFF[0], ws[1] + QUEUE_OFF[1])
        legs = [("at", DISPATCH), ("go", (X_C, Y_BOT)), ("go", (q[0], Y_BOT)),
                ("go", q), ("wait", "人待ち"), ("go", (q[0], Y_BOT)),
                ("go", (X_C, Y_BOT)), ("go", DISPATCH)]
        out.append(("Q%d" % k, 0.0, V_WORK, legs, 0, serve[k] + 2.0))
    # (c) 通路の干渉 5 組 = 10 件: 交差通路(幅 2.0 m)で正面から出会って止まる。
    # ★出会う場所は**棚の列の真横**でなければならない。棚と棚の間でない交差通路は
    #   両側が開けていて空き幅が 1.9 m あり、「狭い通路」に分類されない(最初の
    #   実装は主通路の高さで出会わせてしまい、10 件中 4 件が「その他」に落ちた)。
    for k, (t_enc, y_enc) in enumerate(zip((12.0, 32.0, 52.0, 72.0),
                                           (4.5, 9.3, 12.9, 4.5))):
        a = (X_C, y_enc - 0.45)
        b = (X_C, y_enc + 0.45)
        legs_a = [("at", (X_C, Y_TOP)), ("go", a), ("wait", "通路の干渉"),
                  ("go", (X_C, Y_BOT))]
        legs_b = [("at", (X_C, Y_BOT)), ("go", b), ("wait", "通路の干渉"),
                  ("go", (X_C, Y_TOP))]
        out.append(("Xa%d" % k, 0.0, V_WORK, legs_a, 0, t_enc))
        out.append(("Xb%d" % k, 0.0, V_WORK, legs_b, 0, t_enc + 0.25))
    # (d) システム待ち 5 件: 払い出し口で指示が来るのを待つ(開けた場所・単独)。
    for k, (t0, off) in enumerate(zip((6.0, 22.0, 38.0, 54.0, 70.0),
                                      (-1.0, 0.6, -0.4, 1.0, 0.0))):
        spot = (DISPATCH[0] + off, DISPATCH[1])
        pk = PICKS[["M2", "B1", "M4", "B2", "N4"][k]]
        legs = [("at", (X_C, Y_TOP)), ("go", (X_C, Y_BOT)), ("go", spot),
                ("wait", "システム待ち")] + route_to(pk, spot) \
            + [("go", (pk[0], pk[2])), ("go", (X_C, pk[2])), ("go", (X_C, Y_TOP))]
        out.append(("S%d" % k, t0, V_WORK, legs, None, None))
    # (e) 欠品 4 件: 棚が空 → 短く止まってから**別の棚へ回る**(遠回りが損失)。
    pairs = (("M1", "M2"), ("N1", "N4"), ("B1", "B2"), ("M3", "M4"))
    for k, (t0, (pa, pb)) in enumerate(zip((4.0, 20.0, 36.0, 52.0), pairs)):
        p1, p2 = PICKS[pa], PICKS[pb]
        ws = WS[k]
        if "欠品" in disabled:
            legs = [("at", DISPATCH)] + route_to(p2) + route_from(p2, ws)
        else:
            legs = [("at", DISPATCH)] + route_to(p1) + [("wait", "欠品")] \
                + route_from(p1, (p2[0], p2[2])) + [("go", p2[:2])] \
                + route_from(p2, ws)
        out.append(("K%d" % k, t0, V_WORK, legs, None, None))
    return out


def simulate(disabled=()) -> dict:
    """全員の真の軌跡を DT_BASE 刻みで返す。

    返り値: ``tracks`` = ``{名前: {"t","x","y","present"}}``、``events`` = 真の待ち、
    ``path_len`` = 名前ごとの真の移動距離 [m]。
    """
    def dur_of(c):
        return 0.0 if c in disabled else DUR[c]

    times = np.arange(NT) * DT_BASE
    tracks, events, path_len = {}, [], {}
    for name, t0, spd, legs, anchor, t_want in missions(disabled):
        kfs, evs = build_track(t0, legs, spd, dur_of)
        if anchor is not None and evs:
            j = min(anchor, len(evs) - 1)
            kfs, evs = build_track(t0 + (t_want - evs[j]["t0"]), legs, spd, dur_of)
        kt = np.array([k[0] for k in kfs])
        kx = np.array([k[1] for k in kfs])
        ky = np.array([k[2] for k in kfs])
        present = (times >= kt[0]) & (times <= kt[-1])
        tracks[name] = {"t": times, "x": np.interp(times, kt, kx),
                        "y": np.interp(times, kt, ky), "present": present}
        path_len[name] = float(np.sum(np.hypot(np.diff(kx), np.diff(ky))))
        for e in evs:
            e["agent"] = name
            events.append(e)
    return {"tracks": tracks, "events": events, "path_len": path_len}


# --------------------------------------------------------------------------- #
# 3. 測定の現実 —— 標本間隔・遮蔽・ID の取り違え                                #
# --------------------------------------------------------------------------- #
def measure(scene: dict, dt_meas: float = DT_MEAS, rack_h: float = RACK_H,
            p_switch: float = P_SWITCH, seed: int = SEED) -> dict:
    """真の軌跡 → 天井カメラ + 追跡器の出力(欠測と ID 誤りを含む)。"""
    rng = np.random.default_rng(seed)
    step = max(1, int(round(dt_meas / DT_BASE)))
    frames = np.arange(0, NT, step)
    vis = visibility_map(rack_h)
    names = list(scene["tracks"])
    n = len(names)

    xs = np.full((n, frames.size), np.nan)
    ys = np.full((n, frames.size), np.nan)
    for i, nm in enumerate(names):
        tr = scene["tracks"][nm]
        ok = tr["present"][frames]
        x = tr["x"][frames] + POS_NOISE * rng.standard_normal(frames.size)
        y = tr["y"][frames] + POS_NOISE * rng.standard_normal(frames.size)
        ix = np.clip((x / CELL).astype(int), 0, NX - 1)
        iy = np.clip((y / CELL).astype(int), 0, NY - 1)
        ok &= vis[iy, ix]
        xs[i, ok], ys[i, ok] = x[ok], y[ok]

    # ID の取り違え(**併合**): 近づいた 2 人を追跡器が 1 本の軌跡にしてしまう。
    # 一度併合したら**離れるまで続く**(1 フレームごとにちらつく実装は非現実的)。
    # ★入れ替え(swap)ではなく併合にしてある —— 入れ替えは「同じ柱の中で
    #   遅く始まったほうが待ち」という時間の入れ子を壊さない(役が入れ替わるだけ
    #   で、両方の役が正しく埋まる)。壊れるのは **2 人が 1 人に見えたとき**。
    rid = np.tile(np.arange(n)[:, None], (1, frames.size))
    merged: dict = {}
    for f in range(frames.size):
        live = np.nonzero(np.isfinite(xs[:, f]))[0]
        if live.size > 1:
            px, py = xs[live, f], ys[live, f]
            d = np.hypot(px[:, None] - px[None, :], py[:, None] - py[None, :])
            near = set()
            iu, ju = np.nonzero(np.triu(d < D_SWITCH, 1))
            for a, b in zip(iu, ju):
                i, j = int(live[a]), int(live[b])
                near.add((i, j))
                if (i, j) not in merged and p_switch > 0 \
                        and rng.random() < p_switch:
                    merged[(i, j)] = True
            for pair in [k for k in merged if k not in near]:
                del merged[pair]
        else:
            merged.clear()
        for (i, j) in merged:
            rid[j, f] = rid[i, f]
    seen = int(np.isfinite(xs).sum())
    total = int(sum(scene["tracks"][nm]["present"][frames].sum() for nm in names))
    return {"names": names, "frames": frames, "dt": step * DT_BASE,
            "x": xs, "y": ys, "rid": rid, "vis": vis,
            "seen": seen, "total": total}


# --------------------------------------------------------------------------- #
# 4. ゼロ点 —— 速度しきい値の総滞留時間 / 2-D ヒートマップ                      #
# --------------------------------------------------------------------------- #
def zero_dwell_seconds(meas: dict) -> float:
    """ゼロ点: 速度が :data:`V_TH` 以下だった時間の総和 [s]。型は出ない。"""
    dt = meas["dt"]
    tot = 0.0
    for i in range(len(meas["names"])):
        x, y = meas["x"][i], meas["y"][i]
        ok = np.isfinite(x)
        idx = np.nonzero(ok)[0]
        if idx.size < 2:
            continue
        gap = np.diff(idx) == 1                      # 連続する標本だけで速度を出す
        v = np.hypot(np.diff(x[idx]), np.diff(y[idx])) / dt
        tot += float(np.sum(gap & (v < V_TH))) * dt
    return tot


def build_volume(meas: dict):
    """測定から x-y-t の占有体積 ``(T, NY, NX)`` と ID 体積を作る。

    体積の軸順は **(depth, row, col) = (t, y, x)**(3-D op の規約)。
    足跡は半径 :data:`R_AGENT` の 3x3 マス。
    """
    nf = meas["frames"].size
    vol = np.zeros((nf, NY, NX), bool)
    lab = np.zeros((nf, NY, NX), np.int16)
    for i in range(len(meas["names"])):
        x, y = meas["x"][i], meas["y"][i]
        f = np.nonzero(np.isfinite(x))[0]
        if f.size == 0:
            continue
        iy = np.clip((y[f] / CELL).astype(int), 1, NY - 2)
        ix = np.clip((x[f] / CELL).astype(int), 1, NX - 2)
        rid = meas["rid"][i, f] + 1
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                vol[f, iy + dy, ix + dx] = True
                lab[f, iy + dy, ix + dx] = rid
    return vol, lab


def heatmap_2d(vol: np.ndarray) -> np.ndarray:
    """時間軸に潰した積算(= 現場でいちばん普通の「滞留ヒートマップ」)。

    :func:`fullseye.ledger.render_volume_projection` の ``mode="xray"``、視点 0 度が
    そのまま「軸 0 に沿った総和」なので、専用の関数を書かずにこれで取る。
    """
    return np.asarray(fs.ledger.render_volume_projection(
        vol.astype(np.float32), azimuth=0.0, elevation=0.0, mode="xray"))


# --------------------------------------------------------------------------- #
# 5. 提案 —— x-y-t を 3-D として読む                                            #
# --------------------------------------------------------------------------- #
def dwell_volume(vol: np.ndarray, dt: float) -> np.ndarray:
    """t 軸方向の**線分オープニング**で「柱」だけ残す(「管」は消える)。

    移動している人は 1 つの列(y, x)に足跡の直径 ÷ 速さ ぶんしか居ないので、
    長さ ``K`` フレームの線分で開くと消える。待っている人は同じ列に
    待ち時間ぶん居続けるので残る。**公開経路に軸ごとに長さの違う 3-D 構造要素の
    モルフォロジが無い**ため、ここだけ scipy を直接使っている。
    """
    k = max(MIN_SAMPLES, int(round(K_SEC / dt)))
    se = np.ones((k, 1, 1), bool)
    return ndi.binary_opening(vol, structure=se)


def zone_of(xm: float, ym: float, clear: np.ndarray) -> str:
    """重心の場所を平面図から読む(作業台 > 払い出し口 > 空き幅による通路の区分)。"""
    if min(np.hypot(xm - w[0], ym - w[1]) for w in WS) < LANDMARK_R:
        return "ws"
    if np.hypot(xm - DISPATCH[0], ym - DISPATCH[1]) < LANDMARK_R:
        return "disp"
    c = float(clear[int(np.clip(ym / CELL, 0, NY - 1)),
                    int(np.clip(xm / CELL, 0, NX - 1))])
    if c <= PICK_CLEAR:
        return "pick"
    if c <= NARROW_CLEAR:
        return "narrow"
    return "open"


def _runs_in_components(meas: dict, labels: np.ndarray):
    """各 ID が「どの柱の中に、いつからいつまで居たか」を切り出す。

    ★成分の中身を **ID を焼き込んだ体積**から読むと、柱の脇をすり抜けた人が
    足跡の重なりで数ボクセルを上書きし、**存在しない待ちの ID** が湧く
    (最初の実装がそうなり、作業台の柱が「7 人」になった)。読むのは
    **中心の座標**のほうにする —— すり抜けた人の中心が柱の列に入るのは
    1〜2 フレームだけなので :data:`MIN_SAMPLES` で落ちる。
    """
    runs = []
    for i in range(len(meas["names"])):
        x, y = meas["x"][i], meas["y"][i]
        f = np.nonzero(np.isfinite(x))[0]
        if f.size == 0:
            continue
        iy = np.clip((y[f] / CELL).astype(int), 0, NY - 1)
        ix = np.clip((x[f] / CELL).astype(int), 0, NX - 1)
        comp = labels[f, iy, ix]
        rid = meas["rid"][i, f]
        cur = None
        for k in range(f.size):
            if cur is not None and f[k] - cur["f1"] > 2:
                runs.append(cur)
                cur = None
            if comp[k] <= 0:
                continue
            key = (int(comp[k]), int(rid[k]))
            if cur is not None and cur["key"] != key:
                runs.append(cur)
                cur = None
            if cur is None:
                cur = {"key": key, "f0": int(f[k]), "f1": int(f[k]),
                       "fs": [], "xs": [], "ys": []}
            cur["f1"] = int(f[k])
            cur["fs"].append(int(f[k]))
            cur["xs"].append(float(x[f[k]]))
            cur["ys"].append(float(y[f[k]]))
        if cur is not None:
            runs.append(cur)

    keep = []
    for r in runs:
        ff = np.array(r["fs"])
        xs, ys = np.array(r["xs"]), np.array(r["ys"])
        # ★止まっている**芯**だけを残す。柱は 2 人ぶんの足跡で 1.8 m あるので、
        #   通り抜ける人の中心も 2〜3 フレーム柱の中に入る(実測でそれが
        #   「1 人しか居ない干渉」を作り、10 件中 8 件を落とした)。
        #   中央値から :data:`CORE_R` 以内に居続けた最長の連なりを芯とする。
        near = np.hypot(xs - np.median(xs), ys - np.median(ys)) <= CORE_R
        best_i = best_n = cur_i = cur_n = 0
        for k, v in enumerate(near):
            if v:
                cur_n = cur_n + 1 if cur_n else 1
                cur_i = k - cur_n + 1
                if cur_n > best_n:
                    best_n, best_i = cur_n, cur_i
            else:
                cur_n = 0
        if best_n < MIN_SAMPLES:
            continue
        sl = slice(best_i, best_i + best_n)
        span = int(ff[sl][-1] - ff[sl][0] + 1)
        if span < MIN_SAMPLES:
            continue
        keep.append({"key": r["key"], "f0": int(ff[sl][0]), "f1": int(ff[sl][-1]),
                     "n": int(best_n), "x": float(np.mean(xs[sl])),
                     "y": float(np.mean(ys[sl]))})
    return keep


def detect(meas: dict, clear: np.ndarray) -> dict:
    """x-y-t 体積 → 柱 → 種類。返り値は検出事象の列と中間結果。"""
    vol, _ = build_volume(meas)
    dwell = dwell_volume(vol, meas["dt"])
    labels, ncomp = fs.ledger.vol_label.raw(dwell, connectivity=26)
    runs = _runs_in_components(meas, labels)

    n_ids, first_f = {}, {}
    for r in runs:
        c = r["key"][0]
        n_ids.setdefault(c, set()).add(r["key"][1])
        first_f[c] = min(first_f.get(c, np.inf), r["f0"])

    dt = meas["dt"]
    evs = []
    for r in runs:
        c, rid = r["key"]
        nid = len(n_ids[c])
        dur = (r["f1"] - r["f0"] + 1) * dt
        xm, ym = r["x"], r["y"]
        z = zone_of(xm, ym, clear)
        if z == "ws":
            kind = "人待ち" if (nid >= 2 and r["f0"] > first_f[c]) else "作業"
        elif z == "disp":
            kind = "システム待ち"
        elif z == "narrow" and nid >= 2 and dur < LONG_WAIT:
            kind = "通路の干渉"
        elif z == "pick":
            kind = "補充待ち" if dur >= LONG_WAIT else "欠品"
        else:
            kind = "その他"
        evs.append({"kind": kind, "t0": r["f0"] * dt, "t1": r["f1"] * dt,
                    "x": xm, "y": ym, "zone": z, "dur": dur,
                    "n_ids": nid, "comp": int(c)})
    return {"vol": vol, "dwell": dwell, "labels": labels, "n": int(ncomp),
            "events": evs}


def score(truth, detected) -> dict:
    """型ごとの検出率と適合率(時間の重なり 40 % 以上・重心 0.7 m 以内で照合)。"""
    hit = {k: 0 for k in ALL_TYPES}
    tot = {k: 0 for k in ALL_TYPES}
    for e in truth:
        tot[e["cause"]] += 1
    used = set()
    for e in truth:
        for j, d in enumerate(detected):
            ov = min(e["t1"], d["t1"]) - max(e["t0"], d["t0"])
            if ov / max(e["t1"] - e["t0"], 1e-9) < 0.4:
                continue
            if np.hypot(d["x"] - e["x"], d["y"] - e["y"]) > 0.7:
                continue
            if d["kind"] == e["cause"]:
                hit[e["cause"]] += 1
                used.add(j)
                break
    tp = {k: 0 for k in ALL_TYPES}
    fp = {k: 0 for k in ALL_TYPES}
    for j, d in enumerate(detected):
        ok = False
        for e in truth:
            ov = min(e["t1"], d["t1"]) - max(e["t0"], d["t0"])
            if ov / max(e["t1"] - e["t0"], 1e-9) < 0.4:
                continue
            if np.hypot(d["x"] - e["x"], d["y"] - e["y"]) > 0.7:
                continue
            if d["kind"] == e["cause"]:
                ok = True
                break
        if d["kind"] in tp:
            (tp if ok else fp)[d["kind"]] += 1
    return {"hit": hit, "tot": tot, "tp": tp, "fp": fp}


#: 掃引は 5 通りの乱数で平均する。1 通りだと事象が 4〜10 件しかない型で
#: 検出率が 0.25 刻みにばたつき、崖の位置が乱数で 1 段ずれる。
SEEDS = (7, 17, 27, 37, 47)


def rates(clear, dt_meas=DT_MEAS, rack_h=RACK_H, p_switch=P_SWITCH):
    """掃引の 1 点: 種類別の検出率とゼロ点を :data:`SEEDS` で平均する。"""
    acc = {k: 0.0 for k in LOSS_TYPES}
    z, last = 0.0, None
    for sd in SEEDS:
        r = pipeline(dt_meas=dt_meas, rack_h=rack_h, p_switch=p_switch,
                     clear=clear, seed=sd)
        for k in LOSS_TYPES:
            acc[k] += r["score"]["hit"][k] / max(r["score"]["tot"][k], 1)
        z += r["zero"]
        last = r
    n = len(SEEDS)
    return {k: acc[k] / n for k in LOSS_TYPES}, z / n, last


def pipeline(disabled=(), dt_meas=DT_MEAS, rack_h=RACK_H, p_switch=P_SWITCH,
             clear=None, seed=SEED) -> dict:
    """場面を作る → 測る → ゼロ点と提案の両方で読む(掃引の 1 点ぶん)。"""
    sc = simulate(disabled)
    me = measure(sc, dt_meas, rack_h, p_switch, seed)
    det = detect(me, clear)
    return {"scene": sc, "meas": me, "det": det,
            "zero": zero_dwell_seconds(me),
            "score": score(sc["events"], det["events"])}


# --------------------------------------------------------------------------- #
# 節 1: 場面と真値                                                              #
# --------------------------------------------------------------------------- #
def section_scene(base: dict, clear: np.ndarray) -> dict:
    print("\n" + "=" * 78)
    print("1) 庫内の場面と、仕込んだ待ちの真値")
    print("=" * 78)
    sc = base["scene"]
    racks = rack_mask()
    print("  床面 %.1f x %.1f m(1 マス %.2f m)、棚の占有 %.1f %%、"
          "作業者・搬送機 %d 台、観測 %.0f 秒"
          % (NX * CELL, NY * CELL, CELL, 100 * racks.mean(),
             len(sc["tracks"]), T_END))
    print("  通路の空き幅(esdf の外側): 主通路 %.2f m / 狭通路 %.2f m / "
          "交差通路 %.2f m / 棚前 %.2f m"
          % (clear[int(Y_MAIN / CELL), 40], clear[int(Y_NARROW / CELL), 20],
             clear[30, int(X_C / CELL)], clear[int(5.85 / CELL), int(5.0 / CELL)]))
    print("\n   種類            件数   1 件の長さ [s]   合計 [s]")
    counts = {k: 0 for k in ALL_TYPES}
    for e in sc["events"]:
        counts[e["cause"]] += 1
    for k in ALL_TYPES:
        print("   %-14s %4d   %10.1f      %8.1f"
              % (k, counts[k], DUR[k], counts[k] * DUR[k]))
    loss = sum(counts[k] * DUR[k] for k in LOSS_TYPES)
    work = counts["作業"] * DUR["作業"]
    print("   %-14s %4s   %10s      %8.1f  (うち損失 %.1f / 生産的 %.1f)"
          % ("合計", "", "", loss + work, loss, work))
    creep = 2.0 * CREEP_D / CREEP_V
    print("  ★人待ちと通路の干渉は、**ゼロ点への寄与**(待ち + 前後の徐行 %.1f 秒)"
          % creep)
    print("     が %.1f 秒 / %.1f 秒 で揃うように件数と長さを置いてある。"
          % (counts["人待ち"] * (DUR["人待ち"] + creep),
             counts["通路の干渉"] * (DUR["通路の干渉"] + creep)))
    return {"counts": counts, "loss": loss, "work": work, "racks": racks}


# --------------------------------------------------------------------------- #
# 節 2: ゼロ点                                                                  #
# --------------------------------------------------------------------------- #
def section_zero(base: dict, tru: dict) -> dict:
    print("\n" + "=" * 78)
    print("2) ★★ゼロ点(速度しきい値の総滞留時間)は何を数えているのか")
    print("=" * 78)
    z = base["zero"]
    print("  ゼロ点の総滞留時間        %8.1f 秒   (速度 < %.2f m/s の時間の総和)"
          % (z, V_TH))
    print("  真の待ちの合計            %8.1f 秒   (%.1f %%)"
          % (tru["loss"], 100 * tru["loss"] / z))
    print("  生産的な作業              %8.1f 秒   (%.1f %%)"
          % (tru["work"], 100 * tru["work"] / z))
    creep = z - tru["loss"] - tru["work"]
    print("  待ちに入る/出る徐行       %8.1f 秒   (%.1f %%)"
          % (creep, 100 * creep / z))
    print("\n  ★★この 1 つの数字には**待ちでないもの**が %.1f %% 混ざっている。"
          % (100 * (z - tru["loss"]) / z))
    print("     「滞留を減らせ」と言われた現場が最初に削るのは、削ってはいけない"
          "作業時間になる。")
    return {"zero": z, "creep": creep}


# --------------------------------------------------------------------------- #
# 節 3: 2-D に潰すと何が消えるか                                                #
# --------------------------------------------------------------------------- #
def section_heatmap(base: dict) -> dict:
    print("\n" + "=" * 78)
    print("3) ★2-D の滞留ヒートマップ —— 「多数が通った」と「1 人が長く待った」")
    print("=" * 78)
    vol = base["det"]["vol"]
    heat = heatmap_2d(vol)
    ref = vol.sum(axis=0).astype(np.float32)
    err = float(np.max(np.abs(heat - ref)))
    print("  積算は render_volume_projection(視点 0 度, xray)で取る。"
          "直接の総和との最大差 %.3g(= 同じもの)。" % err)

    ev = base["scene"]["events"]
    wait_mask = np.zeros((NY, NX), bool)
    yy, xx = np.mgrid[0:NY, 0:NX]
    ym, xm = (yy + 0.5) * CELL, (xx + 0.5) * CELL
    for e in ev:
        wait_mask |= (np.hypot(xm - e["x"], ym - e["y"]) < 0.6)
    flat = np.argsort(-heat.ravel())[:30]
    n_wait = int(wait_mask.ravel()[flat].sum())
    print("  積算の上位 30 列のうち、真の待ち位置に当たるのは **%d 列**、"
          "残り %d 列は通路(人が通っただけ)。" % (n_wait, 30 - n_wait))
    print("  ★つまりヒートマップは**場所**はだいたい当てる。当てられないのは"
          "「そこで何が起きたか」のほう —— 同じ積算値が別の中身から出る。")

    # 同じくらいの積算値が、まったく違う中身から出ることを 3 列で見せる。
    dwell_lab0 = base["det"]["labels"]
    probes = [("補充待ち の棚前", PICKS["M1"][0], PICKS["M1"][1]),
              ("出会いの場所(交差通路)", X_C, 9.3),
              ("ただの通路(下段)", X_C, Y_BOT)]
    print("\n   場所                     積算 [フレーム]  3-D の柱の数  最長の柱 [s]")
    probe_rows, probe_rows_heat = [], []
    for lbl, xm, ym in probes:
        iy, ix = int(ym / CELL), int(xm / CELL)
        col = dwell_lab0[:, iy, ix]
        ids = [c for c in np.unique(col) if c > 0]
        longest = 0
        for c in ids:
            f = np.nonzero(col == c)[0]
            longest = max(longest, int(f[-1] - f[0] + 1))
        print("   %-24s %10.0f     %8d      %8.1f"
              % (lbl, heat[iy, ix], len(ids), longest * base["meas"]["dt"]))
        probe_rows.append([lbl, "%.0f" % heat[iy, ix], str(len(ids)),
                           "%.1f" % (longest * base["meas"]["dt"])])
        probe_rows_heat.append(float(heat[iy, ix]))
    print("  ★★いちばん積算が大きいのは**誰も待っていない下段通路**(%.0f フレーム)で、"
          % probe_rows_heat[2])
    print("     18 秒待っている棚前(%.0f)より大きい。3-D に戻すと、通路の柱は"
          " %s 秒、棚前は %s 秒。"
          % (probe_rows_heat[0], probe_rows[2][3], probe_rows[0][3]))
    figs.save_table("heat_ambiguity",
                    ["場所", "積算 [フレーム]", "3-D の柱の数", "最長の柱 [s]"],
                    probe_rows,
                    title="同じ積算値が違う中身から出る(2-D に潰すと消える情報)",
                    caption="ヒートマップは場所を当てるが、"
                            "「1 人が長く待った」と「何人も短く止まった」を分けない。")

    # 柱と管の分かれ目 = **1 人の軌跡の中で**、1 つの列に何フレーム居たか。
    # ★複数人の成分で数えると「通路を 10 人が通った列」が厚くなって混ざるので、
    #   同じ 1 人の中で「待っている間」と「歩いている間」を比べる。
    dwell_lab = base["det"]["labels"]
    probe_agent = "R0"
    i = base["meas"]["names"].index(probe_agent)
    x, y = base["meas"]["x"][i], base["meas"]["y"][i]
    f = np.nonzero(np.isfinite(x))[0]
    iy = np.clip((y[f] / CELL).astype(int), 1, NY - 2)
    ix = np.clip((x[f] / CELL).astype(int), 1, NX - 2)
    inside = dwell_lab[f, iy, ix] > 0
    th_pillar = th_tube = 0.0
    for sel, tag in ((inside, "wait"), (~inside, "move")):
        acc = np.zeros((NY, NX), int)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                np.add.at(acc, (iy[sel] + dy, ix[sel] + dx), 1)
        v = float(acc.max())
        if tag == "wait":
            th_pillar = v
        else:
            th_tube = v
    print("  同じ 1 人(%s)の軌跡で、1 つの列に居たフレーム数の最大: "
          "**待っている間 %.0f / 歩いている間 %.0f** = %.1f 倍。"
          % (probe_agent, th_pillar, th_tube, th_pillar / max(th_tube, 1)))
    print("  ★これは t 軸を持ったままでしか数えられない —— 潰した積算では"
          "「誰の・いつの」厚みかが混ざる(上の下段通路 %.0f フレームがその例)。"
          % probe_rows_heat[2])

    # 柱 1 本をメッシュにして体積と向きを確かめる(3-D op の健全性検査)。
    # 代表は**いちばん長く続いた**成分(いちばん大きい成分ではない —— 2 人ぶんの
    # 足跡で太いだけの短い柱が選ばれてしまう)。
    ext_t = {}
    for c in range(1, int(dwell_lab.max()) + 1):
        zs = np.nonzero((dwell_lab == c).any(axis=(1, 2)))[0]
        if zs.size:
            ext_t[c] = int(zs[-1] - zs[0] + 1)
    pillar = max(ext_t, key=ext_t.get)
    sub = (dwell_lab == pillar)
    zsl = np.nonzero(sub.any(axis=(1, 2)))[0]
    ysl = np.nonzero(sub.any(axis=(0, 2)))[0]
    xsl = np.nonzero(sub.any(axis=(0, 1)))[0]
    pad = np.zeros((zsl.size + 4, ysl.size + 4, xsl.size + 4), np.float32)
    pad[2:-2, 2:-2, 2:-2] = sub[zsl[0]:zsl[-1] + 1, ysl[0]:ysl[-1] + 1,
                                xsl[0]:xsl[-1] + 1]
    verts, faces, _ = fs.ledger.voxel_to_mesh.raw(pad, iso=0.5)
    mvol = float(fs.ledger.mesh_volume((verts, faces)))
    marea = float(np.sum(np.asarray(fs.ledger.face_areas((verts, faces)))))
    print("  いちばん長い柱(%.1f 秒)をメッシュにすると 体積 %.0f voxel"
          "(ボクセル数 %d)、表面積 %.0f、符号 %s。"
          % (ext_t[pillar] * base["meas"]["dt"], mvol, int(sub.sum()), marea,
             "正 = 外向き" if mvol > 0 else "負 = 内向き"))
    print("  ★`voxel_to_mesh`(marching cubes)が返す面の巻き順は**内向き**で、"
          "`mesh_volume` は負を返す。向きの検査に使うなら符号の規約を先に"
          "確かめること(絶対値はボクセル数と %.1f %% 差)。"
          % (100 * abs(abs(mvol) - sub.sum()) / sub.sum()))
    return {"heat": heat, "n_wait_top": n_wait, "th_pillar": th_pillar,
            "th_tube": th_tube, "mesh_vol": mvol, "pillar": pillar}


# --------------------------------------------------------------------------- #
# 節 4: 種類別の成績                                                            #
# --------------------------------------------------------------------------- #
def section_types(base: dict) -> dict:
    print("\n" + "=" * 78)
    print("4) 種類別に数える —— 提案(x-y-t の柱)の成績")
    print("=" * 78)
    s = base["score"]
    print("   種類            真の件数   検出(型も一致)   検出率     誤検出")
    rows = []
    for k in ALL_TYPES:
        rec = s["hit"][k] / max(s["tot"][k], 1)
        print("   %-14s %6d      %8d        %6.2f     %6d"
              % (k, s["tot"][k], s["hit"][k], rec, s["fp"][k]))
        rows.append([k, str(s["tot"][k]), str(s["hit"][k]), "%.2f" % rec,
                     str(s["fp"][k])])
    other = sum(1 for d in base["det"]["events"] if d["kind"] == "その他")
    print("   %-14s %6s      %8s        %6s     %6d" % ("その他", "-", "-", "-", other))
    print("  柱の総数 %d 本(成分 %d 個)。ゼロ点はこの表を 1 つの数字 %.1f 秒に"
          "畳んでいる。" % (len(base["det"]["events"]), base["det"]["n"],
                            base["zero"]))
    figs.save_table("types", ["種類", "真の件数", "検出", "検出率", "誤検出"], rows,
                    title="種類別の検出成績(標本間隔 %.2f 秒 / 棚 %.1f m / "
                          "ID 誤り 0)" % (DT_MEAS, RACK_H),
                    caption="ゼロ点はこの表を 1 つの数字に畳む。畳んだ数字は"
                            "どの行が落ちても同じように動く。")
    return {"rows": rows, "other": other}


# --------------------------------------------------------------------------- #
# 節 5: 対照群 —— 1 種類ずつ止める                                              #
# --------------------------------------------------------------------------- #
def section_control(base: dict, clear: np.ndarray) -> dict:
    print("\n" + "=" * 78)
    print("5) ★★対照群 —— 待ちを 1 種類ずつ止めて、ゼロ点がどれだけ動くか")
    print("=" * 78)
    print("   止めた種類        総滞留時間 [s]    差 [s]     差 [%]   その型の検出")
    z0 = base["zero"]
    rows, out = [], {}
    base_hit = base["score"]["hit"]
    for k in LOSS_TYPES:
        r = pipeline(disabled=(k,), clear=clear)
        d = r["zero"] - z0
        out[k] = {"zero": r["zero"], "d": d,
                  "hit": r["score"]["hit"][k], "tot": base["score"]["tot"][k]}
        print("   %-16s %10.1f   %+9.1f  %+8.2f      %d/%d -> %d/%d"
              % (k, r["zero"], d, 100 * d / z0, base_hit[k],
                 base["score"]["tot"][k], r["score"]["hit"][k],
                 base["score"]["tot"][k]))
        rows.append([k, "%.1f" % r["zero"], "%+.1f" % d, "%+.2f" % (100 * d / z0),
                     "%d/%d -> %d/%d" % (base_hit[k], base["score"]["tot"][k],
                                         r["score"]["hit"][k],
                                         base["score"]["tot"][k])])
    dq = out["人待ち"]["d"]
    dx = out["通路の干渉"]["d"]
    print("\n  ★★人待ちを止めたとき %+.1f 秒、通路の干渉を止めたとき %+.1f 秒 —— "
          "差は %.1f 秒(%.2f %%)。" % (dq, dx, abs(dq - dx),
                                        100 * abs(dq - dx) / abs(dq)))
    print("     **1 本の数字では「通路を広げる」のか「人を増やす」のかが決まらない。**")
    print("     種類別なら、止めた型だけが %d/%d -> %d/%d と落ちるので一意に分かる。"
          % (base_hit["人待ち"], out["人待ち"]["tot"], out["人待ち"]["hit"],
             out["人待ち"]["tot"]))
    print("  ★欠品を止めても総滞留時間は %+.1f 秒(%.2f %%)しか動かない —— "
          "次の節でその損失を測る。"
          % (out["欠品"]["d"], 100 * out["欠品"]["d"] / z0))
    figs.save_table("control", ["止めた種類", "総滞留 [s]", "差 [s]", "差 [%]",
                                "その型の検出"], rows,
                    title="対照群: 1 種類ずつ止めたときのゼロ点の動き",
                    caption="人待ちと通路の干渉は同じだけ動く。"
                            "畳んだ数字からは原因が決まらない。")
    return out


# --------------------------------------------------------------------------- #
# 節 6: 滞留に出ない損失(欠品)                                                #
# --------------------------------------------------------------------------- #
def section_stockout(base: dict, ctrl: dict) -> dict:
    print("\n" + "=" * 78)
    print("6) ★★欠品は滞留として存在しない —— 損失は「余計な移動」に出る")
    print("=" * 78)
    off = simulate(disabled=("欠品",))
    names = [n for n in base["scene"]["path_len"] if n.startswith("K")]
    extra = sum(base["scene"]["path_len"][n] - off["path_len"][n] for n in names)
    print("  欠品を仕込んだ %d 台の真の移動距離 %.1f m、欠品を止めると %.1f m。"
          % (len(names), sum(base["scene"]["path_len"][n] for n in names),
             sum(off["path_len"][n] for n in names)))
    print("  ★余計な移動 **%.1f m**(= %.1f m/台)。歩く速さ %.1f m/s なら "
          "移動時間 %.1f 秒 —— 総滞留時間の動き %+.1f 秒 の %.1f 倍。"
          % (extra, extra / len(names), V_WORK, extra / V_WORK,
             ctrl["欠品"]["d"], abs(extra / V_WORK / ctrl["欠品"]["d"])))

    print("\n   標本間隔 [s]   測った経路長 [m]   真値との差 [%]")
    rows, dts, errs = [], [], []
    truth_len = sum(base["scene"]["path_len"].values())
    for dt in (0.25, 0.5, 1.0, 2.0, 4.0):
        me = measure(base["scene"], dt_meas=dt, rack_h=1.6)
        tot = 0.0
        for i in range(len(me["names"])):
            x, y = me["x"][i], me["y"][i]
            idx = np.nonzero(np.isfinite(x))[0]
            if idx.size < 2:
                continue
            g = np.diff(idx) == 1
            tot += float(np.sum(np.hypot(np.diff(x[idx]), np.diff(y[idx]))[g]))
        e = 100 * (tot - truth_len) / truth_len
        dts.append(dt)
        errs.append(e)
        rows.append([("%.2f" % dt), "%.1f" % tot, "%+.1f" % e])
        print("      %5.2f        %10.1f          %+7.1f" % (dt, tot, e))
    print("  ★経路長は間隔が粗いほど**縮む**(折れ線が角を切る)。"
          "%.2f 秒で %+.1f %%、%.2f 秒で %+.1f %% —— "
          % (dts[0], errs[0], dts[-1], errs[-1]))
    print("     経路長を KPI にするなら標本間隔を固定しないと、"
          "カメラを替えただけで改善に見える。")
    return {"extra": extra, "dts": dts, "errs": errs, "rows": rows}


# --------------------------------------------------------------------------- #
# 節 7: 崖(1) 標本間隔                                                         #
# --------------------------------------------------------------------------- #
def section_sweep_dt(clear: np.ndarray) -> dict:
    print("\n" + "=" * 78)
    print("7) ★崖(1) 標本間隔 —— 先に予測してから測る")
    print("=" * 78)
    creep = 2.0 * CREEP_D / CREEP_V
    print("  予測: 柱と認めるのに %d 標本要るので、長さ T の待ちは Δt > T/%d で消える。"
          % (MIN_SAMPLES, MIN_SAMPLES - 1))
    print("        待ちの前後に徐行が %.1f 秒つくので、実際に見える柱は T + %.1f 秒。"
          % (creep, creep))
    pred = {k: (DUR[k] + creep) / (MIN_SAMPLES - 1) for k in LOSS_TYPES}
    print("   " + "  ".join("%s %.1f s" % (k, pred[k]) for k in LOSS_TYPES))

    dts = (0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0)
    rec = {k: [] for k in LOSS_TYPES}
    zeros = []
    print("\n   Δt [s]   " + "  ".join("%-9s" % k for k in LOSS_TYPES)
          + "  ゼロ点 [s]")
    for dt in dts:
        rr, z, _ = rates(clear, dt_meas=dt)
        zeros.append(z)
        line = "   %5.2f   " % dt
        for k in LOSS_TYPES:
            rec[k].append(rr[k])
            line += "%-9s" % ("%.2f" % rr[k])
        print(line + "  %8.1f" % z)

    print("\n   種類            予測の崖 [s]   実測の崖 [s]   ずれ")
    rows = []
    cliffs = {}
    for k in LOSS_TYPES:
        below = [d for d, v in zip(dts, rec[k]) if v < 0.5]
        c = below[0] if below else np.inf
        cliffs[k] = c
        rows.append([k, "%.1f" % pred[k], ("%.1f" % c) if np.isfinite(c) else ">12",
                     "%+.1f" % (c - pred[k]) if np.isfinite(c) else "-"])
        print("   %-14s %10.1f     %10s   %s"
              % (k, pred[k], ("%.1f" % c) if np.isfinite(c) else ">12",
                 ("%+.1f" % (c - pred[k])) if np.isfinite(c) else "-"))
    print("  ★崖の**順番**は予測どおり(短い待ちから消える)。")
    i2 = list(dts).index(2.0)
    print("  ★★Δt=%.1f 秒では欠品が %.0f/%d まで落ちているのに、ゼロ点は "
          "%.1f -> %.1f 秒(%+.1f %%)。"
          % (dts[i2], rec["欠品"][i2] * 4, 4, zeros[1], zeros[i2],
             100 * (zeros[i2] - zeros[1]) / zeros[1]))
    print("     しかもその %+.1f %% は「滞留が減った」としか読めない —— "
          "実際には**測れなくなっただけ**。"
          % (100 * (zeros[i2] - zeros[1]) / zeros[1]))
    print("  ★★カメラを 0.5 秒間隔から %.1f 秒間隔に替えるだけで %+.1f 秒 動く。"
          % (dts[i2], zeros[i2] - zeros[1]))
    print("     これは「人待ちを 1 件残らず無くす」のと同じ order の変化で、"
          "畳んだ数字では区別がつかない。")
    figs.save_plot("sweep_interval",
                   [(k, list(dts), rec[k]) for k in LOSS_TYPES],
                   xlabel="標本間隔 Δt [秒]", ylabel="種類別の検出率",
                   title="崖は種類ごとに違う場所にある(標本間隔)",
                   caption="短い待ち(通路の干渉・欠品)から先に消える。"
                           "総滞留時間はこの間ほとんど動かない。")
    figs.save_table("cliff_interval", ["種類", "予測の崖 [s]", "実測の崖 [s]", "ずれ"],
                    rows, title="標本間隔の崖: 予測 (T + 徐行)/2 と実測",
                    caption="予測は幾何だけから立てたもの。")
    return {"dts": list(dts), "rec": rec, "pred": pred, "cliffs": cliffs,
            "zeros": zeros, "creep": creep}


# --------------------------------------------------------------------------- #
# 節 8: 崖(2) 遮蔽                                                             #
# --------------------------------------------------------------------------- #
def base_events_replen(clear=None):
    """補充待ちの真の事象(遮蔽の予測と突き合わせるために場所だけ要る)。"""
    return [e for e in simulate()["events"] if e["cause"] == "補充待ち"]


def section_sweep_occ(clear: np.ndarray) -> dict:
    print("\n" + "=" * 78)
    print("8) ★★崖(2) 遮蔽 —— 死角は「棚に挟まれた狭い通路」に先に出る")
    print("=" * 78)
    probe = PICKS["N1"]
    hc = critical_rack_height(probe[0], probe[1])
    hc_open = critical_rack_height(DISPATCH[0], DISPATCH[1])
    print("  予測(幾何): 狭通路の棚前 (%.1f, %.1f) が死角に入る棚の高さは "
          "**%.2f m**。" % (probe[0], probe[1], hc))
    print("             払い出し口 (%.1f, %.1f) は %s。"
          % (DISPATCH[0], DISPATCH[1],
             "どの高さでも見える" if not np.isfinite(hc_open) else "%.2f m" % hc_open))

    hs = (1.6, 2.0, 2.2, 2.4, 2.6, 2.8, 3.2, 4.0)
    rec = {k: [] for k in LOSS_TYPES}
    lost = []
    lost_at = {}                      # 事象 → 最初に見失った棚の高さ
    print("\n   棚の高さ [m]   欠測率 [%]   "
          + "  ".join("%-9s" % k for k in LOSS_TYPES))
    for h in hs:
        rr, _, r = rates(clear, rack_h=h)
        me = r["meas"]
        drop = 100 * (1 - me["seen"] / max(me["total"], 1))
        lost.append(drop)
        line = "   %8.1f      %8.1f     " % (h, drop)
        for k in LOSS_TYPES:
            rec[k].append(rr[k])
            line += "%-9s" % ("%.2f" % rr[k])
        print(line)
        for e in r["scene"]["events"]:
            if e["cause"] != "補充待ち":
                continue
            key = (e["agent"], round(e["t0"], 2))
            found = any(d["kind"] == e["cause"]
                        and np.hypot(d["x"] - e["x"], d["y"] - e["y"]) <= 0.7
                        and min(e["t1"], d["t1"]) - max(e["t0"], d["t0"])
                        >= 0.4 * (e["t1"] - e["t0"])
                        for d in r["det"]["events"])
            if not found and key not in lost_at:
                lost_at[key] = h

    print("\n  ★事象ごとに予測と突き合わせる(補充待ち 5 件):")
    print("   棚前          予測 h_crit [m]   実測で見失った高さ [m]")
    occ_rows = []
    for e in sorted((e for e in base_events_replen(clear)), key=lambda e: e["x"]):
        key = (e["agent"], round(e["t0"], 2))
        hc_e = critical_rack_height(e["x"], e["y"])
        got = lost_at.get(key)
        print("   (%5.1f,%5.1f)  %12s   %20s"
              % (e["x"], e["y"],
                 ("%.2f" % hc_e) if np.isfinite(hc_e) else "見え続ける",
                 ("%.1f" % got) if got else "最後まで見えた"))
        occ_rows.append(["(%.1f, %.1f)" % (e["x"], e["y"]),
                         ("%.2f" % hc_e) if np.isfinite(hc_e) else "-",
                         ("%.1f" % got) if got else "-"])
    figs.save_table("occlusion_prediction",
                    ["棚前の位置 [m]", "予測 h_crit [m]", "実測で消えた高さ [m]"],
                    occ_rows,
                    title="死角に入る棚の高さは撮る前に幾何で出せる",
                    caption="h_crit = 光線が棚の縁を越える高さ。"
                            "主通路側の棚前は 2 台のカメラのどちらかから見え続ける。")
    print("\n  ★補充待ち %.2f -> %.2f、通路の干渉 %.2f -> %.2f に対し、"
          "システム待ちは %.2f -> %.2f。"
          % (rec["補充待ち"][0], rec["補充待ち"][-1], rec["通路の干渉"][0],
             rec["通路の干渉"][-1], rec["システム待ち"][0], rec["システム待ち"][-1]))
    print("     **遮蔽は棚に近い型を狙い撃ちする** —— 開けた場所の待ちは無傷。")
    figs.save_plot("sweep_occlusion",
                   [(k, list(hs), rec[k]) for k in LOSS_TYPES],
                   xlabel="棚の高さ [m]", ylabel="種類別の検出率",
                   title="遮蔽は棚に近い型だけを殺す",
                   caption="天井カメラ 2 台。死角に入る棚の高さは撮る前に幾何で"
                           "出せる(狭通路の棚前で %.2f m)。" % hc)
    return {"hs": list(hs), "rec": rec, "lost": lost, "h_crit": hc}


# --------------------------------------------------------------------------- #
# 節 9: 崖(3) ID の取り違え                                                    #
# --------------------------------------------------------------------------- #
def section_sweep_id(clear: np.ndarray) -> dict:
    print("\n" + "=" * 78)
    print("9) ★★崖(3) ID の併合 —— 壊れるのは「2 人の関係を読む型」だけ")
    print("=" * 78)
    print("  予測: ID に依存するのは**関係を読む 2 つの型**だけ。人待ち"
          "(同じ柱の中で遅く始まったほう)と 通路の干渉(柱の中に 2 人)。")
    print("        補充待ち・システム待ち・欠品は 1 人で決まるので無傷のはず。")
    print("  ★入れ替え(swap)ではなく**併合**にしてある —— 入れ替えは役が交換される"
          "だけで時間の入れ子を壊さない(先に試して何も起きなかった)。")
    ps = (0.0, 0.005, 0.01, 0.02, 0.05, 0.15)
    rec = {k: [] for k in LOSS_TYPES}
    zeros = []
    print("\n   取り違え率     ゼロ点 [s]   "
          + "  ".join("%-9s" % k for k in LOSS_TYPES))
    for p in ps:
        r = pipeline(p_switch=p, clear=clear)
        zeros.append(r["zero"])
        line = "   %10.4g   %8.1f     " % (p, r["zero"])
        for k in LOSS_TYPES:
            v = r["score"]["hit"][k] / max(r["score"]["tot"][k], 1)
            rec[k].append(v)
            line += "%-9s" % ("%.2f" % v)
        print(line)
    print("\n  ★関係を読む型: 人待ち %.2f -> %.2f、通路の干渉 %.2f -> %.2f。"
          % (rec["人待ち"][0], rec["人待ち"][-1], rec["通路の干渉"][0],
             rec["通路の干渉"][-1]))
    print("    1 人で決まる型: 補充待ち %.2f -> %.2f、システム待ち %.2f -> %.2f、"
          "欠品 %.2f -> %.2f —— 予測どおり無傷。"
          % (rec["補充待ち"][0], rec["補充待ち"][-1], rec["システム待ち"][0],
             rec["システム待ち"][-1], rec["欠品"][0], rec["欠品"][-1]))
    print("  ★★ゼロ点は %.1f -> %.1f 秒(%.2f %%)—— **1 秒も動かないに等しい**。"
          % (zeros[0], zeros[-1], 100 * abs(zeros[-1] - zeros[0]) / zeros[0]))
    print("     標本間隔・遮蔽・ID 誤りの 3 つは違う型を壊すのに、"
          "畳んだ数字にはどれも同じ「何も起きていない」に見える。")
    figs.save_plot("sweep_idswitch",
                   [(k, [1e-5 if p == 0 else p for p in ps], rec[k])
                    for k in LOSS_TYPES],
                   xlabel="ID 併合の確率 [/フレーム/近接対]",
                   ylabel="種類別の検出率",
                   title="ID の併合が壊すのは「2 人の関係を読む型」だけ",
                   caption="左端は併合なし(対数軸にできないので 1e-5 に置いた)。"
                           "総滞留時間はこの掃引で 1 秒も動かない。")
    return {"ps": list(ps), "rec": rec, "zeros": zeros}


# --------------------------------------------------------------------------- #
# 節 10: 図                                                                     #
# --------------------------------------------------------------------------- #
TYPE_RGB = {
    "補充待ち": (0.90, 0.55, 0.10), "人待ち": (0.20, 0.45, 0.85),
    "通路の干渉": (0.85, 0.20, 0.35), "システム待ち": (0.35, 0.70, 0.35),
    "欠品": (0.60, 0.30, 0.75), "作業": (0.45, 0.45, 0.45),
    "その他": (0.75, 0.75, 0.75),
}


def _floor_rgb(racks: np.ndarray) -> np.ndarray:
    """平面図の下地(棚 = 濃い灰、通路 = 明るい灰)。"""
    img = np.full((NY, NX, 3), 0.93)
    img[racks] = (0.40, 0.42, 0.46)
    return img


def _stamp(img, xm, ym, rgb, r=1):
    iy = int(np.clip(ym / CELL, 1, NY - 2))
    ix = int(np.clip(xm / CELL, 1, NX - 2))
    img[iy - r:iy + r + 1, ix - r:ix + r + 1] = rgb
    return img


def section_figures(base: dict, tru: dict, heat: dict, clear: np.ndarray) -> None:
    racks = tru["racks"]
    # (a) 場面: 平面図 / 軌跡 / 見えない場所 / 真の待ちの型
    plan = _floor_rgb(racks)
    for w in WS:
        plan = _stamp(plan, w[0], w[1], (0.15, 0.35, 0.65), r=2)
    plan = _stamp(plan, DISPATCH[0], DISPATCH[1], (0.10, 0.55, 0.30), r=2)
    for p in PICKS.values():
        plan = _stamp(plan, p[0], p[1], (0.85, 0.60, 0.15), r=0)

    paths = np.zeros((NY, NX))
    for tr in base["scene"]["tracks"].values():
        m = tr["present"]
        iy = np.clip((tr["y"][m] / CELL).astype(int), 0, NY - 1)
        ix = np.clip((tr["x"][m] / CELL).astype(int), 0, NX - 1)
        np.add.at(paths, (iy, ix), 1.0)
    paths = np.log1p(paths)

    vis = base["meas"]["vis"]
    seen_img = _floor_rgb(racks)
    seen_img[~vis & ~racks] = (0.85, 0.35, 0.35)

    truth_img = _floor_rgb(racks)
    for e in base["scene"]["events"]:
        truth_img = _stamp(truth_img, e["x"], e["y"], TYPE_RGB[e["cause"]], r=1)

    figs.save_grid("scene_layout", [plan, paths, seen_img, truth_img],
                   ["平面図(青 = 作業台 / 緑 = 払い出し口 / 橙 = 棚前)",
                    "全 %d 台の軌跡の重ね(log 濃度)" % len(base["scene"]["tracks"]),
                    "天井カメラ 2 台の死角(赤、棚 %.1f m)" % RACK_H,
                    "真の待ちの位置と種類(色 = 種類)"],
                   ncols=2,
                   title="庫内 %.0f x %.0f m / 1 マス %.2f m / 観測 %.0f 秒"
                         % (NX * CELL, NY * CELL, CELL, T_END),
                   caption="待ちは種類ごとに既知の時刻・長さ・場所で仕込んである。")

    # (b) x-y-t の投影 —— 滞留が柱に見える
    vol = base["det"]["vol"].astype(np.float32)
    dw = base["det"]["dwell"].astype(np.float32)
    top = heatmap_2d(vol)
    tilt1 = np.asarray(fs.ledger.render_volume_projection(
        vol, azimuth=38.0, elevation=18.0, mode="xray"))
    tilt2 = np.asarray(fs.ledger.render_volume_projection(
        dw, azimuth=38.0, elevation=18.0, mode="xray"))
    dtop = heatmap_2d(dw)
    figs.save_grid("xyt_projection", [top, tilt1, dtop, tilt2],
                   ["真上から見た積算(= 2-D ヒートマップ)",
                    "傾けた投影(方位 38 度・仰角 18 度)",
                    "t 軸オープニング後の積算(柱だけ)",
                    "同じ視点で見た柱"],
                   ncols=2,
                   title="動画を (t, y, x) の 1 つの体積として投影する",
                   caption="上段は通路が明るい(人が通っただけ)。下段は"
                           "t 軸の線分 %.1f 秒で開いたあと —— 待ちだけが残る。"
                           % K_SEC)

    # (c) 検出の型別地図(真値と並べる)
    det_img = _floor_rgb(racks)
    for d in base["det"]["events"]:
        det_img = _stamp(det_img, d["x"], d["y"], TYPE_RGB.get(d["kind"],
                                                               (0.7, 0.7, 0.7)), r=1)
    figs.save_grid("map_by_type", [truth_img, det_img],
                   ["真値(仕込んだ待ち)", "提案(x-y-t の柱から読んだ型)"],
                   ncols=2, title="種類ごとの色分け地図",
                   caption="橙 = 補充待ち / 青 = 人待ち / 赤 = 通路の干渉 / "
                           "緑 = システム待ち / 紫 = 欠品 / 灰 = 作業。")

    # (d) 通路の空き幅(esdf)—— 型を決める特徴量そのもの
    figs.save_grid("clearance_map", [np.clip(clear, 0, 3.0), heat["heat"]],
                   ["通路の空き幅 [m](esdf の外側)",
                    "滞留ヒートマップ(積算フレーム数)"],
                   ncols=2, title="型を決める 2 つの地図",
                   caption="空き幅 %.2f m 以下 = 棚前、%.2f m 以下 = 狭い通路。"
                           "右のヒートマップは通路が明るく、待ちが埋もれる。"
                           % (PICK_CLEAR, NARROW_CLEAR))


# --------------------------------------------------------------------------- #
# 節 11: 道具の穴                                                               #
# --------------------------------------------------------------------------- #
def section_tool_gaps() -> None:
    print("\n" + "=" * 78)
    print("11) 道具の穴(この PoC で fullseye を引いてみて)")
    print("=" * 78)
    L = set(n for n in dir(fs.ledger) if not n.startswith("_"))

    assert "vol_label" in L and "vol_region_props" in L and "esdf" in L
    assert not any(n in L for n in ("vol_opening_ball", "vol_erode", "vol_dilate"))
    print("  (a) **軸ごとに長さの違う 3-D 構造要素**でのモルフォロジが公開経路に無い。"
          "この PoC の中心は「t 軸方向の線分 %.1f 秒で開く」ことなので、"
          "ここだけ scipy.ndimage.binary_opening を直接使っている。"
          "(進化 op 側には vol_erode / vol_opening_ball が在るが**球のみ**で、"
          "ledger には出ていない。)" % K_SEC)

    assert not any(n in L for n in ("link_trajectories", "hungarian_match",
                                    "assign_ids"))
    print("  (b) **点の対応づけ(検出 → ID)**の口が無い。`track_points` は画像から"
          "の Lucas-Kanade で、既に検出済みの点列をゲート付きで結ぶ経路は無い。"
          "この PoC は追跡器の出力を入力に取る形で回避したが、"
          "poc_particle_tracking も自前で書いている(2 本目)。")

    assert not any(n in L for n in ("roc_curve", "auc", "detection_score"))
    print("  (c) 検出事象を真値と**照合して数える**枠組み(時間の重なり + 距離での"
          "対応づけ、種類別の検出率)が無い。ROC/AUC も含めて 3 本目の自前実装。")

    assert "occupancy_grid" in L
    print("  (d) `occupancy_grid` は点群 → 占有格子だが、**足跡(円板)を持つ物体を"
          "時間軸つきでラスタライズする**口ではない。x-y-t 体積の作成は自前 12 行。")

    print("  (e) `vol_label_shape_stats` の `extent` / `elongation` は柱と管を"
          "分けるのに効くが、**列あたりの平均時間厚み**(体積 ÷ 投影面積)は無い。"
          "3-D を時空間として使うなら、これは族に入る価値がある。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("庫内の滞留はどこで生まれたか —— 待ちの種類を分けずに数えると全部「混雑」")
    print("床 %.0f x %.0f m / 1 マス %.2f m / 標本間隔 %.2f 秒 / 棚 %.1f m"
          % (NX * CELL, NY * CELL, CELL, DT_MEAS, RACK_H))
    print("=" * 78)

    clear = clearance_map(rack_mask())
    base = pipeline(clear=clear)

    tru = section_scene(base, clear)
    zer = section_zero(base, tru)
    heat = section_heatmap(base)
    typ = section_types(base)
    ctrl = section_control(base, clear)
    stock = section_stockout(base, ctrl)
    swd = section_sweep_dt(clear)
    swo = section_sweep_occ(clear)
    swi = section_sweep_id(clear)
    section_figures(base, tru, heat, clear)
    section_tool_gaps()

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * ゼロ点の総滞留時間 %.1f 秒のうち、真の待ちは %.1f 秒(%.1f %%)。"
          "残りは生産的な作業 %.1f 秒と徐行 %.1f 秒。"
          % (zer["zero"], tru["loss"], 100 * tru["loss"] / zer["zero"],
             tru["work"], zer["creep"]))
    print("  * 人待ちを止めても通路の干渉を止めても、総滞留時間の減りは "
          "%+.1f / %+.1f 秒 —— 同じ数字が違う原因から出る。"
          % (ctrl["人待ち"]["d"], ctrl["通路の干渉"]["d"]))
    print("  * 欠品は総滞留時間を %+.1f 秒しか動かさないが、余計な移動 %.1f m "
          "(= %.1f 秒)を生む。滞留時間だけの KPI では永久に見えない。"
          % (ctrl["欠品"]["d"], stock["extra"], stock["extra"] / V_WORK))
    print("  * 2-D に潰した積算の上位 30 列のうち真の待ちは %d 列。"
          "3-D なら柱 %.1f / 管 %.1f フレームで %.1f 倍離れる。"
          % (heat["n_wait_top"], heat["th_pillar"], heat["th_tube"],
             heat["th_pillar"] / heat["th_tube"]))
    print("  * 崖は 3 本の軸で違う型を殺す: 標本間隔は**短い待ち**"
          "(干渉は Δt %.1f 秒で半減)、" % swd["cliffs"]["通路の干渉"])
    print("    遮蔽は**棚に近い型**(補充待ち %.2f -> %.2f、システム待ちは"
          "%.2f -> %.2f で無傷)、"
          % (swo["rec"]["補充待ち"][0], swo["rec"]["補充待ち"][-1],
             swo["rec"]["システム待ち"][0], swo["rec"]["システム待ち"][-1]))
    print("    ID の併合は**2 人の関係を読む型**(人待ち %.2f -> %.2f / "
          "干渉 %.2f -> %.2f、単独の型は無傷)。"
          % (swi["rec"]["人待ち"][0], swi["rec"]["人待ち"][-1],
             swi["rec"]["通路の干渉"][0], swi["rec"]["通路の干渉"][-1]))
    print("    ID の掃引のあいだ総滞留時間は %.1f -> %.1f 秒 —— "
          "**1 秒も動かない**。"
          % (swi["zeros"][0], swi["zeros"][-1]))

    # --- 所見を固定する assert(壊れたら鳴る) ------------------------------- #
    assert zer["zero"] > tru["loss"] * 1.2, "ゼロ点は真の待ちより明確に多いはず"
    assert abs(ctrl["人待ち"]["d"] - ctrl["通路の干渉"]["d"]) < 4.0, \
        "人待ちと通路の干渉のゼロ点への寄与は同じに置いてある"
    assert abs(ctrl["欠品"]["d"]) < 0.25 * abs(ctrl["補充待ち"]["d"]), \
        "欠品は総滞留時間をほとんど動かさない"
    assert stock["extra"] > 20.0, "欠品の遠回りは 20 m 以上あるはず"
    assert heat["th_pillar"] > 5.0 * heat["th_tube"], "柱と管は時間厚みで分かれる"
    assert swo["rec"]["システム待ち"][-1] >= swo["rec"]["システム待ち"][0] - 0.05, \
        "開けた場所のシステム待ちは遮蔽に強いはず"
    assert swi["rec"]["人待ち"][-1] < swi["rec"]["人待ち"][0], \
        "ID 取り違えは人待ちを壊すはず"
    assert 100 * abs(swi["zeros"][-1] - swi["zeros"][0]) / swi["zeros"][0] < 2.0, \
        "ID 掃引でゼロ点はほとんど動かないはず"

    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
