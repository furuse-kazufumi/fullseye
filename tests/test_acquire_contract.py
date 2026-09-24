# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""acquire の入口契約の門 —— 実機ゼロで確かめられるところを全部確かめる。

★2026-09-24 にこの層で 2 件の欠陥を実測した:

1. **申告と実装の食い違い**: ``capabilities()`` は 9 系統を申告するのに
   ``Camera._open`` の分岐は 5 系統しか無く、``realsense`` / ``oak`` / ``zed`` /
   ``kinect`` は SDK を入れても ``ValueError: unknown backend`` だった。
   登録面だけ数える門はこれに構造的に盲目なので、**表から実装を引く**門を置く。
2. **ビット深度をコンテナから推測していた**: Mono12 を uint16 で受けると
   65535 で割られ **16 倍暗く**なる(実測 4095 → 0.0625)。例外は出ないので、
   下流のしきい値 op が全部静かに外れる。

どちらも「走った」では見つからない型なので、**数で**押さえる。
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import acquire  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. 申告と実装                                                                 #
# --------------------------------------------------------------------------- #
def test_every_declared_backend_has_an_opener():
    """★表に載っている backend は全部、開く実装を持っていること。

    これが今回いちばん効く門 —— 表に行を足すのは 1 行、開く実装を書くのは 30 行で、
    足しただけの行は ``capabilities()`` から「対応しています」と申告してしまう。
    """
    missing = [row[0] for row in acquire._BACKENDS if not hasattr(acquire.Camera, row[5])]
    assert missing == [], (
        "_BACKENDS に在るのに Camera に opener が無い backend: %s —— "
        "capabilities() は「対応」と申告するが、SDK を入れても ValueError になる" % missing)


def test_opener_names_are_unique_and_private():
    names = [row[5] for row in acquire._BACKENDS]
    assert len(set(names)) == len(names), "opener 名が重複している: %s" % names
    assert all(n.startswith("_open_") for n in names), names


def test_coverage_reports_no_gap():
    cov = acquire.coverage()
    assert cov["missing"] == [], cov
    assert cov["implemented"] == cov["declared"] >= 10, cov


def test_capabilities_rows_are_complete():
    keys = {"name", "kind", "available", "implemented", "unit", "pip", "desc"}
    caps = acquire.capabilities()
    assert caps, "backend が 1 つも無い"
    for c in caps:
        assert set(c) == keys, (c["name"], sorted(c))
        assert c["kind"] in ("native", "optional"), c
        assert c["unit"] in ("normalised", "m"), c
        assert c["kind"] == "optional" or c["available"], "native なのに使えない: %s" % c["name"]


def test_unknown_backend_names_the_known_ones():
    with pytest.raises(ValueError) as e:
        acquire.Camera(lambda: np.zeros((4, 4)), backend="nosuchsdk")
    msg = str(e.value)
    assert "nosuchsdk" in msg and "callable" in msg, msg


def test_the_gate_actually_catches_a_missing_opener(monkeypatch):
    """★門を壊して確かめる —— 表に行だけ足しても通ってしまうなら門ではない。"""
    broken = list(acquire._BACKENDS) + [
        ("ghost", None, None, "optional", "normalised", "_open_ghost", "実装の無い行")]
    monkeypatch.setattr(acquire, "_BACKENDS", broken)
    missing = [row[0] for row in acquire._BACKENDS if not hasattr(acquire.Camera, row[5])]
    assert missing == ["ghost"], "壊しても検出できないなら、この門は何も守っていない"


# --------------------------------------------------------------------------- #
# 2. ビット深度(コンテナから推測しない)                                          #
# --------------------------------------------------------------------------- #
def _ramp12():
    """12 bit のフルスケール(0..4095)を uint16 の器に入れたもの。"""
    return (np.linspace(0, 4095, 16).round().astype(np.uint16)).reshape(4, 4)


