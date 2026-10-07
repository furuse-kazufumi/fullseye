"""Universal contracts every operator in the registry must honour.

These are parametrized over the ENTIRE registry, so adding an operator
automatically subjects it to the same guarantees. Four contracts:

  * runs without exception on the edge-input battery,
  * every ndarray/feature output is finite (no NaN/Inf) — even on degenerate
    (constant / empty) inputs,
  * repeated calls on identical input are bit-identical (determinism — the
    evolution's holdout scoring depends on it),
  * the output matches the operator's declared out_sort (and regions stay in
    the unit range).
"""
from __future__ import annotations

import numpy as np
import pytest

import backend_safe as _bs
import ops
from conftest import _REQUIRE_OPTIONAL, KNOBS, copy_input, inputs_for, requires_full_registry

ALL_OPS = list(ops.REGISTRY)
OP_IDS = [op.name for op in ALL_OPS]


def _arrays(out):
    """Yield numeric ndarrays contained in an op output (handles contour dicts)."""
    if isinstance(out, np.ndarray):
        if out.size and np.issubdtype(out.dtype, np.number):
            yield out
    elif isinstance(out, dict):
        for c in out.get("cs", []):
            if isinstance(c, np.ndarray) and c.size:
                yield c


def _equal(x, y) -> bool:
    if isinstance(x, np.ndarray) and isinstance(y, np.ndarray):
        return x.shape == y.shape and np.array_equal(x, y, equal_nan=True)
    if isinstance(x, dict) and isinstance(y, dict):
        cs1, cs2 = x.get("cs", []), y.get("cs", [])
        return len(cs1) == len(cs2) and all(
            a.shape == b.shape and np.array_equal(a, b) for a, b in zip(cs1, cs2))
    try:
        return bool(np.all(np.asarray(x) == np.asarray(y)))
    except Exception:
        return repr(x) == repr(y)


#: 探針バンク(``conftest.BANKS``)が持たない in_sort。ここに載る op は下の 3 つの
#: 契約ゲート(例外を投げない / 非有限を出さない / 決定的)を **一度も実行されない**。
#: ★2026-09-14 実測: 901 op 中 **151 本(16.8 %)** がこの状態で、空ループを 1 周
#: しただけで緑を返していた —— 「門が判定を計算した直後に捨てる」の親戚で、
#: こちらは **判定を一度も計算しない**。まず skip で見えるようにし、
#: ``test_probeless_ops_do_not_grow`` で本数を台帳に固定する(減る分には通る)。
#: ★2026-09-14: **本来の直しを入れて 151 → 0 にした。** 上に「本来の直しは
#: ``conftest.BANKS`` を全 in_sort へ広げること」と自分で書いておきながら、
#: ラチェットで本数を凍結したまま 9 日が過ぎていた —— **台帳は免罪符になりやすい**
#: ([[feedback_never_weaken_the_probe_to_get_green]])。
#:
#: 足したのは 11 sort: points(56) / signal(27) / video(16) / qimage(11) /
#: cimage(9) / counts(8) / lightfield(8) / rgbimage(6) / matrix(4) / beatcube(4) /
#: keypoints(2) = 151 op。形は推測ではなく ``backends_bridge._EMPTY_OF``
#: (12 sort すべての**正準の最小値**)と ``problems.py`` の入力生成器から取った。
#: これで **901 op すべてが 3 つの契約ゲートを実際に通る**。
#:
#: **0 になった以上、このラチェットの役目は「増えたら落とす」に変わった。**
#: 新しい in_sort を足した人は ``conftest.BANKS`` に探針も足すこと —— 足さないと
#: その op たちは「登録されているのに一度も実行されない」状態に戻る。
PROBELESS_OPS_BUDGET = 0

#: 台帳の分類(``KNOWN_FALLS_BACK_ON_EDGE`` / ``KNOWN_SORT_VIOLATIONS``)。
BY_DESIGN = "by-design"        # op が退化入力を**明示の拒否文**で fail-closed にしている(契約どおり)
BACKEND = "backend-limit"      # 下請けライブラリがその入力(極小・定数)を扱えない
SUSPECT = "bug-suspect"        # op 側の欠陥が疑われる(knob の値域・固定形の補助引数・意図しない内部エラー)

