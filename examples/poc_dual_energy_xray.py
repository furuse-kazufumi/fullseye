# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 肉の中の骨片とガラスを、2 つのエネルギーで材質ごとに色分けする(デュアルエナジー / フォトンカウンティング X 線)

    py -3.11 examples/poc_dual_energy_xray.py

【問い】食品の X 線検査の 1 枚の透過像は、各画素で L = −ln(I/I₀) という**1 つの数**しか測らない。
肉の厚みのむらが作る L の揺れは、厚さ 2 mm のガラスの破片や骨片が作る L の段差より大きい ——
1 枚の像では「厚い肉」と「薄い硬い異物」が区別できない。光子のエネルギーを数え分ける検出器
(フォトンカウンティング、窓 2 つ)で撮ると、μ(E) の**形**が材質で違う(光電効果 ∝ Z³/E³、コンプトンは
電子密度だけ)ので、各画素で方程式が 2 本になり、厚みと材質が分かれる(Alvarez & Macovski 1976 の
基底分解)。新 op 14 本(``opstomography`` の ``spectral_xray``: ``materials`` の X 線の列 4 本 +
``dualxray`` 10 本)で、次を実測します。

  0. **表と線源の真値**: 質量減衰係数 μ/ρ を NIST の公表値(Cu の 8 keV 52.55、K 端 8.979 keV で 38.29 →
     278.4 cm²/g、水の 60 keV 0.2059)と、混合則を NIST の化合物の表と、X 線管の模型の半価層を
     IEC 61267 の線質(RQR / RQA、模型の合わせには使っていない)と突き合わせる。
  1. **肉のトレイの異物**: 厚さ 25〜60 mm でむらのある肉(赤身と脂身のまだら)に、骨片・ガラス・アルミ・
     石・PVC・ポリエチレン・ゴムを埋める。1 枚の透過像では骨片とガラスがむらに埋もれ、基底分解
     (赤身 + Al)の Al の像では肉のむらが消えて異物だけが残る。異物ごとの基底の向き(角度)から
     実効原子番号を読み、材質で色を分ける。
  2. **交絡の境界**: 厚いポリエチレンと薄いアルミを、高いエネルギーの窓で同じ L になる組にすると、
     1 枚の像では d′ = 0。2 つの窓での d′ と誤り率 Φ(−d′/2) の閉形式を、モンテカルロの誤り率と比べ、
     「分けられなくなる Al の厚さ」(誤り率 5 %)の閉形式と実測を比べる。肉 40 mm の下では境界が動く。
  3. **分解の雑音 = CRLB**: 基底分解の推定の分散が、Fisher 情報の逆行列(Cramér–Rao の下限)と一致すること。
     窓のしきい値を振って σ が最小になる位置と、同じ光子数の 2 管電圧(エネルギー積分)との比較。
  4. **壊れるところ**: 検出器の電荷共有とエネルギー分解能を知らずに分解すると、肉が「Al」に化ける
     (偽の異物)。単色の近似で分解すると、厚みとともに偏る(ビーム硬化)。測れない入力は値を返さず拒否。

【真値】材料の μ/ρ は NIST SRD 126(Hubbell & Seltzer)の表、組成は ICRU 44。シーンの厚みは仕込んだ値。
【学習】0。【較正】0(検出器の応答は既知とする。4 でその仮定を外す)。

★正直に書いておくこと:
  * 合成です。散乱線(グリッド無しの太いビームでは L が小さく見える)、検出器の K 蛍光の逃げ、
    パイルアップ、画素間の電荷共有の二重計数、陽極のヒール効果は入れていません。
  * X 線管のスペクトルは物理の簡易模型(Kramers + 電子の深さ + 自己吸収 + 特性線)で、強さと深さの
    尺度の 4 定数を別の物理模型 SpekPy(MIT)に合わせています。半価層の門は合わせに使っていない IEC の値です。
  * 実効原子番号の区別には限界があります: 骨(13.2)・アルミ(13)・ガラス(12.2)は Z_eff が近く、
    2 つのエネルギーでは「同じ仲間」に入ります。区別できるのは、有機物 / 軽い無機物 / カルシウムの多い石 / 金属、の粗い分類です。

出典: Alvarez & Macovski, Phys. Med. Biol. 21, 733 (1976) / Lehmann et al., Med. Phys. 8, 659 (1981) /
Roessl & Herrmann, Phys. Med. Biol. 54, 1307 (2009) / Hubbell & Seltzer, NIST SRD 126 (2004) / ICRU Report 44 (1989) /
IEC 61267:2005 の線質の値は Tanguay & Persson, arXiv:2205.03362 の表 I から。

走らせ方: ``py -3.11 examples/poc_dual_energy_xray.py``(図は ``FULLSEYE_FIGURE_DIR`` か既定の ``out/figures/<PoC 名>/``)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402  (台帳の公開経路 fs.ledger を使う)

CHECKS = []
SCENE_EDGES = [None]       # 肉の重なりの縁(段差を測る環から外すため。検出には使わない)
CI = bool(os.environ.get("CI"))

H, W = 160, 240            # 画素(0.5 mm / 画素 → 80 × 120 mm のトレイ)
PX_MM = 0.5
KVP = 80.0
FILTRATION = (("AL", 2.5),)
THRESHOLDS = (20.0, 45.0)  # 窓: 20〜45 keV と 45 keV 以上
PHOTONS = 5.0e4            # 1 画素に入射する光子(全エネルギー)
BASIS = ("MUSCLE_ICRU44", "AL")
FAT_AMP, FAT_SIGMA = 0.08, 14.0  # 脂身の割合のまだら(振幅、空間の σ [px])
MEAT_SIGMA = 30.0                # 肉の厚さのむらの空間の σ [px]

# 仕込む異物: (名前, 材料, 中心 y, x [px], 半径 y, x [px], 厚さ [cm], 形)
INCLUSIONS = [
    ("骨片", "BONE_CORTICAL_ICRU44", 40, 45, 9, 5, 0.20, "ellipse"),
    ("ガラス", "SODA_LIME_GLASS", 40, 120, 8, 8, 0.20, "shard"),
    ("アルミ", "AL", 40, 195, 6, 6, 0.15, "disc"),
    ("石", "CALCITE", 115, 45, 7, 9, 0.25, "ellipse"),
    ("PVC", "PVC", 115, 105, 8, 6, 0.30, "rect"),
    ("ポリエチレン", "POLYETHYLENE", 115, 160, 8, 8, 0.60, "disc"),
    ("ゴム", "NATURAL_RUBBER", 115, 210, 7, 7, 0.60, "disc"),
    ("ステンレス片", "STAINLESS_STEEL_304", 145, 130, 3, 9, 0.04, "rect"),
]
ORGANIC_MAX_Z = 9.5       # 粗い分類の境界(Z_eff): 有機物 < 9.5 <= 軽い無機物 < 14.5 <= Ca の多い石 < 20 <= 金属
CLASS_EDGES = (9.5, 14.5, 20.0)
CLASS_NAMES = ("有機物", "軽い無機物(骨・ガラス・Al)", "Ca の多い石", "金属")


