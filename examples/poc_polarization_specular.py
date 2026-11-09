# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""偏光で鏡面反射を剥がす —— フレネルの式で真値を作り、分離結果を突き合わせる。

EXTEND: 実際の偏光カメラ(市販の偏光イメージセンサ = 画素上に 0/45/90/135 度の
ワイヤグリッドを敷いた division-of-focal-plane センサ)の生データに差し替えるなら、
本 PoC の ``render_sweep`` だけを実データ読み込みに置き換える。留意点は 4 つ。
(1) **デモザイクの前に生 Bayer 相当の 2x2 偏光モザイクを分離する** —— 4 枚は
互いに半画素ずれた別々の視点なので、補間せずに 1/2 解像度で扱うのが最も正直。
補間すると縁で偏光度が跳ね、それが「鏡面」として分離結果に漏れる。
(2) **リニアな輻度に戻す** —— 本族の op は全部リニア RGB / リニア輻度が前提で、
sRGB ガンマのまま渡しても例外は出ず、分離が静かに劣化するだけ。
(3) **飽和を最優先で潰す** —— 8-(c) 節のとおり、白飛びは例外も出さず拡散を
過大評価する側へ倒し、しかも画素率に対して超線形に悪化する。露光を切り詰めるか
HDR 合成する方が、偏光子の角度較正に手をかけるより効く。角度較正は同じ節の
実測では **一番効かない**(素子ばらつき 1 度で誤差 1.1e-4)。ただし全画素共通の
オフセットは分離を一切壊さない代わりに **方位(AoLP)を丸ごと δ ずらす**ので、
形状復元に方位を使うなら絶対角の較正が要る。壊れる先が違う。
(4) **暗電流・黒レベルを引く** —— オフセットが残ると ``I_min`` が持ち上がり、
拡散成分が一律に過大評価される(これは雑音と違って平均しても消えない)。

この PoC が示すこと:

1. **真値は自分で作る** —— 拡散(無偏光)と鏡面(部分偏光)を s/p 成分に分けて
   自分で合成し、フレネルの式から偏光度を出す。分離結果はその真値と突き合わせる。
2. **ゼロ点を置く** —— 「分離しない」「フレームの最小値を拡散とみなす」を並べ、
   偏光を使う手が何倍勝つのかを数字で出す。**20 度では 1.2 倍しか勝たない。**
3. **ブリュースター角が最良、は本当か** —— 20/40/56.31/70 度で測ると、拡散成分の
   誤差は閉形式 ``R_p * E`` に厳密一致し、ブリュースター角で 0 になる。
4. **壊れる条件を数字で** —— 雑音・偏光子角度の較正誤差・白飛びの 3 つ。

10. **実物に見える場面で** —— フィルムで包んだ箱のラベルと鋼のナットを、高さ場の光線追跡・
   フレネルの s/p 反射率(誘電体と金属は glassmirror の別の式)・レンズのぼけ・消光比・
   ショット雑音・12 bit・飽和で撮った生モザイク 1 枚から分離する。フィルムの映り込みは 9 割
   消えて印字が読めるようになり、残りは閉形式 R_p * E と 1 割以内で合う。**ゼロ点は偏光フィルタ
   1 枚(最適角)**: この場面(小さなソフトボックス 1 灯)では固定のフィルタの方が良い。固定のフィルタは 2 通り
   作る —— 偏光カメラと同じモザイクから組んだもの(角度を選べることだけを比べる)と、全画素で撮る別のカメラ
   (同じセンサ・同じ露光、角度は雑音の無い像で選んだ最良、2x2 を足して偏光カメラと同じ画素数)。しわの深さ
   だけ・照明の広さだけを振ると、**どちらも比(偏光カメラ / 固定のフィルタ)を偏光カメラ側へ押し上げる**。
   全画素のフィルタと比べると、狭い照明ではしわを 4 倍にしても比は 1 に届かず(固定のフィルタで足りる)、
   照明だけを大きな面照明まで広げると比は 1 前後(1024 画素・種 6 本で 1.03〜1.07、512 画素・種 13 本で
   0.94〜1.05 —— 読める水準での差は 1 割未満)。両方が大きいと偏光カメラがはっきり勝つ(1.13〜1.43)が、
   CNR は 2 前後でどちらも印字は読めない。言えるのは「しわも照明の広さも差を広げる。1024 画素では比を 1 より
   上へ出したのは照明を広げたときだけ」まで —— **512 画素では互角で、種によってはしわとの順序も入れ替わる**
   (種 137: 照明だけ 0.944 < しわだけ 0.955)。勝敗を決める量(映り込みの入射面の向きのばらつき)は測っていない。
   モザイクから組んだフィルタとの勝ち負け(前の版の門)は種で入れ替わる(512 画素・種 137 の大きな面照明で
   偏光カメラ 6.60 < フィルタ 6.64)ので門にせず、全画素のフィルタとの比だけを門にした。
   モザイクから組んだフィルタは全画素のものより CNR が 2〜7 % 低く、その分だけ偏光カメラを有利に見せていた
   (前の版の「大きな面照明ならしわ 1 倍でも勝つ」は 1024 画素で 11 % → 全画素のフィルタとは 7 %、512 画素では
   互角)。袋の膨らみ(ピロー包装)でも試したが、固定のフィルタに勝てなかった(使っていない)。鋼は飽和しない短い露光で測り直し、消える割合は描画と同じ
   金属のフレネルの式(3 割弱)と合う —— これは実装の検算(雑音・ぼけ・モザイクを通しても式どおり出るか)
   で、外の真値ではない。図の白いナットは飽和。数は図つき実行(1024 画素)と CI(512 画素)で少し違う。
   場面・真値とも自作の描画で、フレネルの式も描画と照合で同じ glassmirror(探した範囲では、
   再配布できる許諾の偏光カメラの公開データが見つからなかった)。

★ この PoC が出した道具の穴は末尾の「所見」節に 5 件まとめた。要点は
``polarization_separate`` の返す "diffuse" が **``R_p * E`` だけ系統的に大きい**
こと、そしてその補正に必要な入射角の口が op に無いこと。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import match3d                                                   # noqa: E402
import specularity                                               # noqa: E402
from fullseye.evaluation import rmse as evaluation_rmse           # noqa: E402

ETA = 1.5                       # 誘電体(ガラス / 樹脂)の屈折率
THETA_B = math.degrees(math.atan(ETA))          # ブリュースター角 = 56.3099 度
ANGLES = (0.0, 45.0, 90.0, 135.0)               # DoFP センサの 4 方位
H, W = 96, 128
E0 = 3.0                        # 鏡面ローブに入る光源の照度(拡散の数倍が普通)
AZIMUTH = 22.5                  # 入射面の方位。4 方位の格子から最も遠い最悪値
THETAS = (20.0, 40.0, THETA_B, 70.0)


#: ---- 実物に見える検査台の場面(2026-11-08)------------------------------------
#: 旧版は平らな楕円 2 個に光沢の山を置いた絵だった。ここでは検査ラインでいちばん
#: 偏光が効く場面 —— **透明フィルムで包んだ箱のラベル**(フィルムの映り込みで印字が
#: 読めない)と、隣の **鋼の六角ナット**(金属の映り込みは偏光しない)—— を、
#: 高さ場の光線追跡・フレネルの s/p 反射率(誘電体 = glassmirror.fresnel_dielectric、
#: 金属 = glassmirror.fresnel_conductor)・面の向きから決まる偏光の方位・レンズのぼけ・
#: 消光比・ショット雑音・読出し雑音・12 bit の量子化・飽和で撮る。
TILT_DEG = 50.0                 # カメラの光軸の傾き(台の法線から)= 平らな面への入射角
FILM_N = 1.57                   # 包装フィルム(PET)の屈折率
STEEL_NK = (2.90, 3.00)         # 鋼(鉄)の複素屈折率 n + ik、可視の中央付近
FULL_WELL_E = 10000.0           # 飽和電子数
READ_E = 3.0                    # 読出し雑音 [e-]
ADC_BITS = 12


def _smooth_noise(rng, shape, sigma):
    from scipy import ndimage as _nd
    a = _nd.gaussian_filter(rng.standard_normal(shape), sigma, mode="wrap")
    return a / max(float(a.std()), 1e-12)


def _label_albedo(h, w, seed):
    """ラベルの印字(白い紙に黒の文字・バーコード・枠)を PIL で描いた反射率 (h, w)。"""
    from PIL import Image, ImageDraw, ImageFont
    rng = np.random.default_rng(seed)
    scale = 4
    im = Image.new("L", (w * scale, h * scale), 225)
    d = ImageDraw.Draw(im)
    W_, H_ = w * scale, h * scale
    d.rectangle((int(0.04 * W_), int(0.05 * H_), int(0.96 * W_), int(0.95 * H_)), outline=30, width=3 * scale)
    font_path = str(figs._japanese_font_path(bold=True))
    f_big = ImageFont.truetype(font_path, int(0.105 * W_))
    f_mid = ImageFont.truetype(font_path, int(0.064 * W_))
    d.text((int(0.08 * W_), int(0.09 * H_)), "精密部品 FS-2611", font=f_big, fill=15)
    d.text((int(0.08 * W_), int(0.27 * H_)), "LOT 261108-A   数量 50", font=f_mid, fill=20)
    d.text((int(0.08 * W_), int(0.39 * H_)), "保管: 直射日光を避ける", font=f_mid, fill=20)
    # バーコード(幅 1〜4 単位の黒白の帯)。実在の符号系の規則は使わない —— 縞の見え方だけ
    x = int(0.08 * W_)
    y0, y1 = int(0.55 * H_), int(0.86 * H_)
    unit = max(2, int(0.0042 * W_))
    black = True
    while x < int(0.62 * W_):
        wbar = unit * int(rng.integers(1, 5))
        if black:
            d.rectangle((x, y0, x + wbar - 1, y1), fill=12)
        x += wbar
        black = not black
    d.text((int(0.66 * W_), int(0.64 * H_)), "検査済", font=f_mid, fill=25)
    a = np.asarray(im.resize((w, h), Image.Resampling.LANCZOS), dtype=np.float64) / 255.0
    return 0.03 + 0.85 * a


def _hex_nut(xx, yy, cx, cy, r_flat, hole, height):
    """六角ナット(面取りつき)の高さ場と mask。"""
    dx, dy = xx - cx, yy - cy
    ang = np.arctan2(dy, dx)
    rr = np.hypot(dx, dy)
    # 六角形: 対辺距離 r_flat の多角形の「半径」(中心から辺まで)
    sector = np.mod(ang + np.pi / 6.0, np.pi / 3.0) - np.pi / 6.0
    d_hex = rr * np.cos(sector)                    # 辺の法線方向の距離
    body = d_hex < r_flat
    # 面取り: 外接円近くで円錐状に落とす(実物の 30 度面取り)
    cham = np.clip((r_flat * 1.08 - rr) / (0.16 * r_flat), 0.0, 1.0)
    top = height * np.minimum(1.0, 0.55 + 0.45 * cham)
    z = np.where(body, top, 0.0)
    # ねじ穴(内側へ円錐の面取り)
    in_hole = rr < hole
    cone = (rr < hole * 1.25) & ~in_hole
    z = np.where(cone, height - (hole * 1.25 - rr) * 0.9, z)
    z = np.where(in_hole, 0.0, z)
    return np.where(body, z, 0.0), body & ~in_hole


def _env_radiance(dirs, rough, soft=(9.0, 14.0)):
    """検査室の環境の輝度(無偏光): 光軸の鏡像側の大きなソフトボックス + 天井の蛍光灯 + 暗い壁。

    dirs (..., 3) は表面から外へ向かう単位ベクトル。rough は面の粗さ(縁のぼけの幅、ラジアン)。
    """
    x, y, z = dirs[..., 0], dirs[..., 1], dirs[..., 2]
    el = np.arcsin(np.clip(z, -1.0, 1.0))
    az = np.arctan2(x, y)                          # 光源側(+y、カメラの反対)を 0
    t = math.radians(TILT_DEG)
    soft_el, soft_az = math.pi / 2 - t, 0.0        # 平らな面での鏡像方向 = 光源の中心
    w_el, w_az = math.radians(soft[0]), math.radians(soft[1])
    edge = 0.025 + rough

    def box(c_el, c_az, h_el, h_az, e):
        a = 0.5 * (1.0 + np.tanh((h_el - np.abs(el - c_el)) / e))
        b = 0.5 * (1.0 + np.tanh((h_az - np.abs(np.angle(np.exp(1j * (az - c_az))))) / e))
        return a * b

    L = 0.05 + 0.10 * np.clip(z, 0.0, 1.0)         # 壁と天井の照り返し
    L = L + 14.0 * box(soft_el, soft_az, w_el, w_az, edge)
    for c_az in (-0.9, 0.95, 2.6):                 # 天井の蛍光灯の帯
        L = L + 1.6 * box(math.radians(72.0), c_az, math.radians(2.0), math.radians(28.0), 0.015 + rough)
    return L * (z > -0.05)


def _bilinear(img, x, y):
    h, w = img.shape
    x = np.clip(x, 0.0, w - 1.001)
    y = np.clip(y, 0.0, h - 1.001)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx, fy = x - x0, y - y0
    return ((1 - fx) * (1 - fy) * img[y0, x0] + fx * (1 - fy) * img[y0, x0 + 1]
            + (1 - fx) * fy * img[y0 + 1, x0] + fx * fy * img[y0 + 1, x0 + 1])


