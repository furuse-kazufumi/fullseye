# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""多ビーム測深で海底が笑う —— 音速を取り違えると、壊れるのは外側ビームだけ。

多ビーム音響測深機(マルチビーム)は、送受波器から扇状にビームを出し、
往復時間と射出角から海底の深さを出します。ところが音は水中で**まっすぐ
進みません** —— 水温・塩分で音速 c が深さごとに変わり、Snell の法則で
光線が曲がります。処理で音速プロファイル c(z) を取り違えると、平らな
海底が**外側ビームだけ反り返って**記録されます。現場ではこれを見た目から
「スマイル(smile)」「フラウン(frown)」と呼びます。

この PoC は、平らな海底と線形音速プロファイルを自分で植えてから、
(a) 平均音速の取り違え、(b) 屈折(光線の曲がり)、(c) 角度測定、
(d) エコー検出、を**別々に**測ります。ゼロ点は「表面の音速計だけを見て
定数と仮定する」現場の手です。

EXTEND: 実データに差し替えるなら :func:`trace_to_depth` が返す走時を、
測深機の生記録(ビームごとの往復時間 τ とビーム角)に置き換え、
:func:`profile_linear` を CTD/SVP キャストの (深さ, 音速) 列に置き換えます。
**この PoC の中心である「真の c(z) と比べる」は実データではできません** ——
真の音速場は誰も測っていないからです(キャストは 1 本の柱の、その瞬間の
値でしかない)。実データでできるのは §8 の**隣接測線の重なりの食い違い**
(これは現場でスマイルを見つける実際の手口)と、キャストを取り替えたときの
差分だけで、絶対誤差は出せません。

この PoC が示すこと(数字はすべて最終実行の実測値):

1. **ゼロ点(表面の音速だけを定数と仮定)は、直下ビームからもう失格**。
   水深 50.0 m・水柱の音速差 -40.0 m/s の場面で、表面音速 1520.0 m/s を
   そのまま使うと直下で **+0.67 m** 深く出ます。IHO S-44 Order 1a の
   鉛直不確かさ TVU(50 m) = 0.820 m の **82 %** を、いちばん素直な
   ビーム 1 本で食い潰しています。
2. ★**平均音速を直下ビームで較正すると、誤差が「消える」のではなく
   「外側へ移動」します**。較正後の直下は誤差 0.000 m ですが、外側 65 度は
   **-2.70 m**。★これが重要な非対称です —— 検査は直下の深さを錘や
   バーチェックで確かめるので、**検査が通る所だけ直る**。
3. ★**崖の位置は測る前に閉形式で出せる**。ラフな展開式
   Δz ≈ (g D²/2c₀)·tan²θ から予測した崖は **48.15 度**、
   厳密な円弧の閉形式から予測した崖は **49.13 度**、
   層に切ったレイトレース + ビーム形成 + エコー検出の全経路を通した実測は
   **49.13 度**。★**厳密式は当たり、ラフな展開式は 1.0 度 外しました** ——
   tan² 展開は 45 度までは 3 % 以内ですが、70 度では **19.4 %** 過大に
   予測します(実測 -4.16 m に対し展開式 -4.97 m)。
4. ★**深い所ほど崖は浅い角度に来ます**。IHO の許容 TVU は深さに比例して
   増えますが(b·d の項)、屈折誤差も深さに比例して増えるので、深水では
   両方が打ち消し合って**崖の角度は深さに依らなくなります**。
   予測した漸近値 arctan√(2·b·c₀/|Δc|) = **44.81 度**に対し、
   200 ケース(音速差 25 通り × 深さ 8 通り)の実測は、10 m で 63.51 度、
   200 m で **45.19 度**。★**「浅い所は安全」は逆で、浅い所のほうが
   swath を広く使えます**。
5. **要因を 1 つずつ止めた対照群**。勾配ゼロ(等音速)では全ビーム
   0.000 m(残るのは数値誤差だけ)。角度測定だけ、エコー検出だけを
   入れた場合の誤差は **0.0004 m / 0.0006 m** で、屈折の 2.70 m より
   **4000 倍以上**小さい —— **スマイルは角度誤差でもエコー検出誤差でも
   ありません**。
6. ★**上向き屈折(frown)は、外側ビームで海底に届きません**。音速が
   深さとともに増える場面では光線が下に凸に曲がり、
   θ₀ > arcsin(c₀/c_bottom) のビームは反転して戻ります。
   Δc = +60 m/s・50 m で予測した限界角 **75.36 度**に対し、実測で
   最後に返ってきたビームは **75.0 度**(1 度刻み)。★深さが出ないのでは
   なく、**そのビームだけ何も記録されない**(swath が黙って狭くなる)。
7. ★**フットプリントの教科書式 d·Δθ/cos²θ は、電子的に振ったビームには
   足りません**。`beamform_delay_sum` で自分の配列のビーム幅を実測すると、
   ステア角 0/45/70 度で 1.100 / 1.550 / 3.150 度 —— **1/cosθ で広がって
   います**(予測 1.058 / 1.496 / 3.092 度、差は最大 6.4 %)。広がりを
   入れると指数は 2 でなく **3**: 70 度でのフットプリントは
   cos² 式 **7.89 m** に対し cos³ 式 **23.06 m**、光線から直に測った実測は
   **23.98 m**。**cos² 式は 3 分の 1 に見積もります**。
8. ★**隣接測線の重なりで、平らな海底に段差が立つ**。測線間隔を swath の
   半分にすると、片方の外側ビームと片方の内側ビームが同じ海底を測り、
   その食い違いは **2.42 m**。これは現場でスマイルを見つける実際の手口で、
   **実データでもできる唯一の検査**です。
9. ★**平らな海底が見かけの勾配を持ちます**。`dem_slope` で測ると、
   真の海底 0.000 度に対し、屈折込みの DTM は swath 端で **8.98 度**。
   海底地形図として見ると「谷の縁」があるように見えます。
10. **道具の穴**。`fs.<name>` / `fs.op.<name>` / `fs.ledger.<name>` /
    `fs.op_find(語幹)` の 4 層すべてを引いて、**音響測深そのものの op は
    1 つもありませんでした**(``sonar`` / ``swath`` / ``bathym`` /
    ``sound_speed`` / ``tvu`` は 0 件)。使えたのは `beamform_delay_sum` /
    `beamform_doa`(電波レーダの語彙のまま、角度スペクトルだけを使う)、
    `find_peaks` / `peak_subbin`、`snell_angle`、`interp_scattered`、
    `dem_slope`。★**使おうとして使えなかったもの**と、次に埋めるべき op は
    §10 に列挙しました。

【グラウンドトゥルース】海底は**深さ 50.0 m の完全な水平面**として置きました
(:data:`DEPTH_REF`)。音速は深さの 1 次式 c(z) = c₀ + g z(:func:`profile_linear`、
水柱全体で -40.0 m/s = 夏の沿岸で表層が速い形)。一定勾配にしたのは、
**光線が半径 R = c/(g sinθ) の円弧に閉じる**からです —— 走時も水平距離も
閉形式で書け、レイトレースの検算ができます。対照群は (a) 勾配ゼロの等音速、
(b) 直下較正の有無、(c) 屈折を止めて角度・エコー検出だけを入れた経路。
構造を持つプロファイル(混合層 + サーモクライン + 深層、:func:`profile_thermocline`)も
1 本混ぜて、一定勾配の当てはめでは直らないことを見ます。

【来歴】IHO S-44 第 6 版の鉛直不確かさ TVU = √(a² + (b·d)²) と、その
Order 1a の係数 a = 0.5 m / b = 0.013 は公開規格の値です(Special Order
a = 0.25 / b = 0.0075、Order 2 a = 1.0 / b = 0.023 も表に入れました)。
一定勾配の層で光線が円弧になること、および走時 t = (1/g)·ln[(c₂/c₁)·
(1+cosθ₁)/(1+cosθ₂)] は Snell の法則からの初等的な積分で、文献は引きません。
音速 1500 m/s 前後・水柱の変化 ±60 m/s は沿岸域で普通に起きる幅として
置いた仮定で、特定の海域の観測値ではありません。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
#: 海底の深さ [m](完全な水平面として植える)。
DEPTH_REF = 50.0

#: 水柱全体の音速差 [m/s]。負 = 表層が速い(夏の沿岸)= スマイル側。
DELTA_C_REF = -40.0

#: 水柱の中央深さでの音速 [m/s]。プロファイルはここを軸に対称に置く。
C_MID = 1500.0

#: ビーム角(鉛直から、度)。±70 度・1 度刻み = 141 本。
BEAM_DEG = np.arange(-70.0, 70.001, 1.0)

#: 送受波器の周波数 [Hz] と素子数。浅海用 200 kHz、素子は λ/2 間隔。
FREQ_HZ = 200.0e3
N_ELEM = 96

#: エコー包絡線の標本化周波数 [Hz] とパルス長 [s]。
ECHO_FS = 48.0e3
PULSE_S = 150.0e-6

#: IHO S-44 第 6 版の鉛直不確かさ係数 ``(a [m], b [-])``。TVU = √(a² + (b d)²)。
IHO_ORDERS = {"Special": (0.25, 0.0075), "Order 1a": (0.5, 0.013),
              "Order 2": (1.0, 0.023)}

#: この PoC の判定に使う等級。
ORDER = "Order 1a"


def tvu(depth, order: str = ORDER) -> float:
    """IHO S-44 の許容鉛直不確かさ [m](95 % 信頼水準)。"""
    a, b = IHO_ORDERS[order]
    return float(np.hypot(a, b * np.asarray(depth, float)))


# --------------------------------------------------------------------------- #
# 音速プロファイル —— 真値も仮定も同じ形で持つ                                  #
# --------------------------------------------------------------------------- #
def profile_linear(delta_c: float, depth: float, c_mid: float = C_MID,
                   z_max: float | None = None):
    """一定勾配の c(z)。``(z ノード, c ノード)``。

    水柱 ``depth`` の全体で音速が ``delta_c`` だけ変わる形。勾配
    ``g = delta_c / depth`` [1/s] は下端より深い所まで**そのまま延長**する
    (処理側が走時を使い切るまで進めるように)。
    """
    g = delta_c / depth
    c0 = c_mid - 0.5 * delta_c
    zm = float(z_max if z_max is not None else 1.8 * depth + 20.0)
    return np.array([0.0, zm]), np.array([c0, c0 + g * zm])


