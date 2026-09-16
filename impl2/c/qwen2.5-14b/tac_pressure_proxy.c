#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 判定: a と b の範囲を [0,1] に制限
    double gain = fmax(0.0, fmin(1.0, a));
    double sigma = 0.5 + 4.0 * fmax(0.0, fmin(1.0, b));

    // データの範囲を [0,1] に制限
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            out[idx] = fmax(0.0, fmin(1.0, in[idx]));
        }
    }

    // データのガウシアン平滑化
    double gaussian_kernel[9] = {
        0.054, 0.138, 0.054,
        0.138, 0.336, 0.138,
        0.054, 0.138, 0.054
    };
    double sum_kernel = 0.0;
    for (int i = 0; i < 9; ++i) {
        sum_kernel += gaussian_kernel[i];
    }

    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double smoothed = 0.0;
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        int idx = ny * w + nx;
                        smoothed += in[idx] * gaussian_kernel[(ky + 1) * 3 + (kx + 1)] / sum_kernel;
                    }
                }
            }
            out[y * w + x] = smoothed;
        }
    }

    // データの偏差の計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            double deviation = fabs(out[idx] - in[idx]);
            out[idx] = deviation;
        }
    }

    // データのゲート処理
    double max_deviation = 0.0;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            max_deviation = fmax(max_deviation, out[idx]);
        }
    }
    double gate_threshold = 0.15 * max_deviation + 0.005;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            if (out[idx] < gate_threshold) {
                out[idx] = 0.0;
            }
        }
    }

    // データのゲイン適用
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            out[idx] *= gain;
        }
    }

    // データのガウシアン平滑化 (再適用)
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double smoothed = 0.0;
            for (int ky = -1; ky <= 1; ++ky) {
                for (int kx = -1; kx <= 1; ++kx) {
                    int ny = y + ky;
                    int nx = x + kx;
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        int idx = ny * w + nx;
                        smoothed += out[idx] * gaussian_kernel[(ky + 1) * 3 + (kx + 1)] / sum_kernel;
                    }
                }
            }
            out[y * w + x] = smoothed;
        }
    }

    // 最終的な出力のクリッピング
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            out[idx] = fmax(0.0, fmin(1.0, out[idx]));
        }
    }
}
