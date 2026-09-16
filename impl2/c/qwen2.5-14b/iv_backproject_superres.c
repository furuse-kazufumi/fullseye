#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 反復回数の計算
    int n = 1 + (int)round(a * 4); // 1 <= n <= 5
    double gain = 0.5 + b; // 0.5 <= gain <= 1.5

    // 出力画像の初期化
    for (int i = 0; i < h * w; ++i) {
        out[i] = in[i];
    }

    // 反復処理
    for (int iter = 0; iter < n; ++iter) {
        // 画像のスケーリングとぼかし
        double* scaled = (double*)malloc(h * w * sizeof(double));
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                scaled[y * w + x] = in[y * w + x];
            }
        }
        // ここにスケーリングとぼかしの処理を追加する

        // リサンプリング
        double* downsampled = (double*)malloc(h * w * sizeof(double));
        // ここにリサンプリングの処理を追加する

        // リサンプリング誤差の計算
        double* error = (double*)malloc(h * w * sizeof(double));
        for (int i = 0; i < h * w; ++i) {
            error[i] = in[i] - downsampled[i];
        }

        // バックプロジェクション
        for (int y = 0; y < h; ++y) {
            for (int x = 0; x < w; ++x) {
                out[y * w + x] += gain * error[y * w + x];
            }
        }

        // メモリの解放
        free(scaled);
        free(downsampled);
        free(error);
    }
}
