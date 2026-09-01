---
guide: gallery2d_gray_arith
dim: 2d
title: 濃淡・階調・算術・定義域 — 使い方ガイド
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.0
---

# 濃淡・階調・算術・定義域 — 使い方ガイド

## この族は何をする道具箱か

画像の「明るさ・コントラスト・階調(トーン)」そのものを作り替える、**1 枚 → 1 枚**の単項変換をまとめた族です。入力はいずれも 2-D の濃淡画像(`float64`, おおむね `[0,1]`)で、出力も同じ形の濃淡画像です(この族は**形状を保存**します)。中身は大きく 4 系統に分かれます。

- **階調曲線(gray / intensity-transform)**: ガンマ・反転・シグモイド・ヒストグラム平坦化・CLAHE など、画素値を写す「トーンカーブ」。露出やコントラストを整える。
- **画素算術(arithmetic)**: `sqrt` / `log` / `exp` / `sin`・`cos` など、画素値そのものに数学関数を掛けるポイント演算。ダイナミックレンジの圧縮・伸張や非線形強調に使う。
- **ビット面・量子化(gray)**: 8-bit 量子化を介したビットシフト・ビットマスク・ビット面抽出・階調数削減。
- **定義域 domain(domain)**: 画像の有効領域(HALCON でいう Region of Definition)を切り出す/広げる。

呼び出しは 1 枚の画像に 2 つのスカラつまみ `a, b ∈ [0,1]` を添える形に統一されています。`fullseye.apply(img, "op名", a, b)` で 1 op、`fullseye.run_pipeline(img, [...])` で連鎖できます。多くの op は `a` を主効き(ガンマ量・閾値・平坦化の局所ブロック数など)、`b` を副次(バイアス・ピボットなど)に割り当てます。`a`/`b` を無視する op もあります(各 op 行に明記)。

## 代表的なパイプライン(op の繋がり)

この族は「トーンを整える前処理」として、後段の segmentation / edges と繋がります。族内は「点変換 → コントラスト強調 → 反転/量子化」と重ねるのが典型です。

```mermaid
flowchart LR
    IMG[濃淡画像 image] --> STRETCH[scale_clip<br/>コントラスト伸張]
    STRETCH --> TONE[gamma / sk_adjust_log<br/>暗部を持ち上げ]
    TONE --> EQ[equ_histo_image / clahe<br/>ヒストグラム平坦化]
    EQ --> OUT[整えた image]
    OUT -.後段.-> SEG[（別族）threshold / canny]
```

```mermaid
flowchart LR
    IMG[濃淡画像 image] --> ARI[log_image / sqrt_image<br/>レンジ圧縮]
    ARI --> INV[invert<br/>1 - x]
    INV --> BIT[it_convert_image_type<br/>階調数削減]
    BIT --> DOM[it_crop_domain<br/>中央窓を残す]
    DOM --> OUT[image]
```

## 使い方(op グループ別)

各 op は「op名 — 何をするか — 呼び出し例」の 1 行。効果は実装で確認済み。挙動が実装依存で微妙なものは型契約(image→image)+サンプル参照に留めます。HALCON 別名がある場合は文末に併記。

