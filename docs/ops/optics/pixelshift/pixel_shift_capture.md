---
op: pixel_shift_capture
dim: optics
category: pixelshift
in: rgbimage × matrix
out: video
examples: [poc_pixel_shift, poc_simcal_pixel_shift]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.0  # fullseye lib version this note was generated for
---

# pixel_shift_capture — OPTICS `pixelshift` op

- **データ種**: `rgbimage × matrix` → `video`
- **呼び出し**: `import fullseye as fs; fs.ledger.pixel_shift_capture(scene, factor, shifts, pattern='RGGB', fill_factor=1.0, per_frame=False, margin=None)` (実装を直接呼ぶなら `import pixelshift; pixelshift.pixel_shift_capture(scene, factor, shifts, pattern='RGGB', fill_factor=1.0, per_frame=False, margin=None)`、台帳から引くなら `opsoptics.get("pixel_shift_capture")`)

## 使い方

シフトした撮像素子で撮る: シーンを画素の開口(正方形の箱)で**厳密に**積分し、Bayer か白黒の生の画像を返す。

*scene*: 細かく描いたシーン。``(Hs, Ws)``(白黒)か ``(Hs, Ws, 3)``(RGB)、有限の実数。1 センサ画素 = *factor* ×
*factor* 標本。``per_frame=True`` なら先頭に枚数の軸 ``(N, Hs, Ws[, 3])`` を持ち、枚ごとに違うシーン(搬送中の
ワーク・動く被写体)を撮る。
*factor*: 1 センサ画素あたりのシーンの標本数(2〜64 の整数)。Hs・Ws はその倍数。
*shifts*: ``(N, 2)`` の**実際の**シフト (dr, dc)[センサ画素] (:func:`pixel_shift_pattern` の誤差込み)。
センサが +dc 動くと、画素 (r, c) はシーンの c + dc を見る。
*pattern*: ``"RGGB"`` などの Bayer(色フィルタはセンサと一緒に動く)か ``None``(白黒。RGB のシーンなら
各画素で 3 色を取る理想センサ = 真値づくり用で、返り値は ``(N, H, W, 3)``)。
*fill_factor*: 画素の開口の一辺 / 画素の間隔(0 < f ≤ 1)。開口の MTF は ``|sinc(f · fill)|``(f は cyc/px)。

*margin*: センサの (0, 0) 画素を置くシーンの升の番号 m(整数)。``None`` なら m = ⌈max |shift|⌉(全シフトで開口が
シーンの内側に残る最小の余白)。★真値(シフト 0 の理想センサ)と比べるときは、比べる相手と同じ m を明示すること
—— シフト列が違うと既定の m が違い、同じ添字の画素がシーンの別の場所を指す。

画素 (r, c) の中心はシーンの座標(升の辺を整数にとる)で ((r + m + ½ + dr)·factor, (c + m + ½ + dc)·factor)。
返す画像は H = Hs/factor − 2m、W = Ws/factor − 2m。
積分は面積の総和表の双線形補間で行い、シーンを「升ごとに一定」とみなす限り誤差は丸めだけ(テストで 1e-12)。

返り値 ``(N, H, W)`` float64(Bayer か白黒)/ ``(N, H, W, 3)``(pattern=None で RGB のシーン)。雑音は足さない
(EMVA 1288 の雑音を足すなら呼び手で。この op は幾何と開口だけ)。

**Raises** ``ValueError``: シーンの形・次元・非有限 / factor・fill_factor の範囲 / Hs・Ws が factor の倍数でない /
シフトの形・大きさ / margin が負・シフトに足りない / per_frame で枚数がシフトと合わない / Bayer なのにシーンが RGB でない(Bayer は色を撮る)/
残る画素が 8 × 8 未満。

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

- [poc_pixel_shift](../../../../examples/poc_pixel_shift.py) — `py -3.11 examples/poc_pixel_shift.py`
- [poc_simcal_pixel_shift](../../../../examples/poc_simcal_pixel_shift.py) — `py -3.11 examples/poc_simcal_pixel_shift.py`

## 型が繋がる次の op(`video` を入力に取れる)

[lockin_demodulate](../lockin/lockin_demodulate.md) · [lockin_amplitude](../lockin/lockin_amplitude.md) · [lockin_phase](../lockin/lockin_phase.md) · [lockin_separate](../lockin/lockin_separate.md) · [pixel_shift_merge](pixel_shift_merge.md) · [pixel_shift_motion_mask](pixel_shift_motion_mask.md)

## 同カテゴリ(`pixelshift`)

[pixel_shift_pattern](pixel_shift_pattern.md) · [pixel_shift_merge](pixel_shift_merge.md) · [pixel_shift_motion_mask](pixel_shift_motion_mask.md) · [false_color_metric](false_color_metric.md) · [pixel_shift_resolution_budget](pixel_shift_resolution_budget.md)

---
*Provenance: pixelshift.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
