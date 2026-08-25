"""H2b — じゃんけん。遅延の効果が **二値** で出る最良のベンチ。

正本 = ``docs/HIGHSPEED_VISION.md`` §4 H2b。

## なぜこの課題か

- 成否が二値(勝ち / あいこ / 負け)。指標の設計も閾値の調整も要らない
- 成否を決めているのが **遅延だけ**。人の手が形になるまでの時間内に、
  認識して勝つ形を作れるかどうか、それだけ
- ユーザーが実機を東京大学 山川研究室で見ている(2026-08-25 の一次観察)

## 検出器 = 円弧プロファイル(ユーザーの一次観察)

> 手のひらを中心に円弧状のプロファイルを取り、そこを横切る指の本数を数える。
> ルールベースを GPU で回しているだけ。

これをそのまま実装する。手のひら重心から半径 R の円周を N 点で標本化し、
手の画素が連続する区間の数を数える。0 本 = グー / 2 本 = チョキ / 5 本 = パー。
**費用は O(N) で画面の大きさに依らない** —— 高速ビジョンの中核の思想。

比較対象として、もっと素直で高い検出器も並べる:
輪郭の凸包欠損を数える / 姿勢ごとのテンプレート照合 / 面積と周長の比。

## 場面

人の手は「全指を握った待機」から始まり、`reveal_ms` かけて目標の形へ開く。
**途中では 3 つの形が似ている**(開き切るまで区別できない)ので、
ロボットは「区別できるようになってから、間に合う速さで」動かねばならない。

ロボットの手は位置アクチュエータ駆動。判定時刻に形が出来ていなければ負け。

## 事前登録した予測

- **勝率 = f(遅延) は閾値型**。遅延 0 で 1.0、ある点から崩れる
- 崩れる点は `reveal_ms` に比例する(人がゆっくり出せばロボットは楽になる)
- 円弧プロファイルは全画面型の検出器より **閉ループで勝つ**(精度ではなく速さで)
- 外れる可能性: 分類が簡単すぎてどの検出器も遅延 0 と同じになる。
  その場合は reveal_ms を縮めて時間圧を上げる
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

try:
    import mujoco
    _HAVE = True
except ImportError:
    _HAVE = False

ROCK, SCISSORS, PAPER = 0, 1, 2
NAMES = {ROCK: "グー", SCISSORS: "チョキ", PAPER: "パー"}
# 指ごとの目標角(0 = 伸ばす, 1.45 = 握る)。親指は判定に使わない
POSES = {
    ROCK:     [1.45, 1.45, 1.45, 1.45, 1.45],
    SCISSORS: [1.45, 0.00, 0.00, 1.45, 1.45],
    PAPER:    [0.00, 0.00, 0.00, 0.00, 0.00],
}
BEATS = {ROCK: PAPER, SCISSORS: ROCK, PAPER: SCISSORS}   # 相手 -> 勝つ手


def _hand(name, x, rgba, actuated):
    """5 本指の手。**手のひらは円盤**、指は縁から放射状に生える。

    最初は手のひらを四角い箱にしていたが、それだと円弧が手のひらの角を横切って
    しまい本数が合わなかった(グー 2 / チョキ 4 / パー 7 と出た)。
    **円弧プロファイルが成立するのは手のひらが丸いから** —— 実際の手の形が
    アルゴリズムの前提になっている。
    """
    R = 0.075                                  # 手のひらの半径
    out = [f'<body name="{name}" pos="{x} 0 0.3">',
           f'  <geom type="cylinder" fromto="0 -.018 0 0 .018 0" size="{R}"'
           f' rgba="{rgba}"/>']
    for i in range(5):
        ar = np.deg2rad(-52.0 + i * 26.0)      # 縁のどこから生えるか
        px, pz = R * np.sin(ar), R * np.cos(ar)
        out += [
            f'  <body name="{name}_f{i}" pos="{px:.4f} 0 {pz:.4f}"'
            f' euler="0 {ar:.4f} 0">',
            f'    <joint name="{name}_j{i}" type="hinge" axis="1 0 0"'
            f' range="-0.1 1.6" damping="0.4"/>',
            f'    <geom type="capsule" fromto="0 0 0 0 0 .080" size=".012"'
            f' rgba="{rgba}"/>',
            '  </body>']
    out.append('</body>')
    act = ""
    if actuated:
        act = "".join(
            f'<position name="{name}_a{i}" joint="{name}_j{i}" kp="30"'
            f' ctrlrange="-0.1 1.6"/>' for i in range(5))
    return chr(10).join(out), act


def build_xml() -> str:
    human, _ = _hand("human", -0.0, ".95 .72 .55 1", actuated=False)
    robot, ract = _hand("robot", 1.2, ".35 .75 .95 1", actuated=True)
    hact = "".join(f'<position name="human_a{i}" joint="human_j{i}" kp="30"'
                   f' ctrlrange="-0.1 1.6"/>' for i in range(5))
    return f"""
