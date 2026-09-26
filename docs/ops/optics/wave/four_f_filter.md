---
op: four_f_filter
dim: optics
category: wave
in: cimage × cimage
out: cimage
examples: [optics_four_f_processor]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# four_f_filter — OPTICS `wave` op

- **データ種**: `cimage × cimage` → `cimage`
- **呼び出し**: `import fullseye as fs; fs.ledger.four_f_filter(field, transfer, invert=True)` (実装を直接呼ぶなら `import optics; optics.four_f_filter(field, transfer, invert=True)`、台帳から引くなら `opsoptics.get("four_f_filter")`)

## 使い方

4f 光学プロセッサ: 2 枚のレンズとフーリエ面のフィルタを通した出力。

入力面 → レンズ 1 → **フーリエ面**(``transfer`` を掛ける)→ レンズ 2 →
出力面。スカラ回折の理想 4f 系では出力は

    ``out(x, y) = (u * h)(-x, -y)``

—— 畳み込みに**座標反転**が付く。2 枚のレンズがそれぞれ*前向きの*フーリエ
変換を行い、``F{F{u}}(x) = u(-x)`` だからである。「フーリエ面で掛けるだけ」
の計算と実物の 4f 系はここが違うので、反転は既定で**する**。

離散でもこの反転は厳密で、添字の写像 ``n -> (-n) mod N`` になる
(``np.roll(a[::-1], 1)``)。反転そのものは添字の入れ替えなので誤差を持たない
—— 残る誤差は FFT の往復が乗せる 1e-16 台だけである(``transfer`` を 1 に
した実測で最大絶対差 3.4e-16)。

*invert* を ``False`` にすると反転を省く(フィルタ後の場を**入力座標のまま**
見たいとき。物理の 4f 系ではないので、既定にはしない)。

真値(この op が再現するもの):

* ``identity`` フィルタ → 入力の 180 度回転に一致(実測 3.4e-16)。
* ``block`` フィルタ → 厳密にゼロ。
* ``derivative_x`` order=n → *n* 階の空間微分。ガウシアン(w=8, 64x64)で
  1 階 5.8e-08 / 2 階 5.4e-08 の相対誤差 —— **1e-16 にならない**のは
  ガウシアンが厳密に帯域制限されていないから(打ち切りの分)。
* 線形性 ``4f(a*u1 + b*u2) = a*4f(u1) + b*4f(u2)``。
* 合成 ``4f(4f(u, H1), H2)`` = ``4f(u, H1*H2)``(反転を 2 回かけた分だけずれる
  ので、合成を試すときは *invert* を ``False`` にする)。
* ``|H| = 1`` のフィルタは総パワーを保つ(Parseval)。

**Raises** ``ValueError``: *field* / *transfer* が 2-D でない、形が違う、
2x2 未満、:data:`MAX_FIELD_ELEMENTS` 超、非有限、マスク付き。

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

[angular_spectrum_propagate](angular_spectrum_propagate.md) · [jones_apply](../polarization/jones_apply.md)

## 同カテゴリ(`wave`)

[airy_pattern](airy_pattern.md) · [angular_spectrum_propagate](angular_spectrum_propagate.md) · [fraunhofer_pattern](fraunhofer_pattern.md) · [fourier_plane_filter](fourier_plane_filter.md) · [gaussian_beam](gaussian_beam.md) · [defocus_from_shift](defocus_from_shift.md) · [pupil_psf](pupil_psf.md) · [pupil_blur](pupil_blur.md)

---
*Provenance: optics.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
