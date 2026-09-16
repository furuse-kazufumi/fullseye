#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを計算
    int se_size = 3 + 2 * (int)(a * 3);
    int se_radius = se_size / 2;

    // 出力画像を初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // エロージョン処理
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double min_val = in[y * w + x];
            for (int dy = -se_radius; dy <= se_radius; dy++) {
                for (int dx = -se_radius; dx <= se_radius; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の境界外を処理する方法: ここでは境界外の画素は現在の画素値を維持する。
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        min_val = fmin(min_val, in[ny * w + nx]);
                    }
                }
            }
            out[y * w + x] = min_val;
        }
    }
}