def profile_constant(c: float, z_max: float = 400.0):
    """等音速(対照群、および「表面の音速だけ」の仮定)。"""
    return np.array([0.0, z_max]), np.array([float(c), float(c)])


def profile_thermocline(z_max: float = 400.0):
    """混合層 + サーモクライン + 深層。**一定勾配では書けない構造**を 1 本混ぜる。

    乱数ではなく段のある形にするのは、一定勾配の当てはめが「平均としては
    合っているのに形が違う」ときに何が残るかを見るため。
    """
    z = np.array([0.0, 8.0, 10.0, 22.0, 30.0, z_max])
    c = np.array([1522.0, 1521.4, 1512.0, 1486.0, 1483.4, 1482.0])
    return z, c


def sound_speed(prof, z):
    """プロファイルを線形補間して深さ z [m] の音速 [m/s]。"""
    zn, cn = prof
    return np.interp(np.asarray(z, float), zn, cn)


def _segments(prof, z_target: float):
    """``[0, z_target]`` を覆う層の ``(z1, z2, c1, c2)``。境界に z_target を足す。"""
    zn, cn = prof
    edges = np.unique(np.concatenate([zn[(zn > 0.0) & (zn < z_target)],
                                      [0.0, float(z_target)]]))
    ce = np.interp(edges, zn, cn)
    return edges[:-1], edges[1:], ce[:-1], ce[1:]


# --------------------------------------------------------------------------- #
# レイトレース —— 一定勾配の層は円弧に閉じる                                    #
# --------------------------------------------------------------------------- #
#: 勾配が実質ゼロとみなす閾値 [1/s]。これ未満は直線として扱う。
G_TINY = 1e-12


def trace_to_depth(prof, theta_deg, z_target: float):
    """射出角 ``theta_deg``(鉛直から、度)の光線を深さ ``z_target`` まで撃つ。

    返り値 ``(x, t, ok)`` —— 水平距離 [m]、**片道**走時 [s]、届いたか。
    層内で音速が 1 次なら、Snell の不変量 p = sinθ/c を使って

    * x += p (c₁+c₂) Δz / (cosθ₁ + cosθ₂)   —— 円弧の弦(勾配 0 でも成立)
    * t += ln[(c₂/c₁)(1+cosθ₁)/(1+cosθ₂)] / g

    と閉形式で積める。**桁落ちを避けた形にしてある**: 素直な
    ``(cosθ₁-cosθ₂)/(g p)`` や ``arctanh`` の差は、直下付近で 1 - 1 になる。

    ``|p c| >= 1`` になる層があると光線はそこで**反転**して海底に届かない
    (上向き屈折の外側ビーム)。その列は ``ok=False`` で返す。
    """
    z1a, z2a, c1a, c2a = _segments(prof, z_target)
    th = np.radians(np.asarray(theta_deg, float))
    p = np.sin(th) / float(c1a[0])
    u = np.cos(th).astype(np.float64)             # cosθ(現在の深さ)
    x = np.zeros_like(u)
    t = np.zeros_like(u)
    ok = np.ones(u.shape, bool)
    for z1, z2, c1, c2 in zip(z1a, z2a, c1a, c2a):
        dz = float(z2 - z1)
        if dz <= 0.0:
            continue
        s2 = p * c2
        ok &= np.abs(s2) < 1.0                    # 反転(turning point)
        u2 = np.sqrt(np.clip(1.0 - s2 * s2, 0.0, 1.0))
        den = np.where(u + u2 > 1e-12, u + u2, 1.0)
        x = x + p * (c1 + c2) * dz / den
        g = (c2 - c1) / dz
        if abs(g) > G_TINY:
            t = t + np.log((c2 / c1) * (1.0 + u) / (1.0 + u2)) / g
        else:
            t = t + dz / (c1 * np.maximum(u, 1e-12))
        u = u2
    return x, t, ok


def trace_for_time(prof, theta_deg, t_one_way):
    """**処理側**の光線: 片道走時 ``t_one_way`` だけ進んだ点 ``(x, z, ok)``。

    測深機が測るのは往復時間とビーム角だけなので、深さは「仮定した
    プロファイルの中を、その時間だけ進んだ先」として出す。これが実務の
    レイトレース処理そのもの。仮定が等音速なら直線 z = c t cosθ に退化する。
    """
    zn, _cn = prof
    z1a, z2a, c1a, c2a = _segments(prof, float(zn[-1]))
    th = np.radians(np.asarray(theta_deg, float))
    p = np.sin(th) / float(c1a[0])
    vertical = np.abs(p) < 1e-14                  # 直下ビーム(arctanh が発散する)
    u = np.cos(th).astype(np.float64)
    x = np.zeros_like(u)
    z = np.zeros_like(u)
    rem = np.asarray(t_one_way, float) * np.ones_like(u)
    ok = np.ones(u.shape, bool)
    for z1, z2, c1, c2 in zip(z1a, z2a, c1a, c2a):
        dz = float(z2 - z1)
        if dz <= 0.0:
            continue
        g = (c2 - c1) / dz
        s2 = p * c2
        u2 = np.sqrt(np.clip(1.0 - s2 * s2, 0.0, 1.0))
        if abs(g) > G_TINY:
            with np.errstate(divide="ignore", invalid="ignore"):
                dt_full = np.log((c2 / c1) * (1.0 + u) / (1.0 + u2)) / g
        else:
            dt_full = dz / (c1 * np.maximum(u, 1e-12))
        # 層の底まで届かない(反転する)列は、残り時間をこの層で使い切る。
        dt_full = np.where(np.abs(s2) >= 1.0, np.inf, dt_full)
        dt = np.minimum(rem, np.where(np.isfinite(dt_full), dt_full, rem))
        live = dt > 0.0                           # まだ走時が残っている列だけ動かす
        if abs(g) > G_TINY:
            # 層内で dt だけ進んだ後の cosθ は tanh(arctanh(cosθ) − g·dt)。
            a = np.arctanh(np.clip(u, -1.0 + 1e-14, 1.0 - 1e-14))
            u_new = np.tanh(a - g * dt)
            c_new = np.where(vertical, c1 * np.exp(g * dt),
                             np.sqrt(np.clip(1.0 - u_new * u_new, 0.0, 1.0))
                             / np.maximum(np.abs(p), 1e-300))
            u_new = np.where(vertical, 1.0, u_new)
            dz_step = (c_new - c1) / g
        else:
            u_new = u
            c_new = np.full_like(u, c1)
            dz_step = c1 * dt * u
        dz_step = np.where(live, dz_step, 0.0)
        den = np.where(u + u_new > 1e-12, u + u_new, 1.0)
        x = x + np.where(live, p * (c1 + c_new) * dz_step / den, 0.0)
        z = z + dz_step
        ok &= ~(live & (u_new <= 1e-9))            # 反転した = 下へ進んでいない
        u = np.where(live, u_new, u)
        rem = np.maximum(rem - dt, 0.0)
    return x, z, ok


# --------------------------------------------------------------------------- #
# 閉形式 —— 測る前に印字する予測                                                #
# --------------------------------------------------------------------------- #
def harmonic_mean_speed(delta_c: float, depth: float, c_mid: float = C_MID) -> float:
    """直下ビームを合わせる平均音速 [m/s]。``D / t(0)`` = 調和平均。"""
    g = delta_c / depth
    c0 = c_mid - 0.5 * delta_c
    if abs(g) < G_TINY:
        return float(c0)
    return float(g * depth / math.log((c0 + g * depth) / c0))


def smile_exact(theta_deg, delta_c: float, depth: float, c_mid: float = C_MID):
    """直下較正した等音速処理の深さ誤差 [m]。**厳密な円弧の閉形式**。

    z/D = cosθ₀·[arctanh(cosθ₀) − arctanh(√(1−k²sin²θ₀))] / ln k、k = c_D/c₀。
    数値は :func:`trace_to_depth` と同じ式から出るが、**層に切らずに 1 本**で
    書けるところが違う(実務のレイトレースはここを層で刻む)。
    """
    g = delta_c / depth
    c0 = c_mid - 0.5 * delta_c
    if abs(g) < G_TINY:
        return np.zeros_like(np.asarray(theta_deg, float))
    k = (c0 + g * depth) / c0
    th = np.radians(np.asarray(theta_deg, float))
    u0 = np.cos(th)
    s = np.sin(th)
    ud = np.sqrt(np.clip(1.0 - (k * s) ** 2, 0.0, 1.0))
    t = np.log(k * (1.0 + u0) / (1.0 + ud)) / g
    ca = harmonic_mean_speed(delta_c, depth, c_mid)
    return ca * t * u0 - depth


def smile_tan2(theta_deg, delta_c: float, depth: float, c_mid: float = C_MID):
    """同じ量の**ラフな展開式** Δz ≈ (g D²/2c₀)·tan²θ₀。

    ε = gD/c₀ の 2 次まで取ると、直下較正した処理の誤差はこの 1 行になる。
    現場の勘所(「外側は角度の 2 乗で効く」)はここから来ている。
    """
    g = delta_c / depth
    c0 = c_mid - 0.5 * delta_c
    return (g * depth * depth / (2.0 * c0)) * np.tan(np.radians(
        np.asarray(theta_deg, float))) ** 2


def cliff_from_tan2(delta_c: float, depth: float, order: str = ORDER,
                    c_mid: float = C_MID) -> float:
    """展開式から出した崖の角度 [度](|Δz| = TVU になる θ₀)。"""
    g = delta_c / depth
    c0 = c_mid - 0.5 * delta_c
    coef = abs(g) * depth * depth / (2.0 * c0)
    if coef <= 0.0:
        return float("inf")
    v = tvu(depth, order) / coef
    return float(math.degrees(math.atan(math.sqrt(v))))


