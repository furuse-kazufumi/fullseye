"""4 方位 DoFP 偏光カメラで Mueller 行列の見える部分を測る PoC。

外から来るもの: Azzam & Bashara, Ellipsometry and Polarized Light (1987),
Eq. (1.14) ``I=.5*(S0+S1 cos2a+S2 sin2a)``。実務条件は 0/45/90/135°
の線偏光マイクロアナライザ、読み出し雑音 0.2 %。
自作: Kronecker 積の設計行列、SVD rank/条件数、200 回 Monte Carlo。
門: rank は SVD から計算、Fullseye Mueller 強度と独立な行ベクトル式の誤差
<1e-12、線偏光だけと QWP 追加設計の復元誤差を同じ真値で比較する。
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1])); import optics as fs  # noqa:E402
import examplefig as figs  # noqa: E402
SLUG="poc_mueller_dofp_observability"; ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/"docs/articles/assets/poc"/SLUG
if not os.environ.get("FULLSEYE_FIGURE_DIR"):   # 図の規約: 環境変数が無ければ公開の図(docs/)を書かない
    import tempfile
    OUT = Path(tempfile.mkdtemp(prefix=SLUG + "_"))
ANG=(0.,45.,90.,135.)
def states(qwp=False):
    out=[]
    for a in ANG:
        p=np.asarray(fs.mueller_element("polarizer",a))
        out.append((np.asarray(fs.mueller_element("quarter_wave",a+22.5))@p if qwp else p)@np.array([1.,0,0,0]))
    return out
def design(qwp=False):
    gens=states(False)+(states(True) if qwp else []); anas=[]
    for a in ANG:
        p=np.asarray(fs.mueller_element("polarizer",a)); anas.append(p[0])
        if qwp: anas.append((p@np.asarray(fs.mueller_element("quarter_wave",a+22.5)))[0])
    return np.array([np.kron(g,a) for g in gens for a in anas])
def compute():
    A=design(False); B=design(True); ranks=(np.linalg.matrix_rank(A,tol=1e-10),np.linalg.matrix_rank(B,tol=1e-10))
    m=np.asarray(fs.mueller_element("retarder",31,73))@np.asarray(fs.mueller_element("polarizer",12)); truth=m.ravel(order="F")
    direct=A@truth; via=[]
    for g in states(False):
        for a in ANG: via.append((np.asarray(fs.mueller_element("polarizer",a))@m@g)[0])
    patherr=float(np.max(abs(direct-via))); assert patherr<1e-12 and ranks==(9,16)
    rng=np.random.default_rng(260103); errs={"linear_only":[],"qwp_added":[]}
    for _ in range(200):
        for key,D in (("linear_only",A),("qwp_added",B)):
            y=D@truth+rng.normal(0,.002,len(D)); est=np.linalg.pinv(D)@y; errs[key].append(np.linalg.norm(est-truth)/np.linalg.norm(truth))
    return A,B,ranks,patherr,{k:float(np.median(v)) for k,v in errs.items()}
def main():
    import matplotlib.pyplot as plt
    A,B,ranks,patherr,errs=compute(); OUT.mkdir(parents=True,exist_ok=True); fig,ax=plt.subplots(1,2,figsize=(16,9),dpi=100)
    for D,label in ((A,"linear DoFP"),(B,"with QWP states")): ax[0].semilogy(np.arange(1,17),np.pad(np.linalg.svd(D,compute_uv=False),(0,16-min(D.shape)),constant_values=np.nan),"o-",label=label)
    ax[0].set(xlabel="singular-value index",ylabel="singular value",title=f"Computed ranks: {ranks[0]} / {ranks[1]}"); ax[0].grid(); ax[0].legend()
    ax[1].bar(errs.keys(),errs.values(),color=["#d95f02","#1b9e77"]); ax[1].set(ylabel="median relative Mueller error",title="200 trials, read noise = 0.2%")
    fig.suptitle("A four-angle polarization camera has a seven-dimensional Mueller blind space"); fig.tight_layout(); fn="01_observability.png"; fig.savefig(OUT/fn); fig.canvas.draw(); figs.save('observability', np.asarray(fig.canvas.buffer_rgba())[..., :3].copy(), caption='SVD-computed observability and noise propagation for linear-only and QWP-augmented polarimeters.'); plt.close(fig)
    metrics={"linear_rank":int(ranks[0]),"qwp_rank":int(ranks[1]),"independent_path_max_error":patherr,"median_relative_error":errs,"trials":200}
    (OUT/"metrics.json").write_text(json.dumps(metrics,indent=2)+"\n"); (OUT/"figures.json").write_text(json.dumps([{"file":fn,"name":"observability","caption":"SVD-computed observability and noise propagation for linear-only and QWP-augmented polarimeters.","shape":[900,1600,4]}],indent=2)+"\n"); print(json.dumps(metrics)); print("PASS",SLUG)

def _report_figure_errors():
    for err in figs.errors():   # 図が書けなかった理由を黙って捨てない
        print("[figure error]", err)

if __name__ == "__main__":
    main()
    _report_figure_errors()
