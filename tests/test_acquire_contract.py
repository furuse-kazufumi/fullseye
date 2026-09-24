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


# --------------------------------------------------------------------------- SFNC
#
# ★機能名はベンダの名前ではなく規格の名前なので、**1 本の語彙表で GenTL を出す
# 全ベンダを覆える**。だからこの層は「どのベンダの SDK を入れたか」と無関係に
# 検査できる —— 模擬ノードマップで足りる。実機が無いことは言い訳にならない。


class _FakeNode:
    """GenICam のノード 1 つ。値を持ち、clamp する(実機はする)。"""

    def __init__(self, value, lo=None, hi=None, executable=False):
        self.value = value
        self._lo, self._hi, self._exec = lo, hi, executable
        self.executed = 0

    def __setattr__(self, k, v):
        if k == "value" and getattr(self, "_lo", None) is not None:
            v = min(max(v, self._lo), self._hi)
        object.__setattr__(self, k, v)

    def execute(self):
        if not self._exec:
            raise AttributeError("not a command")
        self.executed += 1


class _FakeMap:
    """ノードを属性で見せるだけの模擬。harvesters の node_map と同じ触り方。"""

    def __init__(self, **nodes):
        for k, v in nodes.items():
            setattr(self, k, v)


def _fake_camera(**nodes):
    nm = _FakeMap(**nodes)
    return acquire.Camera(lambda: np.zeros((4, 4), dtype=np.uint8),
                          backend="callable", node_map=nm), nm


def test_the_shipped_vocabulary_is_the_published_one():
    """表は手で書いてある。**規格から取った台帳**と突き合わせて留める。"""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "examples", "data", "sfnc_acquire_vocabulary.json")
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    assert doc["source"].startswith("https://www.emva.org/")
    led = doc["features"]
    assert set(acquire.SFNC_FEATURES) <= set(led), (
        sorted(set(acquire.SFNC_FEATURES) - set(led)))
    for name, (level, iface, unit) in sorted(acquire.SFNC_FEATURES.items()):
        row = led[name]
        assert row["level"] == level, (name, row["level"], level)
        assert row["interface"] == iface, (name, row["interface"], iface)
        assert row["unit"] == unit, (name, row["unit"], unit)


def test_the_standard_units_are_not_invented():
    """★SFNC 1.2 が単位を決めている機能だけが単位を持つ。Gain は持たない。"""
    assert acquire.SFNC_FEATURES["ExposureTime"][2] == "us"
    assert acquire.SFNC_FEATURES["AcquisitionFrameRate"][2] == "Hz"
    assert acquire.SFNC_FEATURES["PayloadSize"][2] == "B"
    assert acquire.SFNC_FEATURES["TimestampLatchValue"][2] == "ns"
    #: 規格は Gain に単位を割り当てていない —— dB と呼ばない。
    assert acquire.SFNC_FEATURES["Gain"][2] is None


def test_a_source_without_a_node_map_says_so_instead_of_raising_deeper():
    cam = acquire.Camera(lambda: np.zeros((4, 4), dtype=np.uint8), backend="callable")
    assert cam.node_map() is None
    with pytest.raises(RuntimeError) as e:
        cam.features()
    assert "node map" in str(e.value)


def test_features_are_read_by_their_standard_names():
    cam, _nm = _fake_camera(ExposureTime=_FakeNode(5000.0),
                            PixelFormat=_FakeNode("Mono12"),
                            Width=_FakeNode(1920), Height=_FakeNode(1080))
    got = cam.features(("ExposureTime", "PixelFormat", "Width"))
    assert got == {"ExposureTime": 5000.0, "PixelFormat": "Mono12", "Width": 1920}


def test_configure_reports_what_the_device_took_not_what_was_asked():
    """★カメラは clamp する。要求値を返すのは小さな嘘で、露光の取り違えになる。"""
    cam, _nm = _fake_camera(ExposureTime=_FakeNode(1000.0, lo=10.0, hi=33000.0))
    got = cam.configure(ExposureTime=100000.0)
    assert got["ExposureTime"] == 33000.0          # 要求は 100000 us
    assert got["ExposureTime"] != 100000.0


