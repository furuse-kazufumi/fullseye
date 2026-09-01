<!-- 素材はすべて `astrostack.synth_starfield` / `synth_frame_series` が作った合成星野(星の座標・フラックス・PSF・宇宙線が既知)。実写の天体画像は使っていない。数値はすべてその場の実測。 -->

[![重ねると雑音は sqrt(N) で減る](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_stack_sqrtn_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_stack_sqrtn.png)

*↑ **重ねると雑音は sqrt(N) で減る** ―― 合成星野なので**真値が分かっており、雑音は残差そのもので測れる**。1 枚の残差 RMS は 16.507 e-(空 200 + 読み出し 8 e- から予測される 16.248)で、64 枚まで倍々に重ねると改善は sqrt(N) から**最大 1.1 % しか外れない**。右下の差分図は、星の位置に何も残らず雑音だけが消えたことを示す(発散配色。赤緑の対は使っていない)。使用 op: `synth_frame_series`, `sigma_clip_stack`, `noise_sigma`。*

[![lucky imaging —— 品質点で並べ替える](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_lucky_sheet_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_lucky_sheet.png)

*↑ **lucky imaging —— 品質点で並べ替える** ―― 大気が良い瞬間ほど、同じ総フラックスが少ない画素に集まる。だから選別基準は「基準星のピーク割合 x 真円度」で、これは露出やゲインを変えても動かない。16 枚を点の高い順に並べたのが上位 8 枚で、点と FWHM の相関は**-0.964**(FWHM 3.29 〜 6.21 px)。青が採用、灰が不採用。使用 op: `synth_frame_series`, `frame_quality`, `lucky_select`。*

![上位何 % を採るか —— 鋭さと雑音の取引](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingastro_lucky_sweep.gif)

*↑ **上位何 % を採るか —— 鋭さと雑音の取引** ―― 全部(16 枚)から上位 12 %(2 枚)まで絞ると、合成後の FWHM は 4.319 -> 3.294 px と **23.7 % 良くなる**。ただし枚数が減るぶん残差 RMS は 25.211 -> 61.348 e- と **2.43 倍**に増える。lucky imaging は「改善」ではなく**取引**であり、その両側を同じ図に出すのが正直な出し方。使用 op: `lucky_select`, `sigma_clip_stack`, `frame_quality`。*

[![宇宙線の消え方 —— 尖りで見分ける / 枚数で見分ける](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_cosmic_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_cosmic.png)

*↑ **宇宙線の消え方 —— 尖りで見分ける / 枚数で見分ける** ―― 宇宙線は光学系を通っていないので**星より尖る**。ラプラシアンを 2 倍標本化して微細構造と比べると、植えた 44 画素に対し 39 画素を検出して適合率 **0.949** / 再現率 **0.841** ―― 星の中心を 1 つも拾わないことが要点。合成なので「宇宙線だけ無い同じ観測」を作れて、正解との最大差が 7000 -> 7000 e- に落ちることまで言える(**フレームの最大値では言えない** —— それは一番明るい星の値であって、除去の前後でほとんど動かない)。枚数がある場合はもっと簡単で、8 枚を素直に平均しても宇宙線は 1/8 に薄まって残り正解から 1750 e- ずれるのに対し、κ-σ 合成は検出も置換もせずに 45 e-、フレーム間比較で先に除去すれば 7 e- になる。使用 op: `synth_starfield`, `cosmic_ray_reject`, `cosmic_ray_reject_stack`, `sigma_clip_stack`, `star_detect`。*

[![drizzle は面積を保存する](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_drizzle_flux_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_drizzle_flux.png)

*↑ **drizzle は面積を保存する** ―― 入力画素を一回り縮めた「しずく」として出力格子へ**面積比で**撒くので、しずくが格子の内側にある限り総和は動かない。pixfrac 1.0 / 0.7 / 0.4 x 倍率 x1〜x4 の **12 通りすべてで相対誤差は最大 6.3e-15** ―― これは「ほぼ保存」ではなく倍精度の丸めそのもの。被覆マップ ``wht`` の平均が pixfrac の 2 乗にきっちり一致するのも、撒き方が面積で定義されていることの裏取りになる。入力の総和は 306035.5635 e-。使用 op: `synth_frame_series`, `drizzle_resample`。*

![drizzle —— しずくを小さくすると像が立ち上がる](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingastro_drizzle.gif)

*↑ **drizzle —— しずくを小さくすると像が立ち上がる** ―― 真の FWHM 1.15 画素、つまり**ナイキストを破った**星野を 24 枚、1.5 画素のディザで撮る。1 枚では FWHM 1.357 画素にしか見えず、そのまま平均すると **1.991 画素とかえって鈍る**(ずれを平均するから)。同じずれを drizzle に渡すと pixfrac 1.0 / 0.6 / 0.3 で 1.574 / 1.450 / 1.399 入力画素まで立ち上がり、そのあいだ総フラックスは縁から出た 0.76 % 以外**一切動かない**。しずくを小さくするほど鋭くなる代わりに覆われない出力画素が出る(被覆 wht の最小が 0.041 まで下がる)—— これが drizzle の唯一の調整点。使用 op: `synth_frame_series`, `drizzle_resample`, `sigma_clip_stack`, `frame_quality`。*

[![間隔 1.6 画素の二重星](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_drizzle_pair_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_drizzle_pair.png)

*↑ **間隔 1.6 画素の二重星** ―― sigma 0.55 画素の星を 2 つ、1.6 画素だけ離して 24 枚ディザ撮影する。平均合成では **1 個**しか立たないのに、同じ生データを drizzle x3 (pixfrac 0.4)に通すと **2 個**に分かれる。解像度は「上げた」のではなく、**ディザという形で既に撮れていた情報を捨てずに拾った**だけ。4 枚目は同じ drizzle の生の ``sci``(被覆で割っていない像)で、そこに検出をかけると被覆の格子が **200 個の偽の星**になる ―― 総フラックスを保存する像と、目で見る像は別の量である。使用 op: `drizzle_resample`, `sigma_clip_stack`, `star_detect`。*

![σ クリップの破綻 —— 折れ目はちょうど 50 %](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/media/wingastro_clip_breakdown.gif)

*↑ **σ クリップの破綻 —— 折れ目はちょうど 50 %** ―― 20 枚のうち先頭 k 枚に +900 e- の汚染を入れ、割合を 0 から 60 % まで上げていく。**45 % までは誤差 -0.080 e-** と、汚染ゼロのとき(-0.034 e-)と変わらない答えを返す。ところが **ちょうど 50 % で誤差は +450.0 e-**(汚染量のちょうど半分)、**55 % で +900.0 e-**(汚染量そのもの)に跳ぶ。これは実装の不具合ではなく**中央値の破綻点そのもの**で、半数を超えた時点で中央値が汚染側の母集団に乗り、クリップは**正しいフレームの方を捨てる**(棄却率は 47.4 % のまま働いているのに、捨てる側が入れ替わっている)。最後のコマの折れ線がその証拠で、**中央値そのものも同じ 50 % で折れる**(55 % で +883.6 e-)一方、単純平均は最初から汚染に比例してずれ続ける(+495.0 e-)。直せない限界は、直せるふりをせずそのまま展示する。使用 op: `synth_frame_series`, `sigma_clip_stack`。*

[![位置合わせ —— 星は互いに見分けがつかない](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_align_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_align.png)

*↑ **位置合わせ —— 星は互いに見分けがつかない** ―― 星野に記述子マッチングは効かない。星は**全部同じ形**なので Lowe の比検定がほとんど全部を捨ててしまう。代わりに使うのは配置の幾何 ―― 全ペアの差ベクトルを投票させ、最頻値を粗い平行移動とし、既存の 2-D 点対応 RANSAC で誤対応を落として Umeyama で当てはめる。9 枚・最大 6.0 画素のディザで、ずれの推定誤差は中央値 **0.0359 画素**(内点 中央値 33 対応、残差 RMS 0.112 画素)。位置合わせせずに平均すると FWHM 5.310 px、合わせてから平均すると **3.077 px**。使用 op: `star_detect`, `frame_align`, `align_frames`, `sigma_clip_stack`, `frame_quality`。*

[![既知フラックスを測り返す](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_photometry_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/wingastro_photometry.png)

*↑ **既知フラックスを測り返す** ―― 合成星の総フラックスは 10000 e- とこちらが決めた値で、``erf`` による画素の厳密積分で描いてあるので画像の総和もそれに一致する。半径 8 sigma の開口で測ると 4 つの尺度すべてで誤差 **0.0000 %** ―― 文字どおり測り返す。半径 3 sigma に絞ると -0.968 % 〜 -0.095 % の**負の**ずれが残るが、これはバグではなく**画素化**である: 開口の縁の画素を「画素平均 x 面積比」で代表すると、円の内側ほど明るいぶん必ず少なく出る。ずれが sigma の2 乗で消える(sigma 1.0 -> 3.0 で 10.1 倍小さくなる)ことがその証拠。使用 op: `synth_starfield`, `aperture_photometry`。*
