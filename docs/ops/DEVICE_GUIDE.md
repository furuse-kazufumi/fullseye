# CPU / GPU の選び方

画素ごと、畳み込み、FFT、大きな画像やバッチは GPU の候補になる。逐次依存、不規則な分岐、
優先度キュー、比較整列、小さなデータは CPU が候補になる。ただし速さは推測しない。
`OP_DEVICE.json` の `gpu_timing` が `unmeasured` の op は未計測として返す。

`tools/measure_device_crossover.py` は転送込みで大きさとバッチを測る。GPU の使用状況を確認できない、
計算プロセスがある、またはローカルモデルが載っている場合は何も測らず終了する。生の値と環境は
`docs/ops/device_timing.json` に書き、決定的な再生成検査には含めない。
