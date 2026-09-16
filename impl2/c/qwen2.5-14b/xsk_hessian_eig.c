#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。a はヘッセ行列の微分スケールを調整する。
    // ここでは a の値を 0.5 から 3.0 に変換する。
    double sigma = 0.5 + (3.0 - 0.5) * a;

    // ヘッセ行列の成分を計算するための一時的な配列を用意
    double Ixx[h*w], Ixy[h*w], Iyy[h*w];

    // ヘッセ行列の成分を計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;

            // Ixx: d^2I/dx^2
            Ixx[idx] = (in[idx - 1] - 2 * in[idx] + in[idx + 1]) / (sigma * sigma);

            // Iyy: d^2I/dy^2
            Iyy[idx] = (in[idx - w] - 2 * in[idx] + in[idx + w]) / (sigma * sigma);

            // Ixy: d^2I/dxdy
            Ixy[idx] = (in[idx - w - 1] - in[idx - w + 1] - in[idx + w - 1] + in[idx + w + 1]) / (4 * sigma * sigma);
        }
    }

    // 最大固有値を計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;

            // ヘッセ行列のトレースと行列式を計算
            double trace = Ixx[idx] + Iyy[idx];
            double det = Ixx[idx] * Iyy[idx] - Ixy[idx] * Ixy[idx];

            // 固有値を計算
            double lambda1 = (trace + sqrt(trace * trace - 4 * det)) / 2;
            double lambda2 = (trace - sqrt(trace * trace - 4 * det)) / 2;

            // 絶対値が大きい方の固有値を出力
            out[idx] = fabs(lambda1) > fabs(lambda2) ? fabs(lambda1) : fabs(lambda2);
        }
    }

    // 出力を最大値で正規化
    double max_val = 0.0;
    for (int i = 0; i < h * w; ++i) {
        if (out[i] > max_val) {
            max_val = out[i];
        }
    }
    if (max_val > 0.0) {
        for (int i = 0; i < h * w; ++i) {
            out[i] /= max_val;
        }
    }
}