def _proj(*a, **k):
    """台帳の xray_channel_projection(宣言型 images = チャネルの像の並び)を (C, H, W) の配列にする。"""
    return np.asarray(fs.ledger.xray_channel_projection(*a, **k))


def _decomp(*a, **k):
    """台帳の basis_material_decompose(宣言型 images = 基底の厚みの並び、拒否は NaN)を (B, H, W) の配列にする。"""
    return np.asarray(fs.ledger.basis_material_decompose(*a, **k))


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))


def zclass(z):
    return int(np.searchsorted(CLASS_EDGES, z, side="right"))


# --------------------------------------------------------------------------- #
# シーン                                                                        #
# --------------------------------------------------------------------------- #
def _smooth_field(seed, sigma, shape=(H, W)):
    """決まった種の滑らかな場(平均 0・標準偏差 1)。種は自分の列(共有の乱数列を引かない)。"""
    rng = np.random.default_rng([seed, 2026, 10, 15])
    f = ndimage.gaussian_filter(rng.standard_normal(shape), sigma, mode="reflect")
    return (f - f.mean()) / f.std()


def _mask(kind, cy, cx, ry, rx):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    u, v = (yy - cy) / ry, (xx - cx) / rx
    if kind in ("ellipse", "disc"):
        m = u * u + v * v <= 1.0
    elif kind == "rect":
        m = (np.abs(u) <= 1.0) & (np.abs(v) <= 1.0)
    else:  # shard: 三角形
        m = (u <= 1.0) & (v >= -1.0) & (u - 1.6 * v >= -1.0)
    return m


def scene():
    """肉(赤身 + 脂身)と異物の厚み図 [cm]。異物は肉を押しのける(合計の厚さは肉のまま)。"""
    total = 4.2 + 1.0 * _smooth_field(1, MEAT_SIGMA)
    total = np.clip(total, 2.5, 6.0)
    fat = np.clip(0.18 + FAT_AMP * _smooth_field(2, FAT_SIGMA), 0.0, 0.5)
    # 肉の重なり(縁の鋭い段差): 赤身の折り返し +6 mm と、脂身の塊 +8 mm。1 枚の像の高域フィルタはこの縁も拾う
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
    fold = (yy > 58) & (yy < 100) & (xx > 18) & (xx < 112) & (yy - 0.45 * xx < 70) & (yy + 0.3 * xx > 66)
    chunk = ((yy - 80) / 17.0) ** 2 + ((xx - 186) / 38.0) ** 2 <= 1.0
    chunk &= (xx - 0.8 * yy < 150)
    total = total + 0.6 * fold
    fat_cm = total * fat + 0.8 * chunk
    total = total + 0.8 * chunk
    fat = fat_cm / total
    inc = np.zeros((len(INCLUSIONS), H, W))
    masks = []
    for i, (_, _, cy, cx, ry, rx, t, kind) in enumerate(INCLUSIONS):
        m = _mask(kind, cy, cx, ry, rx)
        inc[i][m] = t
        masks.append(m)
    meat = total - inc.sum(axis=0)
    muscle, adipose = meat * (1.0 - fat), meat * fat
    mats = ["MUSCLE_ICRU44", "ADIPOSE_ICRU44"] + [m for _, m, *_ in INCLUSIONS]
    edges = (ndimage.binary_dilation(fold ^ ndimage.binary_erosion(fold), iterations=2)
             | ndimage.binary_dilation(chunk ^ ndimage.binary_erosion(chunk), iterations=2))
    SCENE_EDGES[0] = edges
    return np.concatenate([muscle[None], adipose[None], inc]), mats, masks, total, fat


