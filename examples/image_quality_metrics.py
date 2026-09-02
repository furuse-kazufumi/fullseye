# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""image_quality_metrics — 画質 op(imgmetrics)を「保存設定を 1 つ選ぶ」筋で一巡する。

    py -3.11 examples/image_quality_metrics.py

【この例が解く問題】
検査ラインが 8 bit カラーで撮った画像を保管したい。全部を生で残すと容量が
足りないので、**保存前に何段へ量子化するか**を 1 つだけ決める。勘で決めず、
「欠陥が見えなくならない」を数値の合否条件に落として選びきる。

(1) 決める前に**物差しを検定する**。CIEDE2000 を公開検証表 34 組と、SSIM を
    scikit-image と突き合わせる。物差しが狂っていたら以降は全部無意味。
(2) 色空間の経路を固定する。``rgb_to_xyz`` → ``xyz_to_lab`` が ``rgb_to_lab``
    と厳密に同じで、``lab_to_rgb`` で戻ること。
(3) ``data_range`` を推測させない。取り違えると PSNR が **48.13 dB** 動くのに
    例外は出ない。
(4) 候補(128/64/32/16/8 段)を ``compare_images`` で測り、``measure_with`` で
    **契約ごと**測り直し、``metrics_table`` で条件つきの表にする。
(5) 情報量で「量子化が何 bit 捨てたか」を測る。
(6) 実際に保存されるバイト数を ``compressed_size`` で測る。``ncd`` は「距離」を
    名乗るので、構造のあるデータで対称性を確かめてから使う。
(7) ``ssim_map`` / ``delta_e_map`` で**どこが**壊れたかを見る。
(8) 判定 —— 3 つの合否条件を全部満たす一番粗い設定を選ぶ。

【グラウンドトゥルース(数値で嘘を弾く)】
1. CIEDE2000: Sharma, Wu & Dalal (2005) の 34 組と最大誤差 4.95e-05
   (表は小数 4 桁なので 5e-05 が丸めの上限)。
2. SSIM: scikit-image の独立実装(gaussian_weights, σ=1.5, 母分散)と
   **差 0.0**(2 つの量子化段で確認)。
3. 色空間: 経路と直接呼びが差 0.0、Lab 往復が 8.9e-16、白は L*=100.0000039
   (行列と白色点の公表値が 7 桁目で食い違う既知量)。
4. PSNR: 一致する 2 枚で ``inf``、一定差 0.1・幅 1.0 でちょうど 20 dB、
   幅を 255 と取り違えると 20*log10(255) = 48.1308 dB ずれる。
5. 情報量: ``I(X;X) = H(X)`` が厳密、``H(A,B) = H(A) + H(B) - I(A;B)`` が厳密、
   ``I(A;B) <= min(H(A), H(B))``。
6. NCD: 直交する縞(縦縞と横縞)で対称化前は 0.571429 対 0.595238 とずれ、
   対称化後は厳密に一致。**同じ検査を一様乱数でやると差は 0.000e+00** で
   何も分からない ―― 構造のあるデータを混ぜる理由。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import imgmetrics as M  # noqa: E402

LEVELS = (128, 64, 32, 16, 8)

# 合否条件(産業向けの色管理でよく使う線)。ΔE00 = 1 が「並べれば分かる」限界。
MAX_MEAN_DE = 1.0          # 画面平均の色差
MAX_P95_DE = 1.0           # 上位 5 % の色差(局所的な破綻を拾う)
MIN_SSIM = 0.99            # 構造の保存


