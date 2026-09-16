#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像のサイズチェック
    if (h <= 0 || w <= 0) {
        return; // 無効なサイズの場合は何もしない
    }

    // 出力画像の最大値を計算
    double max_val = 0.0;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double val = in[y * w + x];
            if (val > max_val) {
                max_val = val;
            }
        }
    }

    // フィルタの選択
    double filter_factor = (b < 0.5) ? 1.0 : 0.5; // Ram-Lak または Shepp-Logan フィルタ

    // バックプロジェクション
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double sum = 0.0;
            for (int angle = 0; angle < 180; ++angle) {
                double rad = angle * M_PI / 180.0;
                double dx = x * cos(rad) - y * sin(rad);
                double dy = x * sin(rad) + y * cos(rad);
                int ix = (int)round(dx);
                int iy = (int)round(dy);
                if (ix >= 0 && ix < w && iy >= 0 && iy < h) {
                    double val = in[iy * w + ix];
                    double filter_val = fabs(rad) * filter_factor; // フィルタリング
                    sum += val * filter_val;
                }
            }
            out[y * w + x] = sum / max_val; // 正規化
        }
    }
}
