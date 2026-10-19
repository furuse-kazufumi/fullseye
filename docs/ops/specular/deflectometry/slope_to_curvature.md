---
op: slope_to_curvature
dim: specular
category: deflectometry
in: normalmap
out: image2d
examples: [poc_phase_measuring_deflectometry]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.7.1  # fullseye lib version this note was generated for
---

# slope_to_curvature — SPECULAR `deflectometry` op

- **データ種**: `normalmap` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.slope_to_curvature(normals, spacing=1.0, kind='mean', sigma_px=0.0)` (実装を直接呼ぶなら `import deflectometry; deflectometry.slope_to_curvature(normals, spacing=1.0, kind='mean', sigma_px=0.0)`、台帳から引くなら `opsspecular.get("slope_to_curvature")`)

## 使い方

法線マップ (H, W, 3) → 曲率の地図 (H, W)。傾きを 1 回微分するだけで、高さへ積分しない。

傾き p = ∂z/∂x、q = ∂z/∂y を `photometric.normals_to_gradients` で取り、``spacing``
(格子間隔、例 mm)で中心差分して z_xx = ∂p/∂x、z_yy = ∂q/∂y、z_xy = (∂p/∂y + ∂q/∂x) / 2。
``kind``:
  * ``"mean"`` —— 平均曲率 H = ((1 + q²) z_xx − 2pq z_xy + (1 + p²) z_yy) / (2 (1 + p² + q²)^{3/2})。
  * ``"gaussian"`` —— ガウス曲率 K = (z_xx z_yy − z_xy²) / (1 + p² + q²)²。
  * ``"laplacian"`` —— z_xx + z_yy(小さな傾きでの 2H)。
単位は 1 / (spacing の単位)。符号: 上に開いた椀(凹み、z = r² / 2R)が**正**(H = 1/R)。
``sigma_px`` > 0 なら微分の前に傾きをガウスで均す(微分は雑音を持ち上げる)。NaN の画素は
重みつきの均しで避け、出力でも NaN。

デフレクトメトリが曲率で欠陥を見る理由: 凹み・うねりは高さでは µm でも曲率は大きく、しかも
面全体の傾きと一定の傾きの誤差(高さと傾きの不定性で出るもの)は微分で消える。

Raises: ``ValueError`` —— 法線が (H, W, 3) でない・2 × 2 未満・無限大を含む・z 成分が正でない
(面の外向きでない)、spacing が正でない、kind が mean / gaussian / laplacian でない、sigma が負。

## 詳しい使い方ガイド

- [specular_photometric ファミリ ガイド](../guides/specular_photometric.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_phase_measuring_deflectometry](../../../../examples/poc_phase_measuring_deflectometry.py) — `py -3.11 examples/poc_phase_measuring_deflectometry.py`

## 型が繋がる次の op(`image2d` を入力に取れる)

[polarization_render](../polarization/polarization_render.md) · [deflectometry_render](deflectometry_render.md) · [deflectometry_phase_to_slope](deflectometry_phase_to_slope.md)

## 同カテゴリ(`deflectometry`)

[deflectometry_rig](deflectometry_rig.md) · [deflectometry_screen_pattern](deflectometry_screen_pattern.md) · [deflectometry_render](deflectometry_render.md) · [deflectometry_phase_to_slope](deflectometry_phase_to_slope.md) · [deflectometry_sensitivity](deflectometry_sensitivity.md)

---
*Provenance: deflectometry.py — SPECULAR operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
