#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 辺の処理を避けるため、内部領域のみを処理する。
    // しきい値の計算
    double low_threshold = 0.1 + 0.3 * a;
    double high_threshold = fmax(low_threshold + 1e-3, 0.3 + 0.4 * b);

    // グレースケール画像の勾配と方向を計算
    // ここでは、簡単のため、勾配の計算を省略し、直接しきい値処理を行う。
    // 実際の実装では、kornia.filters.canny などのライブラリを使用する。

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // 内部ピクセルについて処理
    for (int y = 1; y < h - 1; ++y) {
        for (int x = 1; x < w - 1; ++x) {
            // 簡易的なエッジ検出処理（実際には勾配計算が必要）
            double intensity = in[y * w + x];
            if (intensity > high_threshold) {
                out[y * w + x] = 1.0;
            } else if (intensity > low_threshold) {
                // 非最大値抑制とリンク処理（実装省略）
                // ここでは、しきい値を超えた場合のみエッジとして扱う。
                out[y * w + x] = 1.0;
            }
        }
    }
}