# --------------------------------------------------------------------------- #
# 本体                                                                          #
# --------------------------------------------------------------------------- #
def main():
    t0 = time.time()
    c0 = time.process_time()
    L = fs.ledger

    print("== 0. 表と線源の真値 ==")
    pub = [("CU", 8.0, 52.55), ("CU", 8.9789, 278.4), ("WATER", 60.0, 0.2059), ("AL", 60.0, 0.2778),
           ("PB", 100.0, 5.549), ("BONE_CORTICAL_ICRU44", 60.0, 0.3148)]
    worst = max(abs(L.material_xray_constants(m, e)["mu_rho_cm2_g"] / v - 1.0) for m, e, v in pub)
    below = L.material_xray_constants("CU", 8.97)["mu_rho_cm2_g"]
    check(worst < 1e-9 and 37.0 < below < 39.0, "μ/ρ が NIST の公表値と一致(Cu 8 keV 52.55・K 端の上 278.4・水・Al・Pb・骨)",
          "最大の相対差 %.1e、K 端の直下 8.97 keV で %.2f cm²/g" % (worst, below))
    zw = L.material_effective_z("WATER")["z_eff"]
    check(abs(zw - 7.42) < 0.005, "水の実効原子番号(Mayneord、指数 2.94)= 7.42", "%.4f" % zw)
    iec = [(50, 2.4, 0.0, 1.78), (70, 2.8, 0.0, 2.58), (100, 3.2, 0.0, 3.97), (150, 4.2, 0.0, 6.57),
           (50, 2.4, 10.0, 3.8), (70, 2.8, 21.0, 6.8), (100, 3.2, 34.0, 10.1), (150, 4.2, 45.0, 13.3)]
    hvl_rows = []
    for kv, tf, add, ref in iec:
        h = L.xray_beam_quality(L.xray_tube_spectrum(kv, filtration=(("AL", tf + add),)))["hvl1_mm"]
        hvl_rows.append((kv, tf, add, ref, h))
    hv_err = max(abs(h / ref - 1.0) for *_, ref, h in hvl_rows)
    check(hv_err < 0.07, "X 線管の模型の半価層が IEC 61267 の線質 8 つと 7 % 以内(合わせに使っていない外部真値)",
          "最大 %.1f %%" % (100 * hv_err))

    spec = L.xray_tube_spectrum(KVP, filtration=FILTRATION)
    ch = L.photon_counting_channels(spec, THRESHOLDS)
    q = L.xray_beam_quality(spec)
    print("  線源: %g kV、Al %.1f mm → 半価層 %.2f mm Al、平均 %.1f keV" % (KVP, FILTRATION[0][1], q["hvl1_mm"], q["mean_energy_kev"]))

    print("== 1. 肉のトレイの異物 ==")
    th, mats, masks, total, fat = scene()
    sig = _proj(th, mats, ch, PHOTONS, seed=7)
    flat = PHOTONS * ch["weights"].sum(axis=1)
    single = -np.log(sig.sum(axis=0) / flat.sum())            # 1 枚の透過像(窓を分けない計数)
    b = _decomp(sig, ch, BASIS, PHOTONS)      # 台帳の宣言型 = 厚み (B, H, W)、拒否は NaN
    n_rej = int(np.isnan(b[0]).sum())
    check(n_rej == 0, "基底分解は全画素で収束(拒否 0)", "拒否 %d 画素 / %d" % (n_rej, H * W))
    bg = ~np.any(np.array([ndimage.binary_dilation(m, iterations=4) for m in masks]), axis=0)

    # 背景(異物の無い肉)の推定: Al の像で目立つ画素を外し、残りの画素のガウス重みの平均で埋める
    # (正規化畳み込み)。異物の位置は真値を使わない —— Al の像の外れ値だけで決める。
    rough = b[1] - ndimage.median_filter(b[1], size=31, mode="reflect")
    s0 = 1.4826 * float(np.median(np.abs(rough - np.median(rough))))
    seed_px = np.abs(rough) > 4.0 * s0
    lab0, n0 = ndimage.label(seed_px)
    big = np.isin(lab0, 1 + np.where(ndimage.sum(seed_px, lab0, np.arange(1, n0 + 1)) >= 6)[0]) if n0 else seed_px
    detect = ndimage.binary_dilation(big, iterations=3)

    comps, n_comp = ndimage.label(detect)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)

    def local_bg(img):
        """検出した塊ごとに、周りの環(塊から 3〜12 画素、他の塊を除く)へ 2 次曲面を当てて中を埋める。"""
        out = img.copy()
        for k in range(1, n_comp + 1):
            c = comps == k
            ring = ndimage.binary_dilation(c, iterations=12) & ~ndimage.binary_dilation(c, iterations=3) & ~detect
            if ring.sum() < 12:
                out[c] = np.nan
                continue
            y0, x0 = yy[c].mean(), xx[c].mean()
            A = lambda m: np.stack([np.ones(m.sum()), yy[m] - y0, xx[m] - x0, (yy[m] - y0) ** 2,
                                    (yy[m] - y0) * (xx[m] - x0), (xx[m] - x0) ** 2], axis=1)
            coef = np.linalg.lstsq(A(ring), img[ring], rcond=None)[0]
            out[c] = A(c) @ coef
        return out

    s_bg = local_bg(single)
    al_bg = local_bg(b[1])
    mu_bg = local_bg(b[0])
    noise_single = float(np.std(single[bg]))                  # 肉のむら(背景の揺れ)
    noise_al = s0                                             # Al の像の雑音(中央値からの残差の MAD)
    # 異物ごとの段差は「真の位置」の周りの環(3〜12 画素、他の異物と肉の重なりの縁を除く)へ 2 次曲面を当てて測る。
    # これは見え方の物差しで、検出(上の detect)には真の位置を使わない。
    others = np.any(np.array([ndimage.binary_dilation(m, iterations=3) for m in masks]), axis=0)

    def ring_delta(img, m):
        ring = (ndimage.binary_dilation(m, iterations=12) & ~ndimage.binary_dilation(m, iterations=3) & ~others
                & ~SCENE_EDGES[0])
        y0, x0 = yy[m].mean(), xx[m].mean()
        A = lambda q: np.stack([np.ones(q.sum()), yy[q] - y0, xx[q] - x0, (yy[q] - y0) ** 2,
                                (yy[q] - y0) * (xx[q] - x0), (xx[q] - x0) ** 2], axis=1)
        core = ndimage.binary_erosion(m, iterations=2)
        coef = np.linalg.lstsq(A(ring), img[ring], rcond=None)[0]
        return float(np.mean(img[core] - A(core) @ coef))

    rows1 = []
    for (name, mat, *_), m in zip(INCLUSIONS, masks):
        d_single = ring_delta(single, m)
        d_al = ring_delta(b[1], m)
        d_mu = ring_delta(b[0], m)
        rows1.append([name, mat, d_single, d_single / noise_single, d_al, d_al / noise_al, d_mu])
        print("  %-8s 1 枚の像 ΔL %+.4f(むらの %.2f 倍)  Al の像 %+.4f cm(雑音の %.1f 倍)"
              % (name, d_single, d_single / noise_single, d_al, d_al / noise_al))
    hidden = [r for r in rows1 if r[0] in ("骨片", "ガラス")]
    check(all(abs(r[3]) < 1.0 for r in hidden), "1 枚の像では骨片とガラスの段差が肉のむら(背景の標準偏差)より小さい",
          ", ".join("%s %.2f 倍" % (r[0], r[3]) for r in hidden))
    check(all(r[5] > 5.0 for r in hidden), "基底分解の Al の像では骨片とガラスが雑音の 5 倍を超えて浮く",
          ", ".join("%s %.1f 倍" % (r[0], r[5]) for r in hidden))
    # しきい値 1 本で切る(検査機の最も素朴な判定): 骨片とガラスの芯の 90 % を拾うしきい値で、肉の何 % が引っかかるか
    pos = np.zeros((H, W), bool)
    for (name, *_), m in zip(INCLUSIONS, masks):
        if name in ("骨片", "ガラス"):
            pos |= ndimage.binary_erosion(m, iterations=1)
    single_hp = single - ndimage.median_filter(single, size=31, mode="reflect")
    fp, fobj = {}, {}
    for key, img in (("1 枚の像", single), ("1 枚の像の高域", single_hp), ("Al の像", rough)):
        thr = np.percentile(img[pos], 10.0)
        hit = (img >= thr) & bg
        fp[key] = float(np.mean(img[bg] >= thr))
        lab, n = ndimage.label(hit)
        sizes = ndimage.sum(np.ones_like(img), lab, index=np.arange(1, n + 1)) if n else np.zeros(0)
        fobj[key] = int(np.sum(np.asarray(sizes) >= 6))
    check(fp["1 枚の像"] > 0.2 and fobj["1 枚の像の高域"] >= 2 and fobj["Al の像"] == 0 and fp["Al の像"] < 0.005,
          "骨片とガラスの 90 % を拾うしきい値で: 1 枚の像は肉の 20 % 超、その高域(中央値 31 を引く)は肉の重なりの縁を"
          "偽の異物に拾い、Al の像は偽の異物 0",
          " / ".join("%s %.2f %%・偽の塊 %d 個" % (k, 100 * fp[k], fobj[k]) for k in fp))
    # 異物の材質: 基底の向き(Δ赤身, ΔAl)の角度。埋めた異物は肉を押しのけるので、測れるのは「異物 − 同じ厚さの肉」の
    # 向き —— 組成の Z だけでなく密度にもよる。参照は材料の板を肉 4 cm に埋めた向き(雑音なし)で、角度の円の上で
    # 隣り合う参照の Z を補間した値を「見かけの Z」と呼ぶ。
    zref, aref = _angle_calibration(ch)
    exact = _exact_angles(th, mats, ch)
    zest, ang_meas = [], []
    for r in rows1:
        ang = math.atan2(r[4], r[6])
        ang_meas.append(ang)
        zest.append(float(_angle_to_z(ang, aref, zref)))
    ztrue = [L.material_effective_z(mat)["z_eff"] for _, mat, *_ in INCLUSIONS]
    strong = [i for i, r in enumerate(rows1) if r[5] > 5.0]
    dang = [abs((ang_meas[i] - exact[i] + np.pi) % (2 * np.pi) - np.pi) for i in strong]
    # 許容 0.35 rad は「材質の仲間(有機物 / 無機物)を取り違えない」幅(2 つの仲間の向きは π/2 以上離れている)。
    # Z を 1 刻みで読める精度ではない —— 無機物の向きは Al(13)から Cu(29)まで 0.34 rad に詰まっている(2026-10-18 実測)。
    check(len(strong) == 6 and max(dang) < 0.35,
          "異物の基底の向きを、雑音と背景の推定を通しても 0.35 rad 以内で読む(Al の像で 5 倍超の %d 種。誤差の主因は"
          "ガラスの破片のように押しのけた肉の少ない異物で、肉の厚さのむらの当てはめ)" % len(strong),
          " ".join("%s %.3f" % (rows1[i][0], d) for i, d in zip(strong, dang)))
    z_exact = [float(_angle_to_z(a, aref, zref)) for a in exact]
    light = [i for i, (n, *_) in enumerate(INCLUSIONS) if n in ("骨片", "ガラス", "アルミ", "石")]
    check(all(abs(z_exact[i] - ztrue[i]) < 1.5 for i in light),
          "雑音なしなら、骨片・ガラス・アルミ・石の見かけの Z(押しのけた肉との差の向き)が組成の Z_eff と 1.5 以内",
          " ".join("%s %.1f(組成 %.1f)" % (rows1[i][0], z_exact[i], ztrue[i]) for i in light))
    inorganic = all(rows1[i][4] > 0 and rows1[i][6] < 0 for i in strong)
    check(inorganic, "Al の像で浮いた %d 種はすべて「Al が増え、肉が減る」向き(無機物の半平面)に入る" % len(strong), "")
    weak = [i for i, r in enumerate(rows1) if abs(r[5]) < 3.0]
    check(sorted(INCLUSIONS[i][0] for i in weak) == sorted(["ポリエチレン", "ゴム"]) and all(rows1[i][4] < 0 for i in weak),
          "肉より軽い有機物(PE・ゴム)は画素ごとの Al の像で雑音の 3 倍に届かず、画素ごとの検出では拾わない(色を塗らない)"
          " —— 領域で平均すれば Al が負(肉より軽い Z)の向きに出る",
          " ".join("%s 画素あたり %.1f 倍・領域の平均 %+.4f cm" % (rows1[i][0], rows1[i][5], rows1[i][4]) for i in weak))
    i_pvc = [i for i, (n, *_) in enumerate(INCLUSIONS) if n == "PVC"][0]
    print("  ★PVC は雑音なしでも見かけの Z %.1f(組成 %.1f): 塩素の光電効果と低い密度(1.41)で、押しのけた肉との差の"
          "向きが石に寄る —— 埋まった異物の見かけの Z は組成だけでなく密度で動く" % (z_exact[i_pvc], ztrue[i_pvc]))
    print("  見かけの Z(雑音あり): " + " ".join("%s %.1f" % (rows1[i][0], zest[i]) for i in strong))
    # 色分けの図: 検出した塊ごとに 1 つの見かけの Z(画素ごとの角度は雑音で暴れるので、塊の平均の向きで読む)
    zmap = np.full((H, W), np.nan)
    for k in range(1, n_comp + 1):
        c = comps == k
        if c.sum() < 10:
            continue
        dal, dmu = float(np.mean((b[1] - al_bg)[c])), float(np.mean((b[0] - mu_bg)[c]))
        if abs(dal) < 3.0 * noise_al:
            continue
        zmap[c] = float(_angle_to_z(math.atan2(dal, dmu), aref, zref))
        yc, xc = np.argwhere(c).mean(axis=0)
        print("  塊 (%3.0f, %3.0f) %4d 画素: ΔAl %+.3f cm、Δ赤身 %+.3f cm → 見かけの Z %.1f" % (yc, xc, c.sum(), dal, dmu, zmap[c][0]))
    extra = {"single_hp": single_hp, "rough": rough, "fp": fp, "fobj": fobj}

    print("== 2. 交絡の境界(厚い PE と薄い Al) ==")
    conf = _confound(ch, L)
    check(conf["max_err_dev"] < conf["tol"], "誤り率の閉形式 Φ(−d′/2) がモンテカルロ(各 %d 標本)と一致" % conf["n_mc"],
          "最大の差 %.4f(許容 %.4f)" % (conf["max_err_dev"], conf["tol"]))
    check(abs(conf["t5_mc"] / conf["t5_cf"] - 1.0) < 0.10,
          "分けられなくなる Al の厚さ(誤り率 5 %)の閉形式とモンテカルロが 10 % 以内",
          "閉形式 %.3f mm / 実測 %.3f mm(肉なし)" % (10 * conf["t5_cf"], 10 * conf["t5_mc"]))
    check(conf["single_dp"] < 1e-9, "同じ組を 1 つの窓だけで見ると d′ = 0(1 枚の像では区別できない)", "%.1e" % conf["single_dp"])
    check(conf["t5_meat"] > 2.0 * conf["t5_cf"], "肉 40 mm を重ねると境界の Al の厚さが 2 倍より大きくなる",
          "%.3f mm → %.3f mm" % (10 * conf["t5_cf"], 10 * conf["t5_meat"]))

    print("== 3. 分解の雑音と CRLB ==")
    cr = _crlb_mc(ch, L)
    check(abs(cr["ratio"][0] - 1) < 0.05 and abs(cr["ratio"][1] - 1) < 0.05 and abs(cr["dcorr"]) < 0.05,
          "分解の標準偏差がクラメール・ラオの下限と 5 % 以内(相関も)",
          "σ 実測/下限 = %.3f, %.3f、相関 %.3f vs %.3f" % (cr["ratio"][0], cr["ratio"][1], cr["corr_mc"], cr["corr_cf"]))
    sweep = [(t, L.basis_decomposition_crlb((4.0, 0.0), BASIS, L.photon_counting_channels(spec, (20.0, t)), PHOTONS)["sigma_cm"][1])
             for t in np.arange(26.0, 66.0, 2.0)]
    t_best = min(sweep, key=lambda r: round(r[1], 9))[0]
    check(30.0 <= t_best <= 60.0, "窓の境のしきい値には最適がある(両端より中が良い)", "σ_Al が最小 %.0f keV" % t_best)
    kv_ch = L.dual_kvp_channels(L.xray_tube_spectrum(60.0, filtration=FILTRATION), L.xray_tube_spectrum(120.0, filtration=(("AL", 2.5), ("CU", 0.3))))
    s_pc = L.basis_decomposition_crlb((4.0, 0.0), BASIS, ch, PHOTONS)["sigma_cm"][1]
    s_kv = L.basis_decomposition_crlb((4.0, 0.0), BASIS, kv_ch, PHOTONS)["sigma_cm"][1]
    print("  同じ光子数(半分ずつ 2 回撮る扱いにせず 1 回ぶん)で σ_Al: 計数 2 窓 %.4f cm / 2 管電圧の積分型 %.4f cm" % (s_pc, s_kv))

    print("== 4. 壊れるところ ==")
    real = L.photon_counting_channels(spec, THRESHOLDS, energy_resolution_fwhm_kev=8.0, charge_sharing=0.25)
    sig_r = _proj(th, mats, real, PHOTONS, noise=False)
    ideal = _decomp(_proj(th, mats, ch, PHOTONS, noise=False), ch, BASIS, PHOTONS)
    wrong = _decomp(sig_r, ch, BASIS, PHOTONS)
    right = _decomp(sig_r, real, BASIS, PHOTONS)
    fake = float(np.median((wrong[1] - ideal[1])[bg]))
    honest = float(np.median(np.abs(right[1] - ideal[1])[bg]))
    check(abs(fake) > 3 * noise_al and honest < 0.1 * noise_al,
          "電荷共有 25 %・分解能 8 keV を知らずに分解すると肉が Al に化ける(応答を知れば消える)",
          "肉の Al 成分 %+.4f cm(雑音の %.1f 倍)→ %.1e cm" % (fake, fake / noise_al, honest))
    lin = _linear_bias(ch, L)
    check(lin["bias_thick"] > 5 * lin["bias_thin"], "単色の近似(線形の分解)は厚くなるほど偏る —— ビーム硬化",
          "肉 1 cm で Al %+.4f cm、6 cm で %+.4f cm" % (lin["bias_thin_signed"], lin["bias_thick_signed"]))
    refused = _refusals(L, ch, sig)
    check(refused == 6, "測れない入力は黙って値を返さず拒否する", "%d / 6" % refused)

    elapsed = time.time() - t0
    cpu = time.process_time() - c0
    check(cpu < 120.0, "所要時間(この PoC 自身の CPU 時間)", "CPU %.1f 秒(壁時計 %.1f 秒)" % (cpu, elapsed))

    if figs.enabled():
        _figures(L, spec, ch, q, th, mats, masks, total, fat, sig, single, b, extra, zmap, rows1, (zest, z_exact), ztrue,
                 conf, cr, sweep, t_best, s_pc, s_kv, wrong, real, noise_al, hvl_rows, lin)
    assert not figs.errors(), figs.errors()

    bad = [ck for ck in CHECKS if not ck[0]]
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(CHECKS), len(CHECKS) - len(bad), elapsed))
    if bad:
        for _, label, detail in bad:
            print("  NG:", label, detail)
        raise SystemExit(1)
    print("PASS")