### A. 階調曲線・点 LUT(トーンカーブ)
- `gamma` — ガンマ補正 `x**(0.3+2.5a)`。`a` 小=暗部を持ち上げ、`a` 大=暗く締める(HALCON `pow_image`)。`fullseye.apply(img, "gamma", 0.7, 0.0)`
- `gamma_image` — 同じくガンマ LUT(HALCON `gamma_image`)。`fullseye.apply(img, "gamma_image", 0.6, 0.5)`
- `pow_image` — ガンマ(べき)LUT(HALCON `pow_image`)。`fullseye.apply(img, "pow_image", 0.5, 0.5)`
- `invert` — 点反転 `1 - x`(ネガ化, HALCON `invert_image`)。`fullseye.apply(img, "invert", 0.5, 0.5)`
- `invert_image` — 反転 `1 - x`(HALCON `invert_image`)。`fullseye.apply(img, "invert_image", 0.5, 0.5)`
- `bit_not` — ビット反転。強度画像では `invert` と同じ `1 - x`(HALCON `bit_not`)。`fullseye.apply(img, "bit_not", 0.5, 0.5)`
- `scale_clip` — アフィン `clip((0.5+1.5a)x + (b-0.5), 0, 1)`。`a`=ゲイン(コントラスト)、`b`=バイアス(明るさ)。飽和で実質フルレンジ化(HALCON `scale_image`)。`fullseye.apply(img, "scale_clip", 0.6, 0.5)`
- `scale_image` — `scale_clip` と同じアフィン+クリップ(HALCON `scale_image`)。`fullseye.apply(img, "scale_image", 0.6, 0.5)`
- `sigmoid` — S 字トーンカーブ `1/(1+e^{-(4+12a)(x-(0.2+0.6b))})`。`a`=傾き、`b`=しきい(ピボット)(HALCON 近縁 `scale_image_max`)。`fullseye.apply(img, "sigmoid", 0.5, 0.5)`
- `illuminate` — アンシャープ的な局所コントラスト強調 `x + k(x - blur(x))`。`a`=平滑スケール、`b`=強さ(HALCON `illuminate`)。`fullseye.apply(img, "illuminate", 0.4, 0.6)`
- `f2_lut_trans` — 単調シグモイド LUT(端点を [0,1] へ正規化)を 8-bit 量子化値に table lookup。`a`=ゲイン、`b`=ピボット(HALCON `lut_trans`)。`fullseye.apply(img, "f2_lut_trans", 0.5, 0.5)`
- `cv_trunc` — 閾値での頭刈り `min(x, a)`(飽和した明部を平らに)。`a`=閾値、`b`=無視(HALCON 近縁 `scale_image`)。`fullseye.apply(img, "cv_trunc", 0.5, 0.5)`

### B. ヒストグラム平坦化・局所コントラスト
- `equalize` — ヒストグラム平坦化(CDF を LUT に)。順位を保ちコントラストを均す(HALCON `equ_histo_image`)。`fullseye.apply(img, "equalize", 0.5, 0.5)`
- `equ_histo_image` — 大域ヒストグラム平坦化(HALCON `equ_histo_image`)。`fullseye.apply(img, "equ_histo_image", 0.5, 0.5)`
- `equ_histo_image_rect` — 矩形ブロックごとの局所ヒストグラム平坦化。`a`=ブロック分割数(HALCON `equ_histo_image_rect`)。`fullseye.apply(img, "equ_histo_image_rect", 0.5, 0.5)`
- `clahe` — タイル分割の適応平坦化 + **contrast limit**。各タイルの CDF を近傍 4 タイル中心で**双線形ブレンド**するのでタイル継ぎ目は出ない(Zuiderveld 1994 の標準補間。2026-08-30 に補間を追加)。`a`=タイル数 `2+int(3a)`、`b`=**clip limit**(ビン平均カウントに対する倍率 `256**b`。`b=0` → 1 倍 = 強調ゼロ、`b=1` → 256 倍 = 切り取り無効 = 素の AHE、OpenCV の既定 `clipLimit=40` ≈ `b=0.665`)。切り取った分は全ビンへ均等に配り直す。`fullseye.apply(img, "clahe", 0.5, 0.5)`  
  <br>★2026-09-02 まで `b` は **完全に死んで**おり(`b=0` と `b=1` の出力差がきっかり 0.0)、clip limit が無い以上 **実装は AHE であって CLAHE ではなかった**。`b=1` は旧実装とビット一致する端に選んである。
