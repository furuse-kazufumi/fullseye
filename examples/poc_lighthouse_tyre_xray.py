"""仮想工場のタイヤX線検査。

外から来るもの: WEF 2025付録の「不良流出99%減」(比較対象ではなく併記のみ)。
自作: Beer–Lambert合成、真値、固定閾値基準、Fullseye componentsパイプライン。
門: 検出器は画像しか受け取らず、真値照合は独立。学習seedとholdout seedを分離する。
"""
import examplefig as figs
from lighthouse_vfactory_cli import main


def save_figure(name, image, caption):
    return figs.save(name, image, caption=caption)


if __name__ == "__main__":
    status = main("tyre", save_figure)
    if figs.errors(): print("図の書き出しで失敗:", "; ".join(figs.errors()))
    raise SystemExit(status)
