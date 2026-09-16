#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // K の計算
    double K = 0.02 + 0.2 * a;
    // 反復回数の計算
    int iters = 5 + (int)(b * 15);

    // 画像の周囲を 1 ピクセル分拡張するためのテンポラリ配列
    double* padded_in = (double*)malloc((h + 2) * (w + 2) * sizeof(double));
    double* padded_out = (double*)malloc((h + 2) * (w + 2) * sizeof(double));

    // 入力画像を周期境界条件で拡張
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[(y + 1) * (w + 2) + (x + 1)] = in[y * w + x];
        }
    }

    // 周期境界条件の設定
    for (int x = 0; x < w + 2; x++) {
        padded_in[x + 1] = padded_in[w + x + 1];
        padded_in[(h + 1) * (w + 2) + x + 1] = padded_in[h * (w + 2) + x + 1];
    }
    for (int y = 0; y < h + 2; y++) {
        padded_in[y * (w + 2)] = padded_in[y * (w + 2) + w];
        padded_in[y * (w + 2) + w + 1] = padded_in[y * (w + 2) + 1];
    }

    // 反復処理
    for (int iter = 0; iter < iters; iter++) {
        // 水平方向の処理
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double diff = padded_in[(y + 1) * (w + 2) + (x + 2)] - padded_in[(y + 1) * (w + 2) + x];
                double conductivity = exp(-(diff / K) * (diff / K));
                padded_out[(y + 1) * (w + 2) + (x + 1)] = padded_in[(y + 1) * (w + 2) + (x + 1)] + 0.2 * conductivity * diff;
            }
        }

        // 垂直方向の処理
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double diff = padded_in[(y + 2) * (w + 2) + (x + 1)] - padded_in[(y) * (w + 2) + (x + 1)];
                double conductivity = exp(-(diff / K) * (diff / K));
                padded_out[(y + 1) * (w + 2) + (x + 1)] += 0.2 * conductivity * diff;
            }
        }

        // テンポラリ配列の入れ替え
        double* temp = padded_in;
        padded_in = padded_out;
        padded_out = temp;
    }

    // 出力画像へのコピー
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            out[y * w + x] = padded_in[(y + 1) * (w + 2) + (x + 1)];
        }
    }

    // メモリの解放
    free(padded_in);
    free(padded_out);
}
