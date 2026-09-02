# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""image_forensics_audit — 提出された 1 枚を、証拠として「どこまで言えるか」まで切り分ける。

    py -3.11 examples/image_forensics_audit.py

【この例が解く問題】
編集部に 1 枚の写真が持ち込まれた。撮影者の主張は「社の カメラ A で撮った
JPEG、無加工」。手元にあるのは (a) カメラ A で撮ったと確実に分かっている
清浄なフレーム 8 枚、(b) 同じ場面の保管済みオリジナル、(c) 別のカメラ B の
1 枚。この材料だけで、主張のどこが保てて どこが崩れるかを順に詰める。

    段 0  証拠品を **自分で作る** —— この例の強みは、改竄側を自分で作れること。
          どこから どこへ 何 px ずらしたか、どの品質で貼ったかが手元にある。
    段 1  同一性: 知覚ハッシュで「保管オリジナルと同じ写真か」を数える。
          **ここで局所改竄は見つからない**(ハッシュの原理的な限界)。
    段 2  証拠 → 判定: 利用者自身の清浄データから帰無分布を測り、証拠量が
          そのどこに座るかを出す。**しきい値は同梱されていない**ので自分で作る。
    段 3  由来: PRNU センサ指紋でカメラ A / B を分ける。飽和領域では
          「何も言えない」ことも地図で示す。
    段 4  圧縮履歴: 量子化表からブラインドで品質を当て、ELA と JPEG ゴーストで
          **別の品質で貼られた領域**を浮かせる。
    段 5  雑音整合性: まず既知の σ の校正板で地図を検算し、それから提出画像へ。
    段 6  自己複製: コピー&ムーブを **誤差 0 px** で当てる。
    段 7  出す側の対策: 電子透かしを埋めて、PSNR と BER のトレードオフを表で出す。

【グラウンドトゥルース(数値で嘘を弾く)】
1. コピー&ムーブのシフトはこちらが決めた (110, 128)。誤差 **0 px 厳密**で当たる。
   清浄画像では 1 件も出ない(偽陽性 0)。
2. 貼り付けは品質 60 で符号化してから貼った。JPEG ゴーストの最頻値が **60**。
   台紙は品質 90 で、jpeg_quality_estimate が **90 をブラインドで当てる**。
   無圧縮には ``quality=None`` と答える(「品質 100」とは答えない)。
3. PRNU: 同一センサと別センサで PCE が 2〜3 桁離れる。指紋はゼロ平均・単位分散
   (|mean| < 1e-12、std = 1 ± 1e-9)。飽和させた半面は強度が 1 桁低い。
4. 透かし: 埋めた 128 bit がそのまま戻る(BER = 0、ハミング距離 0)。
   強度を上げると PSNR は単調に下がる = トレードオフが数で見える。
5. 雑音地図: σ = 0.01 / 0.04 の校正板で、真値 2.55 / 10.20(8 bit 階調)を
   1 % 以内で測り返し、比はちょうど 4.0。
6. 帰無分布: 無関係な組は z ≈ 0、同一由来の組は z < -5(分布の完全に外)。
   向きを取り違えると「いちばん強い証拠」が「珍しくない」に化ける(例外は出ない)。
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import imgforensics as F  # noqa: E402

from PIL import Image  # noqa: E402


# --------------------------------------------------------------------------- #
# 場面と機材を合成する —— ここで作った「正解」だけが後段の審判になる            #
# --------------------------------------------------------------------------- #
def natural(n=256, seed=0, beta=1.6):
    """1/f^beta のスペクトルを持つ自然画像風の場。seed で **構造ごと**変わる。"""
    r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    f = np.sqrt(fy ** 2 + fx ** 2)
    f[0, 0] = 1.0
    spec = np.fft.fft2(r.standard_normal((n, n))) / (f ** beta)
    spec[0, 0] = 0
    img = np.real(np.fft.ifft2(spec))
    return 0.15 + 0.7 * (img - img.min()) / (np.ptp(img) + 1e-12)