#: ★2026-10-07: 契約電池で ``backend_safe.guard`` の fallback に落ちる op の台帳
#: ``{op: (分類, 落ちる入力名の集合, 理由)}``。
#:
#: 上の 3 契約(例外なし・有限・決定的)は ``op.fn`` を**guard 越しに**呼ぶ。guard は例外を
#: 握って sort の既定値を返し、非有限の出力は置き換えてから返す —— だから op 本体が
#: 例外を投げても NaN を出しても、assert の時点では「例外なし・有限・決定的」に見えていた
#: (2026-10-07 実測: 936 op 中 46 op が電池のどこかで黙って fallback、うち 8 op は
#: 疑わしい欠陥。``inputs_for`` が sort 既定の帯を返すようにしてさらに 10 op)。
#: 今は guard の台帳(``backend_safe.mark`` / ``events_since``)を見て、ここに無い
#: (op, 入力)で劣化が記録されたら赤にする。台帳の op が電池のどこでも落ちなくなったら
#: それも赤(直ったら行を消す)。入力名の集合は「これ以上増えない」上限として使う。
KNOWN_FALLS_BACK_ON_EDGE: dict = {
    "dl_guided_filter": (BACKEND, frozenset({"tiny4"}),
        "torch の reflect padding(5)が 4x4 画像より大きい"),
    "img_to_monogenic": (BY_DESIGN, frozenset({"tiny4"}),
        "4x4 画像には波長 9 px 前後の帯域に入る空間周波数が無い(monogenic_signal の明示拒否)。"
        "2026-10-07 まで knob a=0 が波長 2 px(ナイキスト)へ写り全入力で拒否していた —— 写しを 3〜15 px に直した"),
    "sk_wavelet": (BACKEND, frozenset({"const0", "const1", "const_mid"}),
        "skimage.denoise_wavelet が分散 0 の定数画像で全画素 NaN を返す(source=output)"),
    "tb_alpha_shape_boundary": (BY_DESIGN, frozenset({"coincident", "collinear", "plane_only", "single"}),
        "退化点群(共面・共線・一致・1 点)は Qhull が四面体分割できず拒否"),
    "tb_bandpass": (BY_DESIGN, frozenset({"tiny2"}),
        "2 サンプルの信号に filtfilt は掛けられない(明示拒否)"),
    "tb_beamform_delay_sum": (BY_DESIGN, frozenset({"const0", "single_chirp"}),
        "全ゼロの cube / 素子 1 個は到来方向が定義されない(明示拒否)"),
    "tb_dem_ecef_to_geodetic": (BY_DESIGN, frozenset({"coincident", "collinear", "normal", "plane_only", "single", "two_clusters"}),
        "sort 既定の探針は op_probe.OP_PROBE_OVERRIDE の理由で拒否される(override が先頭、sort 既定の帯は拒否を確かめる側)"),
    "tb_dtof_depth": (BY_DESIGN, frozenset({"const0", "flat"}),
        "光子ゼロ・平坦なヒストグラムにはピークが無い(明示拒否)"),
    "tb_dynsys_correlation_dimension": (BY_DESIGN, frozenset({"coincident", "collinear", "single"}),
        "N >= 32 点が要る(8 点・1 点の退化雲は明示拒否)"),
    "tb_estimate_alpha": (BY_DESIGN, frozenset({"coincident", "single"}),
        "全点一致・1 点では最近傍距離が無い(明示拒否)"),
    "tb_estimate_oriented_normals": (BY_DESIGN, frozenset({"coincident", "collinear", "single"}),
        "k=22 近傍に足りない点数(明示拒否)"),
    "tb_estimate_point_normals": (BY_DESIGN, frozenset({"single"}),
        "1 点の雲は 3 近傍が取れず法線が定義されない(明示拒否。2026-10-07 まで einsum の内部エラーだった)"),
    "tb_fit_spline_curve": (BACKEND, frozenset({"coincident", "single"}),
        "全点一致の雲は scipy splprep が Invalid inputs で拒否、1 点は点数 <= k の明示拒否"
        "(2026-10-07 に knob (1,1) → k=6 の写しを k ∈ [1,5] へ直した)"),
    "tb_fly_lgmd_eta": (BY_DESIGN, frozenset({"tiny2"}),
        "2 サンプルでは微分が取れない(明示拒否)"),
    "tb_fly_tau_from_expansion": (BY_DESIGN, frozenset({"tiny2"}),
        "2 サンプルでは微分が取れない(明示拒否)"),
    "tb_highpass": (BY_DESIGN, frozenset({"tiny2"}),
        "2 サンプルの信号に filtfilt は掛けられない(明示拒否)"),
    "tb_intrinsics_to_carla": (BY_DESIGN, frozenset({"ill_conditioned", "near_zero", "normal", "singular", "tall", "tiny2", "zeros"}),
        "sort 既定の探針は op_probe.OP_PROBE_OVERRIDE の理由で拒否される(override が先頭、sort 既定の帯は拒否を確かめる側)"),
    "tb_intrinsics_to_fullseye": (BY_DESIGN, frozenset({"ill_conditioned", "near_zero", "normal", "singular", "tall", "tiny2", "zeros"}),
        "sort 既定の探針は op_probe.OP_PROBE_OVERRIDE の理由で拒否される(override が先頭、sort 既定の帯は拒否を確かめる側)"),
    "tb_keypoints_to_image2d": (BY_DESIGN, frozenset({"empty"}),
        "空の keypoints は表現として無効(明示拒否)"),
    "tb_keypoints_uv_to_points": (BY_DESIGN, frozenset({"empty"}),
        "空の keypoints は表現として無効(明示拒否)"),
    "tb_landmark_asymmetry": (BY_DESIGN, frozenset({"coincident", "collinear", "single"}),
        "ランドマーク 1 点(偶数・4 点以上が要る、明示拒否)/ 全点一致・全点一直線では中点も左→右の向きも同じ直線上で、正中面が決まらない"
        "(2026-10-07 から明示拒否。以前は雑音で決まる任意の面を返していた)"),
    "tb_lf_epi_slope": (BY_DESIGN, frozenset({"single_view"}),
        "単一視点の光線場には EPI の傾きが無い(明示拒否)"),
    "tb_local_std": (BY_DESIGN, frozenset({"tiny2"}),
        "2 サンプルの信号は最小の窓(3)より短い(明示拒否。2026-10-07 に knob a=0 → window=2 の写しを [3,17] へ直した)"),
    "tb_lowpass": (BY_DESIGN, frozenset({"tiny2"}),
        "2 サンプルの信号に filtfilt は掛けられない(明示拒否)"),
    "tb_mirror_plane_from_pairs": (BY_DESIGN, frozenset({"coincident", "collinear", "single"}),
        "ランドマーク 1 点(偶数・4 点以上が要る、明示拒否)/ 全点一致・全点一直線では中点も左→右の向きも同じ直線上で、正中面が決まらない"
        "(2026-10-07 から明示拒否。以前は雑音で決まる任意の面を返していた)"),
    "tb_monogenic_amplitude": (BY_DESIGN, frozenset({"normal", "unit"}),
        "sort 既定の探針は op_probe.OP_PROBE_OVERRIDE の理由で拒否される(override が先頭、sort 既定の帯は拒否を確かめる側)"),
    "tb_monogenic_orientation": (BY_DESIGN, frozenset({"normal", "unit"}),
        "sort 既定の探針は op_probe.OP_PROBE_OVERRIDE の理由で拒否される(override が先頭、sort 既定の帯は拒否を確かめる側)"),
    "tb_monogenic_phase": (BY_DESIGN, frozenset({"normal", "unit"}),
        "sort 既定の探針は op_probe.OP_PROBE_OVERRIDE の理由で拒否される(override が先頭、sort 既定の帯は拒否を確かめる側)"),
    "tb_normals_to_egi": (BY_DESIGN, frozenset({"coincident", "collinear", "normal", "single"}),
        "sort 既定の探針は op_probe.OP_PROBE_OVERRIDE の理由で拒否される(override が先頭、sort 既定の帯は拒否を確かめる側)"),
    "tb_pc_density_equalize": (BY_DESIGN, frozenset({"coincident", "collinear", "single"}),
        "k が点数以上(8 点・1 点の雲、明示拒否)"),
    "tb_pc_fill_sparse": (BY_DESIGN, frozenset({"coincident", "collinear", "single"}),
        "k が点数以上(8 点・1 点の雲、明示拒否)"),
    "tb_project_cylindrical": (BY_DESIGN, frozenset({"coincident", "collinear", "plane_only", "single"}),
        "z の幅が 0 の雲は z_range を推定できない(明示拒否)"),
    "tb_quat_normalize_image": (BY_DESIGN, frozenset({"const0"}),
        "絶対値 0 の四元数は正規化の向きが無い(明示拒否)"),
    "tb_quaternion_to_rgb": (BY_DESIGN, frozenset({"normal", "real_only", "unit"}),
        "sort 既定の探針は op_probe.OP_PROBE_OVERRIDE の理由で拒否される(override が先頭、sort 既定の帯は拒否を確かめる側)"),
    "tb_reflection_symmetry_score": (BY_DESIGN, frozenset({"coincident", "single"}),
        "全点一致・1 点では正規化の尺度が無い(明示拒否)"),
    "tb_specular_coefficient_map": (BY_DESIGN, frozenset({"const0", "const1", "grey", "highlight", "normal"}),
        "sort 既定の探針は op_probe.OP_PROBE_OVERRIDE の理由で拒否される(override が先頭、sort 既定の帯は拒否を確かめる側)"),
    "tb_specular_diffuse_split": (BY_DESIGN, frozenset({"const0", "const1", "grey", "highlight", "normal"}),
        "sort 既定の探針は op_probe.OP_PROBE_OVERRIDE の理由で拒否される(override が先頭、sort 既定の帯は拒否を確かめる側)"),
    "tb_stat_correlation": (BY_DESIGN, frozenset({"singular", "zeros"}),
        "分散 0 の列は Pearson 相関が 0/0(明示拒否)"),
    "tb_stat_zscore": (BY_DESIGN, frozenset({"const0", "const1"}),
        "定数信号の z-score は 0/0(明示拒否)"),
    "tb_temporal_band_power": (BY_DESIGN, frozenset({"single_frame"}),
        "1 フレームの動画には時間周波数が無い(明示拒否)。2026-10-07 まで帯域 [3,5] Hz 固定で 12 フレームの"
        "探針にビンが無く全入力で拒否していた —— 帯域をその動画の DFT ビンから選ぶ形(backends_typed.CALL_TIME_ARGS)に直した"),
    "tb_temporal_bandpass": (BY_DESIGN, frozenset({"single_frame"}),
        "同上(1 フレームの動画には時間周波数が無い。明示拒否)"),
    "xcv3_brisk_count": (BACKEND, frozenset({"tiny4"}),
        "OpenCV BRISK の内部 resize が 4x4 で assert"),
    "xkor_clahe": (BACKEND, frozenset({"tiny4"}),
        "kornia CLAHE のタイル格子が 4x4 画像に収まらない"),
    "xkor_dog": (BACKEND, frozenset({"tiny4"}),
        "kornia の padding が 4x4 画像より大きい"),
    "xkor_laplacian": (BACKEND, frozenset({"tiny4"}),
        "kornia の padding が 4x4 画像より大きい"),
    "xsk2_hog": (BACKEND, frozenset({"tiny4"}),
        "skimage HOG は 12x12 以上を要求"),
    "xsk2_multiotsu": (BACKEND, frozenset({"const0", "const1", "const_mid", "single_bright"}),
        "skimage multiotsu は 3 クラスに 3 値以上を要求(定数・2 値画像)"),
    "xsk2_wiener": (BACKEND, frozenset({"tiny4"}),
        "4x4 画像で 5x5 窓の broadcast エラー(ライブラリ側の境界処理)"),
    "xsk_orb_count": (BACKEND, frozenset({"const0", "const1", "const_mid", "tiny4"}),
        "skimage ORB が定数・極小画像で特徴点ゼロを例外にする"),
    "xsk_random_walker": (BACKEND, frozenset({"const_mid"}),
        "定数画像から種(seed)が作れない"),
    "xsp_cspline_smooth": (BACKEND, frozenset({"tiny4"}),
        "scipy cspline の境界条件が 4x4 で収束しない"),
    "xsp_savgol": (BACKEND, frozenset({"tiny4"}),
        "savgol の窓長が 4 画素を超える"),
    "xsp_wiener": (BACKEND, frozenset({"const0"}),
        "scipy.signal.wiener が全ゼロ画像で全画素 NaN を返す(source=output)"),
    "xwt_mra_component": (BACKEND, frozenset({"tiny4"}),
        "pywt MRA の分解段数が 4x4 画像に足りない"),
}

