# Known Issues — 実データ横断テストで発見(2026-08-30)

学術分野横断サンプル生成(`tools/gen_academic_gallery.py`)で実データ・多様画像を
流した際に見つかった既知バグ/設計ギャップ。「実データは合成では出ないバグ発見器」
の実証でもある。**全 5 件は 2026-08-30 に修正済み**(各項の「修正」参照。回帰テストは
`tests/test_known_issues_fixes.py` + `tests/test_specops_fusion.py`)。発見の経緯は
記録として残す。

検証状態の凡例: ✅=メンテナが最小再現で確認済み / ⚠=発見エージェント報告
(再現手順あり、メンテナ未追試)。

## 1. ✅ `count_obj` が 4 連結(HALCON 非パリティ疑い)
対角接触 2 画素の mask で `count_obj`=2、`segment_objects`(既定 8 連結)=1。
HALCON の `connection` 既定は 8 連結なので `count_obj` 側が非パリティ疑い。
実データでは細胞計数 342 vs 327 等の乖離として現れた。
再現: `m=zeros((8,8)); m[2,2]=m[3,3]=1; fs.apply(m,"count_obj") -> 2.0`
**✅ 修正済み(2026-08-30)**: `count_obj`(backends_auto)と `blob_count`(ops)を
8 連結既定に変更(HALCON パリティ)。旧 4 連結は `_blob_count(..., connectivity=4)` /
spec params `{"connectivity": 4}` で残置。回帰テスト:
`test_known_issues_fixes.py::test_count_diagonal_pair_is_one_object` ほか #1 群。

## 2. ✅ `sk_frangi` が a,b ノブを完全無視
(0.5,0.5)/(0.3,0.8)/(0.8,0.8)/(0.5,0.2) の 4 設定で出力がビット一致。
ノブをスケール範囲等へ配線するか、ノブ無しの契約に直すべき。
**✅ 修正済み(2026-08-30)**: a→sigma スケール範囲(最大 σ 1..5)、b→Frangi 感度
beta(0.15+0.7b)に配線。(0.5,0.5) は旧実装 `frangi(v, sigmas=range(1,4))` と
**ビット一致**を保証(既公開の生成画像を無効化しない)。回帰テスト:
`test_sk_frangi_default_matches_historical_output_bitwise` /
`test_sk_frangi_knobs_change_the_output`。

## 3. ⚠ `gen_contour_region_xld` の境界点がラスタ順(トレース順でない)
隣接点間距離 mean 17px / max 50px。順序前提の
`fourierdesc.elliptic_fourier` に食わせると無警告で崩壊(EFD 再構成が 1 軸に潰れる)。
再現: 楕円 mask → `gen_contour_region_xld` → `fourierdesc.from_xld` → 再構成。
回避: skimage `find_contours`(トレース順)を経由。
**✅ 修正済み(2026-08-30)**: 専用 kind `region_boundary` を新設(skimage
`find_contours` サブピクセル・トレース順、skimage 不在時は自前 Moore 近傍トレース)。
回帰テスト: `test_gen_contour_region_xld_points_are_trace_ordered` /
`test_gen_contour_region_xld_feeds_elliptic_fourier_without_collapse`(EFD 両軸
±25% + IoU>0.8)/ Moore フォールバック 2 件。

## 4. ⚠ registry `clahe` にタイル継ぎ目
タイル間の双線形補間が無く、勾配+ノイズ 512² で col 169/340 に不連続
(近傍差分中央値の 6 倍超)。実画像(星雲)で肉眼でも格子が見える。
`cv_clahe` / `xkor_clahe` は継ぎ目なし — 補間実装を移植するか docs に注記を。
**✅ 修正済み(2026-08-30)**: 標準 CLAHE のタイル間双線形補間(Zuiderveld 1994)を
実装(タイル中心 4 近傍の CDF をブレンド)。回帰テスト:
`test_clahe_tile_seams_are_gone`(境界不連続比が補間前の 1/3 未満かつ <2.5)/
`test_clahe_correlates_better_with_cv_clahe_than_before` /
`test_clahe_still_equalises_locally`(既存 `test_fix_clahe_coverage.py` も維持)。

## 5. ⚠ `spec_decorrelation_stretch` が RGB(B=3)を契約で拒否
考古学定番「RGB 写真への DStretch」がスペクトル op 経路では不可(fail-closed 自体は
正しい)。登録 op `principal_comp` で代替可能なことは確認済み。RGB 受け入れの別名 op
か、エラーメッセージでの `principal_comp` 誘導を検討。
**✅ 修正済み(2026-08-30)**: 設計判断=**RGB を受理**(RGB 写真への DStretch は
Gillespie 1986 以来この手法自身の正典的用途のため、この op のみ `_as_cube(...,
allow_rgb=True)` で B=3 を許可)。B=1・非 3 次元・非有限の fail-closed と、他の
スペクトル op の B=3 拒否(モダリティ境界)は維持。回帰テスト:
`test_specops_fusion.py::test_dcs_accepts_rgb_photograph`(受理+脱相関+平均保存+
他 op は拒否のまま)。
