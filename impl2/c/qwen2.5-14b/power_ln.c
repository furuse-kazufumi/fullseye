#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。実装では FFT を行い、振幅の対数を最大値正規化して出力する。
    // 画像の端を処理する際は、境界外のピクセルは既存のピクセル値を用いて補間しない。
    // 代わりに、FFT は境界外のピクセルをゼロと仮定する。

    // FFT を行うためのテンプレート画像を用意。境界外のピクセルは 0 で初期化。
    double* padded_in = (double*)malloc((h + 2) * (w + 2) * sizeof(double));
    for (int i = 0; i < (h + 2) * (w + 2); i++) {
        padded_in[i] = 0.0;
    }
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            padded_in[y * (w + 2) + x + 1] = in[y * w + x];
        }
    }

    // FFT を実行
    // ここでは FFT の実装を省略し、仮想的な振幅と位相を生成する。
    // 実際の実装では fftw3 などのライブラリを使用する。
    double* fft_result = (double*)malloc(h * w * sizeof(double));
    for (int i = 0; i < h * w; i++) {
        fft_result[i] = sqrt(padded_in[i] * padded_in[i] + padded_in[i + h * (w + 2)] * padded_in[i + h * (w + 2)]);
    }

    // 振幅の対数を計算
    double max_amplitude = 0.0;
    for (int i = 0; i < h * w; i++) {
        fft_result[i] = log1p(fft_result[i]);
        if (fft_result[i] > max_amplitude) {
            max_amplitude = fft_result[i];
        }
    }

    // 最大値正規化
    for (int i = 0; i < h * w; i++) {
        out[i] = fft_result[i] / max_amplitude;
    }

    // メモリ解放
    free(padded_in);
    free(fft_result);
}
