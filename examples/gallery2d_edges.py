# -*- coding: utf-8 -*-
"""事例: 2-D エッジ / 微分 / コーナー演算子ギャラリー (task: edges)

平たく言うと (この op ファミリーは何のためのものか):
  「画像のどこで明るさが急に変わるか(= 輪郭・エッジ)」「どこが角か(= コーナー特徴点)」
  を取り出す演算子ファミリー。中身は 4 系統 --
    * 一次微分の輪郭検出: sobel / prewitt / roberts / scharr / frei-chen / kirsch / robinson,
      勾配の強さ (amp/mag) と向き (dir) を返すもの。
    * 二次微分・帯域通過: laplace / LoG (laplace_of_gauss) / DoG (diff_of_gauss) / dog,
      ゼロ交差でエッジ、平坦部やなだらかな勾配には応答しない。
    * コーナー/特徴点: harris / min-eigen / foerstner / GFTT / FAST / Moravec / Kanade-Rosenfeld,
      直線エッジではなく「二方向に曲がる角」で強く応答。
    * 拡張系 (x*/f2_*/tf_*): PIL/scipy/wavelet/steerable/位相合同性 (phase congruency) や
      shock filter・topographic など、別バックエンド由来のエッジ・コーナー表現。
  用途: 物体の輪郭抽出、トラッキング/マッチング用の特徴点、欠陥・画質のエッジ強調。

検証(グラウンドトゥルース / 数値で嘘を弾く):
  edges カテゴリの **全 op** を実入力 (conftest 由来の再現画像) で呼び、op ごとに
    (1) 出力が有限     -- NaN / Inf を含まない
    (2) 宣言 out_sort と一致 -- image は 2 次元 float かつ値域 [0,1]
    (3) 決定的         -- 同一入力 → ビット一致 (2 回呼んで array_equal)
  を強制する。例外を投げた op は握りつぶさず即失敗させる。
  さらに挙動が既知の代表 op には beat-the-null つきの強い GT を課す:
    * sobel/prewitt/roberts_mag は段差(エッジ列)で強く応答し、平坦部では ~0
      (定数画像 = 勾配ゼロでは応答の分散 ~0)。
    * laplace / dog は定数画像(勾配ゼロ)に応答せず(帯域通過に DC 成分なし)、
      段差では明確に応答する。
    * cv_corner_harris は正方形の「角」で直線エッジ・平坦部より強く応答する
      (エッジ検出器ではなくコーナー検出器であることの確認)。

  edges カテゴリの全 op を漏れなく呼び、上記契約を全 op に、GT を代表 op に適用する。
  registry には 'laplace' が 2 度登録されている (素の実装 + _safe ラップ版; 出力は一致)
  ため登録エントリは 57、ユニーク名は 56。本例は 57 エントリすべて (両 laplace) を実行する。

    py -3.11 examples/gallery2d_edges.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import ops  # noqa: E402


# --------------------------------------------------------------------------- #
# 入力ファクトリ -- tests/conftest.py の image_bank / color_bank "normal" を複製。 #
# (examples は tests/ から import しない規約のため、構成をここに再掲する)          #
# --------------------------------------------------------------------------- #
def _image_normal(n: int = 48) -> np.ndarray:
    """conftest.image_bank(n)['normal'] と同一構成の 2-D float 画像 (値域 [0,1])。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    noise = 0.03 * np.random.default_rng(20260812).standard_normal((n, n))
    return np.clip(0.35 * grad + 0.45 * disk + checker + noise, 0, 1)


def _color_normal(n: int = 48) -> np.ndarray:
    """conftest.color_bank(n)['normal'] と同一構成の HxWx3 カラー画像。"""
    g = _image_normal(n)
    return np.clip(np.stack([g, 0.7 * g + 0.1, 1 - g], -1), 0, 1)


def input_for(in_sort: str) -> np.ndarray:
    """op.in_sort に合う妥当な入力を返す。edges ファミリーで出会う sort は image / color のみ。"""
    if in_sort == "image":
        return _image_normal()
    if in_sort == "color":
        return _color_normal()
    # registry が別 sort の edges op を増やしたら黙って通さず落とす。
    raise ValueError(f"input_for: unexpected in_sort for edges family: {in_sort!r}")