<mujoco model="janken">
  <!-- **angle="radian" を明示する**。MuJoCo の既定は degree で、
       この 1 点で 2 回踏んだ:
         (1) カメラの euler="1.5708 0 0" が 1.57 度しか回らず真っ暗な画になった
         (2) 関節の range="-0.1 1.6" が -0.1 度〜1.6 度になり、可動域の拘束力が
             アクチュエータと綱引きして指が 1.24 rad で止まった
             (較正した姿と試合中の姿がずれ、面積検出器が遅延 0 でも勝率 0.33) -->
  <compiler angle="radian"/>
  <option timestep="0.001" gravity="0 0 0"/>
  <!-- 接触は要らない。付けたままだと握った指が手のひらや隣の指に当たって
       目標角(1.45)まで届かず 1.24 で止まり、較正した姿と試合中の姿がずれた
       (面積検出器が遅延 0 でも勝率 0.33 になった原因) -->
  <default><geom contype="0" conaffinity="0"/></default>
  <visual><global offwidth="2048" offheight="2048"/></visual>
  <worldbody>
    <light pos="0 -1 2" dir="0 .4 -1" diffuse="1 1 1"/>
    <geom name="back" type="box" pos="0 .25 .3" size="2 .02 1"
          rgba=".08 .08 .10 1"/>
    {human}
    {robot}
    <camera name="cam" pos="0 -.75 .36" euler="1.5708 0 0" fovy="34"/>
  </worldbody>
  <actuator>{hact}{ract}</actuator>
