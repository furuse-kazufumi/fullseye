#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 円盤の半径を計算
    int radius = 1 + (int)(a * 4);
    // 円盤の半径が画像のサイズを超えないように制限
    if (radius > w / 2) {
        radius = w / 2;
    }
    if (radius > h / 2) {
        radius = h / 2;
    }

    // 画像の端を処理するための境界値
    int border = radius;
    // 画像の端をどのように処理するか: ここでは、端の画素はその値をそのまま出力する。
    // これは、端の画素の近傍が存在しない場合の処理方法です。

    // 出力画像の初期化
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = in[y * w + x];
        }
    }

    // 局所平均を計算
    for (int y = border; y < h - border; y++) {
        for (int x = border; x < w - border; x++) {
            double sum = 0.0;
            int count = 0;
            for (int dy = -radius; dy <= radius; dy++) {
                for (int dx = -radius; dx <= radius; dx++) {
                    int nx = x + dx;
                    int ny = y + dy;
                    if (nx >= 0 && nx < w && ny >= 0 && ny < h) {
                        sum += in[ny * w + nx];
                        count++;
                    }
                }
            }
            double mean = sum / count;
            out[y * w + x] = in[y * w + x] - mean;
        }
    }
}