# --------------------------------------------------------------------------- #
# 下請け                                                                        #
# --------------------------------------------------------------------------- #
#: 角度の照合に使う参照(Z_eff の分かっている物質の板を、同じ厚さの肉に埋める)
ANGLE_REFS = ("POLYETHYLENE", "NATURAL_RUBBER", "ADIPOSE_ICRU44", "PMMA", "PTFE", "MG", "AL", "SI", "S", "CALCITE",
              "TI", "FE", "CU")


def _angle_calibration(ch):
    """基底の向き atan2(ΔAl, Δ赤身) → Z_eff の表を、参照物質の板(肉 4 cm に埋めた 2 mm)で作る。"""
    L = fs.ledger
    angs, zs = [], []
    for m in ANGLE_REFS:
        t = np.zeros((3, 1, 2))
        t[0] = 4.0
        t[0, 0, 1] = 4.0 - 0.2
        t[1, 0, 1] = 0.2
        s = _proj(t[:2], ["MUSCLE_ICRU44", m], ch, PHOTONS, noise=False)
        d = _decomp(s, ch, BASIS, PHOTONS)
        angs.append(math.atan2(d[1, 0, 1] - d[1, 0, 0], d[0, 0, 1] - d[0, 0, 0]))
        zs.append(L.material_effective_z(m)["z_eff"])
    order = np.argsort(angs)
    return np.array(zs)[order], np.array(angs)[order]


