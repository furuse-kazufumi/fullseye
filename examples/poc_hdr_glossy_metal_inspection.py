# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 光沢のある金属部品の検査画像を HDR で作る —— 鏡面の照り返しの中の傷と、暗い所の傷を 1 枚に

    py -3.11 examples/poc_hdr_glossy_metal_inspection.py

研磨した金属の部品をリング照明で撮ると、照明の映り込み(鏡面の帯)と、そこから外れた暗い拡散の
地が同じ画面に入り、明るさの差は 3 桁を超えます。8 ビットのカメラの露出 1 回では、帯に合わせれば
地が黒く潰れ、地に合わせれば帯が白く飛ぶ —— **どちらかの傷が必ず見えない**。この PoC は Fullseye の
``hdr`` 族で次の 4 段を通し、どの数字も真値と比べます。

1. **既知の放射輝度の場面を、EMVA 1288 のセンサで撮る**(``hdr_exposure_series_simulate``):
   量子効率 η = 0.6、系の利得 K = 0.1 DN/e⁻、暗雑音 8 e⁻、オフセット 4 DN、8 ビット、
   応答は γ = 2.2(一般の産業用カメラのガンマ出力の想定)。露出は 4 倍刻みの 6 段。
2. **1 枚ずつ見る**: 帯の中の傷と地の傷のコントラスト対雑音比(CNR)を各露出で測ると、
   両方が CNR ≥ 3 になる露出は無い。
3. **応答関数と放射輝度**: Debevec と Robertson で応答を推定し、真の γ の逆応答との差、
   合成した放射輝度の真値との相対誤差を出す。トーンマップ(既存の ``tonemap_reinhard``)と
   露出融合(Mertens)で 1 枚にし、両方の傷の CNR を測る。
4. **ダイナミックレンジ**(Fullseye だけの層): 露出 1 枚と 6 枚の系の DR を、EMVA 1288 の定義
   (SNR = 1 と分散の最大)でシミュから実測し、閉形式と並べる。

★正直に書いておくこと(合成であること):
  * 場面は 2-D の放射輝度の地図を直接描いたもの(帯 = ガウスの映り込み、地 = ヘアラインの模様)。
    照明と BRDF からの描画ではない。動き・位置ずれ・フレア・ブルーミングは入れていない。
  * 応答の推定は倍率 1 つが決まらない。放射輝度の誤差は倍率を 1 つ当ててから測る。
  * CNR は傷の上と、その両脇の帯状の地の平均・標準偏差から(地の模様も「雑音」に入る)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402

LG = fs.ledger
CHECKS = []

H, W = 192, 256
TS = [0.005, 0.02, 0.08, 0.32, 1.28, 5.12]   # 露出 [ms](4 倍刻み 6 段)
ETA, K, SD, OFF, BITS, GAMMA = 0.6, 0.1, 8.0, 4.0, 8, 2.2


def check(ok, label, detail=""):
    CHECKS.append((bool(ok), label, detail))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label, detail))


def scene():
    """放射輝度 [光子 / 画素 / ms]: 暗い拡散の地 + 照明の映り込みの帯 + 傷 2 本(それぞれ −20 %)。"""
    rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    hair = 1.0 + 0.02 * np.repeat(rng.standard_normal((H, 1)), W, axis=1)       # ヘアライン(行ごとの筋)
    ground = 300.0 * hair
    band = 3.0e5 * np.exp(-((xx - 0.62 * W) / 30.0) ** 2) * hair                   # 鏡面の帯(3 桁)
    rad = ground + band
    scratch_dark = (np.abs(xx - 0.25 * W - 0.15 * (yy - H / 2)) < 1.5) & (np.abs(yy - H / 2) < 60)
    scratch_band = (np.abs(yy - 0.3 * H) < 1.5) & (np.abs(xx - 0.62 * W) < 14)
    rad = np.where(scratch_dark | scratch_band, 0.8 * rad, rad)
    return rad, scratch_dark, scratch_band


