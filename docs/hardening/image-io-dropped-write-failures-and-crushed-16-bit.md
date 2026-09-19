---
id: image-io-dropped-write-failures-and-crushed-16-bit
date: 2026-09-20
found_by: genspark_external_review
kind: silent-wrong
severity: high
where: [api.py, imgio.py, ops.py, dsp.py]
ops: []
gate: [test_write_refuses_a_missing_directory_instead_of_pretending, test_write_refuses_an_unwritable_extension_naming_the_writable_ones, test_ppm_takes_a_grey_image_and_reads_back, test_read_errors_say_which_kind_of_failure, test_uint16_is_written_as_16_bit_and_float_depth_options_are_lossless, test_float_default_is_8_bit_as_documented_and_depth_needs_a_capable_extension]
status: fixed
---

# write_image が書けなかった事実を捨てて無言で戻り、uint16 が 8 bit に潰れ、読めない理由が全部「無い」だった

## 症状

GenSpark 第 18・19 報(N75 / N76 / N77 / N78 / N79、N72 の同族、N81 の音声分)。全部 master で再現した。

- **N76 / N79(高)**: `fullseye.write_image("x.ppm", grey)` と `write_image("no_dir/x.png", img)` は **戻り値 None・例外なし・ファイル無し**。`cv2.imwrite` は失敗を False で返すだけで、facade はそれを見ていなかった。ppm は OpenCV の PxM エンコーダが 3 ch を要求する(灰は失敗)。
- **N77(低)**: 書けない拡張子で OpenCV の内部パス(`loadsave.cpp:1072`)と `(-2:Unspecified error)` がそのまま出て、何なら書けるのかは分からない。
- **N78(低)**: `read_image` は無い・ディレクトリ・壊れたファイル・拡張子なし・空文字の全部が `FileNotFoundError: <path>`。
- **N75(中)**: float を書いて読むと dtype は float64 のまま値が 256 段階に丸まる(max|Δ| = 0.0039)。加えて実測で見つけた非対称: **`uint16` を書くと上位 8 bit に潰れる**(`imgio.save` は `to_uint8`、facade は `>> 8`)のに、`imgio.load` は 16 bit を 65535 で割って **無損失に読む**。pfm も uint8 の値を float32 に入れて往復が合わなかった(max|Δ| = 0.995)。
- 同族: `ops._norm` は 0 要素で `np.max` の生 numpy 文を出す(姉妹の `backend_safe.signed01` は size を見ていた)。`read_wav` / `read_audio` の不在ファイルは OS の errno 文のまま。

## なぜ門が通したか

- facade の I/O は `imgio` と別実装で(cv2 直呼び)、`imgio.save` が 2026-09-03 に「失敗は OSError に正規化」した直しが facade には及んでいなかった([[feedback_same_bug_class_recurs_check_siblings]])。I/O のテストは `imgio` 側にあり、facade の `write_image` は Studio のテストが「呼べる」ことしか見ていなかった。
- 深度は「読みは 16 bit を保つ」を 0.1.x で入れたとき、書きを対にしなかった。float の 8 bit 量子化は仕様だが、docstring に段階数が書かれていなかった。

## 直し

1. **facade は imgio に委譲**: `read_image` → `imgio.load`、`write_image` → `imgio.save`(`depth` を通す)。
2. **`imgio.save`** は書く前に止める: 拡張子なし → ValueError、書けない拡張子 → `OSError`(この環境で書ける一覧つき、`writable_extensions()`)、親ディレクトリ不在 → `FileNotFoundError`(ディレクトリは作らない、と文で言う)。`.ppm` の灰は 3 ch に複製、`.pgm` に色は ValueError。cv2 の失敗は dtype とチャネル数を添えた 1 文。
3. **深度**: `depth=None` は dtype を尊重 —— `uint16` は 16 bit(PNG / TIFF)、それ以外は 8 bit。float の既定は **8 bit = 256 段階と文書化**(往復誤差 1/510)。`depth=16`(PNG / TIFF、1/131070)、`depth="float"`(PFM / TIFF、float32、~1e-7)。対応しない拡張子との組は ValueError。
4. **`imgio.load`**: None / 空 → TypeError、ディレクトリ → `IsADirectoryError`、無い → `FileNotFoundError("no such image file")`、読めない → ValueError(従来)。
5. `ops._norm` は 0 要素をそのまま返す。`dsp` の読み手は不在で `FileNotFoundError("read_wav: no such file: …")`、ディレクトリで `IsADirectoryError`。

**同じ報で設計・次回として分けたもの**:

| 指摘 | 判断 | 理由 |
|---|---|---|
| N75 float 保存に警告を出す | 採らない(文書化) | 8 bit は画像ファイルの既定の契約で、毎回の warn は産業ラインでは雑音。段階数と `depth` を docstring に明記し、無損失の口を足した |
| N79 親ディレクトリを作る | 採らない | 書き先を黙って作るのは副作用。無いことを 1 文で言う |
| N80 `run_pipeline([A, B], ["add_image"])`(第 19 報) | 次回候補 | 第 7 陣で「段は 1 入力」と決めたが、**先頭段だけ n-ary を受けてリストを消費する**拡張は apply の規約と整合する。engine / CLI run と一緒に別の回で |
| N81 read_* の流儀 3 種(第 19 報) | 次回候補(音声分は済) | `read_depth` / `read_mesh` の文を雛形に read_envi / read_frames / read_gltf / read_las / read_pcd / read_pfm / read_volume を揃える |
| N82 退化入力の層ごとの不揃い(第 19 報) | 0.2.0 のみ | master は入口の門で一様(`test_empty_input_contract_is_uniform_across_ops`) |
| N83 `has` の「not in the HALCON reference」(第 19 報) | 0.2.0 のみ | 第 3 陣で「neither an op name, a HALCON alias, nor a HALCON reference operator」に直し済み。rc は argparse の使い方誤り = 2、アプリの失敗 = 1 の 2 段で、揃えない |
| N65 `--version` が rc 2(第 19 報の再確認) | 0.2.0 のみ | 第 6 陣で `action="version"` |
| `fullseye.engine` が無い(第 19 報) | 設計 | エンジンは `fullseye.FullseyeEngine`(facade)。`engine` はトップレベルのモジュール名で、`fullseye.engine` という属性は元から無い |
