"""studio_result.py — the Qt-free *result layer* shared by Fullseye Studio and the engine.

Everything here is pure numpy / stdlib, so it runs outside the Qt UI — the browser
(Pyodide) Studio consumes the very same code the desktop app does. It holds three
things, all of which the Studio UX programme (2026-10-19) calls for:

* :func:`assess_validity` — a result's ``(valid, reasons)`` kept SEPARATE from "it ran
  without raising" (ideas 129 / 130). An op with no success information is *not judged*
  (``valid is None``), never reported green just because no exception happened; non-finite
  counts are named, never blanked. The layer **reports only** — it never changes or hides
  an op's numbers.
* :func:`input_reference` / :func:`resolve_input_ref` — a saved project's input is kept as a
  reference (path + sha256 + size + shape/dtype), so a reopened project can tell whether the
  input is the same file, a changed one, or missing, and offer to re-link it (idea 145).
* :class:`StageCache` — a memory-bounded, LRU stage-output cache (idea 113 "re-compute only
  from the edited stage"; idea 116 "let the user adjust the cache size"). Editing stage *k*
  invalidates *k..n* only; a byte budget bounds retained array memory.

studio.py re-exports the validity / input helpers, so ``studio.assess_validity`` etc. keep
working; engine.py builds its browser-facing ``run_cached`` / ``stepwise_states`` on them.
"""
from __future__ import annotations

import hashlib
import os
import re

import numpy as np

__all__ = [
    "assess_validity", "file_sha256", "input_reference", "resolve_input_ref",
    "StageCache", "array_nbytes", "CACHE_BUDGET_BYTES",
]

# --------------------------------------------------------------------------- #
# 結果の妥当性(ran / valid / reasons を分けて持つ)。Studio は**報告するだけ**で、
# op の数値の問題を直したり隠したりしない。
# --------------------------------------------------------------------------- #
#: 結果の dict が持つ「妥当/非妥当」の明示欄(opsmultivar / lensopt / spc / drive* などの実在の名前)。
_VALIDITY_KEYS = ("converged", "valid", "guf_valid", "ok", "success")
#: ``status`` 欄の文字列のうち、失敗を意味するもの / 成功を意味するもの(出典タグの "primary" などは判定しない)。
_STATUS_BAD = frozenset({"failed", "failure", "error", "diverged", "not_converged", "nonconverged",
                         "max_iter", "maxiter", "max_iterations", "singular", "invalid", "degenerate"})
_STATUS_GOOD = frozenset({"converged", "ok", "success", "succeeded"})


def _is_binary(a):
    # ★2026-10-04: bool の配列(占有格子など、台帳の op が返す)は np.round が bool へ書き戻せず落ちた —— bool はそのまま二値
    if a.dtype == bool:
        return True
    a = np.asarray(a, dtype=np.float64) if a.dtype.kind in "iu" else a
    if a.size > 4096:
        sample = a.reshape(-1)[:4096]
        finite = sample[np.isfinite(sample)]
        if np.unique(finite).size > 2:
            return False
    u = np.unique(a[np.isfinite(a)]) if a.size else a
    return u.size <= 2 and set(np.round(u, 6).tolist()).issubset({0.0, 1.0})


def _bool_verdict(x):
    """明示欄 1 つの判定: True / False / None(読めない)。大きい bool 配列は「有効が 1 つも無い」時だけ False。"""
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, np.ndarray) and x.dtype == bool and x.size:
        if x.size == 1:
            return bool(x.reshape(-1)[0])
        return None if x.any() else False
    return None


