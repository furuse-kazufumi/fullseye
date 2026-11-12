# パラメータを束で持ち、ファイルから読んで op に渡す

引数が多い op の呼び出しを、Python の中で 1 つずつ書かずに済ませるための層です。パラメータを **束(`ParamBundle`)** にして、JSON / TOML / YAML のファイルから読み、op には**その op が受ける引数だけ**を渡します。画面には依りません(束を閲覧・編集する窓は別の話で、この層はその土台です)。

台帳 2,879 op のうち、引数が 6 個以上のものが 873 本あります。カメラ K とレンズ系はすでに束で渡していますが、波長・画素ピッチ・焦点などは 1 つずつ並べていて、同じ量が綴りと単位で割れています(画素ピッチ 3 綴り、波長 `_um` と `_nm`)。束はこの割れを 1 か所で吸収します。

```python
import fullseye as fs
```

## 1. カメラの束を読んで undistort に渡す

`rig.toml`(人が書く。コメントが書ける):

```toml
[camera]
fx = "1200 px"        # 値と単位を文字列で
fy = "1200 px"
cx = 640.0            # 単位の無い数
cy = 480.0
dist = [-0.12, 0.03, 0.0, 0.0, 0.0]
[lens]
wavelength = "550 nm"
focal = "25 mm"
f_number = 4.0
[sensor]
pixel_pitch = "3.45 um"
```

```python
p = fs.load_params("rig.toml")
p.fx, p["camera.fx"], p.camera.fx        # どれも同じ(p.fx は fx という葉が 1 つだけのとき)
p.origin("fx")                           # Origin(source='rig.toml', key='camera.fx', line=None, ref=None)

kw = p.for_op("undistort_image")         # {'K': 3x3 ndarray, 'dist': ndarray(5,)}  — その op の引数だけ
out = fs.undistort_image(img, **kw)      # 素の Python のまま、何が渡るか見える
out = fs.run_params("undistort_image", img, params=p)   # 同じことの糖衣
```

`for_op` が何をしたかは記録として取れます。

```python
kw, rep = p.for_op("airy_pattern", report=True)
print(rep.text())
# airy_pattern (rig.toml)
#   wavelength_um <- lens.wavelength [synonym] (550 nm -> 0.55) nm -> um
#   f_number <- lens.f_number [exact]
#   pixel_pitch_um <- sensor.pixel_pitch [synonym] (3.45 um -> 3.45)
#   unused: camera.fx, camera.fy, ...
```

`K` は束に `K` が無ければ、同じ節の `fx, fy, cx, cy`(任意で `skew`)から作ります(`p.K()`、`p.camera.K()`)。固定の導出だけで、式は書けません。

`fs.apply` の契約も、既存の op の引数も変えていません。`fs.run_params` は別の入口です。`**p` の丸ごと展開は勧めません(op が受けないキーで TypeError になります)。

### 黙って捨てない

| 状況 | どうなるか |
|---|---|
| 束のキーがどの引数にも当たらない | `fs.run_params` は実行後に `ParamWarning` で一覧にする。`strict=True` なら実行前に `UnusedParams` |
| op の必須引数が束から作れない | `MissingParam`。**必要な名前・束にある名前・導出の手がかり**を 1 つの文に入れる |
| 単位違い(`focal = "25 px"` を `focal_mm` に)| `UnitMismatch` |
| 単位の無い数を、単位つきの引数名(`_um` など)へ | `UnitMismatch`(キー名に単位を書くか `"3.45 um"` と書く) |
| 型違い(整数の引数に 3.5、数の引数に文字列)| `ParamTypeError` |
| 同じ名前の葉が複数の節にある | `AmbiguousParam`(`[op名]` の節で解く) |
| 束のキーが 1 つも当たらない(引数が全部既定値つきの op) | `for_op` は空の dict を返す。`require_any=True`(または `strict=True`)なら `MissingParam`(op が探した引数名と束のキーを添える)。`fs.run_params` は `ParamWarning` を出して既定値で走る |

