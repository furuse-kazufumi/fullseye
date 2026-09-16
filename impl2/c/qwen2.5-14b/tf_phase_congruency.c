#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 辺の処理について、仕様書では明確に定義されていないため、反対側へ巻き付ける(周期)と解釈する。
    // これは、入力画像の境界外アクセスを周期的な画像として扱うことを意味する。

    // ログガボールフィルタの基本周波数を設定
    double base_wavelength = exp(b * log(2.0)); // b が 0 から 1 まで変化するとき、基本周波数は 1 から 2 まで変化する

    // フィルタのスケーリングファクター
    double scale_factor = 1.0 / (w * h);

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = 0.0;
        }
    }

    // ログガボールフィルタの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double pixel_value = in[y * w + x];
            double noise_threshold = a * (pixel_value + 1e-6); // a はノイズ閾値

            // ログガボールフィルタの応答を計算
            double log_gabor_response = exp(-0.5 * pow((log(pixel_value) - log(base_wavelength)), 2) / (log(2.0) * log(2.0)));

            // フィルタ応答がノイズ閾値を超える場合のみ処理
            if (log_gabor_response > noise_threshold) {
                // フィルタ応答を出力画像に加算
                out[y * w + x] += log_gabor_response * scale_factor;
            }
        }
    }

    // フィルタ応答の絶対値を計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = fabs(out[y * w + x]);
        }
    }
}
