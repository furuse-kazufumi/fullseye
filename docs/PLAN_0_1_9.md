# 0.1.9 の作業計画

0.1.8 を出したあとに着手する。**根拠はすべて 0.1.8 までに実測したもの**で、
出どころは `docs/KNOWN_ISSUES.md` の #21 / #27 / #29 / #30 と
`tests/test_op_knob_liveness.py` の台帳。推測で足した項目は入れていない。

## 完了条件

1. 「配線できるのに固定している」9 箇所が配線され、**既定値 (a,b)=(0.5,0.5) で
   0.1.8 とビット一致**であることが自動で確かめられる
2. 触れた op の説明が実装と合っていて、**6 言語すべてが 1,722 / 1,722 のまま**
3. `hx_test_self_intersect` が O(n^2) の総当たりでなくなり、**出力はビット一致**
4. `matplotlib` への隠れ依存が無くなる(deptry の唯一の実害)
5. `backend_safe.fallback()` の未検査の枝にテストが付く(変異テストの生き残り)

## 段 -1(最優先)— CI の赤を落とす

**0.1.6 / 0.1.7 / 0.1.8 と、Linux CI は赤のまま出している**(26〜28 失敗 /
10,808 通過)。ローカル Windows が緑なのを門にしていたのが誤りで、
**赤い CI の下では他のどのゲートも信用できない**。ここを最初に直す。

失敗の大半は 1 つの原因に集まっている —— **CI は torch / kornia を入れない方針**
(サイズと時間。GPU の数字は実機で測る)なので、そこで組み上がるレジストリは
Windows 開発機のものより小さい。ところが台帳・指紋・ギャラリーの不変条件は
**開発機のレジストリを前提に書かれている**。

| 群 | 失敗 | 中身 |
|---|---|---|
| レジストリ差 | 約 12 | `test_index_fingerprint_matches_the_live_registry` / `test_notes_match_generator_no_drift` / `test_op_catalog_matches_generator_no_drift` / `test_backend_doc_tables_do_not_name_ops_that_do_not_exist` / `test_coverage_gallery_runs[...]` 5 件 / `test_example_gallery_runs` |
| kornia アダプタ | 約 6 | `test_sobel3d_adapter_drops_conv_batch_axes` / `test_refine_rotation_z_adapter_yields_scalar_angle` / `test_position_canon_is_three_components` ほか |
| Windows 前提 | 1 | `test_read_image_cannot_leave_base_dir` が `C:/Windows/win.ini` を使っている |
| 要調査 | 約 8 | `test_polar_unwrap_rejects_degenerate_shape` / `test_float32_overflow_rejected_not_silent_nan` / `test_nothing_leaks_a_nonfinite_number` / `test_text_that_cannot_fit_raises_instead_of_being_clipped`(Linux のフォント?)ほか |

**方針**: torch を CI に入れて誤魔化さない(方針を曲げることになる)。
不変条件の側を**「いまここに在る op について正しいか」**を見る形に変える ——
文書は開発機の全レジストリから生成し、CI では**存在する op の部分集合**として
突き合わせる。指紋も「生成時のレジストリ」を刻んで比較する。
最後の「要調査」群は 1 件ずつ実測してから分類する(まとめて environment のせいに
しない —— 本物の不具合が混ざっている可能性がある)。

**ゲート**: `gh run list --workflow=ci.yml` が緑。以後、**赤い CI でタグを打たない**。

## 順番と、その順番にした理由

