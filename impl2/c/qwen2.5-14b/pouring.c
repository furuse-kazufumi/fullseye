#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数定義
    const double marker_threshold = 0.2 + 0.3 * a;
    const double sobel_kernel[9] = {1, 0, -1, 2, 0, -2, 1, 0, -1}; // Sobel カーネル

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // 勾配画像の生成
    double* gradient = (double*)malloc(h * w * sizeof(double));
    if (gradient == NULL) {
        return; // メモリ確保失敗
    }

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double gx = 0.0, gy = 0.0;
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int ny = y + ky, nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double value = in[ny * w + nx];
                        gx += value * sobel_kernel[kx + 1 + (ky + 1) * 3];
                        gy += value * sobel_kernel[kx + 1 + (ky + 1) * 3 + 3];
                    }
                }
            }
            gradient[y * w + x] = sqrt(gx * gx + gy * gy);
        }
    }

    // マーカーの生成
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            if (gradient[y * w + x] < marker_threshold) {
                out[y * w + x] = 1.0;
            }
        }
    }

    // メモリ解放
    free(gradient);
}
