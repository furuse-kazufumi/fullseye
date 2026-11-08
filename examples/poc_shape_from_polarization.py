# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 黒光沢とガラスの形を偏光で測る —— 陰影が無くても、偏光は傾きを覚えている

    py -3.11 examples/poc_shape_from_polarization.py

検査ラインで 3D がいちばん取りにくいのは、**黒い光沢の樹脂**(コネクタのハウジング、塗装面)と
**透明なガラス・樹脂のレンズ**です。どちらも拡散反射がほとんど無いので、照明を変えても陰影が
出ず、照度差ステレオは拠り所を失います。けれど表面で 1 回反射した光の**偏光**は、面の傾きで
決まっています(Fresnel の式)。4 方位のオンチップ偏光子を持つセンサなら、それを 1 ショットで
撮れる。この PoC は、黒光沢のドームとガラスのレンズを並べた場面で、次を実測します。

1. **1 ショットの偏光画像から法線が出る**。生のモザイク(2×2 画素に 0/45/90/135°)を
   ``polarization_demosaic`` で 4 枚に分け、``fs.ledger.sfp_normals`` が画素ごとに法線の
   **候補の集合**(鏡面なので 4 本 = 天頂角 2 × 方位 2)を返し、``sfp_disambiguate`` が
   「凸」という事前情報と Brewster の稜線で 1 本を選び、``sfp_height`` が高さに積分します。
2. **同じ部品に照度差ステレオをかけると崩れる**。4 方向の照明で撮った鏡面のハイライトは
   Lambert の式に乗らないので、法線は数十度ずれる。
3. **曖昧さは隠さない**。解消する前の候補の数(4 本、Brewster の稜線上だけ 2 本)を地図にする。
4. **屈折率は較正球で測る**。同じ材料の球(シルエットから天頂角が分かる)の DoLP に Fresnel の
   曲線を当てはめる。DoLP の最大値は屈折率によらず 1 なので、効くのは「どこで」最大になるか。
5. **どこで壊れるか**。(a) 屈折率を間違える、(b) 雑音が Brewster の稜線と頂上に集まる、
   (c) 拡散が混ざる(偏光が 90° ずれて打ち消し合う)—— それぞれの誤差を地図と曲線で出す。
6. **実物に見える描画で同じ解法**(2026-11-08)。同じドームとレンズを検査用のドーム照明(真上に
   カメラの穴、拡散板の継ぎ目、縁の LED の帯)の下、黒い樹脂の台座・黒いベルベットの上に置き、
   黒い樹脂の拡散 1 %、レンズの下から透ける光、消光比 1/200、レンズのぼけ、ショット雑音、
   読出し雑音、12 bit、ほこりを入れて撮る。照明を映さない所(カメラの穴・台)は像が暗いので
   **像だけから**除き、残りで法線と高さを測る。同じドームを天井のパネル照明で撮った場合とも比べる
   (照明が映り込む範囲で精度が決まる)。測れない範囲が照明の穴の大きさで式どおり動くことも確かめる。
   偏光カメラの公開データは、探した範囲では再配布できる許諾のものが見つからなかったので、図はこの描画で、
   順方向(sfp_render)と逆(sfp_normals)は同じモデルの往復 —— 外の真値は tests/test_sfpolar.py の別経路だけ。

真値: 描画に使った解析的な法線(球冠)と高さ。順方向の描画は ``sfp_render``(閉形式)で、
閉形式そのものは ``tests/test_sfpolar.py`` が ``glassmirror`` の Fresnel と ``optics`` の
Mueller 行列の経路(別のコード)で 1e-14 まで確かめてあり、ここでは要点だけ再掲します。

★正直に書いておくこと(合成であること):
  * 環境光は一様・無偏光、反射は 1 回、正射影。**ガラスの裏面反射と相互反射は入っていない**
    (実物のガラスでは裏面から戻る光が DoLP を下げ、天頂角を浅く読ませる)。
  * [1]〜[5] の雑音は 4 枚の画像に足したガウス雑音だけ(ショット雑音・偏光子の消光比・画素ごとの
    角度ずれは入っていない)。消光比が有限だと DoLP は一様に縮み、屈折率の誤りと同じ形で効く。
    [6] には消光比 1/200・ショット雑音・読出し雑音・12 bit・樹脂の拡散 1 %・ほこりを入れた(角度ずれは無い)。
  * [6] でも部品の位置(mask)は描画から与えている(検査で部品の位置が分かっている前提)。高さの原点は
    1 枚では決まらない(測れた範囲が台に届かない)ので、測れた所の平均を真値に合わせて形の誤差だけを測る。
  * 照度差ステレオの比較は、鏡面の葉(Blinn-Phong、指数 60)+ 弱い拡散(アルベド 0.02)で
    描いた 4 枚。光沢の強さで数字は変わる(崩れ方は変わらない)。
  * 凸の事前情報は部品ごとの mask(連結成分)に 1 つずつ。凹んだ部品や、Brewster の稜線が
    雑音で途切れた部品では効かない —— その場合は粗い深度を事前情報に使う
    (``prior="depth"``、テストで実測)。

走らせ方: ``py -3.11 examples/poc_shape_from_polarization.py``
(図は ``FULLSEYE_FIGURE_DIR`` を指定したときだけ書く)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402  (台帳の公開経路 fs.ledger を使う)
import glassmirror  # noqa: E402
import photometric  # noqa: E402
from scipy import ndimage  # noqa: E402

CHECKS = []

H, W = 128, 256
N_RESIN = 1.57            # 黒い光沢樹脂(ドーム)
N_GLASS = 1.52            # クラウンガラス(レンズ)
NOISE = 0.004             # 4 枚それぞれに足す雑音(露光を合わせた後の平均輝度 ~0.5 に対して)
EXPOSURE = 8.0            # 黒光沢は反射率 4〜10 % しかないので露光を伸ばす


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))


def cap(cy, cx, radius, rim):
    """球冠(半径 radius の球の、像面の半径 rim までの部分)。法線・mask・高さ。"""
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    x, y = (xx - cx) / radius, (yy - cy) / radius
    r2 = x * x + y * y
    m = r2 < (rim / radius) ** 2
    nz = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))
    n = np.stack([x, y, nz], axis=-1)
    n[~m] = (0.0, 0.0, 1.0)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    z = np.where(m, radius * (nz - math.sqrt(1.0 - (rim / radius) ** 2)), 0.0)
    return n, m, z


def scene():
    """左 = 黒光沢のドーム(縁の天頂角 72°、Brewster を越える)、右 = ガラスのレンズ(縁 26°)。"""
    nd_, md, zd = cap(64.0, 66.0, 56.0, 53.0)
    nl, ml, zl = cap(64.0, 190.0, 100.0, 44.0)
    nrm = np.where(md[..., None], nd_, nl)
    index = np.where(md, N_RESIN, N_GLASS)
    return nrm, md, ml, zd + zl, index


def reflectance(nrm, index):
    """一様な環境光の映り込みの明るさ = 無偏光の Fresnel 反射率(glassmirror)。"""
    out = np.zeros(nrm.shape[:2])
    for n in np.unique(index):
        sel = index == n
        out[sel] = glassmirror.fresnel_dielectric(np.clip(nrm[..., 2][sel], 0.0, 1.0), 1.0, float(n))
    return out


def render_sweep(nrm, md, ml, index, diffuse=0.0, seed=0, noise=NOISE):
    """部品ごとの屈折率で描いた 4 方位の画像 + 雑音。diffuse = 拡散の輝度(鏡面の平均に対する比)。"""
    refl = EXPOSURE * reflectance(nrm, index)
    sw = np.zeros((4, H, W))
    for msk, n in ((md, N_RESIN), (ml, N_GLASS)):
        if not msk.any():
            continue
        sw += fs.ledger.sfp_render(nrm, n, specular_radiance=refl * msk,
                                   diffuse_radiance=diffuse * refl[msk].mean() * msk, mask=msk)
    rng = np.random.default_rng(seed)
    return np.clip(sw + rng.normal(0.0, noise, sw.shape), 0.0, None) * (md | ml)


