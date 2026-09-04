---
op: aperture_photometry
dim: astrostack
category: photometry
in: image2d × keypoints
out: table
examples: [astro_stacking]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.6  # fullseye lib version this note was generated for
---

# aperture_photometry — ASTROSTACK `photometry` op

- **データ種**: `image2d × keypoints` → `table`
- **呼び出し**: `import astrostack; astrostack.aperture_photometry(image, centers, r_aperture=5.0, r_inner=8.0, r_outer=12.0, read_sigma=0.0, gain=1.0, supersample=8)` (または `opsastrostack.get("aperture_photometry")`)

## 使い方

円形開口 + 環状背景の測光(古典的な CCD 測光)。

開口内の画素は**副画素で重み付け**する(``supersample^2`` 点の標本化)ので、
半径が整数でなくても面積が階段状に飛ばない。背景は ``r_inner``〜``r_outer``
の環の**中央値**(隣の星が環に入っても引きずられない)。

フラックスは ``sum(w * (I - background))``、S/N は古典的な CCD 方程式
(Merline & Howell, *Exp. Astron.* 6, 163 (1995); Howell, *Handbook of CCD
Astronomy*)::

    SNR = F / sqrt(F/gain + A*(B/gain + read_sigma^2))

ここで ``A`` は開口の実効画素数、``B`` は背景レベル。``read_sigma=0`` かつ
``gain=1`` なら純 Poisson の ``F/sqrt(F + A*B)`` に落ちる。

Returns 各星 1 つの dict の ``list``(``table`` 語彙)。キーは ``row`` /
``col`` / ``flux`` / ``background``(1 画素あたり)/ ``area_px``(開口の実効
画素数)/ ``n_annulus`` / ``snr`` / ``flux_error`` / ``mag_instrumental``
(``-2.5 log10(flux)``、フラックスが非正なら ``nan``)。

Ground truth it reproduces(``tests/test_astrostack.py``): ノイズ無しの
ガウシアン星(フラックス 10000 e-)に対して、半径 ``r`` の開口が拾う割合は
``1 - exp(-r^2/(2 sigma^2))``。**開口を広げれば厳密に一致する** ——
``r = 8 sigma`` では sigma = 1.0 / 1.5 / 2.0 / 3.0 のどれでも
測定 10000.00000、誤差 -0.0000 %。

**小さい開口には系統的な負のずれが残る、という正直な話。** ``r = 3 sigma``
では実測が理論を下回る::

    sigma = 1.0  ->  9798.57 / 9888.91  = -0.914 %
    sigma = 1.5  ->  9850.70 / 9888.91  = -0.386 %
    sigma = 2.0  ->  9868.61 / 9888.91  = -0.205 %
    sigma = 3.0  ->  9879.86 / 9888.91  = -0.092 %

これはバグではなく**画素化そのもの**。閉形式は連続なガウシアンを円で積分した
値だが、こちらは「画素の総フラックス × 円に入る面積の割合」を足している。
開口の縁にある画素では、円の内側(中心寄り)の方が実際には明るいので、
画素平均で代表すると必ず**少なく**出る。誤差が ``sigma`` の 2 乗に反比例
して減る(1.0→3.0 で 10 倍)のがその証拠で、標本化が良くなるほど画素平均と
真の分布の差が縮む。開口を広げれば縁の画素の寄与自体が消えるので誤差も消える。

``supersample`` は**円の面積**の離散化だけを直す(実測: ``r=4.5`` で
``pi r^2`` に対し相対 1.6e-3、``r=3`` で 2.5e-4)。上のずれとは別の話で、
上げても縁の画素平均の偏りは消えない。

**Raises** ``ValueError``: 半径の順序が ``0 < r_aperture <= r_inner <
r_outer`` でない / *supersample* が 1 未満 / *gain* が非正 /
*centers* が ``(N, 2)`` でない場合。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [astro_stacking](../../../../examples/astro_stacking.py) — `py -3.11 examples/astro_stacking.py`

## 型が繋がる次の op(`table` を入力に取れる)

—

## 同カテゴリ(`photometry`)

[star_detect](star_detect.md) · [psf_fit](psf_fit.md)

---
*Provenance: astrostack.py — ASTROSTACK operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
