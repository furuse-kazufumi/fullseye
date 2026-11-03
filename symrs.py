# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Reed-Solomon over GF(2^8) —— 2-D コード(QR / DataMatrix)の誤り訂正の土台(numpy 不要の純 Python)。

Reed-Solomon codec over GF(2^8) shared by the QR and DataMatrix readers of the
symbol-reading family (``symcode2d.py``). Pure Python on small integer lists:
a symbol carries at most a few hundred codewords, so tables of 256 ints are the
whole state.

なぜ自前か / why not a library: 印字品質の **未使用の誤り訂正(UEC)** は
「その読み取りで何語を直したか」を要る。既存の読み取り器(zxing-cpp など)は
復号した文字列は返すが、直した語数を返さない。訂正の内訳を数えられる復号器を
自分で持つ必要がある。
The print-quality grade "unused error correction" needs the number of codewords
that were corrected; off-the-shelf readers return the text, not that count.

2 つの流儀(体の生成多項式と生成元のべきの始まり)を引数で選ぶ:

* QR Code:    ``prim = 0x11D``(x^8+x^4+x^3+x^2+1)、根 α^0 … α^(n-1)(``fcr = 0``)
* DataMatrix: ``prim = 0x12D``(x^8+x^5+x^3+x^2+1)、根 α^1 … α^n(``fcr = 1``)

復号は Berlekamp-Massey(誤り位置多項式)→ Chien 探索(根)→ Forney(値)。
消失(位置が分かっている誤り)も受け付ける: 2·誤り + 消失 ≤ nsym まで直せる。

