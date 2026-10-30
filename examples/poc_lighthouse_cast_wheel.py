"""仮想工場の鋳造ホイールX線検査。

外から来るもの: WEF 2025の重大欠陥見逃し98.1%減、既存CT/X線PoCの物理構成。
自作: 気孔・引け巣・介在物と重大度規則、探索・holdout評価。
門: 検出器は画素だけを読み、真値は独立照合にだけ使う。
"""
from lighthouse_vfactory_cli import main
if __name__ == "__main__": raise SystemExit(main("wheel"))
