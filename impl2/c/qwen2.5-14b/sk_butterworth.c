#include <math.h>
#include <stdlib.h>
#include <string.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 画像の周波数領域への変換
    double* fft_in = (double*)malloc(h * w * sizeof(double) * 2); // 実部と虚部
    double* fft_out = (double*)malloc(h * w * sizeof(double) * 2);

    // 1. 入力画像を FFT に変換
    // ここでは、実装の詳細を省略し、仮想的な FFT 関数 fft_transform を使用する
    fft_transform(in, h, w, fft_in);

    // 2. Butterworth フィルタを適用
    double cutoff_frequency_ratio = 0.05 + 0.3 * a;
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            double r = fft_in[idx * 2];
            double i = fft_in[idx * 2 + 1];
            double distance = sqrt((x - w / 2) * (x - w / 2) + (y - h / 2) * (y - h / 2));
            double filter_response = 1.0 / (1.0 + pow(distance / (cutoff_frequency_ratio * w), 2 * a));
            fft_out[idx * 2] = r * filter_response;
            fft_out[idx * 2 + 1] = i * filter_response;
        }
    }

    // 3. FFT の逆変換
    // ここでは、実装の詳細を省略し、仮想的な IFFT 関数 ifft_transform を使用する
    ifft_transform(fft_out, h, w, out);

    // 4. 出力画像のクリッピング
    for (int i = 0; i < h * w; i++) {
        out[i] = fmin(1.0, fmax(0.0, out[i]));
    }

    // メモリの解放
    free(fft_in);
    free(fft_out);
}

// FFT と IFFT の仮想的な実装
void fft_transform(const double* in, int h, int w, double* out) {
    // ここに実際の FFT 実装を記述
}

void ifft_transform(const double* in, int h, int w, double* out) {
    // ここに実際の IFFT 実装を記述
}
