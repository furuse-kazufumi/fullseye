---
op: fourier_plane_filter
dim: optics
category: wave
in: 
out: cimage
examples: [optics_four_f_processor]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# fourier_plane_filter — OPTICS `wave` op

- **データ種**: `なし` → `cimage`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.fourier_plane_filter(size=64, kind='derivative_x', order=1, charge=1, radius_frac=0.25, pixel_pitch_um=1.0)` (実装を直接呼ぶなら `import optics; optics.fourier_plane_filter(size=64, kind='derivative_x', order=1, charge=1, radius_frac=0.25, pixel_pitch_um=1.0)`、台帳から引くなら `opsoptics.get("fourier_plane_filter")`)

## 使い方

4f 系のフーリエ面に置く複素透過関数 ``H(fx, fy)``。

返るのは ``numpy.fft.fftfreq`` の並び(**fftshift しない**)の complex128
``(size, size)`` で、:func:`four_f_filter` にそのまま渡せる。空間周波数の
単位は cycles/um(``fftfreq(size, d=pixel_pitch_um)``)。

*kind*:

``identity``
    ``H = 1``。4f 系は結像するだけ —— 出力は入力の **180 度回転**になる。
``block``
    ``H = 0``。出力は厳密にゼロ(フーリエ面を塞いだ状態)。
``derivative_x`` / ``derivative_y``
    ``H = (i*2*pi*f)**order``。出力は *order* 階の空間微分。**レンズが
    微分を計算する**のがこの 1 行で、光コンピューティングの核である。
``laplacian``
    ``H = -(2*pi)**2 * (fx**2 + fy**2)``。等方な 2 階微分。
``lowpass`` / ``highpass``
    ``|f| <= radius_frac * f_nyquist`` の円形開口(と、その補集合)。
    ``f_nyquist = 1/(2*pixel_pitch_um)``。空間フィルタリングの教科書例。
``hilbert_x``
    ``H = -i*sign(fx)``(``fx = 0`` と、偶数長のナイキストのビンは 0)。
    片側位相で縁が立つ —— シュリーレン法の数値版。★ナイキストを 0 に
    するのは、``fftfreq`` が偶数長で ``-1/2`` だけを返し対になる ``+1/2``
    が無いためで、残すと実数偶関数の出力が**奇対称を厳密に満たさない**
    (実測 1.6e-09 → 0 にして 2.3e-16)。離散ヒルベルト変換の標準的な扱い。
``vortex``
    ``H = exp(i*charge*phi)`` の渦位相板。*charge* は**位相の巻き数**で、
    フーリエ面の閉路を 1 周すると位相が厳密に ``2*pi*charge`` 進む
    —— 整数の不変量なので門にできる。★DC 項は 0 にする(``phi`` が
    原点で定義されないため)。結果として平均が落ちるので、この板は
    **等方な縁強調**(半径方向ヒルベルト変換)として働く。

真値(この op が再現するもの):

* ``identity`` は ``four_f_filter`` を通すと入力の 180 度回転に一致 —— 実測で
  最大絶対差 3.4e-16(64x64 のガウシアン、``pixel_pitch_um=1``)。**ビット一致
  ではない**: FFT の往復が 1e-16 の屑を乗せる。ゼロ距離伝搬のように
  短絡すれば厳密にできるが、それは ``identity`` だけの特別扱いになる。
* ``derivative_x`` order=1 をガウシアン ``exp(-x**2/w**2)`` に当てると
  ``-2x/w**2 * exp(-x**2/w**2)`` に一致(帯域制限の範囲で)。
* ``vortex`` の巻き数は閉路上の位相差の和を ``2*pi`` で割って厳密に *charge*。
* ``lowpass`` + ``highpass`` = ``identity``(同じ *radius_frac* で厳密に 1)。

**Raises** ``ValueError``: *kind* が上の一覧に無い / *size* が 2 未満または
:data:`MAX_GRID` 超 / *order* が 0..8 の外 / *charge* が -32..32 の外 /
*radius_frac* が 0 以下または 1 超 / *pixel_pitch_um* が非正・非有限。

## ファミリ共通の入力契約(fail-closed)

optics の全 op は入力を検証してから計算する(黙って通さない):

- **単位は引数名に埋め込む** — `_mm` / `_um` / `_deg` / `_mrad`。mm と µm の取り違えは crash ではなく「もっともらしく間違った答え」なので、名前で防ぐ。大きさから単位を推測する処理は一切しない。
- **文字列は `ValueError`** — `float('50')` は成功してしまうため、未パースの設定値が長さとして通り抜ける(実測: `thin_lens('50', '200')` がもっともらしい 66.667 mm を返していた)。bool も `True == 1` の暗黙昇格として拒否。
- **complex / masked array は `ValueError`**(実数枠のみ。虚部の無言切り捨て・マスク剥がしを拒否)。**NaN/Inf は全入力で `ValueError`**。
- **0 除算とその親戚を名指しで拒否**: 焦点距離 0・曲率半径 0・屈折率 <= 0・不透明な開口(全 0 なので正規化が 0/0)・総和 <= 0 の PSF・S0 = 0 の Stokes ベクトル・物体が前側焦点にある(像が無限遠)。
- **非有限を返すのは 2 op だけ、しかも契約として明記**: `depth_of_field` の過焦点距離以遠の `far_mm = inf`(それが過焦点距離の定義)と `gaussian_beam` のウエストでの `wavefront_radius_mm = inf`(平面波面の曲率半径)。どちらも有限の相棒(`far_is_infinite` / `curvature_per_mm`)を併せて返す。**それ以外の無言 NaN/Inf は内部で検出して `ValueError`** —「float64 が溢れた」と「答えが無限大」は別の主張なので、後者の顔で前者を返さない。
- **サイズ上限**: 生成格子は `optics.MAX_GRID`(4096)、供給された場/PSF/開口は `optics.MAX_FIELD_ELEMENTS`(2^24)、ABCD 素子列は `optics.MAX_SYSTEM_ELEMENTS`(1024)、Zernike は `MAX_ZERNIKE_TERMS`(512)/ `MAX_ZERNIKE_ORDER`(40)/ `MAX_ZERNIKE_BASIS`(2^25)。小さな引数から巨大な内部確保が起きる経路(実測: n_max=40 × 4096² で 108 GB)を fail-closed で塞ぐ。
- **物理的に不可能な状態も拒否**: 偏光度 > 1 の Stokes ベクトル、負の透過率、負の強度、n-|m| が奇数などの不正な Zernike 添字。

## 詳しい使い方ガイド

- [optics_imaging ファミリ ガイド](../guides/optics_imaging.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [optics_four_f_processor](../../../../examples/optics_four_f_processor.py) — `py -3.11 examples/optics_four_f_processor.py`

## 型が繋がる次の op(`cimage` を入力に取れる)

[angular_spectrum_propagate](angular_spectrum_propagate.md) · [four_f_filter](four_f_filter.md) · [jones_apply](../polarization/jones_apply.md)

## 同カテゴリ(`wave`)

[airy_pattern](airy_pattern.md) · [angular_spectrum_propagate](angular_spectrum_propagate.md) · [fraunhofer_pattern](fraunhofer_pattern.md) · [four_f_filter](four_f_filter.md) · [gaussian_beam](gaussian_beam.md) · [defocus_from_shift](defocus_from_shift.md) · [pupil_psf](pupil_psf.md) · [pupil_blur](pupil_blur.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