出典(公開文献のみ): I. S. Reed & G. Solomon, *J. SIAM* 8(2):300, 1960 /
E. R. Berlekamp, *Algebraic Coding Theory*, 1968 / J. L. Massey,
*IEEE Trans. Inf. Theory* 15(1):122, 1969 / G. D. Forney, *IEEE Trans. Inf. Theory*
11(4):549, 1965。
"""
from __future__ import annotations

__all__ = ["GF256", "QR_FIELD", "DM_FIELD", "RSDecodeError",
           "rs_generator_poly", "rs_encode", "rs_decode"]


class RSDecodeError(ValueError):
    """訂正能力を超えた(または矛盾した)符号語 / the codeword is beyond correction."""


class GF256:
    """GF(2^8) の表(指数・対数)。``prim`` は 9 bit の原始多項式、生成元は 2。

    GF(2^8) arithmetic by exp/log tables. ``prim`` must be a primitive degree-8
    polynomial (checked: the powers of 2 must visit all 255 non-zero elements).
    """

    def __init__(self, prim: int):
        if not isinstance(prim, int) or not 0x100 <= prim <= 0x1FF:
            raise ValueError("GF256: prim must be a degree-8 polynomial (0x100..0x1FF), got %r" % (prim,))
        self.prim = prim
        exp = [0] * 512
        log = [0] * 256
        x = 1
        seen = set()
        for i in range(255):
            exp[i] = x
            log[x] = i
            seen.add(x)
            x <<= 1
            if x & 0x100:
                x ^= prim
        if len(seen) != 255:
            raise ValueError("GF256: 0x%X is not primitive (2 generates only %d elements)" % (prim, len(seen)))
        for i in range(255, 512):
            exp[i] = exp[i - 255]
        self.exp = exp
        self.log = log

    def mul(self, a: int, b: int) -> int:
        """積 / product."""
        if a == 0 or b == 0:
            return 0
        return self.exp[self.log[a] + self.log[b]]

    def div(self, a: int, b: int) -> int:
        """商 / quotient (``b`` != 0)."""
        if b == 0:
            raise ZeroDivisionError("GF256: division by zero")
        if a == 0:
            return 0
        return self.exp[(self.log[a] - self.log[b]) % 255]

    def pow(self, a: int, n: int) -> int:
        """べき / power."""
        if a == 0:
            return 0 if n else 1
        return self.exp[(self.log[a] * n) % 255]

    def inv(self, a: int) -> int:
        """逆元 / inverse."""
        return self.div(1, a)

    # --- polynomials: lists, highest degree first ---------------------------------
    def poly_mul(self, p, q):
        """多項式の積(係数は高次から)/ polynomial product, highest degree first."""
        out = [0] * (len(p) + len(q) - 1)
        for i, a in enumerate(p):
            if a == 0:
                continue
            for j, b in enumerate(q):
                if b:
                    out[i + j] ^= self.mul(a, b)
        return out

    def poly_eval(self, p, x: int) -> int:
        """Horner 法で p(x) / evaluate p at x (Horner)."""
        y = 0
        for c in p:
            y = self.mul(y, x) ^ c
        return y


#: QR Code の体(x^8+x^4+x^3+x^2+1)/ the QR field.
QR_FIELD = GF256(0x11D)
#: DataMatrix ECC200 の体(x^8+x^5+x^3+x^2+1)/ the DataMatrix field.
DM_FIELD = GF256(0x12D)


def _check_ints(seq, name, op):
    out = []
    for v in seq:
        if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 255:
            raise ValueError("%s: %s must hold integers in 0..255, got %r" % (op, name, v))
        out.append(int(v))
    return out


def rs_generator_poly(gf: GF256, nsym: int, fcr: int = 0):
    """生成多項式 ∏(x − α^(fcr+i)), i = 0..nsym-1(係数は高次から、先頭 1)。

    Generator polynomial of an ``nsym``-symbol RS code (monic, highest degree first).
    """
    if isinstance(nsym, bool) or not isinstance(nsym, int) or not 1 <= nsym <= 254:
        raise ValueError("rs_generator_poly: nsym must be an integer in 1..254, got %r" % (nsym,))
    g = [1]
    for i in range(nsym):
        g = gf.poly_mul(g, [1, gf.exp[(fcr + i) % 255]])
    return g


def rs_encode(gf: GF256, data, nsym: int, fcr: int = 0):
    """データ語 ``data`` に対する ``nsym`` 個の誤り訂正語(剰余)を返す。

    Systematic RS encoding: returns the ``nsym`` check codewords (the remainder of
    ``data · x^nsym`` divided by the generator polynomial).
    """
    data = _check_ints(data, "data", "rs_encode")
    if not data:
        raise ValueError("rs_encode: data must not be empty")
    if len(data) + nsym > 255:
        raise ValueError("rs_encode: len(data) + nsym must be <= 255, got %d" % (len(data) + nsym))
    g = rs_generator_poly(gf, nsym, fcr)
    rem = list(data) + [0] * nsym
    for i in range(len(data)):
        c = rem[i]
        if c:
            for j in range(1, len(g)):
                rem[i + j] ^= gf.mul(g[j], c)
    return rem[len(data):]


def _syndromes(gf, msg, nsym, fcr):
    return [gf.poly_eval(msg, gf.exp[(fcr + i) % 255]) for i in range(nsym)]


def rs_decode(gf: GF256, codeword, nsym: int, fcr: int = 0, erase_pos=None):
    """符号語(データ + 訂正語)を訂正して ``(訂正後の符号語, 直した語数)`` を返す。

    Decode an RS codeword in place of errors and erasures. Returns
    ``(corrected, n_corrected)`` where ``corrected`` is the full codeword (data +
    check symbols) and ``n_corrected`` the number of symbols whose value changed.
    Raises :class:`RSDecodeError` (a ``ValueError``) when ``2·errors + erasures``
    exceeds ``nsym`` or the locator is inconsistent (its root count differs from
    its degree, or a root falls outside the codeword) —— never returns a silently
    wrong word that fails its own syndrome check.

    ``erase_pos`` は 0 始まりの位置(符号語の先頭から)。
    """
    op = "rs_decode"
    msg = _check_ints(codeword, "codeword", op)
    n = len(msg)
    if n == 0 or n > 255:
        raise ValueError("%s: codeword length must be 1..255, got %d" % (op, n))
    if isinstance(nsym, bool) or not isinstance(nsym, int) or not 1 <= nsym < n:
        raise ValueError("%s: nsym must be an integer in 1..len(codeword)-1, got %r" % (op, nsym))
    erase = sorted(set(int(p) for p in (erase_pos or ())))
    if any(p < 0 or p >= n for p in erase):
        raise ValueError("%s: erasure position out of range 0..%d" % (op, n - 1))
    if len(erase) > nsym:
        raise RSDecodeError("%s: %d erasures exceed the %d check symbols" % (op, len(erase), nsym))
    for p in erase:
        msg[p] = 0
    synd = _syndromes(gf, msg, nsym, fcr)
    if max(synd) == 0:
        return msg, sum(1 for a, b in zip(codeword, msg) if a != b)

    # 消失の位置多項式 / erasure locator: prod (1 - X_j x), X_j = alpha^(n-1-pos)
    # 係数は低次から(BM の流儀)/ low-degree first inside the BM block.
    def lmul(p, q):
        out = [0] * (len(p) + len(q) - 1)
        for i, a in enumerate(p):
            for j, b in enumerate(q):
                out[i + j] ^= gf.mul(a, b)
        return out

    erase_loc = [1]
    for p in erase:
        erase_loc = lmul(erase_loc, [1, gf.exp[(n - 1 - p) % 255]])

    # 修正シンドローム S(x)·Γ(x) で BM を消失の次から始める / Forney syndromes via BM init.
    sigma = list(erase_loc)
    b_poly = list(erase_loc)
    L = len(erase)
    m = 1
    bb = 1
    for k in range(len(erase), nsym):
        # discrepancy
        d = synd[k]
        for i in range(1, len(sigma)):
            if k - i >= 0:
                d ^= gf.mul(sigma[i], synd[k - i])
        if d == 0:
            m += 1
            continue
        coef = gf.div(d, bb)
        shifted = [0] * m + [gf.mul(coef, c) for c in b_poly]
        new = [0] * max(len(sigma), len(shifted))
        for i, c in enumerate(sigma):
            new[i] ^= c
        for i, c in enumerate(shifted):
            new[i] ^= c
        if 2 * L <= k + len(erase):
            b_poly = sigma
            L = k + 1 + len(erase) - L
            bb = d
            m = 1
        else:
            m += 1
        sigma = new
    while len(sigma) > 1 and sigma[-1] == 0:
        sigma.pop()
    n_err = len(sigma) - 1 - len(erase)
    if 2 * n_err + len(erase) > nsym:
        raise RSDecodeError("%s: too many errors (%d errors + %d erasures > %d check symbols)"
                            % (op, n_err, len(erase), nsym))

    # Chien: 根 X_j^{-1} を探す / find roots X_j^{-1}
    positions = []
    for pos in range(n):
        xinv = gf.exp[(255 - (n - 1 - pos)) % 255]
        y = 0
        for c in reversed(sigma):
            y = gf.mul(y, xinv) ^ c
        if y == 0:
            positions.append(pos)
    if len(positions) != len(sigma) - 1:
        raise RSDecodeError("%s: error locator of degree %d has %d roots in the codeword — uncorrectable"
                            % (op, len(sigma) - 1, len(positions)))

    # Forney: Ω(x) = S(x)Λ(x) mod x^nsym(低次から)/ evaluator polynomial
    omega = [0] * nsym
    for i in range(nsym):
        acc = 0
        for j in range(len(sigma)):
            if i - j >= 0:
                acc ^= gf.mul(sigma[j], synd[i - j])
        omega[i] = acc
    # Λ'(x): 奇数次の項だけ残る / formal derivative keeps odd terms
    for pos in positions:
        X = gf.exp[(n - 1 - pos) % 255]
        Xinv = gf.inv(X)
        num = 0
        xp = 1
        for c in omega:
            num ^= gf.mul(c, xp)
            xp = gf.mul(xp, Xinv)
        den = 0
        for j in range(1, len(sigma), 2):
            den ^= gf.mul(sigma[j], gf.pow(Xinv, j - 1))
        if den == 0:
            raise RSDecodeError("%s: zero derivative of the locator — uncorrectable" % op)
        # e = X^(1-fcr) * Ω(X^-1) / Λ'(X^-1)
        mag = gf.mul(gf.pow(X, (1 - fcr) % 255), gf.div(num, den))
        msg[pos] ^= mag
    if max(_syndromes(gf, msg, nsym, fcr)) != 0:
        raise RSDecodeError("%s: correction left a non-zero syndrome — uncorrectable" % op)
    orig = list(codeword)
    n_changed = sum(1 for a, b in zip(orig, msg) if a != b)
    return msg, n_changed