#: ★2026-10-07: 宣言した out_sort の形を守っていない op(``test_op_honours_declared_sort`` の
#: else 枝 = points/signal/matrix/video/qimage/cimage/… の 120 op を新たに検査して見つかった)。
#: (2026-10-07 同日に 3 op を直して空になった: 複素の sort を名乗る tb_angular_spectrum_propagate /
#: tb_cx_apply_transfer_function / tb_fmcw_window_apply が、ops._wrap_unguarded の guard で実部だけにされ
#: float64 を返していた。表は器として残す —— 次に見つかった違反の置き場。)
KNOWN_SORT_VIOLATIONS: dict = {}


def _call_recording(op, iv, a, b, fell, iname):
    """``op.fn`` を 1 回呼び、guard が台帳に記録した劣化を ``fell[iname]`` に残す。

    ``backend_safe.mark()`` は記録のたびに増える通し番号なので、前後で値が違えば
    この呼び出しの中で劣化が起きた(リングから溢れて ``events_since`` が空でも分かる)。
    """
    m = _bs.mark()
    out = op.fn(copy_input(iv), a, b)
    if _bs.mark() != m and iname not in fell:
        ev = _bs.events_since(m, this_thread=False)
        e = ev[0] if ev else {"source": "?", "error": "event evicted from the ring"}
        err = str(e["error"])
        # ★2026-10-07(CI で判明): optional backend が無い環境の ImportError は「劣化」ではなく
        #   「この環境では走らない」—— requires_backend と同じく skip(py3.11 の完全環境では失敗にする)。
        if ("ImportError" in err or "ModuleNotFoundError" in err) and not _REQUIRE_OPTIONAL:
            pytest.skip("optional backend が無い: %s: %s" % (op.name, err[:160]))
        fell[iname] = "%s @ (a=%s, b=%s): %s" % (e["source"], a, b, err[:240])
        if op.name in KNOWN_ORDER_DEPENDENT:
            _record_order_dependent(op, iv, a, b, iname, err)
    return out


