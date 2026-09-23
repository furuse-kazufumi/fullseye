---
op: video_interpolate_flow
dim: live4d
category: time
in: video
out: video
examples: []
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# video_interpolate_flow — LIVE4D `time` op

- **データ種**: `video` → `video`
- **呼び出し**: `import fullseye as fs; fs.ledger.video_interpolate_flow(video, factor: 'int' = 2, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 3, reg: 'float' = 0.001, occlusion_tau: 'float' = 1.0) -> 'np.ndarray'` (実装を直接呼ぶなら `import live4d; live4d.video_interpolate_flow(video, factor: 'int' = 2, win: 'int' = 3, pyr_levels: 'int' = 3, iters: 'int' = 3, reg: 'float' = 0.001, occlusion_tau: 'float' = 1.0) -> 'np.ndarray'`、台帳から引くなら `opslive4d.get("video_interpolate_flow")`)

## 使い方

動画 ``(T, H, W)`` を流れで補間して ``(T + (T − 1)(factor − 1), H, W)`` に(``video``、時間の超解像)。

隣り合うフレーム a, b の間に ``factor − 1`` 枚を、前向きの流れ(a → b)と後ろ向きの流れ(b → a)で
それぞれ引き戻した像の重みつき平均で作る(流れは**出力画素の位置で**引く近似 —— 場が一様でない所では
始点で定義された変位を終点で読むずれが出る。厳密には逆写像を解く必要があり、ここではしない)。重みは時刻の近さ × 往復一致(a → b → a で戻る誤差
``e`` に対し ``exp(−e / occlusion_tau)``)—— 遮蔽や推定失敗で戻らない場所は、その側の像を信じない。
大きすぎる変位(ピラミッドで追えない)や新しく現れる物体は補間できず、二重像になる —— 補間は
「実測の間を埋める」道具で、無いものを発明する道具ではない。真値つきの検証は、2 倍のフレームレートで
合成 → 半分に間引く → 補間 → 抜いたフレームと比べる(``examples/poc_live4d.py``)。

## 詳しい使い方ガイド

- [live4d ファミリ ガイド](../guides/live4d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- (まだありません)

## 型が繋がる次の op(`video` を入力に取れる)

—

## 同カテゴリ(`time`)

[volseq_interpolate_flow](volseq_interpolate_flow.md) · [volseq_magnify_motion](volseq_magnify_motion.md)

---
*Provenance: live4d.py — LIVE4D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