def _exact_angles(th, mats, ch):
    """雑音なしで、異物を同じ割合の肉に置き換えた真の背景との差の向き(異物ごとの芯の平均)。"""
    L = fs.ledger
    th0 = th.copy()
    rest = th[2:].sum(axis=0)
    meat = th[0] + th[1]
    frac = np.where(meat > 0, th[1] / np.maximum(meat, 1e-12), 0.0)
    th0[0] = th[0] + rest * (1.0 - frac)
    th0[1] = th[1] + rest * frac
    th0[2:] = 0.0
    b1 = _decomp(_proj(th, mats, ch, PHOTONS, noise=False), ch, BASIS, PHOTONS)
    b0 = _decomp(_proj(th0, mats, ch, PHOTONS, noise=False), ch, BASIS, PHOTONS)
    out = []
    for i in range(len(INCLUSIONS)):
        core = ndimage.binary_erosion(th[2 + i] > 0, iterations=2)
        out.append(math.atan2(float((b1[1] - b0[1])[core].mean()), float((b1[0] - b0[0])[core].mean())))
    return out


def _angle_to_z(ang, aref, zref):
    """角度 → Z_eff: 角度の円の上で隣り合う 2 つの参照の間を線形に補間する(参照は角度の順)。

    基底の向きは「異物 − 押しのけた肉」の差なので、肉に近い材料(水・赤身)は差が小さく向きが定まらない ——
    そこは参照に入れず、振幅の小さい画素は材質を言わない(呼び手が NaN にする)。"""
    a = np.mod(np.asarray(ang, dtype=np.float64) - aref[0], 2 * np.pi) + aref[0]
    ae = np.concatenate([aref, [aref[0] + 2 * np.pi]])
    ze = np.concatenate([zref, [zref[0]]])
    return np.interp(a, ae, ze)


def _confound(ch, L):
    """厚い PE と薄い Al(高い窓で同じ L)の誤り率: 閉形式とモンテカルロ。"""
    n_mc = 4000 if CI else 20000
    ts = np.geomspace(0.002, 0.08, 9)               # PE の厚さ [cm] を振り、Al はそれに合わせる
    rows = []
    for i, ta in enumerate(ts):
        r = L.dual_energy_separability("POLYETHYLENE", ta, "AL", None, ch, PHOTONS)
        mc = _mc_error(ch, r, "POLYETHYLENE", ta, "AL", r["thickness_b_cm"], n_mc, 100 + i)
        rows.append((ta, r["thickness_b_cm"], r["d_prime"], r["error_rate"], mc))
    errs = np.array([[r[3], r[4]] for r in rows])
    tol = float(np.max(3.0 * np.sqrt(errs[:, 0] * (1 - errs[:, 0]) / n_mc)) + 0.005)
    dev = float(np.max(np.abs(errs[:, 0] - errs[:, 1])))
    tb = np.array([r[1] for r in rows])

    def t_at(err):
        # 誤り率は Al の厚さとともに単調に下がる。対数の厚さで 5 % の位置を補間する
        e = np.asarray(err)
        j = np.where((e[:-1] >= 0.05) & (e[1:] < 0.05))[0]
        if j.size == 0:
            return float("nan")
        j = j[0]
        f = (e[j] - 0.05) / (e[j] - e[j + 1])
        return float(np.exp(np.log(tb[j]) + f * (np.log(tb[j + 1]) - np.log(tb[j]))))

    single = L.dual_energy_separability("POLYETHYLENE", 0.04, "AL", None, ch, PHOTONS)["d_prime_single"][-1]
    # 肉 40 mm の下
    ts_m = np.geomspace(0.01, 0.6, 12)
    meat = [L.dual_energy_separability("POLYETHYLENE", t, "AL", None, ch, PHOTONS, background=("MUSCLE_ICRU44", 4.0))
            for t in ts_m]
    tbm = np.array([r["thickness_b_cm"] for r in meat])
    em = np.array([r["error_rate"] for r in meat])
    j = np.where((em[:-1] >= 0.05) & (em[1:] < 0.05))[0][0]
    f = (em[j] - 0.05) / (em[j] - em[j + 1])
    t5m = float(np.exp(np.log(tbm[j]) + f * (np.log(tbm[j + 1]) - np.log(tbm[j]))))
    return {"rows": rows, "n_mc": n_mc, "tol": tol, "max_err_dev": dev, "t5_cf": t_at(errs[:, 0]),
            "t5_mc": t_at(errs[:, 1]), "single_dp": float(single), "t5_meat": t5m,
            "meat": [(r["thickness_b_cm"], r["error_rate"]) for r in meat]}