def render_bench_stokes(size=1024, seed=33, wrinkle=1.0, soft=(9.0, 14.0)):
    """検査台を傾けたカメラで撮った、雑音の無い線形の Stokes (S0, S1, S2) と成分の内訳。

    返り値の各場は (size, size)。``diffuse`` は無偏光の拡散(ラベル・ベルト)、``film`` と
    ``metal`` はフィルムと鋼の鏡面の S0、``theta_deg`` は鏡面の入射角、``rs``/``rp`` は
    画素ごとのフレネル反射率(フィルムだけ)。
    """
    import glassmirror
    from scipy import ndimage as _nd

    rng = np.random.default_rng(seed)
    t = math.radians(TILT_DEG)
    s = size / 1024.0
    N = size
    M = int(math.ceil(size / math.cos(t))) + 2     # 台の上の y の範囲(画面の縦が奥行きに伸びる)
    # 透視の視野は画面の端で台の外まで届くので、台の座標は周りに余白を足して持つ
    ox, oy = int(0.30 * N), int(0.45 * M)
    Mt, Nt = M + 2 * oy, N + 2 * ox
    yy, xx = np.mgrid[0:Mt, 0:Nt].astype(np.float64)
    yy -= oy
    xx -= ox
    # --- 高さ場と材質 -------------------------------------------------------- #
    box_x0, box_x1 = 0.06 * N, 0.62 * N
    box_y0, box_y1 = 0.22 * M, 0.80 * M
    box_h = 26.0 * s
    in_box = (xx > box_x0) & (xx < box_x1) & (yy > box_y0) & (yy < box_y1)
    # フィルムのしわ: 低周波のうねり + 斜めの折れ筋(実物の熱収縮フィルムの見え方)
    wr = wrinkle * (2.4 * s * _smooth_noise(rng, (Mt, Nt), 38 * s) + 0.9 * s * _smooth_noise(rng, (Mt, Nt), 9 * s))
    crease = np.zeros((Mt, Nt))
    for k in range(5):
        a = rng.uniform(-0.6, 0.6)
        c = rng.uniform(box_x0, box_x1)
        dist = (xx - c - a * (yy - 0.5 * M)) / np.hypot(1.0, a)
        crease += 1.6 * s * np.exp(-(dist / (5.0 * s)) ** 2) * rng.choice([-1.0, 1.0])
    # 箱の縁でフィルムが丸く回り込む
    ex = np.minimum(xx - box_x0, box_x1 - xx)
    ey = np.minimum(yy - box_y0, box_y1 - yy)
    e = np.minimum(ex, ey)
    rim = np.clip(e / (14.0 * s), 0.0, 1.0)
    z_box = np.where(in_box, box_h * np.sqrt(np.clip(1 - (1 - rim) ** 2, 0, 1)) + (wr + crease) * rim, 0.0)
    nut_cx, nut_cy, nut_r = 0.80 * N, 0.40 * M, 0.11 * N
    z_nut, nut = _hex_nut(xx, yy, nut_cx, nut_cy, nut_r, 0.45 * nut_r, 44.0 * s)
    # 小さい座金(ワッシャ)
    rr2 = np.hypot(xx - 0.80 * N, yy - 0.70 * M)
    wa = (rr2 < 0.075 * N) & (rr2 > 0.035 * N)
    z_wa = np.where(wa, 6.0 * s * (1.0 - 0.3 * ((rr2 - 0.055 * N) / (0.02 * N)) ** 2), 0.0)
    z_wa = np.clip(z_wa, 0.0, None)
    z = z_box + z_nut + z_wa
    z = _nd.gaussian_filter(z, 0.7 * s)
    mat = np.zeros((Mt, Nt), np.int8)                # 0 ベルト / 1 フィルムの箱 / 2 鋼
    mat[in_box & (z > 0.4 * box_h)] = 1
    mat[(nut | wa) & (z > 1.0)] = 2
    # ラベル(箱の上面に貼った紙)
    lab = np.full((Mt, Nt), 0.62)                    # 段ボールの側面・余白
    ly0, ly1 = int(box_y0 + 0.08 * (box_y1 - box_y0)), int(box_y1 - 0.08 * (box_y1 - box_y0))
    lx0, lx1 = int(box_x0 + 0.06 * (box_x1 - box_x0)), int(box_x1 - 0.06 * (box_x1 - box_x0))
    # 画面の上 = 台の奥(+y)なので、台の座標では上下を返して貼る
    lab[oy + ly0:oy + ly1, ox + lx0:ox + lx1] = _label_albedo(ly1 - ly0, lx1 - lx0, seed)[::-1]
    # ベルト(黒いゴム、細かい布目)
    belt = 0.10 + 0.012 * _smooth_noise(rng, (Mt, Nt), 1.2 * s) + 0.01 * np.sin(2 * np.pi * yy / (7.0 * s))
    # 鋼の研削目(同心円の筋)と粗さ
    rr_n = np.hypot(xx - nut_cx, yy - nut_cy)
    brushed = 1.0 + 0.10 * np.sin(rr_n / (1.3 * s)) * _smooth_noise(rng, (Mt, Nt), 3 * s)
    gy, gx = np.gradient(z)
    nx, ny, nz = -gx, -gy, np.ones_like(z)
    nn = np.sqrt(nx * nx + ny * ny + nz * nz)
    nrm = np.stack([nx / nn, ny / nn, nz / nn])

    # --- 透視のカメラで光線を飛ばす(画角 ±13 度。鏡像方向が画面の中で動くので
    #     ソフトボックスの映り込みが「面の一部だけ」に乗る —— 実際のカメラの見え方) ---- #
    d0 = np.array([0.0, math.sin(t), -math.cos(t)])     # 光軸(奥 = +y へ、下へ)
    ex = np.array([1.0, 0.0, 0.0])
    ey = np.array([0.0, math.cos(t), math.sin(t)])       # 画面の上向き
    f_px = 2.2 * N
    centre = np.array([0.5 * N, 0.5 * M, 0.0])
    cam = centre - f_px * d0                             # 中心で 1 画素 = 台の 1 単位
    rows, cols = np.mgrid[0:N, 0:N].astype(np.float64)
    du = (cols - 0.5 * (N - 1)) / f_px
    dv = -(rows - 0.5 * (N - 1)) / f_px
    D = d0[None, None, :] + du[..., None] * ex + dv[..., None] * ey
    D /= np.linalg.norm(D, axis=-1, keepdims=True)
    zmax = float(z.max()) + 2.0
    tt0 = (zmax - cam[2]) / D[..., 2]
    tt1 = (0.0 - cam[2]) / D[..., 2]
    step = 0.8
    n_steps = int(math.ceil(float((tt1 - tt0).max()) / step)) + 2
    # 速くするための近道(結果は同じ): 光線が台に当たる点の周り(光線が高さ zmax から降りる間に横へ進む距離)に
    # 高さが 0 でない所が無ければ、交点は台の上 —— 行進しない。行進は残りの光線だけ
    reach = int(math.ceil(zmax * math.tan(t + 0.25))) + 2
    z_dil = _nd.maximum_filter(z, size=2 * reach + 1)
    gx_ = cam[0] + tt1 * D[..., 0] + ox
    gy_ = cam[1] + tt1 * D[..., 1] + oy
    flat = _bilinear(z_dil, gx_, gy_) <= 0.0
    hit = np.where(flat, tt1, np.nan)
    act = np.nonzero(~flat)
    Da = D[act]
    t0a, t1a = tt0[act], tt1[act]
    hit_a = np.full(t0a.shape, np.nan)
    prev_t = t0a.copy()
    prev_f = np.ones(t0a.shape)
    for k in range(1, n_steps + 1):
        tk = np.minimum(t0a + k * step, t1a)
        qx = cam[0] + tk * Da[:, 0]
        qy = cam[1] + tk * Da[:, 1]
        qz = cam[2] + tk * Da[:, 2]
        f = qz - _bilinear(z, qx + ox, qy + oy)
        new = np.isnan(hit_a) & (f <= 0.0)
        if new.any():
            a_ = prev_f[new] / np.maximum(prev_f[new] - f[new], 1e-12)
            hit_a[new] = prev_t[new] + a_ * (tk[new] - prev_t[new])
        prev_t, prev_f = tk, f
        if not np.isnan(hit_a).any():
            break
    hit[act] = hit_a
    hit = np.where(np.isnan(hit), tt1, hit)
    px = cam[0] + hit * D[..., 0] + ox
    py = cam[1] + hit * D[..., 1] + oy
    n_img = np.stack([_bilinear(nrm[i], px, py) for i in range(3)], axis=-1)
    n_img /= np.linalg.norm(n_img, axis=-1, keepdims=True)
    m_img = _bilinear(mat.astype(np.float64), px, py)
    is_film = m_img > 0.5
    is_film &= m_img < 1.5
    is_metal = m_img > 1.5
    alb = _bilinear(lab, px, py)
    belt_i = _bilinear(belt, px, py)
    brush_i = _bilinear(brushed, px, py)
    # 接地の影(箱とナットの足元を暗く): 高さ場をぼかした差 = 簡単な遮蔽
    occl = np.clip(1.0 - 0.035 * np.maximum(_nd.gaussian_filter(z, 10 * s) - z, 0.0) / s, 0.35, 1.0)
    occ_i = _bilinear(occl, px, py)

    # --- 陰影 ---------------------------------------------------------------- #
    V = -D
    cos_i = np.clip(np.sum(n_img * V, axis=-1), 1e-4, 1.0)
    R = 2.0 * cos_i[..., None] * n_img - V               # 鏡像方向
    theta = np.degrees(np.arccos(cos_i))
    # s 偏光の向き = 入射面の法線 n × V、画面の座標(列 = 右、行 = 下)へ射影
    sv = np.cross(n_img, V)
    sn = np.linalg.norm(sv, axis=-1, keepdims=True)
    sv = np.where(sn > 1e-9, sv / np.maximum(sn, 1e-12), np.array([1.0, 0.0, 0.0]))
    psi = np.arctan2(-(sv @ ey), sv[..., 0])             # 画面の右から下へ測る角
    # 拡散の照度: ソフトボックスの中心方向 + 環境
    Lc = np.array([0.0, math.sin(t), math.cos(t)])
    E = 0.35 + 1.1 * np.clip(n_img @ Lc, 0.0, None)
    # フィルム: 誘電体、ほぼ鏡面(しわの粗さだけ)
    rs_f = glassmirror.fresnel_dielectric(cos_i, 1.0, FILM_N, "s")
    rp_f = glassmirror.fresnel_dielectric(cos_i, 1.0, FILM_N, "p")
    rs_m = glassmirror.fresnel_conductor(cos_i, STEEL_NK[0], STEEL_NK[1], "s")
    rp_m = glassmirror.fresnel_conductor(cos_i, STEEL_NK[0], STEEL_NK[1], "p")
    L_f = _env_radiance(R, 0.01, soft)
    L_m = _env_radiance(R, 0.05, soft) * brush_i
    # ベルトのゴムは粗い誘電体: 鏡面は弱くぼけて、偏光は少し
    L_b = _env_radiance(R, 0.35, soft)
    rs_b, rp_b = 0.06 * rs_f / np.maximum(rs_f + rp_f, 1e-12), 0.06 * rp_f / np.maximum(rs_f + rp_f, 1e-12)
    trans = (1.0 - 0.5 * (rs_f + rp_f)) ** 2                # 往復のフィルム透過(無偏光とみなす)
    diffuse = np.where(is_film, alb * trans, np.where(is_metal, 0.0, belt_i)) * E * occ_i
    spec_s = np.where(is_film, rs_f * L_f, np.where(is_metal, rs_m * L_m, rs_b * L_b * 0.5)) * 0.5
    spec_p = np.where(is_film, rp_f * L_f, np.where(is_metal, rp_m * L_m, rp_b * L_b * 0.5)) * 0.5
    spec_s = spec_s * occ_i
    spec_p = spec_p * occ_i
    s0 = diffuse + spec_s + spec_p
    pol = spec_s - spec_p
    s1 = pol * np.cos(2.0 * psi)
    s2 = pol * np.sin(2.0 * psi)
    film_spec = np.where(is_film, spec_s + spec_p, 0.0)
    metal_spec = np.where(is_metal, spec_s + spec_p, 0.0)
    return {"stokes": np.stack([s0, s1, s2]), "diffuse": diffuse, "film": film_spec,
            "metal": metal_spec, "spec_p": spec_p, "spec_s": spec_s,
            "theta_deg": theta, "is_film": is_film, "is_metal": is_metal,
            "psi_deg": np.degrees(psi), "rs_film": rs_f, "rp_film": rp_f,
            "albedo": np.where(is_film, alb, 0.0)}


def dofp_inspection_scene(size=1024, seed=33, extinction_ratio=120.0, return_truth=False, exposure_scale=1.0,
                          bench=None):
    """検査台(フィルム包装のラベル + 鋼のナット)を 4 方位の画素偏光子を持つセンサで撮った生のモザイク。

    ``render_bench_stokes`` の線形 Stokes に、露光・レンズのぼけ(ガウス σ 0.7 画素)・偏光子の
    消光比(反対向きの成分が 1/extinction_ratio 漏れる)・ショット雑音(飽和 10000 電子)・読出し雑音
    3 電子・12 bit の量子化・飽和をこの順で掛ける。鋼のナットの映り込みは飽和する(白飛びを残す)。
    ``return_truth=True`` は同じ露光の雑音の無い線形の真値(飽和しない HDR)も返す。
    """
    if size < 64 or size % 2:
        raise ValueError("size must be an even integer of at least 64")
    from scipy import ndimage as _nd

    rng = np.random.default_rng(seed)
    b = bench if bench is not None else render_bench_stokes(size=size, seed=seed)
    film = b["is_film"]
    # 露光: フィルム越しのラベルの拡散(95 % 点)が飽和の 0.40 に来るように絞る
    expo = exposure_scale * 0.40 / max(float(np.percentile(b["diffuse"][film], 95.0)), 1e-9)
    s0, s1, s2 = (expo * a for a in b["stokes"])
    blur = [_nd.gaussian_filter(a, 0.7) for a in (s0, s1, s2)]
    ang = np.radians(np.asarray(ANGLES))
    ideal = np.stack([0.5 * (blur[0] + blur[1] * np.cos(2 * a) + blur[2] * np.sin(2 * a)) for a in ang])
    leak = 1.0 / extinction_ratio
    opposite = ideal[[2, 3, 0, 1]]
    measured = (ideal + leak * opposite) / (1.0 + leak)
    electrons = rng.poisson(np.clip(measured, 0.0, None) * FULL_WELL_E).astype(np.float64)
    electrons += rng.normal(0.0, READ_E, electrons.shape)
    levels = 2 ** ADC_BITS - 1
    measured = np.round(np.clip(electrons / FULL_WELL_E, 0.0, 1.0) * levels) / levels
    raw = np.empty((size, size), dtype=np.float64)
    raw[0::2, 0::2] = measured[0, 0::2, 0::2]
    raw[0::2, 1::2] = measured[1, 0::2, 1::2]
    raw[1::2, 0::2] = measured[2, 1::2, 0::2]
    raw[1::2, 1::2] = measured[3, 1::2, 1::2]
    analyzers = np.stack([raw[0::2, 0::2], raw[0::2, 1::2],
                          raw[1::2, 0::2], raw[1::2, 1::2]])
    st0 = analyzers[0] + analyzers[2]
    st1 = analyzers[0] - analyzers[2]
    st2 = analyzers[1] - analyzers[3]
    dolp = np.hypot(st1, st2) / np.maximum(st0, 1e-9)
    aolp = np.mod(0.5 * np.degrees(np.arctan2(st2, st1)), 180.0)
    glare_removed = np.clip(st0 - np.hypot(st1, st2), 0.0, 2.0)
    result = {"raw_mosaic": raw, "analyzers": analyzers,
              "stokes": np.stack([st0, st1, st2]), "dolp": dolp,
              "aolp_deg": aolp, "glare_removed": glare_removed,
              "scene_masks": {"metal": b["is_metal"], "plastic": film},
              "azimuth_deg": float(np.median(b["psi_deg"][film])),
              "extinction_ratio": extinction_ratio, "exposure": expo}
    if return_truth:
        dolp_true = np.hypot(s1, s2) / np.maximum(s0, 1e-12)
        result.update({"truth_stokes": np.stack([s0, s1, s2]),
                       "truth_dolp": dolp_true, "truth_diffuse": expo * b["diffuse"],
                       "truth_glare": expo * b["film"], "truth_metal_glare": expo * b["metal"],
                       "truth_spec_p": expo * b["spec_p"], "truth_albedo": b["albedo"],
                       "truth_theta_deg": b["theta_deg"], "truth_rp_film": b["rp_film"],
                       "truth_rs_film": b["rs_film"]})
    return result


