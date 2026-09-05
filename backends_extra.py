"""Cross-library incorporation — distinctive operators HALCON doesn't emphasise.

imgevolve started HALCON-centric; this module widens it to genuine features from
the broader ecosystem (scikit-image, OpenCV) that have no clean HALCON analogue —
inpainting, blob detectors, keypoint counts, graph/random-walker segmentation,
flood fill, structure/Hessian tensors, and OpenCV's photo/NPR filters (stylization,
pencil sketch, edge-preserving, detail enhance, grabCut, marker watershed).

Same contract as backends.py: `build()` returns typed Op wrappers the registry
appends; every wrapper is exception-safe (degrades to identity) and returns values
in the pipeline's conventions. Names are prefixed `xsk_` / `xcv_` so they never
shadow the core or the existing sk_/cv_ ops. `Op.halcon` is left empty when there
is no faithful HALCON name — these lift *other-library* coverage, not HALCON's.
"""
from __future__ import annotations

import numpy as np

from backend_safe import signed01
from scipy import ndimage


def _safe(fn, out_sort=None):
    """Fail-soft wrapper -> the shared, RECORDING guard (backend_safe.guard).

    A failure degrades to a sort-valid fallback exactly as before, but the event
    is now written to the fallback ledger and strict mode re-raises, so a
    permanently broken op can no longer masquerade as a working identity.
    """
    from backend_safe import guard
    return guard(fn, out_sort)


def _u8(v):
    return (np.clip(np.asarray(v, np.float64), 0, 1) * 255).astype(np.uint8)


def _norm(x):
    x = np.asarray(x, np.float64)
    mx = float(np.max(np.abs(x)))
    return x / mx if mx > 1e-8 else x


