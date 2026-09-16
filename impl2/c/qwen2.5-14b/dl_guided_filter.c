#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 窓の半径と正則化パラメータの計算
    int r = 1 + (int)(a * 4); // 窓の半径
    double eps = 0.001 + 0.05 * b; // 正則化パラメータ

    // 辺の処理方法: 窓が画像の外に出ないように、端のピクセルは無視する。
    // これは、窓が完全に画像内に収まるようにするための簡単な方法である。
    // 画像の端のピクセルは、窓が完全に画像内に収まるまで処理されない。

    // 画像の各ピクセルに対してガイド付きフィルタリングを適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum_I = 0.0, sum_I2 = 0.0, sum_Ix = 0.0, sum_Iy = 0.0;
            double sum_Ix2 = 0.0, sum_Iy2 = 0.0, sum_Ixy = 0.0, sum_IxIy = 0.0;
            double sum_IxI = 0.0, sum_IyI = 0.0;

            // 窓内のピクセルを処理
            for (int dy = -r; dy <= r; ++dy) {
                for (int dx = -r; dx <= r; ++dx) {
                    int y1 = y + dy, x1 = x + dx;
                    if (y1 >= 0 && y1 < h && x1 >= 0 && x1 < w) {
                        double I = in[y1 * w + x1];
                        sum_I += I;
                        sum_I2 += I * I;
                        sum_Ix += I * dx;
                        sum_Iy += I * dy;
                        sum_Ix2 += I * dx * dx;
                        sum_Iy2 += I * dy * dy;
                        sum_Ixy += I * dx * dy;
                        sum_IxI += I * dx * I;
                        sum_IyI += I * dy * I;
                    }
                }
            }

            // 正則化項を考慮した行列の逆行列を計算
            double det = (sum_Ix2 * sum_Iy2 - sum_Ixy * sum_Ixy) + eps;
            double a_lin = (sum_Iy2 * sum_IxI - sum_Ixy * sum_IyI) / det;
            double b_lin = (sum_Ix2 * sum_IyI - sum_Ixy * sum_IxI) / det;

            // 出力画像のピクセルを計算
            out[y * w + x] = a_lin * in[y * w + x] + b_lin;
        }
    }
}