- `cv_clahe` — OpenCV CLAHE。`a`=clipLimit。`fullseye.apply(img, "cv_clahe", 0.5, 0.5)`
- `sk_adapthist` — skimage の適応ヒストグラム平坦化(CLAHE)。`a`=clip_limit。`fullseye.apply(img, "sk_adapthist", 0.5, 0.5)`
- `xkor_clahe` — kornia の CLAHE。`a`=clip_limit。`fullseye.apply(img, "xkor_clahe", 0.5, 0.5)`
- `scale_image_max` — 最小-最大伸張でフルレンジ [0,1] へ(`(x-lo)/(hi-lo)`, HALCON `scale_image_max`)。`fullseye.apply(img, "scale_image_max", 0.5, 0.5)`
- `sk_autolevel` — 局所(円板近傍)オートレベル。近傍の min-max で伸張(HALCON 近縁 `scale_image_max`)。`fullseye.apply(img, "sk_autolevel", 0.5, 0.5)`
- `sk_enhance_contrast` — 局所コントラスト強調(近傍 min/max のうち近い方へ寄せる)。`a`=近傍半径。`fullseye.apply(img, "sk_enhance_contrast", 0.5, 0.5)`
- `xpil_autocontrast` — PIL autocontrast(端を cutoff して伸張)。`a`=cutoff%。`fullseye.apply(img, "xpil_autocontrast", 0.2, 0.0)`
- `xpil_contrast` — 画像平均まわりのコントラスト調整(PIL `ImageEnhance.Contrast`)。`a`=係数。`fullseye.apply(img, "xpil_contrast", 0.7, 0.0)`
- `xsk3_rank_equalize` — 局所(円板)ランク平坦化。`a`=近傍半径。`fullseye.apply(img, "xsk3_rank_equalize", 0.5, 0.5)`
- `xsk3_rank_subtract_mean` — 近傍平均を引く局所コントラスト(平坦化/ハイパス的)。`a`=近傍半径。`fullseye.apply(img, "xsk3_rank_subtract_mean", 0.5, 0.5)`
- `monotony` — 各画素を 8 近傍中でのランク(自分より小さい隣接の割合 /8)に置換する局所順位変換(HALCON `monotony`)。`fullseye.apply(img, "monotony", 0.5, 0.5)`

### C. 画素算術(数学関数のポイント演算)
- `abs_image` — 絶対値 `|x|`(HALCON `abs_image`)。`fullseye.apply(img, "abs_image", 0.5, 0.5)`
- `sqrt_image` — 平方根 `sqrt(x)`。暗部を持ち上げレンジ圧縮(HALCON `sqrt_image`)。`fullseye.apply(img, "sqrt_image", 0.5, 0.5)`
- `exp_image` — 指数 `(e^x - 1)/(e - 1)`([0,1] 正規化, HALCON `exp_image`)。`fullseye.apply(img, "exp_image", 0.5, 0.5)`
- `log_image` — 対数 `log2(1 + x)`。ダイナミックレンジ圧縮(HALCON `log_image`)。`fullseye.apply(img, "log_image", 0.5, 0.5)`
- `sk_adjust_log` — 対数補正(暗部を持ち上げ全体を明るく)。`a`=gain(HALCON `log_image`)。`fullseye.apply(img, "sk_adjust_log", 0.5, 0.5)`
- `sin_image` — 正弦 `(sin(2πx)+1)/2`([0,1] 化, HALCON `sin_image`)。`fullseye.apply(img, "sin_image", 0.5, 0.5)`
- `cos_image` — 余弦 `(cos(2πx)+1)/2`(HALCON `cos_image`)。`fullseye.apply(img, "cos_image", 0.5, 0.5)`
- `tan_image` — 中間調まわりの急峻な S 字(`tan((x-0.5)·0.9π)` を [0,1] へ, HALCON `tan_image`)。`fullseye.apply(img, "tan_image", 0.5, 0.5)`
- 他(逆三角の [0,1] 正規化, いずれも点変換): `asin_image`=`arcsin(x)/(π/2)`、`acos_image`=`arccos(x)/π`(単調減少)、`atan_image`=`arctan(x)/(π/2)`。例: `fullseye.apply(img, "atan_image", 0.5, 0.5)`

### D. ビット面・量子化・型変換
- `it_bit_lshift` — 8-bit 量子化して左シフト `round(7a)` ビット(8-bit マスクで wrap, HALCON `bit_lshift`)。`fullseye.apply(img, "it_bit_lshift", 0.3, 0.0)`
- `it_bit_rshift` — 8-bit 量子化して右シフト `round(7a)`(= `2**shift` で整数除算 → 粗く・暗く, HALCON `bit_rshift`)。`fullseye.apply(img, "it_bit_rshift", 0.5, 0.0)`
- `it_bit_mask` — 定数マスク `round(255a)` と 8-bit AND(下位ビットを落とす, HALCON `bit_mask`)。`fullseye.apply(img, "it_bit_mask", 0.75, 0.0)`
- `f2_bit_slice` — 8-bit 量子化後の 1 ビット面を抽出({0,1} 画像)。`a`=面(0=LSB..7=MSB, HALCON `bit_slice`)。`fullseye.apply(img, "f2_bit_slice", 1.0, 0.0)`
- `it_convert_image_type` — `round(2+254a)` レベルへ均等量子化(ビット深度削減/ポスタライズ, HALCON `convert_image_type`)。`fullseye.apply(img, "it_convert_image_type", 0.1, 0.0)`
- `xpil_posterize` — PIL posterize(`1+6a` ビットへ階調削減)。`fullseye.apply(img, "xpil_posterize", 0.3, 0.0)`
- `xpil_solarize` — PIL solarize(閾値 `64+160a` を超える画素を反転)。`fullseye.apply(img, "xpil_solarize", 0.5, 0.0)`