def _record_order_dependent(op, iv, a, b, iname, err):
    """順序依存の劣化が**起きた瞬間**の状態を warning に残す(再現できない欠陥の証拠集め)。

    単独では 2000 回呼んでも再現しない(2026-10-07 に 4 回試行)ので、推測を重ねる代わりに
    起きた全体実行の中で「同じ呼び出しをもう一度したら直るか(一過性か持続か)」「浮動小数の
    例外設定」「生の backend 出力の非有限画素」を測って CI ログに残す。
    """
    import warnings

    info = {"op": op.name, "input": iname, "a": a, "b": b, "err": err[:160],
            "np_geterr": np.geterr()}
    try:
        again = op.fn(copy_input(iv), a, b)
        info["recall_finite"] = bool(np.all(np.isfinite(np.asarray(again, dtype=complex))))
    except Exception as exc:                                   # noqa: BLE001
        info["recall_error"] = repr(exc)[:160]
    if op.name == "sk_gabor":
        try:
            from skimage import filters as _f
            raw = _f.gabor(np.asarray(copy_input(iv), dtype=np.float64), frequency=0.1 + 0.3 * a)[0]
            info["raw_nonfinite"] = int(np.size(raw) - np.count_nonzero(np.isfinite(raw)))
        except Exception as exc:                               # noqa: BLE001
            info["raw_error"] = repr(exc)[:160]
    warnings.warn("ORDER_DEPENDENT_FORENSICS %r" % (info,), stacklevel=2)