def _mc_error(ch, r, ma, ta, mb, tb, n, seed):
    L = fs.ledger
    flat = PHOTONS * ch["weights"].sum(axis=1)
    sa = _proj(np.full((1, 1, n), ta), [ma], ch, PHOTONS, seed=seed)
    sb = _proj(np.full((1, 1, n), tb), [mb], ch, PHOTONS, seed=seed + 5000)
    xa = -np.log(np.maximum(sa[:, 0, :], 0.5) / flat[:, None])
    xb = -np.log(np.maximum(sb[:, 0, :], 0.5) / flat[:, None])
    w = np.linalg.solve(r["cov_L"], r["L_b"] - r["L_a"])
    c = float(w @ (r["L_a"] + r["L_b"])) / 2.0
    return 0.5 * (float(np.mean(w @ xa > c)) + float(np.mean(w @ xb < c)))


def _crlb_mc(ch, L):
    n = 3000 if CI else 12000
    t = np.zeros((2, 1, n))
    t[0], t[1] = 4.0, 0.05
    s = _proj(t, list(BASIS), ch, PHOTONS, seed=31)
    d = _decomp(s, ch, BASIS, PHOTONS)[:, 0, :]
    cr = L.basis_decomposition_crlb((4.0, 0.05), BASIS, ch, PHOTONS)
    sd = d.std(axis=1)
    corr = float(np.corrcoef(d)[0, 1])
    return {"ratio": sd / cr["sigma_cm"], "corr_mc": corr, "corr_cf": float(cr["correlation"][0, 1]),
            "dcorr": corr - float(cr["correlation"][0, 1]), "samples": d, "crlb": cr, "n": n}


def _linear_bias(ch, L):
    """有効 μ の線形の分解(空のスペクトルの平均 μ で解く)の偏りを、肉だけの厚さで測る。"""
    E = ch["energy_kev"]
    Wg = ch["weights"] * ch["gain"][None, :]
    mu = np.array([np.interp(E, *L.material_xray_attenuation(m, E[0], E[-1], 400, "mu").T) for m in BASIS])
    M = (Wg @ mu.T) / Wg.sum(axis=1)[:, None]
    out = {}
    for name, t in (("thin", 1.0), ("thick", 6.0)):
        s = _proj(np.full((1, 1, 1), t), ["MUSCLE_ICRU44"], ch, PHOTONS, noise=False)
        Lc = -np.log(s[:, 0, 0] / (PHOTONS * ch["weights"].sum(axis=1)))
        bl = np.linalg.solve(M, Lc)
        out["bias_" + name] = abs(float(bl[1]))
        out["bias_%s_signed" % name] = float(bl[1])
    curve = []
    for t in np.linspace(0.5, 8.0, 16):
        s = _proj(np.full((1, 1, 1), t), ["MUSCLE_ICRU44"], ch, PHOTONS, noise=False)
        Lc = -np.log(s[:, 0, 0] / (PHOTONS * ch["weights"].sum(axis=1)))
        bn = _decomp(s, ch, BASIS, PHOTONS)[:, 0, 0]
        curve.append((t, float(np.linalg.solve(M, Lc)[1]), float(bn[1])))
    out["curve"] = curve
    return out


def _refusals(L, ch, sig):
    n = 0
    tries = [
        lambda: L.material_xray_constants(L.material_from_sellmeier("組成の無い硝材"), 60.0),   # 組成の無い材料
        lambda: L.material_xray_constants("WATER", 2000.0),                     # 表の範囲の外
        lambda: L.basis_decomposition_crlb((4.0, 0.0), ("WATER", "WATER"), ch, PHOTONS),   # 同じ基底を 2 回
        lambda: _decomp(sig[:1], ch, BASIS, PHOTONS),         # 窓 1 つで基底 2 つ
        lambda: L.photon_counting_channels(L.xray_tube_spectrum(KVP), (20.0, 90.0)),     # 光子の来ない窓
        lambda: L.xray_tube_spectrum(KVP, filtration=(("PB", 50.0),)),          # 全部吸収
    ]
    for f in tries:
        try:
            f()
        except ValueError:
            n += 1
    # 0 計数の画素は NaN で拒否され、数に出る(値を作らない)
    s = sig[:, :2, :2].copy()
    s[:, 0, 0] = 0.0
    d = _decomp(s, ch, BASIS, PHOTONS)
    if not (np.isnan(d[0, 0, 0]) and int(np.isnan(d[0]).sum()) == 1):
        n -= 1
    return n


# --------------------------------------------------------------------------- #
# 図                                                                            #
# --------------------------------------------------------------------------- #
def _hsv_to_rgb(h, s, v):
    i = np.floor(h * 6.0).astype(int) % 6
    f = h * 6.0 - np.floor(h * 6.0)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)


def _material_rgb(single, zmap):
    """1 枚の像を灰色の地に、材質の分かった画素を Z_eff の色で塗る(青 = 有機物 → 緑 → 橙 → 赤 = 金属)。"""
    g = (single - np.percentile(single, 1)) / (np.percentile(single, 99) - np.percentile(single, 1))
    g = np.clip(1.0 - g, 0.0, 1.0) * 0.8 + 0.1
    rgb = np.repeat(g[..., None], 3, axis=-1)
    m = np.isfinite(zmap)
    hue = np.clip((np.where(m, zmap, 7.0) - 5.0) / 25.0, 0.0, 1.0)
    col = _hsv_to_rgb(0.66 * (1.0 - hue), np.full_like(hue, 0.85), np.full_like(hue, 0.95))
    rgb[m] = col[m]
    return (np.clip(rgb, 0, 1) * 255).astype(np.uint8)


def _lims(series, k):
    v = np.concatenate([np.asarray(s[k], dtype=np.float64).ravel() for s in series])
    v = v[np.isfinite(v)]
    lo, hi = float(v.min()), float(v.max())
    pad = 0.04 * (hi - lo)
    return (lo - pad, hi + pad)