def polarization_resemblance_gate(size=256, seed=34):
    """Check the Brewster region, low-signal angle noise and no-analyser probe."""
    rng = np.random.default_rng(seed)
    rs, rp = fresnel_sp(THETA_B)
    highlight_dolp = (rs - rp) / (rs + rp)
    az = 28.0
    s0, dolp, sigma = 0.16, 0.08, 0.001
    n = size * size
    angles = np.radians(np.asarray(ANGLES))[:, None]
    clean = 0.5 * s0 * (1.0 + dolp * np.cos(2.0 * (angles - np.deg2rad(az))))
    noisy = clean + rng.normal(0.0, sigma, (4, n))
    s1 = noisy[0] - noisy[2]
    s2 = noisy[1] - noisy[3]
    measured = np.std(0.5 * np.arctan2(s2, s1), ddof=1)
    predicted = sigma / (np.sqrt(2.0) * s0 * dolp)
    flat = np.full((4, n), 0.5 * s0) + rng.normal(0.0, sigma * 0.01, (4, n))
    no_pol = np.hypot(flat[0] - flat[2], flat[1] - flat[3]) \
        / np.maximum(flat[0] + flat[2], 1e-12)
    return {"highlight_dolp": float(highlight_dolp),
            "highlight_aolp_error_deg": 0.0,
            "aolp_noise_ratio": float(measured / predicted),
            "no_polarizer_max_dolp": float(np.quantile(no_pol, 0.999))}


def fig_dofp_camera():
    if not figs.enabled():
        return None
    r = dofp_inspection_scene(size=1024, seed=33)
    figs.save("raw_polarizer_mosaic", r["raw_mosaic"], gray=True,
              caption="検査台(フィルムで包んだ箱のラベルと鋼のナット)を 4 方位の画素偏光子センサで撮った生のモザイク(等倍)。"
                      "2x2 画素ごとに 0/45/90/135 度。鋼の映り込みの白飛びと偏光子の消光比 1/120 の漏れを残してある。")
    figs.save_grid("analyzer_samples", list(r["analyzers"]),
                   ["0 deg", "45 deg", "90 deg", "135 deg"], ncols=4, gray=True,
                   caption="モザイクから方位ごとに 1/4 の画素を抜き出した 4 枚(1/2 解像度、補間しない)。"
                           "フィルムの映り込みは 0 度と 90 度で明るさが大きく変わり、鋼の映り込みはあまり変わらない。")
    s0, s1, s2 = r["stokes"]
    hue = np.mod(r["aolp_deg"], 180.0) / 180.0
    h6 = hue * 6.0
    c = np.ones_like(hue)
    x = 1.0 - np.abs(np.mod(h6, 2.0) - 1.0)
    z = np.zeros_like(hue)
    sectors = np.floor(h6).astype(int) % 6
    rgb = np.zeros(hue.shape + (3,), float)
    choices = ((c, x, z), (x, c, z), (z, c, x), (z, x, c), (x, z, c), (c, z, x))
    for k, channels in enumerate(choices):
        mask = sectors == k
        for j in range(3):
            rgb[..., j][mask] = channels[j][mask]
    rgb *= np.clip(r["dolp"], 0.12, 1.0)[..., None]
    legend = np.tile(np.linspace(0, 1, rgb.shape[1])[None, :], (24, 1))
    lh = legend * 6.0
    ls = np.floor(lh).astype(int) % 6
    lx = 1.0 - np.abs(np.mod(lh, 2.0) - 1.0)
    lr = np.zeros(legend.shape + (3,))
    lchoices = ((np.ones_like(legend), lx, np.zeros_like(legend)), (lx, np.ones_like(legend), np.zeros_like(legend)),
                (np.zeros_like(legend), np.ones_like(legend), lx), (np.zeros_like(legend), lx, np.ones_like(legend)),
                (lx, np.zeros_like(legend), np.ones_like(legend)), (np.ones_like(legend), np.zeros_like(legend), lx))
    for k, channels in enumerate(lchoices):
        for j in range(3):
            lr[..., j][ls == k] = channels[j][ls == k]
    rgb[-24:] = lr
    # 偏光度は S0 の小さい画素(影・黒い印字)で 0 割りに近くなり、桁違いの値が表示の範囲を潰す。
    # S0 が中央値の 5 % 未満の画素は 0 にし、0..1 に固定して塗る
    dolp_show = np.where(s0 > 0.05 * float(np.median(s0)), np.clip(r["dolp"], 0.0, 1.0), 0.0)
    figs.save_grid("stokes_and_glare", [s0, s1, s2, dolp_show, rgb, r["glare_removed"]],
                   ["S0", "S1", "S2", "DoLP(0..1)", "AoLP: 0..180 deg", "glare reduced"],
                   vrange=[None, None, None, (0.0, 1.0), None, None],
                   ncols=3, gray=[True, False, False, True, False, True],
                   signed=[False, True, True, False, False, False],
                   caption="Stokes の 3 成分、偏光度、偏光の方位(色相)、偏光成分を引いた像。偏光度の低い所(ベルト・ラベルの紙)は方位が雑音になる。")
    return r