def test_twelve_bit_in_a_sixteen_bit_container_is_not_sixteen_times_dark():
    raw = _ramp12()
    told = acquire.Camera(lambda: raw, backend="callable", pixel_format="Mono12").grab()
    assert told.max() == pytest.approx(1.0, abs=1e-12), (
        "Mono12 と告げているのにフルスケールが 1.0 にならない: %.6f" % told.max())
    not_told = acquire.Camera(lambda: raw, backend="callable").grab()
    assert not_told.max() == pytest.approx(4095.0 / 65535.0, rel=1e-9), not_told.max()
    #: 告げるか告げないかの差は、閉形式で **(2^16-1)/(2^12-1) = 65535/4095 =
    #: 16.003663...**。★「16 倍」と書いて落ちた —— 器の幅と有効ビットの比は
    #: 2^4 ではなく (2^16-1)/(2^12-1) で、1 桁目から違う。
    ratio = (2 ** 16 - 1) / (2 ** 12 - 1)
    assert ratio == pytest.approx(16.003663003663004, rel=1e-15)
    assert told.max() / not_told.max() == pytest.approx(ratio, rel=1e-12)


@pytest.mark.parametrize("fmt,bits", sorted(acquire.PIXEL_BITS.items()))
def test_every_pixel_format_maps_to_its_bits(fmt, bits):
    assert acquire.bit_depth_of(fmt) == bits
    assert 8 <= bits <= 16


def test_unknown_pixel_format_is_refused_not_guessed():
    with pytest.raises(ValueError) as e:
        acquire.Camera(lambda: _ramp12(), backend="callable", pixel_format="Mono13")
    assert "Mono13" in str(e.value) and "bit_depth" in str(e.value)
    assert acquire.bit_depth_of("Mono13") is None
    assert acquire.bit_depth_of(None) is None


def test_full_scale_is_exactly_one_for_every_depth():
    """告げられた深度どおりに割れば、フルスケールは**厳密に** 1 になる。"""
    for fmt, bits in sorted(acquire.PIXEL_BITS.items()):
        full = (1 << bits) - 1
        raw = np.full((2, 2), full, dtype=np.uint16)
        got = acquire.Camera(lambda r=raw: r, backend="callable",
                             pixel_format=fmt, bit_depth=bits).grab()
        assert got.max() == 1.0, (fmt, bits, got.max())


# --------------------------------------------------------------------------- #
# 3. 深度は物理量(正規化しない)                                                 #
# --------------------------------------------------------------------------- #
def test_depth_backends_are_declared_in_metres():
    caps = {c["name"]: c for c in acquire.capabilities()}
    assert set(acquire.DEPTH_BACKENDS) == {n for n, c in caps.items() if c["unit"] == "m"}
    assert {"realsense", "oak", "zed", "kinect"} <= set(acquire.DEPTH_BACKENDS)


def test_a_depth_frame_keeps_its_metres():
    """★[0,1] に正規化したら測距値が壊れる。`depth` を受ける台帳 op は 35 本ある。"""
    far = np.array([[0.5, 1.25], [3.0, 12.0]])
    cam = acquire.Camera(lambda: far, backend="callable", unit="m")
    f = cam.grab_frame()
    assert f.unit == "m"
    assert np.allclose(f.data, far), "深度が書き換えられている"
    assert f.data.max() == 12.0


def test_callable_unit_is_validated():
    with pytest.raises(ValueError):
        acquire.Camera(lambda: np.zeros((2, 2)), backend="callable", unit="mm")


# --------------------------------------------------------------------------- #
# 4. Frame が運ぶもの                                                           #
# --------------------------------------------------------------------------- #
def test_frame_carries_the_device_facts_and_acts_like_an_array():
    raw = _ramp12()
    cam = acquire.Camera(lambda: raw, backend="callable", pixel_format="Mono12")
    f = cam.grab_frame()
    assert isinstance(f, acquire.Frame)
    assert f.pixel_format == "Mono12" and f.bit_depth == 12
    assert f.backend == "callable" and f.unit == "normalised"
    assert f.shape == (4, 4)
    assert np.asarray(f).shape == (4, 4)
    assert np.asarray(f, dtype=np.float32).dtype == np.float32
    assert "Mono12" in repr(f)


def test_frame_ids_advance_so_a_drop_can_be_seen():
    cam = acquire.Camera(lambda: np.zeros((2, 2)), backend="callable")
    ids = [cam.grab_frame().frame_id for _ in range(4)]
    assert ids == [0, 1, 2, 3], ids


def test_timestamp_source_is_never_invented():
    """時刻を持たない backend が「device の時刻」を名乗らないこと。"""
    f = acquire.Camera(lambda: np.zeros((2, 2)), backend="callable").grab_frame()
    assert f.timestamp_source == "host"
    assert f.timestamp_s is None, "持っていない時刻を捏造している"


