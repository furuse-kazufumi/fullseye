# studio_lite — ブラウザ版 Fullseye Studio-lite(v0、2026-10-25)

Qt の Studio(`studio.py`)の**使える部分だけ**を、1 枚の HTML とブラウザの中の Python(Pyodide)で動かす。
インストール不要、外部 URL を読まない(Pyodide 本体・numpy・scipy・fullseye の部分集合を dist に同梱)、
スマホの Safari / Chrome でも動く。可否の実測は `fullseye_private/notes/studio_web_feasibility_2026_10_25.md`、
探針は `tools/probe_studio_web/`。

## できること(v0)

* 画像を読む(ファイル、同梱サンプル coins / blobs)
* ブラウザで**実測で検証済み**の op(`ops_subset.json`)を並べ、ノブ a / b を Studio と同じ `param_specs` で動かす
* pocviewer の「処理の帯」の流儀で 入力 → 各 op → 出力 を並べ、段ごとの所要 ms(手元の CPython の参考値つき)を出す
* 表示は Studio の描画入口 `studio.apply_display` そのもの(gray / region overlay / shaded relief / height / 疑似カラー 18 種)
* レシピを JSON で保存・読込。形は `engine.FullseyeEngine.to_dict`(`fullseye_pipeline` / `name` / `stages`)で、
  desktop Studio の Open pipeline(`studio.validate_pipeline_dict`)がそのまま読む。逆に Studio が書いた
  bypass 印つきの段も読む
* 段の整合は `engine.diagnose_stages`(Studio の Problems パネルと同じ)
* UI 文字列 8 言語(`i18n.json`、pocviewer.LANGS と同じ並び。`?lang=xx` で切替)

## この版に無いもの(測った数で)

cv2 / torch / mujoco / soundfile を使う op、3-D、バッチ、検索。数字は上記ノートの「後回し」の表。

## 組み方

```
npm i pyodide@314.0.7                                     # repo の外(scratchpad など)に
py -3.11 studio_lite/build_bundle.py --pyodide-dir <node_modules/pyodide> --wheels-dir <numpy/scipy/threadpoolctl の wheel> --out <dist>
py -3.11 <dist>/serve.py 8766                             # http://127.0.0.1:8766/
```

wheel は Pyodide の配布元から初回に取る(`tools/probe_studio_web/pyodide_trial.mjs` が `PYO_CACHE` に置く)。
`file://` では WebAssembly を fetch できないので http で配信する。

## op の台帳 `ops_subset.json` の作り方(実測)

```
py -3.11 tools/probe_studio_web/verify_ops_body.py <out> native
node tools/probe_studio_web/verify_ops_pyodide.mjs <repo> tools/probe_studio_web/verify_ops_body.py <out> min
py -3.11 tools/probe_studio_web/compare_outputs.py <out> native pyodide_min --ops-json studio_lite/ops_subset.json
```

「走った」だけでは入れない —— CPython と **bit 一致か 1 ULP 以内** の op だけが台帳に載る。

## 門

```
node studio_lite/gates/gate_browser.mjs <repo> <out>     # ブラウザ側(Pyodide)で 10 レシピを走らせ JSON と出力を残す
py -3.11 studio_lite/gates/gate_native.py <out>          # engine / Studio の検査で読み直し、ULP で照合(exit 0 = 全部通過)
```

`tests/test_studio_lite.py` は node 無しで見られる分(core の API、レシピの形、台帳と registry の整合、i18n の 8 言語)を CI で守る。
