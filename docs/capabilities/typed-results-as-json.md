---
id: typed-results-as-json
title: op の返り値(型付き)を JSON に出し、bit そのままで戻す
title_en: Write typed op results as JSON and read them back bit-for-bit
category: 組み立てる
ops: [to_json, from_json, to_jsonable, from_jsonable, save_json, load_json, to_json_lines, from_json_lines, as_value, apply_json, is_envelope]
examples: [typed_results_json]
version: 0.2.1
---

# op の返り値(型付き)を JSON に出し、bit そのままで戻す

## できること

op の返り値は `image` / `region` / `points` / `contour` / `feature` / `matrix` / `signal` … の**型(sort)**を持つ NumPy 配列や小さな dict で、次の op に渡すには良くても、ファイル・ログ・LLM・別プロセスには渡せません。`to_json(value, sort)` が sort ごとに**一つ**の JSON 形を与え、`from_json(text)` が `(value, sort)` に戻します。封筒は自己記述(`{"fullseye_sort": "points", "version": 1, "payload": …}`)で、戻すときに型の指定は要りません。

浮動小数の配列は little-endian float64 の base64(`b64f64`)で運ぶので、**往復で bit が一致**します(`readable=True` なら数のリストで、これも Python の `repr` が最短の往復可能 10 進なので厳密)。`region` は行優先の run-length、`contour` は `{"shape", "cs": [(N, 2) …]}`、`table` は JSON そのもの(中の NumPy は変換)。非有限値(NaN / inf)は裸のトークンで出さず、封筒に `nonfinite: true` を立てて bytes で運びます。

**色んな場面で使えるよう、薄い便利関数も同梱**します。`save_json(value, sort, path)` / `load_json(path)` はファイルへ一往復。`to_json_lines(items)` / `from_json_lines(text)` は `(value, sort)` の列を **JSON Lines**(1 行 1 封筒)にします —— bbox・特徴・輪郭を 1 行ずつ足していく台帳やログに向きます。Markdown と組み合わせる橋は [`typed-results-as-markdown`](typed-results-as-markdown.md) を参照。

**引数で JSON を渡す・どの op でも JSON で回す**。`as_value(x)` は値でも JSON 封筒(文字列でも dict でも)でも受けて**値**を返すので、関数の入口に一枚かませば「配列でも JSON でも受ける」になります(封筒のふりで壊れていれば fail-closed)。`apply_json(image, op, a, b)` は `fullseye.apply` の JSON 版 —— 入力を封筒で渡し、結果を封筒の文字列で受け取れます(出力の sort はレジストリの `out_sort` 由来)。**MCP でも同じ橋を使います**: `fullseye_import_json`(封筒を引数で受けてハンドル化)と `fullseye_export_json`(ハンドルの中身を封筒 + Markdown で持ち出す)—— どちらも fail-closed・サイズ上限つき(詳細は `docs/MCP.md`)。

## What it does

One JSON form per sort and one way back: a self-describing envelope, float arrays as base64 little-endian float64 (bit-exact round trips, tested with the same probes the op gates use), run-length regions, contours as shape plus point lists, tables as plain JSON. Thin conveniences ride along — `save_json` / `load_json` for a file, `to_json_lines` / `from_json_lines` for a growing ledger as JSON Lines. Unknown sorts, shapes that do not fit the sort and wrong envelope versions are refused — nothing is guessed from an array's shape.

## 向くところ / 向かないところ

**向く**: 結果をファイルに置く・別プロセスや LLM(MCP)に渡す・台帳(bbox / 行 / 特徴)を JSON や JSONL で回す、パイプラインの中間結果の保存と再開。

**向かない**: ★`match` は扱いません(レジストリに 3 要素と 4 要素の慣例が混在しており、JSON にすると片方に固定してしまう —— 慣例を一つにしてから)。★不透明なハンドル(MCP の `fullseye://img/…`)は対象外。★圧縮はしません(base64 は生の 4/3 倍)。大きな体積は `.npy` の方が向きます。

## 最初の 1 本

```python
import fullseye as fs
import numpy as np

pts = np.array([[1.5, 2.0], [3.25, 4.0]])
text = fs.to_json(pts, "points")              # '{"fullseye_sort": "points", "version": 1, ...}'
back, sort = fs.from_json(text)               # (array([[1.5, 2. ], [3.25, 4. ]]), 'points')
assert sort == "points" and np.array_equal(back, pts)

fs.save_json(pts, "points", "pts.json")       # ファイルへ一往復
back2, _ = fs.load_json("pts.json")
print(fs.to_json(np.eye(2) > 0, "region", readable=True))   # run-length で人が読める形

img_json = fs.to_json(np.random.rand(16, 16), "image")
out_json = fs.apply_json(img_json, "gaussian", 1.0, 1.0)    # JSON 入力 → op → JSON 出力
result, sort = fs.from_json(out_json)                        # (array(16, 16), 'image')
```

## 裏づけ

- 実装: `fullseye/jsonio.py`(`JSON_SORTS` に対応する sort の一覧)、MCP 入出口 `fullseye/mcp/server.py`
- 例: [`typed_results_json`](../../examples/typed_results_json.py)
- 試験: `tests/test_jsonio.py`(全配列 sort の bit 一致往復 / op の門と同じ探針の往復 / region の run-length / 非有限値 / fail-closed / table と contour / ファイル往復 / JSON Lines / as_value / apply_json)、`tests/test_mcp_jsonio.py`(import・export の往復と fail-closed・サイズ上限)
