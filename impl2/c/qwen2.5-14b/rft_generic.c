#include <math.h>

void fs2_apply(const double* in, int h, int w, double a, double b, double* out) {
    // つまみ a, b は未使用。実装では通常の複素 FFT を計算してから実部の絶対値を最大値で正規化する。
    // ここでは、実数画像に対して直接実数 FFT を行う代わりに、複素数 FFT を行うため、
    // 入力画像を複素数配列として扱い、虚部は全て 0 とする。

    // 出力画像の最大値を求めるための変数
    double max_out = 0.0;

    // 複素数 FFT を行うための仮想的な虚部配列
    double* imaginary = (double*)malloc(h * w * sizeof(double));
    if (imaginary == NULL) {
        // メモリ確保失敗時の処理
        return;
    }
    memset(imaginary, 0, h * w * sizeof(double)); // 虚部は全て 0

    // 実部と虚部からなる複素数配列
    double complex* complex_in = (double complex*)malloc(h * w * sizeof(double complex));
    if (complex_in == NULL) {
        free(imaginary);
        return;
    }

    // 実部と虚部から複素数配列を作成
    for (int i = 0; i < h * w; i++) {
        complex_in[i] = in[i] + imaginary[i] * I;
    }

    // 複素数 FFT を行う (ここでは、実装の詳細を省略し、FFT 関数を仮定)
    double complex* complex_out = (double complex*)malloc(h * w * sizeof(double complex));
    if (complex_out == NULL) {
        free(complex_in);
        free(imaginary);
        return;
    }

    // FFT 関数の呼び出し (ここでは、実装の詳細を省略)
    // fft(complex_in, complex_out, h, w);

    // 実部の絶対値を計算し、最大値を更新
    for (int i = 0; i < h * w; i++) {
        double abs_val = cabs(complex_out[i]);
        if (abs_val > max_out) {
            max_out = abs_val;
        }
        out[i] = abs_val;
    }

    // 最大値で正規化
    if (max_out > 0.0) {
        for (int i = 0; i < h * w; i++) {
            out[i] /= max_out;
        }
    }

    // メモリ解放
    free(complex_out);
    free(complex_in);
    free(imaginary);
}
