#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // パラメータの範囲チェック
    if (a < 0 || a > 1 || b < 0 || b > 1) {
        return; // パラメータが範囲外の場合は何もしない
    }

    // パディングのための幅と高さの計算
    int padded_h = h + 2;
    int padded_w = w + 2;

    // パディングされた画像の作成
    double* padded_in = (double*)malloc(padded_h * padded_w * sizeof(double));
    if (padded_in == NULL) {
        return; // メモリ確保失敗
    }

    // 元の画像をパディングされた画像にコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + 1) * padded_w + (x + 1)] = in[y * w + x];
        }
    }

    // パディングの境界を元の画像の端の値で埋める
    for (int x = 0; x < padded_w; x++) {
        padded_in[x] = padded_in[x + 1];
        padded_in[(padded_h - 1) * padded_w + x] = padded_in[(padded_h - 2) * padded_w + x];
    }
    for (int y = 0; y < padded_h; y++) {
        padded_in[y * padded_w] = padded_in[y * padded_w + 1];
        padded_in[y * padded_w + (padded_w - 1)] = padded_in[y * padded_w + (padded_w - 2)];
    }

    // バイラテラルフィルタリングの実装
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            double weight_sum = 0.0;
            for (int dy = -1; dy <= 1; dy++) {
                for (int dx = -1; dx <= 1; dx++) {
                    int py = y + dy + 1;
                    int px = x + dx + 1;
                    double weight = exp(-((dy * dy + dx * dx) / (a * a) + (padded_in[py * padded_w + px] - padded_in[(y + 1) * padded_w + (x + 1)]) * (padded_in[py * padded_w + px] - padded_in[(y + 1) * padded_w + (x + 1)]) / (b * b)));
                    sum += padded_in[py * padded_w + px] * weight;
                    weight_sum += weight;
                }
            }
            out[y * w + x] = sum / weight_sum;
        }
    }

    // メモリの解放
    free(padded_in);
}