def cliff_from_exact(delta_c: float, depth: float, order: str = ORDER,
                     c_mid: float = C_MID, hi: float = 89.0) -> float:
    """厳密式から出した崖の角度 [度]。二分法で |Δz(θ)| = TVU を解く。"""
    lim = tvu(depth, order)
    if abs(smile_exact(hi, delta_c, depth, c_mid)) < lim:
        return float("inf")
    lo = 0.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if abs(float(smile_exact(mid, delta_c, depth, c_mid))) < lim:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def cliff_deep_asymptote(delta_c: float, order: str = ORDER,
                         c_mid: float = C_MID) -> float:
    """深水での崖の角度の漸近値 [度]。

    許容 TVU の深さ比例項 b·d と、屈折誤差 (Δc·d/2c₀)tan²θ の**どちらも
    深さに比例する**ので、深水では d が消えて
    tan²θ = 2 b c₀ / |Δc| —— **崖の角度が深さに依らなくなる**。
    """
    b = IHO_ORDERS[order][1]
    c0 = c_mid - 0.5 * delta_c
    return float(math.degrees(math.atan(math.sqrt(2.0 * b * c0 / abs(delta_c)))))


def turning_angle(delta_c: float, depth: float, c_mid: float = C_MID) -> float:
    """海底に届く最大の射出角 [度]。``arcsin(c₀ / c_max)``、下向き屈折なら inf。"""
    if delta_c <= 0.0:
        return float("inf")
    c0 = c_mid - 0.5 * delta_c
    return float(math.degrees(math.asin(min(1.0, c0 / (c0 + delta_c)))))


# --------------------------------------------------------------------------- #
# 配列とビーム形成 —— fullseye の op をそのまま使う                             #
# --------------------------------------------------------------------------- #
#: ビーム形成の角度グリッド [度]。0.05 度刻み(3601 点)。
ANGLE_GRID = np.arange(-90.0, 90.001, 0.05)


def array_snapshot(theta_deg: float, wavelength: float, spacing: float,
                   n_elem: int = N_ELEM):
    """一様直線配列に平面波が角度 ``theta_deg`` から来たときの素子ごとの複素値。"""
    k = np.arange(n_elem, dtype=np.float64)
    return np.exp(1j * 2.0 * np.pi * spacing * k
                  * math.sin(math.radians(theta_deg)) / wavelength)


def as_beat_cube(snapshot):
    """``beamform_*`` が要求する ``(素子, チャープ, 高速時間)`` の立方体に詰める。

    ★ここが**電波レーダの語彙を音響に読み替える**地点。op は FMCW レーダ用で、
    立方体の 2 軸目(チャープ = 遅い時間)と 3 軸目(高速時間)を FFT して
    レンジ-ドップラー面を作り、その 1 セルの素子方向スナップショットを
    ビーム形成する。**パルス測深機にレンジ-ドップラー面は無い**(ビート
    周波数が距離になるのは FMCW だけ)ので、2 軸目・3 軸目を最小の 2 に
    潰して**縮退した 1 セル**にし、**角度スペクトルだけ**を使う。
    その結果 ``range_m`` / ``velocity_ms`` は ``None`` で返り、
    ``range_bin`` / ``doppler_bin`` は 0 —— **意味のある量ではない**ので
    読まない。読み替えが成り立つのは「一様直線配列 + 狭帯域 + 平面波 +
    素子間位相 2πd sinθ/λ」の部分だけで、そこは音波でも電波でも同じ式。
    """
    a = np.asarray(snapshot, complex)
    cube = np.zeros((a.size, 2, 2), complex)
    cube[:, :, :] = a[:, None, None]
    return cube


def beam_pattern(theta_deg: float, wavelength: float, spacing: float,
                 n_elem: int = N_ELEM, grid=ANGLE_GRID):
    """角度スペクトル(正規化)。``fs.ledger.beamform_delay_sum`` をそのまま。"""
    cube = as_beat_cube(array_snapshot(theta_deg, wavelength, spacing, n_elem))
    return np.asarray(fs.ledger.beamform_delay_sum(
        cube, wavelength_m=wavelength, element_spacing_m=spacing,
        angles_deg=grid, normalize=True), np.float64)


def half_power_width(power, grid=ANGLE_GRID) -> float:
    """角度スペクトルの -3 dB 幅 [度](ピークから両側へ半値まで歩く)。"""
    i = int(np.argmax(power))
    half = 0.5 * float(power[i])
    lo = i
    while lo > 0 and power[lo] > half:
        lo -= 1
    hi = i
    while hi < power.size - 1 and power[hi] > half:
        hi += 1
    return float(grid[hi] - grid[lo])


# --------------------------------------------------------------------------- #
# エコー検出 —— 1-D 信号の op をそのまま使う                                    #
# --------------------------------------------------------------------------- #
#: ビーム軸から何ビーム幅ぶんの海底をエコーに入れるか(片側)。
ECHO_SPAN_BW = 1.5

#: エコーを合成する部分角の本数。★これを 61 にすると、70 度では隣り合う
#: 部分角の到来時間が 330 µs 離れ、パルス幅 64 µs より広くなるので、包絡線が
#: **櫛**になって振幅検出が歯を 1 本拾う(検出のずれが -1131 µs と出た)。
#: 到来時間の密度をヒストグラムで作り、パルスで畳むほうが正しい。
ECHO_N_SUB = 4001


def echo_envelope(prof, theta_deg: float, wavelength: float, spacing: float,
                  bw0: float, depth: float = DEPTH_REF):
    """受信包絡線を**ビームが照らす海底を足し上げて**作る。

    ★ここが素直な「τ にガウスを 1 個置く」との違い。ビームは 1 点でなく
    **帯**を照らすので、エコーはその帯の往復時間の分布になる。重みは

    * 配列の角度応答 —— :func:`beam_pattern`(= ``beamform_delay_sum``)を
      そのまま部分角の位置で読む。**自分の配列の実測パターンを使う**。
    * 後方散乱の Lambert 則 cosθ —— 斜めに当たるほど返りが弱い。

    往復時間 τ(φ) は角度に対して**凸**なので、対称なビームでも
    エコーは非対称になり、振幅検出の頂点はビーム軸の τ とずれる。
    返り値は ``(包絡線, 窓の先頭の時刻 [s], ビーム軸の往復時間 [s])``。
    """
    bw = bw0 / math.cos(math.radians(theta_deg))
    lo = max(0.0, theta_deg - ECHO_SPAN_BW * bw)
    hi = min(88.0, theta_deg + ECHO_SPAN_BW * bw)
    sub = np.linspace(lo, hi, ECHO_N_SUB)
    _, t_sub, ok_sub = trace_to_depth(prof, sub, depth)
    patt = beam_pattern(theta_deg, wavelength, spacing)
    w = np.interp(sub, ANGLE_GRID, patt) * np.cos(np.radians(sub))
    w = np.where(ok_sub, w, 0.0)
    tau = 2.0 * t_sub
    _, t_ax, _ = trace_to_depth(prof, np.array([theta_deg]), depth)
    tau_axis = 2.0 * float(t_ax[0])
    half = int(1.4 * float(np.max(np.abs(tau - tau_axis))) * ECHO_FS) + 64
    i0 = int(round(tau_axis * ECHO_FS)) - half
    idx = np.arange(i0, i0 + 2 * half + 1, dtype=np.float64) / ECHO_FS
    sigma = PULSE_S / 2.355
    env = (w[:, None] * np.exp(-0.5 * ((idx[None, :] - tau[:, None]) / sigma) ** 2)
           ).sum(axis=0)
    return env / max(float(env.max()), 1e-300), i0 / ECHO_FS, tau_axis


def detect_two_way(env, t_start: float, fs_hz: float = ECHO_FS) -> float:
    """振幅検出 —— ``find_peaks`` で山を拾い、``peak_subbin`` で標本の間へ。"""
    idx = np.asarray(fs.ledger.find_peaks(env, height=0.5), np.int64)
    if idx.size == 0:
        return float("nan")
    best = int(idx[int(np.argmax(env[idx]))])
    sub = float(np.asarray(fs.peak_subbin(env, np.array([best]), mode="gauss"))[0])
    return t_start + sub / fs_hz


# --------------------------------------------------------------------------- #
def _pct(v, ref):
    return 100.0 * (v - ref) / ref


# --------------------------------------------------------------------------- #
# 1. 場面 —— 真値を植え、閉形式とレイトレースを突き合わせる                      #
# --------------------------------------------------------------------------- #
def section_scene():
    print("=== 1. 場面 —— 平らな海底と、線形の音速プロファイル ===")
    prof = profile_linear(DELTA_C_REF, DEPTH_REF)
    c0 = float(sound_speed(prof, 0.0))
    cb = float(sound_speed(prof, DEPTH_REF))
    g = DELTA_C_REF / DEPTH_REF
    ca = harmonic_mean_speed(DELTA_C_REF, DEPTH_REF)
    print(f"  海底 深さ {DEPTH_REF:.1f} m の完全な水平面(真値)")
    print(f"  音速 表層 {c0:.1f} m/s → 海底 {cb:.1f} m/s、勾配 g = {g:+.3f} /s")
    print(f"  直下ビームを合わせる平均音速(調和平均)= {ca:.3f} m/s")
    print(f"  IHO S-44 {ORDER} の TVU({DEPTH_REF:.0f} m) = {tvu(DEPTH_REF):.4f} m")
    # 光線の円弧半径(閉形式)。R = c / (g sinθ) = 1/(g p)。
    for th in (30.0, 60.0):
        p = math.sin(math.radians(th)) / c0
        print(f"  射出角 {th:.0f} 度の光線は半径 R = 1/(g p) = {abs(1.0/(g*p)):.0f} m "
              f"の円弧(直線ではない)")
    # 層に切ったレイトレースが閉形式と一致するか(層数を変えても動かないはず)
    x_ref, t_ref, ok = trace_to_depth(prof, BEAM_DEG, DEPTH_REF)
    assert bool(np.all(ok))
    worst = 0.0
    for n_layer in (1, 4, 32, 256):
        zn = np.linspace(0.0, float(prof[0][-1]), n_layer + 1)
        sub = (zn, np.interp(zn, prof[0], prof[1]))
        _, t_l, _ = trace_to_depth(sub, BEAM_DEG, DEPTH_REF)
        worst = max(worst, float(np.max(np.abs(t_l - t_ref))))
        print(f"  層 {n_layer:>4} 枚に切ったレイトレース: 走時の差 "
              f"{float(np.max(np.abs(t_l - t_ref))):.3e} s")
    print("  → 層内の音速が 1 次なら、層に切っても走時は動かない(円弧が厳密だから)。")
    return {"prof": prof, "c0": c0, "cb": cb, "g": g, "ca": ca,
            "x": x_ref, "t": t_ref, "layer_worst": worst}


