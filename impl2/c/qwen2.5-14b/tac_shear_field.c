#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端の処理について、境界外のピクセルは近傍のピクセルの値を用いて補間します。
    // これは、仕様書で明示的に指定されていないため、この実装の選択です。

    // ディファージェント (差分) 配列を用意
    double dx[h * w];
    double dy[h * w];

    // ディファージェントを計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // x 方向のディファージェント
            int x_left = x > 0 ? x - 1 : x;
            int x_right = x < w - 1 ? x + 1 : x;
            dx[y * w + x] = in[y * w + x_right] - in[y * w + x_left];

            // y 方向のディファージェント
            int y_top = y > 0 ? y - 1 : y;
            int y_bottom = y < h - 1 ? y + 1 : y;
            dy[y * w + x] = in[y_bottom * w + x] - in[y_top * w + x];
        }
    }

    // 出力画像を計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // J11, J12, J22 の計算
            double J11 = dx[y * w + x] * dx[y * w + x];
            double J12 = dx[y * w + x] * dy[y * w + x];
            double J22 = dy[y * w + x] * dy[y * w + x];

            // コヒーレンスの計算
            double coherence = sqrt(pow(J11 - J22, 2) + 4 * pow(J12, 2)) / (J11 + J22 + 1e-6);

            // 出力画像の値を設定
            out[y * w + x] = coherence;
        }
    }

    // 出力画像を [0, 1] の範囲にクリッピング
    for (int i = 0; i < h * w; ++i) {
        out[i] = fmin(1.0, fmax(0.0, out[i]));
    }
}
