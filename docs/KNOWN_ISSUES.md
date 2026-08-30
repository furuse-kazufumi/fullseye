# Known Issues — 実データ横断テストで発見(2026-08-30)

学術分野横断サンプル生成(`tools/gen_academic_gallery.py`)で実データ・多様画像を
流した際に見つかった既知バグ/設計ギャップ。「実データは合成では出ないバグ発見器」
の実証でもある。**未修正 — 修正時は本ファイルの該当行を消し、回帰テストを添えること。**

検証状態の凡例: ✅=メンテナが最小再現で確認済み / ⚠=発見エージェント報告
(再現手順あり、メンテナ未追試)。

## 1. ✅ `count_obj` が 4 連結(HALCON 非パリティ疑い)
対角接触 2 画素の mask で `count_obj`=2、`segment_objects`(既定 8 連結)=1。
HALCON の `connection` 既定は 8 連結なので `count_obj` 側が非パリティ疑い。
実データでは細胞計数 342 vs 327 等の乖離として現れた。
再現: `m=zeros((8,8)); m[2,2]=m[3,3]=1; fs.apply(m,"count_obj") -> 2.0`

## 2. ✅ `sk_frangi` が a,b ノブを完全無視
(0.5,0.5)/(0.3,0.8)/(0.8,0.8)/(0.5,0.2) の 4 設定で出力がビット一致。
ノブをスケール範囲等へ配線するか、ノブ無しの契約に直すべき。

## 3. ⚠ `gen_contour_region_xld` の境界点がラスタ順(トレース順でない)
隣接点間距離 mean 17px / max 50px。順序前提の
`fourierdesc.elliptic_fourier` に食わせると無警告で崩壊(EFD 再構成が 1 軸に潰れる)。
再現: 楕円 mask → `gen_contour_region_xld` → `fourierdesc.from_xld` → 再構成。
回避: skimage `find_contours`(トレース順)を経由。

## 4. ⚠ registry `clahe` にタイル継ぎ目
タイル間の双線形補間が無く、勾配+ノイズ 512² で col 169/340 に不連続
(近傍差分中央値の 6 倍超)。実画像(星雲)で肉眼でも格子が見える。
`cv_clahe` / `xkor_clahe` は継ぎ目なし — 補間実装を移植するか docs に注記を。

## 5. ⚠ `spec_decorrelation_stretch` が RGB(B=3)を契約で拒否
考古学定番「RGB 写真への DStretch」がスペクトル op 経路では不可(fail-closed 自体は
正しい)。登録 op `principal_comp` で代替可能なことは確認済み。RGB 受け入れの別名 op
か、エラーメッセージでの `principal_comp` 誘導を検討。
