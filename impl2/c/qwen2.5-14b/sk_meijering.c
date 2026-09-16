#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない。仕様書に明記されている。

    // 画像の端を処理する際、ここでは単純に端のピクセルをコピーする。
    // これは、入力画像の境界値を無視せずにそのまま使用するという選択である。

    // Hessian マトリクスの計算に必要なパラメータ
    const double sigmas[] = {1.0, 2.0, 3.0, 4.0}; // 4つのガウシアンスケール
    const int num_scales = sizeof(sigmas) / sizeof(sigmas[0]);

    // 各スケールでのガウシアンフィルタリングとHessianマトリクスの計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double H[3][3] = {{0}};
            double lambda[3] = {0};

            // 各スケールでのガウシアンフィルタリングとHessianマトリクスの計算
            for (int s = 0; s < num_scales; ++s) {
                double sigma = sigmas[s];
                double dx = (x > 0 ? in[(y)*(w) + (x-1)] : in[(y)*(w) + (x)]);
                double dy = (y > 0 ? in[(y-1)*(w) + (x)] : in[(y)*(w) + (x)]);
                double dxx = (x > 1 ? in[(y)*(w) + (x-2)] : in[(y)*(w) + (x)]);
                double dyy = (y > 1 ? in[(y-2)*(w) + (x)] : in[(y)*(w) + (x)]);
                double dxy = (x > 0 && y > 0 ? in[(y-1)*(w) + (x-1)] : in[(y)*(w) + (x)]);
                double dxx2 = (x < w-2 ? in[(y)*(w) + (x+2)] : in[(y)*(w) + (x)]);
                double dyy2 = (y < h-2 ? in[(y+2)*(w) + (x)] : in[(y)*(w) + (x)]);
                double dxy2 = (x < w-1 && y < h-1 ? in[(y+1)*(w) + (x+1)] : in[(y)*(w) + (x)]);

                // Hessian マトリクスの更新
                H[0][0] += (dxx2 - 2 * dxx + dxx) / (sigma * sigma);
                H[0][1] += (dxy2 - 2 * dxy + dxy) / (sigma * sigma);
                H[1][0] += (dxy2 - 2 * dxy + dxy) / (sigma * sigma);
                H[1][1] += (dyy2 - 2 * dy + dyy) / (sigma * sigma);

                // Hessian マトリクスの固有値の計算
                lambda[0] += (H[0][0] + H[1][1] + sqrt((H[0][0] - H[1][1]) * (H[0][0] - H[1][1]) + 4 * H[0][1] * H[1][0])) / 2;
                lambda[1] += (H[0][0] + H[1][1] - sqrt((H[0][0] - H[1][1]) * (H[0][0] - H[1][1]) + 4 * H[0][1] * H[1][0])) / 2;
            }

            // 最終的な出力の計算
            double neuriteness = 0;
            for (int i = 0; i < 2; ++i) {
                neuriteness += exp(-lambda[i] * lambda[i] / (2 * sigmas[0] * sigmas[0]));
            }
            neuriteness /= num_scales;

            // 出力を最大値で正規化
            out[y * w + x] = neuriteness;
        }
    }

    // 最大値の計算
    double max_value = 0;
    for (int i = 0; i < h * w; ++i) {
        if (out[i] > max_value) {
            max_value = out[i];
        }
    }

    // 正規化
    for (int i = 0; i < h * w; ++i) {
        out[i] /= max_value;
    }
}
