---
op: preston_removal_map
dim: drive
category: polish
in: matrix × scalar × scalar × scalar
out: image2d
examples: [poc_polish_wipe_measure]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.6.0  # fullseye lib version this note was generated for
---

# preston_removal_map — DRIVE `polish` op

- **データ種**: `matrix × scalar × scalar × scalar` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.preston_removal_map(path, force, radius: 'float', k_p: 'float', shape=(128, 128), res: 'float' = 0.0001, kind: 'str' = 'flat', speed=None, times=None, spin: 'float' = 0.0, estar=None, step=None, method: 'str' = 'direct') -> 'np.ndarray'` (実装を直接呼ぶなら `import polish; polish.preston_removal_map(path, force, radius: 'float', k_p: 'float', shape=(128, 128), res: 'float' = 0.0001, kind: 'str' = 'flat', speed=None, times=None, spin: 'float' = 0.0, estar=None, step=None, method: 'str' = 'direct') -> 'np.ndarray'`、台帳から引くなら `opsdrive.get("preston_removal_map")`)

## 使い方

軌跡と押す力から、Preston の式 dh/dt = k_p p |v_rel| を積分した除去の深さの地図 [m] (形 ``shape``、画素 ``res``)。

``path`` (N, 2) は工具の中心の xy(NaN の行で工具を持ち上げる)、``force`` はスカラーか行ごとの値(区間の中で線形に補間)、
``speed`` [m/s] か ``times`` [s] (行ごと)のどちらか。``spin`` [rad/s] で工具が回ると相対速度に ω ẑ × (x − c) が足される。
``method="direct"`` は小区間(既定の刻み res/4)ごとに窓の画素で足す。``method="fft"`` は「軌跡の線密度の画像」と正規化した
圧力の窓(:func:`preston_pressure_kernel`)の畳み込み —— 回らない・力が一定・速さが一定の時だけ使える第 2 の実装で、
体積 Σ h res² = k_p F × (窓の半分だけ広げた地図の中の軌跡の長さ)を、地図の外にこぼれる分を除いて保つ。
**Raises** ValueError: 形・数の検査、速さも時刻も無い、時刻が増えない、fft で回る / 力が変わる / 時刻で速さが変わる。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_polish_wipe_measure](../../../../examples/poc_polish_wipe_measure.py) — `py -3.11 examples/poc_polish_wipe_measure.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[flow_from_depth_motion](../ttc/flow_from_depth_motion.md) · [ttc_truth](../ttc/ttc_truth.md) · [ttc_from_flow](../ttc/ttc_from_flow.md) · [foe_from_flow](../ttc/foe_from_flow.md) · [perlin2](../terrain/perlin2.md) · [fbm_height](../terrain/fbm_height.md) · [fbm_gradient](../terrain/fbm_gradient.md) · [radial_periodogram](../terrain/radial_periodogram.md)

## 同カテゴリ(`polish`)

[preston_pressure_kernel](preston_pressure_kernel.md) · [preston_track_profile](preston_track_profile.md) · [wipe_band_width](wipe_band_width.md) · [raster_wipe_area](raster_wipe_area.md) · [coat_image](coat_image.md) · [coat_thickness_from_image](coat_thickness_from_image.md) · [wipe_coverage](wipe_coverage.md) · [band_width_profile](band_width_profile.md)

---
*Provenance: polish.py — DRIVE operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