def assess_validity(val):
    """結果の妥当性を ``(valid, reasons)`` で返す。valid は True / False / None(未判定)。

    * 結果が dict で明示欄(``converged`` / ``valid`` / ``guf_valid`` / ``ok`` / ``success`` /
      ``status`` / ``n_iter`` と ``max_iter``)を持てば、それを写す。どれかが偽なら False。
    * 配列は、非有限値・空・(実数画像で)一定値のときだけ False。それ以外は**判定しない(None)**
      —— 妥当性の情報が無い結果に「OK」を出さない。
    報告するだけで、値は一切変えない。"""
    why = []
    if isinstance(val, dict):
        good = False
        for k in _VALIDITY_KEYS:
            if k not in val:
                continue
            r = _bool_verdict(val[k])
            if r is False:
                big = isinstance(val[k], np.ndarray) and val[k].size > 1
                why.append("%s is False%s" % (k, " (no valid entries)" if big else ""))
            elif r is True:
                good = True
        st = val.get("status")
        if isinstance(st, str):
            sl = st.strip().lower()
            if sl in _STATUS_BAD:
                why.append("status=%s" % st)
            elif sl in _STATUS_GOOD:
                good = True
        for ik in ("n_iter", "iterations"):
            mi = val.get("max_iter", val.get("max_iterations"))
            n = val.get(ik)
            if (isinstance(n, (int, np.integer)) and isinstance(mi, (int, np.integer))
                    and not isinstance(n, bool) and mi > 0 and n >= mi):
                why.append("reached max_iter (%d)" % int(mi))
                break
        if why:
            ir = val.get("invalid_reasons")
            if isinstance(ir, (list, tuple)):
                why.extend(str(x) for x in ir[:8])
            return False, why
        return (True, []) if good else (None, [])
    if isinstance(val, (float, complex, np.floating, np.complexfloating)):
        val = np.asarray(val)
    if not isinstance(val, np.ndarray):
        return None, []
    if val.size == 0:
        return False, ["empty result"]
    if val.dtype.kind in "fc":
        fin = np.isfinite(val)
        k = int(val.size - np.count_nonzero(fin))
        if k:
            why.append("%d non-finite values" % k)
        if val.ndim in (2, 3) and fin.any():
            num = np.abs(val[fin]) if val.dtype.kind == "c" else val[fin]
            if float(np.ptp(num)) == 0.0 and not _is_binary(val):
                why.append("constant image (all pixels equal)")
    return (False, why) if why else (None, [])


# --------------------------------------------------------------------------- #
# 入力画像の参照(project 保存)。path / sha256 / size(bytes)/ shape / dtype。
# --------------------------------------------------------------------------- #
def file_sha256(path):
    """ファイルのバイト列の sha256(16 進)。読めなければ OSError。"""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def input_reference(path, image=None):
    """project 保存に入れる入力画像の参照: path(与えられたまま)・sha256・size(bytes)・shape・dtype。

    ``size`` はファイルのバイト長(idea 145 "入力ファイルの指紋")。sha256 と合わせて、
    開き直したときに「同じファイルか / 中身が変わったか」を安く見分ける第一の手掛かりになる。"""
    ref = {"path": str(path), "sha256": file_sha256(path)}
    try:
        ref["size"] = int(os.path.getsize(path))
    except OSError:
        pass
    if image is not None:
        arr = np.asarray(image)
        ref["shape"] = [int(v) for v in arr.shape]
        ref["dtype"] = str(arr.dtype)
    return ref


def _valid_input_ref(d):
    """保存ファイルの ``input`` 欄を読む。壊れていたら None(古い形と同じ扱い。読み込みは落とさない)。"""
    if not isinstance(d, dict) or not isinstance(d.get("path"), str) or not d["path"]:
        return None
    if not isinstance(d.get("sha256"), str):
        return None
    ref = {"path": d["path"], "sha256": d["sha256"]}
    if isinstance(d.get("size"), int) and not isinstance(d.get("size"), bool):
        ref["size"] = d["size"]
    if isinstance(d.get("shape"), list) and all(isinstance(v, int) and not isinstance(v, bool) for v in d["shape"]):
        ref["shape"] = list(d["shape"])
    if isinstance(d.get("dtype"), str):
        ref["dtype"] = d["dtype"]
    return ref


def resolve_input_ref(ref, base_dir):
    """保存された入力参照を今の環境へ当てる。``{"status", "path", "message"}`` を返す。

    status: ``ok``(ある・sha256 一致 = 黙って読む)/ ``changed``(ある・不一致 = 読むが警告)/
    ``relinked``(元の場所に無く、.json の隣の同じ名前で見つかった・一致)/ ``missing``(見つからない =
    今の画像を保つ)。相対 path は .json のあるフォルダ基準。"""
    given = str(ref["path"])
    cand = given if os.path.isabs(given) else os.path.join(base_dir, given)
    name = re.split(r"[\\/]", given)[-1]

    def _same(p):
        try:
            return file_sha256(p) == ref.get("sha256")
        except OSError:
            return None

    if os.path.isfile(cand):
        same = _same(cand)
        if same:
            return {"status": "ok", "path": cand, "message": ""}
        if same is not None:
            return {"status": "changed", "path": cand,
                    "message": "input file changed since save: %s" % given}
    alt = os.path.join(base_dir, name) if name else ""
    if alt and os.path.isfile(alt) and os.path.abspath(alt) != os.path.abspath(cand):
        same = _same(alt)
        if same:
            return {"status": "relinked", "path": alt,
                    "message": "input relinked by file name: %s -> %s" % (given, alt)}
        if same is not None:
            return {"status": "changed", "path": alt,
                    "message": "input file changed since save: %s (found next to the project file)" % given}
    return {"status": "missing", "path": None, "message": "input not found: %s" % given}