def _local_contrast(a, mask, axis, off=4):
    """傷の画素ごとの局所コントラスト 1 − I / (傷を横切る向きに ±off 離れた 2 画素の平均)。"""
    r, c = np.nonzero(mask)
    if axis == 1:                                 # 縦に近い傷 → 左右の隣
        n = 0.5 * (a[r, np.clip(c - off, 0, W - 1)] + a[r, np.clip(c + off, 0, W - 1)])
    else:                                         # 横の傷 → 上下の隣
        n = 0.5 * (a[np.clip(r - off, 0, H - 1), c] + a[np.clip(r + off, 0, H - 1), c])
    return 1.0 - a[r, c] / np.maximum(n, 1e-12)


def cnr(img, scratch, axis, shift):
    """傷の局所コントラストの平均 / 傷の無い所(同じ形を shift 画素ずらした)の局所コントラストの標準偏差。

    明るさの勾配(帯の裾)を差に持ち込まないよう、傷を横切る向きの隣の画素と比べる。
    """
    a = np.asarray(img, float)
    ref = np.roll(scratch, shift, axis=axis)
    sd = float(_local_contrast(a, ref, axis).std())
    if not sd > 1e-6:
        return float("nan")                       # 地が平ら(飽和・量子化の 1 段)= 測れない
    return float(_local_contrast(a, scratch, axis).mean() / sd)


def cnr_capture(Zimg, scratch, axis, shift, inv, t):
    """1 枚の露出の CNR を放射輝度の領域で(真の逆応答で戻す)。傷の半分以上が飽和なら 0(見えない)。"""
    Z = np.rint(np.asarray(Zimg) * 255.0).astype(int)
    ref = np.roll(scratch, shift, axis=axis)
    if np.mean(Z[scratch] >= 254) > 0.5 or np.mean(Z[ref] >= 254) > 0.5:
        return 0.0
    return cnr(inv[Z] / t, scratch, axis, shift)


