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

真値: 描画に使った解析的な法線(球冠)と高さ。順方向の描画は ``sfp_render``(閉形式)で、
閉形式そのものは ``tests/test_sfpolar.py`` が ``glassmirror`` の Fresnel と ``optics`` の
Mueller 行列の経路(別のコード)で 1e-14 まで確かめてあり、ここでは要点だけ再掲します。

★正直に書いておくこと(合成であること):
  * 環境光は一様・無偏光、反射は 1 回、正射影。**ガラスの裏面反射と相互反射は入っていない**
    (実物のガラスでは裏面から戻る光が DoLP を下げ、天頂角を浅く読ませる)。
  * 雑音は 4 枚の画像に足したガウス雑音だけ(ショット雑音・偏光子の消光比・画素ごとの
    角度ずれは入っていない)。消光比が有限だと DoLP は一様に縮み、屈折率の誤りと同じ形で効く。
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


def main():
    t0 = time.time()
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

    elapsed = time.time() - t0
    check(elapsed < 60.0, "所要時間(CI の上限に余裕を残す)", "%.1f 秒" % elapsed)

    if figs.enabled():
        _figures(nrm, md, ml, both, inner, z_true, sweep, raw, cands, n_sfp, e_sfp, n_ps, e_ps, h, stack,
                 e_wrong, acc, e_mix30, bins, prof, ns, e_n, fr, e_mix, th, tb, clean, gap)
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