# --------------------------------------------------------------------------- #
# 2. 測定系の床 —— 角度もエコーも、屈折より 3 桁小さい                           #
# --------------------------------------------------------------------------- #
def section_floor(scene):
    print("\n=== 2. 床を測る —— 角度推定とエコー検出は、どれだけ効くか ===")
    lam = C_MID / FREQ_HZ
    d = 0.5 * lam
    print(f"  {FREQ_HZ/1e3:.0f} kHz / 音速 {C_MID:.0f} m/s → λ = {1000*lam:.3f} mm、"
          f"素子 {N_ELEM} 本を λ/2 = {1000*d:.3f} mm 間隔(開口 {N_ELEM*d:.3f} m)")
    # (a) 角度推定の床 —— beamform_doa
    rows, err_ang = [], []
    for th in (0.0, 10.0, 30.0, 45.0, 60.0, 70.0):
        cube = as_beat_cube(array_snapshot(th, lam, d))
        r = fs.ledger.beamform_doa(cube, wavelength_m=lam, element_spacing_m=d,
                                   angles_deg=ANGLE_GRID)
        got = float(r["angles_deg"][0])
        err_ang.append(abs(got - th))
        rows.append((f"{th:.1f}", f"{got:.3f}", f"{got - th:+.4f}",
                     f"{float(r['angular_resolution_deg']):.4f}"))
        print(f"  ステア {th:5.1f} 度 → beamform_doa {got:8.3f} 度 "
              f"(誤差 {got - th:+.4f})、報告するビーム幅 "
              f"{float(r['angular_resolution_deg']):.4f} 度")
    print(f"  ★ range_m / velocity_ms は {r['range_m']} / {r['velocity_ms']} "
          f"—— レンジ-ドップラーは音響パルスに無いので**読まない**(§10)")
    # 角度誤差が深さに効く量: dz = -r sinθ dθ
    slant = DEPTH_REF / math.cos(math.radians(60.0))
    dz_ang = slant * math.sin(math.radians(60.0)) * math.radians(max(err_ang) or 1e-4)
    print(f"  → 角度誤差の最大 {max(err_ang):.4f} 度 は、60 度・{DEPTH_REF:.0f} m で "
          f"深さ {dz_ang:.4f} m 相当")
    # (b) エコー検出の床 —— find_peaks + peak_subbin
    prof = scene["prof"]
    rows_e, err_t = [], []
    bw0 = half_power_width(beam_pattern(0.0, lam, d))
    print(f"  {'ビーム [度]':>12}{'往復 [µs]':>12}{'エコー長 [µs]':>14}"
          f"{'検出のずれ [µs]':>16}{'深さ換算 [m]':>14}")
    for th in (0.0, 30.0, 45.0, 60.0, 70.0):
        env, t0e, tau_axis = echo_envelope(prof, th, lam, d, bw0)
        got = detect_two_way(env, t0e)
        # エコーの長さ(半値幅)を測る。ビームが照らす帯の往復時間の幅。
        above = np.where(env > 0.5)[0]
        length = (float(above[-1] - above[0]) / ECHO_FS) if above.size else 0.0
        dz = 0.5 * scene["ca"] * (got - tau_axis) * math.cos(math.radians(th))
        err_t.append(abs(dz))
        rows_e.append((f"{th:.0f}", f"{1e6*tau_axis:.1f}", f"{1e6*length:.1f}",
                       f"{1e6*(got-tau_axis):+.2f}", f"{dz:+.5f}"))
        print(f"  {th:>12.0f}{1e6*tau_axis:>12.1f}{1e6*length:>14.1f}"
              f"{1e6*(got-tau_axis):>16.2f}{dz:>14.5f}")
    print(f"  → 標本間隔 {1e6/ECHO_FS:.2f} µs(深さ {0.5*C_MID/ECHO_FS*100:.2f} cm)を、"
          f"peak_subbin が標本の間へ落としている。")
    print(f"  ★**床は角度 {dz_ang:.4f} m / エコー {max(err_t):.4f} m**。")
    print("     ★エコーの床は直下では µs 未満だが、外側では**ビームが照らす帯**が")
    print("     長くなり、しかも往復時間が角度に対して凸なのでエコーが非対称になる。")
    print("     振幅検出の頂点はビーム軸からずれる —— 外側で位相検出へ切り替える理由。")
    figs.save_table("floor", ["ビーム角 [度]", "往復時間 [µs]", "エコー長 [µs]",
                              "検出のずれ [µs]", "深さ換算 [m]"], rows_e,
                    title="測定系の床 —— 角度推定とエコー検出は深さに何 m 効くか",
                    caption="エコーは beamform_delay_sum の角度応答 × Lambert 後方散乱で"
                            "海底の帯を足し上げて合成。find_peaks + peak_subbin で検出。")
    if figs.enabled():
        series = []
        for th in (0.0, 45.0, 70.0):
            env, t0e, tau_axis = echo_envelope(prof, th, lam, d, bw0)
            tt = 1e6 * ((np.arange(env.size) / ECHO_FS + t0e) - tau_axis)
            series.append((f"ビーム {th:.0f} 度", tt, env))
        figs.save_plot("echo", series, xlabel="ビーム軸の往復時間からのずれ [µs]",
                       ylabel="正規化した受信包絡線",
                       title="外側ビームのエコーは長く、そして非対称",
                       caption="直下は 1 本のパルス。70 度では帯が数十 µs に伸び、"
                               "頂点がビーム軸からずれる。")
    return {"lam": lam, "d": d, "ang_rows": rows, "err_ang": max(err_ang),
            "dz_ang": dz_ang, "err_echo": max(err_t), "bw0": bw0}


# --------------------------------------------------------------------------- #
# 3. ゼロ点 —— 表面の音速だけを定数と仮定する                                    #
# --------------------------------------------------------------------------- #
def section_null(scene):
    print("\n=== 3. ゼロ点 —— 表面の音速計だけを見て、定数と仮定する ===")
    prof = scene["prof"]
    _, t1, ok = trace_to_depth(prof, BEAM_DEG, DEPTH_REF)
    assert bool(np.all(ok))
    out = {}
    for name, ca in (("表面音速 c₀", scene["c0"]),
                     ("水柱の平均(算術)", 0.5 * (scene["c0"] + scene["cb"])),
                     ("直下較正(調和平均)", scene["ca"])):
        z = ca * t1 * np.cos(np.radians(BEAM_DEG))
        dz = z - DEPTH_REF
        nadir = float(dz[int(np.argmin(np.abs(BEAM_DEG)))])
        edge = float(dz[-1])
        out[name] = {"ca": ca, "dz": dz, "nadir": nadir, "edge": edge}
        print(f"  {name:>18}(c_a = {ca:8.3f} m/s): 直下 {nadir:+.3f} m / "
              f"65 度 {float(dz[np.argmin(np.abs(BEAM_DEG-65.0))]):+.3f} m / "
              f"70 度 {edge:+.3f} m")
    lim = tvu(DEPTH_REF)
    print(f"  TVU({DEPTH_REF:.0f} m) = {lim:.4f} m")
    n0 = out["表面音速 c₀"]["nadir"]
    print(f"  → ★ゼロ点は**直下ビームからもう** TVU の {100*abs(n0)/lim:.0f} % を"
          f"食い潰している({n0:+.3f} m)。")
    print("  → ★直下較正すると直下の誤差は 0 になるが、外側は残る —— "
          "**誤差が消えたのではなく、検査されない所へ移った**。")
    print("     現場は直下の深さをバーチェックや錘で確かめる。**直る所だけ直る**。")
    return out


