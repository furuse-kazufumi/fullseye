#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の端を処理する際、境界外のピクセルは近傍のピクセル値を用いる。
    // ここでは、境界外のピクセルは0と仮定する。

    // 出力画像の最大値を初期化
    double max_out = 0.0;

    // フィルタリング処理
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // ピクセルのインデックス
            int idx = y * w + x;

            // フィルタリングのための近傍ピクセルのインデックス
            int idx_left = (x > 0) ? idx - 1 : idx;
            int idx_right = (x < w - 1) ? idx + 1 : idx;
            int idx_top = (y > 0) ? idx - w : idx;
            int idx_bottom = (y < h - 1) ? idx + w : idx;

            // x 方向の微分
            double dx = in[idx_right] - in[idx_left];
            // y 方向の微分
            double dy = in[idx_bottom] - in[idx_top];

            // 方向を指定する
            double derivative = (b == 0.0) ? dx : (b == 1.0) ? dy : sqrt(dx * dx + dy * dy);

            // 階数を指定する
            double result = (a == 1.0) ? derivative : sqrt(dx * dx + dy * dy);

            // 出力画像の最大値を更新
            if (result > max_out) {
                max_out = result;
            }

            // 出力を格納
            out[idx] = result;
        }
    }

    // 出力を正規化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            out[idx] /= max_out;
        }
    }
}
