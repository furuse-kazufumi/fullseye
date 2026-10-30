"""仮想工場のタイヤX線検査。

外から来るもの: WEF 2025付録の「不良流出99%減」(比較対象ではなく併記のみ)。
自作: Beer–Lambert合成、真値、固定閾値基準、Fullseye componentsパイプライン。
門: 検出器は画像しか受け取らず、真値照合は独立。学習seedとholdout seedを分離する。
"""
from lighthouse_vfactory_cli import main
if __name__ == "__main__": raise SystemExit(main("tyre"))
