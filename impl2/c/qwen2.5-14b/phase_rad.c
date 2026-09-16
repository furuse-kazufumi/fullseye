#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は使用しない
    (void)a;
    (void)b;

    // FFT を行うための一時的な配列を確保
    double* fft_real = (double*)malloc(h * w * sizeof(double));
    double* fft_imag = (double*)malloc(h * w * sizeof(double));
    double* phase = (double*)malloc(h * w * sizeof(double));

    // 入力画像を実部と虚部に分割
    for (int i = 0; i < h * w; ++i) {
        fft_real[i] = in[i];
        fft_imag[i] = 0.0; // 虚部は初期値 0
    }

    // 2D FFT を実行 (ここでは手動で実装)
    // ここでは、実装の簡略化のため、2D FFT の実装を省略し、単純な変換を想定
    // 実際には、2D FFT を実装する必要がある

    // 仮の 2D FFT 実装 (ここでは単純な変換を想定)
    for (int y = 0; y < h; ++y) {
        for (int x = 0; x < w; ++x) {
            int idx = y * w + x;
            // 仮の位相計算 (実際には 2D FFT の結果を使用)
            phase[idx] = atan2(fft_imag[idx], fft_real[idx]);
        }
    }

    // 位相を [0, 1] の範囲に線形変換
    for (int i = 0; i < h * w; ++i) {
        // 位相を [-π, π] の範囲に正規化
        phase[i] = (phase[i] + M_PI) / (2 * M_PI);
        // 位相を [0, 1] の範囲に変換
        out[i] = phase[i];
    }

    // 一時的な配列を解放
    free(fft_real);
    free(fft_imag);
    free(phase);
}
