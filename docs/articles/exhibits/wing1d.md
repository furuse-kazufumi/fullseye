<!-- tools/gen_wing1d_gallery.py が自動生成。記事 md への挿入候補であり、
     このファイル自体は記事ではない。数値はすべて生成時の実測値。 -->

# 信号・音響・1D ウィング — 展示キャプション原稿

生成元: `tools/gen_wing1d_gallery.py`(`py -3.11 tools/gen_wing1d_gallery.py`)。
画像はすべて Fullseye の `imagedraw` op と numpy 合成で描いており(matplotlib 不使用)、
図に焼いた数値は 1 つ残らずその場で op を呼んで得た実測値である。乱数は seed 固定、
掃引格子も固定なので再生成でバイト列が一致する(`--verify` で検査)。

束ね方は `tools/exhibit_tile.py` の 3 種に従う ―― **コマ送り GIF**(`flipbook`、
掃引と工程。各コマに工程名と `i/N` の進捗バーが焼いてあるので止めても意味が分かる)、
**タイル**(`contact_sheet`、同じ軸にパラメータ違いを当てた小さなプロットを束ねる)、
**原寸 1 枚**(主張そのもの・軸と数値が読めないと意味が無い図)。静止画の Markdown は
すべて **サムネイル表示 + クリックで原寸** の形で出してある。

## 14. 分数オクターブ帯域 ―― 偶数分数には 1 kHz 帯域が無い

[![分数オクターブ帯域 ―― 偶数分数には 1 kHz 帯域が無い](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing1d_octave_family_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wing1d_octave_family.png)

*↑ **分数オクターブ帯域 ―― 偶数分数には 1 kHz 帯域が無い** ―― 振幅 0.7 の 1000 Hz 純音を、1/1・1/2・1/3・1/6・1/12・1/24 オクターブで測った 6 枚。帯域レベルはどの分数でも閉形式 10log10(A²/2) = -6.108339 dB を返す(最大差 0.0e+00 dB)。違うのは**どの帯域が**それを報告するかで、fraction が奇数 [1, 3] では 1000.000 Hz ちょうどを中心とする帯域があるが、偶数 [2, 6, 12, 24] では指数のオフセットにより 1000 Hz が帯域**端**になり、同じエネルギーが 1188.50 Hz, 944.06 Hz, 971.63 Hz, 1014.50 Hz を中心とする半端な帯域から報告される。定義であって不具合ではないが、「1 kHz でのレベル」を引用するときに知っていないと嘘になる。空の帯域は −inf ではなく床(−200 dB)に落ちる。 使用 op: `octave_bands`, `octave_spectrum`。*

- PNG(タイル): `docs/articles/assets/wing1d_octave_family.png` (1458x828 px, 59 kB, 6 パネル / 3 列)
- サムネ(記事はこちらを表示): `docs/articles/assets/wing1d_octave_family_thumb.jpg` (50 kB)
- 束ね方: sheet
- SHA-256: `06a8435b683e6a4dc6d17c36ceebe947a546dd613faf6bcee3f4266b158c0d53`

<details><summary>この図に焼いた実測値</summary>

```json
{
  "tone_hz": 1000.0,
  "tone_amplitude": 0.7,
  "rate_hz": 48000.0,
  "duration_s": 0.5,
  "closed_form_db": -6.108339156354676,
  "max_abs_diff_from_closed_db": 0.0,
  "fractions_with_exact_1k": [
    1,
    3
  ],
  "fractions_without_exact_1k": [
    2,
    6,
    12,
    24
  ],
  "table": [
    {
      "fraction": 1,
      "n_bands": 10,
      "max_level": -6.108339156354676,
      "max_center": 1000.0,
      "exact_1k": true,
      "diff_from_closed": 0.0,
      "clamped": 9,
      "total_level": -6.108339156354676,
      "nominal_at_max": 1000.0,
      "bandwidth_at_max": 704.5917602386166
    },
    {
      "fraction": 2,
      "n_bands": 20,
      "max_level": -6.108339156354676,
      "max_center": 1188.5022274370185,
      "exact_1k": false,
      "diff_from_closed": 0.0,
      "clamped": 19,
      "total_level": -6.108339156354676,
      "nominal_at_max": 1190.0,
      "bandwidth_at_max": 412.53754462275447
    },
    {
      "fraction": 3,
      "n_bands": 30,
      "max_level": -6.108339156354676,
      "max_center": 1000.0,
      "exact_1k": true,
      "diff_from_closed": 0.0,
      "clamped": 29,
      "total_level": -6.108339156354676,
      "nominal_at_max": 1000.0,
      "bandwidth_at_max": 230.76751616821775
    },
    {
      "fraction": 6,
      "n_bands": 59,
      "max_level": -6.108339156354676,
      "max_center": 944.0608762859234,
      "exact_1k": false,
      "diff_from_closed": 0.0,
      "clamped": 58,
      "total_level": -6.108339156354676,
      "nominal_at_max": 944.0,
      "bandwidth_at_max": 108.74906186625446
    },
    {
      "fraction": 12,
      "n_bands": 118,
      "max_level": -6.108339156354676,
      "max_center": 971.6279515771062,
      "exact_1k": false,
      "diff_from_closed": 0.0,
      "clamped": 117,
      "total_level": -6.108339156354676,
      "nominal_at_max": 972.0,
      "bandwidth_at_max": 55.939123714076686
    },
    {
      "fraction": 24,
      "n_bands": 237,
      "max_level": -6.108339156354676,
      "max_center": 1014.4952080687361,
      "exact_1k": false,
      "diff_from_closed": 0.0,
      "clamped": 236,
      "total_level": -6.108339156354676,
      "nominal_at_max": 1010.0,
      "bandwidth_at_max": 29.200527194428332
    }
  ]
}
```

</details>