#: lambda で定義された op の説明(lambda に docstring は書けないため)。
#: ops.py の登録ループが fn.__doc__ が無い op について ここから Op.doc に積む。
#: キーは op 名。
DOCS = {
    "xsk_richardson_lucy":
        "Richardson-Lucy デコンボリューション。ぼけを 3x3 の平均カーネル(box PSF)と\n"
        "仮定して反復的に鮮鋭化する(skimage.restoration.richardson_lucy をそのまま呼ぶ)。\n\n"
        "``a`` が反復回数を 2〜17 回の範囲で振る(回数が多いほど強く先鋭化するが、\n"
        "ノイズ増幅やリンギングも増える)。``b`` は未使用。PSF は実際のぼけ量に関わらず\n"
        "固定の 3x3 box を仮定するため、真の劣化過程と一致しない画像では改善が限定的、\n"
        "または悪化することがある。",
    "xsk_unwrap_phase":
        "位相アンラップ(phase unwrapping)。入力 [0,1] を位相 [-pi, pi] とみなし、\n"
        "skimage.restoration.unwrap_phase で 2*pi の折返し(ラップ)を取り除いてから、\n"
        "``signed01`` で符号を保ったまま [0,1] へ戻す(0 -> 0.5)。\n\n"
        "``a``, ``b`` は未使用。干渉縞など周期的にラップした位相画像の連続化に使う op で、\n"
        "一様なグラデーションやランダムノイズなど元々位相らしくない入力では意味のある\n"
        "結果にならないことがある。",
    "xsk_meijering":
        "Meijering neuriteness フィルタ。skimage.filters.meijering をスケール\n"
        "sigma=1,2,3 の 3 段で適用し、細い曲線状構造(血管・神経突起など)を強調する\n"
        "(ヘッセ行列の固有値から尾根らしさを計算する点は Frangi 系と同様だが、\n"
        "Meijering は分岐点にも強く応答する)。\n\n"
        "``a``, ``b`` は未使用(sigma は固定)。出力は ``_norm`` で最大絶対値を 1 に\n"
        "正規化した符号なし強度画像。",
    "xsk_sato":
        "Sato tubeness フィルタ。skimage.filters.sato をスケール sigma=1,2,3 の 3 段で\n"
        "適用し、管状構造(血管など)を強調する。ヘッセ行列の固有値比から線状/管状\n"
        "らしさを計算する点は ``xsk_meijering`` と同系だが、応答の重み付けが異なり\n"
        "分岐点には Meijering ほど強く応答しない。\n\n"
        "``a``, ``b`` は未使用(sigma は固定)。出力は ``_norm`` で正規化した符号なし\n"
        "強度画像。",
}


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    out = []

    # ---- scikit-image distinctive ------------------------------------------ #
    try:
        from skimage import restoration, feature, segmentation, filters

        def _inpaint(v, a, b):
            """欠損領域を推定して埋める修復(inpainting)。

            極端に明るい(>0.92)/暗い(<0.08)画素を「欠損」とみなして自動マスクし、
            skimage の biharmonic inpainting(調和方程式に基づく補間)で周囲から
            滑らかに埋める。

            マスクが無ければ(欠損が見当たらなければ)入力をそのまま返す。``a``,
            ``b`` は未使用。しきい値が固定なので、本来ハイライト/シャドウとして
            意味のある画素まで「欠損」扱いされ埋められてしまう場合がある。
            """
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            mask = (x > 0.92) | (x < 0.08)
            if not mask.any():
                return x
            return restoration.inpaint_biharmonic(x, mask)

        def _blob(kind):
            def fn(v, a, b):
                """ブロブ(斑点状構造)の検出数(LoG/DoG/DoH のいずれかで検出)。

                skimage.feature の Laplacian of Gaussian(LoG)/ Difference of
                Gaussian(DoG)/ Determinant of Hessian(DoH)のいずれか(このコードは
                3 種を共通実装しており、どれを使うかは呼び出し元がどの op 名で
                登録したか —— ``xsk_blob_log`` / ``xsk_blob_dog`` / ``xsk_blob_doh``
                —— で決まる)を用いてブロブを検出し、その個数をそのまま返す
                (feature 出力)。

                ``a`` が探索する最大スケール ``max_sigma`` を 5〜25 の範囲で振る
                (大きいほど大きなブロブまで拾う)。``b`` が検出しきい値
                ``threshold`` を 0.02〜0.17 で振る(小さいほど弱いブロブまで拾い、
                検出数が増えやすい)。3 手法は速度・精度が異なる(LoG が最も正確
                だが遅く、DoH はエッジに強い一方、小さいブロブを苦手とする、等)。
                """
                x = np.clip(np.asarray(v, np.float64), 0, 1)
                f = {"log": feature.blob_log, "dog": feature.blob_dog, "doh": feature.blob_doh}[kind]
                bl = f(x, max_sigma=5 + 20 * a, threshold=0.02 + 0.15 * b)
                return np.float64(len(bl))
            return fn

        def _orb_count(v, a, b):
            """ORB(Oriented FAST and Rotated BRIEF)キーポイント検出数。

            skimage.feature.ORB で検出・記述を行い、実際に検出できたキーポイント
            数を返す(feature 出力)。

            ``a`` が要求する最大キーポイント数 ``n_keypoints`` を 50〜450 の範囲で
            振る(上限であり、画像のコントラストや構造が乏しいと実際の検出数は
            それより少なくなる)。``b`` は未使用。テクスチャの豊富さ・特徴点密度の
            目安として使える。
            """
            orb = feature.ORB(n_keypoints=int(50 + 400 * a))
            orb.detect_and_extract(np.clip(np.asarray(v, np.float64), 0, 1))
            return np.float64(len(orb.keypoints))

        def _random_walker(v, a, b):
            """ランダムウォーカー法によるグラフベース領域分割。

            skimage.segmentation.random_walker で、明暗の閾値から自動生成した
            2 クラスのシード(marker)を出発点に、各画素がどちらのシードへ拡散
            伝播しやすいかを解いて 2 値ラベルに分割し、そのラベル境界を返す
            (返り値は領域そのものではなく、領域の境界線 region)。

            ``a`` がシードの閾値幅を振る(暗側シード ``< 0.3+0.2a``、明側シード
            ``> 0.7-0.2a``。``a`` が大きいほどシードが広がり不定領域が減る)。
            ``b`` は拡散のしやすさを決める ``beta``(10〜210)を振り、大きいほど
            エッジをまたいだ伝播が抑えられ境界がシャープになる。
            """
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            markers = np.zeros(x.shape, np.int32)
            markers[x < (0.3 + 0.2 * a)] = 1
            markers[x > (0.7 - 0.2 * a)] = 2
            lab = segmentation.random_walker(x, markers, beta=10 + 200 * b)
            return segmentation.find_boundaries(lab).astype(np.float64)

        def _flood(v, a, b):
            """塗りつぶし(flood fill)領域抽出。

            画像中心の画素を種点とし、skimage.segmentation.flood でその画素値から
            ``tolerance`` 以内の連結画素を region として広げる。

            ``a`` が許容差 ``tolerance`` を 0.05〜0.35 の範囲で振る(大きいほど
            広く塗りつぶす)。``b`` は未使用。中心が背景か前景かで結果が大きく
            変わる(種点固定の単純な実装)。
            """
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            c = (x.shape[0] // 2, x.shape[1] // 2)
            return segmentation.flood(x, c, tolerance=0.05 + 0.3 * a).astype(np.float64)

        def _struct_coh(v, a, b):
            """構造テンソルのコヒーレンス(方位の一貫性)。

            skimage.feature.structure_tensor で勾配の 2 次モーメント行列を計算し、
            その固有値 ``l1>=l2`` から ``(l1-l2)/(l1+l2)`` を求める。値は 1 に
            近いほど局所的に強い一方向の構造(エッジ・線状パターン)、0 に近い
            ほど等方(平坦またはコーナー状)であることを示す。

            ``a`` が構造テンソルの平滑化スケール ``sigma`` を 0.5〜2.5 に振る。
            ``b`` は未使用。テクスチャの方向性の強さを測る特徴として使う
            (向き自体は返さない)。
            """
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            axx, axy, ayy = feature.structure_tensor(x, sigma=0.5 + 2 * a, order="rc")
            l1, l2 = feature.structure_tensor_eigenvalues([axx, axy, ayy])
            return _norm(np.nan_to_num((l1 - l2) / (l1 + l2 + 1e-8)))

        def _hessian_eig(v, a, b):
            """ヘッセ行列の最大固有値(絶対値)によるブロブ/リッジ強度。

            skimage.feature.hessian_matrix(ガウス微分によるヘッセ行列)から
            固有値を求め、絶対値が最大の成分 ``ev[0]`` を ``_norm`` で正規化して
            返す。曲率が強い箇所(ブロブの中心や稜線)ほど値が大きくなる。

            ``a`` が微分のスケール ``sigma`` を 0.5〜3.0 に振る(大きいほど太い
            構造に反応)。``b`` は未使用。符号は捨てているため、山(明るい
            blob)と谷(暗い blob)を区別しない。
            """
            x = np.clip(np.asarray(v, np.float64), 0, 1)
            H = feature.hessian_matrix(x, sigma=0.5 + 2.5 * a, order="rc", use_gaussian_derivatives=True)
            ev = feature.hessian_matrix_eigvals(H)
            # ★``ev[0]`` は**代数的**に最大の固有値であって、絶対値最大ではない。
            # 明るい稜線では主曲率が負なので ev[0] は絶対値の小さい方になり、
            # 稜線上で 0・両脇で 1 という**逆**の応答だった(2026-09-05 Fable レビュー、
            # 実測 [1, .64, 0, 0, 0, 0, .64, 1])。説明どおり絶対値最大を取る。
            return _norm(np.max(np.abs(ev), axis=0))

        def _unwrap_phase(v, a, b):
            """位相の 2π 折返しをつないで連続位相に戻し、``signed01`` で [0,1] へ。

            入力 [0,1] を位相 [-π, π] と読み替えて
            ``skimage.restoration.unwrap_phase`` に渡す。``a`` / ``b`` は未使用。

            非有限(NaN / Inf)の画素は**測れなかった点**として扱い、マスクして
            アンラップの経路から外す(skimage はマスク配列を受け取れる)。
            2026-09-05 の退化入力スイープで、**全 NaN の位相を渡すと 5 分以上
            返ってこない**ことが分かった —— 品質誘導のアンラップは有効画素を
            起点に伸びていくので、起点が 1 つも無いと止まらない。クラッシュと
            違って CI では「遅い」としか見えず、fail-soft のガードも効かない。
            有効画素がゼロなら「つなぐものが無い」ので、そのまま 0.5(位相 0)を返す。
            """
            x = np.asarray(v, np.float64)
            ok = np.isfinite(x)
            if not ok.any():
                return np.full(x.shape, 0.5, np.float64)
            ph = (np.clip(np.where(ok, x, 0.0), 0, 1) - 0.5) * 2 * np.pi
            if ok.all():
                return signed01(restoration.unwrap_phase(ph))
            out = restoration.unwrap_phase(np.ma.masked_array(ph, mask=~ok))
            # マスクされた画素は「不明」。位相 0 で埋めてから [0,1] に写す
            # (有効画素の連続性は保たれる)。
            return signed01(np.ma.filled(out, 0.0))

        sk = [
            ("xsk_inpaint", "restoration", "", IMAGE, IMAGE, _inpaint),
            ("xsk_richardson_lucy", "restoration", "", IMAGE, IMAGE,
             lambda v, a, b: np.clip(restoration.richardson_lucy(
                 np.clip(v, 0, 1), np.ones((3, 3)) / 9, num_iter=2 + int(a * 15)), 0, 1)),
            ("xsk_unwrap_phase", "restoration", "", IMAGE, IMAGE, _unwrap_phase),
            ("xsk_struct_coherence", "texture", "", IMAGE, IMAGE, _struct_coh),
            ("xsk_hessian_eig", "edges", "", IMAGE, IMAGE, _hessian_eig),
            ("xsk_random_walker", "segmentation", "", IMAGE, REGION, _random_walker),
            ("xsk_flood", "segmentation", "", IMAGE, REGION, _flood),
            ("xsk_blob_log", "features", "", IMAGE, FEATURE, _blob("log")),
            ("xsk_blob_dog", "features", "", IMAGE, FEATURE, _blob("dog")),
            ("xsk_blob_doh", "features", "", IMAGE, FEATURE, _blob("doh")),
            ("xsk_orb_count", "features", "", IMAGE, FEATURE, _orb_count),
            ("xsk_meijering", "texture", "", IMAGE, IMAGE,
             lambda v, a, b: _norm(filters.meijering(np.clip(v, 0, 1), sigmas=range(1, 4)))),
            ("xsk_sato", "texture", "", IMAGE, IMAGE,
             lambda v, a, b: _norm(filters.sato(np.clip(v, 0, 1), sigmas=range(1, 4)))),
        ]
        out += [Op(n, c, h, i, o, _safe(f, o)) for (n, c, h, i, o, f) in sk]
    except Exception:
        pass

    # ---- OpenCV photo / NPR / segmentation --------------------------------- #
    try:
        import cv2

        def _to3(v):
            return cv2.cvtColor(_u8(v), cv2.COLOR_GRAY2BGR)

        def _gray(im):
            return cv2.cvtColor(im, cv2.COLOR_BGR2GRAY).astype(np.float64) / 255

        def _stylize(v, a, b):
            """OpenCV の stylization(絵画風/カートゥーン風のノンフォトリアリスティック・
            レンダリング)。

            エッジ保存平滑化を使って細部を均しつつ主要な輪郭を残し、平坦な色面と
            目立つ輪郭からなるイラスト調の画像を作る(内部で 3ch に変換して処理し、
            結果をグレースケールへ戻す)。

            ``a`` が空間方向の平滑化範囲 ``sigma_s`` を 20〜120 で振る(大きいほど
            広い範囲を均す)。``b`` が色(輝度)差の許容範囲 ``sigma_r`` を 0.1〜0.5
            で振る(大きいほどエッジをまたいで均しやすくなり、平坦化が強まる)。
            """
            return _gray(cv2.stylization(_to3(v), sigma_s=20 + 100 * a, sigma_r=0.1 + 0.4 * b))

        def _pencil(v, a, b):
            """OpenCV の pencilSketch(鉛筆画風レンダリング)。

            エッジ保存平滑化とドッジ合成で鉛筆デッサン風の白黒スケッチを作る
            (返り値のうちグレースケール版のみ使用し、カラー版は捨てている)。

            ``a`` が平滑化の空間範囲 ``sigma_s`` を 20〜100 で振る。``b`` は
            色差許容 ``sigma_r``(0.05〜0.2)と陰影の濃さ ``shade_factor``
            (0.02〜0.08)の両方を同時に振る(2 つのパラメータを 1 つのノブに
            まとめている)。
            """
            g, _ = cv2.pencilSketch(_to3(v), sigma_s=20 + 80 * a, sigma_r=0.05 + 0.15 * b,
                                    shade_factor=0.02 + 0.06 * b)
            return g.astype(np.float64) / 255

        def _edge_preserve(v, a, b):
            """OpenCV の edgePreservingFilter(エッジ保存平滑化、``flags=1`` =
            RECURS_FILTER = 再帰フィルタ方式)。

            bilateral フィルタに近い効果をより高速に得る手法で、輪郭を保ちながら
            内部を滑らかにする。

            ``a`` が空間方向の平滑化範囲 ``sigma_s`` を 20〜120 で振る。``b`` が
            色差の許容範囲 ``sigma_r`` を 0.1〜0.6 で振る(大きいほど強く均す)。
            """
            return _gray(cv2.edgePreservingFilter(_to3(v), flags=1, sigma_s=20 + 100 * a,
                                                  sigma_r=0.1 + 0.5 * b))

        def _detail(v, a, b):
            """OpenCV の detailEnhance(細部強調)。

            エッジ保存平滑化をベースに、平坦部は滑らかに保ったまま微細な
            ディテール(テクスチャ)のコントラストを持ち上げる。

            ``a`` が空間範囲 ``sigma_s`` を 10〜50 で振る。``b`` が色差許容
            ``sigma_r`` を 0.1〜0.4 で振る。``xcv_edge_preserving`` と同系の
            処理だが、こちらは細部を「消す」のではなく「強調する」方向のフィルタ。
            """
            return _gray(cv2.detailEnhance(_to3(v), sigma_s=10 + 40 * a, sigma_r=0.1 + 0.3 * b))

        def _inpaint_cv(v, a, b):
            """欠損領域を推定して埋める修復(inpainting)。

            8bit 変換後、極端に明るい(>235)/暗い(<20)画素を「欠損」とみなして
            自動マスクし、OpenCV の Telea 法(高速マーチング法ベース、
            ``cv2.INPAINT_TELEA``)で周囲から埋める。``xsk_inpaint``
            (biharmonic 法)と同じ発想の別アルゴリズム版。

            半径 3 画素の近傍を使う(固定)。``a``, ``b`` は未使用。しきい値が
            固定のため、本来意味のある白飛び/黒つぶれ画素まで埋められてしまう
            場合がある。
            """
            x = _u8(v)
            mask = (((x > 235) | (x < 20)) * 255).astype(np.uint8)
            return cv2.inpaint(x, mask, 3, cv2.INPAINT_TELEA).astype(np.float64) / 255

        def _grabcut(v, a, b):
            """GrabCut(反復グラフカット)による前景/背景の自動分離。

            画像中央 70%×70%の固定矩形を「たぶん前景」の初期領域として与え、
            色分布の GMM とグラフカットで前景/背景を反復的に分離する
            (``cv2.GC_INIT_WITH_RECT``)。「確実な前景」と「たぶん前景」の画素を
            合わせて前景 region として返す。

            ``a`` が反復回数を 2〜5 回の範囲で振る(多いほど収束するが遅い)。
            ``b`` は未使用。矩形が画像中央固定のため、被写体が縁に寄っている
            画像では抽出に失敗しやすい。
            """
            img = _to3(v)
            h, w = img.shape[:2]
            mask = np.zeros((h, w), np.uint8)
            rect = (int(w * 0.15), int(h * 0.15), int(w * 0.7), int(h * 0.7))
            bg, fg = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
            cv2.grabCut(img, mask, rect, bg, fg, 2 + int(a * 3), cv2.GC_INIT_WITH_RECT)
            return ((mask == 1) | (mask == 3)).astype(np.float64)

        def _watershed_markers(v, a, b):
            """マーカー制御ウォーターシェッドによる境界線抽出。

            HALCON の ``watersheds``(ウォーターシェッドと分水嶺盆地を抽出する)に
            相当するが、ここでは盆地のラベルではなく **分水嶺の境界線** だけを
            region として返す(近似)。

            手順は古典的な OpenCV レシピ: Otsu 二値化 -> 膨張で「確実な背景」推定
            -> 距離変換のしきい値で「確実な前景」推定 -> 両者の差分を「不明」領域
            とし、確実な前景の連結成分をマーカーに ``cv2.watershed`` を実行。

            ``a`` が確実な前景を決めるしきい値を距離変換最大値の 30%〜70% の範囲
            で振る(大きいほど前景マーカーが小さく・保守的になり、過分割/過統合
            の傾向が変わる)。``b`` は未使用。
            """
            img = _to3(v)
            x = _u8(v)
            _, thr = cv2.threshold(x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            sure_bg = cv2.dilate(thr, np.ones((3, 3), np.uint8), iterations=3)
            dist = cv2.distanceTransform(thr, cv2.DIST_L2, 5)
            _, sure_fg = cv2.threshold(dist, (0.3 + 0.4 * a) * dist.max(), 255, 0)
            unknown = cv2.subtract(sure_bg, sure_fg.astype(np.uint8))
            _, markers = cv2.connectedComponents(sure_fg.astype(np.uint8))
            markers = markers + 1
            markers[unknown == 255] = 0
            markers = cv2.watershed(img, markers)
            return (markers == -1).astype(np.float64)

        def _orb_cv(v, a, b):
            """OpenCV 版 ORB(Oriented FAST and Rotated BRIEF)キーポイント検出数。

            ``cv2.ORB_create`` で検出のみ行い(記述子は計算しない)、検出できた
            キーポイント数を返す(feature 出力)。``xsk_orb_count``(skimage 版)
            と同じ発想の別実装で、検出器の実装が異なるため件数が一致するとは
            限らない。

            ``a`` が要求する最大特徴点数 ``nfeatures`` を 50〜500 の範囲で振る
            (上限であり、実際の検出数は画像内容に依存してそれより少なくなる)。
            ``b`` は未使用。
            """
            orb = cv2.ORB_create(nfeatures=int(50 + 450 * a))
            kp = orb.detect(_u8(v), None)
            return np.float64(len(kp))

        cv = [
            ("xcv_stylization", "artistic", "", IMAGE, IMAGE, _stylize),
            ("xcv_pencil_sketch", "artistic", "", IMAGE, IMAGE, _pencil),
            ("xcv_edge_preserving", "smoothing", "", IMAGE, IMAGE, _edge_preserve),
            ("xcv_detail_enhance", "gray", "", IMAGE, IMAGE, _detail),
            ("xcv_inpaint", "restoration", "", IMAGE, IMAGE, _inpaint_cv),
            ("xcv_grabcut", "segmentation", "", IMAGE, REGION, _grabcut),
            ("xcv_watershed_markers", "segmentation", "watersheds", IMAGE, REGION, _watershed_markers),
            ("xcv_orb_count", "features", "", IMAGE, FEATURE, _orb_cv),
        ]
        out += [Op(n, c, h, i, o, _safe(f, o)) for (n, c, h, i, o, f) in cv]
    except Exception:
        pass

    return out