# --------------------------------------------------------------------------- #
# 4. 崖 —— 閉形式で予測してから、全経路を通して測る                              #
# --------------------------------------------------------------------------- #
def section_cliff(scene, floor):
    print("\n=== 4. 崖 —— 何度から IHO S-44 を割るか。予測を先に印字する ===")
    pred_tan2 = cliff_from_tan2(DELTA_C_REF, DEPTH_REF)
    pred_exact = cliff_from_exact(DELTA_C_REF, DEPTH_REF)
    print(f"  予測(ラフな展開 Δz ≈ (gD²/2c₀)tan²θ): 崖 = {pred_tan2:.2f} 度")
    print(f"  予測(厳密な円弧の閉形式)          : 崖 = {pred_exact:.2f} 度")
    print("  ↑ ここまでは測る前。以下が実測。")
    prof = scene["prof"]
    lam, d = floor["lam"], floor["d"]
    # 全経路: ビーム形成で角度 → レイトレースで走時 → エコー検出 → 等音速で処理
    ths = np.arange(0.0, 71.0, 1.0)
    meas, exact, tan2 = [], [], []
    for th in ths:
        cube = as_beat_cube(array_snapshot(th, lam, d))
        r = fs.ledger.beamform_doa(cube, wavelength_m=lam, element_spacing_m=d,
                                   angles_deg=ANGLE_GRID)
        th_m = float(r["angles_deg"][0])
        env, t0e, _ = echo_envelope(prof, th, lam, d, floor["bw0"])
        tau_m = detect_two_way(env, t0e)
        meas.append(0.5 * scene["ca"] * tau_m * math.cos(math.radians(th_m)) - DEPTH_REF)
        exact.append(float(smile_exact(th, DELTA_C_REF, DEPTH_REF)))
        tan2.append(float(smile_tan2(th, DELTA_C_REF, DEPTH_REF)))
    meas = np.array(meas)
    exact = np.array(exact)
    tan2 = np.array(tan2)
    lim = tvu(DEPTH_REF)
    # 実測の崖は 0.01 度刻みで補間して読む(1 度刻みの格子で崖を切らないため)
    fine = np.arange(0.0, 70.001, 0.01)
    meas_i = np.interp(fine, ths, np.abs(meas))
    cliff_meas = float(fine[int(np.argmax(meas_i > lim))]) if (meas_i > lim).any() \
        else float("inf")
    print(f"  {'θ₀ [度]':>8}{'実測 Δz [m]':>14}{'厳密式':>12}{'展開式':>12}"
          f"{'展開の外し':>12}")
    rows = []
    for th in (0.0, 20.0, 40.0, 45.0, 50.0, 60.0, 65.0, 70.0):
        i = int(np.argmin(np.abs(ths - th)))
        rows.append((f"{th:.0f}", f"{meas[i]:+.4f}", f"{exact[i]:+.4f}",
                     f"{tan2[i]:+.4f}", f"{100*(tan2[i]-exact[i])/exact[i]:+.1f} %"
                     if exact[i] != 0 else "—"))
        print(f"  {th:>8.0f}{meas[i]:>14.4f}{exact[i]:>12.4f}{tan2[i]:>12.4f}"
              f"{(100*(tan2[i]-exact[i])/exact[i] if exact[i] else 0.0):>11.1f}%")
    print(f"  → 実測の崖 **{cliff_meas:.2f} 度**。厳密式の予測 {pred_exact:.2f} 度 は"
          f"**当たり**、展開式の予測 {pred_tan2:.2f} 度 は "
          f"**{pred_exact - pred_tan2:+.2f} 度 外した**。")
    ratio70 = abs(tan2[-1] / exact[-1])
    print(f"  → ★展開式は 45 度までは "
          f"{abs(100*(tan2[45]-exact[45])/exact[45]):.1f} % 以内だが、"
          f"70 度では {100*(ratio70-1):.1f} % 過大。"
          f"**「tan² で効く」は外側で崩れる**。")
    print(f"  → 実測(全経路)と厳密式の差は最大 "
          f"{float(np.max(np.abs(meas - exact))):.5f} m —— §2 で測った床の大きさ。")
    figs.save_table("cliff", ["θ₀ [度]", "実測 Δz [m]", "厳密式 [m]", "展開式 [m]",
                              "展開の外し"], rows,
                    title="スマイルの大きさ —— 実測 / 厳密式 / ラフな展開式",
                    caption=f"深さ {DEPTH_REF:.0f} m・音速差 {DELTA_C_REF:+.0f} m/s。"
                            f"TVU = {lim:.3f} m を割るのは {cliff_meas:.2f} 度から。")
    if figs.enabled():
        x_at = DEPTH_REF * np.tan(np.radians(ths))
        figs.save_plot(
            "smile",
            [("実測(全経路)", x_at, meas),
             ("厳密な円弧の閉形式", x_at, exact),
             ("ラフな展開 tan²", x_at, tan2),
             ("IHO %s の許容(-)" % ORDER, x_at, np.full_like(x_at, -lim))],
            xlabel="航跡直交距離 [m]", ylabel="深さの誤差 [m](負 = 浅く出る)",
            title="平らな海底が笑う —— 外側ビームだけが浮き上がる",
            caption=f"直下は較正済みで 0。{cliff_meas:.1f} 度(直交距離 "
                    f"{DEPTH_REF*math.tan(math.radians(cliff_meas)):.1f} m)から "
                    f"IHO {ORDER} を割る。展開式は外側で過大に予測する。")
    return {"ths": ths, "meas": meas, "exact": exact, "tan2": tan2,
            "pred_tan2": pred_tan2, "pred_exact": pred_exact,
            "cliff": cliff_meas, "lim": lim,
            "path_gap": float(np.max(np.abs(meas - exact)))}


# --------------------------------------------------------------------------- #
# 5. 対照群 —— 要因を 1 つずつ止める                                            #
# --------------------------------------------------------------------------- #
def section_controls(scene, floor):
    print("\n=== 5. 対照群 —— 要因を 1 つずつ止める ===")
    lam, d = floor["lam"], floor["d"]
    th_edge = 65.0
    rows = []

    def run(prof, use_beamform, use_echo, ca):
        """1 本のビームを、指定した経路だけ通して深さを出す。"""
        th_m = th_edge
        if use_beamform:
            cube = as_beat_cube(array_snapshot(th_edge, lam, d))
            r = fs.ledger.beamform_doa(cube, wavelength_m=lam, element_spacing_m=d,
                                       angles_deg=ANGLE_GRID)
            th_m = float(r["angles_deg"][0])
        _, t1, _ = trace_to_depth(prof, np.array([th_edge]), DEPTH_REF)
        tau = 2.0 * float(t1[0])
        if use_echo:
            env, t0e, _ = echo_envelope(prof, th_edge, lam, d, floor["bw0"], DEPTH_REF)
            tau = detect_two_way(env, t0e)
        return 0.5 * ca * tau * math.cos(math.radians(th_m)) - DEPTH_REF

    flat = profile_constant(C_MID)
    cases = [
        ("勾配ゼロ + 真の平均音速(何も無い)", flat, False, False, C_MID),
        ("角度推定だけ入れる", flat, True, False, C_MID),
        ("エコー検出だけ入れる", flat, False, True, C_MID),
        ("角度 + エコー(屈折なし)", flat, True, True, C_MID),
        ("屈折だけ入れる(直下較正)", scene["prof"], False, False, scene["ca"]),
        ("全部入れる", scene["prof"], True, True, scene["ca"]),
    ]
    out = {}
    for name, prof, ub, ue, ca in cases:
        dz = run(prof, ub, ue, ca)
        out[name] = dz
        rows.append((name, f"{dz:+.6f}"))
        print(f"  {name:<36}{dz:>+12.6f} m")
    only_ang = abs(out["角度推定だけ入れる"])
    only_echo = abs(out["エコー検出だけ入れる"])
    only_ref = abs(out["屈折だけ入れる(直下較正)"])
    print(f"  → ★屈折 {only_ref:.4f} m に対し、角度 {only_ang:.6f} m / "
          f"エコー {only_echo:.6f} m。比は "
          f"{only_ref/max(only_ang, 1e-12):.0f} 倍 / "
          f"{only_ref/max(only_echo, 1e-12):.0f} 倍。")
    print("     **スマイルは角度誤差でもエコー検出誤差でもない**。屈折そのもの。")
    figs.save_table("controls", ["止めずに入れた要因", "65 度での深さ誤差 [m]"], rows,
                    title="対照群 —— 要因を 1 つずつ入れる",
                    caption="勾配ゼロ + 真の平均音速がゼロ点。屈折だけが m の単位で効く。")
    return out


# --------------------------------------------------------------------------- #
# 6. 掃引 —— 200 ケースで崖の位置を測り、深水の漸近を確かめる                     #
# --------------------------------------------------------------------------- #
def section_sweep():
    print("\n=== 6. 掃引 —— 音速差 25 通り × 深さ 8 通り = 200 ケース ===")
    deltas = np.arange(-60.0, 60.001, 5.0)          # 25 通り(0 を含む = 対照群)
    depths = np.array([10.0, 20.0, 30.0, 50.0, 70.0, 100.0, 150.0, 200.0])
    print(f"  音速差 {deltas.min():+.0f} 〜 {deltas.max():+.0f} m/s({deltas.size} 通り)"
          f" × 深さ {depths.min():.0f} 〜 {depths.max():.0f} m({depths.size} 通り)"
          f" = **{deltas.size * depths.size} ケース**(乱数ではなく格子)")
    print(f"  予測: 深水では TVU の b·d と屈折の Δc·d/2c₀ がどちらも d に比例するので、")
    print(f"        崖の角度は深さに依らなくなる —— tan²θ = 2 b c₀ / |Δc|。")
    for dc in (-40.0, -20.0, -60.0):
        print(f"        Δc = {dc:+.0f} m/s の漸近値 = "
              f"{cliff_deep_asymptote(dc):.2f} 度")
    cliffs = np.full((deltas.size, depths.size), np.inf)
    for i, dc in enumerate(deltas):
        for j, dep in enumerate(depths):
            if abs(dc) < 1e-9:
                continue                             # 対照群: 崖は無い
            cliffs[i, j] = cliff_from_exact(float(dc), float(dep))
    zero_row = int(np.argmin(np.abs(deltas)))
    assert not np.isfinite(cliffs[zero_row]).any(), "勾配ゼロに崖が立った"
    print(f"  {'深さ [m]':>10}", end="")
    for dc in (-60.0, -40.0, -20.0, -10.0):
        print(f"{'Δc=%+.0f' % dc:>12}", end="")
    print(f"{'漸近(-40)':>12}")
    rows = []
    for j, dep in enumerate(depths):
        vals = [cliffs[int(np.argmin(np.abs(deltas - dc))), j]
                for dc in (-60.0, -40.0, -20.0, -10.0)]
        print(f"  {dep:>10.0f}", end="")
        for v in vals:
            print(f"{v:>12.2f}", end="")
        print(f"{cliff_deep_asymptote(-40.0):>12.2f}")
        rows.append([f"{dep:.0f}"] + [f"{v:.2f}" for v in vals])
    asym = cliff_deep_asymptote(-40.0)
    j40 = int(np.argmin(np.abs(deltas + 40.0)))
    shallow, deep = cliffs[j40, 0], cliffs[j40, -1]
    print(f"  → ★Δc = -40 m/s で、崖は 10 m の {shallow:.2f} 度 から "
          f"200 m の {deep:.2f} 度 へ**単調に浅い角度へ寄り**、"
          f"漸近値 {asym:.2f} 度 に近づく(差 {deep - asym:+.2f} 度)。")
    print("     **浅い所のほうが swath を広く使える**。深い所は許容 TVU も"
          "大きくなるが、屈折の誤差も同じだけ大きくなるので相殺する。")
    # 65 度 swath で何 % のケースが失格になるか(率を出すので分母を明示)
    fail = 0
    total = 0
    for i, dc in enumerate(deltas):
        for j, dep in enumerate(depths):
            total += 1
            if cliffs[i, j] < 65.0:
                fail += 1
    print(f"  → ±65 度の swath を使うと、{total} ケース中 **{fail} ケース"
          f"({100*fail/total:.1f} %)** が端で {ORDER} を割る。")
    print(f"     分母は {deltas.size}×{depths.size} の格子。うち "
          f"{depths.size} ケース(Δc = 0)は原理的に崖が無い対照群。")
    figs.save_table("sweep", ["深さ [m]", "Δc=-60", "Δc=-40", "Δc=-20", "Δc=-10"],
                    rows, title="崖の角度 [度] —— 深いほど浅い角度へ寄る",
                    caption=f"Δc = -40 m/s の深水漸近値は {asym:.2f} 度。"
                            "深さと一緒に許容も誤差も増えるので、比が止まる。")
    if figs.enabled():
        series = []
        for dc in (-60.0, -40.0, -20.0, -10.0):
            i = int(np.argmin(np.abs(deltas - dc)))
            series.append((f"Δc = {dc:+.0f} m/s", depths, cliffs[i]))
        figs.save_plot("sweep_cliff", series, xlabel="水深 [m]",
                       ylabel="IHO %s を割り始める角度 [度]" % ORDER,
                       title="崖の角度は、深くなるほど浅い角度へ寄る",
                       caption="どの曲線も 2·b·c₀/|Δc| の漸近値へ落ちる。"
                               "浅い所ほど広い swath が使える。")
    return {"deltas": deltas, "depths": depths, "cliffs": cliffs,
            "asym": asym, "shallow": shallow, "deep": deep,
            "fail": fail, "total": total}


