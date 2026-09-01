<!-- tools/gen_wingevo_gallery.py が自動生成。記事本体 (docs/articles/*.md)
     はこのファイルからは触らない。 -->

## 進化とオペレータ品質保証ウィング

この翼で見せるのは、**アルゴリズムが設計されていく様子**と、**バグが見つかる様子**
です。どちらも本来は数字とログの世界にあるので、ここでは可視化そのものを設計して
います。数字はすべて実測で、実走したものと過去の記録から引いたものを区別して
書いてあります。分割の呼び分けは 1 か所だけ覚えてください ―― **観測用 holdout**
(`seed+10000`、毎世代スコアを見るが選択には使わない)と、**locked holdout**
(`seed+20000`、最終 champion に一度だけ当てる)は別物です。

再生成: `py -3.11 tools/gen_wingevo_gallery.py`


### 1. 進化した champion の実力

[![光子計数ヒストグラムのデノイズ(counts)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_champion_photon_denoise_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_champion_photon_denoise.png)

*↑ **光子計数ヒストグラムのデノイズ(counts)** ―― 同じ locked holdout(``seed+20000``、champion に一度だけ当てる分割)で測り直した実測。恒等 0.4174 / 手 0.5536 / 進化 0.7845(1/(1+mse of shape))= 手比 +41.7%。使用 op: `tb_tcspc_irf_convolve`, `tb_tcspc_background_subtract`, `tb_spad_deadtime_correct`, `tb_spad_deadtime_correct`。*


[![振動している場所の地図(video)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_champion_vibration_map_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_champion_vibration_map.png)

*↑ **振動している場所の地図(video)** ―― 同じ locked holdout(``seed+20000``、champion に一度だけ当てる分割)で測り直した実測。恒等 0.0000 / 手 0.7163 / 進化 0.8941(corr)= 手比 +24.8%。使用 op: `tb_temporal_band_power`, `xsp_savgol`, `percentile`, `iv_wiener_deconv_spatial`。*


[![ライトフィールドの視差スロープ(lightfield)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_champion_lf_slope_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_champion_lf_slope.png)

*↑ **ライトフィールドの視差スロープ(lightfield)** ―― 同じ locked holdout(``seed+20000``、champion に一度だけ当てる分割)で測り直した実測。恒等 0.0000 / 手 0.5219 / 進化 0.5465(corr)= 手比 +4.7%。使用 op: `tb_lf_epi_slope`, `xkor_unsharp`, `xsk2_wiener`, `binomial_filter`。*


[![鏡面(テカり)の除去(rgbimage)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_champion_specular_removal_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_champion_specular_removal.png)

*↑ **鏡面(テカり)の除去(rgbimage)** ―― 同じ locked holdout(``seed+20000``、champion に一度だけ当てる分割)で測り直した実測。恒等 0.4905 / 手 0.8343 / 進化 0.6277(1/(1+100*mse))= 手比 -24.8%。使用 op: `tb_rgb_to_quaternion`, `tb_quat_color_rotate`, `tb_quaternion_to_rgb`, `tb_specular_diffuse_split`。*


### 2. 恒等写像に勝てているか

[![beat-the-null 図](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_beat_null_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_beat_null.png)

*↑ **恒等写像に勝てているか** ―― 6 課題の locked holdout を同じ軸に。進化が手を上回るのは 4/6 で、`specular_removal` は手 0.8343 に対し 進化 0.6277 と**負けている**。「進化が勝った」と言う前に、恒等と手の両方を同じ分割で測る。使用 op: `decode_by_names`, `run_stages`。*


### 3. 勝った例と負けた例

[![観測 split と locked holdout の差](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_observed_vs_locked_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_observed_vs_locked.png)

*↑ **勝った例と負けた例** ―― 同じ champion でも観測用 holdout と locked holdout で数字が動く。`specular_removal` は 0.7761 → 0.6277(seed 間 std 0.1900)、`vibration_map` は 0.8783 → 0.8941(std 0.0006)。使用 op: `robust.run`(記録)、`decode_by_names`(手の測り直し)。*


### 4. ばらつきの開示

![seed ばらつきの開示](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingevo_seed_spread.gif)

*↑ **ばらつきの開示** ―― seed だけを変えて実走した locked holdout。`photon_denoise` std 0.0320(min 0.7056 / max 0.8007) / `specular_removal` std 0.2189(min 0.2389 / max 0.8427)。選択は train でのみ行い(黄枠)、locked は選択に使わない。1 本だけ走らせて報告すると、この幅がまるごと消える。使用 op: `evolve.run`, `decode_by_names`。*


### 5. 世代が進むとパイプラインが伸びる/縮む

![世代ごとの champion](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingevo_generations.gif)

*↑ **世代が進むとパイプラインが伸びる/縮む** ―― `photon_denoise` を seed 0 / pop 16 で 24 世代、実際に走らせた軌跡。train は 0.6926 → 0.7881、op 数は 5 → 4 → 4 と伸び縮みし、第 13 世代で `tb_spad_deadtime_correct` が `tb_tcspc_coates_correct` に入れ替わった。使用 op: `evolve.run`, `ops.decode_by_names`。*


### 6. champion のパイプライン図(各段の中間値)

![champion の各段(光子計数)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingevo_stage_photon.gif)

*↑ **champion のパイプライン図(各段の中間値)** ―― `tb_tcspc_irf_convolve` → `tb_tcspc_background_subtract` → `tb_spad_deadtime_correct` → `tb_spad_deadtime_correct` の 4 段。各段を最終出力とみなしたスコアは 0.7965 → 0.8793 → 0.8794 → 0.8794(恒等 0.4174 / 手 0.5536 / 鎖ぜんぶで 0.7845)。光子族だけで閉じた合成 = 新しい族が「単体で使える op」ではなく「op を繋いだ手順」として価値を出した最初の例。*


### 7. 負けた champion の中身(族をまたいだ寄り道)

![負けた champion の各段](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingevo_stage_specular.gif)

*↑ **族をまたいだ寄り道が「惜しく見えた」例** ―― `specular_removal` の champion は `tb_rgb_to_quaternion` → `tb_quat_color_rotate` → `tb_quaternion_to_rgb` → `tb_specular_diffuse_split`。RGB を四元数に持ち上げて色空間で回し、戻してから鏡面分離する。観測用 holdout では 0.7761 と手に迫って見えたのに、locked では 0.6277 で手 0.8343 に**負けている**。1 枚目の item に対する段ごとのスコアは 0.0000 → 0.0000 → 0.5411 → 0.5411 で、四元数へ持ち上げている間は 2 段とも 0.0000(型が合わないので採点対象にならない)。*


### 8. 署名の収束

![署名の収束](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingevo_signature_collapse.gif)

*↑ **署名の収束** ―― 良いエラーメッセージほど実行固有の数を含むので、素の文字列で同一視すると同じ 1 件が毎回別署名になる。実走 600 連鎖で、生の発見 174 件 → 素の文字列で 63 署名 → **数値を伏せて 46 署名**(27% 減)。使用 op: `chain_fuzz.run_chain`, `chain_fuzz.signature`。*


### 9. 型到達可能性の不動点

![型到達可能性の不動点](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingevo_type_fixpoint.gif)

*↑ **型到達可能性の不動点** ―― 「初期プールの型から、入力が揃う op の出力型を足していく」を収束まで回す。初期プールを `image2d` 1 種だけにすると 4 段で 506/515 op に届き、ファザー本体の 37 種の種では 2 段で 513/515。**構造的に到達不能なのは 2 件だけ**(`fuse_to_voxel`, `register_cross`)で、どちらも入力型が `any` = 型では絞れないので専用の引数 builder が要る。*


### 10. 族ごとのカバレッジ内訳

[![族ごとのカバレッジ内訳](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_coverage_families_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_coverage_families.png)

*↑ **族ごとのカバレッジ内訳** ―― 全体の数(今回の実走 445/515)だけでは、残りが頑健なのか到達不能なのかを区別できない。族に割ると、記録に残る wave-8 では photon 族が 10/17(fail-closed が効きすぎて実行されない)と一目で出る。使用 op: `chain_fuzz.catalog`, `chain_fuzz.run_chain`。*


### 11. 拡散と収束

![拡散と収束](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingevo_diffusion.gif)

*↑ **拡散と収束** ―― ランダム連鎖を 600 本張ると到達 op は 142(50 連鎖)→ 346(200 連鎖)→ 445/515 と伸びが鈍る一方、新しい署名は最後まで細く出続ける。この走行の発見は CONTRACT 174。使用 op: `chain_fuzz.run_chain`。*


### 12. 無言のバグの見え方

[![無言のバグの見え方](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_silent_bug_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_silent_bug.png)

*↑ **無言のバグの見え方** ―― 例外ではなく「もっともらしく違う数字」が返る 3 例。(1) 対角に接する 2 画素が 8 連結で 1 個 / 4 連結で 2 個。(2) 昇格ゲートの相対改善が、基準線 0.0 との比で +7.245e+11 に跳ね、それでも判定は PROMOTE。(3) 型を外したパイプラインは例外ではなくスコア 0.0000 を返す。使用 op: `ops._blob_count`, `promote_gate.counterfactual_utility`。*


### 13. 昇格ゲート

[![昇格ゲート](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_promotion_gate_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingevo_promotion_gate.png)

*↑ **昇格ゲート** ―― counterfactual utility(既存語彙の最良 1 段との差)/ 振る舞いの重複判定 / 容量上限の 3 つを全部通らないと語彙に入らない。`macro_denoise` は 2 problem を改善して PROMOTE、`tb_lf_epi_slope` は lf_slope を +37.9% 伸ばすのに**`tb_lf_to_mla` と振る舞いが同じ**なので REJECT。「強い」だけでは通らない。使用 op: `promote_gate.counterfactual_utility`, `promote_gate.find_behavioural_duplicate`。*


---

#### 数字の出どころ

| 展示 | ファイル | 出どころ |
|---|---|---|
| 1. 進化した champion の実力 | `wingevo_champion_photon_denoise` | champion=out/rb_ph/champion_photon_denoise.json / スコアは本スクリプトで実測 |
| 1. 進化した champion の実力 | `wingevo_champion_vibration_map` | champion=out/rb_vibration_map/champion_vibration_map.json / スコアは本スクリプトで実測 |
| 1. 進化した champion の実力 | `wingevo_champion_lf_slope` | champion=out/rb_lf/champion_lf_slope.json / スコアは本スクリプトで実測 |
| 1. 進化した champion の実力 | `wingevo_champion_specular_removal` | champion=out/rb_specular_removal/champion_specular_removal.json / スコアは本スクリプトで実測 |
| 2. 恒等写像に勝てているか | `wingevo_beat_null` | 本スクリプトで locked split を実測(champion は out/rb_* / out/fix_*) |
| 3. 勝った例と負けた例 | `wingevo_observed_vs_locked` | out/rb_vibration_map/robust_vibration_map.json; out/rb_ph/robust_photon_denoise.json; out/rb_lf/robust_lf_slope.json; out/rb_specular_removal/robust_specular_removal.json |
| 4. ばらつきの開示 | `wingevo_seed_spread` | 本スクリプトで実走(evolve.run, seed 0..N-1) |
| 5. 世代が進むとパイプラインが伸びる/縮む | `wingevo_generations` | 本スクリプトで実走(evolve.run gens=1..24) |
| 6. champion のパイプライン図(各段の中間値) | `wingevo_stage_photon` | champion=out/rb_ph/champion_photon_denoise.json / 中間値は本スクリプトで実測 |
| 7. 負けた champion の中身(族をまたいだ寄り道) | `wingevo_stage_specular` | champion=out/rb_specular_removal/champion_specular_removal.json / 中間値は本スクリプトで実測 |
| 8. 署名の収束 | `wingevo_signature_collapse` | 本スクリプトで実走(chain_fuzz.run_chain を in-process) |
| 9. 型到達可能性の不動点 | `wingevo_type_fixpoint` | 本スクリプトで計算(chain_fuzz.catalog / make_generators) |
| 10. 族ごとのカバレッジ内訳 | `wingevo_coverage_families` | 左=本スクリプトで実走 / 右=out/fuzz_wave8_coverage.json |
| 11. 拡散と収束 | `wingevo_diffusion` | 本スクリプトで実走(chain_fuzz.run_chain を in-process) |
| 12. 無言のバグの見え方 | `wingevo_silent_bug` | 本スクリプトで実測(ops / promote_gate を直接呼ぶ) |
| 13. 昇格ゲート | `wingevo_promotion_gate` | 本スクリプトで実走(promote_gate、max_existing=40) |