引数への当て方の順は、`[op名]` の節(例: `[gaussian] sigma = 1.5`)→ 引数名の完全一致 → 同義の綴り(下の表)→ 固定の導出、です。明示のキーワード引数(`fs.run_params(..., K=K2)`)は束より優先します。進化する 2-D op(`fs.apply` の a / b つまみ)は `[op名].a` / `[op名].b` を読みます。

## 2. 単位と同義の綴り

単位は **op の引数名の接尾辞**(`wavelength_um`、`focal_mm`、`angle_deg` …)が決めます。束には書かれた値と単位をそのまま持たせ、**使うとき 1 回だけ**変換します。

- 10 の冪の単位(`m cm mm um nm pm`、`s ms us ns`、`hz khz mhz ghz`)は `Decimal` で厳密に変換します。`550 nm` → `0.55 um` は、`v * 1e-3` だと 10 万個の乱数のうち約 2 万 3 千個が 1 ULP ずれるところを、1 個も外しません。
- `deg` と `rad` は丸めが避けられないので、変換先は引数名が決め、結果を束へ書き戻しません。
- 束の中の値は変換されません(`p["lens.wavelength"]` は `550 nm` のまま)。

同義の綴りの表(`fs.parambundle.SYNONYM_GROUPS` が正本):

| 量 | 同じとみなす綴り(単位の接尾辞を除いた幹)|
|---|---|
| 波長 | `wavelength` `wl` `lambda` |
| 画素ピッチ | `pixel_pitch` `pixel` `pixel_size` |
| 焦点 | `focal` `focal_length` `efl` |
| F 値 | `f_number` `fnumber` `fnum` `fno` `f_no` |
| 開口数 | `na` `numerical_aperture` |
| 露光 | `exposure` `exposure_time` `t_exp` |
| 量子効率 | `qe` `quantum_efficiency` |

入れていない綴り: `pitch`(格子のピッチと画素ピッチを黙って取り違えるため)、`f`(周波数と衝突)。必要なら束に `pitch_um = 1.6` と引数名どおりに書きます。

## 3. 重ね合わせ・参照・include

```python
q = p.merged(fs.load_params("rig_night.toml"))   # 基本 + 上書き。上書きしたキーの出どころは後者
r = p.with_(**{"camera.fx": 820})                # 既にあるキーの差し替え(元は不変、出どころは "<code>")。無いキーは ParamError
s = p.added(**{"camera.k4": 0.1})               # 新しいキーを足すときは明示の added
p.diff(r)                                        # {'camera.fx': (1200 px, 820)}  意味として違うキーだけ
```

- `with_` は**既にあるキーだけ**を差し替えます。`camera.fxx` のような打ち間違いは `ParamError`(もしかして: `camera.fx`)で、足したいときは `added`。`param_grid` / `param_zip` の軸も同じで、新しいキーの軸は `allow_new=True`。
- `merged` は束同士の重ね合わせなので、上に重ねた側にしか無いキーも入ります。入ったかどうかは `fs.params_compare([基本, 重ねた結果])` で `partial`(一部の束に無い)の行として確かめられます。
- **参照**: `{"$param": "camera.fx"}`(JSON / YAML)、`fx = { ref = "camera.fx" }`(TOML)。読むとき 1 回で解決し、循環と未解決は断ります。文字列 `"camera.fx"` は参照ではありません。
- **include**: 最上位の `include = ["base.toml"]`。**そのファイルと同じ階層以下だけ**で、`..`・絶対パス・シンボリックリンク(Windows のジャンクションも)は断ります。入れ子は 8 段まで、循環は断ります。後に書いた物が先を上書きします。
- 束に式や任意のコードは書けません(YAML も `safe_load` のみ)。

## 4. 複数の束を並べて比べる

```python
cmp = fs.params_compare([p, q, r])      # キー = 行、束 = 列
print(cmp.text())
cmp["lens.wavelength"].status           # 'same' / 'differ' / 'partial'(一部の束に無い)
```

`"0.55 um"` と `"550 nm"` は**同じ**と判定します(書き方が違うことは `notation_differs` に残ります)。単位の次元が違う物、数と単位つきの数、真偽と数は別物です。`cmp.table()` は文字の表(1 行目が見出し)で、窓の段組表示の材料になります。