# --------------------------------------------------------------------------- #
# 7. 上向き屈折 —— 外側ビームが海底に届かない                                    #
# --------------------------------------------------------------------------- #
def section_frown():
    print("\n=== 7. 上向き屈折(frown)—— 外側ビームは海底に届かない ===")
    dc = +60.0
    prof = profile_linear(dc, DEPTH_REF)
    c0 = float(sound_speed(prof, 0.0))
    cb = float(sound_speed(prof, DEPTH_REF))
    pred = turning_angle(dc, DEPTH_REF)
    print(f"  音速 表層 {c0:.1f} → 海底 {cb:.1f} m/s(冬の沿岸や淡水層の下)。")
    print(f"  予測: sinθ = p·c は深さとともに増えるので、"
          f"θ₀ > arcsin(c₀/c_bottom) = **{pred:.2f} 度** の光線は反転して戻る。")
    ths = np.arange(0.0, 85.001, 1.0)
    _, _, ok = trace_to_depth(prof, ths, DEPTH_REF)
    last = float(ths[ok][-1]) if ok.any() else float("nan")
    first_bad = float(ths[~ok][0]) if (~ok).any() else float("nan")
    print(f"  実測: 海底に届いた最大のビームは **{last:.1f} 度**、"
          f"届かなくなる最初のビームは {first_bad:.1f} 度(1 度刻み)。")
    print(f"  → 予測 {pred:.2f} 度 はこの 2 本の間 "
          f"({last:.1f} < {pred:.2f} < {first_bad:.1f})。")
    dz = smile_exact(ths[ok], dc, DEPTH_REF)
    print(f"  → 届いたビームは**逆向きに**曲がる: 65 度で "
          f"{float(smile_exact(65.0, dc, DEPTH_REF)):+.3f} m(深く出る = frown)。")
    print("  → ★ここが厄介: 届かないビームは**深さが誤るのではなく、何も記録されない**。")
    print("     swath が黙って狭くなるだけなので、記録を見ても異常に見えない。")
    return {"pred": pred, "last": last, "first_bad": first_bad,
            "dz65": float(smile_exact(65.0, dc, DEPTH_REF)),
            "dz_max": float(np.max(np.abs(dz)))}


# --------------------------------------------------------------------------- #
# 8. フットプリント —— 教科書の cos² 式は足りない                                #
# --------------------------------------------------------------------------- #
def section_footprint(scene, floor):
    print("\n=== 8. 分解能の崖 —— フットプリントは cos² か cos³ か ===")
    lam, d = floor["lam"], floor["d"]
    bw0 = floor["bw0"]
    print(f"  自分の配列のビーム幅を実測する(beamform_delay_sum の -3 dB 幅):")
    print(f"  {'ステア [度]':>12}{'実測 -3dB [度]':>16}{'予測 0.886λ/(Nd cosθ)':>24}"
          f"{'比':>8}")
    rows_bw, widths = [], {}
    for th in (0.0, 30.0, 45.0, 60.0, 70.0):
        w = half_power_width(beam_pattern(th, lam, d))
        pred = math.degrees(0.886 * lam / (N_ELEM * d)) / math.cos(math.radians(th))
        widths[th] = w
        rows_bw.append((f"{th:.0f}", f"{w:.4f}", f"{pred:.4f}", f"{w/pred:.4f}"))
        print(f"  {th:>12.0f}{w:>16.4f}{pred:>24.4f}{w/pred:>8.4f}")
    print(f"  → **ビーム幅は 1/cosθ で広がる**(比は 1.0 前後、最大の外れ "
          f"{max(abs(float(r[3])-1.0) for r in rows_bw)*100:.1f} %)。")
    print("     電子的に振った配列は、開口が cosθ に縮んで見えるから。")
    # フットプリントの 3 通り
    prof = scene["prof"]
    print(f"  {'θ₀ [度]':>8}{'cos² 式':>12}{'cos³ 式':>12}{'光線から実測':>14}"
          f"{'cos² の外し':>14}")
    rows, foot_meas, foot2, foot3 = [], [], [], []
    for th in (0.0, 30.0, 45.0, 60.0, 65.0, 70.0):
        bw = bw0 / math.cos(math.radians(th))       # 実測した広がりを使う
        f2 = DEPTH_REF * math.radians(bw0) / math.cos(math.radians(th)) ** 2
        f3 = DEPTH_REF * math.radians(bw0) / math.cos(math.radians(th)) ** 3
        # 実測: ビームの縁 2 本を実際に撃って、海底での水平距離の差を取る
        edges = np.array([max(0.0, th - 0.5 * bw), min(88.0, th + 0.5 * bw)])
        xe, _, ok = trace_to_depth(prof, edges, DEPTH_REF)
        assert bool(np.all(ok))
        fm = float(abs(xe[1] - xe[0]))
        foot_meas.append(fm)
        foot2.append(f2)
        foot3.append(f3)
        rows.append((f"{th:.0f}", f"{f2:.3f}", f"{f3:.3f}", f"{fm:.3f}",
                     f"{100*(f2-fm)/fm:+.1f} %"))
        print(f"  {th:>8.0f}{f2:>12.3f}{f3:>12.3f}{fm:>14.3f}"
              f"{100*(f2-fm)/fm:>13.1f}%")
    print(f"  → ★70 度で cos² 式 {foot2[-1]:.2f} m、cos³ 式 {foot3[-1]:.2f} m、"
          f"実測 {foot_meas[-1]:.2f} m。")
    print(f"     **cos² 式は実測の {100*foot2[-1]/foot_meas[-1]:.0f} %** —— "
          f"ビーム幅の広がりを勘定に入れていないから。")
    print(f"     残る差(cos³ 式と実測で {100*(foot3[-1]-foot_meas[-1])/foot_meas[-1]:+.1f} %)"
          f"は光線が曲がるぶん。")
    figs.save_table("footprint", ["θ₀ [度]", "cos² 式 [m]", "cos³ 式 [m]",
                                  "光線から実測 [m]", "cos² の外し"], rows,
                    title="海底フットプリント —— 教科書の cos² 式は 3 分の 1",
                    caption=f"深さ {DEPTH_REF:.0f} m、ビーム幅 {bw0:.3f} 度(実測)。"
                            "電子的に振ると幅も 1/cosθ で広がる。")
    figs.save_table("beamwidth", ["ステア [度]", "実測 -3dB [度]",
                                  "予測 [度]", "比"], rows_bw,
                    title="ビーム幅は 1/cosθ で広がる(op で実測)",
                    caption="beamform_delay_sum の角度スペクトルの -3 dB 幅。")
    if figs.enabled():
        ths = np.arange(0.0, 71.0, 1.0)
        cs = np.cos(np.radians(ths))
        figs.save_plot(
            "footprint",
            [("cos² 式(教科書)", ths, DEPTH_REF * math.radians(bw0) / cs ** 2),
             ("cos³ 式(幅の広がり込み)", ths, DEPTH_REF * math.radians(bw0) / cs ** 3),
             ("光線から実測", np.array([0.0, 30.0, 45.0, 60.0, 65.0, 70.0]),
              np.array(foot_meas))],
            xlabel="ビーム角 θ₀ [度]", ylabel="海底フットプリント [m]",
            title="外側ビームは「大きく間違える」前に「大きくぼやける」",
            caption="幅の広がりを入れないと 70 度で 3 分の 1 に見積もる。")
        grid = ANGLE_GRID
        figs.save_plot(
            "beam_pattern",
            [("ステア 0 度", grid, beam_pattern(0.0, lam, d)),
             ("ステア 45 度", grid, beam_pattern(45.0, lam, d)),
             ("ステア 70 度", grid, beam_pattern(70.0, lam, d))],
            xlabel="到来角 [度]", ylabel="正規化パワー",
            xlim=(-90.0, 90.0),
            title="配列の角度スペクトル(beamform_delay_sum)",
            caption=f"素子 {N_ELEM} 本・λ/2 間隔。振るほど主ローブが太る。")
    return {"widths": widths, "foot_meas": foot_meas, "foot2": foot2,
            "foot3": foot3, "rows_bw": rows_bw}


