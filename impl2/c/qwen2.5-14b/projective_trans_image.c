#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 射影変換のパラメータを計算
    double d = 0.06 + 0.12 * a;
    double dx = d * w;
    double dy = d * h;

    // 射影変換行列の計算
    double A[9] = {
        1.0, 0.0, 0.0,
        0.0, 1.0, 0.0,
        -dx / (2.0 * w), -dy / (2.0 * h), 1.0
    };

    // 射影変換の実行
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 射影変換後の座標を計算
            double x_new = (A[0] * x + A[1] * y + A[2]) / (A[6] * x + A[7] * y + A[8]);
            double y_new = (A[3] * x + A[4] * y + A[5]) / (A[6] * x + A[7] * y + A[8]);

            // 反射境界条件を適用
            x_new = fmod(x_new + 0.5, 1.0) - 0.5;
            y_new = fmod(y_new + 0.5, 1.0) - 0.5;

            // 射影変換後の座標を画像の座標に変換
            int x_new_int = (int)(x_new * w + 0.5);
            int y_new_int = (int)(y_new * h + 0.5);

            // 出力画像に値を設定
            out[y * w + x] = in[y_new_int * w + x_new_int];
        }
    }
}
