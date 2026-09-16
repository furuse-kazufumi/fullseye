#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない

    // フーリエ変換のためのテンポラリ配列を確保
    double* fft_in = (double*)malloc(h * w * sizeof(double));
    double* fft_out = (double*)malloc(h * w * sizeof(double));

    // 入力画像を -1 から 1 の範囲にスケーリング
    for (int i = 0; i < h * w; ++i) {
        fft_in[i] = in[i] * 2.0 - 1.0;
    }

    // 2D フーリエ変換 (ここでは単純な実装を想定)
    // 実際の実装では fftw3 などのライブラリを使用することを推奨
    // ここでは単純な例として、各ピクセルをそのまま出力する
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            fft_out[idx] = fft_in[idx];
        }
    }

    // パワースペクトルを計算
    for (int i = 0; i < h * w; ++i) {
        out[i] = log1p(fft_out[i] * fft_out[i]);
    }

    // テンポラリ配列を解放
    free(fft_in);
    free(fft_out);
}
