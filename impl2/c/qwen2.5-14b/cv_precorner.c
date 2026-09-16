#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。OpenCV の preCornerDetect の実装に従う。
    // 端の扱い: OpenCV の BORDER_REFLECT_101 を使用。これは端の画素を重複させずに折り返す方法。
    // 出力をその画像の最大値で正規化する。

    // 画像の最大値を求める
    double max_val = -INFINITY;
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            double val = in[y * w + x];
            if (val > max_val) {
                max_val = val;
            }
        }
    }

    // preCornerDetect の計算
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            // 3x3 のマスクを使用
            double sum = 0.0;
            for (int dy = -1; dy <= 1; ++dy) {
                for (int dx = -1; dx <= 1; ++dx) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 端の画素を重複させずに折り返す
                    if (ny < 0) ny = -ny - 1;
                    if (nx < 0) nx = -nx - 1;
                    if (ny >= h) ny = 2 * h - ny - 1;
                    if (nx >= w) nx = 2 * w - nx - 1;
                    sum += in[ny * w + nx];
                }
            }
            // preCornerDetect の計算
            double val = fabs(sum);
            // 正規化
            out[y * w + x] = val / max_val;
        }
    }
}