def to_mosaic(sweep):
    """4 枚 → 生のモザイク(2×2 = [[90, 45], [135, 0]]、optics.POLARIZATION_MOSAIC_LAYOUT)。"""
    i0, i45, i90, i135 = sweep
    raw = np.zeros((H, W))
    raw[0::2, 0::2] = i90[0::2, 0::2]
    raw[0::2, 1::2] = i45[0::2, 1::2]
    raw[1::2, 0::2] = i135[1::2, 0::2]
    raw[1::2, 1::2] = i0[1::2, 1::2]
    return raw


def solve(sweep, md, ml, n_dome=N_RESIN, n_lens=N_GLASS):
    """部品ごとに候補 → 凸で解消。返り = 法線、候補の表 2 つ。"""
    out = np.zeros((H, W, 3))
    out[..., 2] = 1.0
    cands = []
    for msk, n in ((md, n_dome), (ml, n_lens)):
        c = fs.ledger.sfp_normals(sweep, n, "specular")
        d = fs.ledger.sfp_disambiguate(c, "convex", mask=msk, invalid="exclude")
        out[msk] = d[msk]
        cands.append(c)
    return out, cands


def err_deg(a, b):
    return photometric.angular_error_deg(a, b)



# --------------------------------------------------------------------------- #
# 6. 実物に見える描画で同じ解法(2026-11-08)                                     #
# --------------------------------------------------------------------------- #
#: 旧版の図は一様な環境光(明るさがほぼ一様)で、対象が写っていなかった。ここでは同じドームと
#: レンズを、検査で実際に使う**ドーム照明**(真上にカメラの穴、4 本の継ぎ目、縁ほど暗い)の
#: 下に置き、黒い樹脂のわずかな拡散(反射率 1 %)、レンズの下の黒い台から透けてくる光、
#: 偏光子の消光比 1/200、レンズのぼけ、ショット雑音(飽和 10000 電子)、読出し雑音 3 電子、
#: 12 bit、飽和を入れて撮る。解法は [2] と同じ(凸 + Brewster の稜線)。
SCALE_REAL = 4                     # [2] の場面を 4 倍の画素で(512 x 1024)
RESIN_ALBEDO = 0.01                # 黒い樹脂の拡散(カーボンブラック入り)
STAGE_RADIANCE = 0.06              # 台(暗い灰色のアルマイト)
VELVET_RADIANCE = 0.008            # レンズの下の黒いベルベット
EXTINCTION_REAL = 200.0
FULL_WELL_REAL = 10000.0
READ_E_REAL = 3.0


def cap_at(shape, cy, cx, radius, rim):
    """cap() と同じ球冠を任意の大きさの画面で。"""
    hh, ww = shape
    yy, xx = np.mgrid[0:hh, 0:ww].astype(float)
    x, y = (xx - cx) / radius, (yy - cy) / radius
    r2 = x * x + y * y
    m = r2 < (rim / radius) ** 2
    nz = np.sqrt(np.clip(1.0 - r2, 0.0, 1.0))
    n = np.stack([x, y, nz], axis=-1)
    n[~m] = (0.0, 0.0, 1.0)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    z = np.where(m, radius * (nz - math.sqrt(1.0 - (rim / radius) ** 2)), 0.0)
    return n, m, z


def dome_light(dirs, hole_el=82.0):
    """ドーム照明の輝度(無偏光)。dirs (..., 3) は面から外へ向かう単位ベクトル(+z = カメラ側)。

    内面の拡散板(縁ほど暗い、ムラ 3 %)、真上のカメラの穴(半角 8 度)、4 枚の拡散板の継ぎ目、
    縁の LED の帯。開口(仰角 4 度)より下は暗い部屋の壁、地平線より下は台。
    """
    x, y, z = dirs[..., 0], dirs[..., 1], dirs[..., 2]
    el = np.degrees(np.arcsin(np.clip(z, -1.0, 1.0)))
    az = np.degrees(np.arctan2(y, x))
    L = 0.62 + 0.38 * np.clip(z, 0.0, 1.0) ** 0.7
    L = L * (1.0 + 0.03 * np.sin(np.radians(az) * 7.0 + 0.04 * el) * np.cos(np.radians(el) * 5.0))
    seam = np.abs(((az + 45.0) % 90.0) - 45.0)
    L = L * (1.0 - 0.45 * np.exp(-(seam / 1.0) ** 2))
    L = L + 0.30 * np.exp(-((el - 8.0) / 2.5) ** 2)
    L = np.where(el > hole_el, 0.02, L)
    L = np.where(el < 4.0, 0.05, L)
    return np.where(z > 0.0, L, STAGE_RADIANCE)


def room_light(dirs):
    """検査室の輝度(無偏光): 天井の 2 列のパネル照明・明るい天井・壁・片側の窓・台。

    dirs (..., 3) は面から外へ向かう単位ベクトル(+z = カメラ側 = 天井)。黒い光沢の面は
    この部屋を映す —— 照明の映り込みが曲面で歪むのが、黒光沢が黒光沢に見える理由。
    """
    x, y, z = dirs[..., 0], dirs[..., 1], dirs[..., 2]
    zc = np.clip(z, 1e-3, 1.0)
    # 天井(高さ 1 の平面)へ投影した座標
    u, v = x / zc, y / zc
    L = 0.30 + 0.10 * np.exp(-(u * u + v * v) / 4.0)          # 天井の地
    for cu in (-0.55, 0.55):                                    # 2 列のパネル照明
        for cv in (-1.2, 0.0, 1.2):
            pu = 1.0 / (1.0 + np.exp(np.clip((np.abs(u - cu) - 0.22) / 0.015, -60.0, 60.0)))
            pv = 1.0 / (1.0 + np.exp(np.clip((np.abs(v - cv) - 0.45) / 0.015, -60.0, 60.0)))
            L = L + 2.2 * pu * pv
    el = np.degrees(np.arcsin(np.clip(z, -1.0, 1.0)))
    az = np.degrees(np.arctan2(y, x))
    wall = el < 28.0                                            # 壁(低い仰角)
    win = wall & (el > 6.0) & (el < 22.0) & (np.abs(az - 160.0) < 35.0)
    L = np.where(wall, 0.16 + 0.04 * np.cos(np.radians(az)), L)
    L = np.where(win, 1.4, L)
    return np.where(z > 0.0, L, STAGE_RADIANCE)               # 地平線より下 = 台


