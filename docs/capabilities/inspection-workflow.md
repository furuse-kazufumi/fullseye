---
id: inspection-workflow
title: フォルダを一括検査し、仕様で判定し、集計・SPC・レポート・監査ログまで出す
title_en: Inspect a folder in one call — batch, judge against a spec, aggregate, SPC, report, audit log
category: 組み立てる
ops: [inspect_batch, judge, as_verdict, run_pipeline, spc_ewma, save_xlsx_report, report, to_json_lines]
examples: [inspection_workflow]
version: 0.2.1
---

# フォルダを一括検査し、仕様で判定し、集計・SPC・レポート・監査ログまで出す

## できること

op が 931 本あっても、ライン担当が最初に触る形は「画像フォルダを指して、前処理と計測を決め、仕様で良否をつけ、集計とレポートをもらう」です。`fullseye/inspect_batch.py` の `inspect_batch(folder, recipe, measure=..., spec=...)` はその 1 回の呼び出しで、各画像を **読む → recipe(`run_pipeline` の stages)→ `measure`(計測 op を束ねた callable → dict)→ `judge`(仕様照合)** に通し、行ごとに入力ファイルの sha256・計測値・根拠つきの Verdict・所要時間を返します。数値の計測列は時系列にまとめ、2 点以上あれば EWMA(`spc_ewma`)で工程が管理状態かを添えます。`report_path` の拡張子で `.xlsx` / `.md` / `.jsonl` に書き分け、`audit_path` を渡すと 1 行 1 JSON の監査ログに追記します。

`fullseye/judge.py` の `judge(measurements, spec)` はその判定の入口です。仕様は `{"area": {"min": 10, "max": 15}, "width_mm": {"nominal": 3.0, "tol": 0.05}, "label": {"eq": "OK"}, "grade": {"in": ["A", "B"]}}` の 4 種の規則(境界は含む)で、返り値は PLC が読む語彙(`ok` / `ng` / `error`)の `Verdict` に、違反の一覧 `{key, value, rule, limit}` と人が読む 1 行の根拠が付きます。**黙って ok にしない**のが約束です —— 仕様にあって計測に無いキー、NaN/inf、数値でない値は `error`、規則の綴り間違い(`"mx"` など)は `ValueError` で止まります。1 枚が読めない・op が落ちた場合も既定ではその行を `error` にしてバッチを止めません(`on_error="raise"` で即停止)。入力が 0 枚なら `ValueError`(0 枚を検査して「全部 ok」は報告になりません)。

## What it does

`inspect_batch(folder, recipe, measure=..., spec=...)` is the one call a line operator reaches for first: every image in the folder (or path list, in deterministic order) is loaded, run through the `recipe` (the same stages `run_pipeline` takes), measured by your `measure` callable (any bundle of measurement ops returning a dict) and judged against `spec`. Each row carries the input file's sha256, the measurements, an evidence-carrying `Verdict` and the elapsed time; numeric columns become series and, with two or more points, an EWMA control-chart summary; `report_path` writes `.xlsx` / `.md` / `.jsonl` by extension and `audit_path` appends one JSON line per row. `judge(measurements, spec)` is the entry that turns measurements into the PLC vocabulary (`ok` / `ng` / `error`) with the list of violations and a one-line reason — rules are `min`/`max`, `nominal`±`tol` (inclusive), `eq` and `in`. It never passes silently: missing keys, NaN/inf and non-numeric values are `error`, a misspelled rule is a `ValueError`, a broken image becomes an `error` row without stopping the batch, and an empty batch is refused.

## 向くところ / 向かないところ

**向く**: ロット単位の受入・出荷検査(フォルダ → 良否表)、既存の計測 op(measure1d / shapestat / blob / spc)を束ねて仕様で判定する、レポートを .xlsx で現場に・.md で PR に・.jsonl で機械に同時に出す、判定の根拠(どのキーがどの限界を超えたか)と入力の hash を残して後から突き合わせる、行の Verdict を `signal_verdict` で PLC コイルへ出す。

**向かない**: ★**計測そのもの**(ここは glue —— 何を測るかは `measure` の中で op を呼ぶ)。★**単位換算**(仕様と計測は同じ単位で渡す。ここで mm↔px を換算しない)。★リアルタイムの 1 枚ずつの検査(それは `fsruntime` の Runtime + Verdict の役目。ここはバッチ)。★ゴールデン画像との比較・フィクスチャ管理(次の層)。

## 最初の 1 本

```python
import fullseye as fs

def measure(im):                                   # 計測 op を束ねて dict に
    return {"area": float(fs.apply(im, "area")), "mean": float(im.mean())}

spec = {"area": {"nominal": 400.0, "tol": 60.0},   # 公称 ± 公差
        "mean": {"min": 0.2, "max": 0.6}}          # 下限・上限

out = fs.inspect_batch("lot_0001/", ["gaussian", "otsu"], measure=measure, spec=spec,
                       report_path="lot_0001.xlsx", audit_path="audit.jsonl", title="Lot 0001")
print(out["summary"])                              # {'n': 7, 'ok': 5, 'ng': 1, 'error': 1, 'unjudged': 0}
for r in out["rows"]:
    print(r["hash"], r["verdict"]["status"], r["verdict"]["detail"])
io = fs.open_driver("io-memory")                       # PLC 出口(名簿は fs.drivers())
fs.signal_verdict(io, fs.as_verdict(out["rows"][0]))   # one-hot コイルへ
```

## 裏づけ

- 実装: `fullseye/judge.py`(`judge`: 4 規則・fail-closed)/ `fullseye/inspect_batch.py`(`inspect_batch`, `as_verdict`: 列挙・hash・recipe・計測・判定・series・EWMA・3 系統レポート・監査ログ)
- 例: [`inspection_workflow`](../../examples/inspection_workflow.py)(合成ロット 良品 5・欠陥 1・壊れた 1 を回し、欠陥だけ ng・壊れた 1 枚は error で続行・.md/.jsonl/監査ログ・PLC 出口まで assert)
- 試験: `tests/test_judge.py`(仕様内 ok / 超過 ng+violations / 欠損 error / NaN error / 境界 inclusive / eq・in / 誤字の仕様は ValueError / signal_verdict にそのまま渡せる)/ `tests/test_inspect_batch.py`(決定的順序 / hash・計測・verdict / 欠陥だけ ng・壊れた 1 枚は error で続行 / series→EWMA / .md・.jsonl・.xlsx / 監査ログ追記 / 0 枚・壊れた spec・未知拡張子は拒否)
- 来歴: 新アルゴリズム無し(既存 `run_pipeline` / `spc_ewma`(Roberts 1959)/ jsonio・mdio・xlsxio の配線)。判定語彙は `fsruntime.Verdict` と `device.signal_verdict` に一致。出口は `device.open_driver`(名簿 `device.capabilities()` の driver 名をそのまま渡す)。