# --------------------------------------------------------------------------- #
# TARGET op 名 -- edges カテゴリの登録順・全 57 エントリを文字列リテラルで明示。    #
# ('laplace' は registry に 2 度登録されるため 2 回現れる; 下の drift チェックで  #
#  live registry の名前マルチセットと突き合わせる)。op→example 索引はこの列を読む。  #
# うち 5 件 (KORNIA_OPTIONAL) は backends_kornia (要 torch+kornia) 由来の任意 op で、  #
# 未インストール環境では registry から静かに消える (backends_kornia.build が [] を    #
# 返す; ops.py 側は例外を握りつぶす)。BASE = 常設分、OPTIONAL = kornia 依存分。         #
# --------------------------------------------------------------------------- #
OPS = [
    "sobel_mag", "laplace", "prewitt_mag", "roberts_mag", "dog", "grad_dir",
    "log", "corner_response", "sk_scharr", "sk_farid", "sk_dog", "sk_hessian_det",
    "sk_corner_harris", "cv_scharr", "cv_laplacian", "cv_corner_harris",
    "cv_min_eigen", "cv_precorner", "derivate_gauss", "laplace_of_gauss",
    "diff_of_gauss", "sobel_amp", "sobel_dir", "prewitt_amp", "prewitt_dir",
    "roberts", "kirsch_amp", "kirsch_dir", "frei_amp", "robinson_amp",
    "laplace", "points_foerstner", "points_harris_binomial", "dots_image",
    "frei_dir", "robinson_dir", "edges_color", "xsk_hessian_eig", "xpil_contour",
    "xpil_find_edges", "xsp_morph_laplace", "xsp_gauss_grad_mag", "xsk2_corner_kr",
    "xsk2_inv_gauss_grad", "xwt_hf_reconstruct", "xwt_directional_detail",
    "xsk3_corner_moravec", "xsk3_corner_fast", "xkor_laplacian", "xkor_harris",
    "xkor_gftt", "xkor_hessian", "xkor_dog", "f2_shock", "f2_topographic",
    "tf_steerable_filter", "tf_phase_congruency",
]

# kornia backend 依存の任意 op (torch/kornia 不在なら registry に現れない)。
KORNIA_OPTIONAL = ["xkor_laplacian", "xkor_harris", "xkor_gftt", "xkor_hessian", "xkor_dog"]
BASE_OPS = [n for n in OPS if n not in KORNIA_OPTIONAL]  # 常設分 (= 52)

_TOL = 1e-6  # 値域 [0,1] 判定の浮動小数許容。


def _validate(name: str, op, out) -> None:
    """1 op の出力に契約 (有限 / out_sort 一致 / 値域) を課す。違反は AssertionError。"""
    if op.out_sort in ("image", "region"):
        arr = np.asarray(out, dtype=np.float64)
        assert arr.ndim == 2, f"{name}: {op.out_sort} は 2 次元のはず (got ndim={arr.ndim})"
        assert np.all(np.isfinite(arr)), f"{name}: 非有限値 (NaN/Inf) を含む"
        lo, hi = float(arr.min()), float(arr.max())
        assert -_TOL <= lo and hi <= 1 + _TOL, f"{name}: 値域が [0,1] 外: ({lo}, {hi})"
    elif op.out_sort == "contour":
        assert isinstance(out, dict) and "cs" in out, f"{name}: contour は 'cs' を持つ dict のはず"
    elif op.out_sort == "feature":
        arr = np.asarray(out, dtype=np.float64)
        assert arr.ndim <= 1 and np.all(np.isfinite(arr)), f"{name}: feature は有限のスカラ/1D"
    else:
        raise AssertionError(f"{name}: 未対応の out_sort {op.out_sort!r}")


def _call_twice(op, sort):
    """同一入力で 2 回呼び、(出力, 決定的か) を返す。in-place 変更に備え copy を渡す。"""
    base = input_for(sort)
    a = op.fn(base.copy(), 0.5, 0.5)
    b = op.fn(base.copy(), 0.5, 0.5)
    deterministic = np.array_equal(np.asarray(a), np.asarray(b))
    return a, deterministic