def render_real(seed=11, light="dome", hole_el=82.0):
    """[2] のドームとレンズを、ドーム照明の下で偏光カメラが撮った生モザイクとして描く。"""
    k = SCALE_REAL
    shape = (H * k, W * k)
    nd_, md, zd = cap_at(shape, 64.0 * k, 66.0 * k, 56.0 * k, 53.0 * k)
    nl, ml, zl = cap_at(shape, 64.0 * k, 190.0 * k, 100.0 * k, 44.0 * k)
    nrm = np.where(md[..., None], nd_, nl)
    both = md | ml
    view = np.array([0.0, 0.0, 1.0])
    cos_i = np.clip(nrm[..., 2], 1e-6, 1.0)
    R = 2.0 * cos_i[..., None] * nrm - view                   # 鏡像方向
    env = dome_light(R, hole_el) if light == "dome" else room_light(R)
    spec = np.zeros(shape)
    for msk, n in ((md, N_RESIN), (ml, N_GLASS)):
        spec[msk] = (glassmirror.fresnel_dielectric(cos_i[msk], 1.0, n) * env[msk])
    irr = 0.75                                                 # ドーム照明の照度(拡散に効く平均)
    diff = np.where(md, RESIN_ALBEDO * irr, 0.0) + np.where(ml, VELVET_RADIANCE, 0.0)
    expo = 0.80 / float(np.percentile(spec[both] + diff[both], 99.0))
    sweep = np.zeros((4,) + shape)
    for msk, n in ((md, N_RESIN), (ml, N_GLASS)):
        sweep += fs.ledger.sfp_render(nrm, n, specular_radiance=expo * spec * msk + 1e-12 * msk,
                                      diffuse_radiance=expo * diff * msk, mask=msk)
    # ドームの台座 = 同じ黒光沢樹脂の板(角を丸めた四角、縁は 30 度の面取り)。平らな所は真上の
    # カメラの穴を映して黒く、面取りはドーム照明を映して明るい縁になる(テレセン + ドームの見え方)
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(float)
    bx0, bx1, by0, by1, rc = 6.0 * k, 126.0 * k, 6.0 * k, 122.0 * k, 12.0 * k
    qx = np.abs(xx - 0.5 * (bx0 + bx1)) - (0.5 * (bx1 - bx0) - rc)
    qy = np.abs(yy - 0.5 * (by0 + by1)) - (0.5 * (by1 - by0) - rc)
    inside_r = -(np.hypot(np.maximum(qx, 0.0), np.maximum(qy, 0.0))
                 + np.minimum(np.maximum(qx, qy), 0.0) - rc)     # 角を丸めた四角の縁までの距離(内側が正)
    plate = (inside_r > 0) & ~md
    bevel = plate & (inside_r < 3.0 * k)
    gy_, gx_ = np.gradient(inside_r)
    gn = np.hypot(gx_, gy_) + 1e-12
    tilt = math.tan(math.radians(30.0))
    pn = np.stack([np.where(bevel, -gx_ / gn * tilt, 0.0), np.where(bevel, -gy_ / gn * tilt, 0.0),
                   np.ones(shape)], axis=-1)
    pn /= np.linalg.norm(pn, axis=-1, keepdims=True)
    pc = np.clip(pn[..., 2], 1e-6, 1.0)
    pR = 2.0 * pc[..., None] * pn - view
    penv = dome_light(pR, hole_el) if light == "dome" else room_light(pR)
    pspec = glassmirror.fresnel_dielectric(pc, 1.0, N_RESIN) * penv
    sweep += fs.ledger.sfp_render(pn, N_RESIN, specular_radiance=expo * pspec * plate + 1e-12 * plate,
                                  diffuse_radiance=expo * RESIN_ALBEDO * irr * plate, mask=plate)
    # 背景(偏光しない): 板の外は暗い灰色の台、レンズの下は黒いベルベット(布目の粗さ)
    velvet = (xx > 128 * k) & (np.hypot(yy - 64.0 * k, xx - 190.0 * k) < 60.0 * k)
    tex = ndimage.gaussian_filter(rng.standard_normal(shape), 1.0)
    back = np.where(velvet, VELVET_RADIANCE * (1.0 + 0.4 * tex), STAGE_RADIANCE * 0.25 * (1.0 + 0.06 * tex))
    back = back * ~(both | plate)
    # ほこり: 拡散で光る小さな粒(偏光しない)。実物の表面には必ず乗る
    dust = np.zeros(shape)
    for _ in range(14):
        cy_, cx_ = rng.uniform(0, shape[0]), rng.uniform(0, shape[1])
        rr_ = rng.uniform(0.8, 2.0) * k / 2.0
        dust += 0.35 * np.exp(-((yy - cy_) ** 2 + (xx - cx_) ** 2) / (2 * rr_ ** 2))
    sweep += 0.5 * expo * (back + dust * irr * 0.2)[None]
    sweep = np.stack([ndimage.gaussian_filter(a, 0.6) for a in sweep])
    leak = 1.0 / EXTINCTION_REAL
    sweep = (sweep + leak * sweep[[2, 3, 0, 1]]) / (1.0 + leak)
    e = rng.poisson(np.clip(sweep, 0.0, None) * FULL_WELL_REAL).astype(float)
    e += rng.normal(0.0, READ_E_REAL, e.shape)
    lv = 4095.0
    sweep_meas = np.round(np.clip(e / FULL_WELL_REAL, 0.0, 1.0) * lv) / lv
    i0, i45, i90, i135 = sweep_meas
    raw = np.zeros(shape)
    raw[0::2, 0::2] = i90[0::2, 0::2]
    raw[0::2, 1::2] = i45[0::2, 1::2]
    raw[1::2, 0::2] = i135[1::2, 0::2]
    raw[1::2, 1::2] = i0[1::2, 1::2]
    return {"nrm": nrm, "md": md, "ml": ml, "z": zd + zl, "raw": raw, "expo": expo,
            "spec": expo * spec, "diff": expo * diff, "sat": float((sweep_meas >= 1.0).any(axis=0)[both].mean())}


def solve_real(sweep, md, ml):
    out = np.zeros(sweep.shape[1:] + (3,))
    out[..., 2] = 1.0
    for msk, n in ((md, N_RESIN), (ml, N_GLASS)):
        c = fs.ledger.sfp_normals(sweep, n, "specular")
        d = fs.ledger.sfp_disambiguate(c, "convex", mask=msk, invalid="exclude")
        out[msk] = d[msk]
    return out


def _hidden_line_view(z, mask, step, width, height, z_gain):
    """高さ場の隠れ線表示(粗さ計・三次元測定機の画面の描き方)。奥の行から手前へ、行ごとに
    下を背景で塗りつぶしてから線を引く。mask は 2 = 白い線、1 = 灰の線、0 = 線を引かない
    (塗りつぶしはする = 測れない所は空白に見える)。返り値は (height, width, 3) の uint8。"""
    from PIL import Image, ImageDraw
    hh, ww = z.shape
    im = Image.new("RGB", (width, height), (18, 20, 24))
    d = ImageDraw.Draw(im)
    sx = (width - 40) / ww
    sy = 0.42 * sx
    base = 30 + hh * sy
    for row in range(0, hh, step):
        xs = 20 + np.arange(ww) * sx
        ys = base - (hh - 1 - row) * sy * 0.0 + row * sy - z[row] * z_gain * sx - hh * sy + 40
        pts = list(zip(xs.tolist(), ys.tolist()))
        poly = pts + [(xs[-1], height), (xs[0], height)]
        d.polygon(poly, fill=(18, 20, 24))
        on = mask[row]
        cols = {2: (235, 235, 235), 1: (95, 100, 108)}           # 2 = 測れた所、1 = 台の面、0 = 描かない
        for i in range(ww - 1):
            c = min(int(on[i]), int(on[i + 1]))
            if c:
                d.line((pts[i], pts[i + 1]), fill=cols[c], width=1)
    return np.asarray(im)


def real_chapter():
    """[6] 実物に見える描画で、[2] と同じ解法を回す。数と図の材料を返す。"""
    k = SCALE_REAL
    r = render_real(light="dome")
    md, ml = r["md"], r["ml"]
    both = md | ml
    sweep = np.clip(fs.ledger.polarization_demosaic(r["raw"]), 0.0, None) * both
    n_est = solve_real(sweep, md, ml)
    err = err_deg(n_est, r["nrm"])
    s0 = sweep.sum(axis=0) / 2.0
    # 測れる画素を、撮った像だけから決める: 照明の映らない所(真上のカメラの穴・台)は暗い
    valid = both & (s0 > 0.3 * float(np.median(s0[both])))
    valid = ndimage.binary_opening(valid, iterations=2)
    th = np.degrees(np.arccos(np.clip(r["nrm"][..., 2], -1.0, 1.0)))
    h = np.zeros(md.shape)
    rms, top = {}, {}
    integrated = np.zeros(md.shape, bool)       # 高さを積分した(= 測れた)画素
    for name, msk in (("dome", md), ("lens", ml)):
        v = msk & valid
        lab, nl = ndimage.label(v)
        big = lab == (1 + int(np.argmax(ndimage.sum(v, lab, range(1, nl + 1)))))
        hh = fs.ledger.sfp_height(n_est, mask=big) * big
        off = float(np.mean((r["z"] - hh)[big]))              # 高さの原点は 1 枚では決まらない(定数を合わせる)
        h += np.where(big, hh + off, 0.0)
        integrated |= big
        rms[name] = float(np.sqrt(np.mean((hh + off - r["z"])[big] ** 2)))
        top[name] = (float((hh + off)[big].max()), float(r["z"][big].max()))
    inner = {name: ndimage.binary_erosion(msk & valid, iterations=3 * k) for name, msk in (("dome", md), ("lens", ml))}
    med = {name: float(np.median(err[m_])) for name, m_ in inner.items()}
    # 有効画素の決め方が照明の穴に追従するかの確かめ(式は描画と同じ鏡像の式 —— 実装の検算で、形の測り方の
    # 正しさの外からの確かめではない): カメラの穴の半角を 8° → 15° に広げて撮り直し、像だけで決めた
    # 「頂点の測れない範囲」の縁の天頂角が、正射影の鏡像の式 θ = (90° − 穴の仰角)/2 どおり動くか
    apex = {82.0: apex_edge_deg(r, 82.0)}
    apex[75.0] = apex_edge_deg(render_real(light="dome", hole_el=75.0), 75.0)
    # 同じ部品を部屋の照明(天井のパネル)で撮ると
    rr = render_real(light="room")
    sw2 = np.clip(fs.ledger.polarization_demosaic(rr["raw"]), 0.0, None) * both
    n2 = solve_real(sw2, md, ml)
    in_dome = ndimage.binary_erosion(md, iterations=3 * k)
    room_med = float(np.median(err_deg(n2, rr["nrm"])[in_dome]))
    dome_all = float(np.median(err[in_dome]))
    in_lens = ndimage.binary_erosion(ml, iterations=3 * k)
    lens_all = float(np.median(err[in_lens]))
    # 表示用の高さ: 測れない所のうち、測れた所に囲まれた穴(ドームの頂点 = カメラの穴を映す所)は
    # ラプラス方程式で埋める(線を暗く描く)。外側の急な斜面は 0 のまま(描かない)
    h_show = h.copy()
    shown = np.zeros(md.shape, bool)
    for msk in (md, ml):
        v = msk & integrated
        shown |= v
        holes = ndimage.binary_fill_holes(v) & ~v
        lab, nl = ndimage.label(holes)
        for i in range(1, nl + 1):
            hole = lab == i
            if hole.sum() > 0.05 * msk.sum():                  # 小さい穴(頂点)だけ埋める
                continue
            _, (iy, ix) = ndimage.distance_transform_edt(~v, return_indices=True)
            h_show = np.where(hole, h[iy, ix], h_show)          # いちばん近い測れた画素の高さ
            shown |= hole
    s0_show = np.clip(fs.ledger.polarization_demosaic(r["raw"]), 0.0, None).sum(axis=0) / 2.0
    return {"r": r, "s0": s0, "s0_show": s0_show, "h_show": h_show, "shown": shown, "valid": valid, "h": h, "err": err,
            "med": med, "rms": rms, "top": top,
            "valid_frac": float((md & valid).sum() / md.sum()), "valid_frac_lens": float((ml & valid).sum() / ml.sum()),
            "apex": apex, "integrated": integrated, "room_med": room_med, "dome_all": dome_all, "lens_all": lens_all,
            "both": both}