def fig_analyzer_sweep_explained():
    """入口動画: 検光子を回した真値像、Stokes 分離、3 標本の呼吸を同時に示す。"""
    if not figs.enabled():
        return None
    from PIL import Image, ImageDraw
    import annotate as AN

    r = dofp_inspection_scene(size=1024, seed=33, return_truth=True)
    s0, s1, s2 = [np.asarray(a, dtype=np.float64) for a in r["truth_stokes"]]
    glare = np.asarray(r["truth_glare"])
    metal_glare = np.asarray(r["truth_metal_glare"])
    diffuse = np.asarray(r["truth_diffuse"])
    # A = フィルムの映り込みが強い画素(映り込みが最大値の半分以上)のうち、偏光度が最大の点
    #     (黒い印字の上の映り込み = 拡散が少なく、映り込みだけが呼吸する)。
    # B = 鋼の映り込みが飽和しない画素(真値で 0.9 未満)のうち、映り込みが最大の点。
    tdolp = np.asarray(r["truth_dolp"])
    strong = glare > 0.5 * float(glare.max())
    a_yx = np.unravel_index(np.argmax(np.where(strong, tdolp, -1.0)), glare.shape)
    b_yx = np.unravel_index(np.argmax(np.where(s0 < 0.9, metal_glare, -1.0)), metal_glare.shape)
    # C は拡散が中央値付近、両光沢ローブが実質ゼロの候補から、観測 DoLP が
    # 最小の点を機械的に選ぶ。「動かない地」を目で選ばない。
    med = float(np.median(diffuse))
    candidates = (np.abs(diffuse - med) < 0.01 * max(med, 1e-9)) & (glare < 1e-6) & (metal_glare < 1e-6)
    cy, cx = np.nonzero(candidates)
    ci = int(np.argmin(r["dolp"][cy // 2, cx // 2]))
    c_yx = (int(cy[ci]), int(cx[ci]))
    samples = (a_yx, b_yx, c_yx)
    labels = ("A", "B", "C")

    theta_deg = np.arange(72, dtype=np.float64) * 2.5
    theta = np.deg2rad(theta_deg)
    curves = []
    for yy, xx in samples:
        curves.append(0.5 * (s0[yy, xx] + s1[yy, xx] * np.cos(2.0 * theta)
                             + s2[yy, xx] * np.sin(2.0 * theta)))
    ratios = [float(np.max(v) / np.min(v)) for v in curves]
    dolps = [float(r["dolp"][yy // 2, xx // 2]) for yy, xx in samples]
    assert ratios[0] >= 5.0
    assert ratios[2] <= 1.1

    def put_text(im, text, xy, size=22, anchor="lt", fill=(245, 245, 245),
                 plate=None, pad=3):
        m = AN.measure_text(text, font_size=size, min_font_size=size, wrap=False)
        w, h = m["width"], m["height"]
        ax, ay = anchor
        x0 = int(xy[0] - (w if ax == "r" else w // 2 if ax == "c" else 0))
        y0 = int(xy[1] - (h if ay == "b" else h // 2 if ay == "m" else 0))
        if x0 - pad < 0 or y0 - pad < 0 or x0 + w + pad > im.width or y0 + h + pad > im.height:
            raise ValueError("text overflow: %r at %r, rect=(%d,%d,%d,%d), canvas=%r" %
                             (text, xy, x0, y0, w, h, im.size))
        d = ImageDraw.Draw(im)
        if plate is not None:
            d.rectangle((x0 - pad, y0 - pad, x0 + w + pad, y0 + h + pad), fill=plate)
        for i, line in enumerate(m["lines"]):
            d.text((x0, y0 + i * m["line_height"]), line, font=m["font"], fill=fill)

    def gray_rgb(a, gamma=True):
        q = np.clip(np.asarray(a, dtype=np.float64), 0.0, 1.0)
        if gamma:
            q = q ** (1.0 / 2.2)
        q = np.rint(q * 255.0).astype(np.uint8)
        return np.repeat(q[..., None], 3, axis=2)

    static_glare = Image.fromarray(gray_rgb(r["glare_removed"])).resize(
        (300, 266), Image.Resampling.BILINEAR)
    ay, ax = a_yx
    y0 = min(max(0, ay - 12), r["raw_mosaic"].shape[0] - 24)
    x0 = min(max(0, ax - 12), r["raw_mosaic"].shape[1] - 24)
    crop = gray_rgb(r["raw_mosaic"][y0:y0 + 24, x0:x0 + 24], gamma=False)
    mosaic_zoom = Image.fromarray(crop).resize((288, 288), Image.Resampling.NEAREST)

    def draw_graph(im, k):
        d = ImageDraw.Draw(im)
        rect = (990, 145, 1244, 397)
        d.rectangle(rect, outline=(185, 190, 200), width=1)
        rx0, ry0, rx1, ry1 = rect
        xp = lambda v: rx0 + float(v) / 180.0 * (rx1 - rx0)
        yp = lambda v: ry1 - float(v) * (ry1 - ry0)
        for tv in (0, 45, 90, 135, 180):
            px = int(round(xp(tv))); d.line((px, ry1, px, ry1 + 5), fill=(185, 190, 200))
            put_text(im, str(tv), (px, ry1 + 8), anchor="ct")
        for tv in (0.0, 0.5, 1.0):
            py = int(round(yp(tv))); d.line((rx0 - 5, py, rx0, py), fill=(185, 190, 200))
            put_text(im, "%.1f" % tv, (rx0 - 8, py), anchor="rm")
        colors = ((255, 145, 55), (75, 180, 255), (115, 230, 140))
        for lab, curve, col in zip(labels, curves, colors):
            pts = [(int(round(xp(t))), int(round(yp(np.clip(v, 0.0, 1.0)))))
                   for t, v in zip(theta_deg, curve)]
            d.line(pts, fill=col, width=3)
            for p in pts:
                d.ellipse((p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2), fill=col)
            put_text(im, lab, (pts[-1][0] - 5, pts[-1][1]), size=22, anchor="rm",
                     fill=col, plate=(18, 21, 28), pad=1)
        cur = int(round(xp(theta_deg[k])))
        d.line((cur, ry0, cur, ry1), fill=(255, 238, 80), width=2)
        put_text(im, "3画素の強度対 θ", (950, 62), size=24)
        put_text(im, "強度", (950, 104))
        put_text(im, "θ [度]", ((rx0 + rx1) // 2, 438), anchor="ct")
        put_text(im, "偏光度 DoLP\nA %.2f / B %.2f / C %.3f" % tuple(dolps),
                 (950, 485), size=22)
        put_text(im, "最大/最小比\nA %.2f / B %.2f / C %.2f" % tuple(ratios),
                 (950, 560), size=22)

    frames = []
    for k, deg in enumerate(theta_deg):
        analyser = 0.5 * (s0 + s1 * np.cos(2.0 * theta[k]) + s2 * np.sin(2.0 * theta[k]))
        im = Image.new("RGB", (1280, 720), (18, 21, 28))
        d = ImageDraw.Draw(im)
        d.rectangle((0, 0, 1279, 55), fill=(31, 38, 51))
        put_text(im, "偏光で鏡面を剥がす —— 検光子を回すと光沢だけが cos² で呼吸する",
                 (14, 10), size=24)
        put_text(im, "検光子 θ = %.1f°" % deg, (1265, 10), size=24, anchor="rt")

        left = Image.fromarray(gray_rgb(analyser)).resize((560, 560), Image.Resampling.BILINEAR)
        im.paste(left, (20, 70))
        ld = ImageDraw.Draw(im)
        dcx, dcy, rr = 62, 112, 28
        ld.ellipse((dcx - rr, dcy - rr, dcx + rr, dcy + rr), outline=(255, 245, 100), width=2)
        rad = np.deg2rad(deg)
        ld.line((dcx, dcy, dcx + rr * np.cos(rad), dcy + rr * np.sin(rad)),
                fill=(255, 245, 100), width=3)
        for (yy, xx), lab, col in zip(samples, labels,
                                      ((255, 145, 55), (75, 180, 255), (115, 230, 140))):
            px = 20 + int(round(xx * 559 / 1023)); py = 70 + int(round(yy * 559 / 1023))
            ld.ellipse((px - 7, py - 7, px + 7, py + 7), outline=col, width=3)
            put_text(im, lab, (px + 10, py), size=22, anchor="lm", fill=col,
                     plate=(18, 21, 28), pad=1)

        put_text(im, "鏡面を剥がした像\nS0 − √(S1²+S2²)", (610, 62), size=22)
        im.paste(static_glare.resize((300, 230), Image.Resampling.BILINEAR), (610, 140))

        im.paste(mosaic_zoom, (616, 410))
        put_text(im, "DoFPモザイク　拡大12×", (610, 370), size=22,
                 plate=(18, 21, 28), pad=2)
        # 12 px の単画素へ 22 px 文字は入らないため、代表 2×2 格子を同じ並びの
        # 22 px ラベルで示す。元画素への最近傍拡大は上の 24×24 crop だけに限定。
        for text, px, py in (("0°", 630, 420), ("45°", 765, 420),
                             ("90°", 630, 650), ("135°", 755, 650)):
            put_text(im, text, (px, py), size=22, plate=(18, 21, 28), pad=1)

        draw_graph(im, k)
        ImageDraw.Draw(im).rectangle((0, 680, 1279, 719), fill=(31, 38, 51))
        put_text(im, "A = フィルムの映り込み(強く偏光)  B = 鋼の映り込み(偏光は弱い)  C = ベルト。入射角 約50°",
                 (12, 679), size=22, pad=0)
        frames.append(np.asarray(im, dtype=np.uint8))

    figs.save_video("analyzer_sweep_explained", frames, fps=12.0, gif_every=2, gif_width=640,
                    caption="検光子を0〜177.5度まで回すと、包装フィルムの映り込みAだけが強く呼吸し、鋼のナットの映り込みBは"
                            "わずかしか変わらず、ベルトの地Cは動かない。"
                            "観測DoLPはA/B/C = %.2f/%.2f/%.3f、最大/最小比は %.2f/%.2f/%.2f。"
                            % (*dolps, *ratios))
    return {"dolp": dict(zip(labels, dolps)), "max_min_ratio": dict(zip(labels, ratios)),
            "sample_yx": dict(zip(labels, samples))}


#: 10 節で振る 2 つの条件: 照明の広さ(ソフトボックスの半角 仰角 x 方位、小さなソフトボックス ±9°x±14° 〜
#: 大きな面照明 ±30°x±80°)と しわの深さ(1〜4 倍)。片方だけを振る 2 本の掃引(しわだけ = 小さな照明で、
#: 照明だけ = しわ 1 倍で)と、両方が大きい 1 点を測る。
LIGHTS = {"小さなソフトボックス": (9.0, 14.0), "面照明 ±15°x±30°": (15.0, 30.0),
          "面照明 ±22°x±55°": (22.0, 55.0), "大きな面照明": (30.0, 80.0)}
WRINKLES = (1.0, 2.0, 3.0, 4.0)
#: 測る条件(照明の名前, しわの倍率): しわだけの掃引 + 照明だけの掃引 + 両方が大きい 1 点
SWEEP = ([("小さなソフトボックス", w) for w in WRINKLES] + [(n, 1.0) for n in LIGHTS if n != "小さなソフトボックス"]
         + [("大きな面照明", 4.0)])
#: 2026-11-08 の探針(10 節と同じ関数、種 = 描画の乱数、雑音の種は +2)の 偏光カメラ / 全画素の固定フィルタ の比。
#: 門はこの表で種によらず成り立つものだけ(結果を見てから置いた門 —— 余白は門の所に書く)。
#:   1024 画素・種 33/41/57: しわだけ(小さな照明)1→2→3→4 倍 0.92→0.96→0.97→0.97(3 本とも同じ形)、
#:     照明だけ(しわ 1 倍)±9°→±15°→±22°→±30° 0.92→0.95→1.01〜1.04→1.04〜1.07、両方 1.36〜1.43
#:   512 画素・種 33/41/57/71/89: しわだけ 0.84〜0.86→0.91〜0.92→0.94〜0.95→0.95〜0.96、
#:     照明だけ 0.84〜0.86→0.86〜0.92→0.92〜1.03→0.96〜1.05、両方 1.13〜1.19
#: 2026-11-09 の確認(独立の探針、種 101/113/127/131/137/149/163/179):
#:   512 画素: しわだけの最大 0.947〜0.966、照明だけ(大きな面照明)0.944〜1.025(1 を超えたのは 8 本中 3 本)、
#:     両方 1.145〜1.352。種 137 は照明だけ 0.944 < しわだけ 0.955 で順序が逆 —— 「1 に届いたのは照明だけ」は
#:     1024 画素の所見で、512 画素では言えない。モザイクのフィルタとの勝ち負けは種 137 で逆転(6.60 < 6.64)
#:   1024 画素・種 101/113/127: しわだけの最大 0.969〜0.978、照明だけ 1.033〜1.059、両方 1.331〜1.371
LOW_EXPOSURE = 1.0 / 8.0          # 鋼を飽和させずに測るための短い露光(HDR の短い方の 1 枚)


def _half(a, h2):
    """真値をモザイクの 1/2 解像度にそろえる(2x2 平均)。"""
    a = np.asarray(a, dtype=np.float64)
    return a.reshape(h2, 2, h2, 2).mean(axis=(1, 3))


def _label_cnr_tools(r, h2):
    """印字の読みやすさ: 黒い印字と白い紙の明るさの差 / 紙の上の揺らぎ。飽和した画素は数えない。"""
    film = _half(r["scene_masks"]["plastic"], h2) > 0.99
    alb = _half(r["truth_albedo"], h2)
    unsat = r["analyzers"].max(axis=0) < 0.999
    ink = film & unsat & (alb < 0.15)
    paper = film & unsat & (alb > 0.75)

    def cnr(img):
        return float((img[paper].mean() - img[ink].mean()) / max(img[paper].std(), 1e-12))
    return cnr


def fixed_polarizer_best(r, cnr):
    """ゼロ点: レンズの前に偏光フィルタを 1 枚、最適な角度で固定する(2.5° 刻みで 0〜180° を全部試す)。

    同じ生モザイクの Stokes から ``2·I(θ) = S0 + S1 cos 2θ + S2 sin 2θ`` を組む(フィルタを付けた普通の
    カメラと同じ明るさの尺度)。★実物の固定フィルタはモザイクを持たないので全画素を使え、透過率も
    違う —— ここでは同じセンサの同じ画素数で比べ、角度を選べることだけを比べる。
    """
    s0, s1, s2 = r["stokes"]
    best = (-np.inf, 0.0, None)
    for th in np.arange(0.0, 180.0, 2.5):
        t = math.radians(th)
        img = s0 + s1 * math.cos(2 * t) + s2 * math.sin(2 * t)
        c = cnr(img)
        if c > best[0]:
            best = (c, th, img)
    return best


def fixed_polarizer_fullres(bench, r, cnr, seed):
    """ゼロ点の 2 本目: 全画素で撮る固定の偏光フィルタのカメラ(モザイクを持たない別のカメラ)。

    偏光カメラと同じセンサ(飽和 10000 電子・読出し 3 電子・12 bit)・同じ露光・同じぼけ・同じ消光比 1/120 で、
    全画素が角度 θ の透過 I(θ) を受ける。角度は**雑音の無い像**で印字の CNR が最良になるものを 2.5° 刻みで
    選ぶ(フィルタに有利な選び方)。偏光カメラ(1/2 解像度)と同じ画素数にそろえるため 2x2 を足す(光子も 4 画素分
    —— これもフィルタに有利)。返り値は (雑音入りの CNR, 角度, 雑音の無い CNR)。
    """
    from scipy import ndimage as _nd
    expo = r["exposure"]
    s0, s1, s2 = (_nd.gaussian_filter(expo * a, 0.7) for a in bench["stokes"])
    leak = 1.0 / r["extinction_ratio"]
    h2 = s0.shape[0] // 2

    def through(th):
        t = math.radians(th)
        c, si = math.cos(2 * t), math.sin(2 * t)
        a = 0.5 * (s0 + s1 * c + s2 * si)
        b = 0.5 * (s0 - s1 * c - s2 * si)                  # 直交する成分(消光比の分だけ漏れる)
        return (a + leak * b) / (1.0 + leak)

    def bin2(a):
        return a.reshape(h2, 2, h2, 2).sum(axis=(1, 3))
    clean, th_best = max((cnr(bin2(through(th))), th) for th in np.arange(0.0, 180.0, 2.5))
    m = through(th_best)
    rng = np.random.default_rng(seed + 7)
    e = rng.poisson(np.clip(m, 0.0, None) * FULL_WELL_E).astype(np.float64) + rng.normal(0.0, READ_E, m.shape)
    levels = 2 ** ADC_BITS - 1
    q = np.round(np.clip(e / FULL_WELL_E, 0.0, 1.0) * levels) / levels
    return cnr(bin2(q)), float(th_best), float(clean)


def bench_glare_numbers(size=1024, seed=33):
    """10 節: 実物に見える検査台で、偏光の分離が何を消して何を残すかを数える。

    真値は描画の内訳(拡散・フィルムの鏡面・鋼の鏡面、s と p)で、分離そのものは
    雑音・ぼけ・消光比・量子化・飽和の入った**生のモザイク**から計算する。
    比べるもの: (1) 分離で残る映り込みと閉形式 2 * I_p = R_p * E(4 節と同じ式を、画素ごとに
    違う入射角で)、(2) ゼロ点 = 偏光子なし / 最適角の偏光フィルタ 1 枚(同じモザイクから組む / 全画素の別の
    カメラ)を、しわだけ・照明の広さだけを振った 2 本の掃引と両方が大きい 1 点で、
    (3) 鋼は飽和しない短い露光で、金属のフレネルの式から出る「偏光している割合」と。★真値も場面も
    自作の描画で、(3) の式は描画と同じ glassmirror.fresnel_conductor —— 実装の検算であって外の真値ではない。
    """
    from scipy import ndimage as _nd
    h2 = size // 2
    bench = render_bench_stokes(size=size, seed=seed)
    r = dofp_inspection_scene(size=size, seed=seed, return_truth=True, bench=bench)
    s0_t = _half(_nd.gaussian_filter(r["truth_stokes"][0], 0.7), h2)
    d_t = _half(_nd.gaussian_filter(r["truth_diffuse"], 0.7), h2)
    sp_t = _half(_nd.gaussian_filter(r["truth_spec_p"], 0.7), h2)
    film_g = _half(r["truth_glare"], h2)
    film = _half(r["scene_masks"]["plastic"], h2) > 0.99
    metal = _half(r["scene_masks"]["metal"], h2) > 0.99
    before = r["stokes"][0]                         # 偏光子の無いカメラが撮る明るさ(4 方位の和の半分 x 2)
    after = r["glare_removed"]
    unsat = r["analyzers"].max(axis=0) < 0.999
    gl = film & unsat & (film_g > 0.25 * float(film_g[film].max()))
    resid_meas = float(np.mean(after[gl] - d_t[gl]))
    resid_pred = float(np.mean(2.0 * sp_t[gl]))
    glare_mean = float(np.mean(s0_t[gl] - d_t[gl]))
    film_removed = 1.0 - resid_meas / glare_mean
    cnr = _label_cnr_tools(r, h2)
    fixed = fixed_polarizer_best(r, cnr)
    sat_metal = float((~unsat & metal).sum() / max(metal.sum(), 1))
    # 鋼: 同じ場面を 1/8 の露光で(飽和しない)。分離で消える割合を、金属のフレネルの式から出る値と比べる
    r_lo = dofp_inspection_scene(size=size, seed=seed + 1, return_truth=True, bench=bench, exposure_scale=LOW_EXPOSURE)
    unsat_lo = r_lo["analyzers"].max(axis=0) < 0.999
    mg_t = _half(r_lo["truth_metal_glare"], h2)
    mg = metal & unsat_lo & (mg_t > 0.25 * float(mg_t[metal].max()))
    metal_removed = 1.0 - float(np.mean(r_lo["glare_removed"][mg])) / float(np.mean(r_lo["stokes"][0][mg]))
    th_m = np.radians(_half(r_lo["truth_theta_deg"], h2)[mg])
    import glassmirror
    rs = glassmirror.fresnel_conductor(np.cos(th_m), STEEL_NK[0], STEEL_NK[1], "s")
    rp = glassmirror.fresnel_conductor(np.cos(th_m), STEEL_NK[0], STEEL_NK[1], "p")
    w = mg_t[mg]                                    # 映り込みの明るさで重みを付けた、偏光している割合
    metal_pred = float(np.sum(w * (rs - rp) / (rs + rp)) / np.sum(w))
    # しわだけ・照明の広さだけの掃引(小さなソフトボックス x しわ 1 倍 = 上の場面)。描画の乱数は同じ種なので、
    # しわの形・ラベル・ナットは同じで、振った量だけが違う
    grid = {}
    for lname, wk in SWEEP:
        soft = LIGHTS[lname]
        if lname == "小さなソフトボックス" and wk == 1.0:
            bg, rg, cg = bench, r, cnr
        else:
            bg = render_bench_stokes(size=size, seed=seed, wrinkle=wk, soft=soft)
            rg = dofp_inspection_scene(size=size, seed=seed + 2, return_truth=True, bench=bg)
            cg = _label_cnr_tools(rg, h2)
        fg = fixed_polarizer_best(rg, cg)
        ff = fixed_polarizer_fullres(bg, rg, cg, seed)
        grid[(lname, wk)] = {"none": cg(rg["stokes"][0]), "fixed": fg[0], "fixed_deg": fg[1], "dofp": cg(rg["glare_removed"]),
                             "fixed_full": ff[0], "fixed_full_deg": ff[1], "fixed_full_clean": ff[2]}
    theta = _half(r["truth_theta_deg"], h2)
    return {"r": r, "film_removed": film_removed, "metal_removed": metal_removed, "metal_pred": metal_pred,
            "resid_meas": resid_meas, "resid_pred": resid_pred, "glare_mean": glare_mean,
            "cnr_before": cnr(before), "cnr_after": cnr(after), "cnr_fixed": fixed[0], "fixed_deg": fixed[1],
            "fixed_img": fixed[2], "sat_metal": sat_metal, "sat_metal_lo": float((~unsat_lo & metal).sum() / max(metal.sum(), 1)),
            "theta_film": float(np.median(theta[gl])), "n_glare_px": int(gl.sum()), "size": size,
            "dolp_film": float(np.median(r["dolp"][gl])), "before": before, "after": after,
            "grid": grid}


def _ratio_full(g, light, wrinkle):
    """偏光カメラ / 全画素の固定フィルタ の印字 CNR の比。"""
    v = g["grid"][(light, wrinkle)]
    return v["dofp"] / v["fixed_full"]


def fig_glare_removed_label(g):
    """代表の図: 偏光子なし / 最適角の偏光フィルタ 1 枚 / 偏光カメラで剥がした像 を原寸(1/2 解像度の画素)で並べる。"""
    if not figs.enabled():
        return None
    from PIL import Image, ImageDraw
    import annotate as AN
    white = float(np.percentile(g["before"][g["r"]["scene_masks"]["plastic"][0::2, 0::2]], 99.5))

    def enc(a):
        q = np.clip(np.asarray(a) / white, 0.0, 1.0) ** (1.0 / 2.2)
        return np.repeat(np.rint(q * 255).astype(np.uint8)[..., None], 3, axis=2)

    tiles = [enc(g["before"]), enc(g["fixed_img"]), enc(g["after"])]
    h, w = tiles[0].shape[:2]
    gap, head, foot = 12, 104, 186
    W_ = 3 * w + 2 * gap
    im = Image.new("RGB", (W_, h + head + foot), (24, 26, 30))
    for i, t in enumerate(tiles):
        im.paste(Image.fromarray(t), (i * (w + gap), head))
    d = ImageDraw.Draw(im)

    def text(s, xy, size=24, fill=(240, 240, 240)):
        m = AN.measure_text(s, font_size=size, min_font_size=size, wrap=False)
        if xy[0] + m["width"] > im.width - 4 or xy[1] + m["height"] > im.height:
            raise ValueError("図の文字がはみ出す: %r" % s)
        for i, line in enumerate(m["lines"]):
            d.text((xy[0], xy[1] + i * m["line_height"]), line, font=m["font"], fill=fill)
    cols = [(255, 190, 120), (200, 230, 160), (140, 220, 255)]
    heads = [("偏光子なし", "映り込みで印字が読めない", "印字の CNR %.1f" % g["cnr_before"]),
             ("偏光フィルタ 1 枚(%.1f° に固定)" % g["fixed_deg"], "角度を選べば同じ程度に消える(同じモザイクから組んだ像)",
              "印字の CNR %.1f(全画素で撮るフィルタなら %.1f)" % (g["cnr_fixed"], g["grid"][("小さなソフトボックス", 1.0)]["fixed_full"])),
             ("偏光カメラで剥がす(S0 − |S1,S2|)", "映り込み %.0f %% 減" % (100 * g["film_removed"]),
              "印字の CNR %.1f" % g["cnr_after"])]
    for i, (a, b, c) in enumerate(heads):
        x = i * (w + gap) + 12
        text(a, (x, 8), size=22)
        text(b, (x, 42), size=18, fill=cols[i])
        text(c, (x, 70), size=18, fill=cols[i])
    y0 = h + head + 8
    lines = [
        "4 方位の画素偏光子センサの生モザイク 1 枚(雑音・ぼけ・消光比 1/120・12 bit・飽和入り、%d 画素の描画)。入射角 約 %.0f°。"
        % (g["size"], g["theta_film"]),
        "この場面(小さなソフトボックス 1 灯)では固定の偏光フィルタ 1 枚で足りる。以下の比は 偏光カメラ / 全画素で撮る固定フィルタ:",
        "しわだけ 1→4 倍で %.2f→%.2f、照明だけ大きな面照明へ広げて %.2f、両方で %.2f(CNR %.1f 対 %.1f、どちらも読めない)。"
        % (_ratio_full(g, "小さなソフトボックス", 1.0), _ratio_full(g, "小さなソフトボックス", 4.0),
           _ratio_full(g, "大きな面照明", 1.0), _ratio_full(g, "大きな面照明", 4.0),
           g["grid"][("大きな面照明", 4.0)]["dofp"], g["grid"][("大きな面照明", 4.0)]["fixed_full"]),
        "しわも照明も差を広げる。%d 画素では 1 に届いたのは照明だけ(512 画素では互角で、種によってしわとの順序も入れ替わる)。" % g["size"],
        "鋼のナットが白いのは飽和(鋼の %.0f %%)。飽和しない短い露光では、鋼の映り込みは %.0f %% 消える(描画と同じ式で %.0f %%)。"
        % (100 * g["sat_metal"], 100 * g["metal_removed"], 100 * g["metal_pred"]),
        "剥がした後に残るしわの筋は R_p·E(フレネルの p 成分): 実測 %.4f / 閉形式 %.4f(差 %.0f %%)。"
        % (g["resid_meas"], g["resid_pred"], 100 * abs(g["resid_meas"] / g["resid_pred"] - 1))]
    for i, line in enumerate(lines):
        text(line, (14, y0 + 29 * i), size=17, fill=(210, 210, 210))
    figs.save("glare_removed_label", np.asarray(im),
              caption="フィルムで包んだ箱のラベルと鋼のナットを、4 方位の画素偏光子センサで 1 枚撮った(%d 画素の描画)。"
                      "左から 偏光子なし / 最適角の偏光フィルタ 1 枚(同じモザイクから組んだ像)/ 偏光カメラで剥がした像。"
                      "印字の CNR は %.1f / %.1f / %.1f(全画素で撮るフィルタなら %.1f)—— "
                      "この場面(小さなソフトボックス 1 灯)では固定のフィルタで足りる。全画素で撮る固定のフィルタ(同じ画素数)と比べた比は、"
                      "しわだけを 4 倍にして %.2f→%.2f、照明だけを大きな面照明へ広げて %.2f、両方で %.2f(CNR %.2f 対 %.2f、どちらも"
                      "印字は読めない)。しわも照明の広さも差を広げる。この %d 画素では 1 に届いたのは照明を広げたときだけだが、512 画素では"
                      "互角で、種によってしわとの順序も入れ替わる。読める水準の差は 1 割未満。"
                      "鋼の映り込みは短い露光(飽和なし)で %.0f %% 消え、描画と同じ金属のフレネルの式の %.0f %% と合う"
                      "(実装の検算)。図の白いナットは飽和。"
                      % (g["size"], g["cnr_before"], g["cnr_fixed"], g["cnr_after"],
                         g["grid"][("小さなソフトボックス", 1.0)]["fixed_full"],
                         _ratio_full(g, "小さなソフトボックス", 1.0), _ratio_full(g, "小さなソフトボックス", 4.0),
                         _ratio_full(g, "大きな面照明", 1.0), _ratio_full(g, "大きな面照明", 4.0),
                         g["grid"][("大きな面照明", 4.0)]["dofp"], g["grid"][("大きな面照明", 4.0)]["fixed_full"],
                         g["size"], 100 * g["metal_removed"], 100 * g["metal_pred"]))
    return True


# --------------------------------------------------------------------------- #
# 1. 真値の生成 —— 拡散・鏡面・フレネル                                          #
# --------------------------------------------------------------------------- #
def scene(h=H, w=W):
    """拡散輻度 (H,W) と鏡面ローブ (H,W) を作る。乱数は使わない。

    拡散側は同心円の縞・斜めの傾き・暗いパッチを重ねた **構造を持つ** 場にする。
    一様な板だと「どの画素でも同じ答え」になり、画素ごとに壊れる不具合が
    平均に隠れる(乱数でも同じ理由で隠れる)。
    """
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    r = np.hypot(yy - cy, xx - cx) / max(h, w)
    diffuse = 0.30 + 0.16 * np.cos(14.0 * r) + 0.10 * (xx / (w - 1))
    diffuse[10:26, 12:34] = 0.02                    # 暗いパッチ(雑音が最初に壊す所)
    diffuse[60:80, 90:120] = 0.55                   # 明るいパッチ
    diffuse = np.clip(diffuse, 0.02, 0.60)
    # 鏡面ローブ = 光源の像。中心を外し、拡散の縞とも暗パッチとも重ねる。
    gy, gx = 0.42 * (h - 1), 0.58 * (w - 1)
    lobe = np.exp(-(((yy - gy) / (0.16 * h)) ** 2 + ((xx - gx) / (0.16 * w)) ** 2))
    return diffuse, lobe


def fresnel_sp(theta_deg, eta=ETA):
    """入射角(度)→ (R_s, R_p)。空気 → 屈折率 eta の誘電体、強度反射率。

    r_s = (n1 cos_i - n2 cos_t)/(n1 cos_i + n2 cos_t)
    r_p = (n1 cos_t - n2 cos_i)/(n1 cos_t + n2 cos_i)
    ブリュースター角 tan(theta_B) = n2/n1 で r_p = 0 —— **p 偏光が消える**ので
    反射光は s 偏光だけになる = 偏光度 1。これが「偏光で鏡面が剥がせる」の全て。
    """
    ci = math.cos(math.radians(theta_deg))
    st = math.sin(math.radians(theta_deg)) / eta
    ct = math.sqrt(max(0.0, 1.0 - st * st))
    rs = (ci - eta * ct) / (ci + eta * ct)
    rp = (ct - eta * ci) / (ct + eta * ci)
    return rs * rs, rp * rp


def specular_components(lobe, theta_deg, irradiance=E0):
    """鏡面反射の s 成分・p 成分の輻度 (H,W) を返す。

    無偏光の光源(照度 E)は s と p に E/2 ずつ配分される。反射すると各々
    ``R_s * E/2`` と ``R_p * E/2`` になる。合計 = 鏡面の全輻度、差 = 偏光した分。
    """
    rs, rp = fresnel_sp(theta_deg)
    return 0.5 * rs * irradiance * lobe, 0.5 * rp * irradiance * lobe


def render_sweep(diffuse, spec_s, spec_p, angles=ANGLES, azimuth=AZIMUTH):
    """偏光子掃引 (N,H,W) を合成する。検光子角 t は s 軸から測る。

    ``I(t) = 0.5*D + I_s cos^2(t - az) + I_p sin^2(t - az)``
    拡散は完全無偏光なのでどの角度でも半分通る。鏡面は s/p が独立にマリュスの
    法則に従う。``specularity.polarization_render`` は鏡面を **完全偏光** として
    しか描けないので(下の 2 節で示すとおり等価な組み替えは可能)、部分偏光の
    前方モデルはここで自分で書く。
    """
    t = np.radians(np.asarray(angles, float) - azimuth)[:, None, None]
    return 0.5 * diffuse[None] + spec_s[None] * np.cos(t) ** 2 \
        + spec_p[None] * np.sin(t) ** 2


def rmse(a, b):
    return evaluation_rmse(a, b, mask=None, nan_policy="raise", weights=None,
                           unit="radiance", reduction="mean", empty="raise", domain="array")


def ratio(num, den):
    """num/den。分母 0 は inf(0/0 は 1)—— 比の表で 0 除算に落ちないように。

    ゼロ点が **厳密に** 真値を当てることが実際に起きる(6 節の方位 0/45 度)。
    そこを例外で落とすと、一番面白い行だけが表から消える。
    """
    if den == 0.0:
        return 1.0 if num == 0.0 else float("inf")
    return num / den


def separate(frames, angles=ANGLES, mvf=0.0):
    return specularity.polarization_separate(frames, angles, max_violation_frac=mvf)


# --------------------------------------------------------------------------- #
# ゼロ点(null)                                                                #
# --------------------------------------------------------------------------- #
def null_no_separation(frames):
    """何もしない —— 撮れた輻度をそのまま拡散だとみなす。

    等間隔 4 方位の平均は当てはめの a0 に厳密一致するので、全輻度 = 2*平均。
    """
    return 2.0 * frames.mean(axis=0)


def null_frame_min(frames):
    """素朴 —— 4 枚の画素ごと最小値を拡散とみなす(残りが鏡面)。"""
    return frames.min(axis=0)


def null_frame_min2(frames):
    """素朴 + 尺度だけ直した版 —— 2 x (4 枚の最小値)。

    op と同じ ``2 * I_min`` の式だが、``I_min`` を **正弦波当てはめでなく
    離散の最小値**で取る。方位が 4 方位の格子に乗っていれば op と一致し、
    外れていると必ず過大評価になる。ゼロ点として一番手強い。
    """
    return 2.0 * frames.min(axis=0)


def main():
    t_all = time.perf_counter()
    gate = polarization_resemblance_gate()
    assert gate["highlight_dolp"] > 0.97
    assert gate["highlight_aolp_error_deg"] < 1.0
    assert abs(gate["aolp_noise_ratio"] - 1.0) < 0.20
    assert gate["no_polarizer_max_dolp"] < 0.02
    print("DoFP resemblance: highlight DoLP %.4f, AoLP error %.3f deg, noise ratio %.3f, no-analyser %.4f"
          % (gate["highlight_dolp"], gate["highlight_aolp_error_deg"],
             gate["aolp_noise_ratio"], gate["no_polarizer_max_dolp"]))
    fig_dofp_camera()
    diffuse, lobe = scene()

    # ---------------------------------------------------------------- #
    print("=== 1. フレネル —— 入射角と鏡面の偏光度 ===")
    print(f"  屈折率 {ETA} / ブリュースター角 tan^-1({ETA}) = {THETA_B:.4f} 度")
    print(f"  {'入射角':>8}{'R_s':>10}{'R_p':>12}{'(R_s+R_p)/2':>14}"
          f"{'鏡面の偏光度':>14}{'match3d 差':>12}")
    for th in (0.0, 20.0, 40.0, THETA_B, 70.0, 85.0):
        rs, rp = fresnel_sp(th)
        dop = (rs - rp) / (rs + rp) if (rs + rp) > 0 else 0.0
        ref = match3d.fresnel_reflectance(math.cos(math.radians(th)), 1.0, ETA)
        print(f"  {th:>8.2f}{rs:>10.5f}{rp:>12.3e}{0.5 * (rs + rp):>14.5f}"
              f"{dop:>14.6f}{abs(0.5 * (rs + rp) - ref):>12.2e}")
    print("  → ブリュースター角で R_p が **厳密に 0.0**(丸めですらない: 分子の")
    print("     cos_t - eta*cos_i が倍精度で完全に打ち消す)= 偏光度 1。")
    print("     垂直入射(0 度)は偏光度 0 —— 偏光板を回しても鏡面は動かない。")
    print("     85 度で偏光度が 0.195 まで落ちるのも重要: **浅すぎても深すぎても")
    print("     偏光は効かない**。使える窓はブリュースター角の周りに限られる。")
    print("     最右列は match3d.fresnel_reflectance との差。同じ式を見ている。")
    if figs.enabled():
        # 図: この PoC の物理はこの 3 本の曲線に尽きる。R_p がブリュースター角で
        #     0 を横切ることが「偏光で鏡面が剥がせる」の全て。
        th_ax = np.linspace(0.0, 89.0, 90)
        rs_c = np.array([fresnel_sp(t)[0] for t in th_ax])
        rp_c = np.array([fresnel_sp(t)[1] for t in th_ax])
        figs.save_plot("fresnel",
                       [("R_s", th_ax, rs_c), ("R_p", th_ax, rp_c),
                        ("鏡面の偏光度 (R_s-R_p)/(R_s+R_p)", th_ax,
                         (rs_c - rp_c) / np.maximum(rs_c + rp_c, 1e-30))],
                       xlabel="入射角 [度]", ylabel="強度反射率 / 偏光度",
                       title="フレネル(屈折率 %.1f、ブリュースター角 %.2f 度)"
                             % (ETA, THETA_B),
                       caption="R_p がブリュースター角で 0 を横切る。浅すぎても"
                               "深すぎても偏光度は落ちる —— 使える窓は限られる。")

    # ---------------------------------------------------------------- #
    print("\n=== 2. 前方モデル —— op の完全偏光モデルとの等価な組み替え ===")
    s_s, s_p = specular_components(lobe, THETA_B)
    frames = render_sweep(diffuse, s_s, s_p)
    # I(t) = 0.5*(D + 2*I_p) + (I_s - I_p) cos^2(t-az)  という恒等式。
    eff_d, eff_s = diffuse + 2.0 * s_p, s_s - s_p
    ref = specularity.polarization_render(eff_d, eff_s, ANGLES, azimuth_deg=AZIMUTH)
    print(f"  自作の部分偏光レンダ vs polarization_render(等価な split)"
          f"の最大差 {np.abs(frames - ref).max():.3e}")
    print("  → 部分偏光の鏡面は「無偏光 2*I_p + 完全偏光 (I_s - I_p)」に厳密に")
    print("     分解できる。**op が拡散として返すのは D ではなく D + 2*I_p** で、")
    print("     これが以下すべての誤差の正体(モデルの外挿ではなく恒等式)。")
    for th in (20.0, 70.0):
        a, b = specular_components(lobe, th)
        f2 = render_sweep(diffuse, a, b)
        r2 = specularity.polarization_render(diffuse + 2 * b, a - b, ANGLES,
                                             azimuth_deg=AZIMUTH)
        print(f"     入射角 {th:>5.1f} 度でも最大差 {np.abs(f2 - r2).max():.3e}")

    # ---------------------------------------------------------------- #
    print("\n=== 3. ブリュースター角での分離 —— ゼロ点と並べる ===")
    d_true = diffuse
    s_true = s_s + s_p
    d_op, s_op = separate(frames)
    rho = 1.0                                       # ブリュースター角の鏡面偏光度
    print(f"  真値: 拡散 平均 {d_true.mean():.4f} / 鏡面 最大 {s_true.max():.4f}"
          f"(ローブ中心)")
    print(f"  {'手法':<34}{'拡散 RMSE':>12}{'鏡面 RMSE':>12}{'op 比':>9}")
    base = rmse(d_op, d_true)
    rows = [
        ("ゼロ点 1: 分離しない(全輻度)", null_no_separation(frames), None),
        ("ゼロ点 2: 4 枚の最小値", null_frame_min(frames), None),
        ("ゼロ点 3: 2 x 4 枚の最小値", null_frame_min2(frames), None),
        ("polarization_separate", d_op, s_op),
    ]
    for name, d_est, s_est in rows:
        e = rmse(d_est, d_true)
        es = rmse(s_est, s_true) if s_est is not None else float("nan")
        rs_txt = f"{es:>12.3e}" if s_est is not None else f"{'—':>12}"
        print(f"  {name:<34}{e:>12.3e}{rs_txt}{ratio(e, base):>11.3g}")
    print("  → ブリュースター角では op の誤差が 1e-17 台 = 倍精度の床。R_p = 0 な")
    print("     ので「2*I_min = D」が恒等式として成り立ち、ゼロ点との比は 14〜15 桁。")
    print("     この「比が意味を失うほど勝つ」のはブリュースター角限定で、4 節で")
    print("     角度を振ると 1.2 倍まで落ちる。**一点で測って一般化してはいけない。**")

    # ---------------------------------------------------------------- #
    print("\n=== 4. 入射角を振る —— 誤差は R_p * E に一致するか ===")
    print(f"  {'入射角':>8}{'鏡面偏光度':>12}{'op 拡散RMSE':>14}{'閉形式 R_p*E':>14}"
          f"{'差':>10}{'ゼロ点1':>12}{'ゼロ点1/op':>12}")
    ang_rows = {}
    g_rms = float(np.sqrt(np.mean(lobe ** 2)))
    for th in THETAS:
        a, b = specular_components(lobe, th)
        f = render_sweep(diffuse, a, b)
        d_e, s_e = separate(f)
        rs, rp = fresnel_sp(th)
        dop = (rs - rp) / (rs + rp)
        e = rmse(d_e, diffuse)
        pred = rp * E0 * g_rms                      # 2*I_p = R_p * E * lobe
        e0n = rmse(null_no_separation(f), diffuse)
        rt = ratio(e0n, e)
        ang_rows[th] = (dop, e, pred, e0n, rt)
        print(f"  {th:>8.2f}{dop:>12.6f}{e:>14.3e}{pred:>14.3e}"
              f"{abs(e - pred):>10.1e}{e0n:>12.3e}{rt:>12.3g}")
    th_ax = list(THETAS)
    figs.save_plot("angle_error",
                   [("op の拡散 RMSE", th_ax, [ang_rows[t][1] for t in th_ax]),
                    ("閉形式 R_p * E", th_ax, [ang_rows[t][2] for t in th_ax]),
                    ("ゼロ点 1(分離しない)", th_ax,
                     [ang_rows[t][3] for t in th_ax])],
                   xlabel="入射角 [度]", ylabel="拡散の RMSE",
                   title="誤差は R_p * E に一致する(ブリュースター角で 0)",
                   caption="実測と閉形式が重なる。70 度の絶対誤差は 20 度より悪い"
                           "のに、ゼロ点比では 70 度が最良 —— 最適角は評価軸で割れる。")
    print("  → 誤差は閉形式 R_p * E に厳密一致(差は 1e-17 台)。理論どおり")
    print("     ブリュースター角で最良。ただし **20 度ではゼロ点の 1.2 倍しか")
    print("     勝たない** —— 偏光板を付ける価値が無い角度がある。")
    print("  → **最適角は評価軸で変わる、というのがこの表の一番の中身。**")
    print("     絶対誤差で並べると 56.31 < 40 度(8.6e-3)< 20 度(2.0e-2)")
    print("     < 70 度(2.6e-2)で、**70 度は 20 度より悪い**(R_p が 1 節の表の")
    print("     とおり 20 度 0.033 → 70 度 0.042 と、深い側で急に立ち上がるため)。")
    print("     ところがゼロ点との比では 70 度(4.03)が最良で 20 度(1.20)が最悪。")
    print("     鏡面自体が 70 度で強いので「何もしない」損が大きいから。")
    print("     ハイライトを消したいなら比を、拡散の絶対値が要るなら絶対誤差を見る。")

    # ---------------------------------------------------------------- #
    print("\n=== 5. 入射角が既知なら偏りは閉形式で消せる ===")
    print(f"  {'入射角':>8}{'op RMSE':>12}{'補正後 RMSE':>14}{'雑音増幅 1/ρ':>14}")
    corr_rows = {}
    for th in THETAS:
        a, b = specular_components(lobe, th)
        f = render_sweep(diffuse, a, b)
        d_e, s_e = separate(f)
        rs, rp = fresnel_sp(th)
        r = (rs - rp) / (rs + rp)
        s_c = s_e / r                               # 真の鏡面 = 偏光分 / 偏光度
        d_c = (d_e + s_e) - s_c                     # 全輻度は保存されている
        corr_rows[th] = (rmse(d_e, diffuse), rmse(d_c, diffuse), 1.0 / r)
        print(f"  {th:>8.2f}{corr_rows[th][0]:>12.3e}{corr_rows[th][1]:>14.3e}"
              f"{1.0 / r:>14.2f}")
    print("  → I_s + I_p = (I_s - I_p)/ρ、ρ = (R_s-R_p)/(R_s+R_p) = 鏡面の偏光度。")
    print("     入射角さえ分かれば偏りは完全に消える(1e-17 台)。代償は 1/ρ 倍の")
    print("     雑音増幅で、20 度では 5.9 倍。**op にはこの ρ を渡す口が無い**(所見 a)。")

    # ---------------------------------------------------------------- #
    print("\n=== 6. 方位が 4 方位の格子に乗るかどうか ===")
    print("  ブリュースター角で測る(op が厳密になる条件。ここで出る差は")
    print("  すべて「方位が格子に乗るか」だけに由来する)。右 2 列は入射角 70 度。")
    print(f"  {'入射面方位':>10}{'op RMSE':>12}{'ゼロ点3':>12}{'比':>10}"
          f"{'op(70度)':>12}{'ゼロ点3(70度)':>16}{'比':>8}")
    az_rows = {}
    ab_b, bb_b = specular_components(lobe, THETA_B)
    ab_7, bb_7 = specular_components(lobe, 70.0)
    for az in (0.0, 10.0, 22.5, 45.0):
        fb = render_sweep(diffuse, ab_b, bb_b, azimuth=az)
        f7 = render_sweep(diffuse, ab_7, bb_7, azimuth=az)
        e, e3 = rmse(separate(fb)[0], diffuse), rmse(null_frame_min2(fb), diffuse)
        e7, e37 = rmse(separate(f7)[0], diffuse), rmse(null_frame_min2(f7), diffuse)
        az_rows[az] = (e, e3, e7, e37)
        print(f"  {az:>10.1f}{e:>12.3e}{e3:>12.3e}{ratio(e3, e):>10.3g}"
              f"{e7:>12.3e}{e37:>16.3e}{ratio(e37, e7):>8.2f}")
    print("  → 方位が 0 度 / 45 度(= 測った角度そのもの)では離散最小値が真の")
    print("     I_min に **厳密に**一致するので、素朴なゼロ点 3 の誤差が 0 になり、")
    print("     丸めの乗る当てはめ(4.7e-17)より **わずかに良い**(比 0 はそれ)。")
    print("     22.5 度で初めて差がつく。正弦波当てはめが効くのは格子から外れた")
    print("     ときだけで、「当てはめだから常に良い」ではない。")
    print("  → 右 2 列(70 度)では同じ比が 1.9 倍まで縮む。op 側に R_p 由来の偏り")
    print("     2.6e-2 が常時載っていて、方位のずれによる差をそれが覆い隠すため。")
    print("     **比を見るときは分母が何で律速されているかを先に見る。**")

    # ---------------------------------------------------------------- #
    print("\n=== 7. 偏光度と Stokes —— 別の op も同じ真値に合うか ===")
    a70, b70 = specular_components(lobe, 70.0)
    f70 = render_sweep(diffuse, a70, b70)
    dolp = specularity.polarization_dolp_map(f70, ANGLES)
    dolp_true = (a70 - b70) / (diffuse + a70 + b70)
    print(f"  polarization_dolp_map と閉形式 (I_s-I_p)/(D+I_s+I_p) の最大差 "
          f"{np.abs(dolp - dolp_true).max():.3e}")
    print(f"  画素ごとの偏光度: 最大 {dolp.max():.4f}(ローブ中心)/ "
          f"ローブ外 {dolp[0, 0]:.3e}")
    st = specularity.polarization_stokes(f70, ANGLES)
    s0_true = float((diffuse + a70 + b70).mean())
    print(f"  polarization_stokes S0 {st[0]:.6f} / 閉形式の全輻度平均 "
          f"{s0_true:.6f}(差 {abs(st[0] - s0_true):.2e})")
    print(f"  S3 = {st[3]:.1f} —— 直線検光子だけでは円偏光は見えない(仕様どおり)。")
    if figs.enabled():
        # 図: 入射角 70 度(偏りが常時載る条件)での分離の現物。残差が鏡面ローブ
        #     の形をしていることが、誤差 = R_p * E * lobe の目で見える証拠。
        d70, s70 = separate(f70)
        figs.save_grid("separation",
                       [f70[0], diffuse, d70, d70 - diffuse],
                       ["撮影 0 度", "真の拡散", "op の拡散", "op − 真"],
                       title="入射角 70 度での分離(右下が R_p * E の偏り)",
                       signed=[False, False, False, True],
                       caption="残差はローブと同じ形。鏡面は消えているが、"
                               "拡散が R_p * E だけ持ち上がっている(所見 a)。")
    print(f"  → 場面全体の偏光度は {math.hypot(st[1], st[2]) / st[0]:.4f} で、")
    print(f"     画素最大 {dolp.max():.4f} の 1/6 しかない。**空間平均は鏡面を")
    print("     薄める** —— ここを取り違えると「偏光が使えない場面」と誤判定する。")

    # ---------------------------------------------------------------- #
    print("\n=== 8. 壊れる条件 —— すべてブリュースター角で測る ===")
    print("  雑音も較正誤差も飽和も無ければ op はここで厳密(3 節)。だから以下の")
    print("  表に出る誤差は 100% 壊れ由来で、モデルの偏りと混ざらない。")
    bias70 = ang_rows[70.0][1]              # 入射角 70 度で常時載る偏り = 物差し
    print(f"  物差し: 入射角 70 度で常時載る R_p 由来の偏り = {bias70:.3e}。")
    print("  壊れがこれを超えたら「角度を選び直す」より先に直すべき問題になる。")

    print("\n=== 8-(a) 雑音 ===")
    print(f"  {'雑音σ':>10}{'既定(fail-closed)':>20}{'違反画素率':>12}"
          f"{'RMSE(強制通過)':>16}{'70度の偏り比':>14}")
    fb = render_sweep(diffuse, s_s, s_p)            # ブリュースター角の掃引
    noise_rows = {}
    rng = np.random.default_rng(20260906)
    cvec = np.cos(np.radians(2 * np.asarray(ANGLES)))[:, None, None]
    svec = np.sin(np.radians(2 * np.asarray(ANGLES)))[:, None, None]
    for sigma in (0.0, 1e-4, 1e-3, 2e-3, 3e-3, 4e-3, 5e-3, 1e-2, 3e-2, 1e-1):
        fn = np.maximum(fb + sigma * rng.standard_normal(fb.shape), 0.0)
        try:
            separate(fn)
            verdict = "通る"
        except ValueError:
            verdict = "拒否"
        d_f, _ = separate(fn, mvf=1.0)              # 強制的に通した場合
        # 違反画素率 = 当てはめた最小輻度が負になった画素(4 方位なら閉形式)
        a0 = fn.mean(axis=0)
        amp = np.hypot(2 * (fn * cvec).mean(axis=0), 2 * (fn * svec).mean(axis=0))
        frac = float((a0 - amp < 0).mean())
        e = rmse(d_f, diffuse)
        noise_rows[sigma] = (verdict, frac, e)
        if sigma == 1e-2:
            noisy_ref = fn
        print(f"  {sigma:>10.0e}{verdict:>18}{frac:>12.5f}{e:>16.3e}"
              f"{e / bias70:>14.3f}")
    print("  → **既定の fail-closed が拒否に転じる境界は σ = 3e-3 と 4e-3 の間**")
    print("     (暗パッチの拡散 0.02 = 最小輻度 0.01 に雑音が届く点。12288 画素の")
    print("     うち 0.03% = 4 画素が負の最小輻度を吐いた時点で全体が止まる)。")
    print("     強制通過させた誤差は σ にほぼ厳密に比例する(σ 10 倍 → 誤差 10 倍)。")
    print("     70 度の偏り 2.56e-2 に並ぶのは **σ ≈ 1.3e-2**。つまり σ がそれ未満")
    print("     なら、雑音を減らすより **入射角を選び直す方が効く**。")
    print("     拒否は「使えない」ではなく「その画素の偏光信号が雑音に埋もれた」")
    print("     という正しい報告(1 画素でも全体を止めるのは設計どおり)。")

    # 4 枚目は何を買っているのか。3 枚(0/45/90)でも未知数はちょうど決まる。
    e4 = noise_rows[1e-2][2]
    e3 = rmse(specularity.polarization_separate(
        noisy_ref[:3], ANGLES[:3], max_violation_frac=1.0)[0], diffuse)
    noise_3v4 = (e3, e4)
    print(f"  σ=1e-2 で 3 枚(0/45/90){e3:.3e} vs 4 枚 {e4:.3e} "
          f"= 4 枚が {e3 / e4:.2f} 倍良い")
    print("  → **4 枚目は雑音があるときだけ効く。** 未知数は 3 つなので雑音が")
    print("     無ければ 3 枚で厳密に決まり(この PoC の他の節は 3 枚でも同じ数字)、")
    print("     4 枚目が買っているのは平均化だけ。DoFP センサが 4 方位を敷くのは")
    print("     解を決めるためではない。")

    # ---------------------------------------------------------------- #
    print("\n=== 8-(b) 偏光子角度の較正誤差 ===")
    print(f"  {'誤差δ[度]':>10}{'全体オフセット':>16}{'方位の誤差[度]':>16}"
          f"{'1 枚だけずれ':>16}{'70度の偏り比':>14}")
    cal_rows = {}
    for delta in (0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0):
        f_all = render_sweep(diffuse, s_s, s_p,
                             angles=tuple(x + delta for x in ANGLES))
        e_all = rmse(separate(f_all)[0], diffuse)   # 公称角で解く
        sk = specularity.polarization_stokes(f_all, ANGLES)
        az_est = 0.5 * math.degrees(math.atan2(sk[2], sk[1]))
        az_err = abs((az_est - AZIMUTH + 90.0) % 180.0 - 90.0)
        f_one = render_sweep(diffuse, s_s, s_p,
                             angles=(0.0, 45.0 + delta, 90.0, 135.0))
        e_one = rmse(separate(f_one, mvf=1.0)[0], diffuse)
        cal_rows[delta] = (e_all, az_err, e_one)
        print(f"  {delta:>10.1f}{e_all:>16.3e}{az_err:>16.3f}{e_one:>16.3e}"
              f"{e_one / bias70:>14.3f}")
    print("  → **全画素共通のオフセットは分離を一切壊さない**(20 度ずらしても")
    print("     1e-17 台のまま)。基底が丸ごと回るだけで、当てはめの平均も振幅も")
    print("     変わらないから。代わりに **方位(AoLP)がちょうど δ だけ狂う**")
    print("     (3 列目が δ に厳密一致)。壊れる先が違う 2 つを、1 つの「較正精度」")
    print("     という数字で語ってはいけない —— 絶対角は形状復元だけを壊す。")
    print("  → 1 枚だけのずれ(= 相対角の誤差)は分離そのものを壊すが、**係数が")
    print("     小さい**: δ <= 5 度では 1 度あたり 1.14e-4 で厳密に比例し、その先は")
    print("     頭打ちになる(20 度で 1.5e-3)。20 度ずらしても 70 度の偏りの")
    print("     0.06 倍にしかならず、これは想定と逆だった。**この 3 つの壊れの")
    print("     中で較正誤差が一番効かない。** 市販の偏光センサ級の素子ばらつき 1 度は、")
    print("     偏光分離の観点では無視してよい(方位を使う形状復元では効く)。")

    # ---------------------------------------------------------------- #
    print("\n=== 8-(c) 鏡面の白飛び ===")
    print("  露光は固定のまま **光源だけを強くする**(拡散の最大は 0.275 で")
    print("  飽和しないので、飛ぶのはハイライトだけ)。真の拡散は不変。")
    print(f"  {'光源倍率':>10}{'鏡面ピーク':>12}{'飽和画素率':>12}{'例外':>8}"
          f"{'拡散RMSE':>14}{'70度の偏り比':>14}{'拡散に対する%':>16}")
    sat_rows = {}
    for k in (1.0, 3.0, 4.0, 5.0, 6.0, 8.0):
        fk = np.minimum(render_sweep(diffuse, k * s_s, k * s_p), 1.0)
        raw = render_sweep(diffuse, k * s_s, k * s_p)
        frac = float((raw > 1.0).mean())
        try:
            separate(fk)
            exc = "無し"
        except ValueError:
            exc = "拒否"
        d_k, _ = separate(fk, mvf=1.0)
        e = rmse(d_k, diffuse)
        sat_rows[k] = (frac, exc, e)
        print(f"  {k:>10.1f}{float((k * s_s).max()):>12.3f}{frac:>12.5f}{exc:>8}"
              f"{e:>14.3e}{e / bias70:>14.3f}{100 * e / diffuse.mean():>16.2f}")
    figs.save_table("saturation",
                    ["光源倍率", "飽和画素率 [%]", "例外", "拡散 RMSE",
                     "70 度の偏り比"],
                    [["%.1f" % k, "%.3f" % (100 * sat_rows[k][0]), sat_rows[k][1],
                      "%.3e" % sat_rows[k][2], "%.2f" % (sat_rows[k][2] / bias70)]
                     for k in (1.0, 3.0, 4.0, 5.0, 6.0, 8.0)],
                    title="白飛びは黙って壊す(例外は一度も出ない)",
                    caption="画素率 1.8 倍で誤差 2.8 倍 —— 雑音(σ に比例)や較正誤差"
                            "(δ に比例)と違い、飽和は超線形に効く。",
                    col_w=125)
    fig_analyzer_sweep_explained()
    print("  → 白飛びは **一度も例外を出さない**。I_max が頭打ちになると振幅が")
    print("     縮み、I_min が持ち上がり、拡散が過大評価される側へ静かに倒れる。")
    print("     しかも壊れ方が急峻: 飽和 0.6% で 70 度の偏りの 0.15 倍、1.3% で")
    print("     0.49 倍、**2.4% で 1.35 倍**(拡散平均の 9.7% を誤る)。雑音(σ に")
    print("     比例)や較正誤差(δ に比例)と違い、**飽和は画素率に対して超線形**")
    print("     (画素率 1.8 倍で誤差 2.8 倍)。飛んだ画素では偏光情報が完全に")
    print("     失われるので、当てはめは残った 3 点に平気で正弦波を通す。")
    print("     fail-closed 検査は「最小輻度が負」= **下端しか見ておらず、上端の")
    print("     飽和は素通りする**(所見 c)。3 つの壊れのうちこれだけが黙っている。")

    # ---------------------------------------------------------------- #
    print("\n=== 9. 速度(この機械での実測)===")
    big_d, big_l = scene(1024, 1024)
    ba, bb = specular_components(big_l, 70.0)
    big = render_sweep(big_d, ba, bb)
    for label, fn in (("polarization_separate", lambda: separate(big)),
                      ("polarization_dolp_map",
                       lambda: specularity.polarization_dolp_map(big, ANGLES)),
                      ("polarization_stokes",
                       lambda: specularity.polarization_stokes(big, ANGLES)),
                      ("ゼロ点 3(最小値)", lambda: null_frame_min2(big))):
        t0 = time.perf_counter()
        fn()
        print(f"  {label:<26}{1e3 * (time.perf_counter() - t0):>9.1f} ms  "
              f"(4 x 1024 x 1024)")
    print("  → 3 つの op はどれも同じ正弦波当てはめ 1 回で、コストは区別できない。")
    print("     素朴な最小値の 13 倍だが、1 Mpixel で 83 ms は毎フレーム回せる。")
    print("     **偏光板を付けない理由に計算コストは使えない。**")

    # ---------------------------------------------------------------- #
    print("\n=== 10. 実物に見える検査台 —— フィルムで包んだラベルと鋼のナット ===")
    size10 = 1024 if figs.enabled() else 512
    g10 = bench_glare_numbers(size10)
    print(f"  {size10}x{size10} の生モザイク 1 枚(雑音・ぼけ・消光比 1/120・12 bit・飽和入り)")
    print(f"  フィルムの映り込み(入射角の中央値 {g10['theta_film']:.1f} 度、{g10['n_glare_px']} 画素): "
          f"偏光度 {g10['dolp_film']:.2f}、分離で {100 * g10['film_removed']:.1f} % 消える")
    print(f"  分離の後に残る映り込み: 実測 {g10['resid_meas']:.4f} / 閉形式 2*I_p = R_p*E "
          f"{g10['resid_pred']:.4f}(差 {100 * abs(g10['resid_meas'] / g10['resid_pred'] - 1):.1f} %、映り込みの平均 {g10['glare_mean']:.4f})")
    print(f"  印字の CNR(黒い印字と白い紙の差 / 紙の揺らぎ): 偏光子なし {g10['cnr_before']:.2f} / "
          f"偏光フィルタ 1 枚(最適角 {g10['fixed_deg']:.1f}°){g10['cnr_fixed']:.2f} / 偏光カメラ {g10['cnr_after']:.2f}")
    print("  しわだけ / 照明の広さだけを振る(印字の CNR: 偏光子なし / 固定のフィルタ(モザイクから組む)/"
          " 固定のフィルタ(全画素の別のカメラ、2x2 を足す)/ 偏光カメラ)")
    for (lname, wk), v in g10["grid"].items():
        print(f"    {lname:<14} しわ {wk:.0f} 倍: {v['none']:.2f} / {v['fixed']:.2f}(最適角 {v['fixed_deg']:.1f}°)/ "
              f"{v['fixed_full']:.2f}(最適角 {v['fixed_full_deg']:.1f}°)/ {v['dofp']:.2f}   偏光カメラ / フィルタ = "
              f"{v['dofp'] / v['fixed']:.2f}(モザイク)/ {v['dofp'] / v['fixed_full']:.2f}(全画素)")
    rw = [_ratio_full(g10, "小さなソフトボックス", w) for w in WRINKLES]
    rl = [_ratio_full(g10, n, 1.0) for n in LIGHTS]
    print("  → 全画素の固定フィルタとの比: しわだけ " + " → ".join("%.2f" % x for x in rw)
          + "、照明の広さだけ " + " → ".join("%.2f" % x for x in rl)
          + "、両方 %.2f" % _ratio_full(g10, "大きな面照明", 4.0))
    print("     しわも照明の広さも比を偏光カメラ側へ押し上げる。1024 画素では 1 に届いたのは照明を広げたときだけだが、")
    print("     512 画素では互角で、種によってしわとの順序も入れ替わる(種 137: 照明だけ 0.944 < しわだけ 0.955)。")
    print("     読める水準(CNR > 3)での差は 1 割未満。両方が大きいときの大差は CNR 2 前後(どちらも読めない)。モザイクから組んだフィルタは")
    print("     全画素のものより CNR が低く、その分だけ偏光カメラを有利に見せる(勝ち負けは種で入れ替わるので門にしない)。")
    print("     数は %d 画素・種 1 本(種を振った表は" % size10)
    print("     docstring の SWEEP の上に記録)。")
    print(f"  鋼のナット: 通常の露光では {100 * g10['sat_metal']:.1f} % が飽和。1/8 の露光(飽和 {100 * g10['sat_metal_lo']:.1f} %)で"
          f"分離で消える割合 {100 * g10['metal_removed']:.1f} %、描画と同じ金属のフレネルの式(n {STEEL_NK[0]}, k {STEEL_NK[1]}、実装の検算)で "
          f"{100 * g10['metal_pred']:.1f} %")
    print("  → 誘電体(フィルム)の映り込みは偏光で 9 割剥がれ、残りは R_p*E の 1 割以内。偏光カメラが固定のフィルタを")
    print("     読める水準で上回る差は小さい(照明を広げたときに 1 割未満)。鋼の映り込みが残るのは偏光が弱いこと(式どおり)と飽和の両方。")
    fig_glare_removed_label(g10)

    print("\n所見(想定と違ったこと):")
    print("   (1) 「ブリュースター角付近が最良」は正しかったが、**理由が予想と")
    print("       違った**。最初は「鏡面が強く偏光するから分離しやすい」と書こうと")
    print("       したが、誤差の閉形式は R_p * E であって R_s には依らない。")
    print("       効いているのは「s が強い」ではなく「**p が消える**」の方。")
    print("   (2) 「ブリュースター角から離れるほど悪い」を対称だと思い込んでいた。")
    print("       R_p は浅い側では緩やか(0 度 0.040 → 20 度 0.033 → 40 度 0.014)")
    print("       なのに深い側では急峻(70 度 0.042)で、**70 度の絶対誤差は")
    print("       20 度より悪い**。それでもゼロ点比では 70 度が最良(4.0 対 1.2)。")
    print("       同じ実験の同じ列から、評価軸を変えると最適角が 40 度と 70 度に")
    print("       割れる。**「最良の入射角」は単独では意味を持たない。**")
    print("   (3) 素朴な 2 x 最小値が方位 0/45 度では op に引き分けた(6 節)。")
    print("       それどころか誤差が厳密に 0 で、丸めの乗る当てはめより少し良い。")
    print("       ゼロ点を 3 種類置かなければ「当てはめが常に勝つ」と書いていた。")
    print("   (4) 3 つの壊れの強さの順が予想と逆だった。**較正誤差が一番効かず**")
    print("       (20 度ずれても 70 度の偏りの 0.06 倍)、飽和が一番危ない。")
    print("       危険さは大きさではなく **黙るかどうか** で決まる: 雑音は拒否で")
    print("       止まり、較正誤差は小さく、飽和だけが例外なしで大きく外す。")

    print("\n所見(fullseye の穴 —— この PoC が出した道具の穴):")
    print("   (a) `polarization_separate` の返す \"diffuse\" は真の拡散より")
    print("       **常に R_p * E だけ大きい**(2 節の恒等式、4 節の実測)。docstring は")
    print("       「垂直入射で false」とだけ書くが、**偏りが閉形式で書ける**ことも、")
    print("       ρ = (R_s-R_p)/(R_s+R_p) を渡せば完全に消せることも書いていない。")
    print("       `specular_dop=` のような引数が 1 つあれば 5 節の補正が op 内で済む。")
    print("   (b) **AoLP(偏光の方位角)を返す op が無い。** `_polar_fit` は a1,a2 を")
    print("       計算しているので 0.5*atan2(a2,a1) を返すだけだが、外へ出る口は")
    print("       `polarization_stokes` の **場面全体 1 本**しかない。方位は入射面の")
    print("       向き = 面法線の方位そのもので、形状復元の主役なのに画素ごとに")
    print("       取れない(`polar_cam.py` は自前で計算していて op を使っていない)。")
    print("   (c) fail-closed 検査は下端(最小輻度が負)だけを見ており、**上端の")
    print("       飽和は素通りする**(8-c)。飽和は例外なしで拡散を過大評価する側へ")
    print("       倒れるので、雑音より質が悪い。`I >= 1.0` の画素率を返すか、")
    print("       `max_saturated_frac` があると同じ規律で守れる。")
    print("   (d) **画素ごとの Stokes 地図が無い。** `polarization_stokes` は空間平均")
    print("       (4,) だけで、7 節のとおり場面平均の偏光度 "
          f"{math.hypot(st[1], st[2]) / st[0]:.3f} は画素最大 {dolp.max():.3f} の")
    print("       1/6 以下。平均値で「偏光は使えない」と判断すると取り逃す。")
    print("   (e) 部分偏光の鏡面を **前方合成する op が無い**。")
    print("       `polarization_render` は鏡面完全偏光だけで、フレネルから")
    print("       (R_s, R_p) を作って掃引にする経路は本 PoC が手で書いた。")
    print("       `match3d.fresnel_reflectance` は s/p 平均しか返さないので、")
    print("       s と p を別々に返す口(または `polarization_render_fresnel`)が")
    print("       あれば、この PoC 全体が op の合成で書ける。")

    # ---- 自己検査(速さは assert しない)---------------------------------- #
    # 1. フレネル: ブリュースター角で R_p = 0、match3d と同じ式
    rs_b, rp_b = fresnel_sp(THETA_B)
    assert rp_b < 1e-30, f"ブリュースター角で R_p が 0 でない: {rp_b}"
    for th in (0.0, 20.0, 40.0, 70.0, 85.0):
        rs, rp = fresnel_sp(th)
        assert abs(0.5 * (rs + rp)
                   - match3d.fresnel_reflectance(math.cos(math.radians(th)),
                                                 1.0, ETA)) < 1e-12
    assert abs(fresnel_sp(0.0)[0] - fresnel_sp(0.0)[1]) < 1e-15, \
        "垂直入射で s と p が違う"

    # 2. 前方モデル: 部分偏光レンダ == op の完全偏光レンダ(等価な split)
    assert np.abs(frames - ref).max() < 1e-15, "前方モデルの組み替えが一致しない"

    # 3. ブリュースター角では分離が厳密(倍精度の床)
    assert rmse(d_op, d_true) < 1e-14, \
        f"ブリュースター角で拡散が厳密に出ない: {rmse(d_op, d_true):.3e}"
    assert rmse(s_op, s_true) < 1e-14, "ブリュースター角で鏡面が厳密に出ない"
    # 全輻度は分離で保存される(何も失わず何も作らない)
    assert np.abs((d_op + s_op) - (d_true + s_true)).max() < 1e-14
    # 雑音が無ければ 3 枚でも同じ答え(8-a の主張の裏取り)
    d3 = specularity.polarization_separate(frames[:3], ANGLES[:3])[0]
    assert np.abs(d3 - d_op).max() < 1e-14, "雑音なしで 3 枚と 4 枚の答えが違う"

    # 4. 誤差は閉形式 R_p * E に一致し、ゼロ点に勝つ
    for th, (dop, e, pred, e0n, rt) in ang_rows.items():
        assert abs(e - pred) < 1e-12 + 1e-6 * pred, \
            f"入射角 {th}: 誤差 {e:.3e} が閉形式 {pred:.3e} と違う"
        assert rt > 1.0, f"入射角 {th}: ゼロ点 1 に勝てていない (比 {rt:.2f})"
    assert ang_rows[THETA_B][1] < ang_rows[40.0][1] < ang_rows[20.0][1], \
        "ブリュースター角 → 40 度 → 20 度の順に悪くならない"
    assert ang_rows[THETA_B][1] < ang_rows[70.0][1], "ブリュースター角が最良でない"
    assert ang_rows[20.0][4] < 1.5, "20 度でゼロ点との差が小さいという所見が崩れた"
    # 評価軸で最適角が割れる(所見 2)。絶対誤差では 70 度が 20 度より悪く、
    # ゼロ点比では逆転する。この 2 行が同時に成り立つことが所見の中身そのもの。
    assert ang_rows[70.0][1] > ang_rows[20.0][1], \
        "絶対誤差で 70 度が 20 度より悪い、という所見が崩れた"
    assert ang_rows[70.0][4] > ang_rows[20.0][4], \
        "ゼロ点比で 70 度が 20 度より良い、という所見が崩れた"

    # 5. 入射角が既知なら偏りは消える
    for th, (e_raw, e_corr, amp) in corr_rows.items():
        assert e_corr <= e_raw + 1e-15, f"入射角 {th}: 補正で悪化した"
        assert e_corr < 1e-14, f"入射角 {th}: 補正後も偏りが残る ({e_corr:.3e})"

    # 6. 方位が格子に乗ると素朴なゼロ点が並ぶ / 外れると当てはめが効く
    for az in (0.0, 45.0):
        assert az_rows[az][1] < 1e-14, \
            f"方位 {az} 度で素朴法が引き分ける、という所見が崩れた"
        assert abs(az_rows[az][3] - az_rows[az][2]) < 1e-14, \
            f"方位 {az} 度は 70 度でも引き分けるはず"
    assert az_rows[22.5][1] > 1e3 * az_rows[22.5][0] + 1e-6, \
        "方位 22.5 度で当てはめが効く、という所見が崩れた"
    # op 自体は方位に依らない(当てはめが 3 未知数を厳密に解いているから)
    assert max(az_rows[a][2] for a in az_rows) - min(az_rows[a][2] for a in az_rows) < 1e-14

    # 7. 偏光度と Stokes が閉形式に一致
    assert np.abs(dolp - dolp_true).max() < 1e-12, "偏光度が閉形式と違う"
    assert abs(st[0] - s0_true) < 1e-12, "Stokes S0 が全輻度平均と違う"
    assert st[3] == 0.0, "直線検光子だけで S3 が出ている"

    # 8-(a) 雑音: 既定は fail-closed、σ が上がれば誤差も上がる(単調)
    assert noise_rows[0.0][0] == "通る", "雑音なしで拒否された"
    assert noise_rows[1e-1][0] == "拒否", "σ=0.1 でも拒否されない(fail-closed 破れ)"
    sig = (1e-4, 1e-3, 2e-3, 3e-3, 5e-3, 1e-2, 3e-2, 1e-1)
    errs = [noise_rows[s][2] for s in sig]
    assert all(b > a for a, b in zip(errs, errs[1:])), "雑音で誤差が単調に増えない"
    # 拒否の境界が実在する = どこかで「通る」→「拒否」に変わる
    verdicts = [noise_rows[s][0] for s in sig]
    assert "通る" in verdicts and "拒否" in verdicts, "雑音で境界が見えない"
    assert verdicts.index("拒否") > verdicts.index("通る"), "拒否が先に来ている"
    # 4 枚目は雑音のときだけ効く(3 枚でも未知数はちょうど決まる)
    assert noise_3v4[0] > 1.05 * noise_3v4[1], \
        f"雑音下で 4 枚目が効いていない: 3 枚 {noise_3v4[0]:.3e} / 4 枚 {noise_3v4[1]:.3e}"

    # 8-(b) 全体オフセットは無害(方位だけ δ 狂う)/ 1 枚ずれは有害だが小さい
    for delta, (e_all, az_err, e_one) in cal_rows.items():
        assert e_all < 1e-14, \
            f"全体オフセット {delta} 度で分離が壊れた: {e_all:.3e}"
        assert abs(az_err - delta) < 1e-6, \
            f"全体オフセット {delta} 度で方位誤差が δ に一致しない: {az_err:.4f}"
    assert cal_rows[1.0][2] > 1e6 * cal_rows[0.0][2], \
        "1 枚だけの角度誤差が全体オフセットと区別できない(想定外)"
    assert 1e-5 < cal_rows[1.0][2] < 1e-3, \
        f"1 枚 1 度ずれの誤差が想定の桁でない: {cal_rows[1.0][2]:.3e}"
    ones = [cal_rows[d][2] for d in (0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0)]
    assert all(b > a for a, b in zip(ones, ones[1:])), \
        "1 枚ずれの誤差が δ で単調に増えない"
    assert cal_rows[20.0][2] < bias70, \
        "20 度ずれても 70 度の偏りに届かない、という所見が崩れた"

    # 8-(c) 飽和は例外なしで静かに悪化する(拡散側は最後まで飽和させない)
    assert (0.5 * diffuse).max() < 1.0, "拡散だけで飽和している(実験設計が壊れた)"
    assert sat_rows[1.0][0] == 0.0, "光源 1 倍で既に飽和している"
    assert sat_rows[8.0][0] > 0.02, "光源 8 倍でも飽和しない(シーンが暗すぎる)"
    assert all(v[1] == "無し" for v in sat_rows.values()), \
        "飽和で例外が出た(所見 c の前提が変わった)"
    assert sat_rows[8.0][2] > 1e3 * sat_rows[1.0][2], "飽和で悪化していない"
    assert sat_rows[8.0][2] > bias70, "飽和が 70 度の偏りにすら届かない"

    # 9. ゼロ点の妥当性(そもそもゼロ点が真値そのものになっていないこと)
    assert rmse(null_no_separation(frames), d_true) > 1e-3
    assert rmse(null_frame_min(frames), d_true) > 1e-2

    # 10. 実物に見える検査台: フィルムは剥がれ、鋼は剥がれず、残りは閉形式 R_p*E
    assert g10["film_removed"] > 0.85, f"フィルムの映り込みが剥がれない: {g10['film_removed']:.3f}"
    assert g10["metal_removed"] < 0.60, f"鋼の映り込みまで剥がれた: {g10['metal_removed']:.3f}"
    assert g10["film_removed"] - g10["metal_removed"] > 0.30, "誘電体と金属の差が出ない"
    assert g10["sat_metal_lo"] < 0.01, "短い露光でも鋼が飽和している(飽和と偏光を分けて数えられない)"
    assert abs(g10["metal_removed"] - g10["metal_pred"]) < 0.10, (
        f"鋼の消える割合がフレネルの金属の式と合わない: {g10['metal_removed']:.3f} vs {g10['metal_pred']:.3f}")
    # ゼロ点(偏光フィルタ 1 枚、最適角)。★2026-11-08 の探針(種 5 本 x 512 画素・3 本 x 1024 画素)と 11-09 の確認
    # (種 8 本 x 512・3 本 x 1024、SWEEP の上の表)を見てから置いた門。モザイクから組んだフィルタとの勝ち負けの門
    # (前の版から)は 512 画素・種 137 の大きな面照明で逆転する(6.60 < 6.64)ので外し、全画素のフィルタとの比に一本化した。
    gr = g10["grid"]
    assert max(gr[("大きな面照明", 4.0)]["dofp"], gr[("大きな面照明", 4.0)]["fixed"],
               gr[("大きな面照明", 4.0)]["fixed_full"]) < 3.0, (
        "深いしわ + 面照明で印字が読める CNR になった(「どちらも読めない」の所見が変わった)")
    # 全画素の固定フィルタとの門(探針の種 13 本 x 512・6 本 x 1024 の最小の余白)。CI は 512 画素で走るので、効く余白は
    # 512 画素の列: しわだけでは 1 に届かない(512 の最大 0.966 = 余白 3.4 %。1024 の最大 0.978 = 余白 2.2 % は図つき
    # 実行でだけ効き、CI では効かない)、しわは比を上げる(+0.05 以上、余白 0.03)、照明だけでも比を上げる(512 の種 137 で
    # +0.089、余白 0.039)、照明だけの大きな面照明で差は 1 割未満(0.944〜1.07、余白 4.4 %)、両方が大きいと 1.1 倍を超える
    # (最小 1.13)。「1 に届いたのは照明だけ」は 512 画素で種により成り立たないので門にしない(文で条件を付ける)
    rw = [_ratio_full(g10, "小さなソフトボックス", w) for w in WRINKLES]
    assert max(rw) < 1.0, f"狭い照明でしわだけを深くして全画素の固定フィルタに勝った(所見が変わった): {rw}"
    assert rw[-1] > rw[0] + 0.02, f"しわを深くしても比が上がらない: {rw}"
    r_large = _ratio_full(g10, "大きな面照明", 1.0)
    assert r_large > rw[0] + 0.05, f"照明を広げても比が上がらない: {rw[0]:.3f} → {r_large:.3f}"
    assert abs(r_large - 1.0) < 0.10, f"照明だけを広げたときの差が 1 割を超えた(所見が変わった): {r_large:.3f}"
    assert _ratio_full(g10, "大きな面照明", 4.0) > 1.10, "深いしわ + 面照明で全画素のフィルタとの差が出ない"
    assert all(v["fixed_full"] > 0 and v["fixed"] > 0 for v in gr.values()), "固定のフィルタの CNR が正でない"
    assert abs(g10["resid_meas"] - g10["resid_pred"]) < 0.15 * g10["resid_pred"], (
        f"残る映り込みが R_p*E と合わない: {g10['resid_meas']:.4f} vs {g10['resid_pred']:.4f}")
    assert g10["cnr_after"] > 3.0 * g10["cnr_before"], "剥がしても印字が読みやすくならない"
    assert 45.0 < g10["theta_film"] < 55.0, "入射角がカメラの傾き 50 度の近くにない(幾何が壊れた)"

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))

    print(f"\n総所要 {time.perf_counter() - t_all:.1f} 秒")
    print("PASS")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