# --------------------------------------------------------------------------- #
# 9. DTM 化 —— 測線を 2 本引いて、重なりの段差を測る                             #
# --------------------------------------------------------------------------- #
def section_dtm(scene):
    print("\n=== 9. DTM にして見る —— 隣接測線の重なりに段差が立つ ===")
    prof = scene["prof"]
    ca = scene["ca"]
    beams = np.arange(-65.0, 65.001, 1.0)
    x_true, t1, ok = trace_to_depth(prof, beams, DEPTH_REF)
    assert bool(np.all(ok))
    z_meas = ca * t1 * np.cos(np.radians(beams))
    y_meas = ca * t1 * np.sin(np.radians(beams))
    half_swath = float(np.max(np.abs(y_meas)))
    print(f"  swath 半幅 {half_swath:.2f} m(±65 度・深さ {DEPTH_REF:.0f} m)")
    print(f"  ★航跡直交位置も動く: 65 度のビームは真の {float(x_true[-1]):.3f} m を "
          f"{float(y_meas[-1]):.3f} m と記録({float(y_meas[-1]-x_true[-1]):+.3f} m)。")
    # 測線 2 本。間隔は swath の半分(重複 50 %)。
    spacing = half_swath
    along = np.arange(0.0, 60.001, 2.0)             # 2 m ごとに ping
    pts, vals, line_id = [], [], []
    for line, y0 in enumerate((0.0, spacing)):
        for yy in along:
            pts.append(np.column_stack([y_meas + y0, np.full(beams.size, yy)]))
            vals.append(z_meas)
            line_id.append(np.full(beams.size, line))
    pts = np.vstack(pts)
    vals = np.concatenate(vals)
    line_id = np.concatenate(line_id)
    print(f"  測線 2 本 × ping {along.size} 発 × ビーム {beams.size} 本 = "
          f"{pts.shape[0]} 測点、測線間隔 {spacing:.1f} m")
    # 重なりの食い違い: 同じ航跡直交位置を、測線 1 の外側と測線 2 の内側が測る。
    # ★重なりの**真ん中**を見てはいけない —— そこは両測線とも同じ振れ角なので、
    #   誤差が同じだけ乗って差がゼロになる。**帯全体で最大**を取る。
    ys = np.linspace(spacing - half_swath, half_swath, 401)
    d1 = np.interp(ys, y_meas, z_meas)                       # 測線 1(外側寄り)
    d2 = np.interp(ys - spacing, y_meas, z_meas)             # 測線 2(内側寄り)
    diff = np.abs(d1 - d2)
    k = int(np.argmax(diff))
    mid = 0.5 * (ys[0] + ys[-1])
    a, b = float(d1[k]), float(d2[k])
    print(f"  重なりの帯 x = {ys[0]:.1f} 〜 {ys[-1]:.1f} m。")
    print(f"  ★真ん中(x = {mid:.1f} m)では差 {abs(float(d1[200]-d2[200])):.4f} m —— "
          f"両測線とも同じ振れ角なので**誤差が同じだけ乗って消える**。")
    print(f"  帯の端 x = {ys[k]:.1f} m では、測線 1 が {a:.3f} m(振れ角の外側)、"
          f"測線 2 が {b:.3f} m(内側)→ **食い違い {abs(a-b):.3f} m**")
    print(f"     (TVU {tvu(DEPTH_REF):.3f} m の {abs(a-b)/tvu(DEPTH_REF):.1f} 倍)")
    print("  → ★これが**実データでもできる唯一の検査**。真の海底は誰も知らないが、"
          "\n     同じ海底を 2 度測った差なら、真値なしで出る。")
    # グリッド化して dem_slope で見かけの勾配を測る
    cell = 1.0
    gx = np.arange(-half_swath, spacing + half_swath + 0.001, cell)
    gy = np.arange(0.0, 60.001, cell)
    qx, qy = np.meshgrid(gx, gy)
    got = fs.interp_scattered(pts, vals, np.column_stack([qx.ravel(), qy.ravel()]),
                              method="linear", fill_value=np.nan)
    dtm = np.asarray(got["value"], np.float64).reshape(qx.shape)
    outside = float(got["outside_fraction"])
    filled = np.nan_to_num(dtm, nan=DEPTH_REF)
    slope = np.asarray(fs.ledger.dem_slope(filled, cell), np.float64)
    inner = slope[2:-2, 2:-2]
    print(f"  グリッド {dtm.shape[0]}x{dtm.shape[1]}(セル {cell:.1f} m)、"
          f"凸包の外 {100*outside:.1f} %")
    print(f"  見かけの勾配(dem_slope): 平均 {float(inner.mean()):.3f} 度 / "
          f"最大 **{float(inner.max()):.3f} 度**(真の海底は 0 度)")
    flat_slope = float(np.asarray(fs.ledger.dem_slope(
        np.full_like(filled, DEPTH_REF), cell))[2:-2, 2:-2].max())
    print(f"  対照群(真の平らな海底を同じ手順で)最大 {flat_slope:.6f} 度")
    print("  → 平らな海底が、swath の端で谷の縁のように見える。")
    if figs.enabled():
        figs.save_grid("dtm",
                       [np.full_like(dtm, DEPTH_REF), filled,
                        filled - DEPTH_REF, slope],
                       ["真の海底(平ら、%.0f m)" % DEPTH_REF,
                        "測った DTM [m]", "差 [m](0 が中間色)", "見かけの勾配 [度]"],
                       ncols=2, signed=[False, False, True, False],
                       title="平らな海底の DTM —— 測線の継ぎ目に段差が立つ",
                       caption=f"測線 2 本、間隔 {spacing:.0f} m。差は "
                               f"{float(np.nanmin(filled-DEPTH_REF)):+.2f} 〜 "
                               f"{float(np.nanmax(filled-DEPTH_REF)):+.2f} m、"
                               f"見かけの勾配は最大 {float(inner.max()):.1f} 度。")
        figs.save_plot(
            "across_track",
            [("測った深さ", y_meas, z_meas),
             ("真の海底", y_meas, np.full_like(y_meas, DEPTH_REF))],
            xlabel="航跡直交距離 [m]", ylabel="深さ [m](下が深い)",
            title="1 発の ping の断面 —— 端が持ち上がる",
            caption=f"直下は較正済みで一致。端 65 度で "
                    f"{float(z_meas[-1]-DEPTH_REF):+.2f} m 浅く出る。")
    return {"half_swath": half_swath, "spacing": spacing, "mismatch": abs(a - b),
            "slope_max": float(inner.max()), "slope_flat": flat_slope,
            "outside": outside, "n_points": int(pts.shape[0]),
            "y_shift": float(y_meas[-1] - x_true[-1]), "lines": int(line_id.max()) + 1}


# --------------------------------------------------------------------------- #
# 10. 構造のあるプロファイル —— 一定勾配の当てはめでは直らない                    #
# --------------------------------------------------------------------------- #
def section_thermocline(scene):
    print("\n=== 10. サーモクライン —— 一定勾配を当てはめても直らない ===")
    true_prof = profile_thermocline()
    zs = np.linspace(0.0, DEPTH_REF, 6)
    print("  真のプロファイル(混合層 8 m + サーモクライン + 深層):")
    print("   " + "  ".join(f"{z:.0f} m:{float(sound_speed(true_prof, z)):.1f}"
                            for z in zs))
    _, t1, ok = trace_to_depth(true_prof, BEAM_DEG, DEPTH_REF)
    assert bool(np.all(ok))
    ca_true = DEPTH_REF / float(t1[int(np.argmin(np.abs(BEAM_DEG)))])
    print(f"  直下較正の平均音速 {ca_true:.3f} m/s")
    z_const = ca_true * t1 * np.cos(np.radians(BEAM_DEG))
    # 一定勾配の当てはめ: 表層と海底の音速を結ぶ直線(現場の「2 点キャスト」)
    c_top = float(sound_speed(true_prof, 0.0))
    c_bot = float(sound_speed(true_prof, DEPTH_REF))
    fit = (np.array([0.0, 400.0]),
           np.array([c_top, c_top + (c_bot - c_top) / DEPTH_REF * 400.0]))
    _, z_fit, ok2 = trace_for_time(fit, BEAM_DEG, t1)
    assert bool(np.all(ok2))
    print(f"  {'θ₀ [度]':>8}{'等音速で処理':>16}{'一定勾配で処理':>18}{'改善':>10}")
    rows = []
    for th in (0.0, 30.0, 45.0, 60.0, 65.0, 70.0):
        i = int(np.argmin(np.abs(BEAM_DEG - th)))
        a, b = z_const[i] - DEPTH_REF, z_fit[i] - DEPTH_REF
        rows.append((f"{th:.0f}", f"{a:+.4f}", f"{b:+.4f}",
                     f"{100*(1-abs(b)/max(abs(a), 1e-12)):.0f} %"))
        print(f"  {th:>8.0f}{a:>+16.4f}{b:>+18.4f}"
              f"{100*(1-abs(b)/max(abs(a),1e-12)):>9.0f}%")
    e_const = float(np.max(np.abs(z_const - DEPTH_REF)))
    e_fit = float(np.max(np.abs(z_fit - DEPTH_REF)))
    print(f"  → 等音速だと最大 {e_const:.3f} m、2 点の一定勾配だと "
          f"{e_fit:.3f} m。**減るが消えない**"
          f"({100*(1-e_fit/e_const):.0f} % しか取れない)。")
    print("     当てはめた形(直線)と真の形(段)が違うので、"
          "自由度を 1 つ増やしても偏りは残る。")
    print("  → ★対照群として、**真のプロファイルで処理すれば** 誤差は")
    _, z_ok, _ = trace_for_time(true_prof, BEAM_DEG, t1)
    print(f"     最大 {float(np.max(np.abs(z_ok - DEPTH_REF))):.2e} m "
          f"—— 処理の実装ではなく、**プロファイルの取り違え**が原因だと分かる。")
    figs.save_table("thermocline", ["θ₀ [度]", "等音速で処理 [m]",
                                    "一定勾配で処理 [m]", "改善"], rows,
                    title="サーモクラインは一定勾配で書けない",
                    caption="2 点キャスト(表層と海底だけ)の一定勾配当てはめ。"
                            "誤差は減るが消えない。")
    if figs.enabled():
        zz = np.linspace(0.0, 60.0, 200)
        figs.save_plot(
            "svp",
            [("真(混合層 + サーモクライン)", sound_speed(true_prof, zz), zz),
             ("2 点の一定勾配当てはめ", sound_speed(fit, zz), zz),
             ("等音速(直下較正)", np.full_like(zz, ca_true), zz)],
            xlabel="音速 [m/s]", ylabel="深さ [m](下向き)",
            title="音速プロファイル —— 平均が合っていても形が違う",
            caption="3 本とも直下の走時は同じになるが、外側ビームの光線は違う道を通る。")
    return {"e_const": e_const, "e_fit": e_fit, "ca": ca_true,
            "e_true": float(np.max(np.abs(z_ok - DEPTH_REF)))}


