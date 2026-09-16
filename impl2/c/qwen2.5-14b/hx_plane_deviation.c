#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用パラメータとして無視する。
    (void)a;
    (void)b;

    // 平均値を計算するための一時変数
    double sum_x = 0.0, sum_y = 0.0, sum_xx = 0.0, sum_yy = 0.0, sum_xy = 0.0, sum_xyy = 0.0, sum = 0.0;
    double A, B, C;

    // 入力画像の総和を計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double v = in[y * w + x];
            sum += v;
            sum_x += (double)x * v;
            sum_y += (double)y * v;
            sum_xx += (double)x * x * v;
            sum_yy += (double)y * y * v;
            sum_xy += (double)x * y * v;
            sum_xyy += (double)x * y * y * v;
        }
    }

    // 係数行列の計算
    double det = (double)h * w * sum_xx + sum_xyy * w - sum_xy * sum_xy - sum_x * sum_y * w;
    A = (sum_xx * sum_yy - sum_xy * sum_xy - sum_xyy * sum_x + sum_y * sum_y * sum_xx - sum_yy * sum_x * sum_x) / det;
    B = (sum_yy * sum_x - sum_xy * sum_y - sum_xyy * w + sum_y * sum_y * w - sum_yy * sum_x) / det;
    C = (sum - A * sum_xx - B * sum_x - C * sum_y) / ((double)h * w);

    // 平面近似からの偏差を計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double v = in[y * w + x];
            double plane_value = A * (double)x * x + B * (double)y * y + C;
            double deviation = fabs(v - plane_value);
            out[y * w + x] = fmin(1.0, fmax(0.0, deviation)); // [0,1] にクリップ
        }
    }
}