def _oblique_hits(z, tilt_deg=42.0, out_w=None, step=0.7):
    """高さ場 z を、真上から tilt_deg 傾けた正射影のカメラ(奥 = −y の方へ見下ろす)で見たときの、
    画面の各画素が当たる (x, y) と見えている向き V(面からカメラへ)を返す。行進は高さ場の光線追跡。"""
    hh, ww = z.shape
    t = math.radians(tilt_deg)
    out_w = out_w or ww
    sc = ww / out_w
    zmax = float(z.max()) + 1.0
    rows = int(math.ceil((hh * math.cos(t) + zmax * math.sin(t)) / sc))
    d = np.array([0.0, -math.sin(t), -math.cos(t)])      # 光線の向き(−y へ、下へ)
    V = -d
    ey = np.array([0.0, math.cos(t), -math.sin(t)])       # 画面の下向き(手前 = +y)
    u = (np.arange(out_w) + 0.5) * sc
    v = (np.arange(rows) + 0.5) * sc - zmax * math.sin(t)
    uu, vv = np.meshgrid(u, v)
    # 光線: p = (u, 0, 0) + v*ey + s*d、z が zmax の所から台(z = 0)まで行進
    oy, oz = vv * ey[1], vv * ey[2]
    s0 = (oz - zmax) / math.cos(t)
    s1 = oz / math.cos(t)
    hit = np.full(uu.shape, np.nan)
    prev_s, prev_f = s0.copy(), np.ones(uu.shape)
    n_steps = int(math.ceil(float((s1 - s0).max()) / step)) + 2
    for k in range(1, n_steps + 1):
        sk = np.minimum(s0 + k * step, s1)
        py = oy + sk * d[1]
        pz = oz + sk * d[2]
        inside = (py >= 0) & (py <= hh - 1)
        zz = np.where(inside, ndimage.map_coordinates(z, [np.clip(py, 0, hh - 1), uu], order=1), 0.0)
        f = pz - zz
        new = np.isnan(hit) & (f <= 0.0)
        if new.any():
            a = prev_f[new] / np.maximum(prev_f[new] - f[new], 1e-12)
            hit[new] = prev_s[new] + a * (sk[new] - prev_s[new])
        prev_s, prev_f = sk, f
        if not np.isnan(hit).any():
            break
    hit = np.where(np.isnan(hit), s1, hit)
    py = oy + hit * d[1]
    ok = (py >= 0) & (py <= hh - 1)
    return uu, np.clip(py, 0, hh - 1), ok, V


def _sample(a, x, y, order=1):
    return ndimage.map_coordinates(np.asarray(a, dtype=np.float64), [y, x], order=order)


