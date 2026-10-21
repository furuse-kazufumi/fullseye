---
op: moire_overlay_image
dim: optics
category: moire_align
in: 
out: image2d
examples: [poc_moire_alignment, poc_moire_screen]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.2  # fullseye lib version this note was generated for
---

# moire_overlay_image — OPTICS `moire_align` op

- **データ種**: `なし` → `image2d`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.moire_overlay_image(shape=(256, 1024), pixel_um=0.5, p_mask_um=2.0, p_wafer_um=2.04, shift_nm=0.0, layout='single', profile='square', duty=0.5, blur_sigma_um=1.5, gap_um=0.0, wavelength_um=None, drift_nm=0.0, illum_gradient=0.0, noise_sigma=0.0, seed=0, moving='wafer', n_harmonics=15, allow_aliasing=False, with_mask=True)` (実装を直接呼ぶなら `import moirealign; moirealign.moire_overlay_image(shape=(256, 1024), pixel_um=0.5, p_mask_um=2.0, p_wafer_um=2.04, shift_nm=0.0, layout='single', profile='square', duty=0.5, blur_sigma_um=1.5, gap_um=0.0, wavelength_um=None, drift_nm=0.0, illum_gradient=0.0, noise_sigma=0.0, seed=0, moving='wafer', n_harmonics=15, allow_aliasing=False, with_mask=True)`、台帳から引くなら `opsoptics.get("moire_overlay_image")`)

## 使い方

重ねた 2 枚の格子をカメラで撮った像(位置合わせのマーク)を合成する。

像 = [マークの強度(マスクの格子の像 × ウェハの格子の反射率)] をガウスのぼけ(MTF exp(−2π²σ²f²))と
画素の積分(sinc)で撮ったもの。格子はフーリエ級数で持つので、ぼけと画素は**閉形式**(打ち切りの誤差は
n_harmonics と項の大きさの床 1e-12 だけ)。ギャップ gap_um > 0 ではマスクの像を ``moire_talbot_gap`` と同じく
``optics.angular_spectrum_propagate`` で伝搬する(0/1 の格子だけ、波長 wavelength_um が要る —— ギャップが 0 なら使わない)。ぼけが格子のピッチを潰すので、
像に残るのは差の周波数の縞(モアレ)だけになる —— これが位置合わせのマークの要点。

layout:
  ``"single"``       全面が 1 対(マスク p_m、ウェハ p_w)、線は縦、x のずれを読む。
  ``"differential"`` 上半分 = 対 A(p_m, p_w)、下半分 = 対 B(ピッチを入れ替え)。ずれで 2 つの縞は逆に動き、
                     マーク全体の流れ(drift_nm)では同じ向きに動く。
  ``"quad"``         4 象限: 左上 A_x、右上 B_x、左下 A_y、右下 B_y(下は線が横で y のずれ)。
                     shift_nm と drift_nm は (x, y) の組でもよい。
``with_mask=False`` はマスクを外してウェハの格子だけを撮った**直接の像**(比べ手の相互相関に使う。ピッチ 2 µm の
格子はぼけで消えて一様な灰色になる —— 直接の像ではずれが見えない、を示す)。縞の周期の検査はしない。
shift_nm は moving(既定 ``"wafer"``)の格子のずれ。drift_nm はマーク全体(2 枚とも)がカメラに対して動いた量。
illum_gradient は視野の端から端までの照明の傾き(相対、x と y に同じ量)、noise_sigma は加える白色ガウス雑音の
標準偏差(強度の単位。0/1 の格子 2 枚で平均は 0.25)。

**Raises** ValueError: 同じピッチ、縞の周期が 2 画素未満(ナイキスト超え)、区画に縞が 1 周期も入らない、
ぼけで消えきらない格子の周波数がナイキストを超える(``allow_aliasing=True`` で許す —— 実際のカメラでは
折り返して縞に混ざる)、ギャップがあるのに profile が ``"sine"``、綴り違い、形が小さすぎる。

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

- [poc_moire_alignment](../../../../examples/poc_moire_alignment.py) — `py -3.11 examples/poc_moire_alignment.py`
- [poc_moire_screen](../../../../examples/poc_moire_screen.py) — `py -3.11 examples/poc_moire_screen.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[fraunhofer_pattern](../wave/fraunhofer_pattern.md) · [pupil_psf](../wave/pupil_psf.md) · [pupil_blur](../wave/pupil_blur.md) · [psf_to_mtf](../imaging/psf_to_mtf.md) · [encircled_energy](../imaging/encircled_energy.md) · [ensquared_energy](../imaging/ensquared_energy.md) · [energy_radii](../imaging/energy_radii.md) · [mtf_tangential_sagittal](../imaging/mtf_tangential_sagittal.md)

## 同カテゴリ(`moire_align`)

[moire_magnification](moire_magnification.md) · [moire_talbot_gap](moire_talbot_gap.md) · [moire_phase](moire_phase.md) · [moire_phase_to_shift](moire_phase_to_shift.md) · [moire_differential_shift](moire_differential_shift.md) · [moire_mark_read](moire_mark_read.md) · [moire_phase_crlb](moire_phase_crlb.md)

---
*Provenance: moirealign.py — OPTICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