def textured(n=256, seed=4):
    """低周波の地 + はっきりしたテクスチャ。コーナーが立つ = 特徴点が取れる場面。"""
    r = np.random.default_rng(seed)
    tex = ndimage.gaussian_filter(r.standard_normal((n, n)), 1.0)
    tex = (tex - tex.min()) / np.ptp(tex)
    return np.clip(0.55 * natural(n, seed) + 0.45 * tex, 0, 1)


def jpeg(img, q):
    """本物の JPEG を通して戻す(近似ではない)。真の品質が手元に残る。"""
    buf = io.BytesIO()
    Image.fromarray((np.clip(img, 0, 1) * 255).round().astype(np.uint8), "L").save(
        buf, "JPEG", quality=q, subsampling=0)
    buf.seek(0)
    return np.asarray(Image.open(buf).convert("L"), np.float64) / 255.0


def sensor_pattern(n, seed):
    """カメラ 1 台ぶんの PRNU パターン K(ゼロ平均・単位分散の白色)。"""
    r = np.random.default_rng(seed)
    k = r.standard_normal((n, n))
    return (k - k.mean()) / k.std()


def shoot(scene, K, gain=0.03, read=0.01, seed=0):
    """撮像モデル I = I0·(1 + gain·K) + 読み出し雑音(Chen et al. 2008 の形)。"""
    r = np.random.default_rng(seed)
    return np.clip(scene * (1.0 + gain * K) + read * r.standard_normal(scene.shape),
                   0, 1)


N = 256
SRC, DST, PATCH = (40, 32), (150, 160), 64          # コピー&ムーブの既知の座標
TRUE_SHIFT = (float(DST[0] - SRC[0]), float(DST[1] - SRC[1]))   # = (110, 128)
SPLICE = (slice(130, 178), slice(16, 64))           # 別画像を貼る矩形
BASE_Q, SPLICE_Q = 90, 60                           # 台紙 / 貼り込みの真の品質


