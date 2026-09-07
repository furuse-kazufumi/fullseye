---
op: piv_cross_correlate
dim: piv
category: estimate
in: image2d × image2d
out: flow2d
examples: [piv_field_analysis_tour, piv_flow_from_particles, poc_beam_modal_video, poc_change_detection_misreg, poc_dic_strain, poc_river_surface_velocity, poc_strain_history, poc_superresolution_limits]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.10  # fullseye lib version this note was generated for
---

# piv_cross_correlate — PIV `estimate` op

- **データ種**: `image2d × image2d` → `flow2d`
- **呼び出し**: `import pivops; pivops.piv_cross_correlate(a, b, window=32, overlap=0.5, peak='gauss3', window_func='hann', subtract_mean=True, shift=None, normalize='overlap', search_limit=0.25)` (または `opspiv.get("piv_cross_correlate")`)
- **台帳経由の戻り値**: `fullseye.ledger.piv_cross_correlate(...)` は**宣言 out 型 `flow2d` の値だけ**を返す(本体は補助情報も返す)。捨てられた側が要るときは `fullseye.ledger.piv_cross_correlate.raw(...)`、または `pivops.piv_cross_correlate` を直接呼ぶ。
  - 本体の返り: `(flow, info) -> flow2d`

## 使い方

窓ごとの相互相関で変位場を出す。返りは ``(flow, info)``。

各窓で ``FFT`` を 2 回とって共役積の逆変換を取り(循環相関)、最大値の
位置を整数変位、その周りの 3 点でサブピクセル変位を決める。

**零方向への偏りとその補正(実測)**: 素の相互相関は変位を**零へ引き寄せる**。
窓をずらすと重なる領域が減り、相関の値そのものが変位とともに落ちるからで、
実測でも偏りは変位に比例した(win=32・Hann、``dx`` を 0.5 から 6 px まで
振って偏り / (d/N) が 1.30, 1.29, 1.28, 1.28, 1.28 —— **傾き一定**)。

``normalize="overlap"`` はこれを、**窓関数の自己相関で割る**ことで補正する
(重なり面積で正規化するのと同じ)。ただし縁では割る量が 0 に近づくので、
``search_limit`` で探索範囲を窓の 1/4 に絞るのと**必ず対にする**。実測:

===============  ==========  ==========  ==========
dx [px]          補正なし    補正 + 1/4  補正のみ
===============  ==========  ==========  ==========
1.0 の偏り       -0.0402     -0.0020     -0.2659
5.0 の偏り       -0.2001     -0.0128     -0.9210
5.0 の RMS       0.2081      0.0301      4.8881
===============  ==========  ==========  ==========

右端が「探索を絞らずに正規化だけした」場合で、**補正が誤差を 23 倍に悪化
させる**。片方だけ入れてはいけない、という測定結果をそのまま既定にしてある。

Args:
    a, b: 画像対 ``(H, W)``。
    window: 窓の一辺 [px]。偶数・8 以上。
    overlap: 窓の重なり率 ``[0, 1)``。0.5 が慣行。
    peak: :data:`PEAK_MODES`。
    window_func: :data:`WINDOW_FUNCS`。
    subtract_mean: 窓ごとに平均を引く(背景の直流成分が中央に巨大な
        ピークを作るのを防ぐ)。**切ると零変位に張り付く**。
    shift: 予測変位 ``(2, h, w)``(多段用)。2 枚目の窓をこの整数量だけ
        ずらして切り出し、残差を測る。
    normalize: ``"overlap"``(既定)か ``"none"``。
    search_limit: 探索する変位の上限を窓の比で与える(既定 0.25 = PIV の
        「1/4 則」)。``None`` で無制限 —— ``normalize="overlap"`` との
        併用は上の表のとおり**悪化する**。
Returns:
    ``(flow (2, h, w), info)``。``info`` は ``rows`` / ``cols``(窓中心の
    画像座標)、``peak_ratio``(第 1 ピーク / 第 2 ピーク。1 に近いほど
    当てにならない)、``window`` / ``overlap`` / ``peak`` を持つ dict。

## 詳しい使い方ガイド

- [piv_displacement ファミリ ガイド](../guides/piv_displacement.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [piv_field_analysis_tour](../../../../examples/piv_field_analysis_tour.py) — `py -3.11 examples/piv_field_analysis_tour.py`
- [piv_flow_from_particles](../../../../examples/piv_flow_from_particles.py) — `py -3.11 examples/piv_flow_from_particles.py`
- [poc_beam_modal_video](../../../../examples/poc_beam_modal_video.py) — `py -3.11 examples/poc_beam_modal_video.py`
- [poc_change_detection_misreg](../../../../examples/poc_change_detection_misreg.py) — `py -3.11 examples/poc_change_detection_misreg.py`
- [poc_dic_strain](../../../../examples/poc_dic_strain.py) — `py -3.11 examples/poc_dic_strain.py`
- [poc_river_surface_velocity](../../../../examples/poc_river_surface_velocity.py) — `py -3.11 examples/poc_river_surface_velocity.py`
- [poc_strain_history](../../../../examples/poc_strain_history.py) — `py -3.11 examples/poc_strain_history.py`
- [poc_superresolution_limits](../../../../examples/poc_superresolution_limits.py) — `py -3.11 examples/poc_superresolution_limits.py`

## 型が繋がる次の op(`flow2d` を入力に取れる)

[piv_deform_pass](piv_deform_pass.md) · [piv_outlier_mask](../validate/piv_outlier_mask.md) · [piv_replace_outliers](../validate/piv_replace_outliers.md) · [piv_vorticity](../field/piv_vorticity.md) · [piv_divergence](../field/piv_divergence.md) · [piv_flow_magnitude](../field/piv_flow_magnitude.md) · [piv_to_velocity](../field/piv_to_velocity.md) · [piv_velocity_gradient](../field/piv_velocity_gradient.md)

## 同カテゴリ(`estimate`)

[piv_multipass](piv_multipass.md) · [piv_deform_pass](piv_deform_pass.md) · [piv_ensemble_correlate](piv_ensemble_correlate.md)

---
*Provenance: pivops.py — PIV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
