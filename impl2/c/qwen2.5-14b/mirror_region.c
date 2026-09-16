#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a の値によってミラー軸を決定
    int axis = (a < 0.34) ? 0 : ((a < 0.67) ? 1 : 2);

    // 出力画像の初期化
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            out[y * w + x] = 0.0;
        }
    }

    // ミラー転換
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double in_val = in[y * w + x];
            double out_val = 0.0;

            switch (axis) {
                case 0: // 上下反転
                    out_val = in[(h - 1 - y) * w + x];
                    break;
                case 1: // 左右反転
                    out_val = in[y * w + (w - 1 - x)];
                    break;
                case 2: // 対角線反転
                    out_val = in[(h - 1 - y) * w + (w - 1 - x)];
                    break;
            }

            // 二値化
            if (out_val > 0.5) {
                out_val = 1.0;
            } else {
                out_val = 0.0;
            }

            out[y * w + x] = out_val;
        }
    }
}
