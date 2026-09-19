# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""fullseye.inspect_batch — フォルダ(または画像列)を **一括で検査 → 集計 → レポート**(検査ワークフロー層 #1)。

ライン担当が最初に触る形は「画像フォルダを指して、前処理レシピと計測を決め、仕様で良否を
つけ、集計とレポートをもらう」。op を 1 枚ずつ呼ぶ API はあっても、この glue が無かった。

1 枚あたりの流れ::

    読む(read_image / .npy) → recipe(run_pipeline) → measure(callable → dict)
        → spec があれば judge → Verdict → 行 {path, hash, measurements, verdict, elapsed_ms}

**約束**:

- 列挙は **決定的**(ディレクトリは拡張子で絞って sorted。列で渡せばその順)。空なら
  ``ValueError`` —— 「0 枚を検査して全部 ok」は報告にならない。
- ``on_error="record"``(既定)で 1 枚の失敗(読めない・op が落ちた・計測が dict でない)は
  その行を ``error`` にして **バッチを止めない**。``"raise"`` なら即停止。
- 各行に入力ファイルの sha256(先頭 16 桁)を残す —— レポートの数字がどの bit 列から出たかを
  後から突き合わせられる(責任所在)。
- 数値の計測は列ごとに ``series`` に時系列化し、2 点以上あれば ``spc``(EWMA、目標=平均・
  σ=標本 std)で工程が管理状態かを添える。
- ``report_path`` の拡張子で ``.xlsx``(save_xlsx_report)/ ``.md``(report)/ ``.jsonl``
  (to_json_lines)に書き分け。``audit_path`` を渡すと 1 行 1 JSON の監査ログに **追記**する
  (時刻・hash・recipe・計測・verdict = #5 監査ログ)。

新しいアルゴリズムは無い。既存の read_image / run_pipeline / judge / spc_ewma / 3 系統レポートの
配線だけ —— だから前処理も計測も「呼び手が op を束ねる」形で受け取る(``measure`` は
``callable(processed) -> dict``)。
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import math
import numbers
import os
import time

import numpy as np

from fsruntime import Verdict
from fullseye.judge import judge

__all__ = ["inspect_batch", "as_verdict", "IMAGE_EXTS"]

#: ディレクトリ列挙で拾う拡張子(小文字比較)。``.npy`` は cv2 無しでも読める生配列。
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".npy")

_ON_ERROR = ("record", "raise")


def _list_inputs(paths_or_dir) -> list:
    if isinstance(paths_or_dir, (str, os.PathLike)):
        p = os.fspath(paths_or_dir)
        if os.path.isdir(p):
            names = sorted(n for n in os.listdir(p)
                           if os.path.splitext(n)[1].lower() in IMAGE_EXTS)
            return [os.path.join(p, n) for n in names]
        return [p]
    try:
        paths = [os.fspath(x) for x in paths_or_dir]
    except TypeError:
        raise ValueError("inspect_batch: paths_or_dir must be a directory, a path, "
                         "or an iterable of paths") from None
    return paths