### E. 定義域(domain)・境界
- `it_full_domain` — 定義域を全矩形に拡張。素の numpy 配列は既に全域なので恒等(`a`/`b` 無視, HALCON `full_domain` 相当)。`fullseye.apply(img, "it_full_domain", 0.5, 0.5)`
- `it_crop_domain` — 定義域を中央 `a` 窓に制限し、窓外を 0 に(HALCON `crop_domain`)。`fullseye.apply(img, "it_crop_domain", 0.6, 0.0)`
- `f2_expand_domain` — 有効域(非ゼロ)を最近傍グレー値で外側へ `1..7` px 拡張。`a`=マージン幅(HALCON `expand_domain_gray`)。`fullseye.apply(img, "f2_expand_domain", 0.4, 0.0)`

### F. 詳細強調・平坦化(拡張バックエンド)
- `xcv_detail_enhance` — OpenCV `detailEnhance`(エッジ保存の局所詳細強調)。`a`=sigma_s, `b`=sigma_r。`fullseye.apply(img, "xcv_detail_enhance", 0.5, 0.5)`
- `xpil_detail` — PIL DETAIL フィルタ(軽い先鋭化)。`fullseye.apply(img, "xpil_detail", 0.5, 0.5)`
- `xpil_edge_enhance` — PIL EDGE_ENHANCE_MORE(エッジ強調)。`fullseye.apply(img, "xpil_edge_enhance", 0.5, 0.5)`
- `xmh_soft` — mahotas ソフト閾値(小振幅を抑える収縮, `a`=閾値)。`fullseye.apply(img, "xmh_soft", 0.3, 0.0)`
- `xsp_detrend_flatten` — 行方向・列方向に線形トレンド除去(平面照明ムラの平坦化)、[0,1] へ再正規化。`fullseye.apply(img, "xsp_detrend_flatten", 0.5, 0.5)`
- `xsk3_integral_image` — 積分画像(各画素=左上からの累積和)を max 正規化。前置平滑・高速ボックス統計の基礎。`fullseye.apply(img, "xsk3_integral_image", 0.5, 0.5)`

> 注: この族の全 op は `in_sort=image → out_sort=image`。有限・非負・形状保存・決定的(同一入力→ビット同一出力)は `examples/gallery2d_gray_arith.py` が全 op について機械検証しています。

## 動く最小例(検証済み gallery2d_gray_arith から)

`examples/gallery2d_gray_arith.py` の代表 op に課した強い GT(単に「動く」でなく beat-the-null)を、`fullseye.apply` ファサードで最短化したもの。repo 直下で `py -3.11` 実行可。

