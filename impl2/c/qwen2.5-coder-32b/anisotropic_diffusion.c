#include <math.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    int num_iterations = (int)(2 + 8 * a); // a が [0,1] の範囲で 2〜10 の反復回数にマッピング
    double K = 0.05 + 0.25 * b; // b が [0,1] の範囲で 0.05〜0.3 の閾値にマッピング

    // 一時的な画像バッファ
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        return; // メモリ確保に失敗した場合は何もしない
    }

    // 周期境界条件を適用した近傍ピクセルのインデックスを計算するマクロ
    #define CLAMP(x, min, max) ((x) < (min) ? (max) - (min) + (x) : ((x) > (max) ? (min) : (x)))
    #define INDEX(y, x) ((CLAMP(y, 0, h - 1) * w) + CLAMP(x, 0, w - 1))

    // 初期出力を入力画像にコピー
    memcpy(out, in, h * w * sizeof(double));

    for (int iter = 0; iter < num_iterations; ++iter) {
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                double center = out[y * w + x];
                double left = out[INDEX(y, x - 1)];
                double right = out[INDEX(y, x + 1)];
                double up = out[INDEX(y - 1, x)];
                double down = out[INDEX(y + 1, x)];

                double grad_x = (right - left) / 2.0;
                double grad_y = (down - up) / 2.0;

                double c_x = exp(-(grad_x * grad_x) / (K * K));
                double c_y = exp(-(grad_y * grad_y) / (K * K));

                temp[y * w + x] = center + 0.25 * (c_x * (right - left) + c_y * (down - up));
            }
        }
        // 出力と一時バッファを交換
        double* swap = out;
        out = temp;
        temp = swap;
    }

    // 最終結果を出力バッファにコピー (必要に応じて)
    if (out != temp) {
        memcpy(out, temp, h * w * sizeof(double));
    }

    // 一時バッファを解放
    free(temp);
}