# --------------------------------------------------------------------------- #
# 11. 道具の穴 —— 4 層すべて引いてから「無い」と言う                              #
# --------------------------------------------------------------------------- #
def section_op_holes():
    print("\n=== 11. 道具の穴 —— fs / fs.op / fs.ledger / op_find の 4 層を引く ===")
    wanted = [
        ("sonar", "音響測深そのもの"),
        ("swath", "swath(扇状の帯)の処理"),
        ("bathym", "測深・海底地形"),
        ("sound_speed", "音速プロファイル"),
        ("raytrace_layers", "層に切ったレイトレース"),
        ("tvu", "測量の不確かさ規格(IHO S-44)"),
        ("footprint", "ビームの海底フットプリント"),
        ("crossline", "測線交差点の食い違い"),
    ]
    rows, holes = [], []
    for name, note in wanted:
        tiers = (hasattr(fs, name), hasattr(fs.op, name), hasattr(fs.ledger, name))
        n_find = len(fs.op_find(name))
        rows.append((name, "○" if tiers[0] else "-", "○" if tiers[1] else "-",
                     "○" if tiers[2] else "-", str(n_find), note))
        print(f"  {name:<16} fs:{'○' if tiers[0] else '-'} "
              f"fs.op:{'○' if tiers[1] else '-'} "
              f"fs.ledger:{'○' if tiers[2] else '-'} "
              f"op_find:{n_find:>2} 件   {note}")
        if not any(tiers) and n_find == 0:
            holes.append(name)
    used = ["beamform_delay_sum", "beamform_doa", "find_peaks", "peak_subbin",
            "snell_angle", "interp_scattered", "dem_slope"]
    print("  使えた op: " + ", ".join(used))
    for name in used:
        assert hasattr(fs, name) or hasattr(fs.ledger, name), name
    print("  ★使おうとして**使えなかった**もの:")
    print("    * `beamform_doa` の `range_m` / `velocity_ms` —— FMCW レーダの")
    print("      レンジ-ドップラー面が前提。パルス測深機には無いので None のまま。")
    print("      角度スペクトルの部分だけが音響に読み替えられる(§2 の as_beat_cube)。")
    print("    * `beamform_*` は立方体の 2 軸目・3 軸目に最低 2 を要求するので、")
    print("      素子スナップショット 1 枚を渡すのに `(N,2,2)` へ**水増し**が要る。")
    print("      `beamform_snapshot(x, wavelength, spacing)` があれば素直に書ける。")
    print("    * `snell_angle` は屈折率で受けるので、音響では `eta = 1/c` と")
    print("      **逆数を渡す**必要がある(n ∝ 1/c)。合ってはいるが、読む人は必ず躓く。")
    print("      またスカラー専用なので、141 本のビームを一括で曲げられない。")
    print("    * `dem_slope` は NaN を通すと周囲まで NaN になるので、凸包の外を")
    print("      埋めてから渡した(§9)。「未測定」と「平ら」が区別できない。")
    print("  ★次に埋めるべき op(この PoC を書いていて欲しかった順):")
    print("    1. `svp_ray_trace(profile, angles, depth)` —— 一定勾配層の閉形式。")
    print("       円弧の弦と走時を桁落ちなしで積む(この PoC の trace_to_depth)。")
    print("    2. `svp_harmonic_mean(profile, depth)` —— 直下較正の平均音速。")
    print("    3. `iho_s44_tvu(depth, order)` / `iho_s44_thu` —— 規格の閾値。")
    print("       閾値を各自が書き写すと、必ずどこかで係数が古くなる。")
    print("    4. `beamform_snapshot(snapshot, wavelength, spacing, angles)` ——")
    print("       レンジ-ドップラーを経由しない、素子スナップショット直入力の口。")
    print("    5. `snell_angle` の配列版(+ 音速で受ける薄いラッパ)。")
    print("    6. `crossline_discrepancy(soundings_a, soundings_b)` —— 真値なしで")
    print("       できる唯一の検査(§9)。測量では標準の受入検査。")
    figs.save_table("op_holes", ["語幹", "fs", "fs.op", "fs.ledger", "op_find",
                                 "何が欲しかったか"], rows,
                    title="4 層すべて引いた結果 —— 音響測深の op は 1 つも無い",
                    caption="○ = 在る。`beamform_*` は電波レーダの語彙のまま流用した。")
    return {"holes": holes, "rows": rows, "used": used}


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("多ビーム測深で海底が笑う —— 音速を取り違えると、壊れるのは外側ビームだけ")
    print(f"深さ {DEPTH_REF:.0f} m の平らな海底 / 水柱の音速差 {DELTA_C_REF:+.0f} m/s / "
          f"ビーム ±70 度 {BEAM_DEG.size} 本 / IHO S-44 {ORDER}")
    print("=" * 78)

    scene = section_scene()
    floor = section_floor(scene)
    null = section_null(scene)
    cliff = section_cliff(scene, floor)
    ctrl = section_controls(scene, floor)
    sweep = section_sweep()
    frown = section_frown()
    foot = section_footprint(scene, floor)
    dtm = section_dtm(scene)
    thermo = section_thermocline(scene)
    holes = section_op_holes()

    print("\n" + "=" * 78)
    print("まとめ —— 何がどれだけ効いたか")
    print("=" * 78)
    rows = [
        ("ゼロ点: 表面音速のまま(直下)",
         f"{null['表面音速 c₀']['nadir']:+.3f} m"),
        ("ゼロ点: 表面音速のまま(70 度)",
         f"{null['表面音速 c₀']['edge']:+.3f} m"),
        ("直下較正だけした(直下)", f"{null['直下較正(調和平均)']['nadir']:+.3f} m"),
        ("直下較正だけした(70 度)", f"{null['直下較正(調和平均)']['edge']:+.3f} m"),
        ("角度推定の床(65 度)", f"{ctrl['角度推定だけ入れる']:+.6f} m"),
        ("エコー検出の床(65 度)", f"{ctrl['エコー検出だけ入れる']:+.6f} m"),
        (f"IHO {ORDER} を割る角度(実測)", f"{cliff['cliff']:.2f} 度"),
        ("同(厳密式の予測)", f"{cliff['pred_exact']:.2f} 度"),
        ("同(ラフな展開式の予測)", f"{cliff['pred_tan2']:.2f} 度"),
        ("隣接測線の重なりの食い違い", f"{dtm['mismatch']:.3f} m"),
        ("平らな海底の見かけの勾配(最大)", f"{dtm['slope_max']:.2f} 度"),
        ("70 度のフットプリント(実測)", f"{foot['foot_meas'][-1]:.2f} m"),
    ]
    for name, val in rows:
        print(f"  {name:<38}{val:>14}")
    figs.save_table("summary", ["条件", "値"], rows,
                    title="多ビーム測深 —— 何がどれだけ効くか",
                    caption="直下較正は誤差を消さず、検査されない外側へ移す。")

    # --- 所見を固定する(穴が塞がったら鳴る)--------------------------------- #
    # 1. 層に切ったレイトレースは閉形式と一致する(円弧が厳密だから)
    assert scene["layer_worst"] < 1e-12, scene["layer_worst"]
    # 2. 測定系の床は屈折より 3 桁以上小さい
    assert floor["dz_ang"] < 1e-2, floor["dz_ang"]
    assert floor["err_echo"] < 1e-2, floor["err_echo"]
    # 3. ゼロ点は直下からもう TVU の半分以上を食う
    assert abs(null["表面音速 c₀"]["nadir"]) > 0.5 * cliff["lim"]
    # 4. 直下較正は直下を厳密に 0 にし、外側には残す(誤差の「移動」)
    assert abs(null["直下較正(調和平均)"]["nadir"]) < 1e-9
    assert abs(null["直下較正(調和平均)"]["edge"]) > 3.0
    # 5. 崖: 厳密式は当たる / 展開式は外す(この 2 つが逆転したら鳴る)
    assert abs(cliff["cliff"] - cliff["pred_exact"]) < 0.05, cliff
    assert cliff["pred_exact"] - cliff["pred_tan2"] > 0.5, cliff
    # 展開式は外側で過大(45 度で 3 % 以内、70 度で 15 % 超)
    i45 = int(np.argmin(np.abs(cliff["ths"] - 45.0)))
    assert abs(cliff["tan2"][i45] / cliff["exact"][i45] - 1.0) < 0.05
    assert cliff["tan2"][-1] / cliff["exact"][-1] > 1.15, cliff["tan2"][-1]
    # 全経路の実測は閉形式に床の分だけしか離れない
    assert cliff["path_gap"] < 2e-2, cliff["path_gap"]
    # 6. 対照群: 勾配ゼロは厳密に 0、屈折だけが m の単位
    assert abs(ctrl["勾配ゼロ + 真の平均音速(何も無い)"]) < 1e-12
    assert abs(ctrl["屈折だけ入れる(直下較正)"]) > 1000.0 * max(
        abs(ctrl["角度推定だけ入れる"]), abs(ctrl["エコー検出だけ入れる"]), 1e-9)
    # 7. 掃引: 200 ケース、崖は深いほど浅い角度へ寄り漸近値に近づく
    assert sweep["total"] == 200, sweep["total"]
    assert sweep["shallow"] > sweep["deep"] > sweep["asym"], sweep
    assert sweep["deep"] - sweep["asym"] < 0.5, (sweep["deep"], sweep["asym"])
    assert sweep["fail"] > 100, sweep["fail"]
    # 8. 上向き屈折: 予測した反転角は「届いた最後」と「届かない最初」の間
    assert frown["last"] < frown["pred"] < frown["first_bad"], frown
    assert frown["dz65"] > 0.0, frown["dz65"]      # frown は深く出る
    # 9. フットプリント: ビーム幅は 1/cosθ で広がり、cos² 式は足りない
    for th in (30.0, 45.0, 60.0, 70.0):
        pred = math.degrees(0.886 * floor["lam"] / (N_ELEM * floor["d"])) \
            / math.cos(math.radians(th))
        assert abs(foot["widths"][th] / pred - 1.0) < 0.10, (th, foot["widths"][th])
    assert foot["foot2"][-1] < 0.5 * foot["foot_meas"][-1], foot
    assert abs(foot["foot3"][-1] / foot["foot_meas"][-1] - 1.0) < 0.10, foot
    # 10. DTM: 重なりの段差が TVU を超え、平らな海底に見かけの勾配が立つ
    assert dtm["mismatch"] > cliff["lim"], dtm["mismatch"]
    assert dtm["slope_max"] > 5.0, dtm["slope_max"]
    assert dtm["slope_flat"] < 1e-6, dtm["slope_flat"]
    assert dtm["outside"] == 0.0, dtm["outside"]
    # 11. サーモクライン: 一定勾配の当てはめは減らすが消さない
    assert thermo["e_true"] < 1e-6, thermo["e_true"]
    assert 0.05 * thermo["e_const"] < thermo["e_fit"] < 0.9 * thermo["e_const"], thermo
    # 12. 道具の穴: 音響測深そのものの op は 4 層のどこにも無い
    for name in ("sonar", "swath", "bathym", "sound_speed", "tvu"):
        assert name in holes["holes"], (name, holes["holes"])

    print(f"\n所要 {time.perf_counter() - t0:.1f} s")
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