#: ★2026-10-07: **全体実行でだけ** fallback する op(単独・同じファイル群では再現しない)。
#: KNOWN_FALLS_BACK_ON_EDGE は「必ず落ちる」の完全一致なので、ここに載せたものは「落ちてもよい・
#: 落ちなくてもよい」として扱う —— 門を黙らせるのでなく、原因不明であることを名指しで残す置き場。
#: sk_gabor: -n 6 の全体スイートで tiny4 @ (a=0, b=0) の出力 16 画素中 8 画素が NaN(1 回観測)。
#:   単独・test_fix_gabor_dc / test_studio_params / test_fix_op_name_and_range / test_api_device と
#:   同じプロセスでは毎回有限。前に走った何かが残す大域状態が疑わしい(未特定、見直し台帳に載せた)。
KNOWN_ORDER_DEPENDENT: dict = {
    "sk_gabor": (frozenset({"tiny4"}), "全体実行でだけ tiny4 @ (0,0) が半分 NaN(原因未特定、2026-10-07)"),
}


def _assert_no_unledgered_fallback(op, fell):
    """台帳に無い (op, 入力) で劣化が記録されていないこと(新しい fallback は赤)。"""
    known = KNOWN_FALLS_BACK_ON_EDGE.get(op.name)
    allowed = known[1] if known else frozenset()
    if op.name in KNOWN_ORDER_DEPENDENT:
        allowed = allowed | KNOWN_ORDER_DEPENDENT[op.name][0]
    new = {k: v for k, v in fell.items() if k not in allowed}
    assert not new, (
        "%s が契約電池で guard の fallback に落ちた(例外か非有限の出力を guard が握り潰して"
        "いた)。直すか、理由つきで KNOWN_FALLS_BACK_ON_EDGE に載せる: %s" % (op.name, new))


