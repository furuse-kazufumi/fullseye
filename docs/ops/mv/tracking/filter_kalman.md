---
op: filter_kalman
dim: mv
category: tracking
in: 
out: table
halcon: filter_kalman
gpu: なし
examples: [machine_vision_tour, poc_real_bg_kalman_tracking]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.1  # fullseye lib version this note was generated for
---

# filter_kalman — MV `tracking` op

- **データ種**: `なし` → `table`(引数だけで決まる op —— 画像やデータの入力を取らない)
- **呼び出し**: `import fullseye as fs; fs.ledger.filter_kalman(x, P, z, F, H, Q, R)` (実装を直接呼ぶなら `import mvtrack; mvtrack.filter_kalman(x, P, z, F, H, Q, R)`、台帳から引くなら `opsmv.get("filter_kalman")`)
- **HALCON 相当**: `filter_kalman`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

線形カルマンフィルタの予測と更新を 1 周期ぶん計算する。

``x' = F x``、``P' = F P F^T + Q`` で予測し、観測 ``z`` で更新する。共分散は対称性の崩れに
強い Joseph 形で更新する。``z`` が None なら更新を省く(観測の欠けたコマ)。
空の入力(``x`` が 0 要素)は ValueError。

Args:
    x: 状態 (n,)。
    P: 状態の共分散 (n, n)。
    z: 観測 (m,)。None で予測だけ。
    F: 遷移行列 (n, n)。
    H: 観測行列 (m, n)。
    Q: 過程の雑音の共分散 (n, n)(スカラーは対角へ広げる)。
    R: 観測の雑音の共分散 (m, m)(スカラーは対角へ広げる)。

Returns:
    ``x``、``P``、``gain``、``innovation``、``nis``(正規化した新息の 2 乗)を持つ dict。
    観測が無いコマの ``gain`` と ``innovation`` は 0、``nis`` は NaN。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_real_bg_kalman_tracking](../../../../examples/poc_real_bg_kalman_tracking.py) — `py -3.11 examples/poc_real_bg_kalman_tracking.py`

## 型が繋がる次の op(`table` を入力に取れる)

[map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [find_ncc_models](../detect/find_ncc_models.md) · [run_bg_esti](run_bg_esti.md) · [give_bg_esti](give_bg_esti.md) · [update_bg_esti](update_bg_esti.md) · [classify_class_gmm](../classify/classify_class_gmm.md)

## 同カテゴリ(`tracking`)

[create_bg_esti](create_bg_esti.md) · [run_bg_esti](run_bg_esti.md) · [give_bg_esti](give_bg_esti.md) · [update_bg_esti](update_bg_esti.md)

---
*Provenance: mvtrack.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
