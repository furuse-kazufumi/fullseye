#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // パラメータのスケーリング
    double sigma_s = 1.0 + 3.0 * a; // 空間シグマの範囲を 1 から 4 にスケーリング
    double sigma_r = 0.05 + 0.40 * b; // 輝度シグマの範囲を 0.05 から 0.45 にスケーリング

    // ガウス関数の計算用
    double exp_denom_s = -2.0 * sigma_s * sigma_s;
    double exp_denom_r = -2.0 * sigma_r * sigma_r;

    // 画像の端をゼロパディングする
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double weight_sum = 0.0;

            // 近傍画素の範囲を決定 (ここでは sigma_s * 3 以内)
            int radius = (int)(3.0 * sigma_s);
            for (int ky = -radius; ky <= radius; ky++) {
                for (int kx = -radius; kx <= radius; kx++) {
                    int ny = y + ky;
                    int nx = x + kx;

                    // 境界外の画素はスキップ
                    if (ny < 0 || ny >= h || nx < 0 || nx >= w) {
                        continue;
                    }

                    // 空間距離の計算
                    double dx = (double)kx;
                    double dy = (double)ky;
                    double spatial_dist = dx * dx + dy * dy;

                    // 輝度距離の計算
                    double intensity_dist = in[ny * w + nx] - in[y * w + x];
                    double intensity_dist_sq = intensity_dist * intensity_dist;

                    // ガウスウェイトの計算
                    double spatial_weight = exp(spatial_dist / exp_denom_s);
                    double intensity_weight = exp(intensity_dist_sq / exp_denom_r);
                    double weight = spatial_weight * intensity_weight;

                    // 重み付き和の計算
                    sum += in[ny * w + nx] * weight;
                    weight_sum += weight;
                }
            }

            // 重み付き平均の計算
            out[y * w + x] = weight_sum > 0.0 ? sum / weight_sum : in[y * w + x];
        }
    }
}