def test_grab_still_returns_a_bare_array():
    """既存の呼び出し側を壊していないこと。"""
    out = acquire.Camera(lambda: np.zeros((3, 3)), backend="callable").grab()
    assert isinstance(out, np.ndarray) and out.shape == (3, 3)


# --------------------------------------------------------------------------- #
# 5. 列挙                                                                       #
# --------------------------------------------------------------------------- #
def test_list_devices_never_raises_and_reports_failures():
    out = acquire.list_devices()
    assert isinstance(out, list)
    for e in out:
        assert {"backend", "id", "label"} <= set(e), e


def test_list_devices_skips_backends_whose_sdk_is_absent():
    absent = [c["name"] for c in acquire.capabilities() if not c["available"]]
    if not absent:
        pytest.skip("この環境では全 SDK が入っている")
    got = acquire.list_devices(backends=absent)
    assert got == [], "SDK が無い backend を列挙しようとしている: %s" % got


def test_enumeration_failure_is_reported_not_dropped(monkeypatch):
    """★「見つからない」と「見に行けない」を同じ顔にしない。"""
    def boom(_b):
        raise RuntimeError("permission denied")
    monkeypatch.setattr(acquire, "_enumerate", boom)
    out = acquire.list_devices(backends=["callable"])
    assert len(out) == 1 and "error" in out[0], out
    assert "permission denied" in out[0]["error"]


# --------------------------------------------------------------------------- #
# 6. 文書がずれないこと                                                          #
# --------------------------------------------------------------------------- #
def test_the_connectivity_doc_lists_exactly_the_implemented_backends():
    """★`docs/CONNECTIVITY.md` の acquire の表には門が無く、黙ってずれていた。

    2026-09-24 の実測: 表は 9 件のままで、しかも 4 件は「対応」と書いてあるのに
    開けなかった。**表は主張**なので、主張と実装を突き合わせる門を置く
    (件数・名前・単位・pip の 4 つ)。
    """
    doc = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "docs", "CONNECTIVITY.md")
    text = open(doc, encoding="utf-8").read()
    head = "## 画像取り込み (acquire)"
    assert head in text, "CONNECTIVITY.md に acquire の節が無い"
    section = text[text.index(head):]
    #: ★「次は ## デバイス制御」と決め打ちしていたため、あいだに節を 1 つ足した
    #:   だけでその表の行まで backend 行として読んでしまった(2026-09-24)。
    #:   節の終わりは**次の見出し**であって、特定の見出しの名前ではない。
    nxt = section.find(chr(10) + "## ", 1)
    section = section[:nxt] if nxt != -1 else section
    caps = acquire.capabilities()
    assert "(%d)" % len(caps) in section.splitlines()[0], (
        "見出しの件数が %d と食い違う: %r" % (len(caps), section.splitlines()[0]))
    rows = [ln for ln in section.splitlines() if ln.startswith("| ") and "|---" not in ln]
    rows = [r for r in rows if not r.startswith("| source")]
    listed = {}
    for r in rows:
        cells = [c.strip() for c in r.strip("|").split("|")]
        listed[cells[0]] = cells
    assert set(listed) == {c["name"] for c in caps}, (
        "表と実装で backend の名前が食い違う(表のみ %s / 実装のみ %s)"
        % (sorted(set(listed) - {c["name"] for c in caps}),
           sorted({c["name"] for c in caps} - set(listed))))
    for c in caps:
        cells = listed[c["name"]]
        assert cells[1] == c["kind"], (c["name"], cells[1], c["kind"])
        assert cells[2] == c["unit"], (c["name"], cells[2], c["unit"])
        assert cells[3] == ("✓" if c["implemented"] else "—"), (c["name"], cells[3])
        assert cells[5] == (c["pip"] or "—"), (c["name"], cells[5], c["pip"])


# --------------------------------------------------------------------------- packed
#
# 詰め形式(packed)は **例外を出さずにそれらしく間違う** 型の代表。`Mono12p` の
# バッファを 4095 で割ると、画像に見えるが画像ではないものが出る。並びは EMVA の
# PFNC 2.4 が決めていて無償で読めるので、**規約の図の値そのもの**を門にできる。
# 合成データの往復だけでは自分の思い込みを検査できない(往復は自分の実装同士の
# 一致しか見ない)ので、公表された図の値と往復の両方を置く。