配線 → 説明 → 訳、の順は動かせない。**訳は原文の指紋で紐づいている**ので、
説明を 1 文字変えるとその op の訳 5 言語が「未訳」に落ちる(#30)。
1 件ずつ直して都度訳すと 6 言語 100% が何度も崩れるので、
**コードを全部直してから、触れた op だけをまとめて 1 度訳す**。

### 段 0 — ビット一致の基準を repo に固定する(最初にやる)

いまの基準値は**セッションの一時ディレクトリにしかない**(18 op の指紋)。
消えると「変わっていないこと」を証明できなくなるので、
`tests/data/knob_wiring_baseline.json` として **commit する**。

- 生成: 各 op を `(0.5, 0.5)` で `op_probe.sample_probes` の固定入力に掛け、
  出力の SHA-256 先頭 16 桁
- 検査: `tests/test_knob_wiring_parity.py` が 18 op 全部を突き合わせる
- **この段だけは 0.1.8 のコードに対して作る** —— 変更前の値でないと基準にならない

### 段 1 — 配線 9 箇所(コードだけ、説明はまだ触らない)

規則は 1 つ: **`b=0.5`(既定)で現行の固定値になる式を選ぶ**。
そうすれば段 0 の基準に対してビット一致が保て、既存の進化結果・pin・
サンプル出力が動かない。

| 箇所 | いまの固定値 | 配線先 |
|---|---|---|
| `backends_auto._sh_xld`(lines_gauss 分岐) | `frangi(sigmas=range(1,4))` | `b` → σ の上限。`range(1, 2+round(b*4))` |
| `backends_auto._sh_segment` | `chan_vese(max_num_iter=60)` | `b` → 反復回数 |
| `backends_auto._sh_geom` | `swirl(radius=30)` | `b` → 半径 |
| `backends_auto._sh_cooc` | `graycomatrix(angles=[0.0])` | `b` → 方向(いまは **1 方向しか見ていない**) |
| `backends_auto._sh_diffusion` | `denoise_nl_means(patch_size=5)` | `b` → パッチ径(奇数) |
| `backends_extra._watershed_markers` | `dilate(iterations=3)` | `b` → 反復回数 |
| `backends_filters2.f2_shock` | `grey_dilation/erosion(size=3)` | `b` → 構造要素の径(奇数) |
| `backends_ski2._hog` | `orientations=8` | `b` → 方向ビン数 |
| `backends_halcon_ext._histo_to_thresh` | `histogram(bins=64)` | `b` → 量子化の粗さ(2 の冪) |
| `ops._vol_median` | `median_filter(size=3)` | `a` → 窓径(#21。`b` は別途) |

**先に確かめること**: 上の表は AST で「`a`/`b` に依存しない数値」を拾ったもので、
**その op の `b` が本当に空いているかは別**。`lines_gauss` は確認済み
(`a` がしきい値 `0.1+0.4a` に使われ、`b` が空いている)。残りは
`tests/test_op_knob_liveness.py` の実測台帳と突き合わせてから触る ——
既に効いているノブを上書きしたら、それは配線ではなく破壊。

**配線しないもの**(規約であってノブではない、と判断した根拠を残す):
`border_value` 3 件 / `histogram(range=(0.0,1.0))` / `_fin(default=1.0)`。

**兄弟一掃の宿題**: `sk_frangi` は 0.1.3 で同じ `sigmas=range(1,4)` を配線済み
だったのに、`backends_auto` の同型コードが残っていた。今回は
**同じ形の固定値を全ファイルで grep してから**着手する(1 件直して同クラスを
放置する、を繰り返さない)。

### 段 2 — 説明を実装に合わせる(触れた op だけ)

「``b`` は未使用」が嘘になるので書き直す。**日本語の原文を直すだけ**で、
この時点では訳を触らない。

### 段 3 — 5 言語をまとめて訳す(1 回だけ)

`docs/i18n/op_summary.json` で未訳に落ちた op を列挙し、
**op ごとに 5 言語をまとめて**作る(原文を 1 回読んで 5 言語出す)。規約は 0.1.8 と同じ:

- 限定の言葉(「〜に相当する近似」「``b`` は未使用」)を断定に変えない
- 繁体字(`tw`)は簡体字の機械変換にしない
- ドイツ語の Umlaut を ASCII に潰さない

**ゲート**: `docs/I18N.md` の表が再び 6 言語 × 全 op になること。

### 段 4 — `hx_test_self_intersect` のベクトル化(#27)

プロファイラ 3 種が独立に指した唯一のホットスポット。
`tests/test_op_knob_liveness.py`(約 31 秒)の中だけで `ccw` が **276 万回**。

- **numpy で総当たりをベクトル化する**(掃引線には**しない**)。数式が同じなので
  **出力をビット一致にできる**方から入る。掃引線は数値の縁で結果が変わりうる
- 点数の 2 乗のメモリを使うので**上限を決めて**、超えたら現行の逐次経路へ落とす
- ゲート: 交差する / しない輪郭の両方で `(before, after)` が一致 + 実測の短縮幅を記録

### 段 5 — `matplotlib.path.Path` を自前の `point_in_polygon` に置き換える

`contours_xld.py` の 1 箇所。deptry が挙げた 302 件のうち**唯一の実害**
(宣言していない依存を import している)。repo には自前の実装が既にある。

- ゲート: 置き換え前後で判定がビット一致 + `polygon` extra を消せることを確認
- 副産物: 最小構成(numpy+scipy のみ)の CI ジョブが 1 つ強くなる

### 段 6 — `fallback()` の未検査の枝を埋める

変異テスト(WSL / mutmut、`backend_safe.py` に 563 変異)の生き残り 146 のうち
**89 が `fallback()`、33 が `_finite()`**。0.1.8 で contour / color / match /
feature の枝には直接テストを付けたので、**残りを数え直してから**足す。

- まず WSL でもう一度掛けて、0.1.8 後の生き残り数を測る(減っているはず)
- 減っていない枝にだけテストを書く —— 数字を見ずに書くと、また同じ場所を厚くする

## この版でやらないこと

- `docs/OP_CATALOG.md` と知識ガイド 12 本の翻訳(v1.0.0 のゲート。分量が別格)
- 掃引線 / 空間索引による自己交差判定(段 4 のベクトル化で足りるか測ってから)
- VS Code 拡張
- デバッグ道具の記事(読み手の関心から外れる、と判断)

## 各段の検証コマンド

```
py -3.11 -m pytest tests/test_knob_wiring_parity.py -q        # 段 0/1
py -3.11 -m pytest tests/test_op_knob_liveness.py -q          # 段 1(台帳が縮む)
py -3.11 -m pytest tests/test_fsi18n.py tests/test_opdocs.py -q  # 段 2/3
py -3.11 -m pytest tests/test_backend_safe.py -q              # 段 6
ruff check .
py -3.11 -m pytest -q                                          # 全数(約 26 分)
```
