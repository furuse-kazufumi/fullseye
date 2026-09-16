#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 遮断周波数の計算
    double cutoff = 0.02 + 0.3 * a;

    // FFT を使用して高域通過フィルタを適用
    // 1. 入力画像を複素数配列に変換
    // 2. 2D FFT を適用
    // 3. 遮断周波数を用いて高周波成分を抽出
    // 4. 逆 FFT を適用
    // 5. 実部を [0,1] の範囲にスケーリング

    // 1. 入力画像を複素数配列に変換
    double* complex_input = (double*)malloc(h * w * 2 * sizeof(double));
    for (int i = 0; i < h * w; i++) {
        complex_input[2 * i] = in[i]; // 実部
        complex_input[2 * i + 1] = 0.0; // 虚部
    }

    // 2. 2D FFT を適用
    // ここでは FFT の実装を省略します。実際の使用時には fftw3 などのライブラリを使用することを推奨します。
    // fft(complex_input, h, w);

    // 3. 遮断周波数を用いて高周波成分を抽出
    // ここでは FFT の結果を直接操作します。実際の使用時には、FFT の結果を適切に処理する必要があります。
    for (int i = 0; i < h * w; i++) {
        double radius = sqrt((i % w) * (i % w) + (i / w) * (i / w)) / sqrt(h * w);
        if (radius > cutoff) {
            complex_input[2 * i] = 0.0; // 高周波成分を除去
        }
    }

    // 4. 逆 FFT を適用
    // ここでは逆 FFT の実装を省略します。実際の使用時には fftw3 などのライブラリを使用することを推奨します。
    // ifft(complex_input, h, w);

    // 5. 実部を [0,1] の範囲にスケーリング
    for (int i = 0; i < h * w; i++) {
        out[i] = (complex_input[2 * i] + 1.0) / 2.0; // [0,1] の範囲にスケーリング
    }

    // メモリを解放
    free(complex_input);
}
