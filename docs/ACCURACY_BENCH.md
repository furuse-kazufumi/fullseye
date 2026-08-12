# Accuracy benchmark — champion vs null (holdout)

> Short-budget sweep: gens=8, pop=10, n_train=6, n_holdout=4, size=32, seed=0. Selection is on TRAIN only; all scores below are on the HELD-OUT set. Higher is better. Not the headline long-budget numbers — this is the standing 'does evolution beat the null' table.

| problem | unit | trivial | hand | random | **champion** | best null | beats null? | gap |
|---|---|--:|--:|--:|--:|--:|:--:|--:|
| denoise | dB PSNR | 15.2785 | 20.2116 | 12.3234 | **16.3677** | 20.2116 | no | 1.1763 |
| edge | F1 | 0.4172 | 0.9324 | 0.2851 | **0.3817** | 0.9324 | no | 0.2283 |
| binarize | IoU | 0.7756 | 0.8865 | 0.2626 | **0.5714** | 0.8865 | no | 0.0584 |
| count | 1/(1+err) | 0.0642 | 0.625 | 0.5833 | **0.625** | 0.625 | no | 0.2917 |
| locate | 1/(1+px) | 0.0 | 1.0 | 0.0487 | **1.0** | 1.0 | no | 0.0 |
| locate_rot | 1/(1+px) | 0.0 | 1.0 | 0.185 | **0.5573** | 1.0 | no | -0.1455 |
| classify | accuracy | 0.5 | 0.5 | 1.0 | **1.0** | 1.0 | no | 0.0 |
| barcode | 1/(1+err) | 0.5 | 1.0 | 1.0 | **1.0** | 1.0 | no | 0.0 |
| vol_denoise | dB PSNR | 19.3031 | 21.3223 | 20.3518 | **24.5895** | 21.3223 | yes | -1.029 |
| vol_count | 1/(1+err) | 0.2986 | 1.0 | 1.0 | **1.0** | 1.0 | no | 0.0 |

**Champion beats the best null on holdout in 1/10 problems.** A negative gap means holdout ≥ train (no overfit); a large positive gap flags overfitting.
