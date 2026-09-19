---
id: nonfinite-output-was-sanitized-silently
date: 2026-09-19
found_by: degenerate_inputs
kind: silent-wrong
severity: high
where: [backend_safe.py, opassist.py, api.py]
ops: [gaussian, median_image, mean_image, sobel_amp]
gate: [test_partial_nan_input_is_recorded_as_a_nonfinite_output_under_the_default_policy, test_partial_nan_input_stops_under_raise, test_nary_ops_are_found_by_op_find_and_explained_as_list_calls]
status: fixed
---

# NaN を含む画像がフィルタを通ると、NaN が黙って消えて有限の画像になっていた

## 症状

GenSpark の第 3 報(#14)。中央 1 画素だけ NaN の 9×9 画像を `gaussian` / `median_image` / `mean_image` / `sobel_amp` に通すと、**出力は全画素が有限**で、警告も `fullseye.fallbacks()` の記録も無い。`on_error="raise"` でも止まらない。scipy の `gaussian_filter` は NaN を伝播させるので、消しているのは fullseye。

同じ報告の N2: `fullseye.apply([x, y], "add_image")` は動くのに、`op_names()` にも `op_find("add_image")` にも無い(「呼べるのに存在しないと表示される」—— K1 の逆)。

## なぜ門が通したか

全 op を包む `backend_safe.guard` は「有限で sort として妥当な値を返す」を約束し、その実装 `_finite` は **NaN/Inf の画素を sort の既定値で埋めて返す**。約束の前半(有限・妥当)は守っていたが、この repo の原則「**記録し、黙らない**」(`record`、once-per-op の警告、strict では例外)は**例外の経路にしか掛かっていなかった**: op が例外を投げれば記録、op が NaN を返せば無言で埋める。センサ欠損・0 除算・マスク由来の NaN が「正常な有限値」に化け、検査では見逃しに直結する。

`op_names()` は 1 入力のレジストリ(`ops.REGISTRY`)だけ、`op_find()` は台帳 + レジストリだけを見ていて、`imgops_nary` の 17 op はどちらの語彙にも無かった。`list_ops()` には tier `"nary"` として載っていたので「載っていない」ではなく「探す入口が 2 つ盲目」。

## 直し

1. **`backend_safe._note_nonfinite`** —— `sanitize` が置き換える**前に**非有限の件数を数え、`record(name, ValueError("non_finite_output: N of M …"), source="output")` を残す(入力側の非有限の件数も文に入れる)。**strict(`on_error="raise"`)では例外**。置き換えそのものは従来どおり(既定方針の返り値は 1 bit も変わらない)。出力が有限なら何もしない —— NaN を内部で正しく扱う op(`otsu` は NaN を無視して有限の region を返す)は記録も例外も無し。
2. **`opassist.op_find`** —— n-ary 層(`imgops_nary.build_nary()`)を同じ採点で検索し、`ledger: "nary"`、`call: "apply([x0, x1], name)"` で返す。
3. **`api.op_names` の docstring** —— n-ary は載らない理由と在処(`list_ops()` の tier `"nary"`、`op_find`)を書く。`op_names()` の数(931)は変えない(README / 索引の門が数えている)。

**門が最初に捕まえたもの**: 全 op の構造探針(`tests/test_op_probe_ledger`)で `tb_fly_tau_from_expansion` が 256 標本中 125 を NaN で返していた。これは元の関数 `fly_tau_from_expansion` が「膨張していない標本の time-to-contact は NaN(数を発明すると plausible-wrong)」と**仕様として書いている**もので、レジストリ版は有限契約のために signal の既定値で埋める。仕様の NaN まで fallback と数えると門が常に赤になるので、`backend_safe.NONFINITE_BY_DESIGN` に**docstring に理由が書いてある op だけ**を載せて除外する(いまは 1 本)。

**変えなかったもの**: 部分 NaN の**入力**を門で断ることはしない(NaN を「無効」として扱う op があり、`_check_input_range` も `nanmin` で NaN を許している)。断るのは「黙って有限にする」ことで、NaN を受けて有限を返す op は、それが記録されていれば正当。
