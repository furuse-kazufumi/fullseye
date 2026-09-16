#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 256エントリの対数変換テーブルを生成
    double lut[256];
    for (int i = 0; i < 256; i++) {
        double x = (double)i / 255.0;
        lut[i] = 1.0 / (1.0 + exp(-a * (x - b) / (b * (1.0 - b))));
    }

    // 入力画像を処理し、出力画像を生成
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            double value = in[idx];
            // 入力値が [0, 1] の範囲外の場合、範囲内にクリップする
            if (value < 0.0) value = 0.0;
            if (value > 1.0) value = 1.0;
            // 8ビット量子化
            int quantized = (int)(value * 255.0);
            // LUT を使用して変換
            out[idx] = lut[quantized] / 255.0;
        }
    }
}
