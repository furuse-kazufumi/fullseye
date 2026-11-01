---
op: orientation_code
dim: codematch
category: code
in: image2d
out: image2d
gpu: なし
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# orientation_code — CODEMATCH `code` op

- **データ種**: `image2d` → `image2d`
- **呼び出し**: `import fullseye as fs; fs.ledger.orientation_code(image, n_codes=16, grad_thresh=0.05)` (実装を直接呼ぶなら `import codematch; codematch.orientation_code(image, n_codes=16, grad_thresh=0.05)`、台帳から引くなら `opscodematch.get("orientation_code")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

勾配の向きを ``n_codes`` 段に量子化した方向符号の画像(OCM の符号化)。

``θ = atan2(∂I/∂行, ∂I/∂列)`` を [0, 2π) に取り(Sobel、縁は最近傍で延長)、
``floor(θ / (2π/N))`` を符号 0..N-1 にする。``|∂I/∂列| + |∂I/∂行| <= grad_thresh``
の画素は無効符号 ``N``(雑音しか無い所の向きは信用しない)。

``grad_thresh`` は [0, 1] の明るさで測った Sobel の和の閾値。既定 0.05 は、
8 ビットの量子化雑音(σ = 1/255)が作る和の平均(約 0.022)の 2 倍強。
``n_codes`` は 4 の倍数(既定 16 = 22.5° 刻み)。返りは int16 の 2 次元配列。

明るさに定数を足しても符号は 1 つも変わらない。明るさを g 倍したときは
``grad_thresh`` も g 倍すれば同じ符号になる。画像を 90° 回すと、符号は
``N/4`` だけ巡回してずれる(``np.rot90`` で反時計回りなら ``-N/4``)。

## 詳しい使い方ガイド

- [robust_code_matching ファミリ ガイド](../guides/robust_code_matching.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`image2d` を入力に取れる)

[increment_sign](increment_sign.md) · [ocm_match](../match/ocm_match.md) · [isc_match](../match/isc_match.md) · [scc_match](../match/scc_match.md) · [radial_reach_filter](../change/radial_reach_filter.md)

## 同カテゴリ(`code`)

[increment_sign](increment_sign.md)

---
*Provenance: codematch.py — CODEMATCH operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
