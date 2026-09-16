#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // Wienerフィルタの適用
    // aパラメータはウィンドウサイズを決定する。ウィンドウサイズは3から9の奇数で、a=0で3、a=1で9となる。
    int window_size = 3 + 2 * (int)(a * 3);
    int half_window = window_size / 2;

    // 出力画像の初期化
    memset(out, 0, h * w * sizeof(double));

    // Wienerフィルタの適用
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            double local_sum = 0.0;
            int count = 0;

            // 局所的なウィンドウ内のピクセルを処理
            for (int dy = -half_window; dy <= half_window; dy++) {
                for (int dx = -half_window; dx <= half_window; dx++) {
                    int ny = y + dy;
                    int nx = x + dx;

                    // ボーダー処理: ピクセルが画像の外に出ないようにする
                    if (ny >= 0 && ny < h && nx >= 0 && nx < w) {
                        local_sum += in[ny * w + nx];
                        count++;
                    }
                }
            }

            // 局所的な平均を計算
            double local_mean = local_sum / count;

            // Wienerフィルタの適用: 局所的な平均を出力に設定
            out[y * w + x] = local_mean;
        }
    }

    // 出力を[0,1]の範囲にクリッピング
    for (int i = 0; i < h * w; i++) {
        if (out[i] < 0.0) {
            out[i] = 0.0;
        } else if (out[i] > 1.0) {
            out[i] = 1.0;
        }
    }
}