def test_a_vendor_name_is_refused_by_the_standard_table():
    cam, _nm = _fake_camera(ExposureTimeAbs=_FakeNode(5000.0))
    for call in (lambda: cam.configure(ExposureTimeAbs=1.0),
                 lambda: cam.features(("ExposureTimeAbs",))):
        with pytest.raises(ValueError) as e:
            call()
        assert "SFNC" in str(e.value)


def test_writing_a_feature_the_device_lacks_is_refused_here_not_deeper():
    cam, _nm = _fake_camera(ExposureTime=_FakeNode(5000.0))
    with pytest.raises(ValueError) as e:
        cam.configure(Gain=3.0)
    assert "does not expose" in str(e.value)


def test_a_missing_required_feature_is_reported_and_an_optional_one_is_not():
    """★規格が必須と言う機能の不在は**装置についての発見**。黙って飛ばさない。"""
    cam, _nm = _fake_camera(ExposureTime=_FakeNode(5000.0))
    got = cam.features(("ExposureTime", "Width", "Gain"))
    assert got["ExposureTime"] == 5000.0
    assert got["Width"] is None                    # 必須なのに無い -> 見える
    assert "Gain" not in got                       # 任意で無い -> 黙っていてよい


def test_missing_required_features_lists_the_gap():
    cam, _nm = _fake_camera(ExposureTime=_FakeNode(5000.0), Width=_FakeNode(64),
                            Height=_FakeNode(64))
    gap = cam.missing_required_features()
    assert "PixelFormat" in gap and "TriggerMode" in gap
    assert "ExposureTime" not in gap and "Width" not in gap
    #: 任意の機能は不足に数えない
    assert "Gain" not in gap and "ExposureAuto" not in gap


def test_commands_are_executed_not_assigned():
    cam, nm = _fake_camera(AcquisitionStart=_FakeNode(None, executable=True))
    cam.node_map().execute("AcquisitionStart")
    assert nm.AcquisitionStart.executed == 1


def test_a_command_has_no_value_so_reading_all_features_skips_it():
    cam, _nm = _fake_camera(AcquisitionStart=_FakeNode(None, executable=True),
                            ExposureTime=_FakeNode(1.0))
    got = cam.features()
    assert "AcquisitionStart" not in got
    assert got["ExposureTime"] == 1.0


def test_every_required_feature_in_the_table_is_marked_required():
    assert set(acquire.SFNC_REQUIRED) == {
        n for n, (lvl, _i, _u) in acquire.SFNC_FEATURES.items() if lvl == "R"}
    assert "ExposureTime" in acquire.SFNC_REQUIRED
    assert "Gain" not in acquire.SFNC_REQUIRED


def test_the_connectivity_doc_sfnc_section_matches_the_code():
    doc = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "docs", "CONNECTIVITY.md")
    text = open(doc, encoding="utf-8").read()
    n = len(acquire.SFNC_FEATURES)
    req = len(acquire.SFNC_REQUIRED)
    assert "## カメラの機能名 (SFNC %d 機能)" % n in text
    assert "| 規格が**必須**と決めている機能 | %d |" % req in text
    assert "| 任意の機能 | %d |" % (n - req) in text
    #: 例に書いた呼び方が実在すること(説明のコード例は門が無いと静かに腐る)
    for name in ("configure", "missing_required_features"):
        assert "cam.%s(" % name in text
        assert callable(getattr(acquire.Camera, name))


# --------------------------------------------------------------------------- バッファ
#
# ★SDK のバッファを指したまま返すと、**次の 1 枚が前の 1 枚を書き換える**。
# 例外は出ない —— 絵だけが入れ替わるので、連写を保存して初めて気づく。
# 実機が要る経路なので実行では確かめられない。**ソースで確かめる**。


