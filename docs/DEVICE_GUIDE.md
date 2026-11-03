# CPU / GPU の選び方

画素ごと、畳み込み、FFT、大きな画像やバッチは GPU の候補になる。逐次依存、不規則な分岐、
優先度キュー、比較整列、小さなデータは CPU が候補になる。ただし速さは推測しない。
装置選択は `fullseye_choose` が返す実測済み候補だけを使い、計測の無い候補は選ばない。

`tools/measure_device_crossover.py` は転送込み・GPU常駐の両方を、代表op名つきで温め後の中央値として測る。GPU の使用状況を確認できない、
計算プロセスがある、またはローカルモデルが載っている場合は何も測らず終了する。生の値と環境は
実行に成功した場合だけ `docs/ops/device_timing.json` を作る。このファイルは未計測環境には存在せず、決定的な再生成検査には含めない。

## GPU の依存の入れ方

- `pip install "fullseye[gpu]"` で torch・kornia・CuPy(`cupy-cuda12x`、CUDA 12 系)が入る。
  CuPy の wheel は Linux と Windows だけなので、macOS では CuPy を入れない(torch と kornia は入る)。
- cuCIM(scikit-image の API を GPU に移したもの)は Windows に wheel が無いので extra に入れていない。
  Linux で使うなら別に `pip install cucim-cu12` を入れる。