def _sha16(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _load(path: str, sort: str):
    if path.lower().endswith(".npy"):
        arr = np.load(path, allow_pickle=False)
        want = 3 if sort in ("color", "rgb", "rgbimage") else 2
        if arr.ndim != want:
            raise ValueError("%s: expected a %d-D array for sort %r, got shape %s"
                             % (os.path.basename(path), want, sort, arr.shape))
        return np.asarray(arr, np.float64)
    import api
    return api.read_image(path, sort=sort)


def _is_number(v) -> bool:
    return isinstance(v, (numbers.Real, np.integer, np.floating)) and not isinstance(v, bool)


def _verdict_dict(v: Verdict) -> dict:
    return {"status": v.status, "detail": v.detail, "result": v.result}


def as_verdict(row: dict) -> Verdict:
    """行 dict の ``verdict`` を :class:`fsruntime.Verdict` に戻す(:func:`device.signal_verdict` へ)。
    未判定(spec 無し)の行は ``ValueError``(判定していないものを PLC に出さない)。"""
    v = row.get("verdict")
    if not v:
        raise ValueError("as_verdict: row %r has no verdict (no spec was given)" % row.get("path"))
    return Verdict(status=v["status"], result=v.get("result"),
                   elapsed_ms=float(row.get("elapsed_ms", 0.0)), detail=v.get("detail", ""))


def _series(rows: list) -> dict:
    keys: list = []
    for r in rows:
        for k, v in r["measurements"].items():
            if _is_number(v) and k not in keys:
                keys.append(k)
    out = {}
    for k in keys:
        col = []
        for r in rows:
            v = r["measurements"].get(k)
            col.append(float(v) if _is_number(v) else math.nan)
        out[k] = np.asarray(col, np.float64)
    return out


def _spc(series: dict) -> dict:
    from spc import spc_ewma
    out = {}
    for k, s in series.items():
        x = s[np.isfinite(s)]
        if x.size < 2:
            continue
        sd = float(np.std(x, ddof=1))
        ew = spc_ewma(x, float(np.mean(x)), sigma=sd if sd > 0 else 1e-12)
        out[k] = {"n": int(x.size), "target": float(ew["target"]), "sigma": sd,
                  "ucl_inf": float(ew["ucl_inf"]), "lcl_inf": float(ew["lcl_inf"]),
                  "alarms": list(ew["alarms"]), "in_control": bool(ew["in_control"])}
    return out


def _row_record(row: dict) -> dict:
    """レポート/監査用の平らな 1 行(JSON-native)。"""
    rec = {"path": os.path.basename(row["path"]), "hash": row["hash"],
           "status": row["verdict"]["status"] if row["verdict"] else "unjudged"}
    for k, v in row["measurements"].items():
        if k in ("path", "hash", "status", "detail", "elapsed_ms", "error"):
            k = "m_" + k                                     # 予約列と衝突する計測名は退避
        rec[k] = float(v) if _is_number(v) else (v if isinstance(v, (str, bool)) or v is None else str(v))
    rec["detail"] = row["verdict"]["detail"] if row["verdict"] else ""
    rec["elapsed_ms"] = float(row["elapsed_ms"])
    if row.get("error"):
        rec["error"] = row["error"]
    return rec


def _write_report(path: str, title: str, summary: dict, rows: list, series: dict, spc: dict) -> None:
    ext = os.path.splitext(path)[1].lower()
    records = [_row_record(r) for r in rows]
    sections = [("要約 / summary", [dict(summary)], "table"),
                ("画像ごと / per image", records, "table")]
    if spc:
        sections.append(("工程管理 (EWMA) / SPC", [dict(key=k, **v) for k, v in spc.items()], "table"))
    for k, s in series.items():
        if np.isfinite(s).any():
            sections.append(("系列 / series: %s" % k, s, "signal"))
    if ext == ".xlsx":
        from fullseye.xlsxio import save_xlsx_report
        save_xlsx_report(sections, path, title=title)
    elif ext == ".md":
        from fullseye.mdio import report
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(report(sections, title=title))
    elif ext == ".jsonl":
        from fullseye.jsonio import to_json_lines
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(to_json_lines([(rec, "table") for rec in records]) + "\n")
    else:
        raise ValueError("inspect_batch: report_path must end with .xlsx, .md or .jsonl (got %r)" % ext)


def _append_audit(path: str, title: str, recipe, spec, rows: list) -> None:
    from fullseye.jsonio import to_json_lines
    stamp = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    recipe_json = [list(s) if isinstance(s, (tuple, list)) else s for s in (recipe or [])]
    items = []
    for r in rows:
        rec = _row_record(r)
        rec.update({"time": stamp, "batch": title, "recipe": recipe_json,
                    "spec": spec if spec is not None else None,
                    "violations": (r["verdict"]["result"] or {}).get("violations", []) if r["verdict"] else []})
        items.append((rec, "table"))
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(to_json_lines(items) + "\n")


def inspect_batch(paths_or_dir, recipe=None, *, measure, spec=None, report_path=None,
                  audit_path=None, title=None, sort="image", on_error="record",
                  a=0.5, b=0.5) -> dict:
    """画像フォルダ(または画像パス列)を一括で 前処理 → 計測 → 判定 → 集計 する。

    ``recipe`` は :func:`api.run_pipeline` の stages(名前の列、または ``(name, a, b)`` の列。
    ``None`` / 空なら前処理なし)。``measure`` は ``callable(processed) -> dict`` で、計測 op を
    束ねて dict にするのは呼び手(例: ``lambda im: {"area": fs.apply(im, "area")}``)。
    ``spec`` を渡すと各画像の計測を :func:`fullseye.judge.judge` に通して Verdict を付ける。

    返り値::

        {"rows": [{"path", "hash", "measurements", "verdict"(dict or None), "elapsed_ms", "error"?}, ...],
         "series": {key: ndarray},                 # 数値計測の列(欠損は NaN)
         "summary": {"n", "ok", "ng", "error", "unjudged"},
         "spc": {key: {"in_control", "alarms", "target", "sigma", ...}},   # 2 点以上の列だけ
         "report_path": str | None, "audit_path": str | None}

    ``report_path`` は拡張子で ``.xlsx`` / ``.md`` / ``.jsonl`` に書き分け。``audit_path`` は
    JSON Lines の監査ログに追記。``on_error`` は ``"record"``(失敗行を error にして続行)か
    ``"raise"``。入力が 0 枚なら ``ValueError``(fail-closed)。
    """
    if on_error not in _ON_ERROR:
        raise ValueError("inspect_batch: on_error must be one of %s" % (_ON_ERROR,))
    if not callable(measure):
        raise ValueError("inspect_batch: measure must be callable(processed) -> dict")
    if spec is not None:
        from fullseye.judge import _validate_spec
        _validate_spec(spec)                                 # 仕様の壊れは 1 枚目の前に落とす
    paths = _list_inputs(paths_or_dir)
    if not paths:
        raise ValueError("inspect_batch: no input images (looked for %s)" % (IMAGE_EXTS,))
    title = title or "Inspection batch"
    stages = list(recipe) if recipe else []

    import api
    rows = []
    for path in paths:
        t0 = time.perf_counter()
        row = {"path": path, "hash": None, "measurements": {}, "verdict": None, "elapsed_ms": 0.0}
        try:
            row["hash"] = _sha16(path)
            img = _load(path, sort)
            processed = api.run_pipeline(img, stages, a=a, b=b) if stages else img
            m = measure(processed)
            if not isinstance(m, dict):
                raise TypeError("measure must return a dict, got %s" % type(m).__name__)
            row["measurements"] = dict(m)
            if spec is not None:
                row["verdict"] = _verdict_dict(judge(m, spec))
        except Exception as exc:                              # noqa: BLE001 — 1 枚の失敗を行に残す
            if on_error == "raise":
                raise
            row["error"] = "%s: %s" % (type(exc).__name__, exc)
            row["verdict"] = _verdict_dict(Verdict("error", result={"exception": row["error"]},
                                                   detail="error: " + row["error"]))
        row["elapsed_ms"] = (time.perf_counter() - t0) * 1000.0
        rows.append(row)

    summary = {"n": len(rows), "ok": 0, "ng": 0, "error": 0, "unjudged": 0}
    for r in rows:
        summary[r["verdict"]["status"] if r["verdict"] else "unjudged"] += 1
    series = _series([r for r in rows if not r.get("error")])
    spc = _spc(series)
    out = {"rows": rows, "series": series, "summary": summary, "spc": spc,
           "report_path": None, "audit_path": None}
    if report_path:
        _write_report(os.fspath(report_path), title, summary, rows, series, spc)
        out["report_path"] = os.fspath(report_path)
    if audit_path:
        _append_audit(os.fspath(audit_path), title, stages, spec, rows)
        out["audit_path"] = os.fspath(audit_path)
    return out