def _raw_grab_returns() -> dict:
    """``_raw_grab`` の backend ごとに「何を返しているか」を式のまま集める。

    枝は ``if b == "<name>":`` で分かれているので、その名前を鍵にする。
    """
    import ast as _ast
    import inspect
    import textwrap

    #: メソッドのソースは字下げされているので、そのままでは parse できない。
    src = textwrap.dedent(inspect.getsource(acquire.Camera._raw_grab))
    fn = _ast.parse(src).body[0]
    out = {}
    for node in _ast.walk(fn):
        if not isinstance(node, _ast.If):
            continue
        t = node.test
        if not (isinstance(t, _ast.Compare) and isinstance(t.comparators[0], _ast.Constant)):
            continue
        name = t.comparators[0].value
        if not isinstance(name, str):
            continue
        for n in _ast.walk(node):
            if isinstance(n, _ast.Return) and isinstance(n.value, _ast.Tuple) and n.value.elts:
                expr = _ast.unparse(n.value.elts[0])
                if expr != "None":
                    out.setdefault(name, []).append(expr)
    return out


#: 複製を作る呼び方。これのどれかで包まれていなければ、SDK のメモリを指したまま。
_COPIERS = ("np.array(", ".astype(", ".copy()")

#: ★複製が要らない backend と、その**理由**。黙って外さない。
_NO_COPY_NEEDED = {
    "callable": "利用者の関数が作った配列。こちらが所有するバッファではない",
    "dir": "画像を 1 枚ずつ読むので毎回新しい配列になる",
    "opencv": "VideoCapture.read() / imread() は呼ぶたびに確保する",
}


def test_every_sdk_backend_copies_out_of_its_buffer():
    """★バッファを使い回す SDK から、指したままの配列を返していないか。

    2026-09-25 の実測: ``vimba`` の ``as_numpy_ndarray()`` は**フレームのバッファを
    そのまま指す**(vmbpy 同梱の例が「同じメモリを使う」と書いている)。vmbpy の
    取得はフレームを再キューしてバッファを使い回すので、複製しないと**次の 1 枚が
    前の 1 枚を書き換える** —— 例外は出ず、絵だけが入れ替わる。

    実機が要る経路なので実行では確かめられない。**ソースで確かめる**。
    """
    got = _raw_grab_returns()
    assert len(got) >= 8, ("backend の枝が %d 本しか読めていない —— 門が空になっている"
                           % len(got))
    #: 申告した backend が全部読めているか(表と実装のずれもここで出る)
    declared = {c["name"] for c in acquire.capabilities()}
    missing = sorted(declared - set(got) - set(_NO_COPY_NEEDED))
    assert not missing, "枝が見つからない backend: %s" % missing
    bad = []
    for name, exprs in sorted(got.items()):
        if name in _NO_COPY_NEEDED:
            continue
        for e in exprs:
            if not any(c in e for c in _COPIERS):
                bad.append("%s: %s" % (name, e))
    assert not bad, (
        ("SDK のバッファを複製せずに返している枝がある: %s" + chr(10) +
         "次の 1 枚が前の 1 枚を書き換える(例外は出ない)。np.array(...) で包むこと。")
        % bad)


def test_the_exemptions_are_named_and_still_exist():
    """免除は**理由つきで名指し**。実在しない backend の免除は嘘になる。"""
    names = {c["name"] for c in acquire.capabilities()}
    stale = sorted(set(_NO_COPY_NEEDED) - names)
    assert not stale, "実在しない backend の免除: %s" % stale
    for n, why in _NO_COPY_NEEDED.items():
        assert len(why) > 10, n


def test_the_copy_gate_actually_catches_a_view():
    """★門は壊して確かめる。複製しない式を混ぜたら落ちること。"""
    bad = [r for r in ["frame.as_numpy_ndarray()"]
           if not any(c in r for c in _COPIERS)]
    assert bad, "複製していない式を _COPIERS が通してしまう"


# --------------------------------------------------------------------------- 8 軸
#
# ★SDK を採点したのと**同じ物差し**で自分も採点する。違う物差しで測った数を
# 並べると「SDK より厚い」が意味を失う。しかも自己申告にしない —— 各軸が
# どの入口で満たされているかを**実在する名前**で名指しし、門がそれを引く。


def test_every_coverage_axis_names_something_that_exists():
    got = acquire.axes()
    assert len(got) == 8, got
    missing = {a: v["entry"] for a, v in got.items() if not v["present"]}
    assert not missing, (
        ("軸が名指しした入口が見つからない: %s" + chr(10) +
         "改名か削除。主張のほうを直すこと —— 消えた証拠つきの「対応済み」は嘘になる。")
        % missing)


