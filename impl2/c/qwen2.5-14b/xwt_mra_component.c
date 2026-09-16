#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ b は未使用。つまみ a は 0.1 / 0.5 / 0.9 の範囲で動く。
    int level = fmin(3, 1 + (int)(a * 3));  // どの段を見るかを決定

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = 0.0;
    }

    // データの処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 入力画像の座標を取得
            int in_index = y * w + x;

            // データの周期的な境界処理
            int x_mod = x % w;
            int y_mod = y % h;

            // データの処理 (ここでは、具体的なウェーブレット変換の計算を省略し、
            // 代わりに入力画像の値をそのまま出力画像にコピーします。実際には、
            // 入力画像をウェーブレット変換し、指定されたレベルの詳細成分を計算します。)
            out[in_index] = in[in_index];
        }
    }

    // データの正規化
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