def _probes(op):
    """この op に当てられる探針。空なら契約ゲートは何も検査できない。

    ★``op.name`` を渡すのは ``op_probe.OP_PROBE_OVERRIDE``(op 専用の探針と
    「なぜ sort 既定では駄目か」の理由)を引かせるため(2026-09-15)。
    """
    return list(inputs_for(op.in_sort, op.name))


@pytest.mark.parametrize("op", ALL_OPS, ids=OP_IDS)
def test_op_runs_without_exception(op):
    probes = _probes(op)
    if not probes:
        pytest.skip("in_sort '%s' に探針が無い(BANKS 未対応)" % op.in_sort)
    fell = {}
    for iname, iv in probes:
        for a, b in KNOBS:
            _call_recording(op, iv, a, b, fell, iname)  # must not raise
    # ★guard 越しでは「例外なし」は自明に真 —— 劣化の台帳で本当に走ったかを見る
    _assert_no_unledgered_fallback(op, fell)
    if op.name in KNOWN_FALLS_BACK_ON_EDGE:
        assert fell, ("%s は契約電池のどこでも fallback しなくなった —— "
                      "KNOWN_FALLS_BACK_ON_EDGE から行を消す" % op.name)


@pytest.mark.parametrize("op", ALL_OPS, ids=OP_IDS)
def test_op_output_is_finite(op):
    """No NaN/Inf on ANY battery input — degenerate inputs are the acid test."""
    probes = _probes(op)
    if not probes:
        pytest.skip("in_sort '%s' に探針が無い(BANKS 未対応)" % op.in_sort)
    # ★**非有限がその op の意味を運んでいる**ものは、この門の対象外。判断は
    #   ここで持たず `ops.NONFINITE_IS_MEANINGFUL` を**単一の正本として引く**
    #   (`test_backends_typed_liveness.KNOWN_NONFINITE_BY_CONTRACT` が同じ表の
    #    写しで、一致は別の検査が見ている。3 つ目の写しを作らない)。
    #
    #   2026-09-14: 探針バンクを 6 sort 広げたとき、ここで `tb_mat_cond`(特異行列の
    #   条件数 = inf)と `tb_geodesic_distances`(不達 = inf)が落ちた。一度
    #   **探針から特異行列と非連結点群を外して緑にしかけた**が、それは誤り ——
    #   台帳は「inf が正しい答え」と既に宣言しており、落ちていたのは**門がその
    #   台帳を見ていない**ことだった。探針を削って緑にするのは欠陥を隠す行為で、
    #   しかも同じ台帳の註に「自分の probe では特異行列を作っていなかったので
    #   tb_mat_cond を取りこぼした」という 2026-09-05 の教訓が書いてある。
    if op.name in ops.NONFINITE_IS_MEANINGFUL:
        pytest.skip("非有限が契約上の意味を持つ op(ops.NONFINITE_IS_MEANINGFUL): %s"
                    % ops.NONFINITE_IS_MEANINGFUL[op.name])
    fell = {}
    for iname, iv in probes:
        for a, b in KNOBS:
            out = _call_recording(op, iv, a, b, fell, iname)
            for arr in _arrays(out):
                bad = ~np.isfinite(arr)
                assert not bad.any(), (
                    f"{op.name} produced {int(bad.sum())} non-finite value(s) "
                    f"on input '{iname}' (a={a}, b={b})")
            if op.out_sort == "feature":
                f = np.asarray(out, np.float64).reshape(-1)
                assert f.size >= 1 and np.isfinite(f[0]), (
                    f"{op.name} feature non-finite on '{iname}' (a={a}, b={b})")
    # ★guard は非有限の出力を置き換えてから返す(source=output で台帳に残る)。
    #   上の assert は置き換え後を見ているので、台帳の側で「置き換えが起きていない」を確かめる。
    _assert_no_unledgered_fallback(op, fell)