def _pack_lsb(vals, bits):
    """検査用に詰め直す(PFNC 2.4 6.3.1)。"""
    v = np.asarray(vals, dtype=np.uint32)
    b = ((v[:, None] >> np.arange(bits)) & 1).astype(np.uint8).ravel()
    pad = (-b.size) % 8
    if pad:
        b = np.concatenate([b, np.zeros(pad, np.uint8)])
    return np.packbits(b, bitorder="little")


def test_the_published_figure_for_lsb_grouped_decodes_to_its_own_values():
    """PFNC 2.4 図 6-13: byte0=L1[11:4] / byte1=L2[3:0]<<4|L1[3:0] / byte2=L2[11:4]。"""
    raw = np.array([0xAB, (0x3 << 4) | 0xC, 0x12], np.uint8)
    got = acquire.unpack(raw, "Mono12Packed", (1, 2))
    assert list(got.ravel()) == [0xABC, 0x123]


def test_ten_bit_lsb_packed_is_four_pixels_in_five_bytes():
    """PFNC 2.4 図 6-9。詰め方が違えば必要なバイト数が変わる —— 数で押さえる。"""
    buf = _pack_lsb([0x3FF, 0x000, 0x155, 0x2AA], 10)
    assert buf.size == 5
    assert list(acquire.unpack(buf, "Mono10p", (2, 2)).ravel()) == [0x3FF, 0, 0x155, 0x2AA]


@pytest.mark.parametrize("fmt", sorted(acquire.PACKED_FORMATS))
def test_every_packed_format_survives_a_round_trip(fmt):
    bits, layout = acquire.PACKED_FORMATS[fmt]
    rng = np.random.default_rng(abs(hash(fmt)) % (2 ** 32))
    n = 32 * 16
    vals = rng.integers(0, 1 << bits, n).astype(np.uint32)
    if layout == "p":
        buf = _pack_lsb(vals, bits)
    else:
        low = bits - 8
        p0, p1 = vals[0::2], vals[1::2]
        buf = np.empty((p0.size, 3), np.uint8)
        buf[:, 0] = (p0 >> low) & 0xFF
        buf[:, 1] = ((p1 & ((1 << low) - 1)) << 4) | (p0 & ((1 << low) - 1))
        buf[:, 2] = (p1 >> low) & 0xFF
        buf = buf.ravel()
    got = acquire.unpack(buf, fmt, (32, 16))
    assert got.shape == (32, 16)
    assert np.array_equal(got.ravel(), vals)


def test_a_short_buffer_is_refused_not_padded():
    """落ちたパケットを 0 で埋めて画像にしない。"""
    for fmt in ("Mono12p", "Mono12Packed"):
        with pytest.raises(ValueError) as e:
            acquire.unpack(np.zeros(4, np.uint8), fmt, (8, 8))
        assert str(e.value).startswith(("unpack_lsb:", "unpack_grouped:"))


def test_an_unknown_format_is_refused_by_name():
    with pytest.raises(ValueError) as e:
        acquire.unpack(np.zeros(64, np.uint8), "Mono12", (4, 4))
    assert str(e.value).startswith("unpack:")


def test_coerce_refuses_a_packed_buffer_instead_of_scaling_it():
    """★この門が無いと、間違った画像が「動いた」に見える。"""
    with pytest.raises(ValueError) as e:
        acquire._coerce(np.zeros((8, 8), np.uint8), True, 12, "Mono12p")
    assert "packed" in str(e.value)
    #: 展開済み(uint16)なら通す —— 門が正しい相手だけを止めているか。
    out = acquire._coerce(np.full((8, 8), 4095, np.uint16), True, 12, "Mono12p")
    assert out.max() == pytest.approx(1.0)


def test_every_packed_format_is_also_in_the_bit_depth_table():
    """綴りが 2 つの表に割れると、片方だけ増えて静かにずれる。"""
    missing = [f for f in acquire.PACKED_FORMATS if f not in acquire.PIXEL_BITS]
    assert not missing, missing
    wrong = [(f, acquire.PIXEL_BITS[f], b)
             for f, (b, _l) in acquire.PACKED_FORMATS.items()
             if acquire.PIXEL_BITS[f] != b]
    assert not wrong, wrong


def test_gain_does_not_claim_a_unit_the_standard_does_not_give_it():
    """SFNC v2.8 は Gain に単位を割り当てていない(dB は 1.2 の一覧に在るだけ)。

    だから値と単位を別々に運ぶ。``gain_db`` という名前は標準より強い主張だった。
    """
    f = acquire.Frame(np.zeros((2, 2)), gain=3.5, gain_unit="dB")
    assert f.gain == 3.5 and f.gain_unit == "dB"
    assert not hasattr(f, "gain_db")
    assert acquire.Frame(np.zeros((2, 2))).gain is None


