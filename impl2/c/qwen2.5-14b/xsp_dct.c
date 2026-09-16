#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // DCT-II の実装
    // ここでは、DCT-II を実装するための 2D DCT のテンプレートを使用します。
    // DCT-II は正規化された形で実装します。

    // 出力画像のサイズ
    int output_size = h * w;

    // 一時的な配列を確保
    double* temp = (double*)malloc(output_size * sizeof(double));
    if (temp == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // DCT-II の正規化係数
    double norm_factor = 1.0 / sqrt(h * w);

    // DCT-II の実装
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double sum = 0.0;
            for (int i = 0; i < h; i++) {
                for (int j = 0; j < w; j++) {
                    double cos_val = cos(M_PI * (2 * i + 1) * y / (2 * h)) * cos(M_PI * (2 * j + 1) * x / (2 * w));
                    sum += in[i * w + j] * cos_val;
                }
            }
            temp[y * w + x] = sum;
        }
    }

    // パワースペクトルを計算
    for (int i = 0; i < output_size; i++) {
        out[i] = log1p(fabs(temp[i])) * norm_factor;
    }

    // 一時的な配列を解放
    free(temp);
}