def test_the_axes_are_the_same_eight_the_sdks_were_scored_on():
    """物差しが勝手に増えたり減ったりしていないこと。"""
    assert set(acquire.COVERAGE_AXES) == {
        "enumeration", "acquisition_mode", "buffer", "pixel_format",
        "bit_depth", "metadata", "physical_unit", "teardown"}


def test_the_axis_gate_catches_a_renamed_entry_point():
    """★門は壊して確かめる。存在しない名前を混ぜたら落ちること。"""
    saved = dict(acquire.COVERAGE_AXES)
    try:
        acquire.COVERAGE_AXES["teardown"] = ("Camera.close", "Camera.shutdown_all")
        bad = {a: v for a, v in acquire.axes().items() if not v["present"]}
        assert "teardown" in bad, "存在しない入口を門が通した"
    finally:
        acquire.COVERAGE_AXES.clear()
        acquire.COVERAGE_AXES.update(saved)


def test_the_connectivity_doc_axis_table_matches_the_code():
    doc = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "docs", "CONNECTIVITY.md")
    text = open(doc, encoding="utf-8").read()
    got = acquire.axes()
    n = sum(1 for v in got.values() if v["present"])
    assert "## 取り込み層の 8 軸 (%d/%d)" % (n, len(got)) in text
    #: 入口の名前も本文に出ていること(名前が消えたら表も落ちる)
    for v in got.values():
        for entry in v["entry"]:
            assert "`%s`" % entry in text, entry


# --------------------------------------------------------------------------- GenTL
#
# ★列挙軸の一番大きな穴はここだった。`_enumerate("genicam")` は [] を返していて、
# **GenTL を出す全ベンダを覆える唯一の経路だけが列挙できない**状態だった。
# GenTL 1.6 が「プロデューサのインストーラは GENICAM_GENTL{32/64}_PATH に自分を
# 足す」と決めているので、こちらはその変数を読めばよく、ベンダごとの表は要らない。
# 実機も SDK も無しで検査できる —— 変数と `.cti` という名前のファイルがあればよい。


def test_gentl_producers_are_found_through_the_standard_variable(tmp_path):
    d = tmp_path / "producers"
    d.mkdir()
    (d / "TLSimu.cti").write_bytes(b"x")
    (d / "vendor.cti").write_bytes(b"x")
    (d / "readme.txt").write_bytes(b"x")          # .cti でないものは拾わない
    got = acquire.gentl_producers({"GENICAM_GENTL64_PATH": str(d)})
    assert [os.path.basename(g) for g in got] == ["TLSimu.cti", "vendor.cti"]


def test_several_directories_are_read_in_the_order_the_variable_lists_them(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "first.cti").write_bytes(b"x")
    (b / "second.cti").write_bytes(b"x")
    env = {"GENICAM_GENTL64_PATH": os.pathsep.join([str(a), str(b)])}
    got = [os.path.basename(g) for g in acquire.gentl_producers(env)]
    assert got == ["first.cti", "second.cti"]


def test_a_producer_listed_twice_is_returned_once(tmp_path):
    d = tmp_path / "p"
    d.mkdir()
    (d / "one.cti").write_bytes(b"x")
    env = {"GENICAM_GENTL64_PATH": os.pathsep.join([str(d), str(d)]),
           "GENICAM_GENTL32_PATH": str(d)}
    assert len(acquire.gentl_producers(env)) == 1


def test_a_missing_directory_is_skipped_not_raised(tmp_path):
    """装置が無いことと、道具が壊れていることを取り違えない。"""
    env = {"GENICAM_GENTL64_PATH": os.pathsep.join([str(tmp_path / "nope"), ""])}
    assert acquire.gentl_producers(env) == []


def test_no_producer_installed_is_an_empty_list_not_an_error():
    assert acquire.gentl_producers({}) == []


def test_the_variable_names_are_the_ones_the_standard_defines():
    """★綴りは GenTL 1.6 が決めている。推測で似た名前を書かない。"""
    assert acquire.GENTL_PATH_VARS == ("GENICAM_GENTL64_PATH", "GENICAM_GENTL32_PATH")
