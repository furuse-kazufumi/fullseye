---
op: focus_sweep_height_video
dim: live4d
category: render
in: volseq
out: video
examples: [poc_live4d]
author: Kazufumi Furuse
license: Apache-2.0
version: 0.2.3  # fullseye lib version this note was generated for
---

# focus_sweep_height_video — LIVE4D `render` op

- **データ種**: `volseq` → `video`
- **呼び出し**: `import fullseye as fs; fs.ledger.focus_sweep_height_video(volseq, window: 'int' = 5) -> 'np.ndarray'` (実装を直接呼ぶなら `import live4d; live4d.focus_sweep_height_video(volseq, window: 'int' = 5) -> 'np.ndarray'`、台帳から引くなら `opslive4d.get("focus_sweep_height_video")`)

## 使い方

焦点掃引(各フレームが z の合焦スタック)の時系列から**高さ場の動画** ``(T, Y, X)`` を起こす(``video``、
単位は z の枚数)。

合焦度は局所ラプラシアン絶対値の平均(``window``、Sum-Modified-Laplacian)、各画素の高さは合焦度が
最大の z を放物線で副ボクセル精度にしたもの(``depth_from_focus`` の時系列版)。数値が欲しいときはこちら、
絵が欲しいときは ``focus_sweep_surface_video``。テクスチャの無い画素は合焦度が平らで高さが決まらない。

## 詳しい使い方ガイド

- [live4d ファミリ ガイド](../guides/live4d.md)

## 参考(サンプルデータ・文献)

- [サンプルデータ カタログ(DL URL / ライセンス)](../../SAMPLES.md) — 2-D は skimage.data(BSD/public)+ 合成、3-D は実データ源(Stanford/PDS 等)の DL URL。
- [演算子の来歴・参考文献](../../../REFERENCES.md) — この op 族の元になった研究/手法の出典。
- アルゴリズムの正典(著者・年)と用途は上記**ファミリ使い方ガイド**に記載。

## 実行できる例(この op を実際に呼ぶ検証済みサンプル)

- [poc_live4d](../../../../examples/poc_live4d.py) — `py -3.11 examples/poc_live4d.py`

## 型が繋がる次の op(`video` を入力に取れる)

[video_interpolate_flow](../time/video_interpolate_flow.md)

## 同カテゴリ(`render`)

[volseq_render_orbit](volseq_render_orbit.md) · [focus_sweep_surface_video](focus_sweep_surface_video.md)

---
*Provenance: live4d.py — LIVE4D operator registry. この per-op ノートは `tools/opdocs.py md` が自動生成(手編集しない)。*

© 2026 Kazufumi Furuse — Fullseye operator documentation. Licensed under Apache-2.0.
