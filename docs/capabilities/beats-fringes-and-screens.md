---
id: beats-fringes-and-screens
title: うなりは一つ(膜のモード・干渉縞・回折次数・印刷のモアレ・墨に落とす)
title_en: One beat (membrane modes, fringes, diffraction orders, print moire, and turning tone into ink)
category: 波と信号
ops: [wave_membrane_mode, wave_mode_frequencies, wave_nodal_lines, wave_two_slit, wave_fringe_period, wave_grating_orders, halftone_screen, halftone_moire_period, engrave_lines, hatch_field, mosaic_tiles_sites, mosaic_tiles_render]
examples: [poc_beats_fringes_and_screens]
version: 0.2.4
---

# うなりは一つ(膜のモード・干渉縞・回折次数・印刷のモアレ・墨に落とす)

## できること

膜の固有モードと節線、二重スリットの干渉縞、回折格子の次数、そして印刷の網点・モアレ・彫版線・ハッチ・モザイクを作り、**どれも絵の外にある真値で採点します**。

二重スリットの縞と、2 版を重ねた網点のモアレは教科書では別の章に載っていますが、**どちらも「2 つの周期構造の周波数ベクトルの差」**であって式は 1 本しかありません。この層はその 1 本を両側から確かめます(実測):

- ★**矩形膜の固有値は `π²(m²/a² + n²/b²)`** —— 正方膜の 8 モードが**最大差 0.00e+00** で一致します。よく書かれる `mnπ` は**積**の式で別物です: (1,1) と (2,2) の比だけでは区別できませんが、**縮退の重複**(正方膜で 5 が 2 回・10 が 2 回)まで見ると完全に分かれます。節線の本数 `m−1` / `n−1` は整数なので丸めの余地がありません。
- ★**クラドニ図形は「板」ではなく膜の解です** —— よく見る `cos·cos − cos·cos` はヘルムホルツ方程式 + 境界条件の**膜**のモードで、実際のクラドニ板は**重調和方程式**に従う別物です。砂が節線に集まる絵は同じでも周波数比は合いません。ここでは膜と明記し、膜の真値だけで採点します。
- ★**円膜の節円は `J₀` の零点 / k** にあります(自由端の量子化を決めるのは `J′₀` の零点で、そちらは**腹**の位置)。取り違えると op が誤っているように見えます —— 実際に一度読み違えました。
- ★**縞間隔 `λD/d`** —— 作る op(`wave_two_slit`)と測る op(`wave_fringe_period`)を**分けてある**ので、使った式で答え合わせになりません。波長・分離・距離を振った 4 設定すべてで比 0.998〜1.003。縞が 3 本入らない設定は黙って「1 本の縞」を返さず拒みます。
- ★**既存 op との往復** —— `wave_grating_orders` の次数を既存 `grating_wavelengths` に逆算させると **550.000000 nm** に戻ります。伝播しない次数(`|sinθ| > 1`)は角度を捏造せず `propagates=False` で返します。さらに既存 `fraunhofer_pattern`(数値で解いた遠視野)と突き合わせると、デューティ 50 % の矩形格子では**偶数次が消え**(矩形波のフーリエ係数が偶数調波で 0)、3 次 / 1 次の強度比は `sinc(m/2)²` の 1/9(実測 0.1140)。
- ★★**モアレの周期は描く前に分かります** —— 閉形式で出してから、重ねた絵の 2-D FFT で測り返して比 0.948〜0.986。同じ線数なら周期は `1 / (2 f sin(Δ/2))` で、45° 対 75° は閉形式と 1e-6 未満まで一致します。同じスクリーン同士は `inf` を返さず拒みます。
- ★**測るときに探す範囲を切ります** —— うなりは**低周波**側にあるので `f_max` を渡さないと**スクリーン自身の山**(どの角度でも 16.7 px = 1/f)を拾い、「予言と全然合わない」と読めます。逆にハッチの線は**高周波**側なので `f_min` を渡さないと濃淡の包絡(元の絵と同じ周期)を拾って 90° ずれて見えます。どちらも一度読み違えました。
- ★**網点が捨てるもの・保つもの** —— 捨てたのは階調で、**保ったのは局所の平均濃度**です。網点 4 周期の窓で平均すると元の濃淡に戻り、平均絶対差 0.0517。
- ★**彫版線のインク率は `w/d` の閉形式** —— 濃淡 0.2 / 0.4 / 0.6 / 0.8 の 4 段すべてで**差 0.0000**。
- ★**ハッチの向きは既存 `structure_tensor_orientation` が決めます**(この層は構造テンソルを再実装しません)。向きが構成で分かっている縞(0°/30°/60°/135°)で 0.0〜0.3° のずれ、線の間隔は指定 8 px に対し 7.87〜8.00 px。
- ★**Lloyd のエネルギーは既存 `stipple_energy` が測って単調減少** —— 反復 0 → 16 で 2,782,566 → 1,491,442。セル平均は L2 最適で、セル 10 個を全数走査して反例 0 件。

★**絵の良さではなく、保った量と捨てた量を数で言う**のがこの層の主張です。既存の NPR ライブラリは絵しか返しません —— 差はそこにあります。

## What it does

