#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 異方性拡散のパラメータ
    int iterations = (int)(a * 9) + 2; // 反復回数
    double threshold = b * 0.25 + 0.05; // 伝導度の閾値

    // 画像の端の処理は周期的に行う
    // 画像のコピーを作成し、端の処理を周期的に行うための準備
    double* temp = (double*)malloc(h * w * sizeof(double));
    if (temp == NULL) {
        return; // メモリ確保失敗
    }

    // 入力画像をコピー
    for (int i = 0; i < h * w; i++) {
        temp[i] = in[i];
    }

    // 異方性拡散の反復処理
    for (int iter = 0; iter < iterations; iter++) {
        // 横方向の拡散
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double left = temp[(y * w + (x - 1 + w) % w)];
                double right = temp[(y * w + (x + 1) % w)];
                double diff = (right - left) / 2.0;
                double conductance = exp(-(diff / threshold) * (diff / threshold));
                out[y * w + x] = temp[y * w + x] + conductance * diff;
            }
        }

        // 縦方向の拡散
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                double up = temp[((y - 1 + h) % h) * w + x];
                double down = temp[((y + 1) % h) * w + x];
                double diff = (down - up) / 2.0;
                double conductance = exp(-(diff / threshold) * (diff / threshold));
                out[y * w + x] += conductance * diff;
            }
        }

        // 次の反復のために出力を一時領域にコピー
        for (int i = 0; i < h * w; i++) {
            temp[i] = out[i];
        }
    }

    // メモリ解放
    free(temp);
}
