# 汎用アルゴリズムを実装可能にする — algo-c 対応ロードマップ

> ユーザー要望(2026-08-16): <https://github.com/okumuralab/algo-c>(奥村晴彦
> 『[改訂新版] C言語による標準アルゴリズム事典』全ソース)にあるような**汎用アルゴリズム**も
> Fullseye で実装できるようにしたい。
>
> **正直な現状認識**: Fullseye は現在 **画像アルゴリズム設計 AI**(op レジストリ = image/region/
> feature/contour/volume の sort、進化 + holdout gate + Python→C codegen)。汎用アルゴリズム
> (ソート/探索/グラフ/数論/暗号/圧縮)は画像 sort に載らないため、**言語・型・codegen の拡張**が要る。
> これは複数セッションの作業。本 doc はその**確定計画**(次セッションが full context で実行する正本)。

## algo-c のカテゴリ(書籍 TOC・実装対象マップ)
※ 厳密な網羅は repo の `/src` を正本とする。

| 分野 | 代表アルゴリズム | Fullseye での受け皿 |
|---|---|---|
| 数値計算 | 方程式(二分法/Newton)、数値積分(Simpson/Romberg)、連立一次(Gauss/LU)、補間(spline)、FFT | 既存 `dsp`(FFT)+ 新 `numeric` op 族 |
| 乱数・統計 | Mersenne Twister、分布、統計量 | 新 `rng`/`stat` op(決定的 seed) |
| ソート | quick/heap/merge/shell/radix | 新 `array` sort + `seq` 型 |
| 探索 | 二分探索、ハッシュ、BST/AVL/B-tree | 新 `array`/`map` op |
| 文字列 | KMP/BM/Rabin-Karp、編集距離、正規表現 | 新 `text` 型 + op |
| グラフ | DFS/BFS、Dijkstra、Warshall-Floyd、MST、最大流 | 新 `graph` 型 + op |
| 幾何 | 凸包、線分交差、ボロノイ | 既存 `pcseg`/幾何 + 新 `geom2d` |
| 数論・暗号 | 素数、GCD、RSA、MD5/SHA、AES | 新 `numtheory`/`crypto`(教育用・honest 開示) |
| データ圧縮 | Huffman、LZ/LZW、算術符号化 | 新 `compress` op |
| DP/探索 | 8-queens、ナップサック、DP | fscript の制御フロー + `array` |

## 実装アーキテクチャ(確定方針)
Fullseye の既存資産を汎用へ拡張する。**画像 AI の焦点は薄めない**(汎用 op は別 tier / opt-in)。

1. **型システム拡張**: 現在 6+1 sort(image/region/feature/contour/match/any/volume)に
   **`seq`(1-D 配列)/`text`(文字列)/`graph`/`scalar`** を追加(`ops.py` の sort・`fslib` 型)。
2. **fscript の汎用言語化**: 既に if/for/while・代入・タプルがある。**配列/文字列リテラル、
   インデックス、procedure(関数)** を段階追加(現在は言語スコープを絞る決定だったので、
   汎用 tier は別プロファイルで解禁)。正本 = `docs/FSCRIPT_DECISION.md` の A/B 分岐を再検討。
3. **op レジストリ拡張**: algo-c の各アルゴリズムを **op**(name/in-out sort/params/**c_stmt**)として
   登録。既存の Python→C codegen(`engine.to_python`/`to_c`)+ **difftest**(honest gate: Python が
   oracle、C を差分検証)をそのまま流用 → **「C で実装できる」を実測で保証**。
4. **honest gate**: algo-c の C を参照実装として `difftest` に食わせ、Fullseye codegen の C と
   数値/ビット一致を検証(既存 gate の拡張)。**元コードのライセンス**(algo-c = 書籍付属、
   利用条件を要確認)を尊重し、**丸写しでなく仕様から再実装**(公開開示ポリシー)。

## 段階計画(次セッション以降)
- **P1**: `seq`/`scalar` 型 + ソート 3 種(quick/heap/merge)を op 化 + C codegen + difftest。
  = 「Fullseye は汎用アルゴリズムも C 生成できる」最小実証。
- **P2**: 数値計算(二分法/Newton/Simpson/Gauss)op 族。
- **P3**: 文字列(KMP/BM/編集距離)+ `text` 型。
- **P4**: グラフ(Dijkstra/BFS/MST)+ `graph` 型。
- **P5**: 圧縮/数論/暗号(教育用・honest 開示、丸写し禁止)。
- 各 P で: 進化 gate は非対象(汎用 op は決定的・holdout 進化しない)、**difftest で C 一致を honest 実測**、
  Studio の op ブラウザに新 tier を出す。

## honest な限界と規律
- **丸写ししない**: algo-c の C を参照しつつ**仕様から再実装**(`feedback_provenance_research_method`)。
  ライセンス確認前にコードを取り込まない。
- **画像 AI の焦点を薄めない**: 汎用 op は opt-in tier。北極星(HALCON 級画像 op 網羅 + honest
  holdout)は不変。
- **本セッションでは着手しない**(context budget)。本 doc が次セッションの実行正本。