</mujoco>
"""


@dataclass(frozen=True)
class JCfg:
    res: int = 256
    reveal_ms: int = 200       # 人が待機から目標の形になるまでの時間
    hold_ms: int = 120         # 形になってから判定するまで
    latency: int = 0           # 知覚 + 計算 + 駆動の合計遅延 [ms = steps]
    settle_tol: float = 0.28   # ロボットの指が目標にこれだけ近ければ「形が出来た」
    detector: str = "arc"      # arc | area | template
    arc_r: float = 1.40        # 円弧の半径(**握った拳の半幅** に対する比)
    arc_px: float = 0.0        # 較正済みの絶対半径 [px]。0 なら init で決める
    area_th: tuple = ()        # 面積検出器のしきい値。空なら init で較正する
    prom: float = 0.45         # プロファイル版: 山と認める突出の割合
    prom_min: float = 0.0      # 突出の下限。0 なら init で較正する
    arc_n: int = 64            # 円周の標本点数


def available() -> bool:
    return _HAVE


# --------------------------------------------------------------------------
# 検出器
# --------------------------------------------------------------------------
def _skin(img):
    """人の手の画素(肌色)。ロボットは青いので混ざらない。"""
    r = img[:, :, 0].astype(np.int16)
    g = img[:, :, 1].astype(np.int16)
    b = img[:, :, 2].astype(np.int16)
    return (r > 110) & (r - b > 40) & (g > b)


def _palm(mask):
    m00 = float(mask.sum())
    if m00 < 30:
        return None
    rows = np.arange(mask.shape[0], dtype=float)
    cols = np.arange(mask.shape[1], dtype=float)
    cy = float((mask.sum(1) * rows).sum() / m00)
    cx = float((mask.sum(0) * cols).sum() / m00)
    return cy, cx, m00


def detect_arc(img, cfg: JCfg):
    """**円弧プロファイル** — 手のひら中心の円周を標本化し、指の本数を数える。

    ユーザーが実機で見た方式。費用は O(標本点数) で画面の大きさに依らない。
    """
    mask = _skin(img)
    p = _palm(mask)
    if p is None:
        return None
    cy, cx, m00 = p
    # **半径は較正済みの絶対値**。最初は「見えている手の幅」から決めていたが、
    # 幅は姿勢で変わる(握ると狭い)ので、グーのとき円弧が手のひらの縁に来て
    # 指の付け根を 5 本数えてしまった。実機では手とカメラの距離が固定なので
    # 半径は一度較正すればよい —— **アルゴリズムが設置条件に依存している**
    R = cfg.arc_px if cfg.arc_px > 0 else cfg.arc_r * np.sqrt(m00 / np.pi)
    th = np.arange(cfg.arc_n) * (2 * np.pi / cfg.arc_n)
    yy = np.clip((cy + R * np.sin(th)).astype(int), 0, mask.shape[0] - 1)
    xx = np.clip((cx + R * np.cos(th)).astype(int), 0, mask.shape[1] - 1)
    prof = mask[yy, xx].astype(np.int8)
    runs = int(((prof == 1) & (np.roll(prof, 1) == 0)).sum())
    return _classify_from_fingers(runs)


def area_fill(img) -> float | None:
    """外接矩形に対する充実度。全画素に触るが円弧より素直。"""
    mask = _skin(img)
    m00 = float(mask.sum())
    if m00 < 30:
        return None
    ys, xs = np.nonzero(mask)
    box = (ys.max() - ys.min() + 1) * (xs.max() - xs.min() + 1)
    return m00 / max(box, 1)


_TRACK: dict = {}


def detect_arc_win(img, cfg: JCfg):
    """**追跡つき円弧** — 手のひらの位置を前フレームから引き継ぎ、小窓だけ見る。

    素の `detect_arc` は手のひら重心を出すために全画面のマスクを作っており、
    **O(画面) のままだった**(実測 0.19 ms、全画面型の面積検出器 0.22 ms とほぼ同じ)。
    「円弧は O(標本点数)」という主張は実装として嘘だった。

    実機は手のひらを追跡しているはずで、それは §4b で測った Self-Windowing そのもの。
    ここでは小窓のマスクだけで重心を更新し、円弧の標本は元画像から直接引く。
    """
    st = _TRACK.get("yx")
    H, W = img.shape[0], img.shape[1]
    w = int(cfg.arc_px * 3)
    if st is not None:
        cy0, cx0 = int(st[0]), int(st[1])
        y0, y1 = max(0, cy0 - w // 2), min(H, cy0 + w // 2)
        x0, x1 = max(0, cx0 - w // 2), min(W, cx0 + w // 2)
        sub = _skin(img[y0:y1, x0:x1])
        p = _palm(sub)
        if p is not None:
            cy, cx = p[0] + y0, p[1] + x0
        else:
            p = _palm(_skin(img))
            if p is None:
                _TRACK["yx"] = None
                return None
            cy, cx = p[0], p[1]
    else:
        p = _palm(_skin(img))
        if p is None:
            return None
        cy, cx = p[0], p[1]
    _TRACK["yx"] = (cy, cx)
    R = cfg.arc_px
    th = np.arange(cfg.arc_n) * (2 * np.pi / cfg.arc_n)
    yy = np.clip((cy + R * np.sin(th)).astype(int), 0, H - 1)
    xx = np.clip((cx + R * np.cos(th)).astype(int), 0, W - 1)
    px = img[yy, xx]                        # **円周上の点だけ** 色を読む
    r = px[:, 0].astype(np.int16)
    g = px[:, 1].astype(np.int16)
    b = px[:, 2].astype(np.int16)
    prof = ((r > 110) & (r - b > 40) & (g > b)).astype(np.int8)
    runs = int(((prof == 1) & (np.roll(prof, 1) == 0)).sum())
    return _classify_from_fingers(runs)


def detect_arc_profile(img, cfg: JCfg):
    """**半径方向プロファイル版の円弧** — 各方向への手の広がりを測り、山を数える。

    ユーザーの説明は「円弧状の **プロファイル取得後** の指の本数カウント」だった。
    プロファイルは **信号** であって二値ではない。最初に実装した `detect_arc` は
    「固定半径の円周を横切るか」という最も過酷な二値版で、
    **指が円周を越えるまで何も起きない**(実測 判別 129 ms)。

    こちらは各方向 theta について「手が存在する最大半径」を測って 1 次元の
    プロファイルにし、突出(prominence)が閾値を超える山を指として数える。
    指が伸び始めた瞬間から連続的に反応するはず。
    費用は O(方向数 x 半径方向の標本数) で **画面の大きさに依らない** のは同じ。
    """
    st = _TRACK.get("yx")
    H, W = img.shape[0], img.shape[1]
    if st is None:
        p0 = _palm(_skin(img))
        if p0 is None:
            return None
        cy, cx = p0[0], p0[1]
    else:
        cy, cx = st
    n_th, n_r = cfg.arc_n, 40
    R_max = cfg.arc_px * 1.9
    th = np.arange(n_th) * (2 * np.pi / n_th)
    rr = np.linspace(0.15 * R_max, R_max, n_r)
    yy = np.clip((cy + rr[None, :] * np.sin(th)[:, None]).astype(int), 0, H - 1)
    xx = np.clip((cx + rr[None, :] * np.cos(th)[:, None]).astype(int), 0, W - 1)
    px = img[yy, xx]
    r_ = px[:, :, 0].astype(np.int16)
    g_ = px[:, :, 1].astype(np.int16)
    b_ = px[:, :, 2].astype(np.int16)
    hit = (r_ > 110) & (r_ - b_ > 40) & (g_ > b_)
    idx = np.where(hit.any(1), n_r - 1 - np.argmax(hit[:, ::-1], axis=1), 0)
    prof = rr[idx]                                   # 各方向の手の広がり
    # 重心も更新しておく(追跡)
    if st is not None:
        m = _skin(img[max(0, int(cy) - int(cfg.arc_px)):int(cy) + int(cfg.arc_px),
                      max(0, int(cx) - int(cfg.arc_px)):int(cx) + int(cfg.arc_px)])
        pm = _palm(m)
        if pm is not None:
            _TRACK["yx"] = (pm[0] + max(0, int(cy) - int(cfg.arc_px)),
                            pm[1] + max(0, int(cx) - int(cfg.arc_px)))
    else:
        _TRACK["yx"] = (cy, cx)
    base = float(np.median(prof))
    thr = base + cfg.prom * (prof.max() - base) if prof.max() > base else np.inf
    if not np.isfinite(thr) or prof.max() - base < cfg.prom_min * cfg.arc_px:
        return ROCK
    up = prof > thr
    runs = int(((up) & (~np.roll(up, 1))).sum())
    return _classify_from_fingers(runs)


def detect_area(img, cfg: JCfg):
    """充実度で分類。しきい値は 3 姿勢の完成形から較正する(円弧と同じ較正予算)。"""
    f = area_fill(img)
    if f is None or not cfg.area_th:
        return None
    t1, t2 = cfg.area_th                       # t1 > t2。大きいほど詰まっている
    if f > t1:
        return ROCK
    return SCISSORS if f > t2 else PAPER


_TPL: dict = {}


def detect_template(img, cfg: JCfg, tpls=None):
    """姿勢ごとのテンプレートと相関を取る。いちばん正確で高い。"""
    from scipy.ndimage import zoom
    mask = _skin(img).astype(float)
    if mask.sum() < 30:
        return None
    ys, xs = np.nonzero(mask)
    sub = mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    # 外接矩形を切り出して 48x48 に正規化してから相関を取る。
    # この正規化を省くと画素数の多いパーが必ず勝つ(最初そうなっていた)
    z = zoom(sub, (48 / sub.shape[0], 48 / sub.shape[1]), order=1)
    z = z - z.mean()
    z = z / (np.sqrt((z ** 2).sum()) or 1.0)
    best, arg = -np.inf, None
    for k, t in (tpls or _TPL).items():
        r = float((z * t).sum())
        if r > best:
            best, arg = r, k
    return arg


def _classify_from_fingers(n: int):
    if n <= 1:
        return ROCK
    return SCISSORS if n <= 3 else PAPER


DETECTORS = {"arc": detect_arc, "arc_win": detect_arc_win,
             "arc_prof": detect_arc_profile,
             "area": detect_area, "template": detect_template}


# --------------------------------------------------------------------------
# 試合
# --------------------------------------------------------------------------
class Janken:
    def __init__(self, cfg: JCfg):
        if not _HAVE:
            raise RuntimeError("mujoco が要る")
        self.cfg = cfg
        self.model = mujoco.MjModel.from_xml_string(build_xml())
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, cfg.res, cfg.res)
        self.hj = [self.model.actuator(f"human_a{i}").id for i in range(5)]
        self.rj = [self.model.actuator(f"robot_a{i}").id for i in range(5)]
        self.rq = [self.model.joint(f"robot_j{i}").qposadr[0] for i in range(5)]
        if cfg.arc_px <= 0 or not cfg.area_th or cfg.prom_min <= 0:
            from dataclasses import replace as _rep
            self.cfg = _rep(cfg, arc_px=self._calibrate_arc(cfg.arc_r),
                            area_th=self._calibrate_area())
            self.cfg = _rep(self.cfg, prom_min=self._calibrate_prom())

    def _profile(self, img, cy=None, cx=None):
        """各方向への手の広がり(半径方向プロファイル)。"""
        c = self.cfg
        if cy is None:
            p0 = _palm(_skin(img))
            if p0 is None:
                return None
            cy, cx = p0[0], p0[1]
        H, W = img.shape[0], img.shape[1]
        n_r, R = 40, c.arc_px * 1.9
        th = np.arange(c.arc_n) * (2 * np.pi / c.arc_n)
        rr = np.linspace(0.15 * R, R, n_r)
        yy = np.clip((cy + rr[None, :] * np.sin(th)[:, None]).astype(int), 0, H - 1)
        xx = np.clip((cx + rr[None, :] * np.cos(th)[:, None]).astype(int), 0, W - 1)
        px = img[yy, xx]
        r_ = px[:, :, 0].astype(np.int16)
        g_ = px[:, :, 1].astype(np.int16)
        b_ = px[:, :, 2].astype(np.int16)
        hit = (r_ > 110) & (r_ - b_ > 40) & (g_ > b_)
        idx = np.where(hit.any(1), n_r - 1 - np.argmax(hit[:, ::-1], axis=1), 0)
        return rr[idx]

    def _calibrate_prom(self) -> float:
        """握り拳と、チョキ・パーの突出の中点をしきい値にする。"""
        pr = {}
        for pose in POSES:
            v = self._profile(self._pose_image(pose))
            pr[pose] = (v.max() - float(np.median(v))) / self.cfg.arc_px
        lo = pr[ROCK]
        hi = min(pr[SCISSORS], pr[PAPER])
        return float((lo + hi) / 2)

    def _pose_image(self, pose: int):
        mujoco.mj_resetData(self.model, self.data)
        for i, a in enumerate(POSES[pose]):
            self.data.ctrl[self.hj[i]] = a
            self.data.qpos[self.model.joint(f"human_j{i}").qposadr[0]] = a
        mujoco.mj_forward(self.model, self.data)
        return self._render()

    def _calibrate_area(self) -> tuple:
        """3 姿勢の完成形の充実度の中点をしきい値にする。"""
        f = {p: area_fill(self._pose_image(p)) for p in POSES}
        return ((f[ROCK] + f[SCISSORS]) / 2, (f[SCISSORS] + f[PAPER]) / 2)

    def _calibrate_arc(self, k: float) -> float:
        """握った拳を 1 枚撮って、その半幅から円弧の半径を決める(設置時の較正)。"""
        m = _skin(self._pose_image(ROCK))
        _, xs = np.nonzero(m)
        return float(k * (xs.max() - xs.min() + 1) / 2.0)

    def _render(self):
        self.renderer.update_scene(self.data, camera="cam")
        return self.renderer.render()

    def make_templates(self):
        """姿勢ごとの完成形マスクをテンプレートにする。"""
        from scipy.ndimage import zoom
        out = {}
        for pose in POSES:
            m = _skin(self._pose_image(pose)).astype(float)
            ys, xs = np.nonzero(m)
            sub = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
            z = zoom(sub, (48 / sub.shape[0], 48 / sub.shape[1]), order=1)
            z = z - z.mean()
            out[pose] = z / (np.sqrt((z ** 2).sum()) or 1.0)
        _TPL.update(out)
        return out

    def play(self, human_pose: int, seed: int = 0) -> dict:
        """1 試合。返り値に勝敗と、ロボットが形を作れたかを含む。"""
        c = self.cfg
        m, d = self.model, self.data
        mujoco.mj_resetData(m, d)
        for i in range(5):                       # 待機 = 全指を握る
            d.ctrl[self.hj[i]] = POSES[ROCK][i]
            d.qpos[m.joint(f"human_j{i}").qposadr[0]] = POSES[ROCK][i]
            d.ctrl[self.rj[i]] = POSES[ROCK][i]
            d.qpos[m.joint(f"robot_j{i}").qposadr[0]] = POSES[ROCK][i]
        mujoco.mj_forward(m, d)

        fn = DETECTORS[c.detector]
        _TRACK.clear()          # 追跡状態は試合ごとに初期化
        buf: list[int | None] = [None] * (c.latency + 1)
        total = c.reveal_ms + c.hold_ms
        guess_hist = []
        for k in range(total):
            f = min(1.0, k / max(1, c.reveal_ms))       # 開き具合
            for i in range(5):
                a = POSES[ROCK][i] + f * (POSES[human_pose][i] - POSES[ROCK][i])
                d.ctrl[self.hj[i]] = a
            img = self._render()
            buf.append(fn(img, c))
            seen = buf.pop(0)
            if seen is not None:
                want = BEATS[seen]
                for i in range(5):
                    d.ctrl[self.rj[i]] = POSES[want][i]
                guess_hist.append(seen)
            mujoco.mj_step(m, d)

        want = BEATS[human_pose]
        q = np.array([d.qpos[a] for a in self.rq])
        formed = bool(np.abs(q - np.array(POSES[want])).max() < c.settle_tol)
        # ロボットが実際に作った形を、目標との距離で判定する
        dists = {p: float(np.abs(q - np.array(POSES[p])).max()) for p in POSES}
        shown = min(dists, key=dists.get)
        if dists[shown] > c.settle_tol:
            result = "未完成"
        elif shown == want:
            result = "勝ち"
        elif shown == human_pose:
            result = "あいこ"
        else:
            result = "負け"
        return {"result": result, "formed": formed, "shown": shown,
                "want": want, "human": human_pose,
                "guesses": guess_hist[-1] if guess_hist else None}


def discrimination_time(cfg: JCfg) -> dict:
    """**いつ判別できるようになるか**。早く判るのは実効的に遅延が小さいのと同じ。

    人の手が開いていく途中で、各検出器が初めて正解を返した時刻(ms)を返す。
    以後ずっと正解であり続けた最初の時刻を採る(一瞬だけ当たるのは数えない)。
    """
    j = Janken(cfg)
    if cfg.detector == "template":
        j.make_templates()
    fn = DETECTORS[cfg.detector]
    out = {}
    for pose in POSES:
        _TRACK.clear()
        mujoco.mj_resetData(j.model, j.data)
        for i in range(5):
            j.data.qpos[j.model.joint(f"human_j{i}").qposadr[0]] = POSES[ROCK][i]
        ok_from = None
        for k in range(cfg.reveal_ms + 1):
            f = min(1.0, k / max(1, cfg.reveal_ms))
            for i in range(5):
                a = POSES[ROCK][i] + f * (POSES[pose][i] - POSES[ROCK][i])
                j.data.ctrl[j.hj[i]] = a
                j.data.qpos[j.model.joint(f"human_j{i}").qposadr[0]] = a
            mujoco.mj_forward(j.model, j.data)
            got = fn(j._render(), j.cfg)
            if got == pose:
                ok_from = k if ok_from is None else ok_from
            else:
                ok_from = None
        out[pose] = ok_from
    return out


def win_rate(cfg: JCfg, reps: int = 3) -> dict:
    j = Janken(cfg)
    if cfg.detector == "template":
        j.make_templates()
    out = {"勝ち": 0, "あいこ": 0, "負け": 0, "未完成": 0}
    n = 0
    for _ in range(reps):
        for pose in (ROCK, SCISSORS, PAPER):
            out[j.play(pose)["result"]] += 1
            n += 1
    return {k: v / n for k, v in out.items()}


def latency_budget(cfg: JCfg, hi: int = 500, step: int = 10) -> int:
    """勝率 1.00 を保てる **最大の遅延** [ms]。これが「遅延の予算」。"""
    from dataclasses import replace
    last = -1
    for L in range(0, hi + 1, step):
        if win_rate(replace(cfg, latency=L), reps=1)["勝ち"] < 1.0:
            return last
        last = L
    return last


def main():
    if not available():
        print("mujoco が無い")
        return
    from dataclasses import replace
    base = JCfg()
    print("H2b じゃんけん — 勝率 = f(遅延)")
    print(f"  人が形を出すまで {base.reveal_ms} ms / 判定まで さらに "
          f"{base.hold_ms} ms / 解像度 {base.res}")

    print(f"\n  検出器の健全性(遅延 0)")
    for det in DETECTORS:
        r = win_rate(replace(base, detector=det, latency=0))
        print(f"   {det:<10} 勝ち {r['勝ち']:.2f}  あいこ {r['あいこ']:.2f}  "
              f"負け {r['負け']:.2f}  未完成 {r['未完成']:.2f}")

    print(f"\n  勝率 = f(遅延)")
    lats = (0, 20, 40, 60, 80, 120, 160, 200)
    print(f"  {'遅延 ms':>8}" + "".join(f"{d:>12}" for d in DETECTORS))
    for L in lats:
        row = []
        for det in DETECTORS:
            row.append(win_rate(replace(base, detector=det, latency=L))["勝ち"])
        print(f"  {L:>8}" + "".join(f"{x:12.2f}" for x in row), flush=True)


if __name__ == "__main__":
    main()
