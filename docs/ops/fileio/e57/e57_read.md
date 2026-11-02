---
op: e57_read
dim: fileio
category: e57
in: any
out: table
gpu: なし
examples: [fileio_roundtrip]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.8.1  # fullseye lib version this note was generated for
---

# e57_read — FILEIO `e57` op

- **データ種**: `any` → `table`
- **呼び出し**: `import fullseye as fs; fs.ledger.e57_read(data)` (実装を直接呼ぶなら `import fileio; fileio.e57_read(data)`、台帳から引くなら `opsfileio.get("e57_read")`)
- **GPU**: なし(CPU 参照実装のみ)

## 使い方

ASTM E57 の ``bytes`` を読み、座標・強度・色・pose の点群 ``table`` を返す。

この op は 1 scan の E57 を受け付ける。``pye57`` 未導入時は黙って代替せず
導入コマンドを含む ``ImportError`` を返す。呼び出し例: ``table = e57_read(payload)``。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [fileio_roundtrip](../../../../examples/fileio_roundtrip.py) — `py -3.11 examples/fileio_roundtrip.py`

## 型が繋がる次の op(`table` を入力に取れる)

[table_write_csv](../table/table_write_csv.md) · [mesh_write_ply](../mesh/mesh_write_ply.md) · [mesh_read_ply](../mesh/mesh_read_ply.md) · [mesh_read_stl](../mesh/mesh_read_stl.md) · [e57_write](e57_write.md)

## 同カテゴリ(`e57`)

[e57_write](e57_write.md)

---
*Provenance: fileio.py — FILEIO operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
