#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // この実装では、画像の端は境界値を保持するように処理します。
    // つまり、境界外のピクセルは端のピクセルの値を用います。

    // デリバティブのスムージングスケールと平坦勾配許容度を定義
    double smoothing_scale = a;
    double flat_gradient_tolerance = b;

    // デリバティブの計算に必要なパラメータ
    double dx[3] = {-1, 0, 1};
    double dy[3] = {-1, 0, 1};

    // Hessian マトリックスの計算に必要なパラメータ
    double dxx[3][3] = {
        {-1, 0, 1},
        {-2, 0, 2},
        {-1, 0, 1}
    };
    double dxy[3][3] = {
        {1, 0, -1},
        {0, 0, 0},
        {-1, 0, 1}
    };
    double dyy[3][3] = {
        {1, 0, -1},
        {2, 0, -2},
        {1, 0, -1}
    };

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 各ピクセルについて、勾配の大きさとヘッシアンの固有値の符号に基づいて分類
    for (int y = 1; y < h - 1; y++) {
        for (int x = 1; x < w - 1; x++) {
            // 勾配の計算
            double gx = 0.0, gy = 0.0;
            for (int i = 0; i < 3; i++) {
                for (int j = 0; j < 3; j++) {
                    gx += dx[i] * in[(y + dy[j]) * w + (x + dx[i])];
                    gy += dy[j] * in[(y + dy[j]) * w + (x + dx[i])];
                }
            }

            // ヘッシアンの計算
            double dxx_val = 0.0, dxy_val = 0.0, dyy_val = 0.0;
            for (int i = 0; i < 3; i++) {
                for (int j = 0; j < 3; j++) {
                    dxx_val += dxx[i][j] * in[(y + dy[j]) * w + (x + dx[i])];
                    dxy_val += dxy[i][j] * in[(y + dy[j]) * w + (x + dx[i])];
                    dyy_val += dyy[i][j] * in[(y + dy[j]) * w + (x + dx[i])];
                }
            }

            // 勾配の大きさとヘッシアンの固有値の符号に基づいて分類
            double gradient_magnitude = sqrt(gx * gx + gy * gy);
            double hessian_trace = dxx_val + dyy_val;
            double hessian_det = dxx_val * dyy_val - dxy_val * dxy_val;

            if (gradient_magnitude < flat_gradient_tolerance) {
                out[y * w + x] = 0.0; // flat
            } else if (hessian_trace > 0 && hessian_det > 0) {
                out[y * w + x] = 1.0; // peak
            } else if (hessian_trace < 0 && hessian_det > 0) {
                out[y * w + x] = 0.14; // pit
            } else if (hessian_trace > 0 && hessian_det < 0) {
                out[y * w + x] = 0.30; // ravine
            } else if (hessian_trace < 0 && hessian_det < 0) {
                out[y * w + x] = 0.45; // saddle
            } else if (hessian_trace == 0 && hessian_det > 0) {
                out[y * w + x] = 0.55; // hillside
            } else if (hessian_trace == 0 && hessian_det < 0) {
                out[y * w + x] = 0.75; // ridge
            } else {
                out[y * w + x] = 0.5; // flat
            }
        }
    }
}
