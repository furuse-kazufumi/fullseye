#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // LBP の近傍点数
    const int P = 8;
    // 半径 R の範囲
    const int R_min = 1;
    const int R_max = 4;
    // 符号化方法の選択
    const char* method = (b < 0.60) ? "default" : (b < 0.75) ? "ror" : (b < 0.90) ? "uniform" : "nri_uniform";

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // LBP の適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 半径 R の計算
            int R = R_min + (int)(a * (R_max - R_min));
            // LBP の計算
            double lbp = 0;
            for (int i = 0; i < P; i++) {
                int dx = (int)(R * cos(2 * M_PI * i / P));
                int dy = (int)(R * sin(2 * M_PI * i / P));
                int nx = x + dx;
                int ny = y + dy;
                // 画像の境界外を処理するための補間
                if (nx < 0 || nx >= w || ny < 0 || ny >= h) {
                    nx = (nx < 0) ? 0 : (nx >= w) ? w - 1 : nx;
                    ny = (ny < 0) ? 0 : (ny >= h) ? h - 1 : ny;
                }
                double neighbor = in[ny * w + nx];
                if (neighbor > in[y * w + x]) {
                    lbp += pow(2, i);
                }
            }
            // 符号化方法の適用
            switch (method) {
                case "default":
                    out[y * w + x] = lbp;
                    break;
                case "ror":
                    // 回転不変な符号化
                    out[y * w + x] = (lbp << 1) | (lbp >> (P - 1));
                    break;
                case "uniform":
                    // 一様な符号化
                    int uniform = 0;
                    for (int i = 0; i < P; i++) {
                        if ((lbp & (1 << i)) && (lbp & (1 << (i + 1) % P))) {
                            uniform++;
                        }
                    }
                    out[y * w + x] = (uniform <= 2) ? uniform : 2;
                    break;
                case "nri_uniform":
                    // 非冗長一様な符号化
                    int nri_uniform = 0;
                    for (int i = 0; i < P; i++) {
                        if ((lbp & (1 << i)) && (lbp & (1 << (i + 1) % P))) {
                            nri_uniform++;
                        }
                    }
                    out[y * w + x] = (nri_uniform <= 2) ? nri_uniform : 2;
                    break;
            }
        }
    }

    // 出力画像の正規化
    double max_val = 0;
    for (int i = 0; i < h * w; i++) {
        if (out[i] > max_val) {
            max_val = out[i];
        }
    }
    if (max_val > 0) {
        for (int i = 0; i < h * w; i++) {
            out[i] /= max_val;
        }
    }
}