# --------------------------------------------------------------------------- #
# GT 用の合成画像 (効果が既知)。                                                 #
# --------------------------------------------------------------------------- #
def _step_edge(n: int = 48) -> np.ndarray:
    x = np.zeros((n, n)); x[:, n // 2:] = 1.0  # 左 0 / 右 1、col=n/2 に縦エッジ
    return x


def _constant(n: int = 48, v: float = 0.4) -> np.ndarray:
    return np.full((n, n), v)


def _filled_square(n: int = 48) -> np.ndarray:
    x = np.zeros((n, n)); x[14:34, 14:34] = 1.0  # 4 隅を持つ塗り正方形
    return x


def _ground_truth_checks(BY) -> int:
    """挙動が既知の代表 op に beat-the-null つきの強い GT を課す。GT 件数を返す。"""
    n = 48
    step, const, sq = _step_edge(n), _constant(n), _filled_square(n)
    checks = 0

    # 一次微分エッジ検出: 段差で強く応答し平坦部では ~0。定数画像では応答分散 ~0。
    for name, margin in (("sobel_mag", 0.3), ("prewitt_mag", 0.3), ("roberts_mag", 0.2)):
        o = BY[name].fn(step.copy(), 0.5, 0.5)
        edge_resp = float(o[:, n // 2 - 1:n // 2 + 1].mean())
        flat_resp = float(o[:, 4:8].mean())
        assert edge_resp > flat_resp + margin, (
            f"GT {name}: エッジ応答 {edge_resp:.4f} が平坦部 {flat_resp:.4f} を上回らない")
        oc = BY[name].fn(const.copy(), 0.5, 0.5)
        assert float(oc.std()) < 1e-6, (
            f"GT {name}: 勾配ゼロの定数画像で応答が出ている (std={oc.std():.2e})")
        checks += 1

    # 二次微分・帯域通過: 定数画像には応答せず (DC なし)、段差では明確に応答。
    for name in ("laplace", "dog"):
        oc = BY[name].fn(const.copy(), 0.5, 0.5)
        assert float(np.abs(oc).mean()) < 1e-6, (
            f"GT {name}: 定数画像に応答している (|mean|={np.abs(oc).mean():.2e})")
        oe = BY[name].fn(step.copy(), 0.5, 0.5)
        assert float(oe.max()) > 0.1, f"GT {name}: 段差に応答していない (max={oe.max():.4f})"
        checks += 1

    # コーナー検出: 正方形の「角」が直線エッジ・平坦部より強い (= 単なるエッジ検出でない)。
    o = BY["cv_corner_harris"].fn(sq.copy(), 0.5, 0.5)
    corner = float(o[12:17, 12:17].max())   # 角 (14,14) 近傍
    straight = float(o[12:17, 22:27].max())  # 上辺中央 (直線エッジ)
    flat = float(o[22:27, 22:27].mean())     # 内部平坦
    assert corner > straight + 0.2 and corner > flat + 0.2, (
        f"GT cv_corner_harris: 角 {corner:.4f} が直線 {straight:.4f} / 平坦 {flat:.4f} を上回らない")
    checks += 1

    return checks


def main() -> None:
    # BY は task 指定どおり name->op (registry 全体; 'laplace' は 1 つに畳まれる)。
    BY = {o.name: o for o in ops.REGISTRY}

    edges = [o for o in ops.REGISTRY if o.category == "edges"]
    lap_entries = [o for o in edges if o.name == "laplace"]
    live_names = {o.name for o in edges}

    # --- kornia 不在なら KORNIA_OPTIONAL 分を除いた「利用可能集合」を対象にする ---- #
    skipped = sorted(n for n in KORNIA_OPTIONAL if n not in live_names)
    if skipped:
        print(f"skipped {len(skipped)} optional ops (kornia not installed): {', '.join(skipped)}")
    active_ops = [n for n in OPS if n not in skipped]
    expected = len(BASE_OPS) + (len(KORNIA_OPTIONAL) - len(skipped))

    # --- ハードコード OPS (利用可能集合) を live registry と突き合わせ (drift 検出) - #
    assert len(edges) == expected, (
        f"registry drift: edges エントリは {expected} のはず (got {len(edges)}, "
        f"base={len(BASE_OPS)} skipped_kornia={skipped})")
    assert len(lap_entries) == 2, f"'laplace' は edges に 2 度登録のはず (got {len(lap_entries)})"
    assert sorted(active_ops) == sorted(o.name for o in edges), "OPS の名前マルチセットが registry と不一致"
    assert len(active_ops) == expected, f"active_ops 長は {expected} のはず (got {len(active_ops)})"

    # --- 全 op を呼んで契約検証。'laplace' は 2 エントリを個別に実行 (影に隠さない) - #
    seen_laplace = 0
    n_called = 0
    for name in active_ops:
        if name == "laplace":
            # registry の 2 つの 'laplace' (素 / _safe ラップ) を順に実体で実行する。
            op = lap_entries[seen_laplace]
            seen_laplace += 1
        else:
            op = ops._BY_NAME[name]
            assert op.category == "edges", f"{name}: _BY_NAME が edges 以外を指している"
        out, deterministic = _call_twice(op, op.in_sort)
        assert deterministic, f"{name}: 非決定的 (同一入力で出力がビット不一致)"
        _validate(name, op, out)
        n_called += 1

    assert seen_laplace == 2, "両 laplace エントリを実行できていない"
    assert n_called == expected, f"呼び出し数が {expected} でない (got {n_called})"

    # --- 代表 op に強い GT ----------------------------------------------------- #
    gt = _ground_truth_checks(BY)

    print(f"PASS: {n_called} ops exercised ({len(set(active_ops))} unique names), "
          f"all finite/typed/deterministic; {gt} GT checks")


if __name__ == "__main__":
    main()