Build membrane eigenmodes and nodal lines, two-slit fringes, grating orders, and the printing side (halftone screens, moire, engraving lines, structure-following hatching, mosaic tiles) — and score every one of them against a truth that lives outside the picture. The thesis: a two-slit fringe and the moire of two superposed halftone screens are **the same beat**, the difference of two frequency vectors, so one formula is checked from both ends. Rectangular membrane eigenvalues match `pi^2 (m^2/a^2 + n^2/b^2)` to 0.00e+00 including the degeneracies (the widely quoted `mn*pi` is a *product* and is a different sequence); circular nodal circles sit at the zeros of `J0` (the zeros of `J'0` are the antinodes); the fringe period `lambda*D/d` is measured back by a *different* op (ratio 0.998-1.003); grating orders round-trip through the existing `grating_wavelengths` to 550.000000 nm and agree with the existing `fraunhofer_pattern`, where a 50 % duty grating drops the even orders and the 3rd/1st intensity ratio is `sinc(m/2)^2` = 1/9; the moire period is predicted before drawing and confirmed by FFT (0.948-0.986); halftoning discards tone but preserves local mean density (0.0517 mean absolute error through a 4-period window); engraving ink coverage matches the closed form `w/d` to 0.0000; hatch direction comes from the existing `structure_tensor_orientation` and lands within 0.3 degrees of a grating whose angle is known by construction; and Lloyd's energy, measured by the existing `stipple_energy`, decreases monotonically with the cell mean being the exact L2 optimum.

## 向くところ / 向かないところ

**向く**: 印刷・製版の設計(スクリーン角度の組み合わせを**刷る前に**決める)。光学の教材図版を採点つきで作る。干渉計・格子分光器の設計の当たりを取る(次数と角度)。写真を墨に落とす様式化で「どれだけ濃度を保ったか」を数で言う。ペンプロッタ・レーザー彫刻の線の設計(被覆率が閉形式で解ける)。

**向かない**: **クラドニ板そのものは扱えません**(膜の解であって板の重調和解ではない)。`wave_two_slit` はフラウンホーファー領域の遠視野で、近接場やフレネル領域は既存 `angular_spectrum_propagate` の仕事です。膜のモードは矩形と円の**解析解だけ**で、任意形状の固有値は解きません。`wave_fringe_period` は**1 本の支配的な周期**を返すので、複数の周期が重なった像では最大の山しか見ません。モアレの予言は**同じ形のスクリーン 2 枚**の場合で、3 版以上や点形状の違いによる 2 次のうなりは入りません。網点・彫版・ハッチはすべて**閾値で墨に落とす**ので、出力は 2 値に近い `image2d` であって連続階調ではありません。`hatch_field` は画素ごとに 1 つの向きしか持てないため、交差や分岐(構造テンソルが等方になる所)では向きが任意になります —— そこを信じてよいかを言うのは向きではなく**コヒーレンス**(既存 `structure_tensor_coherence`)です。モザイクの母点は Lloyd 反復なので**局所最適**に落ちます(反復を増やしても大域最適は保証しません)。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

# 刷る前にモアレの周期が分かる(2 版の周波数ベクトルの差)
p = fs.ledger.halftone_moire_period(lpi_a=60.0, angle_a_deg=45.0,
                                    lpi_b=60.0, angle_b_deg=75.0, pixel_um=25.4)
print("モアレの周期 %.2f px / 向き %.1f 度" % (p["period_px"][0], p["angle_deg"][0]))

# 縞間隔は作った op とは別の op が測り返す
img = fs.wave_two_slit(wavelength_nm=550.0, slit_sep_um=200.0,
                       distance_mm=200.0, shape=(64, 1024), pixel_um=5.0)
print("縞間隔 実測 %.2f px / lambda*D/d = %.2f px"
      % (fs.wave_fringe_period(img), 0.55 * 200e3 / (200.0 * 5.0)))

# 膜の固有値は平方和(積の mn*pi ではない)
print("正方膜 lambda/pi^2 =",
      np.round(fs.wave_mode_frequencies("rectangular", 8, 1.0) / np.pi ** 2, 4))
```

## 裏づけ

- op: `wave_membrane_mode` / `wave_mode_frequencies` / `wave_nodal_lines` / `wave_two_slit` / `wave_fringe_period` / `wave_grating_orders` / `halftone_screen` / `halftone_moire_period` / `engrave_lines` / `hatch_field` / `mosaic_tiles_sites` / `mosaic_tiles_render`
- 例: [`poc_beats_fringes_and_screens`](../../examples/poc_beats_fringes_and_screens.py)
- 既存 op と組む: `grating_wavelengths`(次数の逆算)・`fraunhofer_pattern`(数値で解いた遠視野)・`structure_tensor_orientation`(ハッチの向き)・`structure_tensor_coherence`(その向きを信じてよいか)・`stipple_energy`(Lloyd の単調減少)・`stipple_points_from_image` と `stroke_tour_closed`(墨を 1 本の線に)
- 先行: E. Chladni, *Entdeckungen über die Theorie des Klanges* (1787) —— ただし砂の図は板であってここで解くのは膜; Lord Rayleigh, *The Theory of Sound* (1877) の膜の固有値; T. Young (1804) の二重スリット; B. Oztan, G. Sharma, R. P. Loce, "Misregistration sensitivity in clustered-dot color halftones", *J. Electronic Imaging* 17 (2008) のモアレのベクトル解析; A. Secord, "Weighted Voronoi stippling", *NPAR 2002*; S. Lloyd, "Least squares quantization in PCM", *IEEE Trans. Inf. Theory* 28 (1982); A. Gersho, "Asymptotically optimal block quantization", *IEEE Trans. Inf. Theory* 25 (1979)。