def _normals_from_height(z):
    gy, gx = np.gradient(z)
    n = np.stack([-gx, -gy, np.ones_like(z)], axis=-1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def oblique_photo(rc):
    """見た目の図: 同じドームとレンズを、天井のパネル照明の部屋で斜めから撮った像(黒光沢の映り込み)。

    黒い樹脂(n 1.57、拡散 1 %)の台座(厚さ 6 画素 x 縮尺)の上にドーム、黒いベルベットの上にガラスのレンズ。
    台は暗い灰のアルマイト。表示の白は部品に映る照明の明るい所(露出をそこに合わせる)、階調は線形(ガンマ 1)。
    鏡面は Fresnel(glassmirror)x 部屋の輝度、レンズは下の黒いベルベットが透ける分を足す。
    """
    k = SCALE_REAL
    r = rc["r"]
    md, ml = r["md"], r["ml"]
    hh, ww = md.shape
    yy, xx = np.mgrid[0:hh, 0:ww].astype(float)
    bx0, bx1, by0, by1, rcn = 6.0 * k, 126.0 * k, 6.0 * k, 122.0 * k, 12.0 * k
    qx = np.abs(xx - 0.5 * (bx0 + bx1)) - (0.5 * (bx1 - bx0) - rcn)
    qy = np.abs(yy - 0.5 * (by0 + by1)) - (0.5 * (by1 - by0) - rcn)
    inside = -(np.hypot(np.maximum(qx, 0.0), np.maximum(qy, 0.0)) + np.minimum(np.maximum(qx, qy), 0.0) - rcn)
    plate_h = 6.0 * k
    plate = np.clip(inside / (2.0 * k), 0.0, 1.0) * plate_h            # 縁は面取り(2 画素 x 縮尺)
    z = ndimage.gaussian_filter(np.where(md, r["z"] + plate_h, plate) + np.where(ml, r["z"], 0.0), 0.8)
    x, y, ok, V = _oblique_hits(z, out_w=ww // 2)
    nrm = _normals_from_height(z)
    n_img = np.stack([_sample(nrm[..., i], x, y) for i in range(3)], axis=-1)
    n_img /= np.linalg.norm(n_img, axis=-1, keepdims=True)
    cos_i = np.clip(n_img @ V, 1e-4, 1.0)
    R = 2.0 * cos_i[..., None] * n_img - V
    env = room_light(R)
    mat_d = _sample(md.astype(float), x, y) > 0.5
    mat_l = _sample(ml.astype(float), x, y) > 0.5
    mat_p = (_sample(plate, x, y) > 0.5 * plate_h) & ~mat_d
    f_res = glassmirror.fresnel_dielectric(cos_i, 1.0, N_RESIN)
    f_gl = glassmirror.fresnel_dielectric(cos_i, 1.0, N_GLASS)
    irr = 0.35 + 0.4 * np.clip(n_img[..., 2], 0.0, 1.0)
    img = np.full(x.shape, STAGE_RADIANCE) * irr                        # 暗い灰のアルマイトの台(拡散)
    glossy = mat_d | mat_p
    img = np.where(glossy, f_res * env + RESIN_ALBEDO * irr, img)
    img = np.where(mat_l, f_gl * env + (1.0 - f_gl) ** 2 * VELVET_RADIANCE, img)
    velvet = (_sample(((xx > 128 * k) & (np.hypot(yy - 64.0 * k, xx - 190.0 * k) < 60.0 * k)).astype(float), x, y) > 0.5)
    img = np.where(velvet & ~mat_l, VELVET_RADIANCE * irr, img)
    img = np.where(ok, img, 0.02)
    # 白 = 部品に映る照明の明るい所(黒光沢は照明の映り込みだけが白く、樹脂そのものと台は暗い)。
    # 表示は産業用カメラの既定の線形(ガンマ 1)—— ガンマ 2.2 だと暗い樹脂と台が中間の灰に持ち上がる
    white = float(np.percentile(img[(glossy | mat_l) & ok], 99.5))
    keep = np.nonzero(ok.any(axis=1))[0]
    return np.rint(np.clip(img[keep[0]:] / white, 0.0, 1.0) * 255).astype(np.uint8)


def oblique_result(rc):
    """復元した形の図: 1 枚から積分した高さを斜めから陰影つきで描き、法線の誤差を色で重ねる。

    色は誤差 0°(青)〜 10°(赤)、明るさは Lambert の陰影。測れない所(照明を映さない)は灰の縞。
    台(z = 0)は暗い灰。高さの原点は 1 枚では決まらないので、測れた所の平均を真値に合わせてある。
    """
    r = rc["r"]
    md, ml = r["md"], r["ml"]
    shown = rc["shown"]
    z = ndimage.gaussian_filter(np.where(shown, rc["h_show"], 0.0), 0.8)
    x, y, ok, V = _oblique_hits(z, out_w=md.shape[1] // 2)
    nrm = _normals_from_height(z)
    n_img = np.stack([_sample(nrm[..., i], x, y) for i in range(3)], axis=-1)
    n_img /= np.linalg.norm(n_img, axis=-1, keepdims=True)
    L = np.array([-0.4, 0.5, 0.77])
    L /= np.linalg.norm(L)
    lam = 0.25 + 0.75 * np.clip(n_img @ L, 0.0, 1.0)
    e = _sample(np.where(shown, np.nan_to_num(rc["err"], nan=90.0), 0.0), x, y, order=0)
    on = _sample(rc["integrated"].astype(float), x, y, order=0) > 0.5     # 縞 = 測れない(頂点の穴を埋めた所も)
    on &= n_img[..., 2] > 0.3                    # 測れた所の縁から台へ落ちる壁は描画の継ぎ目(測った面ではない)
    part = _sample((md | ml).astype(float), x, y, order=0) > 0.5
    t = np.clip(e / 10.0, 0.0, 1.0)[..., None]
    col = (1 - t) * np.array([70.0, 140.0, 255.0]) + t * np.array([255.0, 70.0, 50.0])
    rgb = np.where(on[..., None], col * lam[..., None], 0.0)
    stripes = ((np.add.outer(np.arange(x.shape[0]), np.arange(x.shape[1])) // 4) % 2).astype(float)
    rgb = np.where((part & ~on)[..., None], (70 + 40 * stripes)[..., None] * np.ones(3), rgb)
    rgb = np.where((~part & ~on)[..., None], 55.0 * lam[..., None] * np.ones(3), rgb)
    rgb = np.where(ok[..., None], rgb, 20.0)
    keep = np.nonzero(ok.any(axis=1))[0]
    return np.rint(np.clip(rgb[keep[0]:], 0, 255)).astype(np.uint8)


def apex_edge_deg(r, hole_el):
    """カメラの穴を映して測れない頂点の範囲の縁の天頂角(像だけで決めた有効画素から)。"""
    md = r["md"]
    sweep = np.clip(fs.ledger.polarization_demosaic(r["raw"]), 0.0, None) * (md | r["ml"])
    s0 = sweep.sum(axis=0) / 2.0
    valid = (md | r["ml"]) & (s0 > 0.3 * float(np.median(s0[md | r["ml"]])))
    th = np.degrees(np.arccos(np.clip(r["nrm"][..., 2], -1.0, 1.0)))
    lab, _ = ndimage.label(md & ~valid)
    cy, cx = np.unravel_index(np.argmin(np.where(md, th, 99.0)), th.shape)
    apex = lab == lab[cy, cx]
    edge = apex & ~ndimage.binary_erosion(apex)
    return float(np.median(th[edge])), (90.0 - hole_el) / 2.0


def _fig_real(rc):
    """代表の図: 見た目(部屋の照明・斜め)/ 測るときの 1 枚(ドーム照明・真上)/ 1 枚から復元した形(斜め・誤差の色)。"""
    from PIL import Image, ImageDraw
    import annotate as AN
    r, valid = rc["r"], rc["valid"]
    white = float(np.percentile(rc["s0_show"][rc["both"]], 99.5))
    s0_img = np.rint(np.clip(rc["s0_show"] / white, 0.0, 1.0) ** (1 / 2.2) * 255).astype(np.uint8)
    hh, ww = s0_img.shape
    photo = oblique_photo(rc)
    result = oblique_result(rc)
    ph = min(photo.shape[0], result.shape[0])
    photo, result = photo[-ph:], result[-ph:]
    pw = photo.shape[1]
    # 生のモザイク: ドームの斜面の 40 x 40 画素を 4 倍(最近傍)、真上の像の右下に差し込む
    cy, cx = 44 * SCALE_REAL, 90 * SCALE_REAL
    c_ = r["raw"][cy:cy + 40, cx:cx + 40]
    zoom = np.kron(np.rint(np.clip((c_ - c_.min()) / max(float(np.ptp(c_)), 1e-12), 0, 1) * 255).astype(np.uint8),
                   np.ones((4, 4), np.uint8))
    gap, head, cap_h, foot = 12, 50, 34, 118
    W_ = max(ww, 2 * pw + gap)
    H_ = head + ph + cap_h + hh + foot + cap_h
    im = Image.new("RGB", (W_, H_), (24, 26, 30))
    d = ImageDraw.Draw(im)

    def text(s, xy, size=22, fill=(240, 240, 240)):
        m_ = AN.measure_text(s, font_size=size, min_font_size=size, wrap=False)
        if xy[0] + m_["width"] > W_ - 4 or xy[1] + m_["height"] > H_:
            raise ValueError("図の文字がはみ出す: %r" % s)
        for i, line in enumerate(m_["lines"]):
            d.text((xy[0], xy[1] + i * m_["line_height"]), line, font=m_["font"], fill=fill)
    text("照度差ステレオが効かない黒光沢樹脂とガラスを、偏光カメラ 1 枚で測る", (12, 10), size=24)
    y = head
    text("見た目(天井のパネル照明、斜めから)", (8, y), size=19, fill=(235, 235, 235))
    text("復元した形(色 = 法線の誤差 0〜10°、縞 = 測れない)", (pw + gap + 8, y), size=19, fill=(140, 220, 255))
    y += cap_h
    im.paste(Image.fromarray(np.repeat(photo[..., None], 3, 2)), (0, y))
    im.paste(Image.fromarray(result), (pw + gap, y))
    y += ph + 6
    text("測るときの 1 枚(ドーム照明、真上から、偏光カメラの明るさ S0): 黒光沢は一様に明るく、陰影が無い", (8, y), size=19)
    y += cap_h - 6
    im.paste(Image.fromarray(np.repeat(s0_img[..., None], 3, 2)), (0, y))
    zy, zx = y + hh - zoom.shape[0] - 6, ww - zoom.shape[1] - 6
    im.paste(Image.fromarray(np.repeat(zoom[..., None], 3, 2)), (zx, zy))
    d.rectangle((zx - 1, zy - 1, zx + zoom.shape[1], zy + zoom.shape[0]), outline=(255, 200, 80), width=2)
    d.rectangle((cx, y + cy, cx + 40, y + cy + 40), outline=(255, 200, 80), width=2)
    text("生モザイク x4", (zx + 4, zy - 26), size=17, fill=(255, 200, 80))
    fy = y + hh + 8
    text("法線の誤差の中央値 測れた所: ドーム %.1f° / レンズ %.1f°、全体: %.1f° / %.1f°(測れた割合 %.0f %% / %.0f %%)"
         % (rc["med"]["dome"], rc["med"]["lens"], rc["dome_all"], rc["lens_all"], 100 * rc["valid_frac"],
            100 * rc["valid_frac_lens"]), (8, fy), size=17, fill=(140, 220, 255))
    text("高さの RMS 誤差 %.1f px(高さ %.0f px)。カメラの穴と台を映す所は暗く、像だけで除く。" % (rc["rms"]["dome"], rc["top"]["dome"][1]),
         (8, fy + 26), size=17, fill=(210, 210, 210))
    text("天井のパネル照明で測ると誤差の中央値 %.1f°(ドーム照明 %.1f°)。拡散 1 %%・消光比 1/200・ショット雑音入り。"
         % (rc["room_med"], rc["dome_all"]), (8, fy + 52), size=17, fill=(210, 210, 210))
    text("★部品の位置(mask)と高さの原点(測れた所の平均)は描画の真値から与えた —— 偏光から出したのは法線と形だけ。",
         (8, fy + 78), size=17, fill=(255, 200, 80))
    figs.save("real_dome_and_lens", np.asarray(im),
              caption="黒光沢樹脂のドーム(n %.2f)とガラスのレンズ(n %.2f)。上段左は天井のパネル照明の部屋で斜めから見た姿、"
                      "下段は測るときのドーム照明で真上から撮った 1 枚(黒光沢が一様に明るく、陰影が無い)。上段右はその 1 枚の偏光から"
                      "復元した形で、色は法線の誤差。誤差の中央値は測れた所でドーム %.1f° / レンズ %.1f°、部品全体ではドーム %.1f° / "
                      "レンズ %.1f°(測れた割合 %.0f %% / %.0f %%)。真上のカメラの穴と台を映す所は暗く、像だけから測れないと分かる。"
                      "部品の位置(mask)と高さの原点は描画の真値から与えた(偏光から出したのは法線と形だけ)。"
                      % (N_RESIN, N_GLASS, rc["med"]["dome"], rc["med"]["lens"], rc["dome_all"], rc["lens_all"],
                         100 * rc["valid_frac"], 100 * rc["valid_frac_lens"]))


def main():
    t0 = time.time()
    c0 = time.process_time()
    print("=" * 76)
    print("PoC: 黒光沢とガラスの形を偏光で測る(偏光からの形状復元)")
    print("=" * 76)
    nrm, md, ml, z_true, index = scene()
    both = md | ml
    inner = ndimage.binary_erosion(md, iterations=3) | ndimage.binary_erosion(ml, iterations=3)
    th_true = np.degrees(np.arccos(nrm[..., 2]))
    print("ドーム: 黒光沢樹脂 n = %.2f、縁の天頂角 %.0f°(Brewster %.1f°)/ レンズ: ガラス n = %.2f、縁 %.0f°"
          % (N_RESIN, th_true[md].max(), math.degrees(math.atan(N_RESIN)), N_GLASS, th_true[ml].max()))

    # ---- 1. 物理の要点 ------------------------------------------------------- #
    print("\n[1] Fresnel の偏光度(閉形式 = glassmirror の s/p 反射率から作った値)")
    th = np.linspace(0.0, 89.0, 891)
    c = np.cos(np.radians(th))
    rs = glassmirror.fresnel_dielectric(c, 1.0, N_RESIN, "s")
    rp = glassmirror.fresnel_dielectric(c, 1.0, N_RESIN, "p")
    dmax = float(np.abs(fs.ledger.sfp_dolp_model(th, N_RESIN, "specular") - (rs - rp) / (rs + rp)).max())
    tb = math.degrees(math.atan(N_RESIN))
    top = float(fs.ledger.sfp_dolp_model(tb, N_RESIN, "specular"))
    check(dmax < 1e-12 and abs(top - 1.0) < 1e-15,
          "鏡面の DoLP は Brewster 角 atan n で厳密に 1、別の Fresnel と一致",
          "DoLP(%.2f°) = %.17g、最大差 %.1e" % (tb, top, dmax))
    z2 = fs.ledger.dolp_to_zenith(np.array([0.8]), N_RESIN, "specular")["zenith_deg"][:, 0]
    back = fs.ledger.sfp_dolp_model(z2, N_RESIN, "specular")
    az = fs.ledger.aolp_to_azimuth(np.array([30.0]), "specular")["azimuth_deg"][:, 0]
    azd = fs.ledger.aolp_to_azimuth(np.array([30.0]), "diffuse")["azimuth_deg"][:, 0]
    check(z2[0] < tb < z2[1] and np.abs(back - 0.8).max() < 1e-12
          and abs(az[0] - azd[0] - 90.0) < 1e-12 and abs(az[1] - az[0] - 180.0) < 1e-12,
          "DoLP 0.8 の天頂角は Brewster を挟んで 2 つ、AoLP 30° の方位は 2 つ(π)で拡散と 90° ずれる",
          "θ = %.2f° / %.2f°、鏡面の方位 %.0f° / %.0f°(拡散 %.0f° / %.0f°)"
          % (z2[0], z2[1], az[0], az[1], azd[0], azd[1]))

    # ---- 2. 1 ショット → 候補 → 解消 → 高さ ----------------------------------- #
    print("\n[2] 生のモザイク 1 枚から法線と高さ")
    sweep_ideal = render_sweep(nrm, md, ml, index)
    raw = to_mosaic(sweep_ideal)
    sweep = np.clip(fs.ledger.polarization_demosaic(raw), 0.0, None) * both
    n_ideal, _ = solve(sweep_ideal, md, ml)
    n_sfp, cands = solve(sweep, md, ml)
    e_ideal = err_deg(n_ideal, nrm)
    e_sfp = err_deg(n_sfp, nrm)
    for name, msk in (("ドーム", md & inner), ("レンズ", ml & inner)):
        print("  %s: 法線の誤差 中央値 %.2f° / 平均 %.2f° / 95%% 点 %.2f°(4 枚を直接: 中央値 %.2f°)"
              % (name, np.median(e_sfp[msk]), e_sfp[msk].mean(), np.percentile(e_sfp[msk], 95),
                 np.median(e_ideal[msk])))
    check(np.median(e_sfp[md & inner]) < 2.0 and np.median(e_sfp[ml & inner]) < 3.0,
          "モザイク → 4 枚 → 法線(縁の 3 画素を除く)",
          "中央値 ドーム %.2f° / レンズ %.2f°" % (np.median(e_sfp[md & inner]), np.median(e_sfp[ml & inner])))
    clean = fs.ledger.sfp_normals(render_sweep(nrm, md, ml, index, noise=0.0), N_RESIN, "specular")
    nd0 = clean["n_distinct"]
    gap = np.abs(clean["zenith_deg"][1] - clean["zenith_deg"][0])
    jmin = np.unravel_index(np.argmin(np.where(md, gap, np.inf)), gap.shape)
    check((nd0[md] == 4).all() and abs(th_true[jmin] - tb) < 1.0,
          "解消する前は全画素に 4 本。2 つの天頂角の差は Brewster 角の上で 0 に縮む(雑音なし)",
          "4 本 %d / %d 画素、差の最小 %.3f° は天頂角 %.2f° の画素(Brewster %.2f°)"
          % (int((nd0[md] == 4).sum()), int(md.sum()), gap[jmin], th_true[jmin], tb))
    nd = cands[0]["n_distinct"]
    print("  雑音ありでは DoLP が 1 に張り付く画素(候補 2 本)が %d、無効(DoLP > 1.05)が %d 画素。"
          "モザイク経由の方が良いのはデモザイクの補間が近傍を平均する = 雑音を均すから"
          % (int((md & (nd == 2)).sum()), int((md & (nd == 0)).sum())))
    h = np.zeros((H, W))
    for msk in (md, ml):
        h += fs.ledger.sfp_height(n_sfp, mask=msk) * msk
    for name, msk in (("ドーム", md), ("レンズ", ml)):
        rms = float(np.sqrt(np.mean((h - z_true)[msk] ** 2)))
        print("  %s: 高さ 最大 %.1f px(真値 %.1f px)、RMS 誤差 %.2f px"
              % (name, h[msk].max(), z_true[msk].max(), rms))
    rms_d = float(np.sqrt(np.mean((h - z_true)[md] ** 2)))
    check(rms_d < 0.05 * z_true[md].max(), "ドームの高さ(RMS 誤差 / 高さ < 5 %)",
          "%.2f px / %.1f px" % (rms_d, z_true[md].max()))

    # ---- 3. 照度差ステレオは同じ部品で崩れる ------------------------------------ #
    print("\n[3] 同じ部品を照度差ステレオで(4 方向の照明、光沢 + 弱い拡散)")
    el = math.radians(45.0)
    lights = np.array([[math.cos(el) * math.cos(a), math.cos(el) * math.sin(a), math.sin(el)]
                       for a in np.radians([0.0, 90.0, 180.0, 270.0])])
    stack = []
    for L in lights:
        spec = fs.ledger.brdf_blinn_phong(nrm, light=tuple(L), view=(0.0, 0.0, 1.0), shininess=60.0)
        lam = 0.02 * np.clip(nrm @ L, 0.0, None)
        stack.append((spec + lam) * both)
    stack = np.stack(stack)
    n_ps = np.asarray(fs.ledger.photometric_stereo_robust(stack, lights, method="ransac"), float)
    e_ps = err_deg(n_ps, nrm)
    lost = ~np.isfinite(e_ps) & md & inner
    print("  照度差ステレオが法線を返せなかった画素(光沢の点が 3 灯に満たない): %d / %d"
          % (int(lost.sum()), int((md & inner).sum())))
    e_ps = np.where(np.isfinite(e_ps), e_ps, 90.0)            # 返せなかった画素は 90° の失敗として数える
    ratio = np.median(e_ps[md & inner]) / max(np.median(e_sfp[md & inner]), 1e-9)
    check(ratio > 5.0, "照度差ステレオの誤差は偏光の何倍か(ドーム、中央値)",
          "照度差 %.1f° vs 偏光 %.2f° → %.0f 倍" % (np.median(e_ps[md & inner]), np.median(e_sfp[md & inner]), ratio))

    # ---- 4. 屈折率は較正球で ------------------------------------------------- #
    print("\n[4] 屈折率を較正球(同じ樹脂の球)で測る")
    ball_n, ball_m, _ = cap(64.0, 128.0, 56.0, 55.0)
    ball_th = np.degrees(np.arccos(ball_n[..., 2]))               # シルエットから分かる天頂角
    ball = render_sweep(ball_n, ball_m, np.zeros_like(ball_m), np.full((H, W), N_RESIN), seed=7)
    cb = fs.ledger.sfp_normals(ball, 1.5, "specular")              # 仮の n で読んでも DoLP は同じ
    est = fs.ledger.sfp_estimate_index(cb["dolp"], ball_th, "specular", mask=ball_m)
    check(abs(est["refractive_index"] - N_RESIN) < 0.01, "DoLP の Fresnel 曲線の当てはめ",
          "n = %.4f(真値 %.2f)。DoLP 最大の位置からの近道 tan θ = %.3f は雑音の山を拾う"
          % (est["refractive_index"], N_RESIN, est["brewster_index"]))

    # ---- 5. どこで壊れるか ---------------------------------------------------- #
    print("\n[5] どこで壊れるか")
    # (a) 屈折率の誤り
    ns = [1.40, 1.45, 1.50, 1.57, 1.65, 1.75]
    e_n = []
    quiet = render_sweep(nrm, md, ml, index, noise=0.0)          # 屈折率の効果だけを見るため雑音なし
    for nn in ns:
        nw_, _ = solve(quiet, md, ml, n_dome=nn)
        e_n.append(float(np.median(err_deg(nw_, nrm)[md & inner])))
    n_wrong, _ = solve(quiet, md, ml, n_dome=1.50)
    e_wrong = err_deg(n_wrong, nrm)
    i57 = ns.index(1.57)
    check(e_n[i57] < 0.01 and min(e_n[:i57] + e_n[i57 + 1:]) > 0.3
          and all(a > b for a, b in zip(e_n[:i57], e_n[1:i57 + 1]))
          and all(a < b for a, b in zip(e_n[i57:], e_n[i57 + 1:])),
          "(a) 屈折率を間違えると誤差が滑らかに増える(ドーム、中央値、雑音なし)",
          " / ".join("n=%.2f: %.2f°" % (a, b) for a, b in zip(ns, e_n)))
    # (b) 雑音は Brewster の稜線と頂上に集まる
    bins = np.arange(0.0, 75.0, 5.0)
    acc = np.zeros((H, W))
    for s in range(4):
        n_s, _ = solve(render_sweep(nrm, md, ml, index, seed=100 + s), md, ml)
        acc += err_deg(n_s, nrm) / 4.0
    prof = [float(np.median(acc[md & inner & (th_true >= b) & (th_true < b + 5.0)]))
            if (md & inner & (th_true >= b) & (th_true < b + 5.0)).any() else float("nan") for b in bins]
    near_b = float(np.median(acc[md & inner & (np.abs(th_true - tb) < 2.5)]))
    calm = float(np.median(acc[md & inner & (th_true > 25.0) & (th_true < 45.0)]))
    apex = float(np.median(acc[md & inner & (th_true < 5.0)]))
    check(near_b > 1.5 * calm and apex > 1.5 * calm,
          "(b) 雑音の誤差は Brewster の稜線(DoLP の頂上で平ら)と頂点(DoLP → 0 で方位が不定)に集まる",
          "稜線 %.2f° / 頂点 %.2f° / 中腹 %.2f°" % (near_b, apex, calm))
    # (c) 拡散が混ざる
    fr = [0.0, 0.05, 0.1, 0.2, 0.3, 0.5]
    e_mix = []
    for f in fr:
        n_m, _ = solve(render_sweep(nrm, md, ml, index, diffuse=f, noise=0.0), md, ml)
        e_mix.append(float(np.mean(err_deg(n_m, nrm)[md & inner])))
    n_mix30, _ = solve(render_sweep(nrm, md, ml, index, diffuse=0.3, noise=0.0), md, ml)
    e_mix30 = err_deg(n_mix30, nrm)
    check(all(b > a for a, b in zip(e_mix, e_mix[1:])) and e_mix[-2] > 5.0,
          "(c) 拡散が混ざると誤差が単調に増える(ドーム、平均、雑音なし)",
          " / ".join("%d %%: %.1f°" % (100 * a, b) for a, b in zip(fr, e_mix)))

    # ---- 6. 実物に見える描画 ------------------------------------------------- #
    print("\n[6] 実物に見える描画で同じ解法(ドーム照明・黒い樹脂の拡散 1 %・消光比 1/200・ショット雑音・ほこり)")
    rc = real_chapter()
    print("  512 x 1024 の生モザイク 1 枚。測れる画素は像の暗さだけで決める(ドーム %.0f %% / レンズ %.0f %%)"
          % (100 * rc["valid_frac"], 100 * rc["valid_frac_lens"]))
    print("  法線の誤差の中央値: 部品全体(縁の 12 画素を除く)ドーム %.2f° / レンズ %.2f°" % (rc["dome_all"], rc["lens_all"]))
    check(rc["med"]["dome"] < 3.0 and rc["med"]["lens"] < 3.0,
          "測れた所の法線(縁の 12 画素を除く、中央値)",
          "ドーム %.2f° / レンズ %.2f°" % (rc["med"]["dome"], rc["med"]["lens"]))
    check(rc["rms"]["dome"] < 0.03 * rc["top"]["dome"][1],
          "測れた所の高さ(ドーム、RMS 誤差 / 高さ < 3 %)",
          "%.2f px / %.1f px(レンズ %.2f px / %.1f px)" % (rc["rms"]["dome"], rc["top"]["dome"][1],
                                                         rc["rms"]["lens"], rc["top"]["lens"][1]))
    (e82, p82), (e75, p75) = rc["apex"][82.0], rc["apex"][75.0]
    check(abs(e82 - p82) < 1.0 and abs(e75 - p75) < 1.0 and abs((e75 - e82) - (p75 - p82)) < 1.0,
          "測れない頂点の範囲は照明の穴で式どおり動く: 穴の仰角 82° → 75° で、像だけで決めた範囲の縁 θ = (90 − 穴)/2",
          "穴 82°: 縁 %.2f°(式 %.1f°)/ 穴 75°: 縁 %.2f°(式 %.1f°)" % (e82, p82, e75, p75))
    check(rc["room_med"] > 1.5 * rc["dome_all"],
          "同じドームを天井のパネル照明で撮ると悪くなる(映り込む照明が暗い所で、樹脂の拡散 1 % が混ざる)",
          "パネル照明 %.2f° vs ドーム照明 %.2f°(ドーム全体の中央値)" % (rc["room_med"], rc["dome_all"]))

    elapsed = time.time() - t0
    cpu = time.process_time() - c0
    # ★2026-10-15: 壁時計は CI の並列のシャードで同じ機械の他のテストの負荷まで数える
    #   (poc_phase_measuring_deflectometry がこれで赤になった)。この門が抑えたいのはこの PoC 自身の計算量なので、プロセスの CPU 時間
    #   (time.process_time)で測り、壁時計は併記する。
    check(cpu < 60.0, "所要時間(CI の上限に余裕を残す)", "CPU %.1f 秒(壁時計 %.1f 秒)" % (cpu, elapsed))

    if figs.enabled():
        _figures(nrm, md, ml, both, inner, z_true, sweep, raw, cands, n_sfp, e_sfp, n_ps, e_ps, h, stack,
                 e_wrong, acc, e_mix30, bins, prof, ns, e_n, fr, e_mix, th, tb, clean, gap)
        _fig_real(rc)
    assert not figs.errors(), figs.errors()

    bad = [c for c in CHECKS if not c[0]]
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(CHECKS), len(CHECKS) - len(bad), elapsed))
    if bad:
        for _, label, detail in bad:
            print("  NG:", label, detail)
        raise SystemExit(1)
    print("PASS")


def _rgb_normals(n, msk):
    """法線を色にする(x → 赤、y → 緑、z → 青、背景は灰)。"""
    img = 0.5 * (np.asarray(n, float) + 1.0)
    img[~msk] = 0.25
    return np.clip(img, 0.0, 1.0)


def _figures(nrm, md, ml, both, inner, z_true, sweep, raw, cands, n_sfp, e_sfp, n_ps, e_ps, h, stack,
             e_wrong, acc, e_mix30, bins, prof, ns, e_n, fr, e_mix, th, tb, clean, gap):
    s0 = sweep.sum(axis=0) / 2.0
    dolp = np.where(md, cands[0]["dolp"], 0.0) + np.where(ml, cands[1]["dolp"], 0.0)
    aolp = np.where(both, cands[0]["aolp_deg"], 0.0)
    figs.save_plot("fresnel", [("鏡面(反射、n = %.2f)" % N_RESIN, th, fs.ledger.sfp_dolp_model(th, N_RESIN, "specular")),
                               ("拡散(透過、n = %.2f)" % N_RESIN, th, fs.ledger.sfp_dolp_model(th, N_RESIN, "diffuse")),
                               ("Brewster 角 %.1f°" % tb, np.array([tb, tb]), np.array([0.0, 1.0]))],
                   xlabel="天頂角 θ [°]", ylabel="偏光度 DoLP", title="1 つの DoLP に天頂角が 2 つ(鏡面)",
                   colors=["emphasis", "neutral", "reference"], styles=[None, None, "dashed"], size=(640, 380),
                   caption="鏡面の DoLP は Brewster 角でちょうど 1 になり、その両側に同じ値が 2 回出る。"
                           "拡散は単調だが弱い(最大 (n²−1)/(n²+1))。")
    figs.save_grid("scene", [raw, s0, stack[0], dolp, aolp],
                   ["生のモザイク(2×2 = 0/45/90/135°)", "明るさ S0: 黒光沢もガラスもほぼ一様",
                    "照度差ステレオの 1 枚: 光沢の点だけ", "偏光度 DoLP(Brewster で 1)",
                    "偏光の方位 AoLP [°]"],
                   title="陰影は乏しいが、偏光は傾きを覚えている", ncols=3,
                   gray=[True, True, True, False, False], vrange=[None, None, None, (0.0, 1.0), (0.0, 180.0)],
                   caption="左 = 黒光沢樹脂のドーム(n = %.2f)、右 = ガラスのレンズ(n = %.2f)。DoLP の明るい輪が "
                           "Brewster 角 %.1f° の等高線。" % (N_RESIN, N_GLASS, tb))
    # 偏光子を回すと見え方が変わる(GIF)
    S0 = s0
    S1 = sweep[0] - sweep[2]
    S2 = sweep[1] - sweep[3]
    frames = []
    for t in np.radians(np.arange(0.0, 180.0, 7.5)):
        frames.append(np.clip(0.5 * (S0 + S1 * np.cos(2 * t) + S2 * np.sin(2 * t)), 0.0, None))
    figs.save_gif("analyser", frames, fps=10.0,
                  caption="検光子を 0〜180° 回したときの明るさ。黒い蝶ネクタイが回る —— 暗くなる向きが、"
                          "その画素の面の傾きの向き(鏡面では入射面に直交)。")
    cand = clean["candidates"]
    panels = [_rgb_normals(cand[k], md) for k in range(4)] + [np.where(md, gap, 0.0)]
    figs.save_grid("candidates", panels,
                   ["候補 1: 低い天頂角 × 方位 ψ+90°", "候補 2: 低い天頂角 × 方位 ψ+270°",
                    "候補 3: 高い天頂角 × 方位 ψ+90°", "候補 4: 高い天頂角 × 方位 ψ+270°",
                    "2 つの天頂角の差 [°](Brewster の輪で 0)"],
                   title="解消する前: 1 画素に 4 本の法線", ncols=3,
                   caption="鏡面の DoLP は Brewster を挟んで 2 つの天頂角を持ち、方位は偏光子にとって π が同じ。"
                           "どれが正しいかは偏光だけでは決まらない —— だから集合のまま返す。")
    figs.save_grid("normals",
                   [_rgb_normals(nrm, both), _rgb_normals(n_sfp, both), _rgb_normals(n_ps, both),
                    np.where(both, e_sfp, 0.0), np.where(both, e_ps, 0.0)],
                   ["真値の法線", "偏光(凸 + Brewster の稜線で解消)", "照度差ステレオ",
                    "偏光の誤差 [°](0〜20)", "照度差ステレオの誤差 [°](0〜20)"],
                   title="同じ部品、偏光と照度差ステレオ", ncols=3,
                   vrange=[None, None, None, (0.0, 20.0), (0.0, 20.0)],
                   caption="照度差ステレオは光沢の点しか見えず、法線を Lambert の式に無理に乗せる。")
    row = 64
    xs = np.arange(W)
    figs.save_plot("height", [("真値", xs, z_true[row]), ("偏光 → sfp_height", xs, h[row])],
                   xlabel="列 [px]", ylabel="高さ [px]", title="中央の行の高さ(左 = ドーム、右 = レンズ)",
                   colors=["reference", "emphasis"], styles=["dashed", None], size=(720, 360),
                   caption="法線を鏡像拡張した Frankot–Chellappa で積分。縁(天頂角 72°)まで形が残る。")
    figs.save_grid("failures",
                   [np.where(both, e_wrong, 0.0), np.where(both, acc, 0.0), np.where(both, e_mix30, 0.0)],
                   ["n = 1.50 と仮定(真値 1.57、雑音なし)[0〜5°]", "雑音の誤差: 稜線と頂点に集まる [0〜5°]",
                    "拡散 30 % が混ざる(雑音なし)[0〜30°]"],
                   title="どこで壊れるか(法線の誤差)", ncols=3, vrange=[(0.0, 5.0), (0.0, 5.0), (0.0, 30.0)],
                   caption="屈折率の誤りは全体を滑らかにずらす。雑音は Brewster の輪(DoLP の頂上は平らで逆算が不安定)と"
                           "頂点(DoLP → 0 で方位が不定)に集まる。拡散が混ざると偏光の打ち消しで縁ほど崩れる。")
    ok = np.isfinite(np.asarray(prof))
    figs.save_plot("where_it_breaks",
                   [("ドーム: 天頂角ごとの誤差の中央値", (bins + 2.5)[ok], np.asarray(prof)[ok])],
                   xlabel="真の天頂角 [°]", ylabel="誤差 [°](雑音 4 回の平均)",
                   title="雑音の誤差は Brewster 角 %.1f° と頂点で山になる" % tb,
                   colors=["emphasis"], size=(640, 380),
                   caption="中腹(25〜45°)がいちばん安定。")
    figs.save_plot("index_and_mixing",
                   [("仮定した屈折率(真値 1.57)", np.asarray(ns), np.asarray(e_n))],
                   xlabel="仮定した屈折率 n", ylabel="誤差の中央値 [°]",
                   title="屈折率の誤り: 真値で谷、外すほど増える", kinds=["line"], colors=["wrong"],
                   size=(560, 340), caption="較正球で測れば 0.01 以内に入る([4])。")
    figs.save_plot("mixing", [("拡散の割合", 100 * np.asarray(fr), np.asarray(e_mix))],
                   xlabel="拡散の割合 [%]", ylabel="平均誤差 [°]",
                   title="拡散が混ざると鏡面モデルは崩れる", colors=["wrong"], size=(560, 340),
                   caption="拡散の偏光は鏡面と 90° ずれていて、混ざると打ち消し合う。混合比を推定する op は無い。")


if __name__ == "__main__":
    main()
