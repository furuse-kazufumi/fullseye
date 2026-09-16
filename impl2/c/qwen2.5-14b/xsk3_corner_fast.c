#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 定数の計算
    int n = 9 + (int)(a * 3); // 連続画素数のしきい値
    double threshold = 0.05 + 0.2 * b; // 輝度差のしきい値

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // FAST コーナー検出
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 中心画素の明るさ
            double center = in[y * w + x];

            // 連続する明るい/暗い画素のカウント
            int bright_count = 0;
            int dark_count = 0;

            // 中心画素の周囲の円周上の画素をチェック
            for (int i = 0; i < 16; i++) {
                int nx = (x + cos(M_PI * i / 8.0)) + 0.5;
                int ny = (y + sin(M_PI * i / 8.0)) + 0.5;

                // 画像の範囲外を処理するための境界処理
                if (nx < 0) nx = 0;
                if (ny < 0) ny = 0;
                if (nx >= w) nx = w - 1;
                if (ny >= h) ny = h - 1;

                double neighbor = in[ny * w + nx];

                // 輝度差の計算
                double diff = fabs(center - neighbor);

                // 連続する明るい/暗い画素のカウント
                if (diff > threshold) {
                    if (neighbor > center) {
                        bright_count++;
                    } else {
                        dark_count++;
                    }
                }

                // 連続画素数のしきい値を超えた場合、コーナーとして検出
                if (bright_count >= n || dark_count >= n) {
                    out[y * w + x] = 1.0;
                    break;
                }
            }
        }
    }

    // 出力画像の正規化
    double max_response = 0.0;
    for (int i = 0; i < h * w; i++) {
        if (out[i] > max_response) {
            max_response = out[i];
        }
    }
    if (max_response > 0.0) {
        for (int i = 0; i < h * w; i++) {
            out[i] /= max_response;
        }
    }
}
