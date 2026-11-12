---
op: create_ncc_model
dim: mv
category: detect
in: image2d
out: table
halcon: create_ncc_model
gpu: なし
examples: [machine_vision_tour, poc_real_stereo_multiscanline]
author: Kazufumi Furuse
license: Apache-2.0
version: 1.1.0  # fullseye lib version this note was generated for
---

# create_ncc_model — MV `detect` op

- **データ種**: `image2d` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.create_ncc_model(template) -> 'dict'` (実装を直接呼ぶなら `import matching; matching.create_ncc_model(template) -> 'dict'`、台帳から引くなら `opsmv.get("create_ncc_model")`)
- **HALCON 相当**: `create_ncc_model`(意味・パラメータは HALCON リファレンスが参考になる)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

NCC モデル(=正規化テンプレート)を準備(create_ncc_model)。

Args:
    template: 2次元の有限値テンプレート。呼び出し元と独立した
        float64 コピーを保持する。

Returns:
    中心化・単位ノルム化済みテンプレートと準備時の
    ``template_scale``、整数の ``template_scale_exp`` を持つモデル。
    最大絶対値の2進指数が -500 未満または 500 超、すなわち
    ``2**-500`` 未満または ``2**501`` 以上のとき、有限な正の
    2のべき乗で拡大縮小して ``norm`` を計算する。有限の非定数
    テンプレートは倍率によらず自己一致が 1（誤差 1e-12 以下）に
    なり、``1e-200`` と ``1e200`` の混在も含む。最大値と最小値が
    等しい定数テンプレートは ``constant=True``、``norm=0``、
    ``t0n`` が全ゼロとなり、すべての窓にスコア0を返す。

空の入力(``template`` が 0 要素)は ValueError。

Raises:
    FsValueError: ``template`` が NaN または無限大を含む場合。

## 詳しい使い方ガイド

- [machine_vision_classics ファミリ ガイド](../guides/machine_vision_classics.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [machine_vision_tour](../../../../examples/machine_vision_tour.py) — `py -3.11 examples/machine_vision_tour.py`
- [poc_real_stereo_multiscanline](../../../../examples/poc_real_stereo_multiscanline.py) — `py -3.11 examples/poc_real_stereo_multiscanline.py`

## 型が繋がる次の op(`table` を入力に取れる)

[map_image](../resample/map_image.md) · [rectify_to_world_plane](../resample/rectify_to_world_plane.md) · [change_radial_distortion_image](../resample/change_radial_distortion_image.md) · [find_ncc_models](find_ncc_models.md) · [run_bg_esti](../tracking/run_bg_esti.md) · [give_bg_esti](../tracking/give_bg_esti.md) · [update_bg_esti](../tracking/update_bg_esti.md) · [classify_class_gmm](../classify/classify_class_gmm.md)

## 同カテゴリ(`detect`)

[points_lepetit](points_lepetit.md) · [find_ncc_models](find_ncc_models.md)

---
*Provenance: matching.py — MV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