# --------------------------------------------------------------------------- #
# ステージ結果キャッシュ(メモリ上限つき LRU)。engine 層に置き、Qt の外(ブラウザ版)からも使える。
# --------------------------------------------------------------------------- #
#: 既定のキャッシュ予算(bytes)。保持する段の出力配列の合計をこの範囲に収める。
#: 512x512 float64 1 枚 = 2 MB、20 段で ~42 MB。既定 256 MB なら通常のパイプラインは全段を保持し、
#: 大画像・長いパイプラインでだけ古い段から捨てる。利用者は :meth:`StageCache.set_budget` で変えられる(idea 116)。
CACHE_BUDGET_BYTES = 256 * 1024 * 1024


def array_nbytes(v):
    """値が保持するバイト数(ndarray のみ数える。スカラー・dict は ~0)。"""
    return int(v.nbytes) if isinstance(v, np.ndarray) else 0


def over_budget(total_bytes, budget_bytes, kept):
    """予算超過かを 1 箇所で判定(StageCache と PipelineModel が同じ規則を使う単一の入口)。

    ``kept`` は現在値を保持している段の数。予算を超えていても **最低 1 段は残す**
    (1 段の出力だけで予算を超える場合に空にして毎回再計算する事故を避ける)。"""
    return total_bytes > budget_bytes and kept > 1


class StageCache:
    """線形パイプライン用の、メモリ上限つき LRU なステージ出力キャッシュ(engine 層・Qt 非依存)。

    鍵は **prefix key**: 入力の同一性ハッシュ + その段までの各段の ``(op, a, b, bypass)`` 列。
    段 *k* を編集すると *k..n* の prefix key が変わって一致しなくなり再計算対象になる。*0..k-1* は残る。

    バイト予算が保持配列メモリの総量を抑える。超えると least-recently-used な段の **値** を捨てる
    (時間などのメタは残す)。予算は 1 段を下回らず、``protect`` に渡した鍵(直後に読む段)は捨てない。
    報告のための :meth:`stats` を持つ(idea 114 段ごとの時間とメモリ)。
    """

    def __init__(self, budget_bytes=CACHE_BUDGET_BYTES):
        self._d = {}          # key -> [value, ms, nbytes]
        self._order = []      # keys, least-recently-used first (most-recently-used last)
        self._bytes = 0
        self.budget_bytes = int(budget_bytes)

    def __len__(self):
        return len(self._d)

    def __contains__(self, key):
        return key in self._d

    def nbytes(self):
        """現在保持している配列メモリの合計(bytes)。"""
        return self._bytes

    def clear(self):
        self._d.clear()
        self._order.clear()
        self._bytes = 0

    def set_budget(self, budget_bytes):
        """予算を変えて、必要なら即座に LRU で切り詰める(idea 116 利用者がキャッシュ量を調整)。"""
        self.budget_bytes = int(budget_bytes)
        self._enforce(protect=())
        return self.budget_bytes

    def get(self, key, default=None):
        """値を返し、その段を most-recently-used にする。無ければ *default*。"""
        rec = self._d.get(key)
        if rec is None:
            return default
        try:
            self._order.remove(key)
        except ValueError:
            pass
        self._order.append(key)
        return rec[0]

    def ms(self, key):
        """その段の最後の計算の所要 ms(無ければ None)。LRU 順は変えない。"""
        rec = self._d.get(key)
        return None if rec is None else rec[1]

    def put(self, key, value, ms=0.0, protect=()):
        """段の出力を入れ、予算を超えたら LRU で古い段の値を捨てる。

        *protect* に渡した鍵(と今入れた鍵)は捨てない —— 呼び手が直後に読む段を守る。"""
        if key in self._d:
            self._bytes -= self._d[key][2]
            try:
                self._order.remove(key)
            except ValueError:
                pass
        nb = array_nbytes(value)
        self._d[key] = [value, round(float(ms), 1), nb]
        self._order.append(key)
        self._bytes += nb
        self._enforce(protect=tuple(protect) + (key,))
        return value

    def _enforce(self, protect):
        protect = set(protect)
        i = 0
        while over_budget(self._bytes, self.budget_bytes, len(self._order)):
            if i >= len(self._order):
                break
            key = self._order[i]
            if key in protect:
                i += 1
                continue
            rec = self._d.pop(key)
            self._bytes -= rec[2]
            self._order.pop(i)

    def stats(self):
        """報告用: 保持段数・合計バイト・予算。"""
        return {"entries": len(self._d), "bytes": self._bytes, "budget_bytes": self.budget_bytes}