def main() -> int:
    t0 = time.time()
    rad, sd_mask, sb_mask = scene()
    print("=" * 78)
    print("1) 場面: 地 %.0f、帯の頂 %.0f 光子/ms(比 %.0f 倍)。EMVA のセンサ、γ = %.1f、露出 %s ms"
          % (np.median(rad[:, :40]), rad.max(), rad.max() / np.median(rad[:, :40]), GAMMA, TS))
    print("=" * 78)
    imgs = LG.hdr_exposure_series_simulate(rad, TS, ETA, K, SD, OFF, BITS, gamma=GAMMA, seed=11)

    print()
    print("2) 1 枚ずつ: 傷の CNR(地の傷 / 帯の中の傷、真の逆応答で放射輝度に戻して。飽和 = 0)")
    Zl = np.arange(1 << BITS)
    inv_true = (255.0 * (Zl / 255.0) ** GAMMA - OFF) / (K * ETA)
    both = []
    single = []
    for t, im in zip(TS, imgs):
        c1, c2 = cnr_capture(im, sd_mask, 1, 12, inv_true, t), cnr_capture(im, sb_mask, 0, 12, inv_true, t)
        c1, c2 = (0.0 if c1 != c1 else c1), (0.0 if c2 != c2 else c2)
        single.append((c1, c2))
        sat = float(np.mean(np.asarray(im) >= 1.0))
        both.append(min(c1, c2))
        print("  t = %5.2f ms: 地 %6.2f、帯 %6.2f、飽和 %.1f %%" % (t, c1, c2, 100 * sat))
    check(max(both) < 3.0, "露出 1 回では 2 本の傷の両方を CNR ≥ 3 で見られない", "(最良 %.2f)" % max(both))

    print()
    print("3) 応答関数と放射輝度(真値と比べる)")
    Z = np.arange(1 << BITS)
    Xt = (255.0 * (Z / 255.0) ** GAMMA - OFF) / (K * ETA)
    ok = (Xt > 50.0) & (Z <= 240)
    dr1 = LG.hdr_dynamic_range([TS[0]], ETA, K, SD, OFF, BITS, n_frames=2000)
    drn = LG.hdr_dynamic_range(TS, ETA, K, SD, OFF, BITS, n_frames=2000)
    m = (rad > 10.0 * drn["L_min"]) & (rad < 0.5 * drn["L_sat"])
    res = {}
    resp = {"debevec": LG.camera_response_debevec(imgs, TS, smoothness=10.0),
            "robertson": LG.camera_response_robertson(imgs, TS, max_iter=30)}
    for name in ("debevec", "robertson"):
        r = resp[name]
        d = r["g"][ok] - np.log(Xt[ok])
        d -= np.median(d)
        E = LG.hdr_merge(imgs, TS, response=r)
        er = LG.hdr_radiance_error(E, rad, mask=m)
        res[name] = (r, E, er)
        print("  %-9s 応答の ln 誤差 rms %.3f(最大 %.3f)、放射輝度の相対誤差 rms %.3f / 中央値 %.3f / p95 %.3f"
              % (name, np.sqrt(np.mean(d * d)), np.abs(d).max(), er["rms_rel"], er["median_rel"], er["p95_rel"]))
        # 実測 rms 0.114(Debevec)/ 0.117(Robertson)。この場面は中間の明るさの画素が少ない
        # (地と帯の 2 つの山)ので、単体テストの階調の場面(0.090 / 0.057)より粗い。
        check(np.sqrt(np.mean(d * d)) < 0.15, "%s の応答が真の γ の逆応答と ln で 0.15 以内" % name)
        # 実測の中央値: Debevec 0.118、Robertson 0.095(6 段。5 段の版では 0.079 / 0.070)。単体テストの階調の
        # 場面より粗いのは、この場面の画素が地と帯の 2 つの明るさに偏り、応答の暗い段の誤差が効くため。
        check(er["median_rel"] < 0.15, "%s の放射輝度が真値と中央値 15 %% 以内(倍率 1 つを当てて)" % name)
    # Debevec の三角の重みは雑音を見ない: 地の画素では短い露出の暗い段(雑音だらけ)にも重みが入る。
    # 露出時間を掛けた重み(対数の推定の逆分散)と比べる。
    rdeb = res["debevec"][0]
    E_hat = res["debevec"][1]
    E = LG.hdr_merge(imgs, TS, response=rdeb, weight="hat_time")
    n_all_sat = int(np.sum(np.all([np.asarray(i) >= 1.0 for i in imgs], axis=0)))
    check(n_all_sat == 0, "どの露出でも飽和する画素が無い(あれば合成は下限しか返さない)", "(%d 画素)" % n_all_sat)
    # 応答を EMVA で特性化した(真の γ の逆応答を知っている)場合と、自己校正(Debevec)の場合
    rtrue = {"kind": "camera_response", "levels": 1 << BITS, "inverse": inv_true}
    # γ = 1 のカメラなら EMVA で測った K·η とオフセットだけで逆応答が書ける(camera_response_linear)
    lin = LG.camera_response_linear(1 << BITS, OFF, K * ETA)
    assert np.allclose(lin["inverse"], (255.0 * (Zl / 255.0) - OFF) / (K * ETA))
    E_true = LG.hdr_merge(imgs, TS, response=rtrue, weight="hat_time")
    E_true_hat = LG.hdr_merge(imgs, TS, response=rtrue, weight="hat")
    c_true = (cnr(E_true, sd_mask, 1, 12), cnr(E_true, sb_mask, 0, 12))
    c_true_hat = (cnr(E_true_hat, sd_mask, 1, 12), cnr(E_true_hat, sb_mask, 0, 12))
    c_hat = (cnr(E_hat, sd_mask, 1, 12), cnr(E_hat, sb_mask, 0, 12))
    c_ht = (cnr(E, sd_mask, 1, 12), cnr(E, sb_mask, 0, 12))
    best_dark = max(c for c, _ in single)
    print("  合成した放射輝度の傷の CNR(地 / 帯):")
    print("    真の応答 + 露出時間つきの重み  %.2f / %.2f" % c_true)
    print("    真の応答 + 三角の重み          %.2f / %.2f" % c_true_hat)
    print("    Debevec の応答 + 露出時間つき   %.2f / %.2f" % c_ht)
    print("    Debevec の応答 + 三角の重み    %.2f / %.2f" % c_hat)
    print("    1 枚の最良                     %.2f / %.2f" % (best_dark, max(c for _, c in single)))
    check(min(c_true) >= 3.0, "特性化した応答の HDR で 2 本の傷がどちらも CNR ≥ 3", "(%.2f, %.2f)" % c_true)
    check(c_true[0] > best_dark, "逆分散(露出時間)の重みの HDR は暗部でも 1 枚の最良より良い",
          "(%.2f > %.2f)" % (c_true[0], best_dark))
    check(c_true[0] > c_true_hat[0] and c_ht[0] > c_hat[0],
          "露出時間の重みは三角の重みより地の傷の CNR が高い(短い露出の雑音を持ち込まない)")
    # ★自己校正した応答は暗い段で ln 0.2 ほど外れ(1 章の誤差の最大)、露出ごとの推定が食い違って
    #   暗部の傷の CNR を半分以下に落とす。検査に使うなら応答は EMVA で特性化しておく(教訓)。
    check(c_ht[0] < 0.6 * c_true[0], "記録: 自己校正の応答では暗部の傷の CNR が特性化した応答の 6 割未満",
          "(%.2f vs %.2f)" % (c_ht[0], c_true[0]))
    E = E_true
    lw = float(np.log(E.max() / np.median(E)))
    tm = LG.tonemap_reinhard(E / np.median(E), white=math.exp(lw))
    fu = LG.exposure_fusion_mertens(imgs)
    c1, c2 = cnr(fu, sd_mask, 1, 12), cnr(fu, sb_mask, 0, 12)
    print("  露出融合(Mertens、表示の画像)の CNR: 地 %.2f、帯 %.2f" % (c1, c2))
    check(min(c1, c2) >= 3.0, "露出融合でも 2 本の傷がどちらも CNR ≥ 3", "(%.2f, %.2f)" % (c1, c2))

    print()
    print("4) ダイナミックレンジ(EMVA 1288 の定義、シミュの実測 vs 閉形式)")
    for nm, d in (("露出 1 枚", dr1), ("露出 6 枚", drn)):
        print("  %-8s 実測 %.1f dB(%.2f ビット)、閉形式 %.1f dB、比 %.3f"
              % (nm, d["dr_db"], d["dr_bits"], d["dr_db_closed_form"], d["ratio_measured_to_closed_form"]))
        check(abs(d["ratio_measured_to_closed_form"] - 1.0) < 0.05, "%s の DR が閉形式と 5 %% 以内" % nm)
    need = 20.0 * math.log10(rad.max() / rad.min())
    print("  場面に要る DR = %.1f dB → 1 枚 %.1f dB では足りず、6 枚 %.1f dB で足りる" % (need, dr1["dr_db"], drn["dr_db"]))
    # ★比だけでなく位置も: 場面の最大が最短の露出の飽和(L_sat)より下、最小が L_min より上
    #   (比だけの門は、最大が飽和を超えていても通ってしまった —— 5 段の版で実測)。
    check(dr1["dr_db"] < need and drn["L_min"] < rad.min() and rad.max() < drn["L_sat"],
          "場面の明暗は 1 枚の DR を超え、6 枚の系の [L_min, L_sat] の内側",
          "(%.0f..%.0f ⊂ %.1f..%.0f)" % (rad.min(), rad.max(), drn["L_min"], drn["L_sat"]))

    if figs.enabled():
        figs.save_grid("exposures", [np.asarray(i) for i in imgs], ["t = %.2f ms" % t for t in TS], ncols=5,
                       title="露出 5 段: 帯に合わせると地が潰れ、地に合わせると帯が飛ぶ")
        lg = np.log10(np.maximum(E, 1e-6))
        figs.save_grid("results", [np.log10(rad), lg, tm, fu],
                       ["真の放射輝度(log10)", "HDR の放射輝度(log10)", "HDR + Reinhard(白 = 最大)", "Mertens 融合"],
                       ncols=2, gray=True, title="2 本の傷(地の斜めの線・帯の中の横線)が 1 枚に入る")
        figs.save_plot("response", [("true", Z[ok], np.log(Xt[ok]) - np.median(np.log(Xt[ok]))),
                                    ("debevec", Z[ok], res["debevec"][0]["g"][ok] - np.median(res["debevec"][0]["g"][ok])),
                                    ("robertson", Z[ok], res["robertson"][0]["g"][ok]
                                     - np.median(res["robertson"][0]["g"][ok]))],
                       xlabel="段 Z", ylabel="ln 露光量(定数を外す)", title="推定した応答と真の γ = 2.2")
        assert not figs.errors(), figs.errors()
    bad = [c for c in CHECKS if not c[0]]
    print()
    print("門: %d / %d 合格(%.1f 秒)" % (len(CHECKS) - len(bad), len(CHECKS), time.time() - t0))
    if not bad:
        print("PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
