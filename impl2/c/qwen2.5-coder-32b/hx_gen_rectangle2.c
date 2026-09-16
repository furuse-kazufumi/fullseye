#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 中心座標
    double cx = w / 2.0;
    double cy = h / 2.0;

    // 半幅と半高さの計算
    double half_width = a * w * 0.5;
    double half_height = a * h * 0.3;

    // 回転角の計算 (b は [0, 1] の範囲で、0 〜 180 度に対応)
    double angle = b * M_PI;

    // 回転行列の計算
    double cos_theta = cos(angle);
    double sin_theta = sin(angle);

    // 出力領域を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // 矩形の境界を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 中心からの相対座標
            double dx = x - cx;
            double dy = y - cy;

            // 回転行列の逆行列を用いて元の座標系に戻す
            double x_prime = dx * cos_theta + dy * sin_theta;
            double y_prime = -dx * sin_theta + dy * cos_theta;

            // 矩形の境界内かどうかを判定
            if (fabs(x_prime) <= half_width && fabs(y_prime) <= half_height) {
                out[y * w + x] = 1.0;
            }
        }
    }
}
