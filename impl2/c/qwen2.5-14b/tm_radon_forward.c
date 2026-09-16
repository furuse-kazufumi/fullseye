#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a から角度の数を計算
    int n_angles = (int)round(h * a);
    n_angles = n_angles < 8 ? 8 : (n_angles > 360 ? 360 : n_angles);

    // つまみ b から角度の範囲を計算
    double angle_span = 180 * (b < 0.5 ? 2 * b : 1);

    // 出力画像の高さと幅を計算
    int out_h = n_angles;
    int out_w = w;

    // 出力画像の初期化
    for (int i = 0; i < out_h * out_w; ++i) {
        out[i] = 0.0;
    }

    // Radon 変換の実装
    for (int angle_idx = 0; angle_idx < n_angles; ++angle_idx) {
        double angle = angle_idx * (angle_span / n_angles);
        double sin_theta = sin(angle * M_PI / 180.0);
        double cos_theta = cos(angle * M_PI / 180.0);

        // 各角度での積分
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            for (int y = 0; y < h; ++y) {
                double x_prime = x * cos_theta + y * sin_theta;
                double y_prime = -x * sin_theta + y * cos_theta;
                int x_int = (int)round(x_prime);
                int y_int = (int)round(y_prime);

                // 画像の範囲外の場合は無視
                if (x_int >= 0 && x_int < w && y_int >= 0 && y_int < h) {
                    sum += in[y_int * w + x_int];
                }
            }
            out[angle_idx * out_w + x] = sum;
        }
    }
}
