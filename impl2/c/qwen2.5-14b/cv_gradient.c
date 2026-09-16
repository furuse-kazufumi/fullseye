#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 構造要素のサイズを計算
    int se_size = 3 + 2 * (int)(a * 3);
    // 構造要素のサイズが奇数であることを確認
    if (se_size % 2 == 0) {
        se_size++;
    }

    // 出力画像の最大値を初期化
    double max_out = 0.0;

    // 出力画像の各ピクセルを計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            // 膨張結果と収縮結果を計算
            double dilation = 0.0;
            double erosion = DBL_MAX;
            for (int dy = -se_size / 2; dy <= se_size / 2; dy++) {
                for (int dx = -se_size / 2; dx <= se_size / 2; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;
                    // 画像の境界外を無視
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        double pixel = in[ny * w + nx];
                        dilation = fmax(dilation, pixel);
                        erosion = fmin(erosion, pixel);
                    }
                }
            }
            // 勾配を計算
            double gradient = dilation - erosion;
            // 出力画像の最大値を更新
            max_out = fmax(max_out, gradient);
            // 出力画像に勾配を格納
            out[y * w + x] = gradient;
        }
    }

    // 出力画像を正規化
    for (int i = 0; i < h * w; i++) {
        out[i] /= max_out;
    }
}