def main():
    # ------------------------------------------------------------------ #
    # 0) 証拠品を自分で作る —— 何をどうしたか **全部こちらが知っている**    #
    # ------------------------------------------------------------------ #
    K_a, K_b = sensor_pattern(N, 101), sensor_pattern(N, 202)   # カメラ A / B
    scene = textured(N, 4)
    original = jpeg(shoot(scene, K_a, seed=5000), BASE_Q)       # 保管オリジナル

    submitted = original.copy()
    # 加工 1: 同じ写真の中からの複製(クローンスタンプ)
    submitted[DST[0]:DST[0] + PATCH, DST[1]:DST[1] + PATCH] = \
        original[SRC[0]:SRC[0] + PATCH, SRC[1]:SRC[1] + PATCH]
    # 加工 2: 別の写真を品質 60 で符号化してから貼る(スプライス)
    foreign = jpeg(natural(N, 13), SPLICE_Q)
    submitted[SPLICE] = foreign[SPLICE]

    print(f"0) 証拠品: {N}x{N}  台紙 q={BASE_Q}  複製 {SRC}→{DST} {PATCH}px 角 "
          f"(真のシフト {TRUE_SHIFT})  貼り込み q={SPLICE_Q} "
          f"rows{SPLICE[0].start}-{SPLICE[0].stop} cols{SPLICE[1].start}-{SPLICE[1].stop}")
    changed = float(np.mean(submitted != original))
    print(f"   提出画像は保管オリジナルと {100 * changed:.2f}% の画素で異なる")
    assert changed > 0.05

    # ------------------------------------------------------------------ #
    # 1) 同一性 —— 知覚ハッシュは「同じ写真か」しか言えない                 #
    # ------------------------------------------------------------------ #
    clone_only = original.copy()
    clone_only[DST[0]:DST[0] + PATCH, DST[1]:DST[1] + PATCH] = \
        original[SRC[0]:SRC[0] + PATCH, SRC[1]:SRC[1] + PATCH]
    h_orig = F.perceptual_hash(original, "dct")
    h_sub = F.perceptual_hash(submitted, "dct")
    h_clone = F.perceptual_hash(clone_only, "dct")
    h_other = F.perceptual_hash(natural(N, 77), "dct")
    d_same = F.hash_distance(h_orig, h_sub)
    d_clone = F.hash_distance(h_orig, h_clone)
    d_other = F.hash_distance(h_orig, h_other)
    print(f"1) 同一性(dct 64 bit): 提出 vs オリジナル = {d_same} bit  /  "
          f"複製だけの版 = {d_clone} bit  /  無関係な 1 枚 = {d_other} bit")
    assert h_orig.dtype == np.bool_ and h_orig.shape == (64,)
    assert d_clone < d_same < 18 < d_other      # どちらも「同じ写真」の域に入る
    print(f"   → 『同じ写真』とは言える({d_same} bit は無関係な組の域 {d_other} の"
          f"はるか内側)。しかし **どこを どう変えたかは何も言っていない** —— "
          f"画素の {100 * changed:.1f}% を書き換えても {d_same} bit、"
          f"同じ写真からの複製だけなら {d_clone} bit で、ほぼ見えない")

    # ------------------------------------------------------------------ #
    # 2) 証拠を判定に変える —— しきい値は同梱されない。自分の清浄データで作る #
    # ------------------------------------------------------------------ #
    clean_pairs = [F.hash_distance(F.perceptual_hash(natural(N, s), "dct"),
                                   F.perceptual_hash(natural(N, s + 50), "dct"))
                   for s in range(20)]
    null_hash = F.null_distribution(clean_pairs)
    print(f"2) 帰無分布(無関係な清浄 {null_hash['n']} 組の距離): "
          f"平均 {null_hash['mean']:.2f}  σ {null_hash['std']:.2f}  "
          f"5% 分位 {null_hash['quantiles'][5]:.1f}  95% 分位 {null_hash['quantiles'][95]:.1f}")
    q_same = F.evidence_quantile(d_same, null_hash, higher_is_stronger=False)
    q_other = F.evidence_quantile(d_other, null_hash, higher_is_stronger=False)
    print(f"   提出 vs オリジナル: z={q_same['z']:+.2f}  分布の外側 "
          f"{100 * q_same['beyond_fraction']:.0f}%  /  無関係な組: z={q_other['z']:+.2f}  "
          f"外側 {100 * q_other['beyond_fraction']:.0f}%")
    assert q_same["z"] < -5.0 and q_same["beyond_fraction"] == 1.0
    assert abs(q_other["z"]) < 2.0
    assert "verdict" not in q_same and "tampered" not in q_same   # 判定は返らない
    # 向きを取り違えても例外は出ない —— 「いちばん強い証拠」が「よくある」に化ける
    wrong = F.evidence_quantile(d_same, null_hash, higher_is_stronger=True)
    print(f"   向きを取り違えると: 外側 {100 * wrong['beyond_fraction']:.0f}% "
          f"(同じ数値が『珍しくない』になる。例外は出ない)")
    assert wrong["beyond_fraction"] == 0.0

    # ------------------------------------------------------------------ #
    # 3) 由来 —— PRNU センサ指紋でカメラを分ける                            #
    # ------------------------------------------------------------------ #
    bank_a = [shoot(natural(N, 300 + i), K_a, seed=1000 + i) for i in range(8)]
    fp_a = F.sensor_fingerprint(bank_a)
    print(f"3) 指紋(カメラ A の清浄 8 枚から): shape={fp_a.shape}  "
          f"|mean|={abs(float(fp_a.mean())):.2e}  std={float(fp_a.std()):.9f}  "
          f"真の K との相関={np.corrcoef(fp_a.ravel(), K_a.ravel())[0, 1]:.3f}")
    assert abs(float(fp_a.mean())) < 1e-12
    assert abs(float(fp_a.std()) - 1.0) < 1e-9

    r_a = F.fingerprint_correlate(submitted, fp_a)
    r_b = F.fingerprint_correlate(shoot(natural(N, 900), K_b, seed=5001), fp_a)
    print(f"   提出画像 vs 指紋 A: PCE={r_a['pce']:.1f} ピーク位置={r_a['peak_shift']}  /  "
          f"カメラ B の 1 枚: PCE={r_b['pce']:.1f} ピーク位置={r_b['peak_shift']}")
    assert r_a["peak_shift"] == (0, 0)          # 同一センサはピークが原点
    assert r_b["peak_shift"] != (0, 0)
    assert r_a["pce"] > 100 * abs(r_b["pce"])   # 2 桁以上離れる
    assert r_a["caveats"]                       # 「注意書き無しの証拠」は返らない

    # PCE の帰無分布は「別カメラの束」で作る = 向きは higher_is_stronger
    null_pce = F.null_distribution(
        [F.fingerprint_correlate(shoot(natural(N, 700 + i), K_b, seed=6000 + i),
                                 fp_a)["pce"] for i in range(12)])
    q_pce = F.evidence_quantile(r_a["pce"], null_pce, higher_is_stronger=True)
    print(f"   別カメラ 12 枚の PCE 帰無分布: 平均 {null_pce['mean']:.2f} "
          f"σ {null_pce['std']:.2f} 最大 {null_pce['max']:.2f}  → 提出画像は "
          f"z={q_pce['z']:+.1f}、外側 {100 * q_pce['beyond_fraction']:.0f}%")
    assert q_pce["beyond_fraction"] == 1.0 and q_pce["z"] > 10.0

    # 飽和した領域では指紋が乗らない = 「そこでは何も言えない」を地図で言う
    sat_bank = []
    for i in range(8):
        sc = natural(N, 300 + i).copy()
        sc[:, :N // 2] = 1.6                    # clip されて飽和する半面
        sat_bank.append(shoot(sc, K_a, seed=1000 + i))
    smap = F.fingerprint_strength_map(F.sensor_fingerprint(sat_bank), 16)
    sat, ok = float(smap[:, :N // 2].mean()), float(smap[:, N // 2:].mean())
    print(f"   強度地図: 飽和した半面 {sat:.3f} / 正常な半面 {ok:.3f} "
          f"= {ok / sat:.1f} 倍  (飽和側では PCE の低さを『別カメラ』と読めない)")
    assert smap.shape == (N, N) and ok / sat > 5.0

    # ------------------------------------------------------------------ #
    # 4) 圧縮履歴 —— 量子化表・ELA・JPEG ゴースト                           #
    # ------------------------------------------------------------------ #
    est = F.jpeg_quality_estimate(submitted)
    est_clean = F.jpeg_quality_estimate(scene)          # 無圧縮の対照
    print(f"4) 品質のブラインド推定: 提出画像 quality={est['quality']} "
          f"(真値 {BASE_Q})  読めた係数 {est['n_quantized']} 本  /  "
          f"無圧縮の対照 quality={est_clean['quality']} "
          f"(『品質 100』とは答えない)")
    assert est["quality"] == BASE_Q and est["jpeg_compressed"] is True
    assert est["table"].shape == (8, 8)
    assert est_clean["quality"] is None and est_clean["jpeg_compressed"] is False

    ela = F.error_level_map(submitted, 90)
    inside = np.zeros((N, N), bool)
    inside[SPLICE] = True
    border = ndimage.binary_dilation(inside, np.ones((9, 9))) & ~inside
    outside = ~ndimage.binary_dilation(inside, np.ones((17, 17)))
    ratio_ela = float(ela[inside].mean() / ela[outside].mean())
    print(f"   ELA(再圧縮品質 90): 貼り込み内 {ela[inside].mean():.4f} / "
          f"外 {ela[outside].mean():.4f} = {ratio_ela:.2f} 倍")
    assert ela.shape == (N, N) and 0.0 <= ela.min() and abs(ela.max() - 1.0) < 1e-12
    assert ratio_ela > 1.5
    # ELA が意味を持つのは「台紙が JPEG」のときだけ。無圧縮の台紙で比を測ると消える
    png_paste = scene.copy()
    png_paste[SPLICE] = foreign[SPLICE]
    ela_png = F.error_level_map(png_paste, 90)
    ratio_png = float(ela_png[inside].mean() / ela_png[outside].mean())
    print(f"   同じ貼り込みでも台紙が無圧縮だと {ratio_png:.2f} 倍 = 区別できない "
          f"(ELA は量子化履歴を比べているのであって、高周波を見ているのではない)")
    assert ratio_png < 1.5 < ratio_ela

    qs = list(range(40, 100, 5))
    ghosts = F.jpeg_ghost_map(submitted, qs, block=16)
    qmap = F.jpeg_ghost_quality(ghosts, qs)
    q_in = int(np.bincount(qmap[inside].astype(int)).argmax())
    q_out = int(np.bincount(qmap[outside].astype(int)).argmax())
    print(f"   JPEG ゴースト({len(ghosts)} 品質を掃引): 貼り込み内の最頻品質 "
          f"{q_in}(真値 {SPLICE_Q})  /  台紙側 {q_out}(真値 {BASE_Q})")
    assert len(ghosts) == len(qs) and all(g.shape == (N, N) for g in ghosts)
    assert q_in == SPLICE_Q
    assert qmap.shape == (N, N)
    # 本数がずれたら黙って答えない(添字のずれた地図は返さない)
    try:
        F.jpeg_ghost_quality(ghosts[:3], qs)
        raise AssertionError("本数不一致が通ってしまった")
    except ValueError as e:
        print(f"   本数不一致は fail-closed: {str(e).splitlines()[0][:48]}...")

    # ------------------------------------------------------------------ #
    # 5) 雑音整合性 —— 先に既知の σ で地図そのものを検算する                 #
    # ------------------------------------------------------------------ #
    r = np.random.default_rng(3)
    chart = np.full((N, N), 0.5) + 0.01 * r.standard_normal((N, N))
    chart[N // 2:] = 0.5 + 0.04 * r.standard_normal((N // 2, N))
    nm = F.noise_inconsistency_map(np.clip(chart, 0, 1), 16)
    lo = float(nm[16:96, 16:240].mean())        # 真値 0.01 * 255 = 2.55
    hi = float(nm[160:240, 16:240].mean())      # 真値 0.04 * 255 = 10.20
    print(f"5) 雑音地図の校正: 上半分 {lo:.3f}(真値 2.550) / "
          f"下半分 {hi:.3f}(真値 10.200)  比 {hi / lo:.3f}(真値 4.000)")
    assert abs(lo - 2.55) / 2.55 < 0.01 and abs(hi - 10.20) / 10.20 < 0.01
    assert abs(hi / lo - 4.0) < 0.08
    nm_sub = F.noise_inconsistency_map(submitted, 16)
    print(f"   提出画像の雑音地図: 貼り込み内 {nm_sub[inside].mean():.3f} / "
          f"外 {nm_sub[outside].mean():.3f} —— 段差はあるが、模様の濃い場所でも"
          "同じ段差が出るので、これ単独は証拠にならない")
    assert nm_sub.shape == (N, N)

    # ------------------------------------------------------------------ #
    # 6) 自己複製 —— こちらが決めたシフトを誤差 0 px で当てる                #
    # ------------------------------------------------------------------ #
    for method, step in (("keypoint", None), ("block", 2)):
        kw = {"method": method} if step is None else {"method": method, "step": step}
        found = F.copy_move_regions(submitted, **kw)
        assert len(found) == 1, (method, len(found))
        top = found[0]
        err = max(abs(top["offset"][0] - TRUE_SHIFT[0]),
                  abs(top["offset"][1] - TRUE_SHIFT[1]))
        print(f"6) コピー&ムーブ({method}): シフト {top['offset']} "
              f"(真値 {TRUE_SHIFT}、誤差 {err:.0e} px)  対応 {top['n_matches']} 個  "
              f"複製元 bbox {top['src_bbox']}  複製先 bbox {top['dst_bbox']}")
        assert err == 0.0
        sr0, sc0, sr1, sc1 = top["src_bbox"]
        dr0, dc0, dr1, dc1 = top["dst_bbox"]
        assert SRC[0] <= sr0 and sr1 <= SRC[0] + PATCH
        assert SRC[1] <= sc0 and sc1 <= SRC[1] + PATCH
        assert DST[0] <= dr0 and dr1 <= DST[0] + PATCH
        assert DST[1] <= dc0 and dc1 <= DST[1] + PATCH
        assert top["caveats"]
    # 偽陽性 0 —— 保管オリジナル(改竄していない)では 1 件も出ない
    fp_kp = F.copy_move_regions(original, method="keypoint")
    fp_blk = F.copy_move_regions(original, method="block", step=2)
    print(f"   改竄していない保管オリジナル: keypoint {len(fp_kp)} 件 / "
          f"block {len(fp_blk)} 件(偽陽性 0 が検出器の最低条件)")
    assert fp_kp == [] and fp_blk == []
    # 貼り込みの側はコピー&ムーブでは取れない。**道具ごとに見えるものが違う**
    only_splice = original.copy()
    only_splice[SPLICE] = foreign[SPLICE]
    print(f"   貼り込みだけの画像: keypoint "
          f"{len(F.copy_move_regions(only_splice, method='keypoint'))} 件 "
          f"—— 自己複製ではないので原理的に出ない(ELA/ゴーストの仕事)")
    assert F.copy_move_regions(only_splice, method="keypoint") == []

    # ------------------------------------------------------------------ #
    # 7) 出す側の対策 —— 電子透かしで「後から証明できる」ようにする          #
    # ------------------------------------------------------------------ #
    bits = np.random.default_rng(0).integers(0, 2, 128).astype(bool)
    marked = F.watermark_embed(original, bits, strength=0.1)
    got = F.watermark_extract(marked, 128)
    blind = F.watermark_extract(original, 128)          # 透かしの無い画像から
    print(f"7) 透かし: 埋めた 128 bit → 抽出のハミング距離 {F.hash_distance(bits, got)} "
          f"(BER {F.hash_distance(bits, got) / 128:.1%})  /  未署名の画像から読むと "
          f"{F.hash_distance(bits, blind)} bit = 乱数と同じ")
    assert got.dtype == np.bool_ and got.shape == (128,)
    assert F.hash_distance(bits, got) == 0
    assert F.hash_distance(bits, blind) > 40
    assert marked.shape == original.shape

    cap = F.watermark_capacity(original, bits, jpeg_quality=75)
    print(f"   容量 {cap['capacity_bits']} bit(LL {cap['ll_shape']})  強度→画質/誤り:")
    for row in cap["rows"]:
        print(f"     強度 {row['strength']:.2f}  PSNR {row['psnr_db']:5.2f} dB  "
              f"BER {row['ber']:.3f}  JPEG q75 後の BER {row['ber_jpeg']:.4f}")
    psnr = [r["psnr_db"] for r in cap["rows"]]
    assert psnr == sorted(psnr, reverse=True)           # 強度↑ で画質は単調に↓
    assert all(r["ber"] == 0.0 for r in cap["rows"])    # 無攻撃なら誤り 0
    weak = cap["rows"][0]["ber_jpeg"]
    strong = cap["rows"][-1]["ber_jpeg"]
    print(f"   → 弱い透かし(強度 {cap['rows'][0]['strength']})は JPEG で "
          f"{weak:.1%} が化け、強い透かし(強度 {cap['rows'][-1]['strength']})は "
          f"{strong:.1%}。これが『目立たなさ』と『頑健さ』の取引の実体")
    assert weak > strong and strong == 0.0
    # 1 px ずらすだけで壊れる = 幾何変形には無力(隠さずに数で残す)
    shifted = F.watermark_extract(np.roll(marked, 1, axis=1), 128)
    print(f"   1 px ずらすと {F.hash_distance(bits, shifted)} bit が化ける "
          f"(ブロック位置がずれる。切り抜き・回転には効かない)")
    assert F.hash_distance(bits, shifted) > 10

    print("PASS: imgforensics 16 op —— 既知のシフト (110, 128) を誤差 0 px、"
          "貼り込みの真の品質 60、台紙の真の品質 90、透かし BER 0 で当て、"
          "破綻点(ハッシュは局所改竄に無力 / ELA は無圧縮台紙で無効 / "
          "透かしは 1 px のずれで壊れる)も同じ数で示した")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