def _figures(L, spec, ch, q, th, mats, masks, total, fat, sig, single, b, extra, zmap, rows1, zest, ztrue,
             conf, cr, sweep, t_best, s_pc, s_kv, wrong, real, noise_al, hvl_rows, lin):
    E = ch["energy_kev"]
    figs.save_plot("spectrum_and_windows",
                   [("X 線管(%g kV、Al 2.5 mm)" % KVP, spec[:, 0], spec[:, 1] / spec[:, 1].max()),
                    ("窓 1(%s)の感度" % ch["labels"][0], E, ch["weights"][0] / ch["weights"].max()),
                    ("窓 2(%s)の感度" % ch["labels"][1], E, ch["weights"][1] / ch["weights"].max())],
                   xlabel="光子のエネルギー [keV]", ylabel="相対値", title="スペクトルと 2 つのエネルギーの窓",
                   colors=["neutral", "reference", "emphasis"], styles=[None, "dashed", None], size=(640, 360),
                   caption="W 陽極の管(Kramers の厚い陽極 + 自己吸収 + K 線 59 / 67 keV)を Al 2.5 mm で濾した光子スペクトル"
                           "(半価層 %.2f mm Al、平均 %.1f keV)。CdTe 2 mm の吸収効率をかけ、堆積エネルギーで 2 つの窓に分ける。" % (q["hvl1_mm"], q["mean_energy_kev"]))
    Eg = np.geomspace(10, 150, 300)
    ser = []
    for m, lab in (("ADIPOSE_ICRU44", "脂身"), ("MUSCLE_ICRU44", "赤身"), ("POLYETHYLENE", "PE"), ("BONE_CORTICAL_ICRU44", "骨"),
                   ("SODA_LIME_GLASS", "ガラス"), ("AL", "Al"), ("CALCITE", "石(方解石)")):
        a = L.material_xray_attenuation(m, 10, 150, 300)
        ser.append((lab, a[:, 0], np.log10(a[:, 1])))
    figs.save_plot("mass_attenuation", ser, xlabel="エネルギー [keV]", ylabel="log10 μ/ρ [cm²/g]",
                   title="質量減衰係数(NIST SRD 126 の表と混合則)", size=(640, 380),
                   caption="低いエネルギーでは光電効果(≈ Z³/E³)で Z の大きい材料ほど急に増え、高いエネルギーでは"
                           "コンプトン散乱で電子密度に揃う。この**傾きの違い**が 2 つのエネルギーで材質を分ける手がかり。")
    figs.save_table("iec_beam_quality", ["線質", "管電圧 kV", "全ろ過 Al mm", "公表 HVL mm Al", "模型 HVL", "差"],
                    [["RQR" if add == 0 else "RQA", "%d" % kv, "%.1f" % (tf + add), "%.2f" % ref, "%.2f" % h,
                      "%+.1f %%" % (100 * (h / ref - 1))] for kv, tf, add, ref, h in hvl_rows],
                    title="X 線管の模型の半価層と IEC 61267 の線質",
                    caption="模型の 4 定数は SpekPy のスペクトルの形に合わせたもので、この表の値は合わせに使っていない。"
                            "IEC の値は Tanguay & Persson(arXiv:2205.03362)表 I と Yoshizumi & Caldas の表から。")
    truth = np.zeros((H, W))
    for i, m in enumerate(masks):
        truth[m] = i + 1
    fp, fobj = extra["fp"], extra["fobj"]
    figs.save_grid("tray_single_vs_basis", [total * 10, single, extra["single_hp"], extra["rough"]],
                   ["肉の厚さ [mm](真値、折り返しと脂身の塊つき)", "1 枚の透過像 L(窓を分けない)",
                    "1 枚の像の高域(中央値 31 を引く)", "基底分解: Al の厚さの高域 [cm]"],
                   title="肉のトレイ: 1 枚の像は肉の縁も拾い、Al の像は異物だけを拾う", ncols=2,
                   signed=[False, False, True, True], gray=[False, True, False, False],
                   vrange=[None, None, (-0.3, 0.3), (-0.3, 0.3)],
                   caption="上段左: 仕込んだ肉の厚さ(25〜60 mm のむら、左に赤身の折り返し +6 mm、右に脂身の塊 +8 mm)。"
                           "上段右: 1 枚の透過像 —— 骨片とガラスの段差は肉のむらの %.2f 倍・%.2f 倍で、しきい値 1 本では肉の %.0f %% が"
                           "引っかかる。下段左: 高域を取ると異物は見えるが、肉の重なりの縁も同じ明るさで残る(偽の塊 %d 個)。"
                           "下段右: 2 つの窓を赤身と Al に分けた Al の像 —— 肉の厚みも重なりも赤身の側に入り、異物だけが残る(偽の塊 %d 個)。"
                           % (rows1[0][3], rows1[1][3], 100 * fp["1 枚の像"], fobj["1 枚の像の高域"], fobj["Al の像"]))
    rgb = _material_rgb(single, zmap)
    big = np.kron(rgb, np.ones((3, 3, 1), dtype=np.uint8))
    zest, z_exact = zest
    shown = [abs(r[5]) >= 3.0 for r in rows1]
    figs.save("material_colour", big,
              caption="1 枚の透過像(灰色)の上に、Al の像で浮いた画素だけ、基底の向きから読んだ見かけの Z を色で重ねた"
                      "(緑 ≈ 12〜14、黄〜橙 ≈ 15〜20、赤 ≈ 25 以上)。読み(雑音あり / 雑音なし / 組成): "
                      + "、".join("%s %.1f / %.1f / %.1f" % (n[0], a, e, t)
                                 for n, a, e, t, sh in zip(INCLUSIONS, zest, z_exact, ztrue, shown) if sh)
                      + "。PE とゴムは画素ごとの差が雑音に届かず、色を塗らない(材質を言わない。領域で平均すれば肉より軽い向きに出る)。埋まった異物は肉を押しのける"
                        "ので、見かけの Z は組成だけでなく密度でも動く(PVC は密度 1.41 で石の向きに寄る)。")
    figs.save_table("inclusions", ["異物", "材料", "厚さ mm", "1 枚の像の段差 / むら", "Al の像 / 雑音",
                                   "見かけの Z(雑音あり)", "見かけの Z(雑音なし)", "組成の Z_eff"],
                    [[r[0], r[1], "%.1f" % (10 * inc[6]), "%.2f" % r[3], "%.1f" % r[5],
                      ("%.1f" % ze) if sh else "—", "%.1f" % zx, "%.1f" % zt]
                     for r, inc, ze, zx, zt, sh in zip(rows1, INCLUSIONS, zest, z_exact, ztrue, shown)],
                    title="異物 8 種: 1 枚の像と基底分解",
                    caption="見かけの Z = 「異物 − 押しのけた同じ厚さの肉」の基底の向きを、材料の板を肉に埋めた参照の向きと照合した値。"
                            "Z が大きいほど向きが 1 点に寄るので、向きの小さな誤差(肉のむらの当てはめ)が Z の大きな誤差になる。")
    # R vs L_high の散布図
    Lc = -np.log(np.maximum(sig, 0.5) / (PHOTONS * ch["weights"].sum(axis=1))[:, None, None])
    Rm = Lc[0] / Lc[1]
    sel = np.zeros((H, W), bool)
    sel[::3, ::3] = True
    inc_any = np.any(np.array(masks), axis=0)
    ser = [("肉の画素", Lc[1][sel & ~inc_any], Rm[sel & ~inc_any])]
    groups = (("骨片・ガラス・アルミ", ("骨片", "ガラス", "アルミ")), ("石・PVC", ("石", "PVC")),
              ("ステンレス片", ("ステンレス片",)), ("PE・ゴム", ("ポリエチレン", "ゴム")))
    for lab, names in groups:
        core = np.zeros((H, W), bool)
        for (name, *_), m in zip(INCLUSIONS, masks):
            if name in names:
                core |= ndimage.binary_erosion(m, iterations=2)
        ser.append((lab, Lc[1][core], Rm[core]))
    kinds = ["scatter"] * len(ser)
    lmax = float(np.nanmax(Lc[1])) * 1.05
    for m, lab in (("MUSCLE_ICRU44", "赤身の板(雑音なし)"), ("AL", "Al の板(雑音なし)")):
        mu_hi = L.material_xray_constants(m, 50.0)["mu_per_cm"]
        tt = np.linspace(0.25, lmax, 60) / mu_hi
        s = _proj(np.reshape(tt, (1, 1, -1)), [m], ch, PHOTONS, noise=False)
        l2 = -np.log(s[:, 0, :] / (PHOTONS * ch["weights"].sum(axis=1))[:, None])
        ser.append((lab, l2[1], l2[0] / l2[1]))
        kinds.append("line")
    figs.save_plot("r_value_scatter", ser, xlabel="高い窓の L", ylabel="R = L_低 / L_高", kinds=kinds,
                   styles=[None] * 5 + ["dashed"] * 2, size=(700, 440), xlim=_lims(ser, 1), ylim=_lims(ser, 2),
                   colors=["neutral", "right", "emphasis", "wrong", "reference", "neutral", "right"],
                   title="R 値の散布図: 肉の帯と異物",
                   caption="単色なら R は材質だけで決まる。多色では厚くなるほどビーム硬化で R が下がる(破線の板の曲線が右下へ"
                           "流れる)。肉の画素は赤身の曲線に乗り、異物の画素は肉と異物の混ざりなので、肉の帯から上(重い)"
                           "か下(軽い)へ少しだけずれる —— だから異物は基底分解の**差**で見る。")
    # 交絡の境界
    rows = conf["rows"]
    tb = np.array([r[1] for r in rows]) * 10
    figs.save_plot("confound_boundary",
                   [("閉形式 Φ(−d′/2)", tb, np.array([r[3] for r in rows])),
                    ("モンテカルロ(%d 標本)" % conf["n_mc"], tb, np.array([r[4] for r in rows])),
                    ("肉 40 mm の下(閉形式)", np.array([t for t, _ in conf["meat"]]) * 10, np.array([e for _, e in conf["meat"]]))],
                   xlabel="Al の厚さ [mm](PE はこれと高い窓で同じ L になる厚さ)", ylabel="誤り率",
                   kinds=["line", "scatter", "line"], styles=[None, None, "dashed"], colors=["reference", "emphasis", "wrong"],
                   size=(660, 380),
                   title="厚い PE と薄い Al: どこで分けられなくなるか",
                   caption="高い窓だけでは同じ L(1 枚の像の d′ = 0)。2 つの窓の d′ は Al の厚さに比例して伸び、誤り率 5 %% の"
                           "境界は閉形式 %.3f mm・モンテカルロ %.3f mm。肉 40 mm を重ねると光子が減り、境界は %.2f mm へ動く。"
                           % (10 * conf["t5_cf"], 10 * conf["t5_mc"], 10 * conf["t5_meat"]))
    d = cr["samples"]
    cf = cr["crlb"]
    ang = np.linspace(0, 2 * np.pi, 200)
    evals, evecs = np.linalg.eigh(cf["cov"])
    ell = (evecs @ (np.sqrt(evals)[:, None] * np.array([np.cos(ang), np.sin(ang)])) * 2.0)
    figs.save_plot("crlb_ellipse",
                   [("分解した画素(%d)" % cr["n"], d[0, ::4] - 4.0, (d[1, ::4] - 0.05) * 10),
                    ("CRLB の 2σ 楕円", ell[0], ell[1] * 10)],
                   xlabel="赤身の厚さの誤差 [cm]", ylabel="Al の厚さの誤差 [mm]", kinds=["scatter", "line"],
                   styles=[None, "dashed"], colors=["neutral", "reference"], size=(560, 420),
                   title="基底分解の雑音はクラメール・ラオの下限に乗る",
                   caption="肉 4 cm + Al 0.5 mm を 1 万回撮って分解した。2 つの基底の誤差は強く負に相関する(相関 %.3f、閉形式 %.3f)"
                           " —— Al を多く見積もると赤身を少なく見積もる。標準偏差は下限の %.3f 倍・%.3f 倍。"
                           % (cr["corr_mc"], cr["corr_cf"], cr["ratio"][0], cr["ratio"][1]))
    figs.save_plot("threshold_sweep", [("σ_Al(CRLB)", np.array([t for t, _ in sweep]), np.array([s * 10 for _, s in sweep]))],
                   xlabel="2 つの窓の境のしきい値 [keV]", ylabel="Al の厚さの σ [mm]", size=(560, 340),
                   title="窓の境をどこに置くか",
                   caption="肉 4 cm の下の Al の厚さの雑音(下限)。境が低すぎると低い窓の光子が肉に吸われて減り、高すぎると 2 つの"
                           "窓の μ の差が縮む。最小は %.0f keV。同じ光子数の 2 管電圧(60 / 120 kV、エネルギー積分)は σ_Al %.3f mm、"
                           "計数 2 窓は %.3f mm。" % (t_best, 10 * s_kv, 10 * s_pc))
    figs.save_grid("charge_sharing_fake", [wrong[1] - np.median(wrong[1]), b[1] - np.median(b[1])],
                   ["応答を知らずに分解した Al の像(偏りの中央値を引いた)", "正しい応答の Al の像"],
                   title="電荷共有と分解能を知らないと、肉が Al に化ける", ncols=2, signed=True, vrange=(-0.06, 0.06),
                   caption="電荷共有 25 % と分解能 8 keV(FWHM)の検出器を、理想の応答だと思って分解すると、高い窓の光子が低い窓へ"
                           "漏れて肉全体が「Al を含む」と出る(左、肉の厚さの模様が Al の像に写る)。")
    c = lin["curve"]
    figs.save_plot("beam_hardening_bias",
                   [("単色の近似(線形の分解)", np.array([r[0] for r in c]), np.array([r[1] * 10 for r in c])),
                    ("多色の模型(この op)", np.array([r[0] for r in c]), np.array([r[2] * 10 for r in c]))],
                   xlabel="肉の厚さ [cm](異物なし)", ylabel="見かけの Al の厚さ [mm]", colors=["wrong", "right"],
                   size=(560, 340), title="単色の近似は厚くなるほど偏る(ビーム硬化)",
                   caption="空のスペクトルの平均 μ で連立方程式を解くと、肉が厚くなるにつれ硬くなったスペクトルを読み違え、"
                           "肉だけなのに Al が負に出る。多色の順方向模型を解けば 0 のまま。")


if __name__ == "__main__":
    main()
