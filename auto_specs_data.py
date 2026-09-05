"""Generated wheel-shippable mirror of data/auto_specs/*.json — DO NOT hand-edit.

Written by gen_auto_specs_data.py. backends_auto.load_specs() reads this when the
flat-layout data/auto_specs/ dir is absent (a pip-installed wheel), so the data-driven
auto ops register on an installed package, not only in the editable source tree."""
from __future__ import annotations

AUTO_SPECS = [{'halcon': 'tan_image',
  'category': 'arithmetic',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'pointwise',
  'params': {'func': 'tan'},
  'doc': '画素値の正接（tangent）をとる逐点（pointwise）変換。HALCON の ``tan_image``（画像の正接を計算）に相当するが正規化規約が異なる近似。\n'
         '\n'
         '実装は x を [0,1] にクリップし、(x-0.5) を ±0.45π の範囲へ写してから tan を掛け、結果を signed01（符号つき値を [0,1] '
         'に写す、0.5 が 0 に対応）で戻す。a, b は未使用。角度域を ±0.45π に抑えているため tan の発散（±90° '
         '付近）には達しない。中間輝度付近で傾きが最大になり、コントラストを強めたい局所帯域を狙うのに使える。'},
 {'halcon': 'bit_not',
  'category': 'gray',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'lut',
  'params': {'kind': 'invert'},
  'doc': '階調の反転（ネガポジ反転）。実装は ``1 - x``（[0,1] の連続値としての反転）で、a, b は未使用。\n'
         '\n'
         'HALCON の ``bit_not``（画素の全ビットを反転するビット単位演算）とは動作原理が異なる近似 —— 8bit '
         '整数のビット補数ではなく浮動小数の線形反転なので、量子化された画像でのビットパターンは再現しない。明るい/暗いを単純に入れ替えたい用途には使える。'},
 {'halcon': 'monotony',
  'category': 'gray',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'lut',
  'params': {'kind': 'monotony'},
  'doc': '画素値がその 8 近傍の中で何番目に大きいか（単調性、monotony）を [0,1] で返す。中心より小さい近傍の数を数えて 8 で割るので、値 1.0 '
         'は中心が近傍全てより大きい局所最大、0.0 は局所最小に近いことを示す。a, b は未使用。\n'
         '\n'
         'エッジの向き（明→暗か暗→明か）を区別できる非対称なエッジ検出に使う。HALCON の ``monotony``（単調性演算の計算）に相当。'},
 {'halcon': 'eliminate_min_max',
  'category': 'rank',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'rank',
  'params': {'kind': 'median'},
  'doc': '中央値フィルタ（median filter）による平滑化。実装は ``median_image`` などと同じ ``_sh_rank`` の median '
         '分岐で、窓内画素の中央値に置き換えるだけ。a は窓サイズを 3/5/7/9 の 4 段階に振る（``_k(a)``）。b は未使用。\n'
         '\n'
         'HALCON の '
         '``eliminate_min_max``（最小値・最大値の画素だけを周辺の平均値等で置き換えてノイズを抑える演算）とは異なり、この実装は最小・最大画素を選別せず窓全体を単純な中央値フィルタにかけているだけの近似（本来の「外れ値だけを直す」性質は再現しない）。'},
 {'halcon': 'median_weighted',
  'category': 'rank',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'rank',
  'params': {'kind': 'median'},
  'doc': '中央値フィルタ（median filter）。実装は eliminate_min_max/median_image と同じ ``_sh_rank`` の median '
         '分岐で、円形・八角形などマスク形状ごとの重み付けは行わず、正方形窓の単純な中央値を返す。a が窓サイズを 3/5/7/9 に振り、b は未使用。\n'
         '\n'
         'HALCON の '
         '``median_weighted``（円・矩形・八角形など複数のマスクで重み付き中央値フィルタを行う演算）の代役だが、実装は重みなしの通常の中央値フィルタで、マスク形状の違いは再現しない。'},
 {'halcon': 'mean_sp',
  'category': 'rank',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'rank',
  'params': {'kind': 'trimmed_mean'},
  'doc': 'ロバスト平滑化フィルタ。窓内の 20 パーセンタイルと 80 パーセンタイルの平均を返す（トリム平均、trimmed '
         'mean）ことで、極端に明るい/暗い外れ値（ソルト&ペッパー雑音など）の影響を抑える。a が窓サイズを 3/5/7/9 に振る（``_k(a)``）。b は未使用。\n'
         '\n'
         'HALCON の ``mean_sp``（ソルト&ペッパーノイズを抑制する平均化演算）に相当する近似 —— 上下 20% '
         'を除いた範囲の中点をとる点で単純平均よりノイズに強いが、HALCON 固有のアルゴリズムとは実装が異なる。'},
 {'halcon': 'eliminate_sp',
  'category': 'rank',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'rank',
  'params': {'kind': 'sigma'},
  'doc': 'シグマフィルタ（sigma filter, Lee 型）によるノイズ抑制。窓内平均値との差が閾値（0.05〜0.4、b '
         'で振る）未満の画素だけを使って再平均化し、極端に外れた画素（ソルト&ペッパー雑音など）の影響を除く。該当画素が窓内に無ければ元の値をそのまま返す。a が窓サイズを '
         '3/5/7/9 に振る。\n'
         '\n'
         'HALCON の ``eliminate_sp``（閾値外の値を周辺の平均値で置き換えてソルト&ペッパーノイズを除去する演算）に相当する近似実装。'},
 {'halcon': 'simulate_defocus',
  'category': 'smoothing',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'linfilter',
  'params': {'kind': 'mean'},
  'doc': '一様なピンボケ（デフォーカス）をシミュレートする平滑化。実装は矩形窓の平均フィルタ（box filter, '
         '``ndimage.uniform_filter``）で、円形絞りによる本来のボケ形状（circle-of-confusion）ではなく正方形窓で近似する。a が窓幅を '
         '3/5/7/9 の 4 段階に振り（``_k(a)``）、b は未使用。\n'
         '\n'
         'HALCON の '
         '``simulate_defocus``（一様なピンボケをシミュレートする演算）に相当するが、光学的に正しい円形ボケではなく矩形平均という粗い近似である点に注意。'},
 {'halcon': 'dots_image',
  'category': 'edges',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'linfilter',
  'params': {'kind': 'laplace_gauss'},
  'doc': 'ガウシアンラプラシアン（Laplacian of Gaussian, LoG）フィルタ。σ = 0.5+2.5a のガウス核でラプラシアンを取り、signed01（符号つき値を '
         '[0,1]、0.5=応答ゼロ）で正規化する。b は未使用。円形の点状パターン（ドット）はガウシアンの等方性からくる強い LoG 応答を示すため、円形ドットの強調に使われる。\n'
         '\n'
         'HALCON の ``dots_image``（画像中の円形ドットを強調する演算）に相当する近似で、専用のドット検出カーネルではなく一般的な LoG フィルタで代用している。'},
 {'halcon': 'frei_dir',
  'category': 'edges',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'edge',
  'params': {'kind': 'frei_dir'},
  'doc': 'Frei-Chen 型カーネルによるエッジ方向（角度）マップ。水平カーネル ``_FREI[0]``（行/縦方向勾配）と垂直カーネル '
         '``_FREI[1]``（列/横方向勾配）への畳み込み応答から ``arctan2(gy, gx)`` を計算し、``sobel_dir``/``prewitt_dir`` '
         'と同じ規約で [0,1] に写す（0/1 が -180°、0.5 が 0°）。a, b は未使用。\n'
         '\n'
         'HALCON の ``frei_dir``（Frei-Chen 演算子でエッジの振幅と方向を検出する演算）のうち方向成分に相当する近似。振幅は ``frei_amp`` '
         '側が担当する。'},
 {'halcon': 'robinson_dir',
  'category': 'edges',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'edge',
  'params': {'kind': 'robinson_dir'},
  'doc': 'Robinson コンパス演算子によるエッジ方向マップ。8 方向（45° ずつ回転させた ``_ROBINSON[0]``/``_ROBINSON[1]`` カーネル計 8 '
         '個）それぞれへの畳み込み応答のうち最大のものを選び、そのカーネル番号を 0〜1 に正規化して返す。a, b は未使用。\n'
         '\n'
         '``frei_dir``/``sobel_dir`` が ``arctan2`` による連続角度なのに対し、こちらは 8 '
         '方向のうち最も強く反応したカーネルの**インデックス**を返す離散近似である点に注意（8 段階の量子化角度）。HALCON の '
         '``robinson_dir``（Robinson 演算子でエッジの振幅と方向を検出する演算）の方向成分に相当。振幅は ``robinson_amp`` が担当する。'},
 {'halcon': 'fft_generic',
  'category': 'frequency',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'freq',
  'params': {'kind': 'fft_power'},
  'doc': '画像のフーリエ変換の振幅スペクトルを対数圧縮して返す（``log1p(|F|)`` を最大値で正規化）。中心が低周波、周辺が高周波成分に対応する（``fftshift`` '
         '済み）。a, b は未使用。\n'
         '\n'
         'HALCON の ``fft_generic``（順変換・逆変換・実数/複素数など多数のモードを持つ汎用 FFT 演算）のうち、順方向の振幅スペクトル表示だけを実装した近似 '
         '—— 逆変換や位相成分などの他モードは別 op（``fft_image_inv``、``phase_deg`` など）が個別に担う。'},
 {'halcon': 'power_ln',
  'category': 'frequency',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'freq',
  'params': {'kind': 'fft_power'},
  'doc': '複素画像のパワースペクトルの代役。実装は fft_generic と同一で、入力画像に自前で FFT をかけてから振幅の対数 ``log1p(|F|)`` '
         'を最大値正規化して返す（``_sh_freq`` の ``fft_power`` 分岐を共有）。a, b は未使用。\n'
         '\n'
         'HALCON の ``power_ln``（複素画像のパワースペクトルを返す演算、通常は fft_generic '
         '等が出力した複素画像を入力に取る）とは異なり、この実装は複素入力を受け取らず実画像から自前で FFT を計算する簡略近似。fft_generic とは実装上区別がない。'},
 {'halcon': 'rft_generic',
  'category': 'frequency',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'freq',
  'params': {'kind': 'fft_power_real'},
  'doc': '実数フーリエ変換（real FFT, RFFT）の代役。実装は通常の複素 FFT を計算してから実部の絶対値 ``|Re F|`` を最大値正規化して返すもので、HALCON '
         'の rft_generic が実際に計算する半分サイズの実数専用高速変換（対称性を利用したデータ量削減）ではない。a, b は未使用。\n'
         '\n'
         'HALCON の ``rft_generic``（画像の実数値高速フーリエ変換を計算する演算）に相当する近似 —— '
         '出力される値の意味（実部の大きさの分布）は近いが、アルゴリズムそのものは異なる。'},
 {'halcon': 'phase_deg',
  'category': 'frequency',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'freq',
  'params': {'kind': 'fft_phase'},
  'doc': '複素画像の位相角マップ。``np.angle(F)``（-π〜π）を ``(angle+π)/(2π)`` で [0,1] に線形写像する。a, b は未使用。\n'
         '\n'
         '名称は「度（degree）」を示唆するが、実装は phase_rad と同じ ``_sh_freq`` の ``fft_phase`` '
         '分岐を共有しており、度数法への変換は行っていない —— 返るのは [0,1] に正規化された角度で、実際の度数（0-360°）ではない。HALCON の '
         '``phase_deg``（複素画像の位相を度単位で返す演算）の代役としては単位が違う近似である点に注意。'},
 {'halcon': 'affine_trans_image_size',
  'category': 'geometry',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'geom',
  'params': {'kind': 'affine'},
  'doc': 'アフィン変換（回転+シアー）を画像に掛ける。実装は ``affine_trans_image`` と同じ ``_sh_geom`` の ``affine`` '
         '分岐を共有しており、a で回転角を -20°〜+20° に、b でシアー量を振る。枠外は鏡映（reflect）で埋める。\n'
         '\n'
         'HALCON の '
         '``affine_trans_image_size``（アフィン変換を適用し、出力画像のキャンバスサイズを明示的に指定できる演算）とは異なり、この実装は出力サイズの指定を受け付けず、常に入力と同じキャンバスサイズを保つ近似（``affine_trans_image`` '
         'と実質同一の実装）。'},
 {'halcon': 'polar_trans_image_ext',
  'category': 'geometry',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'geom',
  'params': {'kind': 'polar'},
  'doc': '画像全体を極座標（半径・角度）表現へ変換する（``cv2.warpPolar``、順方向・線形補間）。中心は画像中心固定、半径の最大値は ``min(h,w)/2``。a, b '
         'は未使用（同じ ``_sh_geom`` の ``polar`` 分岐を ``polar_trans_image`` と共有）。\n'
         '\n'
         'HALCON の '
         '``polar_trans_image_ext``（中心・半径範囲・角度範囲などを個別指定できる、環状の一部だけを切り出して極座標変換する拡張版演算）とは異なり、この実装は画像全体を固定パラメータで変換する簡略近似 '
         '—— 環状領域や角度範囲の指定はできない。'},
 {'halcon': 'lines_facet',
  'category': 'contour',
  'in_sort': 'image',
  'out_sort': 'contour',
  'shape': 'xld',
  'params': {'kind': 'lines_gauss'},
  'doc': '線状構造（リッジ）を検出して輪郭（XLD contour）として返す。実装は Frangi フィルタ（``skimage.filters.frangi``、多スケール '
         'σ=1..3 のリッジ強調）で線らしさを求め、閾値 ``0.1+0.4a`` を超える連結成分の画素座標をそのまま輪郭点列として出力する。b は未使用。\n'
         '\n'
         'HALCON の ``lines_facet``（局所多項式近似=ファセットモデルで線を検出する演算）とは検出原理が異なる近似 —— facet '
         'モデルによるサブピクセル位置推定は行わず、Frangi 応答の二値化領域を輪郭化しているだけなので、座標はサブピクセル精度を持たない。'},
 {'halcon': 'add_noise_distribution',
  'category': 'noise',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'noise',
  'params': {'kind': 'gaussian'},
  'doc': '画像に加法性ノイズを加える。実装はガウス（正規分布）ノイズのみで、``add_noise_white`` と同じ ``_sh_noise`` の ``gaussian`` '
         '分岐を共有する。乱数は a から決まる固定シード（``int(a*997)+7``）で発生させるため同じ a なら毎回同じノイズになる（決定的）。b がノイズの標準偏差を '
         '0.02〜0.22 に振る。\n'
         '\n'
         'HALCON の '
         '``add_noise_distribution``（任意の確率分布（ヒストグラム指定）に従うノイズを加える演算）とは異なり、この実装は常にガウス分布のノイズしか生成できない近似 '
         '—— 分布形状の指定は反映されない。'},
 {'halcon': 'bin_threshold',
  'category': 'segmentation',
  'in_sort': 'image',
  'out_sort': 'region',
  'shape': 'threshold',
  'params': {'method': 'otsu'},
  'doc': "大津の判別分析法（Otsu's method）による自動しきい値二値化。``binary_threshold``/``auto_threshold`` と同じ "
         '``_sh_threshold`` の ``otsu`` 分岐を共有し、a, b は未使用。しきい値より明るい画素を前景(1)とする。skimage '
         'が無い環境では画像平均値をしきい値とするフォールバックになる。\n'
         '\n'
         'HALCON の '
         '``bin_threshold``（複数の自動しきい値決定アルゴリズムから選んで二値化する演算、既定は最大分離度=大津法相当）に相当する近似で、大津法のみをサポートし他のアルゴリズム選択肢は無い。'},
 {'halcon': 'erosion_golay',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'binmorph',
  'params': {'op': 'erosion', 'shape': 'disk'},
  'doc': '円形構造要素（disk, 半径 ``_rad(a)``=1〜4）による二値の収縮（erosion）。b は未使用。\n'
         '\n'
         'HALCON の ``erosion_golay``（Golay アルファベット——形態学的画像解析の古典的な 14 '
         '種の定型構造要素集合——から選んだ要素で収縮する演算）とは異なり、この実装は Golay アルファベットの特定要素ではなく単純な円板構造要素で近似する。'},
 {'halcon': 'dilation_golay',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'binmorph',
  'params': {'op': 'dilation', 'shape': 'disk'},
  'doc': '円形構造要素（disk, 半径 ``_rad(a)``=1〜4）による二値の膨張（dilation）。b は未使用。\n'
         '\n'
         'HALCON の ``dilation_golay``（Golay アルファベットから選んだ要素で膨張する演算）とは異なり、この実装は Golay '
         'アルファベットの特定要素ではなく単純な円板構造要素で近似する。'},
 {'halcon': 'opening_golay',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'binmorph',
  'params': {'op': 'opening', 'shape': 'disk'},
  'doc': '円形構造要素（disk, 半径 ``_rad(a)``=1〜4）による二値オープニング（opening、収縮の後に膨張）。小さな突起や孤立点を除去する。b は未使用。\n'
         '\n'
         'HALCON の ``opening_golay``（Golay アルファベットから選んだ要素でオープニングする演算）とは異なり、この実装は Golay '
         'アルファベットの特定要素ではなく単純な円板構造要素で近似する。'},
 {'halcon': 'closing_golay',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'binmorph',
  'params': {'op': 'closing', 'shape': 'disk'},
  'doc': '円形構造要素（disk, 半径 ``_rad(a)``=1〜4）による二値クロージング（closing、膨張の後に収縮）。小さな穴やくびれを埋める。b は未使用。\n'
         '\n'
         'HALCON の ``closing_golay``（Golay アルファベットから選んだ要素でクロージングする演算）とは異なり、この実装は Golay '
         'アルファベットの特定要素ではなく単純な円板構造要素で近似する。'},
 {'halcon': 'erosion_seq',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'binmorph',
  'params': {'op': 'erosion_it'},
  'doc': '既定の十字形構造要素（4 近傍）で、a に応じて 1〜4 回反復して収縮（erosion）する逐次的収縮。b は未使用。反復回数を増やすほど収縮量が大きくなる（1 回あたり半径 '
         '1 画素相当）。\n'
         '\n'
         'HALCON の ``erosion_seq``（構造要素を繰り返し適用して逐次的に収縮する演算）に相当する近似。円形やユーザー定義の構造要素ではなく scipy '
         '既定の十字形要素を使う点が簡略化されている。'},
 {'halcon': 'dilation_seq',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'binmorph',
  'params': {'op': 'dilation_it'},
  'doc': '既定の十字形構造要素（4 近傍）で、a に応じて 1〜4 回反復して膨張（dilation）する逐次的膨張。b は未使用。\n'
         '\n'
         'HALCON の ``dilation_seq``（構造要素を繰り返し適用して逐次的に膨張する演算）に相当する近似。円形やユーザー定義の構造要素ではなく scipy '
         '既定の十字形要素を使う点が簡略化されている。'},
 {'halcon': 'morph_skeleton',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'region_trans',
  'params': {'kind': 'skeleton'},
  'doc': '領域の骨格線（スケルトン）を抽出する。実装は skimage の ``skeletonize``（Zhang–Suen 型の反復細線化アルゴリズム）で、a, b は未使用。\n'
         '\n'
         'HALCON の ``morph_skeleton``（構造要素による反復収縮とその差分から求める形態学的スケルトン）とはアルゴリズムが異なる近似 —— 同じ「1 '
         '画素幅の骨格」という結果を目指すが、生成過程・端点の扱いなどが morph_skeleton の定義と一致するとは限らない。'},
 {'halcon': 'thinning_golay',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'region_trans',
  'params': {'kind': 'thin'},
  'doc': '領域を細線化する。実装は skimage の ``thin``（Guo–Hall 型の反復細線化）で完全に 1 画素幅になるまで繰り返し、a, b は未使用。\n'
         '\n'
         'HALCON の ``thinning_golay``（Golay アルファベットの構造要素を使ったヒット・オア・ミス変換で 1 '
         'ステップぶんだけ細線化する演算、通常は反復して使う）とはアルゴリズムも粒度も異なる近似 —— 単一ステップではなく収束するまで細線化してしまう。'},
 {'halcon': 'thinning_seq',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'region_trans',
  'params': {'kind': 'thin'},
  'doc': '領域を細線化する。実装は thinning_golay と同一（skimage の ``thin``、収束するまで反復する Guo–Hall 型細線化）で、a, b '
         'は未使用。\n'
         '\n'
         'HALCON の ``thinning_seq``（構造要素を逐次適用して細線化していく演算）に相当する近似だが、この backend では thinning_golay '
         'と実装上の区別がない。'},
 {'halcon': 'gray_erosion_shape',
  'category': 'morphology',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'graymorph',
  'params': {'op': 'erosion', 'shape': 'disk'},
  'doc': '円形（disk, 半径 ``_rad(a)``=1〜4）構造要素によるグレースケール収縮（gray erosion）—— 窓内の最小値に置き換える。b は未使用。\n'
         '\n'
         'HALCON の ``gray_erosion_shape``（円・矩形など任意形状のマスクで窓内最小のグレー値を求める演算）に相当。矩形版は '
         '``gray_erosion_rect`` が担当する。'},
 {'halcon': 'gray_dilation_shape',
  'category': 'morphology',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'graymorph',
  'params': {'op': 'dilation', 'shape': 'disk'},
  'doc': '円形（disk, 半径 ``_rad(a)``=1〜4）構造要素によるグレースケール膨張（gray dilation）—— 窓内の最大値に置き換える。b は未使用。\n'
         '\n'
         'HALCON の ``gray_dilation_shape``（円・矩形など任意形状のマスクで窓内最大のグレー値を求める演算）に相当。矩形版は '
         '``gray_dilation_rect`` が担当する。'},
 {'halcon': 'gray_opening_rect',
  'category': 'morphology',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'graymorph',
  'params': {'op': 'opening', 'shape': 'rect'},
  'doc': '正方形窓（一辺 ``_k(a)``=3/5/7/9）によるグレースケール・オープニング（gray '
         'opening、収縮の後に膨張）。小さな明るい突起・ノイズを除去しながら大まかな明るさは保つ。b は未使用。\n'
         '\n'
         'HALCON の ``gray_opening_rect``（矩形マスクによるグレー値オープニング演算）に相当。'},
 {'halcon': 'gray_closing_rect',
  'category': 'morphology',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'graymorph',
  'params': {'op': 'closing', 'shape': 'rect'},
  'doc': '正方形窓（一辺 ``_k(a)``=3/5/7/9）によるグレースケール・クロージング（gray '
         'closing、膨張の後に収縮）。小さな暗い穴・くぼみを埋めながら大まかな明るさは保つ。b は未使用。\n'
         '\n'
         'HALCON の ``gray_closing_rect``（矩形マスクによるグレー値クロージング演算）に相当。'},
 {'halcon': 'dual_rank',
  'category': 'rank',
  'in_sort': 'image',
  'out_sort': 'image',
  'shape': 'rank',
  'params': {'kind': 'rank'},
  'doc': 'パーセンタイル（順位統計）フィルタ。窓内画素を昇順に並べ、b で指定した百分位（5〜95%、``rank_image``/``rank_rect`` と同じ '
         '``_sh_rank`` の ``rank`` 分岐）の値を返す。a が窓サイズを 3/5/7/9 に振る。\n'
         '\n'
         'HALCON の '
         '``dual_rank``（円形または矩形マスクでオープニング・中央値・クロージングを組み合わせて行う演算）とは異なり、この実装は単一の順位フィルタのみで、開閉処理の組み合わせは再現しない簡略近似。'},
 {'halcon': 'fast_threshold',
  'category': 'segmentation',
  'in_sort': 'image',
  'out_sort': 'region',
  'shape': 'threshold',
  'params': {'method': 'fixed'},
  'doc': '固定しきい値による二値化。``x`` が ``(a, a+0.5+0.5b)`` の帯域に入る画素を前景(1)とする（``threshold`` seed op と同じ '
         '``_sh_threshold`` の ``fixed`` 分岐）。a が下限、b が帯域幅（上限）を振る。\n'
         '\n'
         'HALCON の '
         '``fast_threshold``（大域しきい値による高速な二値化、通常は単純な閾値以上/以下の判定）に相当するが、この実装は下限・上限の両方を持つ帯域しきい値である点、および高速化のための整数近似などは行っていない点で近似。'},
 {'halcon': 'nonmax_suppression_amp',
  'category': 'segmentation',
  'in_sort': 'image',
  'out_sort': 'region',
  'shape': 'segment',
  'params': {'kind': 'local_max'},
  'doc': '極大点（ローカルマキシマム）を抽出する非極大値抑制。窓内最大値と一致し、かつ閾値 ``0.3+0.4b`` を超える画素だけを前景として残す。a が窓サイズを 3/5/7/9 '
         'に振る。\n'
         '\n'
         'HALCON の ``nonmax_suppression_amp``（エッジ振幅画像上で法線方向に非極大点を抑制し、稜線を 1 '
         '画素幅に絞る演算）とは異なり、この実装は方向を考慮しない単純な局所最大値判定で、エッジ法線方向のサブピクセル抑制は行わない近似。'},
 {'halcon': 'pouring',
  'category': 'segmentation',
  'in_sort': 'image',
  'out_sort': 'region',
  'shape': 'segment',
  'params': {'kind': 'watershed'},
  'doc': '分水嶺法（watershed）による領域分割の境界抽出。勾配画像（Sobel 振幅）を地形とみなし、暗い領域（``x < '
         '0.2+0.3a``）を種（マーカー）として分水嶺を計算、``skimage.segmentation.find_boundaries`` で境界を前景として返す。b '
         'は未使用。\n'
         '\n'
         'HALCON の ``pouring``（水を注ぐように画素値の低い場所から領域を満たしていく古典的な pouring アルゴリズムで分割する演算）に相当する近似 —— '
         'アルゴリズムの詳細は異なるが、低輝度領域を起点に領域を広げるという発想は共通。``watersheds``/``watersheds_threshold`` '
         'と実装を共有する。'},
 {'halcon': 'affine_trans_region',
  'category': 'geometry',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'geom',
  'params': {'kind': 'affine'},
  'doc': '領域にアフィン変換（回転+シアー）を掛ける。``affine_trans_image`` と同じ ``_sh_geom`` の ``affine`` '
         '分岐で連続値として変換したのち、``_rebinarise`` により 0.5 で二値化し直して {0,1} の領域として返す（幾何変換の補間で生じる中間値を除去するため）。a '
         'が回転角（-20°〜+20°）、b がシアー量を振る。\n'
         '\n'
         'HALCON の ``affine_trans_region``（領域に任意のアフィン 2D 変換を適用する演算）に相当する近似。'},
 {'halcon': 'mirror_region',
  'category': 'geometry',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'geom',
  'params': {'kind': 'mirror'},
  'doc': '領域を反転（ミラー）する。a の値で軸を切り替える: a<0.34 で上下反転（``flipud``）、0.34≤a<0.67 '
         'で左右反転（``fliplr``）、それ以外で転置（対角線反転、``x.T``）。b は未使用。フリップは値を変えない演算なので ``_rebinarise`` '
         'は実質何もしない。\n'
         '\n'
         'HALCON の ``mirror_region``（軸を指定して領域を反射する演算）に相当。HALCON は軸位置を任意に指定できるが、この実装は画像中心を通る 3 '
         '種類の軸（縦/横/対角）に固定されている近似。'},
 {'halcon': 'zoom_region',
  'category': 'geometry',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'geom',
  'params': {'kind': 'zoom'},
  'doc': '領域を等方（縦横同倍率）にズームする。倍率 ``s = 0.7+0.6a``（0.7〜1.3 倍）で中心基準に拡大縮小し、境界外は鏡映（reflect）で埋めたのち '
         '``_rebinarise`` で 0.5 しきい値により二値領域に戻す。b は未使用。\n'
         '\n'
         'HALCON の ``zoom_region``（領域を指定倍率でズームする演算）に相当する近似。縦横独立の倍率を持つ ``zoom_image_factor`` '
         'とは異なり単一倍率のみ。'},
 {'halcon': 'fill_up_shape',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'region_trans',
  'params': {'kind': 'remove_holes'},
  'doc': '領域内の小さな穴を埋める。``area_threshold = 16+200a`` 画素以下の穴だけを埋める（skimage の '
         '``remove_small_holes``）。b は未使用。\n'
         '\n'
         'HALCON の ``fill_up_shape``（面積・円形度など形状特徴で選んだ穴だけを埋める演算）とは異なり、この実装は面積の上限だけで穴を選別する単純化された近似 '
         '—— 円形度や凸性など他の形状特徴によるフィルタリングはできない。'},
 {'halcon': 'remove_noise_region',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'binmorph',
  'params': {'op': 'opening', 'shape': 'disk'},
  'doc': '円形構造要素（半径 ``_rad(a)``=1〜4）による二値オープニング（opening、収縮の後に膨張）で、孤立した小さな点状ノイズを除去する。b は未使用。\n'
         '\n'
         'HALCON の '
         '``remove_noise_region``（小さな孤立領域=ノイズをフィルタ処理で除去する演算）に相当。円形構造要素のサイズだけがノイズ除去の強さを決める近似。'},
 {'halcon': 'smallest_rectangle1',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'region_trans',
  'params': {'kind': 'shape_bbox'},
  'doc': '領域を囲む座標軸平行の外接矩形（axis-aligned bounding box）で塗りつぶした領域を返す。a, b は未使用。領域が空なら全ゼロを返す。\n'
         '\n'
         'HALCON の ``smallest_rectangle1``（座標軸に平行な最小外接矩形を求める演算）に相当する実装（回転を許す最小外接矩形の '
         '``smallest_rectangle2`` とは別物）。'},
 {'halcon': 'get_region_contour',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'region_trans',
  'params': {'kind': 'boundary'},
  'doc': '領域の輪郭（境界線、1 画素幅）を抽出する。領域からその収縮版（1 回の二値収縮）を引くことで外周だけを残す。a, b は未使用。``boundary`` seed op '
         'と同じ実装。\n'
         '\n'
         'HALCON の ``get_region_contour``（領域の輪郭を取得する演算、本来は XLD 輪郭として座標列を返す）とは出力形式が異なる近似 —— この '
         'backend は輪郭を region（画素マスク）として返し、XLD の座標点列にはしていない。'},
 {'halcon': 'get_region_convex',
  'category': 'region',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'region_trans',
  'params': {'kind': 'convex'},
  'doc': '領域の凸包（convex hull）を塗りつぶした領域として返す（``skimage.morphology.convex_hull_image``）。a, b '
         'は未使用。``shape_trans``（凸包への形状変換 seed op）と同じ実装。\n'
         '\n'
         'HALCON の ``get_region_convex``（領域の凸包を XLD 輪郭として取得する演算）とは出力形式が異なる近似 —— 輪郭の座標列ではなく塗りつぶした '
         'region を返す。'},
 {'halcon': 'gen_region_polygon_xld',
  'category': 'contour',
  'in_sort': 'contour',
  'out_sort': 'region',
  'shape': 'xld',
  'params': {'kind': 'to_region'},
  'doc': 'XLD 輪郭（多角形の頂点列）を region（画素マスク）へ変換する。輪郭点を最近傍画素に打点したのち、``1+2a`` '
         '回の二値膨張（dilation）で線を太らせて連結させる。b は未使用。\n'
         '\n'
         'HALCON の ``gen_region_polygon_xld``（XLD 多角形の内部を塗りつぶした region '
         'を生成する演算）とは異なり、この実装は多角形の内部を塗りつぶすのではなく、輪郭線そのものを膨張させて太らせるだけの近似 —— '
         '閉じていない輪郭や自己交差する輪郭では本来の内部塗りつぶしと結果が食い違う。'},
 {'halcon': 'connect_and_holes',
  'category': 'features',
  'in_sort': 'region',
  'out_sort': 'feature',
  'shape': 'region_feat',
  'params': {'metric': 'count'},
  'doc': '領域の連結成分数を数える（8 連結、``count_obj`` と同じ ``_sh_region_feat`` の ``count`` 分岐）。a, b は未使用。\n'
         '\n'
         'HALCON の ``connect_and_holes``（連結成分数と穴の数の 2 つを同時に返す演算）のうち**連結成分数だけ**を返す近似 —— feature '
         'sort は 1 スカラーしか運べないため、穴の数は含まれない（``area_holes`` が穴の面積比を別途計算する）。'},
 {'halcon': 'elliptic_axis',
  'category': 'features',
  'in_sort': 'region',
  'out_sort': 'feature',
  'shape': 'region_feat',
  'params': {'metric': 'anisometry'},
  'doc': '領域に等価な楕円（equivalent '
         'ellipse、慣性モーメントが一致する楕円）の長軸と短軸の比（アスペクト比）を返す。``skimage.measure.regionprops`` の '
         '``axis_major_length``/``axis_minor_length`` から計算し、/10 でおおよそ [0,1] '
         '程度のスケールに収める（正規化ではないため、非常に細長い領域では 1 を超えうる）。a, b は未使用。\n'
         '\n'
         'HALCON の ``elliptic_axis``（等価楕円の長半径・短半径そのもの 2 '
         'つの長さを返す演算）とは異なり、この実装は長さではなく比（アニソメトリー、``anisometry`` と同じ metric）だけを 1 スカラーで返す近似。'},
 {'halcon': 'polar_trans_region_inv',
  'category': 'geometry',
  'in_sort': 'region',
  'out_sort': 'region',
  'shape': 'geom',
  'params': {'kind': 'polar_inv'},
  'doc': '極座標表現を通常の直交座標（デカルト座標）へ逆変換する（``cv2.warpPolar`` の逆写像モード）。中心から半径 ``min(h,w)/2`` の円盤の外側は 0 '
         'で埋め、``_rebinarise`` により 0.5 しきい値で二値領域に戻す。a, b は未使用（``polar_trans_image_inv`` と同じ '
         '``_sh_geom`` の ``polar_inv`` 分岐を共有）。\n'
         '\n'
         'HALCON の ``polar_trans_region_inv``（極座標領域を元のデカルト座標系の領域に戻す演算）に相当。実装上、円盤境界付近 1 '
         '画素程度は補間の丸めで非決定的になりうるため外側を明示的に 0 で塗って安全側に倒している（2026-09-02 修正済み、詳細は ``_sh_geom`` の '
         '``polar_inv`` 分岐のコメント参照）。'},
 {'halcon': 'affine_trans_polygon_xld',
  'category': 'contour',
  'in_sort': 'contour',
  'out_sort': 'contour',
  'shape': 'xld',
  'params': {'kind': 'affine'},
  'doc': 'XLD 輪郭（多角形/曲線の頂点列）にアフィン回転を掛ける。画像中心を基準に角度 ``-20°+40a`` '
         'で回転させる（せん断・平行移動は行わない、回転のみの部分アフィン）。b は未使用。\n'
         '\n'
         'HALCON の ``affine_trans_polygon_xld``（XLD 多角形に任意のアフィン 2D '
         '変換を適用する演算）とは異なり、この実装は回転成分だけを再現する近似で、拡大縮小やせん断は反映されない。'},
 {'halcon': 'gen_contour_region_xld',
  'category': 'contour',
  'in_sort': 'region',
  'out_sort': 'contour',
  'shape': 'xld',
  'params': {'kind': 'region_boundary'},
  'doc': 'region（画素マスク）の外周を、トレース順（輪郭に沿った順序）を保った XLD 輪郭として抽出する。skimage があれば '
         '``find_contours``（marching squares によるサブピクセル輪郭）、無ければ自前の Moore 近傍追跡（8 近傍、Jacob '
         'の停止条件）にフォールバックする。a, b は未使用。\n'
         '\n'
         '2026-08-30 の修正で、以前使っていた汎用の ``edges_sub_pix`` 経路は ``np.where`` '
         'のラスタ順で点を返しており、順序に依存する後段処理（楕円フーリエ記述子など）を壊していた。HALCON の ``gen_contour_region_xld``（region '
         'から XLD 輪郭を生成する演算）に相当する。'},
 {'halcon': 'select_shape_xld',
  'category': 'contour',
  'in_sort': 'contour',
  'out_sort': 'contour',
  'shape': 'xld',
  'params': {'kind': 'select_contours'},
  'doc': '点数の少ない XLD 輪郭を足切りするフィルタ。輪郭の頂点数が ``3+40a`` 点未満のものを除去する。b は未使用。\n'
         '\n'
         'HALCON の ``select_shape_xld``（面積・円形度・凸性など多様な形状特徴で XLD '
         '輪郭を選別する演算）とは異なり、この実装は頂点数（≈輪郭の長さ）という単一の特徴でしか選別できない簡略近似。'},
 {'halcon': 'contour_point_num_xld',
  'category': 'contour',
  'in_sort': 'contour',
  'out_sort': 'feature',
  'shape': 'xld',
  'params': {'kind': 'num_points'},
  'doc': 'XLD 輪郭群のうち最も点数の多い輪郭を選び、その頂点数を 500 点で正規化して [0,1] で返す（500 点以上は 1.0 に飽和）。a, b は未使用。輪郭が無ければ '
         '0 を返す。\n'
         '\n'
         'HALCON の ``contour_point_num_xld``（XLD 輪郭に含まれる点の実数をそのまま返す演算）とは異なり、この実装は点数そのものではなく 500 '
         '点でスケーリングした比率を返す近似（feature sort が [0,1] 想定の値を運ぶ契約のため）。'}]
