---
op: perceptual_hash
dim: imgforensics
category: hash
in: image2d
out: phash
examples: [image_forensics_audit]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.1.9  # fullseye lib version this note was generated for
---

# perceptual_hash — IMGFORENSICS `hash` op

- **データ種**: `image2d` → `phash`
- **呼び出し**: `import imgforensics; imgforensics.perceptual_hash(image, mode: 'str' = 'dct', hash_size: 'int' = 8) -> 'np.ndarray'` (または `opsimgforensics.get("perceptual_hash")`)

## 使い方

知覚ハッシュ(perceptual hash)。**bool の 1-D ビット列**を返す。

``mode``:

``"dct"``   縮小 ``(hash_size * 4)`` 角 → 2-D DCT-II(直交)→ 左上
            ``hash_size x hash_size`` を取り、**DC を除いた中央値**と比較。
            Zauner 2010 の pHash と同じ手順。長さ ``hash_size**2`` ビット。
``"average"`` 縮小 ``hash_size`` 角 → 平均と比較(aHash)。同じ長さ。
``"difference"`` 縮小 ``(hash_size, hash_size + 1)`` → **横に隣り合う画素の
            大小**を比較(dHash)。同じ長さで、平均輝度の変化に強い。

実測(``tests/test_imgforensics.py`` が数で固定。256x256 の 1/f^1.6 画像、
``hash_size=8`` = 64 ビット。**無関係な 2 枚の距離**は dct 31.3 / average 34.2 /
difference 32.6(20 対の平均。理論値は 32 = ビット長の半分)):

===================== ======== ========== ============
変換                  dct      average    difference
===================== ======== ========== ============
JPEG 品質 60 再圧縮   0        0          0
JPEG 品質 30 再圧縮   2        0          0
1/2 縮小              0        0          0
1/4 縮小              0        0          0
明るさ +0.1           0        0          0
**左右反転**          **28**   **42**     **34**
**90 度回転**         **32**   **30**     **32**
別の画像              28       40         34
===================== ======== ========== ============

**この op が言えないこと**:

* 距離が小さい = 同じ画像、ではない。8x8 の粗い縮小に落としているので、
  **細部の改竄は距離 0 のまま通る**。実測:512x512 の画像に 24x24 の
  コピー&ムーブを入れたときの距離は dct 0 / average 0 / difference 1。
* 距離が大きい = 別画像、でもない。上の表のとおり **反転と回転は「別の画像」と
  区別が付かない**(どちらも無関係な 2 枚と同じ距離域に入る)。幾何変換に対する
  不変性は一切無い。
* 返り値は **``phash`` 語彙**であって ``signal`` ではない。bool の 1-D は
  既存の ``signal`` / ``indices`` / ``descriptor`` の述語をすべて満たすので、
  取り違えると ``signal1d.lowpass`` などが **有限でもっともらしい値**を返す
  (実測 5 op)。だから :func:`hash_distance` は dtype を検査する。

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [image_forensics_audit](../../../../examples/image_forensics_audit.py) — `py -3.11 examples/image_forensics_audit.py`

## 型が繋がる次の op(`phash` を入力に取れる)

[hash_distance](hash_distance.md) · [watermark_embed](../watermark/watermark_embed.md) · [watermark_capacity](../watermark/watermark_capacity.md)

## 同カテゴリ(`hash`)

[hash_distance](hash_distance.md)

---
*Provenance: imgforensics.py — IMGFORENSICS operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