def inspection_plate(n=256):
    """検査画像を組む —— **乱数だけにしない**。

    照明の勾配(なだらか)+ 8 px 周期の縦縞(細かい構造)+ 平坦なワーク面
    (同値だらけの領域)+ 円形の欠陥(見失ってはいけないもの)、その上に
    1.2 LSB のセンサ雑音。乱数だけの絵は対称性の破れも量子化の影響も隠す。
    """
    y, x = np.mgrid[0:n, 0:n] / (n - 1.0)
    img = 0.30 + 0.40 * x                                   # 照明の勾配
    img = img + 0.06 * ((np.arange(n) // 8) % 2)[None, :]   # 8 px 周期の縦縞
    img[n // 8: n // 3, n // 8: n // 3] = 0.82              # 平坦なワーク面
    defect = (y - 0.66) ** 2 + (x - 0.62) ** 2 < 0.0045
    img[defect] = 0.10                                      # 円形の欠陥
    rgb = np.stack([img, img * 0.92 + 0.05, img * 0.80 + 0.12], axis=-1)
    rgb = rgb + (1.2 / 255.0) * np.random.default_rng(7).standard_normal(rgb.shape)
    return np.round(np.clip(rgb, 0.0, 1.0) * 255.0).astype(np.uint8), defect


def quantise(u8, levels):
    """``levels`` 段へ均等量子化して 8 bit に戻す(``levels=256`` は恒等)。"""
    q = np.round(u8.astype(np.float64) / 255.0 * (levels - 1))
    return np.round(q * 255.0 / (levels - 1)).astype(np.uint8)


def main():
    plate, defect = inspection_plate()
    gray = plate[..., 1].copy()                             # G チャネル(輝度代用)

    # ------------------------------------------------------------------ #
    # 0) 物差しの検定 —— 外部基準に当てる                                  #
    # ------------------------------------------------------------------ #
    worst = max(abs(float(M.delta_e_2000((L1, a1, b1), (L2, a2, b2))) - want)
                for L1, a1, b1, L2, a2, b2, want in M.CIEDE2000_TEST_PAIRS)
    print(f"0) 物差しの検定: CIEDE2000 を Sharma et al. (2005) の "
          f"{len(M.CIEDE2000_TEST_PAIRS)} 組と照合 → 最大誤差 {worst:.2e}")
    assert len(M.CIEDE2000_TEST_PAIRS) == 34
    assert worst < 5e-5                                     # 表は小数 4 桁

    try:
        import skimage.metrics as ski
    except ImportError:                                     # pragma: no cover
        ski = None
    if ski is not None:
        for lv in (32, 8):
            q = quantise(gray, lv)
            mine = M.ssim(gray, q, data_range=255.0)
            # 原論文の設定に揃える(ガウシアン窓 σ=1.5・母分散)。片方だけ
            # 標本分散にすると値が変わるので、揃えないと比較にならない。
            theirs = float(ski.structural_similarity(
                gray, q, data_range=255.0, gaussian_weights=True,
                sigma=1.5, use_sample_covariance=False))
            print(f"   SSIM({lv:3d} 段) 自前={mine:.10f} scikit-image={theirs:.10f}  "
                  f"差={abs(mine - theirs):.1e}")
            assert abs(mine - theirs) < 1e-9
    else:                                                   # pragma: no cover
        print("   SSIM: scikit-image が無いので外部照合はスキップ")

    # ------------------------------------------------------------------ #
    # 1) 色空間の経路と data_range —— 黙って間違う場所を先に潰す           #
    # ------------------------------------------------------------------ #
    unit = plate / 255.0
    lab_chain = M.xyz_to_lab(M.rgb_to_xyz(unit))            # 2 段で
    lab_direct = M.rgb_to_lab(unit)                         # 1 段で
    roundtrip = float(np.abs(M.lab_to_rgb(lab_direct) - unit).max())
    white = M.rgb_to_lab(np.array([1.0, 1.0, 1.0]))
    print(f"1) 色空間: rgb_to_xyz→xyz_to_lab と rgb_to_lab の差="
          f"{float(np.abs(lab_chain - lab_direct).max()):.1e}  "
          f"Lab 往復={roundtrip:.1e}  白の L*={white[0]:.7f}")
    assert np.array_equal(lab_chain, lab_direct)            # 同じ計算に至る
    assert roundtrip < 1e-12                                # 色域内なので厳密
    assert abs(white[0] - 100.0) < 1e-5                     # 公表値の 7 桁目の食い違い

    dr_u8 = M.data_range_of(plate)                          # dtype から一意
    dr_f = M.data_range_of(unit)                            # [0,1] の float
    lo = quantise(plate, 16) / 255.0
    shift = M.psnr(unit, lo, data_range=255.0) - M.psnr(unit, lo, data_range=1.0)
    print(f"   data_range: uint8 → {dr_u8}  [0,1] float → {dr_f}  "
          f"取り違えたときの PSNR のずれ={shift:.4f} dB "
          f"(= 20*log10(255) = {20 * np.log10(255.0):.4f}、例外は出ない)")
    assert dr_u8 == 255.0 and dr_f == 1.0
    assert abs(shift - 20.0 * np.log10(255.0)) < 1e-9

    # 閉じた形の既知値でも当てておく(一定差 0.1・幅 1.0 → ちょうど 20 dB)
    flat_a = np.zeros((16, 16))
    flat_b = np.full((16, 16), 0.1)
    print(f"   閉形式: mse={M.mse(flat_a, flat_b):.6f}  rmse={M.rmse(flat_a, flat_b):.6f}  "
          f"psnr={M.psnr(flat_a, flat_b, data_range=1.0):.6f} dB  "
          f"自分自身との psnr={M.psnr(plate, plate.copy())}")
    assert abs(M.mse(flat_a, flat_b) - 0.01) < 1e-15
    assert abs(M.rmse(flat_a, flat_b) - 0.1) < 1e-15
    assert abs(M.psnr(flat_a, flat_b, data_range=1.0) - 20.0) < 1e-12
    assert M.psnr(plate, plate.copy()) == float("inf")      # 有限値に化かさない

    # ------------------------------------------------------------------ #
    # 2) 候補ごとに測る —— 契約を持ち回る                                  #
    # ------------------------------------------------------------------ #
    assert np.array_equal(quantise(plate, 256), plate)      # 256 段は恒等
    base_bytes = M.compressed_size(plate)
    reports = {}
    first = None
    print(f"2) 候補ごとの測定(原画 {plate.shape} uint8、lzma で {base_bytes} B):")
    print("   段数   PSNR[dB]     SSIM   MS-SSIM   ΔE00 平均   ΔE00 p95   保存 B   対原画")
    for lv in LEVELS:
        q = quantise(plate, lv)
        if first is None:
            # 最初の 1 回だけ契約を作る。以降は measure_with で**同じ条件**を
            # 持ち回る ―― 数値だけを表に写して条件が消える事故を作れなくする。
            rep = M.compare_images(plate, q, channel_axis=-1)
            first = rep
        else:
            rep = M.measure_with(first, plate, q)
        assert rep["contract"] == first["contract"]         # 条件は 1 つだけ
        dmap = M.delta_e_map(plate / 255.0, q / 255.0)
        rep["delta_e_p95"] = float(np.percentile(dmap, 95))
        rep["ms_ssim"] = M.ms_ssim(gray, quantise(gray, lv), data_range=255.0)
        rep["bytes"] = M.compressed_size(q)
        reports[lv] = rep
        print(f"   {lv:4d}  {rep['psnr']:9.3f}  {rep['ssim']:.6f}  {rep['ms_ssim']:.6f}  "
              f"{rep['delta_e_2000_mean']:9.4f}  {rep['delta_e_p95']:9.4f}  "
              f"{rep['bytes']:7d}  {rep['bytes'] / base_bytes:6.1%}")
        # ΔE00 の平均は compare_images の中でも独立に出ている(同じ値になる)
        assert abs(rep["delta_e_2000_mean"] - float(dmap.mean())) < 1e-12

    # 粗くするほど悪くなる —— 全指標が同じ向きに動くこと
    for a, b in zip(LEVELS, LEVELS[1:]):
        assert reports[a]["psnr"] > reports[b]["psnr"]
        assert reports[a]["ssim"] > reports[b]["ssim"]
        assert reports[a]["ms_ssim"] > reports[b]["ms_ssim"]
        assert reports[a]["delta_e_2000_mean"] < reports[b]["delta_e_2000_mean"]
        assert reports[a]["bytes"] > reports[b]["bytes"]

    print("   16 段の報告を表に(数値だけの表は作れない ―― 条件の行が必ず付く):")
    for name, value in M.metrics_table(reports[16]):
        if isinstance(value, float):
            print(f"      {name:<32} {value:.6f}")
        else:
            print(f"      {name:<32} {value}")
    names = [n for n, _ in M.metrics_table(reports[16])]
    assert "条件: data_range" in names and "条件: channel_axis" in names
    assert "条件: ssim_win_size" in names

    # ------------------------------------------------------------------ #
    # 3) 情報量 —— 量子化が捨てた bit を測る                               #
    # ------------------------------------------------------------------ #
    h_gray = M.image_entropy(gray, bins=64, data_range=255.0)
    assert abs(M.mutual_information(gray, gray.copy(), bins=64, data_range=255.0)
               - h_gray) < 1e-12                            # I(X;X) = H(X) は厳密
    assert abs(M.normalized_mutual_information(
        gray, gray.copy(), bins=64, data_range=255.0) - 1.0) < 1e-12
    print(f"3) 情報量(64 ビン、data_range=255): 原画 H(X)={h_gray:.4f} bit  "
          f"I(X;X)=H(X) が厳密に成立")
    print("   段数   H(Q)     I(X;Q)   H(X,Q)   NMI      検算 |H(X)+H(Q)-I-H(X,Q)|")
    for lv in LEVELS:
        q = quantise(gray, lv)
        hq = M.image_entropy(q, bins=64, data_range=255.0)
        mi = M.mutual_information(gray, q, bins=64, data_range=255.0)
        hj = M.joint_entropy(gray, q, bins=64, data_range=255.0)
        nmi = M.normalized_mutual_information(gray, q, bins=64, data_range=255.0)
        resid = abs(h_gray + hq - mi - hj)
        print(f"   {lv:4d}  {hq:7.4f}  {mi:7.4f}  {hj:7.4f}  {nmi:.4f}  {resid:.2e}")
        assert resid < 1e-12                                # 定義から厳密
        assert mi <= min(h_gray, hq) + 1e-12                # 情報は増えない
        assert 0.0 < nmi <= 1.0 + 1e-12
    # 同時ヒストグラムは正規化された同時確率
    jh = M.joint_histogram(gray, quantise(gray, 8), bins=64, data_range=255.0)
    print(f"   joint_histogram: 形 {jh.shape}  総和 {jh.sum():.15f}  "
          f"非零セル {int(np.count_nonzero(jh))} / {jh.size}"
          "(8 段に潰したので対応が疎)")
    assert jh.shape == (64, 64) and abs(jh.sum() - 1.0) < 1e-12
    assert np.all(jh >= 0.0)

    # ------------------------------------------------------------------ #
    # 4) 圧縮距離 —— 使う前に「距離」であることを確かめる                  #
    # ------------------------------------------------------------------ #
    stripe_v = np.tile(np.arange(64, dtype=np.uint8), (64, 1))         # 縦縞
    stripe_h = np.repeat(np.arange(64, dtype=np.uint8), 64).reshape(64, 64)  # 横縞
    raw_vh = M.ncd(stripe_v, stripe_h, symmetric=False)
    raw_hv = M.ncd(stripe_h, stripe_v, symmetric=False)
    sym_vh = M.ncd(stripe_v, stripe_h)
    sym_hv = M.ncd(stripe_h, stripe_v)
    rng = np.random.default_rng(0)
    noise_a = (rng.random((64, 64)) * 255).astype(np.uint8)
    noise_b = (rng.random((64, 64)) * 255).astype(np.uint8)
    rand_gap = abs(M.ncd(noise_a, noise_b, symmetric=False)
                   - M.ncd(noise_b, noise_a, symmetric=False))
    print(f"4) NCD の対称性: 直交縞で 対称化前 {raw_vh:.6f} 対 {raw_hv:.6f}"
          f"(差 {abs(raw_vh - raw_hv):.3e})→ 対称化後 {sym_vh:.6f} 対 {sym_hv:.6f}")
    print(f"   同じ検査を一様乱数でやると差は {rand_gap:.3e} "
          "—— 乱数だけでは対称性の破れが見えない")
    assert abs(raw_vh - 0.571429) < 1e-5 and abs(raw_hv - 0.595238) < 1e-5
    assert raw_vh != raw_hv                                 # 素朴版は非対称
    assert sym_vh == sym_hv                                 # 対称化後は厳密一致
    assert rand_gap == 0.0                                  # 乱数では破れが隠れる

    # 雑音があると NCD の分離能が消える(生 float を拒む理由と同じ仕組み)
    clean = np.round(np.clip(
        inspection_plate()[0] / 255.0 - 0.0, 0, 1) * 255).astype(np.uint8)
    y, x = np.mgrid[0:256, 0:256] / 255.0
    noiseless = np.zeros_like(clean)
    tmp = 0.30 + 0.40 * x + 0.06 * ((np.arange(256) // 8) % 2)[None, :]
    tmp[32:85, 32:85] = 0.82
    tmp[defect] = 0.10
    for c, k in enumerate((1.0, 0.92, 0.80)):
        off = (0.0, 0.05, 0.12)[c]
        noiseless[..., c] = np.round(np.clip(tmp * k + off, 0, 1) * 255)
    unrelated = (np.random.default_rng(3).random(clean.shape) * 255).astype(np.uint8)
    for label, img in (("雑音なし", noiseless), ("雑音あり(実機)", clean)):
        near = M.ncd(img, quantise(img, 8))
        far = M.ncd(img, unrelated)
        print(f"   {label:<14} lzma {M.compressed_size(img):7d} B  "
              f"NCD(自分, 8 段量子化)={near:.4f}  NCD(自分, 無関係)={far:.4f}  "
              f"分離={'できる' if near < far - 0.05 else 'できない'}")
    assert M.ncd(noiseless, quantise(noiseless, 8)) < M.ncd(noiseless, unrelated) - 0.2
    # 実機の絵では 1.2 LSB の雑音が下位ビットを埋め、バイト列の共通部分が消える
    assert M.ncd(clean, quantise(clean, 8)) > M.ncd(clean, unrelated) - 0.05
    print("   → 下位ビットが雑音だと NCD は「似ている」を見つけられない。"
          "生の float を拒むのと同じ仕組みなので、判定には使わない。")

    # ------------------------------------------------------------------ #
    # 5) どこが壊れたか —— マップで見る                                    #
    # ------------------------------------------------------------------ #
    smap = M.ssim_map(gray, quantise(gray, 8), data_range=255.0)
    pad = (11 - 1) // 2
    inner_defect = defect[pad:-pad, pad:-pad]
    plateau = smap[40:70, 40:70].mean()                     # 平坦なワーク面
    stripes = smap[170:230, 20:110].mean()                  # 縞のある領域
    print(f"5) 8 段に落としたときの SSIM マップ {smap.shape}: "
          f"欠陥内 {smap[inner_defect].mean():.4f}  平坦部 {plateau:.4f}  "
          f"縞領域 {stripes:.4f}  最小 {smap.min():.4f}")
    assert smap.shape == (gray.shape[0] - 2 * pad, gray.shape[1] - 2 * pad)
    assert stripes < plateau                                # 壊れるのは細かい構造
    assert stripes < smap[inner_defect].mean()
    print("   → 量子化が壊すのは**細かい構造**であって大きな塊ではない。"
          "欠陥そのものより縞の方が先に潰れる。")

    dmap8 = M.delta_e_map(plate / 255.0, quantise(plate, 8) / 255.0)
    dmap76 = M.delta_e_map(plate / 255.0, quantise(plate, 8) / 255.0, kind="76")
    lab_q = M.rgb_to_lab(quantise(plate, 8) / 255.0)
    assert np.array_equal(dmap8, M.delta_e_2000(lab_direct, lab_q))
    assert np.array_equal(dmap76, M.delta_e_76(lab_direct, lab_q))
    print(f"   ΔE の定義違い: CIE76 平均 {dmap76.mean():.4f} / 最大 {dmap76.max():.4f}、"
          f"CIEDE2000 平均 {dmap8.mean():.4f} / 最大 {dmap8.max():.4f}"
          f"(平均で {dmap76.mean() / dmap8.mean():.3f} 倍)")
    assert dmap76.mean() > dmap8.mean()   # CIE76 は彩度差を過大評価する側

    # ------------------------------------------------------------------ #
    # 6) 判定                                                             #
    # ------------------------------------------------------------------ #
    print(f"6) 判定(ΔE00 平均 < {MAX_MEAN_DE} かつ ΔE00 p95 < {MAX_P95_DE} "
          f"かつ SSIM > {MIN_SSIM}):")
    passed = []
    for lv in LEVELS:
        r = reports[lv]
        ok = (r["delta_e_2000_mean"] < MAX_MEAN_DE and r["delta_e_p95"] < MAX_P95_DE
              and r["ssim"] > MIN_SSIM)
        why = "合格" if ok else "、".join(
            w for w, c in (("ΔE00 平均超過", r["delta_e_2000_mean"] >= MAX_MEAN_DE),
                           ("ΔE00 p95 超過", r["delta_e_p95"] >= MAX_P95_DE),
                           ("SSIM 不足", r["ssim"] <= MIN_SSIM)) if c)
        print(f"   {lv:4d} 段: {why}")
        if ok:
            passed.append(lv)
    assert passed, "どの候補も条件を満たさなかった"
    chosen = min(passed)                                    # 合格の中で一番粗い
    r = reports[chosen]
    print(f"   → **{chosen} 段(1 チャネル {int(np.log2(chosen))} bit)を選ぶ**。"
          f"保存 {base_bytes} B → {r['bytes']} B "
          f"({1 - r['bytes'] / base_bytes:.1%} 削減)、"
          f"最悪の色差 p95 = {r['delta_e_p95']:.4f} ΔE00 は目視限界の下。")
    assert chosen == 128
    assert r["bytes"] < base_bytes
    assert r["delta_e_p95"] < 1.0

    print("PASS: imgmetrics 24 op すべてを通し、外部検証表・独立実装・"
          "情報量の恒等式と一致")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
