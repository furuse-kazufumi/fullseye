---
op: points_to_gaussians
dim: reprconv
category: gaussians
in: points
out: gaussians
examples: [representation_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.7  # fullseye lib version this note was generated for
---

# points_to_gaussians — REPRCONV `gaussians` op

- **データ種**: `points` → `gaussians`
- **呼び出し**: `import reprconv; reprconv.points_to_gaussians(points, k=6, scale=1.0)` (または `opsreprconv.get("points_to_gaussians")`)

## 使い方

点群 ``(N,3)`` → 等方ガウシアン ``gaussians``。**この型の唯一の入口**。

``gaussians`` は台帳で ``fuse3d.to_points`` が食う型だが、**産む op が
1 つも無かった**(実測)—— 消費側だけがある型は、生成器を種として置かない限り
一度も実行されない。ここでは 3D Gaussian Splatting の初期化と同じやり方で
作る: 各点の k 近傍までの**平均距離**を sigma、重みを 1/N の等分にする。

``mu`` は入力点そのものなので :func:`gaussians_to_points` と往復して
**bit 一致**(実測 max|Δ| = 0.0)。sigma と w は往復で戻らない —— 点群には
もともと無かった量だからで、これは損失ではなく**追加**である。

Args:
    points: (N, 3)。N >= 2。
    k: sigma を決める近傍数(既定 6)。N-1 を超えると N-1 に丸める。
    scale: sigma に掛ける係数(既定 1.0)。
Returns:
    dict(``mu`` (N,3) / ``sigma`` (N,) / ``w`` (N,))。
Raises:
    ValueError: N < 2 / k < 1 / scale <= 0 / 形状不正 / 非有限。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [representation_roundtrip](../../../../examples/representation_roundtrip.py) — `py -3.11 examples/representation_roundtrip.py`

## 型が繋がる次の op(`gaussians` を入力に取れる)

[gaussians_to_points](gaussians_to_points.md) · [gaussians_to_voxel](gaussians_to_voxel.md)

## 同カテゴリ(`gaussians`)

[gaussians_to_points](gaussians_to_points.md) · [gaussians_to_voxel](gaussians_to_voxel.md)

---
*Provenance: reprconv.py — REPRCONV operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
