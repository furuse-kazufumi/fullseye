#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Chan-Vese セグメンテーションの初期化
    // 初期レベルセットはチェッカーボード状とし、境界条件は周期的とする。
    // 画像の端を処理する際は、周期的な境界条件を想定する。

    // パラメータ設定
    double mu = 0.1 + 0.4 * a; // 辺長重み
    int max_num_iter = 60;     // 反復回数

    // レベルセットの初期化
    double* phi = (double*)malloc(h * w * sizeof(double));
    for (int i = 0; i < h * w; i++) {
        phi[i] = (i % 2 == 0) ? 1.0 : -1.0; // チェッカーボード状の初期化
    }

    // Chan-Vese アルゴリズムの反復計算
    for (int iter = 0; iter < max_num_iter; iter++) {
        // レベルセットの更新
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int idx = y * w + x;
                double c = 0.0, d = 0.0;
                for (int dy = -1; dy <= 1; dy++) {
                    for (int dx = -1; dx <= 1; dx++) {
                        int ny = (y + dy + h) % h; // 周期的な境界条件
                        int nx = (x + dx + w) % w;
                        int nidx = ny * w + nx;
                        c += exp(-mu * (in[idx] - in[nidx]) * (in[idx] - in[nidx]));
                        d += exp(-mu * (phi[idx] - phi[nidx]) * (phi[idx] - phi[nidx]));
                    }
                }
                phi[idx] = (c > d) ? 1.0 : -1.0;
            }
        }
    }

    // 出力画像の生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            out[idx] = (phi[idx] > 0) ? 1.0 : 0.0;
        }
    }

    // メモリの解放
    free(phi);
}
