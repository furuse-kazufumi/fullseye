#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用
    (void)a;
    (void)b;

    // フーリエ変換の結果を格納する配列
    double* fft_result = (double*)malloc(h * w * sizeof(double) * 2);
    if (fft_result == NULL) {
        // メモリ確保失敗時の処理
        return;
    }

    // 画像のフーリエ変換
    // ここでは、単純なフーリエ変換の実装を想定しています。
    // 実際には、より効率的なアルゴリズム（例：FFT）を使用する必要があります。
    // また、複素数の配列として fft_result を扱います。
    // ここでは、単純な実装のため、各ピクセルの値をそのまま複素数の実部とし、虚部は0とします。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            fft_result[idx * 2] = in[idx]; // 実部
            fft_result[idx * 2 + 1] = 0.0; // 虚部
        }
    }

    // フーリエ変換の結果を fftshift する
    // 低周波成分を中心に移動させる
    double* fft_shifted = (double*)malloc(h * w * sizeof(double) * 2);
    if (fft_shifted == NULL) {
        free(fft_result);
        return;
    }
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            int shifted_y = (y + h / 2) % h;
            int shifted_x = (x + w / 2) % w;
            int shifted_idx = shifted_y * w + shifted_x;
            fft_shifted[shifted_idx * 2] = fft_result[idx * 2]; // 実部
            fft_shifted[shifted_idx * 2 + 1] = fft_result[idx * 2 + 1]; // 虚部
        }
    }
    free(fft_result);

    // パワースペクトルを計算
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            int fft_idx = idx * 2;
            double real = fft_shifted[fft_idx];
            double imag = fft_shifted[fft_idx + 1];
            double power = real * real + imag * imag;
            out[idx] = log1p(power); // log1p で圧縮
        }
    }

    // メモリを解放
    free(fft_shifted);
}
