#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は未使用パラメータであるため、無視する。

    // 2次多項式近似のための係数を格納する配列
    double coefficients[6];
    // 各点の重みを格納する配列
    double weights[h * w];
    // 各点の x, y 座標を格納する配列
    double x_coords[h * w];
    double y_coords[h * w];

    // 座標を [-1, 1] に正規化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            x_coords[idx] = (2.0 * x - w) / (w - 1);
            y_coords[idx] = (2.0 * y - h) / (h - 1);
            weights[idx] = in[idx];
        }
    }

    // 最小二乗法で係数を計算
    // ここでは、単純な最小二乗法を適用する。より効率的な方法（例：QR分解）を用いることも可能。
    // しかし、この実装では即座の最小二乗法を適用する。
    double A[6 * 6] = {0};
    double b[6] = {0};
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double x_val = x_coords[idx];
            double y_val = y_coords[idx];
            double weight = weights[idx];

            // A の更新
            A[0 + 0 * 6] += weight;
            A[1 + 1 * 6] += weight * x_val * x_val;
            A[2 + 2 * 6] += weight * y_val * y_val;
            A[3 + 3 * 6] += weight * x_val;
            A[4 + 4 * 6] += weight * y_val;
            A[5 + 5 * 6] += weight;
            A[1 + 3 * 6] += weight * x_val;
            A[2 + 4 * 6] += weight * y_val;
            A[3 + 5 * 6] += weight * x_val;
            A[4 + 5 * 6] += weight * y_val;

            // b の更新
            b[0] += weight * in[idx];
            b[1] += weight * in[idx] * x_val;
            b[2] += weight * in[idx] * y_val;
            b[3] += weight * in[idx] * x_val * x_val;
            b[4] += weight * in[idx] * y_val * y_val;
            b[5] += weight * in[idx] * x_val * y_val;
        }
    }

    // A の対角成分を更新
    for (int i = 0; i < 6; ++i) {
        A[i + i * 6] += 1e-6; // 正則化項を追加
    }

    // 係数を計算
    // ここでは、単純なガウス消去法を適用する。
    // 他のより効率的な方法（例：LU分解）を用いることも可能。
    for (int i = 0; i < 6; ++i) {
        double max = fabs(A[i + i * 6]);
        int max_row = i;
        for (int k = i + 1; k < 6; ++k) {
            if (fabs(A[k + i * 6]) > max) {
                max = fabs(A[k + i * 6]);
                max_row = k;
            }
        }
        if (max_row != i) {
            for (int k = i; k < 6; ++k) {
                double tmp = A[max_row + k * 6];
                A[max_row + k * 6] = A[i + k * 6];
                A[i + k * 6] = tmp;
            }
            double tmp = b[max_row];
            b[max_row] = b[i];
            b[i] = tmp;
        }
        for (int k = i + 1; k < 6; ++k) {
            double c = A[k + i * 6] / A[i + i * 6];
            for (int j = i; j < 6; ++j) {
                A[k + j * 6] -= c * A[i + j * 6];
            }
            b[k] -= c * b[i];
        }
    }

    // 係数を計算
    for (int i = 5; i >= 0; --i) {
        double sum = b[i];
        for (int j = i + 1; j < 6; ++j) {
            sum -= A[i + j * 6] * coefficients[j];
        }
        coefficients[i] = sum / A[i + i * 6];
    }

    // 出力を計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double x_val = x_coords[idx];
            double y_val = y_coords[idx];
            out[idx] = coefficients[0] + coefficients[1] * x_val + coefficients[2] * y_val +
                       coefficients[3] * x_val * x_val + coefficients[4] * y_val * y_val +
                       coefficients[5] * x_val * y_val;
        }
    }

    // 出力を [0, 1] の範囲に正規化
    double max_out = 0.0;
    for (int i = 0; i < h * w; ++i) {
        if (out[i] > max_out) {
            max_out = out[i];
        }
    }
    for (int i = 0; i < h * w; ++i) {
        out[i] /= max_out;
    }
}
