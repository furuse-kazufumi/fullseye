# evis 系動画素材 — fullseye 総合紹介記事用スニペット

生成: `tools/gen_evis_media.py`(再現可能、`--subjects stereo,track,legacy`)。
入力は evis_chopstick プロジェクトの実験キャプチャ
`C:\dev\projects\evis_chopstick\out\chop_vision_frames\`(241 フレーム、読み取りのみ・無改変)と、
onocollo-complete の既存 GIF 1 本。**動画 1・2 は「evis の実験映像を fullseye の登録 op で実処理した実出力」**、
動画 3 は fullseye 処理なしの既存実験素材の再エンコードです(キャプションで明示)。

出所メモ: evis / MS-Human-700 系モデルと ChopMimic シーンは著者自身のプロジェクト(evis_chopstick)の自作アセット。
両眼キャプチャの諸元(IPD 64mm / fovy 60° / f=415.69px @640×480)と毎フレームの真値
(豆の 3D 位置・真距離・画素重心)は同プロジェクトの `chop_vision_meta.json` に記録されている。

---

## 1. evis 両眼 → fullseye ステレオ深度(本命)

- (a) 再生リンク: https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/media/evis_stereo_fullseye.mp4
- (b) サムネ raw URL: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/evis_stereo_fullseye_thumb.jpg
- 静止画(フルサイズ): https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/evis_stereo_fullseye_still.png
- 実体: `docs/articles/assets/media/evis_stereo_fullseye.mp4`(2.3MB, 960×268, 20fps, 12s)

**キャプション案(正直版)**:

> evis(筋骨格ヒューマノイド)が箸で豆を打つ ChopMimic シーンを、evis 自身の両眼カメラ
> (瞳孔間距離 64mm)で撮った実験キャプチャ 241 フレームに、Fullseye の
> `disparity_sgm → speckle_filter → fill_disparity → depth_from_disparity` を
> 毎フレーム適用した実出力。左=evis の左眼映像(evis_chopstick プロジェクトの実験素材)、
> 中央=Fullseye が計算した視差、右=同じく深度。下段の豆までの距離は、左右眼それぞれに
> `segment_objects` を当てた重心の視差から Z=f·B/d で読み出したもので、シミュレータ真値との
> 誤差は 229 フレームで中央値 0.66%・最大 1.91%(豆が箸に隠れた 12 フレームは
> 「bean not in view」と正直に表示)。

**検算(実測)**: 豆の距離推定 vs 真値 — 読み出し可能 229/241 フレーム、
誤差 中央値 0.66% / p90 0.68% / 最大 1.91%、5% 以内 100%。

---

## 2. 箸先カメラ → fullseye 豆トラッキング

- (a) 再生リンク: https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/media/evis_bean_track_fullseye.mp4
- (b) サムネ raw URL: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/evis_bean_track_fullseye_thumb.jpg
- 静止画(フルサイズ): https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/evis_bean_track_fullseye_still.png
- 実体: `docs/articles/assets/media/evis_bean_track_fullseye.mp4`(1.7MB, 720×402, 20fps, 12s)

**キャプション案(正直版)**:

> 同じ ChopMimic 実験の箸先カメラ映像(evis_chopstick プロジェクトの実験素材)に、
> Fullseye の `segment_objects → draw_objects` を毎フレーム適用して豆を追跡した実出力。
> 左=三人称視点(文脈用、無加工)、右=Fullseye が検出した豆の bbox とマスク。
> 豆が箸先カメラに写っている 163 フレームでは 163 フレームすべてで検出
> (可視フレーム検出率 100%)、残り 78 フレームは箸・皿に隠れて実際に見えていない。
> 重心の画素誤差は真値比で中央値 0.10px。

**検算(実測)**: 検出 163/241(可視 163 フレームの 100%)、重心誤差 中央値 0.10px / 最大 14.53px。

---

## 3. evis 700 筋 活性ヒートマップ(既存素材・fullseye 処理なし)

- (a) 再生リンク: https://github.com/furuse-kazufumi/fullseye/blob/master/docs/articles/assets/media/evis_muscle_heatmap.mp4
- (b) サムネ raw URL: https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/evis_muscle_heatmap_thumb.jpg
- 静止画(フルサイズ): https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/evis_muscle_heatmap_still.png
- 実体: `docs/articles/assets/media/evis_muscle_heatmap.mp4`(0.7MB, 480×360, 10fps)

**キャプション案(正直版)**:

> Fullseye の"お客さん第一号"である evis の体そのもの。700 本の腱の色を、実物理
> 再シミュレーション中の実活性(d.act)で毎フレーム更新した筋活性ヒートマップ
> (腕挙上→歩行追従。挙上時は三角筋、歩行時は腸骨筋・前脛骨筋が点灯)。
> **これは evis 側プロジェクト(onocollo-complete)の実験映像の再エンコードで、
> Fullseye の処理は入っていません** ―― この体に「目」を供給するのが Fullseye 層③の役割です。

出所: `onocollo-complete/docs/qiita/20260822_g1_evis/evis_muscle_heatmap.gif`
(同ディレクトリ MATERIAL.md に「実物理再シミュレーション・実活性 d.act・張力プロキシではない」と記録あり)。

---

## 挿入位置の提案(文字過密区間の実測)

`docs/articles/fullseye_overview_qiita_ja.md`(90,433 字、視覚要素 132 個)で
画像・図の間が 3,000 字以上空く区間は 5 つ:

| # | 行範囲 | 空白量 | 区間の内容 | 提案 |
|---|--------|--------|-----------|------|
| 1 | L23–130 | 4,834 字 | 冒頭〜「なぜ作ったか」。**L128 に evis 初登場**(お客さん第一号)、L136 に「動くより先に見える」 | **動画 2(豆トラッキング)のサムネ+リンクを L136 の段落直後へ**。「箸で豆をつまむ」の文章に実映像が付く |
| 2 | L353–434 | 5,459 字 | 層②進化の説明〜層③見出し | 挿入不要(層②の話題に evis 素材は合わない)。層③見出し直後は #3 区間で対応 |
| 3 | L434–495 | 5,393 字 | 「6つのセンサーをひとつずつ」LiDAR/ステレオ/DVS 各論 | **動画 1(ステレオ深度)を「#### ステレオ深度」小節の末尾へ**。合成シーンの説明の直後に「実際のロボット実験でも同じ op が動く」実例として最適 |
| 4 | L568–607 | 3,710 字 | サンプルデータ源リスト〜**L584 の evis 段落**〜Studio 見出し | **最有力**。L584「この層の"お客さん第一号"が evis」段落の直後に**動画 1 と 3 を並べる**(動画 1 を #3 で使った場合はここに 3 のみ)。「ステレオ→深度→…→700筋」の文がそのまま両動画の説明になる |
| 5 | L864–1155 | 23,764 字 | 設計思想 4 本柱〜RAG 節〜公開前夜(最大の文字砂漠) | evis 素材の話題適合は弱め。あえて 1 本入れるなら、**L1139「Physical AI の目――…700 筋で"つまむ"まで」(次回予告)の直前**に動画 3(筋ヒートマップ)を「次回の主役の顔見せ」として。ただし本区間は evis 以外の素材(RAG 応答例のスクショ等)での分割が本筋 |

推奨配線(重複なし): 動画 2 → 区間 1(L136 付近)/ 動画 1 → 区間 4(L584 直後)/
動画 3 → 区間 5(L1139 直前)。区間 3 のステレオ小節には動画 1 の静止サムネを再掲せず、
「後述の evis 節で実ロボット適用例を示す」の一文リンクでも成立します。

※ 記事 md 本体は未編集(配線は著者が行う)。