## 5. 走査

```python
grid = fs.param_grid(p, **{"lens.f_number": [2.8, 5.6, 11.0], "sensor.pixel_pitch": ["3 um", "4 um"]})   # 直積 6 束
len(grid), grid.points()[0]
rows = fs.sweep(lambda b: fs.ledger.airy_pattern(**b.for_op("airy_pattern")), None, grid,
                metric=lambda r: float(r.sum()))
# 各行: {'index': 0, 'lens.f_number': 2.8, 'sensor.pixel_pitch': '3 um', 'value': ..., 'error': None}
```

- `fs.param_zip` は同じ長さの軸を 1 つずつ組にします(直積ではない)。
- 直積の件数が `max_points`(既定 10,000)を超えるときは、件数と見積もり(束を全部持った場合のメモリ、実行回数)を先に出して `GridTooLarge` で断ります。
- `fs.sweep(op, x, grid, metric=...)` の `op` は op 名(`fs.run_params` で走る)か、束を受ける関数です。失敗は既定で例外、`on_error="record"` なら行の `error` に残します。段の列(パイプライン)全体の実行は扱いません。

## 6. 書く

```python
fs.save_params(p, "out.json")           # JSON だけ。allow_nan=False、同じフォルダの一時ファイル → 置き換え(原子的)
```

TOML / YAML への書き出しと、コメントを保つ差分書き込みはしません(JSON にコメントは無く、`tomllib` は読むだけです)。「人が書く形式は TOML / YAML、機械が書く形式は JSON」と割り切っています。参照と `include` は展開した値で書かれ、出どころは書かれません。

## 7. 形式と門

| 形式 | 読み | 備考 |
|---|---|---|
| JSON | 標準 | コメント・末尾カンマ・`NaN` は断る。キー重複は断る |
| TOML | 標準 `tomllib`(読むだけ)| コメント可。`1e-3` は float。日付は文字列へ |
| YAML | **optional**(`pip install "fullseye[yaml]"`)| `safe_load` だけ。下の門 |
| JSONC / JSON5 | 受けない | 1 つの読み手に 1 つの文法。手書きは TOML |

YAML は YAML 1.1 の罠が多いので、読んだあとに門を置いています。

- **素のスカラーは YAML 1.2 の core schema で読みます**(真偽は `true` / `false` だけ、8 進は `0o10` だけ、60 進は無し、`1e3` は float)。
- **YAML 1.1 なら別の値になる、引用符なしのスカラーは断ります**(黙ってどちらかに解釈しない): `yes` `no` `on` `off` `y` `n` とその大文字小文字違い(`NO` は False になる)、先頭 0 の整数(`010` は 1.1 で 8)、コロン入りの数字(`12:30:00` は 1.1 で 45000)、`0b101`、`1_000`。行番号つきで「引用符で囲むか、`true`/`false`・`0o10`・秒の数で書く」と言います。引用符で囲めば文字列として通ります(`'NO'`)。
- `1.10` は float として正しいので `1.1` で通ります。**版番号(`ver: 1.10`)に使うと末尾の 0 が消える**ので、版は文字列(`"1.10"`)で書いてください。
- 数の欄(`_um` などの単位つきの名前や `wavelength` など)の文字列・真偽は、どの形式でも断ります。
- キー重複(PyYAML は後勝ちで黙る)は断る。アンカー / エイリアスは展開後の節点数 10 万・深さ 100 を超えたら断る(billion laughs)。循環も断る。
- 日付・日時は文字列にする。`null` / `~` / 空の値は断る。`.inf` `.nan` は断る(束は有限の数だけ)。
- 行番号の出どころ(`p.origin(key).line`)が取れるのは YAML だけです。TOML と JSON はファイル名とキーの経路までです。

値は「数」「数 + 単位の文字列」「配列」「文字列」「真偽」です。`null` と、配列の中の表は受けません。単位として受ける綴りは `m cm mm um nm pm`、`s ms us ns`、`hz khz mhz ghz`、`px`、`deg rad`(`µm` `°` `Hz` も可)。
