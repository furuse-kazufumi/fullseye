#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // a, b は使用しないパラメータであるため、無視する。

    // 出力画像のサイズは入力画像と同じである。
    int size = h * w;

    // フーリエ変換のための配列を確保
    double* fft_in = (double*)malloc(size * sizeof(double));
    double* fft_out = (double*)malloc(size * sizeof(double));

    // 入力画像を複素数配列に変換 (ここでは実部のみ使用し、虚部は0とする)
    for (int i = 0; i < size; i++) {
        fft_in[i] = in[i];
    }

    // 2次元フーリエ変換を実行
    // ここでは、直接フーリエ変換の実装を行う代わりに、
    // 1次元フーリエ変換を2回適用することを想定する。
    // 実際の実装では、より効率的な2次元フーリエ変換アルゴリズムを使用するべきである。
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            int index = y * w + x;
            fft_out[index] = fft_1d(fft_in + index * w, w);
        }
    }
    for (int x = 0; x < w; x++) {
        for (int y = 0; y < h; y++) {
            int index = y * w + x;
            fft_out[index] = fft_1d(fft_out + index, h);
        }
    }

    // フーリエ変換結果の振幅スペクトルを計算
    for (int i = 0; i < size; i++) {
        fft_out[i] = sqrt(fft_out[i] * fft_out[i]);
    }

    // 振幅スペクトルを対数圧縮して最大値で正規化
    double max_val = 0.0;
    for (int i = 0; i < size; i++) {
        fft_out[i] = log1p(fft_out[i]);
        if (fft_out[i] > max_val) {
            max_val = fft_out[i];
        }
    }
    for (int i = 0; i < size; i++) {
        out[i] = fft_out[i] / max_val;
    }

    // メモリを解放
    free(fft_in);
    free(fft_out);
}

// 1次元フーリエ変換の簡易実装 (ここでは実装しない)
double fft_1d(double* data, int n) {
    // 1次元フーリエ変換の実装
    // ここでは、簡易的な実装として、単純な畳み込みを想定する。
    // 実際の実装では、より効率的なアルゴリズムを使用するべきである。
    double sum = 0.0;
    for (int i = 0; i < n; i++) {
        sum += data[i];
    }
    return sum;
}