@pytest.mark.parametrize("op", ALL_OPS, ids=OP_IDS)
def test_op_is_deterministic(op):
    """Same input twice -> identical output (required for reproducible scoring).

    Iterate every battery input and repeat 3x: uninitialized-buffer bugs
    (e.g. cv2 warp on unmapped pixels) are flaky, so a single input/pair can
    miss them. A correct op is identical across all of them.
    """
    probes = _probes(op)
    if not probes:
        pytest.skip("in_sort '%s' に探針が無い(BANKS 未対応)" % op.in_sort)
    fell = {}
    for iname, iv in probes:
        ref = _call_recording(op, iv, 0.5, 0.5, fell, iname)
        for _ in range(3):
            again = _call_recording(op, iv, 0.5, 0.5, fell, iname)
            assert _equal(ref, again), f"{op.name} is nondeterministic on input '{iname}'"
    # ★fallback の値は自明に決定的 —— 比べたのが op 本体の出力であることを台帳で確かめる
    _assert_no_unledgered_fallback(op, fell)


def test_fallback_ledgers_name_live_ops_and_real_inputs():
    """台帳の op 名が実在し、入力名がその op の電池に実在すること(綴り違い・改名の残骸を弾く)。"""
    requires_full_registry()
    by = {op.name: op for op in ALL_OPS}
    stale = sorted(set(KNOWN_FALLS_BACK_ON_EDGE) - set(by))
    assert not stale, "居ない op が KNOWN_FALLS_BACK_ON_EDGE に残っている: %s" % stale
    stale = sorted(set(KNOWN_SORT_VIOLATIONS) - set(by))
    assert not stale, "居ない op が KNOWN_SORT_VIOLATIONS に残っている: %s" % stale
    for name, (cat, inputs, why) in KNOWN_FALLS_BACK_ON_EDGE.items():
        assert cat in (BY_DESIGN, BACKEND, SUSPECT) and why, name
        names = {iname for iname, _ in _probes(by[name])}
        assert inputs and inputs <= names, (name, sorted(inputs - names))
    assert len(KNOWN_FALLS_BACK_ON_EDGE) <= 56, (
        "fallback 台帳が 2026-10-07 の 56 行より増えた —— 台帳は言い訳の置き場ではない")


