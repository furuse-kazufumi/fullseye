#include <math.h>
#include <stdlib.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // 低周波数フィルタリングの遮断周波数を計算
    double cutoff = 0.05 + 0.4 * a;

    // 画像のサイズ
    int size = h * w;

    // FFT 用の配列を確保
    double* fft_in = (double*)malloc(size * 2 * sizeof(double));
    double* fft_out = (double*)malloc(size * 2 * sizeof(double));

    // 入力画像を複素数配列に変換
    for (int i = 0; i < size; i++) {
        fft_in[i * 2] = in[i]; // 実部
        fft_in[i * 2 + 1] = 0.0; // 虚部
    }

    // 2D FFT を実行
    // ここでは FFT の実装を仮定します。実際には fftw3 などのライブラリを使用します。
    // fftw_plan plan = fftw_plan_dft_r2c_2d(h, w, fft_in, fft_out, FFTW_ESTIMATE);
    // fftw_execute(plan);
    // fftw_destroy_plan(plan);

    // 低周波数フィルタリング
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int idx = y * w + x;
            int freq_idx = idx * 2;

            // 周波数空間での座標
            double u = (double)x / w;
            double v = (double)y / h;

            // 周波数空間での距離
            double rad = sqrt((u - 0.5) * (u - 0.5) + (v - 0.5) * (v - 0.5));

            // 低周波数成分を残し、高周波数成分をゼロにする
            if (rad <= cutoff) {
                fft_out[freq_idx] *= 1.0;
                fft_out[freq_idx + 1] *= 1.0;
            } else {
                fft_out[freq_idx] = 0.0;
                fft_out[freq_idx + 1] = 0.0;
            }
        }
    }

    // 逆 FFT を実行
    // ここでは逆 FFT の実装を仮定します。
    // fftw_plan ifft_plan = fftw_plan_dft_c2r_2d(h, w, fft_out, fft_in, FFTW_ESTIMATE);
    // fftw_execute(ifft_plan);
    // fftw_destroy_plan(ifft_plan);

    // 実部を出力画像にコピー
    for (int i = 0; i < size; i++) {
        out[i] = fft_in[i];
    }

    // 画像の値域を [0, 1] にクリップ
    for (int i = 0; i < size; i++) {
        if (out[i] < 0.0) {
            out[i] = 0.0;
        } else if (out[i] > 1.0) {
            out[i] = 1.0;
        }
    }

    // メモリを解放
    free(fft_in);
    free(fft_out);
}
