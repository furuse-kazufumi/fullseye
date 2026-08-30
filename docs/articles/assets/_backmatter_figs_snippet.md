<!-- 記事後半(L860 以降の文字砂漠)への挿入候補スニペット。
     生成: py -3.11 tools/gen_backmatter_figs.py
     数値の出所は各図とも (a) その場で再実測 か (b) 記事既載の実績値のみ(創作なし)。
     画像はサムネ(720px JPG)リンクでフル PNG へ。 -->

# 後半図版の挿入候補(_backmatter_figs)

---

## 1. fig_ci_waterfall — 「公開前夜」章、「数字で見る推移、そして教訓の言語化」節の直後あたり

[![CI 失敗テスト数の推移 約80→9→1→0](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_ci_waterfall_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_ci_waterfall.png)

*↑ 失敗テスト数の推移(約80 → 9 → 1 → 0)。第1波=torch の無条件 import、第2波=絶対値と符号で捕まる9件、最終波=クリーン venv 検証で見つけた scikit-image の無条件 import。数値は本文記載の実績値。*

en 案:
*↑ Failing-test count across the three waves (about 80 → 9 → 1 → 0): wave 1 = an unconditional torch import, wave 2 = nine failures caught by absolute values and signs, final wave = an unconditional scikit-image import found by clean-venv verification. Numbers are the actual counts reported in this article.*

---

## 2. fig_kabsch_margin — バグ⑥/CI 章、第2波 (c) カメラ縮退判定の段落直後(「なぜ再投影誤差が…」のかみくだきの前後)

[![カメラ縮退検定の 14 桁マージン(実測)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_kabsch_margin_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_kabsch_margin.png)

*↑ 視差の存在検定を本図のために再実測したもの。縮退ペア(純回転)の Kabsch 残差中央値は 4.9×10⁻¹⁶、健全ペアは 1.5×10⁻² ―― 約13.5桁のマージンで、本文の 3.5×10⁻¹⁶ / 1.8×10⁻² と同オーダー。しきい値 1e-9 はどちらからも遠い。*

en 案:
*↑ The parallax-existence test, re-measured for this figure: median Kabsch residual is 4.9×10⁻¹⁶ for the degenerate (pure-rotation) pair vs 1.5×10⁻² for the healthy pair — a margin of about 13.5 orders of magnitude, matching the 3.5×10⁻¹⁶ / 1.8×10⁻² reported in the text. The 1e-9 threshold sits comfortably far from both.*

---

## 3. fig_bug4_curvature — バグ④の節(「修正して…」の対策段落の直後)

[![バグ④修正後の検証: 球の曲率が 1/R に乗る(実測)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_bug4_curvature_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_bug4_curvature.png)

*↑ 修正後の検証を本図のために再実測したもの。半径 R の合成球(2000 点)へ `curvedness` を実行すると、実測中央値が理論値 1/R の線に乗る(中央値×R = 1.009)。破線は修正前の系統誤差 1/(32R) ―― 比率だけ合って絶対値が 1/32 だった場所。*

en 案:
*↑ Post-fix verification, re-measured for this figure: running `curvedness` on synthetic spheres of radius R (2,000 points) puts the measured medians on the theoretical 1/R line (median × R = 1.009). The dashed line marks the pre-fix systematic error 1/(32R) — ratios were right, absolute values off by 32×.*

---

## 4. fig_rag_corpus — RAG 章、「実際に聞いてみると、何が返ってくるか」の grep 段落(「ベクタ検索でも埋め込み類似度計算でもありません」)の直後あたり

[![RAG コーパスの実物: per-op ノートと 3 ステップ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_rag_corpus_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_rag_corpus.png)

*↑ RAG コーパスの実物 ―― `docs/ops/2d/smoothing/bilateral.md` の frontmatter(型契約 `in:`/`out:`、HALCON 別名、著者・ライセンス・版)と「型が繋がる次の op」リンク。右は AI がやっている3ステップで、③の PASS 行はこの図の生成時に worked example を実行して得た実出力。*

en 案:
*↑ The RAG corpus itself — `docs/ops/2d/smoothing/bilateral.md` with its frontmatter (type contract `in:`/`out:`, HALCON alias, author/license/version) and the "next ops whose types connect" links. Right: the three steps the AI performs; the PASS line in step 3 is the actual output of running the worked example while generating this figure.*

---

## 5. fig_optional_extras — 設計思想章の柱3「重い依存はぜんぶオプション」の掘り下げ段落の直後(または「限界と、これから」の導入部)

[![コア numpy+scipy と optional extras の依存マップ](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_optional_extras_thumb.jpg)](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/fig_optional_extras.png)

*↑ 依存マップ ―― 必須依存は numpy + scipy の2つだけで、OpenCV / scikit-image / torch / GUI / 点群 I/O / 産業 I/O はすべて opt-in の extras。`pyproject.toml` の実定義から機械生成。*

en 案:
*↑ The dependency map — the only required dependencies are numpy + scipy; OpenCV / scikit-image / torch / GUI / point-cloud I/O / industrial I/O are all opt-in extras. Generated mechanically from the actual `pyproject.toml` definitions.*