# --------------------------------------------------------------------------- 規格の全数
#
# ★ここまでの門は「acquire が持っている綴り」からしか数えていない。**規格の全数**を
# 分母に置くと、そもそも知らない形式が見つかる —— 実際これで 10 bit 非詰めの Bayer
# 4 形式が丸ごと抜けていた(2026-09-24)。台帳は EMVA が無償公開している
# 「GenICam Pixel Format Names and Values」の単板 59 形式。


def _pfnc():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "examples", "data", "pfnc_single_plane.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def test_the_spec_ledger_is_the_published_one_not_a_copy_that_drifted():
    doc = _pfnc()
    assert doc["source"].startswith("https://www.emva.org/")
    assert len(doc["formats"]) == 59
    #: 32-bit 値の第 2 バイトが格納ビット数 —— 台帳が壊れたらここで気づく。
    for name, row in doc["formats"].items():
        assert ((int(row["value"], 16) >> 16) & 0xFF) == row["storage_bits"], name


@pytest.mark.parametrize("name", sorted(_pfnc()["formats"]))
def test_every_published_single_plane_format_is_accounted_for(name):
    """対応するか、**理由をつけて外す**か。黙って知らないままにはしない。"""
    assert name in acquire.PIXEL_BITS or name in acquire.NOT_CARRIED, (
        "%s は規格にあるのに PIXEL_BITS にも NOT_CARRIED にも無い" % name)


@pytest.mark.parametrize("name", sorted(_pfnc()["formats"]))
def test_carried_formats_agree_with_the_published_bit_counts(name):
    row = _pfnc()["formats"][name]
    if name not in acquire.PIXEL_BITS:
        return
    assert acquire.PIXEL_BITS[name] == row["bits"], (name, row["desc"])


def test_a_format_is_never_both_carried_and_deliberately_left_out():
    both = sorted(set(acquire.PIXEL_BITS) & set(acquire.NOT_CARRIED))
    assert not both, both


def test_the_container_is_wider_than_the_samples_for_exactly_the_known_formats():
    """容器 > 有効 の形式だけが「16.0037 倍暗い」欠陥を起こしうる。全数で押さえる。"""
    doc = _pfnc()["formats"]
    risky = sorted(n for n, r in doc.items()
                   if n in acquire.PIXEL_BITS and r["storage_bits"] > r["bits"])
    #: ★最初ここに「詰め形式は容器 = 有効」と書いて、この門に捕まった。実際は
    #:   2 通りある: (a) 10/12/14 bit の**非詰め**が 16 bit 容器に入る場合と、
    #:   (b) **grouped**(GigE Vision 1.x の `Packed`)の 10 bit が 12 bit に
    #:   入る場合 —— 2 画素 = 3 バイトなので 1 画素あたり 12 bit になる。
    #:   真の lsb packed(`p`)だけが容器 = 有効。
    assert risky, "1 つも無いなら台帳か表が壊れている"
    for n in risky:
        assert not n.endswith("p") or n.endswith("Packed"), n
        assert acquire.PIXEL_BITS[n] in (10, 12, 14), n
    #: 逆向き: 真の lsb packed は 1 つも risky に入らない
    lsb = [n for n, (_b, layout) in acquire.PACKED_FORMATS.items() if layout == "p"]
    assert not (set(lsb) & set(risky)), sorted(set(lsb) & set(risky))


def test_the_connectivity_doc_pixel_format_table_matches_the_code():
    """表の数字は手で書いてある。**書いた瞬間から腐る**ので門で留める。"""
    doc = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "docs", "CONNECTIVITY.md")
    text = open(doc, encoding="utf-8").read()
    led = _pfnc()["formats"]
    assert "## 画素形式 (単板 %d 形式)" % len(led) in text
    for label, pre in (("Mono", "Mono"), ("Bayer", "Bayer")):
        names = [n for n in led if n.startswith(pre)]
        have = sum(1 for n in names if n in acquire.PIXEL_BITS)
        skip = sum(1 for n in names if n in acquire.NOT_CARRIED)
        row = "| %s | %d | %d | %d |" % (label, len(names), have, skip)
        assert row in text, row
    assert "%d 形式)は `acquire.unpack()`" % len(acquire.PACKED_FORMATS) in text