def test_probeless_ops_do_not_grow():
    """探針の当たらない op を**台帳で固定**する(減る分には通る)。

    上の 3 つの契約ゲートは、探針が無い op に対しては何も検査できない。skip に
    したので見えるようにはなったが、**skip は緑**なので放っておくと増える。
    ここで本数を上限として押さえ、新しい in_sort を足した人が探針も足すよう促す。
    ★本来の直しは ``conftest.BANKS`` を全 in_sort へ広げること(``op_probe`` の
    探針生成を流用できる)。この台帳はその作業までの見張りであって、代わりではない。
    """
    from collections import Counter
    probeless = Counter(op.in_sort for op in ALL_OPS if not _probes(op))
    total = sum(probeless.values())
    assert total <= PROBELESS_OPS_BUDGET, (
        "探針の無い op が %d 本に増えた(上限 %d)。内訳 %s —— "
        "新しい in_sort を足したなら conftest.BANKS に探針も足すこと"
        % (total, PROBELESS_OPS_BUDGET, dict(probeless)))


@pytest.mark.parametrize("op", ALL_OPS, ids=OP_IDS)
def test_op_honours_declared_sort(op):
    iv = next(iter(inputs_for(op.in_sort, op.name)), None)
    if iv is None:
        pytest.skip(f"no input bank for sort {op.in_sort}")
    out = op.fn(copy_input(iv[1]), 0.5, 0.5)
    os_ = op.out_sort
    if os_ in ("image", "region"):
        assert isinstance(out, np.ndarray) and out.ndim == 2, f"{op.name} {os_} not 2-D ndarray"
    elif os_ == "color":
        assert isinstance(out, np.ndarray) and out.ndim == 3 and out.shape[-1] == 3
    elif os_ == "volume":
        assert isinstance(out, np.ndarray) and out.ndim == 3
    elif os_ == "feature":
        assert np.asarray(out, np.float64).reshape(-1).size >= 1
    elif os_ == "contour":
        assert isinstance(out, dict) and "cs" in out and "shape" in out
    elif os_ == "match":
        assert isinstance(out, np.ndarray) and out.ndim == 1
    else:
        # ★2026-10-07: ここに else が無く、points/signal/matrix/video/qimage/cimage/counts/
        #   keypoints/rgbimage/beatcube/lightfield/any の 120 op は**何も検査されずに緑**だった。
        #   形の契約の正本は backends_typed._sort_ok(進化の橋の出口と同じ表)。複素の sort は
        #   dtype も見る(backends_bridge._COMPLEX_SORTS)。
        import backends_typed as _bt
        from backends_bridge import _COMPLEX_SORTS

        ok = bool(_bt._sort_ok(out, os_))
        if ok and os_ in _COMPLEX_SORTS:
            ok = bool(np.iscomplexobj(out))
        known = KNOWN_SORT_VIOLATIONS.get(op.name)
        if known is not None:
            assert not ok, ("%s は out_sort=%s を守るようになった —— KNOWN_SORT_VIOLATIONS から"
                            "行を消す" % (op.name, os_))
            pytest.xfail("[%s] %s" % known)
        assert ok, ("%s: out_sort=%s を宣言したが %s (shape=%s, dtype=%s) が返った"
                    % (op.name, os_, type(out).__name__, getattr(out, "shape", None),
                       getattr(out, "dtype", None)))


@pytest.mark.parametrize("op", [o for o in ALL_OPS if o.out_sort == "region"],
                         ids=[o.name for o in ALL_OPS if o.out_sort == "region"])
def test_region_output_in_unit_range(op):
    for iname, iv in inputs_for(op.in_sort, op.name):
        out = op.fn(copy_input(iv), 0.5, 0.5)
        if isinstance(out, np.ndarray) and out.size:
            mn, mx = float(np.min(out)), float(np.max(out))
            assert mn >= -1e-9 and mx <= 1 + 1e-9, (
                f"{op.name} region out of [0,1] on '{iname}': min={mn} max={mx}")