```python
# repo 直下で: py -3.11 this_snippet.py
import numpy as np
import fullseye

# --- 検証済みの代表画像(勾配 + 円板 + 市松 + 微小ノイズ, 決定的) ---
n = 48
rng = np.random.default_rng(20260812)
yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
grad = xx / (n - 1)
disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
img = np.clip(0.35 * grad + 0.45 * disk + checker + 0.03 * rng.standard_normal((n, n)), 0, 1)

# 1) invert: 点反転 1 - x（null=恒等コピーは +1 相関、反転は -1）
o = np.asarray(fullseye.apply(img, "invert", 0.5, 0.5))
assert np.allclose(o, 1.0 - img, atol=1e-9)
assert np.corrcoef(o.ravel(), img.ravel())[0, 1] < -0.99

# 2) cv_trunc: 頭刈り min(x, a)（値を増やさない・実際に刈る）
o = np.asarray(fullseye.apply(img, "cv_trunc", 0.5, 0.5))
assert np.all(o <= img + 1e-9)
assert float(o.max()) < float(img.max()) - 0.05

# 3) equ_histo_image: ヒストグラム平坦化 = 単調 + コントラスト増
o = np.asarray(fullseye.apply(img, "equ_histo_image", 0.5, 0.5))
order = np.argsort(img, axis=None, kind="stable")
assert np.all(np.diff(o.ravel()[order]) >= -1e-9)          # 順位保存
assert o.std() > 1.2 * img.std()                            # コントラスト増

# 4) scale_clip: アフィン伸張 → フルレンジ [0,1]
o = np.asarray(fullseye.apply(img, "scale_clip", 0.5, 0.5))
assert o.min() < 0.01 and o.max() > 0.99

# 5) it_bit_rshift: 右シフトは暗くする（平均が半減未満）
o = np.asarray(fullseye.apply(img, "it_bit_rshift", 0.5, 0.5))
assert np.all(o <= img + 1e-9) and o.mean() < 0.5 * img.mean()

# 6) 連鎖: 伸張 → 平坦化 → 反転（image を保つ）
o = np.asarray(fullseye.run_pipeline(
    img, [("scale_clip", 0.5, 0.5), ("equ_histo_image", 0.5, 0.5), ("invert", 0.5, 0.5)]))
assert o.shape == img.shape and np.isfinite(o).all()

print("PASS")
```

## 数式(必要な op のみ)

いずれも点変換(画素 $r\in[0,1]$ → 出力 $s$)。つまみ `a,b` は上の各 op 行の割当。

- ガンマ(`gamma`/`gamma_image`/`pow_image`): $s = r^{\gamma},\quad \gamma = 0.3 + 2.5a$
- 反転(`invert`/`invert_image`/`bit_not`): $s = 1 - r$
- アフィン伸張(`scale_clip`/`scale_image`): $s = \mathrm{clip}\big((0.5+1.5a)\,r + (b-0.5),\ 0,\ 1\big)$
- シグモイド(`sigmoid`): $s = \dfrac{1}{1 + e^{-(4+12a)\,(r-(0.2+0.6b))}}$
- 対数 / 指数(`log_image` / `exp_image`): $s = \log_2(1+r)\ \ /\ \ s = \dfrac{e^{r}-1}{e-1}$
- ヒストグラム平坦化(`equalize`/`equ_histo_image`): $s = \mathrm{CDF}(r),\quad \mathrm{CDF}(r) = \frac{1}{N}\sum_{i \le r} h(i)$
- 最小-最大伸張(`scale_image_max`): $s = \dfrac{r - r_{\min}}{r_{\max} - r_{\min}}$
- 局所順位(`monotony`): $\displaystyle s(p) = \frac{1}{8}\sum_{q\in \mathcal{N}_8(p)} \mathbf{1}\!\left[\,I(q) < I(p)\,\right]$
- ビット面抽出(`f2_bit_slice`): $b_k(p) = \big(\lfloor 255\,I(p)\rceil \gg k\big)\ \&\ 1,\quad k = \mathrm{round}(7a)$

## サンプルデータ

デバッグには `../../SAMPLES.md` の 2-D 画像源が使えます。低コントラストの `coins` や文書画像 `page` はヒストグラム平坦化・オートレベルの効き確認に、`camera` は階調曲線(ガンマ/シグモイド)の見た目確認に向きます。合成の `gradient` / `checker_noisy` は本ガイドの最小例と同系で、伸張・反転・ビット面の GT を数値で確かめやすい入力です(`import sample_images; sample_images.load("coins")`)。

## 参考文献(正典)

台帳 `../../../REFERENCES.md` に準拠。この族のアルゴリズムの古典:

- Gonzalez, R.C. & Woods, R.E. (2018). *Digital Image Processing* (4th ed.) — intensity transformations（ガンマ・反転・アフィン伸張・シグモイド・ヒストグラム平坦化・ビット面スライス・対数/指数変換の標準テキスト）.
- Pizer, S.M., et al. (1987). "Adaptive Histogram Equalization and Its Variations." *Computer Vision, Graphics, and Image Processing*, 39(3), 355–368.
- Zuiderveld, K. (1994). "Contrast Limited Adaptive Histogram Equalization." *Graphics Gems IV*, Academic Press（CLAHE）.
- Zabih, R. & Woodfill, J. (1994). "Non-parametric Local Transforms for Computing Visual Correspondence." *ECCV*（局所順位/ランク変換 = `monotony` の系譜）.

---
© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
