# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""台帳(``ops3d.OPS3D``)の **宣言と実装の一致** を機械検証する回帰テスト。

二段構えになっている:

1. **個別の回帰** — 2026-09-01 に見つかった 7 件(宣言 out 型と実返りの乖離 5 件
   + 宣言 in 型の嘘 1 件 + 曲面モデル型の相乗り 1 件)。どれも「修正前は落ちて
   修正後は通る」最小再現で、実際に修正前のコードで失敗することを確認済み。

2. **台帳全体の健全性検査** — ``OPS3D`` の **全 op** について「宣言 out 型と実際の
   返り(``RESULT_ADAPTERS`` 適用後)が合う」ことを代表入力で確かめる。5 件だけ
   直して同じクラスの残りを見逃さないための網。

健全性検査の入力は **型プールの不動点閉包**で作る: 連鎖ファザー
(``tools/chain_fuzz``)の生成器で種を置き、実行できた op の産物を宣言 out 型の
プールへ戻す、を繰り返す。こうすると ``poly_surface`` のように**生成器を持たず
他の op だけが産む型**も自然に埋まり、その型を食う op まで検査が届く。

型判定の正本は ``tools/chain_fuzz.TYPE_CHECKS``(重複定義すると必ず drift する)。
到達できなかった op は **黙って飛ばさず**、理由つきで一覧に出す。
"""
from __future__ import annotations

import inspect
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (ROOT, os.path.join(ROOT, "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ops3d  # noqa: E402

cf = pytest.importorskip(
    "chain_fuzz",
    reason="tools/chain_fuzz.py が読めない(型判定の正本 TYPE_CHECKS がそこにある)")


# --------------------------------------------------------------------------- #
# 1. 個別の回帰(修正前に落ち、修正後に通る最小再現)                            #
# --------------------------------------------------------------------------- #
K_32 = np.array([[32.0, 0.0, 16.0], [0.0, 32.0, 16.0], [0.0, 0.0, 1.0]])


def _pts(n=160, seed=0):
    return np.random.default_rng(seed).random((n, 3)) * 10.0


def test_project_points_declares_keypoints_not_image():
    """project_points は画像ではなく (N,2) の投影点 + 深度を返す。

    修正前: out 宣言 "image2d" / adapter 無し → 素の返りは tuple で型の嘘。
    """
    meta = ops3d.info("project_points")
    assert meta["out"] == "keypoints"
    raw = ops3d.get("project_points")(_pts(), K_32)
    assert isinstance(raw, tuple) and len(raw) == 2      # 素の返りは (uv, depth)
    uv = ops3d.call("project_points", _pts(), K_32)      # 宣言型どおり
    assert isinstance(uv, np.ndarray) and uv.shape == (160, 2)
    assert cf.TYPE_CHECKS["keypoints"](uv)


def test_alpha_shape_boundary_declares_indices():
    """alpha_shape_boundary が返すのは点ではなく入力点への添字。

    修正前: out 宣言 "points"(= (N,3))だが実返りは (K,) int64。
    """
    assert ops3d.info("alpha_shape_boundary")["out"] == "indices"
    idx = ops3d.call("alpha_shape_boundary", _pts(), 1.0)
    assert idx.ndim == 1 and idx.dtype.kind in "iu"
    assert cf.TYPE_CHECKS["indices"](idx)
    assert not cf.TYPE_CHECKS["points"](idx)             # 旧宣言では型の嘘だった


def test_segment_rigid_motions_adapter_unwraps_labels():
    """segment_rigid_motions は dict を返す(motions は捨てられない)。

    修正前: out 宣言 "labels" / adapter 無し → 実返りは dict で型の嘘。
    """
    p0 = _pts()
    raw = ops3d.get("segment_rigid_motions")(p0, p0 + 0.1, 0.2)
    assert isinstance(raw, dict) and set(raw) == {"labels", "motions"}
    labels = ops3d.call("segment_rigid_motions", p0, p0 + 0.1, 0.2)
    assert cf.TYPE_CHECKS["labels"](labels)
    assert labels.shape == (len(p0),)


def test_pnp_declares_keypoints_and_rejects_images():
    """PnP の第 2 引数は (N,2) の画像平面点。画像を渡したら fail-closed。

    修正前: in 宣言が ["points", "image2d"] で、宣言どおり 32x32 の画像を渡すと
    生の IndexError になっていた。
    """
    for name in ("dlt_pose", "pnp_ransac", "reprojection_error"):
        assert ops3d.info(name)["in"][1] == "keypoints", name
    import pnp3d
    pts = _pts(40)
    image = np.random.default_rng(1).random((32, 32))
    with pytest.raises(ValueError, match=r"\(N, 2\) image-plane points"):
        pnp3d.pnp_ransac(pts, image, K_32, thresh=2.0)
    with pytest.raises(ValueError, match=r"\(N, 2\) image-plane points"):
        pnp3d.dlt_pose(pts, image, K_32)
    with pytest.raises(ValueError, match=r"\(N, 2\) image-plane points"):
        pnp3d.reprojection_error(pts, image, K_32, np.eye(3), np.zeros(3))


def test_pnp_accepts_project_points_output():
    """project_points の産物がそのまま PnP に入る(型が繋がっていることの実証)。"""
    import pnp3d
    R = np.eye(3)
    t = np.array([0.0, 0.0, 25.0])
    pts = _pts(50, seed=3)
    uv = ops3d.call("project_points", pts, K_32, R, t)
    R_est, t_est, mask, info = pnp3d.pnp_ransac(pts, uv, K_32, thresh=1e-3)
    assert np.allclose(R_est, R, atol=1e-6)
    assert np.allclose(t_est, t, atol=1e-5)
    assert info["n_inliers"] == len(pts)


def test_surface_models_are_separate_types():
    """多項式曲面 / B スプライン曲面 / B スプライン曲線は別型で、取り違えは fail-closed。

    修正前: 3 つとも out 宣言が "surface" で、eval_poly_surface に B スプライン
    モデルが流れると生の TypeError("list indices must be integers ...")だった。
    """
    import bspline_surf
    import match3d

    assert ops3d.info("fit_poly_surface")["out"] == "poly_surface"
    assert ops3d.info("fit_bspline_surface")["out"] == "bspline_surface"
    assert ops3d.info("fit_bspline_curve")["out"] == "bspline_curve"
    # 消費側も分かれている = 台帳の連鎖では取り違えが起きえない
    assert ops3d.info("eval_poly_surface")["in"][0] == "poly_surface"
    assert ops3d.info("eval_bspline_surface")["in"][0] == "bspline_surface"
    assert ops3d.info("eval_bspline_curve")["in"][0] == "bspline_curve"

    curve = bspline_surf.fit_bspline_curve(_pts(40))
    yy, xx = np.mgrid[0:8, 0:8].astype(float)
    poly = match3d.fit_poly_surface(xx, yy, xx * 0.1 + yy * 0.2)
    surf = bspline_surf.fit_bspline_surface(xx, yy, xx * 0.1 + yy * 0.2)

    # 素の呼び出し(型を分けても守れない経路)も名指しの ValueError で弾く
    with pytest.raises(ValueError, match="fit_poly_surface"):
        match3d.eval_poly_surface(curve, xx, yy)
    with pytest.raises(ValueError, match="fit_poly_surface"):
        match3d.eval_poly_surface(surf, xx, yy)
    with pytest.raises(ValueError, match="polynomial surface model"):
        bspline_surf.eval_bspline_surface(poly, xx, yy)
    with pytest.raises(ValueError, match="curve tck"):
        bspline_surf.eval_bspline_surface(curve, xx, yy)
    with pytest.raises(ValueError, match="surface tck"):
        bspline_surf.eval_bspline_curve(surf)

    # 正しい組み合わせは通り、宣言 out 型と一致する
    assert cf.TYPE_CHECKS["image2d"](match3d.eval_poly_surface(poly, xx, yy))
    assert cf.TYPE_CHECKS["image2d"](bspline_surf.eval_bspline_surface(surf, xx, yy))
    assert cf.TYPE_CHECKS["points"](bspline_surf.eval_bspline_curve(curve))


def test_surface_residual_adapter_yields_scalar():
    """surface_residual は dict(rms/max/pv)を返す → adapter で pv(形状誤差)。"""
    import bspline_surf
    yy, xx = np.mgrid[0:8, 0:8].astype(float)
    zz = xx * 0.1 + yy * 0.2
    surf = bspline_surf.fit_bspline_surface(xx, yy, zz)
    raw = ops3d.get("surface_residual")(xx, yy, zz, surf)
    assert isinstance(raw, dict) and set(raw) == {"rms", "max", "pv"}
    pv = ops3d.call("surface_residual", xx, yy, zz, surf)
    assert cf.TYPE_CHECKS["measurement"](pv)


def test_label_components_adapter_unwraps_labels():
    """label_components は (labels, n) を返す。vol_label と同じ "labels" 宣言へ。"""
    assert ops3d.info("label_components")["out"] == "labels"
    vol = np.zeros((6, 6, 6))
    vol[1:3, 1:3, 1:3] = 1.0
    vol[4:6, 4:6, 4:6] = 1.0
    raw = ops3d.get("label_components")(vol)
    assert isinstance(raw, tuple) and raw[1] == 2
    labels = ops3d.call("label_components", vol)
    assert cf.TYPE_CHECKS["labels"](labels) and labels.shape == vol.shape


# --------------------------------------------------------------------------- #
# 2. 台帳全体の健全性検査                                                       #
# --------------------------------------------------------------------------- #
#: このテスト固有の追加引数ヒント。``chain_fuzz.PARAM_HINTS`` に無いために
#: 「必須引数を束縛できず飛ばされる」op を減らすためだけのもので、ファザー本体の
#: 挙動は変えない(向こうは向こうの探索都合がある)。値はプールの寸法に合わせる:
#: points ∈ [0,10]^3 / image2d = 32x32 / voxel = 16^3。
EXTRA_PARAM_HINTS = {
    "tol": 1.5, "tau": 0.5, "min_inliers": 3, "min_voxels": 1,
    "voxel_size": 1.0, "min_distance": 2, "max_radius": 3, "r": 0.5,
    "ss": 2, "spatial_sigma": 2.0, "range_sigma": 0.2,
    "source": 0, "weight": 0.5, "trunc": 1.0,
    "eps": (1.0, 1.0),                       # スーパー2次曲面の形状指数 (eps1, eps2)
    "half_extents": np.array([2.0, 2.0, 2.0]),
    "plane_point": np.zeros(3), "plane_normal": np.array([0.0, 0.0, 1.0]),
    "albedo": 0.8, "light": np.array([0.0, 0.0, 1.0]),
    "H": np.eye(3),
    "transform": np.eye(4), "gt_transform": np.eye(4), "est_transform": np.eye(4),
    "R_gt": np.eye(3), "t_gt": np.zeros(3),
    "points_b": lambda rng: rng.random((160, 3)) * 10.0,
    "normals_b": lambda rng: np.tile([0.0, 0.0, 1.0], (160, 1)),
    "pts2": lambda rng: rng.random((160, 2)) * 32.0,
    "P1": np.hstack([K_32, np.zeros((3, 1))]),
    "P2": np.hstack([K_32 @ np.eye(3), (K_32 @ np.array([1.0, 0.0, 0.0]))[:, None]]),
    "depth_candidates": np.linspace(1.0, 2.0, 8),
    "scales": lambda rng: np.full(160, 0.3),      # points プールと同じ点数
    "opacities": lambda rng: np.full(160, 0.5),
    "offset": (0, 0, 0), "shape": (16, 16, 16),
    "fn": (lambda block: block),
}

#: op 固有の上書き(名前が同じでも意味・形が違う引数)。
EXTRA_OP_HINTS = {
    # sphere_sdf の R は **半径**(汎用ヒントの R = 回転行列と名前が衝突する)
    ("sphere_sdf", "R"): 3.0,
    ("sphere_sdf", "center"): np.array([5.0, 5.0, 5.0]),
    ("box_sdf", "center"): np.array([5.0, 5.0, 5.0]),
    # grid_coords / occupancy_grid の bounds は ((min,max) x3)。ファザーの
    # PARAM_HINTS["bounds"] は平坦 6-tuple なので、そちらでは毎回 ValueError
    ("grid_coords", "bounds"): ((0.0, 10.0), (0.0, 10.0), (0.0, 10.0)),
    ("grid_coords", "res"): 12,
    ("occupancy_grid", "bounds"): ((0.0, 10.0), (0.0, 10.0), (0.0, 10.0)),
    ("extract_surface_points", "bounds"): (0.0, 0.0, 0.0, 10.0, 10.0, 10.0),
    ("gaussians_to_voxel", "size"): 16,
    ("gaussians_to_voxel", "bounds"): (0.0, 0.0, 0.0, 10.0, 10.0, 10.0),
    ("vol_resize", "factor"): 1.0,
    ("angle_3points", "a"): np.array([1.0, 0.0, 0.0]),
    ("line_from_2points", "a"): np.array([1.0, 0.0, 0.0]),
    ("plane_from_3points", "a"): np.array([1.0, 0.0, 0.0]),
    ("inside_outside", "a"): np.array([2.0, 2.0, 2.0]),
    ("superquadric_residual", "a"): np.array([2.0, 2.0, 2.0]),
}

#: 実行に時間がかかりすぎる/この検査では意味の無い op(理由つきで飛ばす)。
SLOW_OR_UNSUITABLE = {
    "vol_tiled_map": "呼び手が渡すコールバックの挙動に依存(台帳の型契約とは別軸)",
}

#: **まだ直せていない**乖離。黙って許すのではなく、op 名と理由を明記し、
#: 「ちょうどこの集合だけ」であることを検査する(新しい乖離が増えれば落ちる)。
KNOWN_LEDGER_GAPS = {
    "vol_rle_components":
        "宣言 'rle_region'(単一領域)だが実返りは list[VolRLE](成分ごと)。"
        "adapter で r[0] にすると成分を黙って捨てるため採らず、out を 'table'"
        "(list|dict)へ移すのが筋。ただし tools/chain_fuzz.py が同 op に "
        "ローカル adapter(r[0])を後掛けしており、そこを直さないと "
        "'table' 宣言に対して VolRLE が返って新たな TYPEMISS になる。"
        "chain_fuzz.py は親が編集中で触れないため、台帳側も現状維持として記録する。",
}


def _resolve(hint, rng):
    return hint(rng) if callable(hint) and not isinstance(hint, np.ndarray) else hint


def _bind(name, fn, data_args, rng):
    """先頭に *data_args* を置き、残る必須引数をヒントで束縛。→ (args, kwargs) or 理由。"""
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return list(data_args), {}
    params = [p for p in sig.parameters.values()
              if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
    kwargs, unbound = {}, []
    for p in params[len(data_args):]:
        op_hint = EXTRA_OP_HINTS.get((name, p.name))
        if op_hint is None:
            op_hint = cf.OP_PARAM_HINTS.get((name, p.name))
        if p.default is not inspect.Parameter.empty:
            if op_hint is not None:
                val = _resolve(op_hint, rng)
                if val is not None:
                    kwargs[p.name] = val
            continue
        hint = op_hint
        if hint is None:
            hint = cf.PARAM_HINTS.get(p.name)
        if hint is None:
            hint = EXTRA_PARAM_HINTS.get(p.name)
        val = _resolve(hint, rng) if hint is not None else None
        if val is None:
            unbound.append(p.name)
            continue
        kwargs[p.name] = val
    if unbound:
        return None, "必須引数を束縛できない: " + ", ".join(unbound)
    return (list(data_args), kwargs), None


def _seed_pool():
    rng = np.random.default_rng(20260901)
    return {t: g(rng) for t, g in cf.make_generators().items()}


def audit_ledger(rounds: int = 4):
    """全 op を代表入力で 1 回ずつ実行し、宣言 out 型と実返りを突き合わせる。

    → ``{op 名: (判定, 詳細)}``。判定は
    OK / TYPEMISS / SUSPECT / CONTRACT / NOCHECK / SKIP。
    """
    pool = _seed_pool()
    verdict: dict[str, tuple[str, str]] = {}
    for _round in range(rounds):
        progressed = False
        for name, meta in sorted(ops3d.OPS3D.items()):
            if verdict.get(name, ("", ""))[0] in ("OK", "NOCHECK", "TYPEMISS"):
                continue
            fn = meta["func"]
            out, ins = meta["out"], meta["in"]
            if fn is None:
                verdict[name] = ("SKIP", "実体が見つからない(ops3d.missing)")
                continue
            if name in SLOW_OR_UNSUITABLE:
                verdict[name] = ("SKIP", SLOW_OR_UNSUITABLE[name])
                continue
            want = ["points" if t == "any" else t for t in ins]
            lack = sorted({t for t in want if t not in pool})
            if lack:
                verdict[name] = ("SKIP", "この型を産む op がまだ無い: " + ", ".join(lack))
                continue
            rng = np.random.default_rng(20260901)
            if name in cf.OP_ARG_BUILDERS:
                # in 宣言が「素直な先頭位置引数の並び」でない op(to_points の
                # any-of 列挙など)はファザーの専用ビルダーが正本
                built = cf.OP_ARG_BUILDERS[name]({t: [v] for t, v in pool.items()}, rng)
                if built is None:
                    verdict[name] = ("SKIP", "OP_ARG_BUILDERS が組み立てを断念")
                    continue
                args, kwargs = list(built[0]), dict(built[1])
            else:
                bound, why = _bind(name, fn, [pool[t] for t in want], rng)
                if bound is None:
                    verdict[name] = ("SKIP", why)
                    continue
                args, kwargs = bound
            try:
                res = fn(*args, **kwargs)
            except (ImportError, NotImplementedError) as exc:
                verdict[name] = ("SKIP", f"optional 依存 {type(exc).__name__}: {exc}")
                continue
            except ValueError as exc:
                verdict[name] = ("CONTRACT", f"ValueError: {str(exc)[:110]}")
                continue
            except Exception as exc:  # noqa: BLE001 — 生の例外漏れを検出するのが目的
                verdict[name] = ("SUSPECT", f"{type(exc).__name__}: {str(exc)[:110]}")
                continue
            adapter = ops3d.RESULT_ADAPTERS.get(name)
            if adapter is not None:
                try:
                    res = adapter(res)
                except Exception as exc:  # noqa: BLE001
                    verdict[name] = ("SUSPECT", f"RESULT_ADAPTERS が失敗: {exc}")
                    continue
            check = cf.TYPE_CHECKS.get(out)
            if check is None:
                verdict[name] = ("NOCHECK", f"型 {out!r} に正本の述語が無い "
                                            f"(実返り {type(res).__name__})")
            elif not check(res):
                verdict[name] = ("TYPEMISS", "宣言 %r だが %s%s を返した" % (
                    out, type(res).__name__, getattr(res, "shape", "")))
                continue
            else:
                verdict[name] = ("OK", "")
            if res is not None and out not in pool:
                pool[out] = res              # 新しい型が埋まった = 次の round で前進
                progressed = True
        if not progressed:
            break
    return verdict


@pytest.fixture(scope="module")
def ledger_audit():
    return audit_ledger()


def test_ledger_out_types_match_actual_returns(ledger_audit, capsys):
    """全 op で「宣言 out 型 == 実返り(adapter 適用後)」。同クラス一掃の網。"""
    bad = {n: d for n, (k, d) in ledger_audit.items() if k == "TYPEMISS"}
    with capsys.disabled():
        counts: dict[str, int] = {}
        for kind, _ in ledger_audit.values():
            counts[kind] = counts.get(kind, 0) + 1
        print("\n== ops3d 台帳 健全性検査: %d op %s" % (len(ledger_audit), counts))
        for kind in ("TYPEMISS", "SUSPECT"):
            for n, (k, d) in sorted(ledger_audit.items()):
                if k == kind:
                    known = " [既知・未修正]" if n in KNOWN_LEDGER_GAPS else ""
                    print("  [%s] %-30s %s%s" % (kind, n, d, known))
    new = {n: d for n, d in bad.items() if n not in KNOWN_LEDGER_GAPS}
    assert not new, "宣言 out 型と実返りが食い違う op(新規): %s" % new
    stale = sorted(set(KNOWN_LEDGER_GAPS) - set(bad))
    assert not stale, ("KNOWN_LEDGER_GAPS に残っているが実際は乖離していない: %s"
                       " — 直ったなら一覧から消すこと" % stale)


def test_ledger_no_raw_exceptions(ledger_audit):
    """代表入力で ValueError 以外の生の例外(TypeError/IndexError/…)を漏らさない。

    fail-closed がデフォルト = 入力が悪いなら「何が悪いか」を名指しする
    ValueError であるべきで、生の IndexError は契約の穴と区別がつかない。
    """
    bad = {n: d for n, (k, d) in ledger_audit.items() if k == "SUSPECT"}
    assert not bad, "生の例外を漏らした op: %s" % bad


def test_ledger_skips_are_reported_not_silent(ledger_audit, capsys):
    """到達できなかった op は理由つきで出力する(黙って飛ばさない)。"""
    skipped = {n: d for n, (k, d) in ledger_audit.items() if k == "SKIP"}
    nocheck = {n: d for n, (k, d) in ledger_audit.items() if k == "NOCHECK"}
    with capsys.disabled():
        print("\n== 到達できずスキップ: %d op" % len(skipped))
        for n, d in sorted(skipped.items()):
            print("  [SKIP]    %-30s %s" % (n, d))
        types = sorted({d.split("'")[1] for d in nocheck.values() if "'" in d})
        print("== 型述語が無く機械検証できない: %d op / 型 %s" % (len(nocheck), types))
    # 検査が空回りしていないことの下限(回帰よけ)。数はこのコミット時点の実測。
    ok = sum(1 for k, _ in ledger_audit.values() if k == "OK")
    assert ok >= 150, "健全性検査が届いた op が少なすぎる: OK=%d" % ok


def test_result_adapters_only_reference_real_ops():
    """RESULT_ADAPTERS の鍵はすべて台帳に実在する op(stale entry を作らない)。"""
    unknown = sorted(set(ops3d.RESULT_ADAPTERS) - set(ops3d.OPS3D))
    assert not unknown, "台帳に無い op の adapter: %s" % unknown


def test_every_declared_type_has_a_producer_or_generator():
    """入力に使われる型は「生成器がある」か「台帳内に産む op がある」。

    死んだ語彙(誰も産まない型を食う op = 永久に到達不能)を作らないための不変条件。
    """
    produced = {m["out"] for m in ops3d.OPS3D.values()} | set(cf.make_generators())
    consumed = {t for m in ops3d.OPS3D.values() for t in m["in"] if t != "any"}
    orphan = sorted(consumed - produced)
    assert not orphan, "誰も産まない型を入力に取る宣言がある: %s" % orphan
